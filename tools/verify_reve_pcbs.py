"""Read back both Rev E PCBs against XML and the shared stack contract.

Run using KiCad's bundled Python. The checker never saves a board, edits a
project, or imports a PCB generator. Only outputs/pcb_review_2026-11-11 is
written. Native CLI DRC is rerun unless --skip-drc is explicitly requested.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import pcbnew as p


REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / 'outputs/pcb_review_2026-11-11'
CLI = Path('C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
KICAD = Path('C:/Program Files/KiCad/10.0/share/kicad')
EXPECTED = {'controller': {'references': 47, 'pins': 233, 'DNP': 3},
            'inverter': {'references': 317, 'pins': 969, 'DNP': 14}}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mm(value):
    return round(p.ToMM(value), 6)


def xy(item):
    return [mm(item.GetPosition().x), mm(item.GetPosition().y)]


def bbox(box):
    return [mm(box.GetX()), mm(box.GetY()), mm(box.GetRight()), mm(box.GetBottom())]


def close(a, b):
    return abs(a - b) <= .005


def fields(part):
    return {field.get('name'): field.text or '' for field in part.findall('./fields/field')}


def read_xml(path):
    root = ET.parse(path).getroot()
    parts = {part.get('ref'): part for part in root.findall('./components/comp')}
    nets, pins = {}, {}
    for net in root.findall('./nets/net'):
        group = {(node.get('ref'), node.get('pin')) for node in net.findall('node')
                 if node.get('ref') in parts}
        if group:
            assert net.get('name') not in nets
            nets[net.get('name')] = group
        for node in group:
            assert node not in pins
            pins[node] = net.get('name')
    libpins = {(part.get('lib'), part.get('part')):
               {pin.get('num') for pin in part.findall('./pins/pin')}
               for part in root.findall('./libparts/libpart')}
    for ref, part in parts.items():
        source = part.find('libsource')
        expected = libpins[(source.get('lib'), source.get('part'))]
        assert expected == {number for rr, number in pins if rr == ref}, (ref, 'XML pin omissions')
    nc = {node for name, group in nets.items() if len(group) == 1
          and name.rsplit('/', 1)[-1].startswith('unconnected-') for node in group}
    return parts, nets, pins, nc


def courtyard(fp):
    fp.BuildCourtyardCaches()
    shapes = []
    for layer in (p.F_CrtYd, p.B_CrtYd):
        shape = fp.GetCourtyard(layer)
        if shape.OutlineCount() and shape.Area() > 0:
            shapes.append((layer, shape))
    return shapes


def model_path(filename, board_dir):
    variables = dict(os.environ)
    variables['KIPRJMOD'] = str(board_dir)
    variables.setdefault('KICAD10_3DMODEL_DIR', str(KICAD / '3dmodels'))
    expanded = re.sub(r'\$\{([^}]+)\}', lambda m: variables.get(m[1], m[0]), filename)
    expanded = re.sub(r'\$\(([^)]+)\)', lambda m: variables.get(m[1], m[0]), expanded)
    target = Path(expanded)
    if not target.is_absolute():
        target = board_dir / target
    return target


def anonymous_mask_association(fp, pad, xml_pin_nets):
    """Validate an optional net annotation on a nonconductive mask aperture.

    Mask-only pads are manufacturing shapes, not additional circuit terminals.
    A net annotation is accepted only as an exact, same-footprint association
    with a numbered copper pad already checked against the XML. Unassigned
    mask/paste/mechanical shapes retain their existing handling.
    """
    record = {'reference': fp.GetReference(), 'position_mm': xy(pad),
              'net': pad.GetNetname(), 'net_code': int(pad.GetNetCode()),
              'layers': [fp.GetBoard().GetLayerName(layer) for layer in pad.GetLayerSet().Seq()]}
    layers = set(pad.GetLayerSet().Seq())
    mask_to_copper = {p.F_Mask: p.F_Cu, p.B_Mask: p.B_Cu}
    if pad.GetNumber():
        return False, record | {'reason': 'association helper requires an unnumbered pad'}
    if not pad.GetNetCode():
        return True, record | {'mode': 'unassigned manufacturing/mechanical shape'}
    if not layers or not layers <= set(mask_to_copper):
        return False, record | {'reason': 'assigned unnumbered pad is not exclusively solder mask'}
    if pad.GetDrillSize().x or pad.GetDrillSize().y:
        return False, record | {'reason': 'mask association cannot have a drilled hole'}
    matches = []
    for copper in fp.Pads():
        key = (fp.GetReference(), copper.GetNumber())
        if (not copper.GetNumber() or key not in xml_pin_nets
                or copper.GetAttribute() == p.PAD_ATTRIB_NPTH
                or copper.GetPosition() != pad.GetPosition()
                or not all(copper.IsOnLayer(mask_to_copper[layer]) for layer in layers)
                or copper.GetNetCode() != pad.GetNetCode()
                or copper.GetNetname() != pad.GetNetname()
                or copper.GetNetname().replace('{slash}', '/') != xml_pin_nets[key]):
            continue
        matches.append(copper)
    if len(matches) != 1:
        return False, record | {'reason': 'expected exactly one co-centered same-net numbered copper pad on the matching face',
                               'matching_copper_pads': len(matches)}
    return True, record | {'mode': 'mask-only metadata association',
                           'associated_numbered_copper_pad': matches[0].GetNumber(),
                           'XML_net': xml_pin_nets[(fp.GetReference(), matches[0].GetNumber())]}


def physical_check(role, path, xml_path, stack):
    parts, nets, pins, nc = read_xml(xml_path)
    board = p.LoadBoard(str(path))
    fps = list(board.GetFootprints())
    by_ref = defaultdict(list)
    for fp in fps:
        by_ref[fp.GetReference()].append(fp)
    failures = []
    record = {'board': str(path.relative_to(REPO)), 'XML': str(xml_path.relative_to(REPO)),
              'input_sha256': {'board': sha(path), 'XML': sha(xml_path)},
              'errors': failures, 'warnings': []}
    mechanical = {row['reference'] for row in stack['mounting_holes']}
    missing, extra = set(parts)-set(by_ref), set(by_ref)-set(parts)-mechanical
    duplicate_refs = {ref: len(items) for ref, items in by_ref.items() if len(items) != 1}
    for check, detail in [('missing_references', sorted(missing)), ('extra_references', sorted(extra)),
                          ('duplicate_references', duplicate_refs)]:
        if detail:
            failures.append({'check': check, 'findings': detail})
    dnp = sum(part.find("property[@name='dnp']") is not None for part in parts.values())
    counts = {'references': len(parts), 'pins': len(pins), 'DNP': dnp}
    if counts != EXPECTED[role]:
        failures.append({'check': 'expected_XML_counts', 'actual': counts, 'expected': EXPECTED[role]})
    pads_checked, unique_nodes = 0, set()
    actual_groups = defaultdict(set)
    duplicate_pad_numbers, nc_records, mismatch, mask_associations = [], [], [], []
    for ref, part in parts.items():
        if ref not in by_ref or len(by_ref[ref]) != 1:
            continue
        fp = by_ref[ref][0]
        expected_fp = part.findtext('footprint') or ''
        for check, actual, expected in [
            ('footprint_ID', fp.GetFPIDAsString(), expected_fp),
            ('component_value', fp.GetValue(), part.findtext('value') or ''),
            ('DNP', bool(fp.IsDNP()), part.find("property[@name='dnp']") is not None),
        ]:
            if actual != expected:
                mismatch.append({'reference': ref, 'check': check, 'expected': expected, 'actual': actual})
        physical = defaultdict(list)
        for pad in fp.Pads():
            number = pad.GetNumber()
            if not number:
                if pad.GetNetCode():
                    accepted, association = anonymous_mask_association(fp, pad, pins)
                    if accepted:
                        mask_associations.append(association)
                    else:
                        mismatch.append({'reference': ref, 'check': 'invalid_unnumbered_pad_net',
                                         'association': association})
                continue
            physical[number].append(pad)
        expected_numbers = {number for rr, number in pins if rr == ref}
        if set(physical) != expected_numbers:
            mismatch.append({'reference': ref, 'check': 'physical_pad_numbers',
                             'missing': sorted(expected_numbers-set(physical)),
                             'extra': sorted(set(physical)-expected_numbers)})
        for number, pads in physical.items():
            key = (ref, number)
            unique_nodes.add(key)
            if len(pads) > 1:
                duplicate_pad_numbers.append({'reference': ref, 'number': number, 'pads': len(pads)})
            for pad in pads:
                pads_checked += 1
                expected, actual = pins.get(key), pad.GetNetname().replace('{slash}', '/')
                if key in nc:
                    accepted = actual in ('', expected)
                    nc_records.append({'reference': ref, 'pin': number, 'net': actual})
                else:
                    accepted = expected is not None and actual == expected and pad.GetNetCode() != 0
                    actual_groups[int(pad.GetNetCode())].add(key)
                if not accepted:
                    mismatch.append({'reference': ref, 'pin': number, 'check': 'pad_net',
                                     'expected': expected, 'actual': actual})
    expected_groups = {frozenset(group) for name, group in nets.items() if not group <= nc}
    groups_equal = expected_groups == {frozenset(group) for group in actual_groups.values()}
    if not groups_equal:
        failures.append({'check': 'non_NC_net_partitions'})
    if mismatch:
        failures.append({'check': 'component_or_pad_mapping', 'findings': mismatch})
    if unique_nodes != set(pins):
        failures.append({'check': 'unique_physical_pin_coverage', 'actual': len(unique_nodes), 'expected': len(pins)})
    record['mapping'] = {'counts': counts, 'PCB_footprints': len(fps),
                         'board_only_mounting_references': sorted(set(by_ref) & mechanical),
                         'unique_physical_pin_nodes': len(unique_nodes),
                         'numbered_copper_pads_checked': pads_checked,
                         'duplicate_numbers_checked_individually': duplicate_pad_numbers,
                         'validated_mask_only_net_associations': mask_associations,
                         'anonymous_pad_policy': 'Unassigned manufacturing/mechanical shapes remain valid. Assigned shapes must be mask-only, hole-free, exactly co-centered with one same-footprint numbered copper pad on each matching face, and use that pad\'s XML-verified net. Anonymous copper cannot carry a net.',
                         'NC_pads': nc_records, 'non_NC_net_partitions_equal': groups_equal,
                         'mismatches': mismatch}
    record['mapping_pass'] = not failures
    record['placements'] = {fp.GetReference(): {'position_mm': xy(fp),
                             'angle_deg': fp.GetOrientationDegrees(), 'layer': fp.GetLayerName(),
                             'footprint': fp.GetFPIDAsString(), 'DNP': bool(fp.IsDNP())}
                            for fp in fps}
    geometry_check(board, by_ref, role, stack, record)
    models, no_models = [], []
    for fp in fps:
        linked = list(fp.Models())
        if not linked:
            no_models.append(fp.GetReference())
        for model in linked:
            target = model_path(model.m_Filename, path.parent)
            models.append({'reference': fp.GetReference(), 'model': model.m_Filename,
                           'resolved_path': str(target), 'exists': target.is_file(),
                           'shown': bool(model.m_Show)})
    record['3D_models'] = {'links': models, 'references_without_model': sorted(no_models),
                           'missing_files': [model for model in models if not model['exists']],
                           'scope': 'File resolution only; a generic model does not qualify exact body or mating height.'}
    if record['3D_models']['missing_files']:
        record['warnings'].append({'check': 'missing_3D_model_files',
                                   'count': len(record['3D_models']['missing_files'])})
    board.BuildConnectivity()
    tracks = list(board.GetTracks())
    record['routing'] = {'raw_pcbnew_unconnected': int(board.GetConnectivity().GetUnconnectedCount(False)),
                          'track_segments': sum(item.GetClass() != 'PCB_VIA' for item in tracks),
                          'vias': sum(item.GetClass() == 'PCB_VIA' for item in tracks),
                          'zones': len(list(board.Zones()))}
    return board, by_ref, record, pins


def geometry_check(board, by_ref, role, stack, record):
    errors, warnings = record['errors'], record['warnings']
    poly = p.SHAPE_POLY_SET()
    valid = board.GetBoardPolygonOutlines(poly, False, None, False, False)
    expected = stack['outline']
    expected_box = [expected[key] for key in ('min_x', 'min_y', 'max_x', 'max_y')]
    actual_box = bbox(poly.BBox()) if valid else None
    outline_pass = bool(valid and poly.OutlineCount() == 1 and
                        all(close(a, b) for a, b in zip(actual_box, expected_box)))
    layers = board.GetCopperLayerCount()
    if not outline_pass:
        errors.append({'check': 'stack_outline', 'expected': expected_box, 'actual': actual_box,
                       'closed': bool(valid), 'outer_contours': poly.OutlineCount()})
    if layers != stack[role]['copper_layers_candidate']:
        errors.append({'check': 'copper_layer_count', 'actual': layers,
                       'expected': stack[role]['copper_layers_candidate']})
    if not close(mm(board.GetDesignSettings().GetBoardThickness()), stack['board_thickness']):
        errors.append({'check': 'board_thickness', 'actual': mm(board.GetDesignSettings().GetBoardThickness())})
    if role == 'controller' and 'U30' in by_ref and by_ref['U30'][0].GetLayer() != p.F_Cu:
        errors.append({'check': 'MCU_top_layer', 'actual': by_ref['U30'][0].GetLayerName()})
    all_courtyards, missing, outside = [], [], []
    for ref, fplist in by_ref.items():
        for fp in fplist:
            shapes = courtyard(fp)
            if not shapes:
                missing.append(ref)
            for layer, shape in shapes:
                all_courtyards.append((ref, layer, shape))
                box = bbox(shape.BBox())
                if any([box[0] < expected_box[0]-.005, box[1] < expected_box[1]-.005,
                        box[2] > expected_box[2]+.005, box[3] > expected_box[3]+.005]):
                    outside.append({'reference': ref, 'layer': board.GetLayerName(layer), 'bbox': box})
    overlaps = []
    for i, (ra, la, a) in enumerate(all_courtyards):
        for rb, lb, b in all_courtyards[i+1:]:
            if ra == rb or la != lb or not a.BBox().Intersects(b.BBox()):
                continue
            intersection = p.SHAPE_POLY_SET()
            intersection.BooleanIntersection(a, b)
            area = float(intersection.Area()) / p.FromMM(1)**2
            if area > .0001:
                overlaps.append({'references': [ra, rb], 'layer': board.GetLayerName(la),
                                 'area_mm2': round(area, 6)})
    if overlaps or missing or outside:
        warnings.append({'check': 'courtyard_review', 'overlaps': len(overlaps),
                         'missing': missing, 'outside_board': len(outside)})
    hole_records, copper_hits, hardware_hits = [], [], []
    copper_layers = list(board.GetEnabledLayers().CuStack())
    unfilled_zones = []
    for raw in board.Zones():
        zone = p.Cast_to_ZONE(raw)
        if not zone.GetIsRuleArea() and not zone.IsFilled():
            unfilled_zones.append({'net': zone.GetNetname(), 'uuid': zone.m_Uuid.AsString()})
    if unfilled_zones:
        warnings.append({'check': 'unfilled_zone_geometry_not_checked', 'zones': unfilled_zones})
    for hole in stack['mounting_holes']:
        ref = hole['reference']
        if ref not in by_ref or len(by_ref[ref]) != 1:
            errors.append({'check': 'mounting_hole_missing', 'reference': ref})
            continue
        fp = by_ref[ref][0]
        pads = list(fp.Pads())
        drill = [mm(pad.GetDrillSize().x) for pad in pads]
        expected_xy = [hole['x'], hole['y']]
        okay = (len(pads) == 1 and pads[0].GetAttribute() == p.PAD_ATTRIB_NPTH
                and all(close(a, b) for a, b in zip(xy(pads[0]), expected_xy))
                and close(mm(pads[0].GetDrillSize().x), hole['drill'])
                and close(mm(pads[0].GetDrillSize().y), hole['drill'])
                and pads[0].GetNetCode() == 0)
        hole_records.append({'reference': ref, 'position_mm': xy(fp), 'drill_mm': drill, 'pass': okay})
        if not okay:
            errors.append({'check': 'mounting_hole_geometry', 'reference': ref})
        point = p.VECTOR2I(p.FromMM(hole['x']), p.FromMM(hole['y']))
        radius = p.FromMM(stack['mounting_copper_keepout_radius'])
        for rr, fplist in by_ref.items():
            for other in fplist:
                for pad in other.Pads():
                    if pad.GetAttribute() == p.PAD_ATTRIB_NPTH:
                        continue
                    hit_layers = [board.GetLayerName(layer) for layer in copper_layers
                                  if pad.IsOnLayer(layer) and pad.GetEffectiveShape(layer).Collide(point, radius)]
                    if hit_layers:
                        copper_hits.append({'hole': ref, 'kind': 'pad', 'reference': rr,
                                            'number': pad.GetNumber(), 'layers': hit_layers})
        for item in board.GetTracks():
            hit_layers = [board.GetLayerName(layer) for layer in copper_layers
                          if item.IsOnLayer(layer) and item.GetEffectiveShape(layer).Collide(point, radius)]
            if hit_layers:
                copper_hits.append({'hole': ref, 'kind': item.GetClass(), 'net': item.GetNetname(),
                                    'uuid': item.m_Uuid.AsString(), 'layers': hit_layers})
        for raw in board.Zones():
            zone = p.Cast_to_ZONE(raw)
            if zone.GetIsRuleArea():
                continue
            hit_layers = [board.GetLayerName(layer) for layer in copper_layers
                          if zone.HasFilledPolysForLayer(layer)
                          and zone.GetFilledPolysList(layer).Collide(point, radius)]
            if hit_layers:
                copper_hits.append({'hole': ref, 'kind': 'filled_zone', 'net': zone.GetNetname(),
                                    'layers': hit_layers})
        for rr, layer, shape in all_courtyards:
            if rr != ref and shape.Collide(point, radius):
                hardware_hits.append({'hole': ref, 'reference': rr, 'layer': board.GetLayerName(layer)})
    if copper_hits:
        errors.append({'check': 'mounting_copper_keepout', 'findings': copper_hits})
    if hardware_hits:
        warnings.append({'check': 'mounting_hardware_courtyard_review', 'findings': hardware_hits})
    buttons = []
    reserve = stack['button_access_reserved']
    for ref in ('SW2', 'SW3') if role == 'controller' else ():
        if ref in by_ref:
            fp = by_ref[ref][0]
            pos = xy(fp)
            okay = (fp.GetLayer() == p.F_Cu and reserve['min_x'] <= pos[0] <= reserve['max_x']
                    and reserve['min_y'] <= pos[1] <= reserve['max_y'])
            buttons.append({'reference': ref, 'position_mm': pos, 'layer': fp.GetLayerName(),
                            'nominal_height_mm': 2.5, 'height_tolerance_mm': .1, 'edge_placement_pass': okay})
            if not okay:
                errors.append({'check': 'core_button_side_access_placement', 'reference': ref})
    bottom_obstacles = []
    if role == 'inverter':
        for ref, layer, shape in all_courtyards:
            if layer != p.B_CrtYd:
                continue
            box = bbox(shape.BBox())
            if (min(box[2], reserve['max_x']) > max(box[0], reserve['min_x'])+.001 and
                    min(box[3], reserve['max_y']) > max(box[1], reserve['min_y'])+.001):
                bottom_obstacles.append({'reference': ref, 'bbox': box,
                                         'connector': ref.startswith('J')})
        if bottom_obstacles:
            warnings.append({'check': 'upper_board_button_access_region', 'findings': bottom_obstacles,
                             'note': 'Review height and hand/tool access; 2D courtyards do not prove 3D collision.'})
    record['geometry'] = {'outline_pass': outline_pass, 'outline_bbox_mm': actual_box,
                           'copper_layers': layers, 'mounting_holes': hole_records,
                           'mounting_copper_keepout_radius_mm': stack['mounting_copper_keepout_radius'],
                           'mounting_copper_intrusions': copper_hits,
                           'unfilled_copper_zones': unfilled_zones,
                           'mounting_hardware_courtyard_review': hardware_hits,
                           'courtyard_missing': missing, 'courtyard_outside_board': outside,
                           'courtyard_overlaps': overlaps, 'core_buttons': buttons,
                           'upper_board_button_access_obstacles': bottom_obstacles}


def stack_check(boards, references, pins, electrical, stack):
    rows, errors = [], []
    for ref, geometry in stack['headers'].items():
        for number in range(1, 33):
            expected_xy = [geometry['pad_1_x'] if number % 2 else geometry['pad_2_x'],
                           geometry['pad_1_y'] + ((number-1)//2)*geometry['row_step_y']]
            actuals = {}
            for role, items in references.items():
                if ref not in items or len(items[ref]) != 1:
                    errors.append({'check': 'header_missing', 'role': role, 'reference': ref})
                    continue
                fp = items[ref][0]
                pads = [pad for pad in fp.Pads() if pad.GetNumber() == str(number)]
                okay = len(pads) == 1 and all(close(a, b) for a, b in zip(xy(pads[0]), expected_xy))
                desired = p.F_Cu if role == 'controller' else p.B_Cu
                okay = okay and fp.GetLayer() == desired
                if not okay:
                    errors.append({'check': 'mating_pad_geometry', 'role': role, 'reference': ref,
                                   'pin': number, 'expected_xy': expected_xy,
                                   'actual_xy': [xy(pad) for pad in pads], 'layer': fp.GetLayerName()})
                expected = electrical[ref][str(number)]
                aliases = electrical['supply_alias'].get(expected, {})
                expected_net = aliases.get(role, expected)
                actual = pins[role].get((ref, str(number)), '').rsplit('/', 1)[-1]
                if role == 'inverter' and expected in electrical['base_unassigned_ports']:
                    net_ok = actual.startswith('unconnected-')
                else:
                    net_ok = actual == expected_net
                if not net_ok:
                    errors.append({'check': 'mating_electrical_contract', 'role': role,
                                   'reference': ref, 'pin': number, 'expected': expected_net, 'actual': actual})
                actuals[role] = {'position_mm': xy(pads[0]) if len(pads) == 1 else None,
                                 'XML_net': actual, 'expected_XML_net': expected_net,
                                 'contract_pass': net_ok, 'geometry_pass': okay}
            rows.append({'header': ref, 'pin': number, 'expected_XY_mm': expected_xy, 'boards': actuals})
    return {'contacts': len(rows), 'pins': rows, 'errors': errors, 'pass': not errors,
            'support_height': stack['support_height'],
            'scope': 'Common assembled XY, independent per-board supply aliases and explicit base NCs; no cross-board net-name equality assumption.'}


def functional_layout_specs(xml_path):
    """Return pad-level relationships from the existing circuit, never a placement rule."""
    parts, nets, pins, nc = read_xml(xml_path)
    links = []

    def add(group, purpose, a, b):
        aa, bb = tuple(a.split('.')), tuple(b.split('.'))
        assert aa in pins and bb in pins, (a, b, 'functional layout pin absent')
        assert pins[aa] == pins[bb], (a, b, 'functional layout net differs')
        links.append({'group': group, 'purpose': purpose, 'from': a, 'to': b,
                      'XML_net': pins[aa]})

    for phase, driver, high, low, rg_hi, rg_lo, boot, bypass, ina, shunt, decap in [
        ('U', 'U7', 'Q1', 'Q2', 'R19', 'R20', ('C25','C26'), ('C27','C28'), 'U10', 'RS1', 'C37'),
        ('V', 'U8', 'Q3', 'Q4', 'R25', 'R26', ('C29','C30'), ('C31','C32'), 'U11', 'RS2', 'C38'),
        ('W', 'U9', 'Q5', 'Q6', 'R31', 'R32', ('C33','C34'), ('C35','C36'), 'U12', 'RS3', 'C39'),
    ]:
        group = phase + '_bridge'
        add(group, 'HO to high-side gate resistor input', driver+'.7', rg_hi+'.1')
        add(group, 'high-side resistor output to MOS gate', rg_hi+'.2', high+'.4')
        add(group, 'LO to low-side gate resistor input', driver+'.4', rg_lo+'.1')
        add(group, 'low-side resistor output to MOS gate', rg_lo+'.2', low+'.4')
        for source in (1,2,3):
            add(group, 'high-side VS return to source toe', driver+'.6', high+'.'+str(source))
            add(group, 'low-side COM return to source toe', driver+'.3', low+'.'+str(source))
            add(group, 'low-side power source to shunt hot terminal', low+'.'+str(source), shunt+'.1')
        add(group, 'COM return to shunt hot terminal', driver+'.3', shunt+'.1')
        for cap in boot:
            add(group, 'bootstrap cap positive to VB', cap+'.1', driver+'.8')
            add(group, 'bootstrap cap return to VS', cap+'.2', driver+'.6')
        for cap in bypass:
            add(group, 'VCC bypass positive', cap+'.1', driver+'.5')
            add(group, 'VCC bypass return to local COM', cap+'.2', driver+'.3')
        add(group, 'INA positive Kelvin takeoff', ina+'.8', shunt+'.1')
        add(group, 'INA negative Kelvin takeoff', ina+'.1', shunt+'.2')
        add(group, 'INA local decoupling positive', decap+'.1', ina+'.6')
        add(group, 'INA local decoupling return', decap+'.2', ina+'.2')

    for cap in ('C3','C6','C7'):
        add('U2_L1_12V', 'input capacitor to VINP', cap+'.1', 'U2.4')
        add('U2_L1_12V', 'input capacitor power return', cap+'.2', 'U2.1')
    add('U2_L1_12V', 'switch node L1 to inductor end', 'U2.2', 'L1.1')
    add('U2_L1_12V', 'switch node L2 to inductor end', 'U2.20', 'L1.2')
    for cap, bst, sw in [('C4','3','2'), ('C5','19','20')]:
        add('U2_L1_12V', 'bootstrap capacitor positive', cap+'.1', 'U2.'+bst)
        add('U2_L1_12V', 'bootstrap capacitor switch return', cap+'.2', 'U2.'+sw)
    for cap in ('C8','C9'):
        add('U2_L1_12V', 'output capacitor positive to VOUT', cap+'.1', 'U2.17')
        add('U2_L1_12V', 'output capacitor power return', cap+'.2', 'U2.21')
        add('U2_L1_12V', 'quiet output sense to output capacitor', 'U2.16', cap+'.1')
    add('U2_L1_12V', 'internal VREG local bypass', 'C10.1', 'U2.12')
    add('U2_L1_12V', 'internal VREG bypass ground', 'C10.2', 'U2.13')
    add('U3_L2_5V', 'input capacitor to VIN', 'C11.1', 'U3.3')
    add('U3_L2_5V', 'input capacitor to local GND', 'C11.2', 'U3.4')
    add('U3_L2_5V', 'switch node to inductor input', 'U3.5', 'L2.1')
    add('U3_L2_5V', 'bootstrap positive to BST', 'C12.1', 'U3.6')
    add('U3_L2_5V', 'bootstrap return to SW', 'C12.2', 'U3.5')
    for cap in ('C13','C14','C15'):
        add('U3_L2_5V', 'inductor output to output capacitor', 'L2.2', cap+'.1')
        add('U3_L2_5V', 'output capacitor return to local GND', cap+'.2', 'U3.4')
        add('U3_L2_5V', 'quiet FB sense to output capacitor', 'U3.1', cap+'.1')
    return {'links': links, 'component_values': {ref: part.findtext('value') for ref, part in parts.items()
            if ref in {node.split('.')[0] for link in links for node in (link['from'],link['to'])}},
            'scope': 'Net-verified circuit relationships only; no common distance pass/fail threshold.'}


def functional_layout_check(board, xml_path):
    """Measure saved-pad coordinates; distances are lower bounds, not route qualification."""
    spec = functional_layout_specs(xml_path)
    pads = defaultdict(list)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNumber():
                pads[fp.GetReference()+'.'+pad.GetNumber()].append(pad)
    net_copper = defaultdict(lambda: {'track_length_mm': 0.0, 'segments': 0, 'vias': 0, 'layers': set()})
    for item in board.GetTracks():
        row = net_copper[item.GetNetname()]
        if item.GetClass() == 'PCB_VIA':
            row['vias'] += 1
        else:
            row['segments'] += 1
            row['track_length_mm'] += p.ToMM(item.GetLength())
            row['layers'].add(item.GetLayerName())
    rows = []
    for link in spec['links']:
        assert link['from'] in pads and link['to'] in pads, link
        distances = [(math.dist(xy(a), xy(b)), a, b)
                     for a in pads[link['from']] for b in pads[link['to']]]
        distance, a, b = min(distances, key=lambda row: row[0])
        copper = net_copper.get(link['XML_net'], {})
        rows.append(link | {'from_XY_mm': xy(a), 'to_XY_mm': xy(b),
                            'pad_center_distance_mm': round(distance, 4),
                            'from_footprint_layer': a.GetParentFootprint().GetLayerName(),
                            'to_footprint_layer': b.GetParentFootprint().GetLayerName(),
                            'whole_net_explicit_copper': {
                                'track_length_mm': round(copper.get('track_length_mm',0), 4),
                                'segments': copper.get('segments',0), 'vias': copper.get('vias',0),
                                'layers': sorted(copper.get('layers',set()))}})
    return {'relationships': rows, 'component_values': spec['component_values'],
            'interpretation': 'Center-to-center distance is a geometric lower bound. Whole-net copper length is not a two-pad route length; GND totals include unrelated circuits. Separate Kelvin takeoffs, local return loops, switch-node exposure and real routed copper require manual review.',
            'distance_threshold_used': None}


def native_drc(path, role, run):
    output = OUTPUT / (role + '_drc.json')
    if not run:
        return {'run': False, 'note': 'Skipped explicitly; no stale DRC report reused.'}
    if output.exists():
        output.unlink()  # Never attach an old report if this CLI invocation fails.
    command = [str(CLI), 'pcb', 'drc', '--format', 'json', '--severity-all', '--all-track-errors',
               '--schematic-parity', '--output', str(output), str(path)]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if not output.is_file():
        return {'run': True, 'error': 'DRC did not produce JSON', 'exit_code': result.returncode,
                'stdout': result.stdout, 'stderr': result.stderr}
    data = json.loads(output.read_text(encoding='utf-8-sig'))
    report = {'run': True, 'exit_code': result.returncode, 'path': str(output.relative_to(REPO)),
              'sha256': sha(output), 'board_sha256': sha(path), 'date': data.get('date'),
              'kicad_version': data.get('kicad_version'), 'stdout': result.stdout, 'stderr': result.stderr}
    for key in ('violations', 'unconnected_items', 'schematic_parity'):
        items = data.get(key, [])
        report[key] = {'count': len(items), 'types': dict(Counter(item.get('type', 'unknown') for item in items)),
                        'severities': dict(Counter(item.get('severity', 'unknown') for item in items))}
    parity = data.get('schematic_parity', [])
    filter_metadata = [item for item in parity
                       if item.get('type') == 'footprint_symbol_field_mismatch'
                       and 'ki_fp_filters' in item.get('description', '')]
    report['schematic_parity_classification'] = {
        'ki_fp_filters_metadata_items': len(filter_metadata),
        'other_items': len(parity)-len(filter_metadata),
        'note': 'Classification only; all native findings remain counted and retained. Exact FPID/value/pad/net is checked independently.'}
    return report


def main():
    global OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller', type=Path, default=REPO/'controller/hardware/g431_core/controller.kicad_pcb')
    parser.add_argument('--inverter', type=Path, default=REPO/'inverter/hardware/inverter.kicad_pcb')
    parser.add_argument('--skip-drc', action='store_true')
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args = parser.parse_args()
    OUTPUT=args.output.resolve()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stack_path = REPO/'docs/pcb_stack_contract_rev_e.json'
    electrical_path = REPO/'docs/daughterboard_pin_contract.json'
    stack = json.loads(stack_path.read_text(encoding='utf-8'))
    electrical = json.loads(electrical_path.read_text(encoding='utf-8'))
    boards, refs, pins, records = {}, {}, {}, {}
    all_watched = [args.controller, args.inverter, stack_path, electrical_path]
    for role, directory in [('controller', REPO/'controller/hardware/g431_core'), ('inverter', REPO/'inverter/hardware')]:
        path, xml = getattr(args, role).resolve(), directory/'review'/(role+'.net.xml')
        assert path.is_file() and xml.is_file(), ('PCB/XML missing', path, xml)
        all_watched += [xml, path.with_suffix('.kicad_pro')]
    all_watched = [path for path in all_watched if path.is_file()]
    before = {str(path): sha(path) for path in all_watched}
    for role, directory in [('controller', REPO/'controller/hardware/g431_core'), ('inverter', REPO/'inverter/hardware')]:
        path, xml = getattr(args, role).resolve(), directory/'review'/(role+'.net.xml')
        boards[role], refs[role], records[role], pins[role] = physical_check(role, path, xml, stack)
        if role == 'inverter':
            records[role]['functional_layout'] = functional_layout_check(boards[role], xml)
        records[role]['DRC'] = native_drc(path, role, not args.skip_drc)
        drc = records[role]['DRC']
        records[role]['routing']['complete'] = bool(drc.get('run') and not drc.get('error')
            and drc['unconnected_items']['count'] == 0
            and records[role]['routing']['raw_pcbnew_unconnected'] == 0)
    mating = stack_check(boards, refs, pins, electrical, stack)
    unchanged = {path: digest == sha(Path(path)) for path, digest in before.items()}
    assert all(unchanged.values()), ('checker input changed during review', unchanged)
    mapping = all(record['mapping_pass'] for record in records.values()) and mating['pass']
    errors = sum(len(record['errors']) for record in records.values()) + len(mating['errors'])
    findings = any(record['warnings'] or record['DRC'].get('error') or not record['routing']['complete']
                   or any(record['DRC'].get(key, {}).get('count', 0) for key in
                          ('violations', 'unconnected_items', 'schematic_parity')) for record in records.values())
    report = {'date': datetime.now(timezone.utc).isoformat(), 'revision': stack['revision'],
              'pcbnew_version': p.GetBuildVersion(),
              'status': 'FAIL_MAPPING_OR_GEOMETRY' if errors else 'REVIEW_WITH_FINDINGS' if findings else 'PASS_REVIEW',
              'mapping_pass': mapping, 'boards': records, 'mating': mating,
              'input_sha256': before, 'input_files_unchanged': unchanged,
              'scope': 'Saved PCB vs current XML, 64-pin mating, native geometry, model path resolution and actual CLI DRC. No board/project saved.',
              'mechanical_limit': 'Button access and standoff length still require assembled insertion/height checks.',
              'manufacturing_release': False}
    (OUTPUT/'system_check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (OUTPUT/'functional_layout_distances.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['group','purpose','from','to','XML_net',
            'from_XY_mm','to_XY_mm','pad_center_distance_mm','from_footprint_layer','to_footprint_layer',
            'whole_net_explicit_copper'])
        writer.writeheader()
        writer.writerows(records['inverter']['functional_layout']['relationships'])
    summary = {role: {'references': record['mapping']['counts']['references'],
                     'pins': record['mapping']['counts']['pins'], 'mapping_pass': record['mapping_pass'],
                     'errors': len(record['errors']), 'warnings': len(record['warnings']),
                     'DRC': {key: record['DRC'].get(key, {}).get('count') for key in
                             ('violations', 'unconnected_items', 'schematic_parity')},
                     'raw_unconnected': record['routing']['raw_pcbnew_unconnected']}
               for role, record in records.items()}
    text = json.dumps({'status': report['status'], 'mapping_pass': mapping, 'mating_pass': mating['pass'],
                       'contacts': mating['contacts'], 'boards': summary}, ensure_ascii=False, indent=2)
    (OUTPUT/'system_check.txt').write_text(text+'\n', encoding='utf-8')
    print(text)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

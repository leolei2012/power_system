"""Read-only Kelvin protection audit against the immutable Rev E power seed.

Run with KiCad bundled Python. Only the requested JSON report is written;
neither PCB nor project is saved. The baseline remains the 277-track/98-via
power checkpoint even after a routed candidate is promoted to canonical.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import sys

import pcbnew as p


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'inverter/hardware/review/pcb_rev_e_2026-11-11'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def position(item):
    point = item.GetPosition()
    return [round(p.ToMM(point.x), 6), round(p.ToMM(point.y), 6)]


def signature(item):
    value = (item.GetClass(), item.GetNetname(), item.GetLayer(),
             item.GetStart().x, item.GetStart().y, item.GetEnd().x, item.GetEnd().y,
             item.IsLocked())
    if item.GetClass() == 'PCB_VIA':
        via = p.Cast_to_PCB_VIA(item)
        return value + (via.GetWidth(p.F_Cu), via.GetDrillValue(),
                        tuple(via.GetLayerSet().Seq()), via.GetRemoveUnconnected(),
                        via.GetKeepStartEnd())
    return value + (item.GetWidth(),)


def shape(item, layer):
    # An outer via disk on all spanned layers is conservative for barrel and
    # annular-ring protection, including unflashed internal annular rings.
    return item.GetEffectiveShape(p.F_Cu if item.GetClass() == 'PCB_VIA' else layer)


def polygon(item, layer, clearance=0):
    result = p.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(result, p.F_Cu if item.GetClass() == 'PCB_VIA' else layer,
                                 clearance, 1, p.ERROR_OUTSIDE)
    return result


def confined_to_star(item, protected, star, layer, clearance):
    if star is None or not star.IsOnLayer(layer):
        return False
    region = p.SHAPE_POLY_SET()
    region.BooleanIntersection(polygon(item, layer, clearance), polygon(protected, layer))
    if not region.OutlineCount():
        return False
    outside = p.SHAPE_POLY_SET()
    outside.BooleanSubtract(region, polygon(star, layer, clearance))
    return abs(outside.Area()) <= 1  # At most one square internal unit.


def gap_mm(a, b, maximum):
    if a.Collide(b, 0):
        return 0.0
    lower, upper = 0, maximum
    while upper-lower > 1:
        middle = (lower+upper)//2
        if a.Collide(b, middle):
            upper = middle
        else:
            lower = middle
    return round(p.ToMM(upper), 6)


def verify(args):
    source_before = sha(args.source)
    baseline_before = sha(args.baseline)
    metadata_before = sha(args.metadata)
    board = p.LoadBoard(str(args.source))
    baseline = p.LoadBoard(str(args.baseline))
    metadata = json.loads(args.metadata.read_text(encoding='utf-8'))
    items = {item.m_Uuid.AsString(): item for item in board.GetTracks()}
    original = {item.m_Uuid.AsString(): item for item in baseline.GetTracks()}
    locked = {uid: item for uid, item in original.items() if item.IsLocked()}
    footprints = {fp.GetReference(): fp for fp in board.GetFootprints()}
    layers = list(board.GetEnabledLayers().CuStack())
    locked_tracks = sum(item.GetClass() != 'PCB_VIA' for item in locked.values())
    locked_vias = len(locked)-locked_tracks
    errors = []
    if (locked_tracks, locked_vias) != (277, 98):
        errors.append({'check': 'baseline_locked_count', 'tracks': locked_tracks, 'vias': locked_vias})
    changed = [uid for uid, item in locked.items()
               if uid not in items or signature(item) != signature(items[uid])]
    if changed:
        errors.append({'check': 'baseline_locked_geometry', 'UUIDs': changed})
    if args.expected_sha256 and args.expected_sha256.lower() != source_before:
        errors.append({'check': 'expected_source_SHA256', 'expected': args.expected_sha256,
                       'actual': source_before})

    protected = []
    for phase in metadata['kelvin']:
        for sign in ('positive', 'negative'):
            number = '1' if sign == 'positive' else '2'
            star = next(pad for pad in footprints[phase['RS']].Pads() if pad.GetNumber() == number)
            for uid in phase[sign+'_track_uuids'] + [phase[sign+'_via_uuid']]:
                if uid not in items:
                    errors.append({'check': 'protected_object_missing', 'UUID': uid})
                    continue
                protected.append((phase['phase'], sign, uid, items[uid], star))
        for number, sign in [('1', 'negative_INA_pad'), ('8', 'positive_INA_pad')]:
            pad = next(pad for pad in footprints[phase['INA']].Pads() if pad.GetNumber() == number)
            protected.append((phase['phase'], sign, phase['INA']+'.'+number, pad, None))
    protected_ids = {uid for _, kind, uid, _, _ in protected if not kind.endswith('INA_pad')}
    if protected_ids != set(metadata['protected_kelvin_uuids']):
        errors.append({'check': 'protected_object_set'})

    new = {uid: item for uid, item in items.items() if uid not in original}
    contacts, under_guard, star_exceptions = [], [], []
    guard = p.FromMM(args.minimum_clearance_mm)
    probe = max(0, guard-1)  # Exactly the requested separation is acceptable.
    for uid, item in new.items():
        for phase, kind, protected_id, other, star in protected:
            if item.GetNetname() != other.GetNetname():
                continue
            for layer in layers:
                if not item.IsOnLayer(layer) or not other.IsOnLayer(layer):
                    continue
                a, b = shape(item, layer), shape(other, layer)
                if not a.Collide(b, probe):
                    continue
                exact = bool(a.Collide(b, 0))
                row = {'new_UUID': uid, 'new_kind': item.GetClass(), 'net': item.GetNetname(),
                       'phase': phase, 'protected_kind': kind, 'protected_id': protected_id,
                       'layer': board.GetLayerName(layer), 'new_start_mm': position(item),
                       'new_end_mm': [round(p.ToMM(item.GetEnd().x),6), round(p.ToMM(item.GetEnd().y),6)],
                       'gap_mm': gap_mm(a, b, guard), 'contact': exact}
                if exact and not confined_to_star(item, other, star, layer, 0):
                    contacts.append(row)
                elif confined_to_star(item, other, star, layer, guard):
                    star_exceptions.append(row)
                else:
                    under_guard.append(row)

    # Zones are physical copper too. Check every actually filled matching-net
    # zone on the layers where protected copper exists, rather than trusting
    # the zone outline or an unfilled cache.
    zone_contacts, zone_near, filled_zones = [], [], []
    for raw in board.Zones():
        zone = p.Cast_to_ZONE(raw)
        if zone.GetIsRuleArea():
            continue
        for layer in layers:
            if not zone.HasFilledPolysForLayer(layer):
                continue
            filled = zone.GetFilledPolysList(layer)
            filled_zones.append({'UUID': zone.m_Uuid.AsString(), 'net': zone.GetNetname(),
                                 'layer': board.GetLayerName(layer), 'filled': bool(zone.IsFilled())})
            for phase, kind, protected_id, other, star in protected:
                if zone.GetNetname() != other.GetNetname() or not other.IsOnLayer(layer):
                    continue
                copper = shape(other, layer)
                if copper.Collide(filled, probe):
                    row = {'zone_UUID': zone.m_Uuid.AsString(), 'phase': phase,
                           'protected_kind': kind, 'protected_id': protected_id,
                           'layer': board.GetLayerName(layer), 'gap_mm': gap_mm(copper, filled, guard)}
                    (zone_contacts if copper.Collide(filled,0) else zone_near).append(row)

    negative_planes = []
    for phase in metadata['kelvin']:
        uid = phase['negative_via_uuid']
        if uid not in items:
            continue
        via = items[uid]
        for layer in layers:
            if layer in (p.F_Cu, p.B_Cu):
                continue
            available = [row for row in filled_zones if row['net'] == 'GND'
                         and row['layer'] == board.GetLayerName(layer) and row['filled']]
            hits = [row for row in zone_contacts if row['protected_id'] == uid
                    and row['layer'] == board.GetLayerName(layer)]
            negative_planes.append({'phase': phase['phase'], 'via_UUID': uid,
                                    'layer': board.GetLayerName(layer),
                                    'filled_GND_zone_count': len(available), 'isolated': not hits})
            if layer in (p.In1_Cu, p.In4_Cu) and not available:
                errors.append({'check': 'expected_filled_GND_plane_unavailable',
                               'phase': phase['phase'], 'layer': board.GetLayerName(layer)})

    source_after, baseline_after, metadata_after = sha(args.source), sha(args.baseline), sha(args.metadata)
    unchanged = (source_before == source_after and baseline_before == baseline_after
                 and metadata_before == metadata_after)
    if not unchanged:
        errors.append({'check': 'inputs_changed_during_review'})
    passed = not (errors or contacts or under_guard or zone_contacts or zone_near)
    return {'pass': passed, 'date_UTC': datetime.now(timezone.utc).isoformat(),
            'source': str(args.source), 'source_sha256_before': source_before,
            'source_sha256_after': source_after, 'source_unchanged': source_before == source_after,
            'baseline': str(args.baseline), 'baseline_sha256_before': baseline_before,
            'baseline_sha256_after': baseline_after, 'metadata': str(args.metadata),
            'metadata_sha256_before': metadata_before, 'metadata_sha256_after': metadata_after,
            'all_inputs_unchanged': unchanged, 'checker_sha256': sha(Path(__file__)),
            'pcbnew_version': p.GetBuildVersion(), 'minimum_same_net_clearance_mm': args.minimum_clearance_mm,
            'canonical_locked_tracks': locked_tracks, 'canonical_locked_vias': locked_vias,
            'canonical_locked_changed_UUIDs': changed, 'protected_tracks_vias': len(protected_ids),
            'INA_input_pads': sum(kind.endswith('INA_pad') for _,kind,_,_,_ in protected),
            'new_nonbaseline_tracks_vias_checked': len(new), 'errors': errors,
            'same_net_contacts_outside_actual_RS_star': contacts,
            'same_net_clearance_below_minimum': under_guard,
            'RS_star_region_exceptions': star_exceptions,
            'same_net_filled_zone_contacts': zone_contacts,
            'same_net_filled_zone_clearance_below_minimum': zone_near,
            'filled_zone_availability': filled_zones,
            'negative_via_actual_inner_plane_isolation': negative_planes,
            'method': 'All nonbaseline tracks/vias and actual same-net filled-zone polygons vs 30 protected Kelvin objects and six INA1/8 pads, on every common copper layer. Native copper shapes; conservative via outer disks. RS exceptions require the complete contact/proximity polygon to remain within the corresponding actual shunt pad (expanded only for the proximity margin).',
            'read_only': True, 'scope': 'Kelvin topology/clearance and immutable power copper audit; no PCB saved, no routing completeness or fabrication release claim.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path,
        default=REVIEW/'aux_bb_final/vreg_tp_finish.work/inverter.kicad_pcb')
    parser.add_argument('--baseline', type=Path, default=REVIEW/'power/inverter.kicad_pcb')
    parser.add_argument('--metadata', type=Path, default=REVIEW/'power/power_copper.json')
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/pcb_review_2026-11-11/final_kelvin_review.json')
    parser.add_argument('--expected-sha256')
    parser.add_argument('--minimum-clearance-mm', type=float, default=.25)
    args = parser.parse_args()
    for field in ('source','baseline','metadata','output'):
        setattr(args, field, getattr(args, field).resolve())
    report = verify(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'pass': report['pass'], 'locked_tracks': report['canonical_locked_tracks'],
        'locked_vias': report['canonical_locked_vias'], 'new_items': report['new_nonbaseline_tracks_vias_checked'],
        'contacts': len(report['same_net_contacts_outside_actual_RS_star']),
        'clearance_findings': len(report['same_net_clearance_below_minimum']),
        'zone_contacts': len(report['same_net_filled_zone_contacts']),
        'zone_clearance_findings': len(report['same_net_filled_zone_clearance_below_minimum']),
        'source_sha256_after': report['source_sha256_after'], 'errors': report['errors']}, ensure_ascii=False))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())

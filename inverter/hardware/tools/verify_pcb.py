"""Independently check the saved PCB against the actual KiCad XML netlist.

Run with KiCad's bundled Python, for example:
  & 'C:/Program Files/KiCad/10.0/bin/python.exe' tools/verify_pcb.py

This checker does not import the PCB builder or use its placement objects.
It reads the board back through pcbnew and writes pcb_check.json / .txt.
An unrouted placement can pass physical mapping while remaining explicitly
incomplete.  KiCad DRC is a separate check; an existing pcb_drc.json is summarized.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

try:
    import pcbnew as pcb
except ImportError:
    raise SystemExit("Use KiCad bundled Python: C:/Program Files/KiCad/10.0/bin/python.exe")


BASE = Path(__file__).resolve().parents[1]
IU_MM = pcb.FromMM(1)


def mm(value):
    return round(float(value) / IU_MM, 6)


def mm2(value):
    return round(float(value) / (IU_MM * IU_MM), 8)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def natural(value):
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value)]


def bbox_data(box):
    return {
        "x": mm(box.GetX()), "y": mm(box.GetY()),
        "width": mm(box.GetWidth()), "height": mm(box.GetHeight()),
        "right": mm(box.GetX() + box.GetWidth()),
        "bottom": mm(box.GetY() + box.GetHeight()),
    }


def xml_dnp(component):
    return any(prop.attrib.get("name", "").lower() == "dnp"
               and prop.attrib.get("value", "yes").lower() not in {"no", "false", "0"}
               for prop in component.findall("property"))


def is_nc(name, group):
    return bool(name and name.rsplit("/", 1)[-1].startswith("unconnected-") and len(group) == 1)


def read_contract(path):
    root = ET.parse(path).getroot()
    components = {node.attrib["ref"]: node for node in root.findall("./components/comp")}
    library_pins = {}
    for part in root.findall("./libparts/libpart"):
        library_pins[(part.attrib["lib"], part.attrib["part"])] = {
            pin.attrib["num"] for pin in part.findall("./pins/pin")
        }
    pin_nets, groups = {}, {}
    for net in root.findall("./nets/net"):
        name = net.attrib["name"]
        if name in groups:
            raise ValueError("Duplicate complete XML net name: " + name)
        groups[name] = {(node.attrib["ref"], node.attrib["pin"]) for node in net.findall("node")}
        for key in groups[name]:
            if key in pin_nets:
                raise ValueError("XML pin is assigned to multiple nets: " + repr(key))
            pin_nets[key] = name
    pins = {}
    for ref, component in components.items():
        source = component.find("libsource")
        libkey = (source.attrib["lib"], source.attrib["part"]) if source is not None else None
        pins[ref] = set(library_pins.get(libkey, ()))
        pins[ref].update(pin.attrib["num"] for pin in component.findall("./units/unit/pins/pin"))
        pins[ref].update(pin for (r, pin) in pin_nets if r == ref)
        if not pins[ref]:
            raise ValueError("No physical symbol pins found in XML for " + ref)
    return components, pins, pin_nets, groups


def mechanical_hole(footprint, expected_refs):
    ref = str(footprint.GetReference())
    if ref in expected_refs:
        return False
    pads = list(footprint.Pads())
    only_npth = bool(pads) and all(p.GetAttribute() == pcb.PAD_ATTRIB_NPTH for p in pads)
    return only_npth and (str(footprint.GetFPIDAsString()).startswith("MountingHole:")
                          or re.fullmatch(r"H\d+", ref) is not None)


def drc_summary(path):
    if not path.is_file():
        return {"available": False, "path": str(path), "note": "DRC was not run by this checker."}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        summary = {"available": True, "path": str(path), "sha256": sha256(path)}
        summary["date"] = data.get("date")
        for key in ["violations", "unconnected_items", "schematic_parity"]:
            values = data.get(key, [])
            if isinstance(values, list):
                summary[key + "_count"] = len(values)
                summary[key + "_types"] = dict(Counter(v.get("type", "unknown") for v in values))
                summary[key + "_severities"] = dict(Counter(v.get("severity", "unknown") for v in values))
        summary["note"] = "External DRC result; freshness must be checked against this board revision."
        return summary
    except (ValueError, OSError) as exc:
        return {"available": True, "path": str(path), "read_error": str(exc)}


def layout_checks(board, footprints, report, args):
    errors = report["errors"]
    warnings = report["warnings"]
    layers = [{"id": int(layer), "name": board.GetLayerName(layer)}
              for layer in board.GetEnabledLayers().CuStack()]
    report["copper_stack"] = layers
    report["counts"]["copper_layers"] = int(board.GetCopperLayerCount())
    if board.GetCopperLayerCount() != args.expected_copper_layers:
        errors.append({"check": "copper_layer_count", "expected": args.expected_copper_layers,
                       "actual": int(board.GetCopperLayerCount())})

    edge_drawings = [item for item in board.GetDrawings() if item.GetLayer() == pcb.Edge_Cuts]
    outline = pcb.SHAPE_POLY_SET()
    outline_ok = bool(board.GetBoardPolygonOutlines(outline, False, None, False, False))
    contour_count = int(outline.OutlineCount())
    report["outline"] = {
        "closed_valid_outline": outline_ok, "outer_contour_count": contour_count,
        "expected_outer_contour_count": args.expected_outer_contours,
        "edge_cuts_drawing_count": len(edge_drawings),
        "edge_cuts_item_types": dict(Counter(item.GetClass() for item in edge_drawings)),
        "area_mm2": mm2(outline.Area()) if outline_ok else None,
        "bbox_mm": bbox_data(board.GetBoardEdgesBoundingBox()),
        "npth_included_as_board_cutouts": False,
    }
    if outline_ok:
        outline_box=outline.BBox()
        dimensions=[mm(outline_box.GetWidth()),mm(outline_box.GetHeight())]
        report['outline']['centerline_dimensions_mm']=dimensions
        for expected,actual,axis in [(args.expected_width_mm,dimensions[0],'width'),(args.expected_height_mm,dimensions[1],'height')]:
            if expected is not None and abs(actual-expected)>.005:
                errors.append({'check':'expected_board_dimension','axis':axis,'expected_mm':expected,'actual_mm':actual})
    if not outline_ok or contour_count != args.expected_outer_contours or not edge_drawings:
        errors.append({"check": "closed_board_outline", "valid": outline_ok,
                       "outer_contours": contour_count, "edge_cuts_items": len(edge_drawings)})

    expected_refs = set(report["expected_references"])
    mounting = [fp for fp in footprints if mechanical_hole(fp, expected_refs)]
    hole_pads = [p for fp in mounting for p in fp.Pads() if p.GetAttribute() == pcb.PAD_ATTRIB_NPTH]
    all_npth = [p for fp in footprints for p in fp.Pads() if p.GetAttribute() == pcb.PAD_ATTRIB_NPTH]
    report["counts"].update({"mounting_hole_footprints": len(mounting),
                             "mounting_hole_npth_pads": len(hole_pads), "all_npth_pads": len(all_npth)})
    report["mounting_holes"] = [
        {"reference": fp.GetReference(), "footprint": fp.GetFPIDAsString(),
         "position_mm": [mm(fp.GetPosition().x), mm(fp.GetPosition().y)],
         "npth_drills_mm": [[mm(p.GetDrillSize().x), mm(p.GetDrillSize().y)]
                            for p in fp.Pads() if p.GetAttribute() == pcb.PAD_ATTRIB_NPTH]}
        for fp in mounting
    ]
    if len(mounting) != args.expected_mounting_holes or len(hole_pads) != args.expected_mounting_holes:
        errors.append({"check": "mounting_hole_count", "expected": args.expected_mounting_holes,
                       "footprints": len(mounting), "npth_pads": len(hole_pads)})

    bounds = board.GetBoardEdgesBoundingBox()
    bx0, by0 = bounds.GetX(), bounds.GetY()
    bx1, by1 = bx0 + bounds.GetWidth(), by0 + bounds.GetHeight()
    tolerance = pcb.FromMM(args.boundary_tolerance_mm)
    outside = []
    for fp in footprints:
        box = fp.GetBoundingBox(False, False)
        x0, y0 = box.GetX(), box.GetY()
        x1, y1 = x0 + box.GetWidth(), y0 + box.GetHeight()
        exceeds_bbox = x0 < bx0-tolerance or y0 < by0-tolerance or x1 > bx1+tolerance or y1 > by1+tolerance
        samples = [(x0, y0), (x1, y0), (x1, y1), (x0, y1),
                   ((x0+x1)//2, y0), (x1, (y0+y1)//2), ((x0+x1)//2, y1), (x0, (y0+y1)//2)]
        outside_outline = outline_ok and any(not outline.Contains(pcb.VECTOR2I(x, y), -1, tolerance)
                                             for x, y in samples)
        if exceeds_bbox or outside_outline:
            outside.append({"reference": fp.GetReference(), "bbox_mm": bbox_data(box),
                            "exceeds_edge_bbox": bool(exceeds_bbox),
                            "bbox_samples_outside_outline": bool(outside_outline)})
    report["footprint_bounds"] = {
        "method": "pcbnew footprint bbox excluding text, compared with Edge.Cuts bbox and 8 outline sample points",
        "tolerance_mm": args.boundary_tolerance_mm, "out_of_bounds": outside,
    }
    if outside:
        warnings.append({"check": "footprint_bbox_outside_board", "count": len(outside),
                         "note": "Includes component graphics/courtyard; intentional connector overhang still needs review."})

    courtyards, missing, malformed = [], [], []
    for fp in footprints:
        try:
            fp.BuildCourtyardCaches()
            found = False
            for layer in [pcb.F_CrtYd, pcb.B_CrtYd]:
                shape = fp.GetCourtyard(layer)
                if shape.OutlineCount() and shape.Area() > 0:
                    found = True
                    courtyards.append((fp.GetReference(), layer, shape, shape.BBox(), float(shape.Area())))
            if not found:
                missing.append(fp.GetReference())
        except Exception as exc:
            malformed.append({"reference": fp.GetReference(), "error": str(exc)})
    collisions = []
    for index, (refa, layera, shapea, boxa, areaa) in enumerate(courtyards):
        for refb, layerb, shapeb, boxb, areab in courtyards[index+1:]:
            if refa == refb or layera != layerb or not boxa.Intersects(boxb):
                continue
            overlap = pcb.SHAPE_POLY_SET()
            overlap.BooleanIntersection(shapea, shapeb)
            area = float(overlap.Area())
            area_mm2 = mm2(area)
            if area_mm2 <= 0.0001:
                continue
            ratio = area / min(areaa, areab)
            severe = area_mm2 >= args.severe_overlap_area_mm2 and ratio >= args.severe_overlap_ratio
            collisions.append({"references": [refa, refb], "layer": board.GetLayerName(layera),
                               "overlap_area_mm2": area_mm2, "fraction_of_smaller_courtyard": round(ratio, 6),
                               "severe": severe})
    serious = [item for item in collisions if item["severe"]]
    report["courtyard"] = {
        "method": "pcbnew cached native same-side courtyard polygon Boolean intersections",
        "severe_threshold_area_mm2": args.severe_overlap_area_mm2,
        "severe_threshold_fraction_of_smaller": args.severe_overlap_ratio,
        "missing": sorted(missing, key=natural), "malformed": malformed,
        "overlap_count": len(collisions), "severe_overlap_count": len(serious), "overlaps": collisions,
    }
    if collisions:
        warnings.append({"check": "courtyard_overlaps", "count": len(collisions), "severe": len(serious)})
    if missing or malformed:
        warnings.append({"check": "courtyard_check_incomplete", "missing": len(missing), "malformed": len(malformed)})
    report["layout_geometry_pass"] = not (outside or serious or malformed)
    if args.strict_layout and not report["layout_geometry_pass"]:
        errors.append({"check": "strict_layout", "out_of_bounds": len(outside),
                       "severe_courtyard_overlaps": len(serious), "malformed_courtyards": len(malformed)})


def connectivity_checks(board, pads, expected_pin_nets, expected_groups, report):
    tracks = list(board.GetTracks())
    # KiCad 10 may expose container entries through an opaque SWIG base.  Cast
    # explicitly and use the current GetIsRuleArea API (not IsRuleArea).
    zones = [pcb.Cast_to_ZONE(zone) for zone in board.Zones()]
    track_count = sum(item.GetClass() != "PCB_VIA" for item in tracks)
    via_count = sum(item.GetClass() == "PCB_VIA" for item in tracks)
    report["counts"].update({"tracks_and_arcs": track_count, "vias": via_count, "zones": len(zones),
                             "copper_zones": sum(not z.GetIsRuleArea() for z in zones),
                             "rule_areas": sum(z.GetIsRuleArea() for z in zones)})
    report["track_classes"] = dict(Counter(item.GetClass() for item in tracks))
    non_ground_reference_tracks = [
        {"uuid": item.m_Uuid.AsString(), "net": item.GetNetname()}
        for item in tracks
        if item.GetClass() != "PCB_VIA" and item.GetLayer() == pcb.In1_Cu
        and item.GetNetname() != "GND"
    ]
    report["reference_plane"] = {"layer": "In1.Cu", "required_net": "GND",
                                  "non_ground_tracks": non_ground_reference_tracks}
    if non_ground_reference_tracks:
        report["errors"].append({"check": "non_ground_reference_layer_tracks",
                                  "count": len(non_ground_reference_tracks)})
    if board.GetCopperLayerCount()==6:
        bad=[{'uuid':item.m_Uuid.AsString(),'net':item.GetNetname()} for item in tracks
             if item.GetClass()!='PCB_VIA' and item.GetLayer()==pcb.In4_Cu and item.GetNetname()!='GND']
        report['additional_reference_planes']=[{'layer':'In4.Cu','non_ground_tracks':bad}]
        if bad:report['errors'].append({'check':'non_ground_In4_reference_layer_tracks','count':len(bad)})
    report["track_widths_mm"] = dict(Counter(str(mm(item.GetWidth())) for item in tracks
                                           if item.GetClass() != "PCB_VIA"))
    report["zones"] = [{"net": str(zone.GetNetname()), "net_code": int(zone.GetNetCode()),
                         "layer": board.GetLayerName(zone.GetLayer()), "rule_area": bool(zone.GetIsRuleArea()),
                         "filled": bool(zone.IsFilled()) if hasattr(zone, "IsFilled") else None}
                        for zone in zones]
    connectivity = {"available": False, "unconnected_count": None,
                    "cross_net_contacts": [], "physical_contact_check_available": False,
                    "count_source": "Raw pcbnew GetUnconnectedCount(False); reported independently from CLI DRC unconnected_items."}
    try:
        board.BuildConnectivity()
        connection = board.GetConnectivity()
        connectivity["available"] = True
        connectivity["unconnected_count"] = int(connection.GetUnconnectedCount(False))
        contacts = set()
        failures = []
        for ref, number, pad in pads:
            expected = expected_pin_nets.get((ref, number))
            if expected is None or is_nc(expected, expected_groups.get(expected, ())):
                continue
            try:
                for other in connection.GetConnectedItems(pad, pcb.IGNORE_NETS):
                    other_net = str(other.GetNetname())
                    if other.GetNetCode() and pad.GetNetCode() and other_net != str(pad.GetNetname()):
                        contacts.add(tuple(sorted((str(pad.GetNetname()), other_net))))
            except Exception as exc:
                failures.append(str(exc))
                break
        connectivity["cross_net_contacts"] = [list(pair) for pair in sorted(contacts)]
        connectivity["physical_contact_check_available"] = not failures
        if failures:
            connectivity["physical_contact_check_error"] = failures[0]
        if contacts:
            report["errors"].append({"check": "pcbnew_cross_net_copper_contact", "net_pairs": connectivity["cross_net_contacts"]})
    except Exception as exc:
        connectivity["error"] = str(exc)
        report["warnings"].append({"check": "connectivity_api_unavailable", "error": str(exc)})
    report["connectivity"] = connectivity
    external = report.get("external_DRC", {})
    report["routing_complete"] = (connectivity["available"] and connectivity["unconnected_count"] == 0
                                   and external.get("unconnected_items_count") == 0)
    if not report["routing_complete"]:
        report["warnings"].append({"check": "routing_incomplete", "unconnected": connectivity["unconnected_count"],
                                    "note": "A placement review is not a routed or fabrication-ready PCB."})


def verify(args):
    report = {
        "schema_version": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
        "checker": "independent pcbnew readback against actual KiCad XML; no builder imported",
        "pcbnew_version": pcb.Version(), "board": str(args.board), "netlist": str(args.netlist),
        "verification_completed": False, "physical_mapping_pass": False,
        "errors": [], "warnings": [], "counts": {},
    }
    for path, kind in [(args.board, "board"), (args.netlist, "XML netlist"), (args.candidates, "candidate mapping")]:
        if not path.is_file():
            report["status"] = "NOT_RUN"
            report["errors"].append({"check": "input_missing", "kind": kind, "path": str(path)})
    if report["errors"]:
        return report, 2
    report["input_sha256"] = {"board": sha256(args.board), "netlist": sha256(args.netlist),
                               "candidates": sha256(args.candidates)}
    components, expected_pins, pin_nets, groups = read_contract(args.netlist)
    expected_refs = set(components)
    report["expected_references"] = sorted(expected_refs, key=natural)
    report["counts"].update({"expected_physical_references": len(expected_refs),
                             "expected_symbol_pins": sum(map(len, expected_pins.values()))})
    if len(expected_refs) != args.expected_components:
        report["errors"].append({"check": "XML_component_count", "expected": args.expected_components, "actual": len(expected_refs)})

    board = pcb.LoadBoard(str(args.board))
    footprints = list(board.GetFootprints())
    report["footprint_placements"] = {
        fp.GetReference(): {"x_mm": mm(fp.GetPosition().x), "y_mm": mm(fp.GetPosition().y),
                            "rotation_deg": fp.GetOrientationDegrees(),
                            "layer": board.GetLayerName(fp.GetLayer()),
                            "footprint": fp.GetFPIDAsString(), "DNP": bool(fp.IsDNP())}
        for fp in sorted(footprints, key=lambda item: natural(item.GetReference()))
    }
    actual = defaultdict(list)
    for fp in footprints:
        actual[str(fp.GetReference())].append(fp)
    duplicates = {ref: len(items) for ref, items in actual.items() if len(items) != 1}
    missing = sorted(expected_refs-set(actual), key=natural)
    unexpected = sorted(ref for ref in set(actual)-expected_refs
                        if not all(mechanical_hole(fp, expected_refs) for fp in actual[ref]))
    report["reference_check"] = {"missing": missing, "unexpected_non_mechanical": unexpected, "duplicates": duplicates}
    if missing or unexpected or duplicates:
        report["errors"].append({"check": "physical_reference_set", **report["reference_check"]})
    report["counts"].update({"all_board_footprints": len(footprints),
                             "XML_physical_references_present": len(expected_refs & set(actual)),
                             "board_mechanical_only_footprints": sum(mechanical_hole(fp, expected_refs) for fp in footprints)})

    candidates = json.loads(args.candidates.read_text(encoding="utf-8-sig"))
    candidate_map = candidates["footprint_map"]
    if len(candidate_map) != 19:
        report["errors"].append({"check": "candidate_map_count", "expected": 19, "actual": len(candidate_map)})
    mismatches, missing_pads, extra_pads, fp_mismatches, dnp_mismatches, value_mismatches = [], [], [], [], [], []
    duplicate_pad_numbers, pad_records = [], []
    netcode_groups, actual_pin_groups = defaultdict(set), defaultdict(set)
    nc_empty = 0
    for ref in sorted(expected_refs & set(actual), key=natural):
        if len(actual[ref]) != 1:
            continue
        fp = actual[ref][0]
        expected_fp = candidate_map.get(ref) or components[ref].findtext("footprint", "")
        if not expected_fp or str(fp.GetFPIDAsString()) != expected_fp:
            fp_mismatches.append({"reference": ref, "expected": expected_fp, "actual": str(fp.GetFPIDAsString())})
        if bool(fp.IsDNP()) != xml_dnp(components[ref]):
            dnp_mismatches.append({"reference": ref, "expected": xml_dnp(components[ref]), "actual": bool(fp.IsDNP())})
        if str(fp.GetValue()) != components[ref].findtext("value", ""):
            value_mismatches.append({"reference": ref, "expected": components[ref].findtext("value", ""), "actual": str(fp.GetValue())})
        pads = list(fp.Pads())
        numbers = Counter(str(p.GetNumber()) for p in pads if str(p.GetNumber()))
        for number, count in numbers.items():
            if count > 1:
                duplicate_pad_numbers.append({"reference": ref, "pad": number, "physical_count": count})
        for number in sorted(expected_pins[ref]-set(numbers), key=natural):
            missing_pads.append({"reference": ref, "pin": number, "expected_net": pin_nets.get((ref, number))})
        for number in sorted(set(numbers)-expected_pins[ref], key=natural):
            extra_pads.append({"reference": ref, "pad": number})
        for pad_index, pad in enumerate(pads):
            number = str(pad.GetNumber())
            if not number:
                if pad.GetNetCode():
                    mismatches.append({"reference": ref, "pad": "", "pad_index": pad_index,
                                       "expected_net": None, "actual_net": str(pad.GetNetname()),
                                       "issue": "unnumbered mechanical pad has an electrical net"})
                continue
            pad_records.append((ref, number, pad))
            expected = pin_nets.get((ref, number))
            actual_net = str(pad.GetNetname())
            nc = is_nc(expected, groups.get(expected, ()))
            accepted = actual_net == (expected or "") or (nc and actual_net == "")
            if nc and actual_net == "":
                nc_empty += 1
            if not accepted:
                mismatches.append({"reference": ref, "pad": number, "pad_index": pad_index,
                                   "expected_net": expected, "actual_net": actual_net,
                                   "net_code": int(pad.GetNetCode()),
                                   "position_mm": [mm(pad.GetPosition().x), mm(pad.GetPosition().y)]})
            if expected and not nc:
                netcode_groups[int(pad.GetNetCode())].add(expected)
                actual_pin_groups[actual_net].add((ref, number))
    cross_groups = [{"net_code": code, "XML_nets": sorted(names)} for code, names in netcode_groups.items() if len(names) > 1]
    expected_groups = {frozenset(node for node in nodes if node[0] in expected_refs)
                       for net, nodes in groups.items() if not is_nc(net, nodes)}
    expected_groups.discard(frozenset())
    board_groups = {frozenset(nodes) for nodes in actual_pin_groups.values()}
    report["pin_mapping"] = {
        "pad_net_mismatches": mismatches, "missing_physical_pads": missing_pads,
        "extra_numbered_pads": extra_pads, "duplicate_pad_numbers_checked_individually": duplicate_pad_numbers,
        "named_netcode_cross_groups": cross_groups,
        "expected_non_NC_netgroups": len(expected_groups), "actual_non_NC_netgroups": len(board_groups),
        "non_NC_netgroup_membership_equal": expected_groups == board_groups,
        "NC_policy": "Every NC symbol pin must have a pad. XML singleton unconnected-* may be unnamed on PCB; no functional net may be unnamed.",
        "NC_physical_pads_with_empty_PCB_net": nc_empty,
    }
    report["counts"].update({"physical_numbered_pads_checked": len(pad_records),
                             "XML_DNP_components": sum(xml_dnp(c) for c in components.values()),
                             "PCB_DNP_components": sum(fp.IsDNP() for fp in footprints if fp.GetReference() in expected_refs)})
    report["footprint_mapping"] = {"mismatches": fp_mismatches, "candidate_map_count": len(candidate_map),
                                    "candidate_19_match": all(ref in actual and len(actual[ref]) == 1
                                                               and str(actual[ref][0].GetFPIDAsString()) == fp
                                                               for ref, fp in candidate_map.items())}
    report["DNP_mismatches"] = dnp_mismatches
    report["value_mismatches"] = value_mismatches
    for check, findings in [("pad_net_mapping", mismatches), ("missing_physical_pads", missing_pads),
                             ("extra_numbered_pads", extra_pads), ("netcode_cross_groups", cross_groups),
                             ("footprint_ID_mapping", fp_mismatches), ("DNP_mapping", dnp_mismatches),
                             ("component_values", value_mismatches)]:
        if findings:
            report["errors"].append({"check": check, "count": len(findings)})
    if expected_groups != board_groups:
        report["errors"].append({"check": "non_NC_netgroup_membership"})
    if not report["footprint_mapping"]["candidate_19_match"]:
        report["errors"].append({"check": "candidate_19_footprint_mapping"})
    report["physical_mapping_pass"] = not report["errors"]

    report["external_DRC"] = drc_summary(args.drc)
    layout_checks(board, footprints, report, args)
    connectivity_checks(board, pad_records, pin_nets, groups, report)
    if report["connectivity"]["cross_net_contacts"]:
        report["physical_mapping_pass"] = False
    report["verification_completed"] = True
    report["status"] = "PASS_MAPPING" if not report["errors"] else "FAIL"
    report["fabrication_ready"] = False
    report["scope_limit"] = "Readback validates physical assignment and records layout/routing findings; electrical ratings, thermal design and manufacturability are not approved."
    return report, 0 if not report["errors"] else 1


def write_report(report, args):
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_text.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    counts = report.get("counts", {})
    text = ["Independent PCB readback check", "="*30, "Status: " + report.get("status", "ERROR"),
            "Verification completed: " + str(report.get("verification_completed", False)),
            "Physical mapping pass: " + str(report.get("physical_mapping_pass", False)),
            "Board: " + str(args.board), "XML netlist: " + str(args.netlist),
            "Expected / present physical references: %s / %s" % (counts.get("expected_physical_references"), counts.get("XML_physical_references_present")),
            "Numbered physical pads checked: " + str(counts.get("physical_numbered_pads_checked")),
            "Copper layers / mounting holes: %s / %s" % (counts.get("copper_layers"), counts.get("mounting_hole_footprints")),
            "Tracks+arcs / vias / zones: %s / %s / %s" % (counts.get("tracks_and_arcs"), counts.get("vias"), counts.get("zones")),
            "Unconnected (pcbnew raw): " + str(report.get("connectivity", {}).get("unconnected_count")),
            "Unconnected (external CLI DRC): " + str(report.get("external_DRC", {}).get("unconnected_items_count", "not supplied")),
            "Layout geometry pass: " + str(report.get("layout_geometry_pass")),
            "Routing complete: " + str(report.get("routing_complete", False)),
            "Fabrication release: NOT APPROVED", "", "Errors (%s):" % len(report["errors"])]
    text.extend(json.dumps(item, ensure_ascii=False) for item in report["errors"])
    text.extend(["", "Warnings (%s):" % len(report["warnings"])])
    text.extend(json.dumps(item, ensure_ascii=False) for item in report["warnings"])
    text.extend(["", "Full pad mismatches, courtyard intersections, bounds and DRC summary are in pcb_check.json."])
    args.output_text.write_text("\n".join(text)+"\n", encoding="utf-8")
    print("\n".join(text[:17]))
    print("Reports:", args.output_json, args.output_text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--board", type=Path, default=BASE/"inverter.kicad_pcb")
    parser.add_argument("--netlist", type=Path, default=BASE/"review/inverter.net.xml")
    parser.add_argument("--candidates", type=Path, default=BASE/"tools/compact_footprint_candidates.json")
    parser.add_argument("--drc", type=Path, default=BASE/"review/pcb_drc.json")
    parser.add_argument("--output-json", type=Path, default=BASE/"review/pcb_check.json")
    parser.add_argument("--output-text", type=Path, default=BASE/"review/pcb_check.txt")
    parser.add_argument("--expected-components", type=int, default=313)
    parser.add_argument("--expected-copper-layers", type=int, default=6)
    parser.add_argument("--expected-width-mm", type=float, default=60)
    parser.add_argument("--expected-height-mm", type=float, default=60)
    parser.add_argument("--expected-outer-contours", type=int, default=1)
    parser.add_argument("--expected-mounting-holes", type=int, default=4)
    parser.add_argument("--boundary-tolerance-mm", type=float, default=0.05)
    parser.add_argument("--severe-overlap-area-mm2", type=float, default=0.25)
    parser.add_argument("--severe-overlap-ratio", type=float, default=0.05)
    parser.add_argument("--strict-layout", action="store_true", help="Make out-of-bounds or severe courtyard findings fail the process too.")
    args = parser.parse_args()
    try:
        report, code = verify(args)
    except Exception as exc:
        report = {"schema_version": 1, "status": "CHECKER_ERROR", "verification_completed": False,
                  "physical_mapping_pass": False, "errors": [{"check": "checker_exception", "type": type(exc).__name__, "error": str(exc)}],
                  "warnings": [], "counts": {}}
        code = 2
    write_report(report, args)
    return code


if __name__ == "__main__":
    sys.exit(main())

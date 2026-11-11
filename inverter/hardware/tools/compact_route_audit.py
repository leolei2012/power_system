"""Read-only post-route length audit for the integrated STM32G431 inverter.

Use KiCad's Python, for example:
  python compact_route_audit.py --board ../inverter.kicad_pcb --out ../review/compact_route_audit.json

No board, project, schematic or zone fill is written.  Saved filled-zone islands
prove connectivity only: no distance is assigned to a pour.  Explicit routes
use actual track centrelines, via axes and copper-covered pad/junction links.
This is a shortest path in that stated graph, not a continuous-copper geodesic,
an impedance calculation, or a declaration that the decoupling loop is sound.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import heapq
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

try:
    import pcbnew as pcb
except ImportError:
    raise SystemExit("Use C:/Program Files/KiCad/10.0/bin/python.exe")

BASE = Path(__file__).resolve().parents[1]
IU = pcb.FromMM(1)


def xy(item):
    q = item.GetPosition()
    return (q.x / IU, q.y / IU)


def point(q):
    return pcb.VECTOR2I(round(q[0] * IU), round(q[1] * IU))


def uid(item):
    return item.m_Uuid.AsString()


def box(shape):
    bb = shape.BBox()
    return (bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom())


def intersects(a, b):
    return a[0] <= b[2] and a[2] >= b[0] and a[1] <= b[3] and a[3] >= b[1]


def project(q, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    dd = dx * dx + dy * dy
    t = max(0., min(1., ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / dd)) if dd else 0.
    return t, (a[0] + t * dx, a[1] + t * dy)


def nearest_segments(a, b, c, d):
    """Closest centreline points, with an explicit crossing case."""
    cross = lambda u, v: u[0] * v[1] - u[1] * v[0]
    ab, cd, ac = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1]), (c[0] - a[0], c[1] - a[1])
    denominator = cross(ab, cd)
    if abs(denominator) > 1e-14:
        t, u = cross(ac, cd) / denominator, cross(ac, ab) / denominator
        if 0 <= t <= 1 and 0 <= u <= 1:
            q = (a[0] + t * ab[0], a[1] + t * ab[1])
            return t, q, u, q
    candidates = []
    for t, q in [(0., a), (1., b)]:
        u, r = project(q, c, d)
        candidates.append((math.dist(q, r), t, q, u, r))
    for u, r in [(0., c), (1., d)]:
        t, q = project(r, a, b)
        candidates.append((math.dist(q, r), t, q, u, r))
    _, t, q, u, r = min(candidates)
    return t, q, u, r


class CopperNet:
    """Independent per-net physical union and measurable-route graph."""
    def __init__(self, board, code, objects, zones, layers):
        self.board, self.code, self.layers = board, code, layers
        self.primitives, self.by_uuid, self.edges = [], {}, defaultdict(list)
        self.nodes, self.node_index = [], {}
        self.segment_contacts = defaultdict(dict)
        self.unmodeled_joins = 0
        self.unfilled_zones = 0
        for obj in objects:
            kind = "pad" if isinstance(obj, pcb.PAD) else "via" if obj.GetClass() == "PCB_VIA" else "arc" if obj.GetClass() == "PCB_ARC" else "track"
            shapes = {l: obj.GetEffectiveShape(l) for l in layers if obj.IsOnLayer(l)}
            data = {"uuid": uid(obj), "kind": kind, "shapes": shapes, "object": obj}
            if kind == "track":
                a, b = obj.GetStart(), obj.GetEnd()
                data.update(a=(a.x / IU, a.y / IU), b=(b.x / IU, b.y / IU))
                data["length"] = math.dist(data["a"], data["b"])
            else:
                data["center"] = xy(obj)
            self.add(data)
        for raw in zones:
            z = raw if hasattr(raw, "GetNetCode") else pcb.Cast_to_ZONE(raw)
            for layer in layers:
                if not z.IsOnLayer(layer):
                    continue
                poly = z.GetFilledPolysList(layer)
                if not poly.OutlineCount():
                    self.unfilled_zones += 1
                for island in range(poly.OutlineCount()):
                    self.add({"uuid": f"{uid(z)}:{layer}:{island}", "zone_uuid": uid(z),
                              "kind": "zone", "shapes": {layer: poly.UnitSet(island)}, "object": z})
        self.parent = list(range(len(self.primitives)))
        self.build()

    def add(self, item):
        item["boxes"] = {layer: box(shape) for layer, shape in item["shapes"].items()}
        self.by_uuid[item["uuid"]] = len(self.primitives)
        self.primitives.append(item)

    def root(self, index):
        while self.parent[index] != index:
            self.parent[index] = self.parent[self.parent[index]]
            index = self.parent[index]
        return index

    def node(self, key, xy_value, layer, primitive):
        if key not in self.node_index:
            self.node_index[key] = len(self.nodes)
            self.nodes.append({"xy": xy_value, "layer": layer, "primitive": primitive})
        return self.node_index[key]

    def contact(self, index, layer, parameter=None):
        item = self.primitives[index]
        if item["kind"] == "track":
            t = round(float(parameter), 12)
            q = (item["a"][0] + t * (item["b"][0] - item["a"][0]),
                 item["a"][1] + t * (item["b"][1] - item["a"][1]))
            node = self.node((index, layer, t), q, layer, index)
            self.segment_contacts[index][t] = node
            return node
        return self.node((index, layer, "center"), item["center"], layer, index)

    def edge(self, a, b, length, kind, primitives):
        data = {"length": length, "kind": kind, "primitives": primitives}
        self.edges[a].append((b, data))
        self.edges[b].append((a, data))

    @staticmethod
    def covered(a, b, shape_a, shape_b):
        # Avoid inventing a straight join across an empty concavity.  Actual
        # shape intersection has already proved a physical connection; if this
        # sampled join cannot be represented, leave its distance unquantified.
        count = max(1, math.ceil(math.dist(a, b) / .025))
        for i in range(count + 1):
            t = i / count
            q = point((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            if not (shape_a.Collide(q) or shape_b.Collide(q)):
                return False
        return True

    def join(self, i, j, layer):
        a, b = self.primitives[i], self.primitives[j]
        if a["kind"] in ["zone", "arc"] or b["kind"] in ["zone", "arc"]:
            return
        if a["kind"] == b["kind"] == "track":
            t, q, u, r = nearest_segments(a["a"], a["b"], b["a"], b["b"])
        elif a["kind"] == "track":
            t, q = project(b["center"], a["a"], a["b"])
            u, r = None, b["center"]
        elif b["kind"] == "track":
            u, r = project(a["center"], b["a"], b["b"])
            t, q = None, a["center"]
        else:
            t, q, u, r = None, a["center"], None, b["center"]
        if not self.covered(q, r, a["shapes"][layer], b["shapes"][layer]):
            self.unmodeled_joins += 1
            return
        na, nb = self.contact(i, layer, t), self.contact(j, layer, u)
        self.edge(na, nb, math.dist(q, r), "copper_join", [i, j])

    def build(self):
        for i, item in enumerate(self.primitives):
            if item["kind"] in ["pad", "via"]:
                nodes = [self.contact(i, layer) for layer in item["shapes"]]
                for k, a in enumerate(nodes):
                    for b in nodes[k + 1:]:
                        self.edge(a, b, 0., "via_barrel" if item["kind"] == "via" else "plated_pad_barrel", [i])
            elif item["kind"] == "track":
                for layer in item["shapes"]:
                    self.contact(i, layer, 0.)
                    self.contact(i, layer, 1.)
        by_layer = defaultdict(list)
        for i, item in enumerate(self.primitives):
            for layer in item["shapes"]:
                by_layer[layer].append(i)
        for layer, indices in by_layer.items():
            for k, i in enumerate(indices):
                a = self.primitives[i]
                for j in indices[:k]:
                    b = self.primitives[j]
                    if not intersects(a["boxes"][layer], b["boxes"][layer]):
                        continue
                    if a["shapes"][layer].Collide(b["shapes"][layer]):
                        self.parent[self.root(i)] = self.root(j)
                        self.join(i, j, layer)
        for i, contacts in self.segment_contacts.items():
            ordered = sorted(contacts.items())
            for (ta, a), (tb, b) in zip(ordered, ordered[1:]):
                self.edge(a, b, (tb - ta) * self.primitives[i]["length"], "track_centerline", [i])

    def audit(self, source_pads, target_pads):
        source_indices = [self.by_uuid[uid(a)] for a in source_pads]
        target_indices = [self.by_uuid[uid(a)] for a in target_pads]
        connected_pairs = [(a, b) for a in source_indices for b in target_indices if self.root(a) == self.root(b)]
        roots = {self.root(a) for a in source_indices}
        pour_islands = [q for i, q in enumerate(self.primitives) if q["kind"] == "zone" and self.root(i) in roots]
        start = [self.contact(i, l) for i in source_indices for l in self.primitives[i]["shapes"]]
        ends = {self.contact(i, l) for i in target_indices for l in self.primitives[i]["shapes"]}
        distances, previous, queue = {}, {}, []
        for node in start:
            distances[node] = 0.
            heapq.heappush(queue, (0., node))
        reached = None
        while queue:
            distance, node = heapq.heappop(queue)
            if distance != distances[node]:
                continue
            if node in ends:
                reached = node
                break
            for nxt, edge in self.edges[node]:
                candidate = distance + edge["length"]
                if candidate + 1e-10 < distances.get(nxt, math.inf):
                    distances[nxt] = candidate
                    previous[nxt] = (node, edge)
                    heapq.heappush(queue, (candidate, nxt))
        result = {"saved_copper_connected": bool(connected_pairs),
                  "pour_islands_in_source_component": len(pour_islands),
                  "length_including_pours_mm": None,
                  "via_count": None, "layers_used": None,
                  "unfilled_zone_layer_count": self.unfilled_zones}
        if reached is None:
            result["status"] = "connected_pour_length_unquantified" if connected_pairs and pour_islands else "connected_geometry_length_unquantified" if connected_pairs else "missing_saved_copper_path"
            result["planar_copper_path_model_mm"] = None
            result["track_centerline_mm"] = None
            result["connectivity_pour_evidence"] = [{"zone_uuid": q["zone_uuid"], "island": q["uuid"],
                                                     "layers": [self.board.GetLayerName(l) for l in q["shapes"]]} for q in pour_islands]
            return result
        path_nodes, path_edges = [reached], []
        while path_nodes[-1] in previous:
            before, edge = previous[path_nodes[-1]]
            path_edges.append(edge)
            path_nodes.append(before)
        path_nodes.reverse()
        path_edges.reverse()
        tracks, via_transitions, pad_transitions, touched_vias = set(), set(), set(), set()
        track_length = join_length = 0.
        for edge in path_edges:
            if edge["kind"] == "track_centerline":
                track_length += edge["length"]
                tracks.update(self.primitives[i]["uuid"] for i in edge["primitives"])
            elif edge["kind"] == "copper_join":
                join_length += edge["length"]
            elif edge["kind"] == "via_barrel":
                via_transitions.update(self.primitives[i]["uuid"] for i in edge["primitives"])
            elif edge["kind"] == "plated_pad_barrel":
                pad_transitions.update(self.primitives[i]["uuid"] for i in edge["primitives"])
            touched_vias.update(self.primitives[i]["uuid"] for i in edge["primitives"] if self.primitives[i]["kind"] == "via")
        result.update(status="quantified_explicit_route", planar_copper_path_model_mm=round(distances[reached], 6),
                      track_centerline_mm=round(track_length, 6), pad_and_junction_mm=round(join_length, 6),
                      via_count=len(via_transitions), via_uuids=sorted(via_transitions),
                      via_objects_touched_count=len(touched_vias), plated_pad_layer_changes=len(pad_transitions),
                      layers_used=sorted({self.board.GetLayerName(self.nodes[n]["layer"]) for n in path_nodes}),
                      track_uuids=sorted(tracks),
                      globally_shortest_copper_length_proven=False,
                      pour_shortcuts_not_quantified=bool(pour_islands),
                      path_points=[{"x": round(self.nodes[n]["xy"][0], 6), "y": round(self.nodes[n]["xy"][1], 6),
                                    "layer": self.board.GetLayerName(self.nodes[n]["layer"])} for n in path_nodes])
        return result


def targets(board_pads):
    result = []
    def add(name, group, a, ap, b, bp):
        result.append({"name": name, "group": group, "source": {"ref": a, "pin": str(ap)}, "target": {"ref": b, "pin": str(bp)}})
    for phase, driver, rh, rl, first in [("U", "U7", "R19", "R20", 25), ("V", "U8", "R25", "R26", 29), ("W", "U9", "R31", "R32", 33)]:
        add(phase + " HO to gate resistor", "driver_gate", driver, 7, rh, 1)
        add(phase + " LO to gate resistor", "driver_gate", driver, 4, rl, 1)
        for c in [first, first + 1]:
            add(f"{phase} VB to C{c}", "driver_bootstrap", driver, 8, f"C{c}", 1)
            add(f"{phase} VS return from C{c}", "driver_bootstrap_return", driver, 6, f"C{c}", 2)
        for c in [first + 2, first + 3]:
            add(f"{phase} VCC to C{c}", "driver_vcc", driver, 5, f"C{c}", 1)
            add(f"{phase} COM return from C{c}", "driver_com_return", driver, 3, f"C{c}", 2)
    for c, supply, ground in [(63, 16, 15), (64, 32, 31), (65, 48, 47), (66, 64, 63), (67, 1, 63)]:
        add(f"C{c} MCU supply pin{supply}", "mcu_decoupling", f"C{c}", 1, "U30", supply)
        add(f"C{c} MCU ground pin{ground}", "mcu_decoupling_return", f"C{c}", 2, "U30", ground)
    for pin in [16, 32, 48, 64]:
        add(f"C68 bulk to VDD{pin}", "mcu_bulk_distribution", "C68", 1, "U30", pin)
    ground_pins = [15, 27, 31, 47, 63]
    if board_pads.get(("C68", "2")):
        cap = board_pads[("C68", "2")][0]
        nearest = min(ground_pins, key=lambda p: min(math.dist(xy(cap), xy(q)) for q in board_pads.get(("U30", str(p)), [])))
        add("C68 ground to physically nearest MCU VSS", "mcu_bulk_return", "C68", 2, "U30", nearest)
    for cap, pin in [(77, 29), (78, 29), (79, 28), (80, 28)]:
        add(f"C{cap} analog supply pin{pin}", "mcu_analog_decoupling", f"C{cap}", 1, "U30", pin)
        add(f"C{cap} analog return VSSA", "mcu_analog_return", f"C{cap}", 2, "U30", 27)
    for i, mcu_pin in enumerate([8, 9, 10, 11, 18, 24, 25, 26]):
        cap, resistor = f"C{69 + i}", f"R{84 + i}"
        add(f"{resistor} output to {cap}", "adc_rc_node", resistor, 2, cap, 1)
        add(f"{cap} ADC to MCU pin{mcu_pin}", "adc_to_mcu", cap, 1, "U30", mcu_pin)
        add(f"{cap} ground reference to VSSA", "adc_ground_reference", cap, 2, "U30", 27)
    return result


def audit(board_path, xml_path):
    before = hashlib.sha256(board_path.read_bytes()).hexdigest()
    board = pcb.LoadBoard(str(board_path))
    layers = list(board.GetEnabledLayers().CuStack())
    xml = ET.parse(xml_path).getroot()
    contract = {(n.get("ref"), n.get("pin")): net.get("name") for net in xml.findall("./nets/net") for n in net.findall("node")}
    pads, by_net, zones = defaultdict(list), defaultdict(list), defaultdict(list)
    for f in board.GetFootprints():
        for pad in f.Pads():
            if not pad.GetNumber():
                continue
            pads[(f.GetReference(), pad.GetNumber())].append(pad)
            if pad.GetNetCode():
                by_net[pad.GetNetCode()].append(pad)
    for track in board.GetTracks():
        if track.GetNetCode():
            by_net[track.GetNetCode()].append(track)
    for raw in board.Zones():
        zone = raw if hasattr(raw, "GetNetCode") else pcb.Cast_to_ZONE(raw)
        if not zone.GetIsRuleArea() and zone.GetNetCode():
            zones[zone.GetNetCode()].append(zone)
    cache, results = {}, []
    for item in targets(pads):
        source_key, target_key = (item["source"]["ref"], item["source"]["pin"]), (item["target"]["ref"], item["target"]["pin"])
        aa, bb = pads.get(source_key, []), pads.get(target_key, [])
        item["expected_net"] = contract.get(source_key)
        item["endpoints"] = {side: [{"uuid": uid(p), "x": round(xy(p)[0], 6), "y": round(xy(p)[1], 6),
                                      "net": p.GetNetname(), "layers": [board.GetLayerName(l) for l in layers if p.IsOnLayer(l)]} for p in pp]
                             for side, pp in [("source", aa), ("target", bb)]}
        if not aa or not bb:
            item["status"] = "missing_endpoint"
        elif not contract.get(source_key) or contract.get(source_key) != contract.get(target_key) or any(p.GetNetname() != contract[source_key] for p in aa + bb):
            item["status"] = "endpoint_XML_net_mismatch"
            item["target_XML_net"] = contract.get(target_key)
        else:
            item["straight_line_mm"] = round(min(math.dist(xy(a), xy(b)) for a in aa for b in bb), 6)
            code = aa[0].GetNetCode()
            if code not in cache:
                cache[code] = CopperNet(board, code, by_net[code], zones[code], layers)
            item.update(cache[code].audit(aa, bb))
            if item.get("planar_copper_path_model_mm") is not None and item["straight_line_mm"]:
                item["model_detour_ratio"] = round(item["planar_copper_path_model_mm"] / item["straight_line_mm"], 4)
        results.append(item)
    after = hashlib.sha256(board_path.read_bytes()).hexdigest()
    return {"schema_version": 1, "generated_UTC": datetime.now(timezone.utc).isoformat(),
            "board": str(board_path), "board_sha256": before, "netlist": str(xml_path),
            "netlist_sha256": hashlib.sha256(xml_path.read_bytes()).hexdigest(),
            "source_unchanged_during_audit": before == after,
            "read_only": True, "copper_layers": [board.GetLayerName(l) for l in layers],
            "method": {"connectivity": "Actual same-net effective copper shapes and each saved filled-zone island are unioned per shared copper layer; via/PTH plating connects layers.",
                       "length": "Dijkstra shortest path on actual track centrelines plus copper-covered pad-centre/junction links. 0.025 mm sampled join coverage; explicit track portions use Euclidean centreline lengths.",
                       "excluded": "No length through pours, arc centrelines, or unrepresentable shape joins. Via/PTH vertical barrel length excluded; counted separately. No board or zone fill is saved.",
                       "limits": "This graph length is not a continuous-copper geodesic, loop area, impedance, thermal result or pass/fail threshold. Existing explicit routes may have unmeasured pour shortcuts. Saved fill can be stale until final DRC/refill."},
            "summary": {"pair_count": len(results), "statuses": dict(Counter(r["status"] for r in results)),
                        "endpoint_contract_errors": sum(r["status"] in ["missing_endpoint", "endpoint_XML_net_mismatch"] for r in results)},
            "nets": [{"net": board.GetNetsByNetcode()[code].GetNetname(), "primitive_count": len(net.primitives),
                      "graph_nodes": len(net.nodes), "saved_zone_islands": sum(p["kind"] == "zone" for p in net.primitives),
                      "arcs_excluded_from_length": sum(p["kind"] == "arc" for p in net.primitives),
                      "copper_joins_not_quantified": net.unmodeled_joins} for code, net in cache.items()],
            "pairs": results}


def self_test():
    """A non-Euclidean two-layer physical route: 7 mm, 5 mm chord, 1 via."""
    board = pcb.BOARD()
    board.SetCopperLayerCount(2)
    net = pcb.NETINFO_ITEM(board, "TEST", 1)
    board.Add(net)
    objects, endpoints = [], []
    for name, q, layer in [("A", (0, 0), pcb.F_Cu), ("B", (4, 3), pcb.B_Cu)]:
        fp = pcb.FOOTPRINT(board)
        fp.SetReference(name)
        board.Add(fp)
        pad = pcb.PAD(fp)
        pad.SetNumber("1")
        pad.SetAttribute(pcb.PAD_ATTRIB_SMD)
        pad.SetShape(pcb.PAD_SHAPE_RECT)
        pad.SetSize(point((.4, .4)))
        layer_set = pcb.LSET()
        layer_set.AddLayer(layer)
        pad.SetLayerSet(layer_set)
        pad.SetPosition(point(q))
        pad.SetNet(net)
        fp.Add(pad)
        endpoints.append(pad)
        objects.append(pad)
    for a, b, layer in [((0, 0), (3, 0), pcb.F_Cu), ((3, 0), (3, 3), pcb.B_Cu), ((3, 3), (4, 3), pcb.B_Cu)]:
        t = pcb.PCB_TRACK(board)
        t.SetStart(point(a))
        t.SetEnd(point(b))
        t.SetLayer(layer)
        t.SetWidth(pcb.FromMM(.2))
        t.SetNet(net)
        board.Add(t)
        objects.append(t)
    via = pcb.PCB_VIA(board)
    via.SetPosition(point((3, 0)))
    via.SetWidth(pcb.FromMM(.6))
    via.SetDrill(pcb.FromMM(.3))
    via.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
    via.SetNet(net)
    board.Add(via)
    objects.append(via)
    graph = CopperNet(board, 1, objects, [], [pcb.F_Cu, pcb.B_Cu])
    result = graph.audit([endpoints[0]], [endpoints[1]])
    assert result["status"] == "quantified_explicit_route", result
    assert abs(result["planar_copper_path_model_mm"] - 7) < 1e-6, result
    assert result["via_count"] == 1, result
    assert set(result["layers_used"]) == {"F.Cu", "B.Cu"}, result
    cut = CopperNet(board, 1, [o for o in objects if o is not objects[-2]], [], [pcb.F_Cu, pcb.B_Cu])
    missing = cut.audit([endpoints[0]], [endpoints[1]])
    assert missing["status"] == "missing_saved_copper_path", missing
    print("PASS: measured route7 mm != chord5 mm; via1; layerF/B; a missing segment remains disconnected.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board", type=Path, default=BASE / "inverter.kicad_pcb")
    parser.add_argument("--netlist", type=Path, default=BASE / "review/inverter.net.xml")
    parser.add_argument("--out", type=Path, default=BASE / "review/compact_route_audit.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    out = args.out.resolve()
    if out.suffix.lower() != ".json":
        out = out.with_suffix(".json")
    board_path, xml_path = args.board.resolve(), args.netlist.resolve()
    assert out not in [board_path, xml_path] and out.with_suffix(".txt") not in [board_path, xml_path]
    report = audit(board_path, xml_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    lines = ["Compact inverter read-only route-length audit", "Board: " + str(board_path), "SHA256: " + report["board_sha256"],
             "Counts: " + json.dumps(report["summary"]),
             "Lengths are explicit-route graph model distances; pours/arcs/vertical barrels are not measured.", ""]
    for row in report["pairs"]:
        lines.append(f"{row['name']}: {row['status']}; route_mm={row.get('planar_copper_path_model_mm')}; "
                     f"straight_mm={row.get('straight_line_mm')}; vias={row.get('via_count')}; layers={row.get('layers_used')}")
    out.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf8")
    print(json.dumps(report["summary"]))
    print("Source unchanged:", report["source_unchanged_during_audit"], "Reports:", out, out.with_suffix(".txt"))
    return int(bool(report["summary"]["endpoint_contract_errors"]) or not report["source_unchanged_during_audit"])


if __name__ == "__main__":
    sys.exit(main())

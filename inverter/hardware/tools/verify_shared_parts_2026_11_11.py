"""Independently compare CLI-exported before/after Rev E physical connectivity."""
from pathlib import Path
import collections
import json
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
OUT = BASE/'review/shared_parts_2026-11-11'


def read(name):
    return ET.parse(OUT/name).getroot()


def nets(root):
    return {n.attrib['name']: frozenset((x.attrib['ref'], x.attrib['pin']) for x in n.findall('node'))
            for n in root.findall('./nets/net')}


def comps(root):
    return {c.attrib['ref']: c for c in root.findall('./components/comp')}


def dnp_map(components):
    return {r: c.find("./property[@name='dnp']") is not None for r, c in components.items()}


def main():
    old, new = read('before.net.xml'), read('after.net.xml')
    a, b = nets(old), nets(new)
    x, y = comps(old), comps(new)
    old_partition, new_partition = collections.Counter(a.values()), collections.Counter(b.values())
    # Explicit page/global labels must keep their names. Only KiCad-generated
    # Net-(ref-pinFunction) names can change with a manufacturer pin name.
    stable_names = {n: v for n, v in a.items() if not n.startswith(('Net-(', 'unconnected-('))}
    renames = []
    for name, nodes in a.items():
        if b.get(name) != nodes:
            match = [new_name for new_name, new_nodes in b.items() if new_nodes == nodes]
            renames.append({'before': name, 'after': match, 'nodes': sorted(nodes)})
    amap = {p: n for n, nodes in a.items() for p in nodes}
    bmap = {p: n for n, nodes in b.items() for p in nodes}
    ref_equal = x.keys() == y.keys()
    value_changes = [(r, x[r].findtext('value'), y[r].findtext('value'))
                     for r in x.keys() & y.keys()
                     if x[r].findtext('value') != y[r].findtext('value')]
    header_equal = all(amap.get((r, str(p))) == bmap.get((r, str(p)))
                       for r in ['J101', 'J102'] for p in range(1, 33))
    report = {
        'before_components': len(x), 'after_components': len(y),
        'ref_set_equal': ref_equal, 'before_physical_pin_nodes': len(amap),
        'after_physical_pin_nodes': len(bmap), 'before_nets': len(a), 'after_nets': len(b),
        'pin_partition_equal': old_partition == new_partition,
        'explicit_net_names_preserved': all(b.get(n) == nodes for n, nodes in stable_names.items()),
        'automatic_net_renames': renames,
        'value_changes': value_changes, 'dnp_equal': dnp_map(x) == dnp_map(y),
        'dnp_count': sum(dnp_map(y).values()), 'header64_pin_net_equal': header_equal,
        'shared_bound_refs': sum(c.find('libsource').attrib['lib'] == 'MyParts' for c in y.values()),
        'mos_pad_map': {r: {p: bmap[(r, p)] for p in '12345678'}
                        for r in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7']},
    }
    report['pass'] = (ref_equal and not value_changes and report['dnp_equal'] and header_equal
                      and report['pin_partition_equal'] and report['explicit_net_names_preserved'])
    (OUT/'pin_equivalence.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ['mos_pad_map', 'automatic_net_renames']}, indent=2))
    assert report['pass'], 'Physical pin connectivity changed'


if __name__ == '__main__':
    main()

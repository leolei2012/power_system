"""Incrementally adopt reviewed shared parts in the CURRENT 47-reference Rev E.

This is not a schematic generator. It only replaces selected existing symbol
definitions / procurement metadata / footprints. Existing physical pin numbers,
positions, wires, instance UUIDs, values, reference designators and DNP stay put.
It refuses any shared symbol whose pin coordinates need manual rewiring.

Run once with --apply, then --verify after exporting the resulting netlist.
Never use the earlier Rev C / Rev D authoring scripts to rerun this migration.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
import zipfile

import sexpdata as sx

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
SHARED = REPO.parent / 'kicad_library'
CLI = Path('C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
REVIEW = BASE / 'review/shared_parts_2026-11-11'
MANIFEST = REVIEW / 'migration.json'
BEFORE_XML = REVIEW / 'before.net.xml'
AFTER_XML = BASE / 'review/controller.net.xml'
CAP_REFS = {'C304', 'C306', 'C307', 'C308'}
SWITCH_REFS = {'SW2', 'SW3'}


def tag(item, name):
    return isinstance(item, list) and bool(item) and str(item[0]) == name


def children(item, name):
    return [x for x in item if tag(x, name)]


def child(item, name):
    return next((x for x in item if tag(x, name)), None)


def properties(item):
    return {str(x[1]): str(x[2]) for x in children(item, 'property')}


def read(path):
    return sx.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def write(path, data):
    path.write_text('(' + str(data[0]) + '\n' + '\n'.join(sx.dumps(x) for x in data[1:]) + ')\n', encoding='utf-8')


def active_pages():
    result = {}

    def visit(path):
        path = path.resolve()
        assert path.is_relative_to(BASE), ('Outside owned directory', path)
        if path in result:
            return
        data = read(path)
        result[path] = data
        for sheet in children(data, 'sheet'):
            visit(path.parent / properties(sheet)['Sheetfile'])

    visit(BASE / 'controller.kicad_sch')
    assert len(result) == 7, len(result)
    return result


def pins(definition, unit):
    result = {}
    for sub in children(definition, 'symbol'):
        if int(str(sub[1]).rsplit('_', 2)[1]) not in (0, unit):
            continue
        for pin in children(sub, 'pin'):
            number = str(child(pin, 'number')[1])
            assert number not in result, number
            result[number] = {
                'at': list(child(pin, 'at')[1:]),
                'type': str(pin[1]),
                'name': str(child(pin, 'name')[1]),
            }
    return result


def instance_records(pages):
    result = {}
    for path, data in pages.items():
        for inst in children(data, 'symbol'):
            p = properties(inst)
            ref = p['Reference']
            if ref.startswith('#'):
                continue
            assert ref not in result, ref
            result[ref] = {
                'page': path.name,
                'lib_id': str(child(inst, 'lib_id')[1]),
                'properties': p,
                'dnp': str(child(inst, 'dnp')[1]),
                'at': list(child(inst, 'at')[1:]),
                'unit': int(child(inst, 'unit')[1]),
                'uuid': str(child(inst, 'uuid')[1]),
            }
    assert len(result) == 47, len(result)
    return result


def export_xml(path):
    done = subprocess.run([str(CLI), 'sch', 'export', 'netlist', '--format', 'kicadxml',
                           '--output', str(path), str(BASE / 'controller.kicad_sch')],
                          capture_output=True, text=True, encoding='utf-8')
    if done.returncode:
        raise RuntimeError(done.stdout + done.stderr)


def set_property(inst, key, value):
    existing = next((p for p in children(inst, 'property') if str(p[1]) == key), None)
    if existing is not None:
        existing[2] = value
        return
    x, y = child(inst, 'at')[1:3]
    inst.append([sx.Symbol('property'), key, value,
                 [sx.Symbol('at'), x, y, 0],
                 [sx.Symbol('hide'), sx.Symbol('yes')],
                 [sx.Symbol('effects'), [sx.Symbol('font'), [sx.Symbol('size'), .9, .9]]]])


def apply():
    assert not MANIFEST.exists(), 'Migration already has a manifest; do not replay over current work.'
    pages = active_pages()
    before = instance_records(pages)
    rows = list(csv.DictReader((SHARED / 'parts.csv').open(encoding='utf-8-sig', newline='')))
    by_c = {r['Supplier_PN']: r for r in rows}
    shared_defs = {str(x[1]): x for x in children(read(SHARED / 'symbols/MyParts.kicad_sym'), 'symbol')}
    REVIEW.mkdir(parents=True, exist_ok=True)
    export_xml(BEFORE_XML)

    # The archive is deliberately an active Rev E snapshot, not an old generator input.
    history = BASE / 'history'
    history.mkdir(exist_ok=True)
    archive = history / 'rev_e_before_shared_parts_2026-11-11.zip'
    assert not archive.exists(), archive
    backup = set(pages)
    for name in ('controller.kicad_pro', 'sym-lib-table', 'fp-lib-table',
                 'InverterLocal.kicad_sym', 'CoreProtection.kicad_sym',
                 'STM32G431RBT6_pin_plan.csv', 'README.md', 'core_supply_design.md'):
        backup.add(BASE / name)
    backup.update((BASE / 'bom').glob('*.csv'))
    backup.update((BASE / 'bom').glob('*.md'))
    for name in ('controller.net.xml', 'erc.json', 'core_supply_validation.json', 'minimum_core_validation.json'):
        if (BASE / 'review' / name).is_file():
            backup.add(BASE / 'review' / name)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(backup):
            z.write(path, path.relative_to(BASE).as_posix())
        z.write(BEFORE_XML, 'review/fresh_before_shared_parts.net.xml')
        z.writestr('snapshot.json', json.dumps({
            'revision': 'E-minimum-core-draft', 'date': '2026-11-11',
            'files_sha256': {p.relative_to(BASE).as_posix(): sha(p) for p in sorted(backup)},
            'physical_refs': 47, 'active_pages': 7,
        }, indent=2))

    migration = []
    for path, data in pages.items():
        lib_container = child(data, 'lib_symbols')
        old_defs = {str(x[1]): x for x in children(lib_container, 'symbol')}
        replacements = {}
        before_geometry = [copy.deepcopy(x) for x in data if isinstance(x, list) and str(x[0]) in
                           {'wire', 'junction', 'no_connect', 'label', 'global_label', 'hierarchical_label'}]
        for inst in children(data, 'symbol'):
            p = properties(inst)
            ref = p['Reference']
            if ref.startswith('#'):
                continue
            c = 'C318938' if ref in SWITCH_REFS else 'C14663' if ref in CAP_REFS else p.get('Supplier_PN', '')
            if not c:
                continue
            assert c in by_c, ('Exact C-number missing from shared catalogue', ref, c)
            row = by_c[c]
            assert row['Verification'] == 'reviewed', (ref, row['Verification'])
            if ref in CAP_REFS:
                assert p['Value'] == '100n' and p['Manufacturer'] == 'YAGEO'
                assert p['Footprint'] == 'Capacitor_SMD:C_0603_1608Metric'
                assert p.get('Voltage_Rating') == '16V'
                assert row['MPN'] == 'CC0603KRX7R9BB104'
                # Reviewed record: 100nF / 50V / +/-10% / X7R / 0603. Source
                # decouplers specify nominal 100n and 16V, not an unverified Ceff.
                assert '100nF' in row['Description'] and '50VDC' in row['Description'] and 'X7R' in row['Description']
            elif ref not in SWITCH_REFS:
                assert p['MPN'] == row['MPN'], (ref, p['MPN'], row['MPN'])
            old_id = str(child(inst, 'lib_id')[1])
            new_id = row['Symbol']
            new_def = copy.deepcopy(shared_defs[new_id.split(':', 1)[1]])
            old_pins = pins(old_defs[old_id], int(child(inst, 'unit')[1]))
            new_pins = pins(new_def, int(child(inst, 'unit')[1]))
            assert old_pins.keys() == new_pins.keys(), (ref, 'Physical pin set changed')
            changed_coords = {number: [old_pins[number]['at'], new_pins[number]['at']]
                              for number in old_pins if old_pins[number]['at'] != new_pins[number]['at']}
            assert not changed_coords, (ref, 'MANUAL REWIRE REQUIRED', changed_coords)
            new_def[1] = new_id
            replacements[new_id] = new_def
            child(inst, 'lib_id')[1] = new_id
            # Keep original displayed electrical value and reference placement.
            # Copy reviewed sourcing fields, not default Reference/Value positions.
            for key, value in properties(new_def).items():
                if key in {'Reference', 'Value', 'ki_fp_filters'}:
                    continue
                if key == 'Datasheet_File' and row['Datasheet_File']:
                    value = '${KIPRJMOD}/../../../../kicad_library/' + row['Datasheet_File']
                set_property(inst, key, value)
            for key in ('Manufacturer', 'MPN', 'Supplier_PN', 'Footprint', 'Verification', 'Library_Revision'):
                set_property(inst, key, row[key])
            url = 'https://item.szlcsc.com/15331.html' if c == 'C14663' else row['Purchase_URL']
            assert url.startswith('https://item.szlcsc.com/'), (ref, 'Domestic procurement URL required', url)
            set_property(inst, 'Purchase_URL', url)
            set_property(inst, 'Supplier', 'LCSC')
            set_property(inst, 'Selection_Status', 'Shared reviewed component reused; application and assembly validation remain pending.')
            if ref in CAP_REFS:
                set_property(inst, 'Voltage_Rating', '50V')
                set_property(inst, 'Tolerance', '10%')
                set_property(inst, 'Dielectric', 'X7R')
            if ref in SWITCH_REFS:
                set_property(inst, 'Assembly_Side', 'Top')
                set_property(inst, 'Design_Note',
                             'RESET/BOOT: controller TOP, same face as MCU, actuator faces UP. '
                             'Near board edge; reach from stack side and press DOWN. '
                             'Allow holding BOOT while operating RESET; clearance needs PCB/structure review.')
            # Reserved filter metadata belongs in lib_symbols, not instance user
            # fields (KiCad 10 PCB parity cannot preserve this reserved property).
            for prop in list(children(inst, 'property')):
                if str(prop[1]) == 'ki_fp_filters':
                    inst.remove(prop)
            migration.append({
                'ref': ref, 'page': path.name, 'supplier_pn': c,
                'before_symbol': old_id, 'after_symbol': new_id,
                'before_footprint': p['Footprint'], 'after_footprint': row['Footprint'],
                'before_mpn': p.get('MPN'), 'after_mpn': row['MPN'],
                'physical_pin_numbers': sorted(old_pins, key=lambda x: int(x)),
                'pin_coordinates_identical': True,
                'pin_semantic_changes': {n: [old_pins[n], new_pins[n]] for n in old_pins
                                         if old_pins[n] != new_pins[n]},
            })
        if replacements:
            for old in list(children(lib_container, 'symbol')):
                if str(old[1]) in replacements:
                    lib_container.remove(old)
            lib_container.extend(replacements.values())
            used = {str(child(x, 'lib_id')[1]) for x in children(data, 'symbol')}
            for old in list(children(lib_container, 'symbol')):
                if str(old[1]) not in used:
                    lib_container.remove(old)
            if path.name == 'mcu_control.kicad_sch':
                note = ('SW2 / SW3: TS-1101-C-W (C318938), controller TOP face, actuator UP; near board edge.\n'
                        'Reach from stack side and press DOWN; allow holding BOOT while operating RESET.\n'
                        'Keep clear of headers, supports and wiring. Stack access needs PCB / structure review.')
                data.append([sx.Symbol('text'), note, [sx.Symbol('at'), 20.32, 111.76, 0],
                             [sx.Symbol('effects'), [sx.Symbol('font'), [sx.Symbol('size'), 1.05, 1.05]],
                              [sx.Symbol('justify'), sx.Symbol('left'), sx.Symbol('top')]],
                             [sx.Symbol('uuid'), str(uuid.uuid5(uuid.NAMESPACE_URL,
                                                              'power_system/core/shared_buttons/2026-11-11'))]])
        after_geometry = [x for x in data if isinstance(x, list) and str(x[0]) in
                          {'wire', 'junction', 'no_connect', 'label', 'global_label', 'hierarchical_label'}]
        assert before_geometry == after_geometry, path
        if replacements:
            title = child(data, 'title_block')
            for entry in children(title, 'comment'):
                if entry[1] == 2 and str(entry[2]).startswith('INVERTER |'):
                    entry[2] = 'CONTROLLER | 4.75-5.25 V header input | common-ground minimum core'
            write(path, data)
    assert len(migration) == 20, len(migration)
    after = instance_records(active_pages())
    assert before.keys() == after.keys()
    for ref in before:
        for key in ('at', 'unit', 'uuid', 'dnp'):
            assert before[ref][key] == after[ref][key], (ref, key)
        assert before[ref]['properties']['Value'] == after[ref]['properties']['Value'], ref
    dump_json(MANIFEST, {
        'revision': 'E-minimum-core-draft', 'date': '2026-11-11',
        'archive': str(archive), 'archive_sha256': sha(archive),
        'shared_catalogue_sha256': sha(SHARED / 'parts.csv'),
        'shared_symbols_sha256': sha(SHARED / 'symbols/MyParts.kicad_sym'),
        'baseline_xml': str(BEFORE_XML), 'baseline_xml_sha256': sha(BEFORE_XML),
        'before_instances': before, 'after_instances': after,
        'adopted_references': migration,
        'unchanged_graphics': 'All wires, labels, junctions and NC markers retained exactly. Shared pin coordinate equality checked first.',
        'old_script_compatibility': {
            'tools/migrate_core.py': 'Historical Rev C to Rev D authoring snapshot; not executed.',
            'tools/verify_migrated_core.py': 'Hardcodes 97 refs, old five-page subset, old NC/LED/ADC assumptions; not current Rev E.',
            'tools/build_core_supply.py': 'Historical power-page authoring snapshot; not executed.',
            'inverter/hardware/tools/verify_minimum_core.py': 'Current architecture checks useful, but compares old Value/Footprint exactly and writes CSV; root will adapt system verifier. Not executed by this migration.',
        },
        'allowed_procurement_changes': ['SW2/SW3 use TS-1101-C-W/C318938',
                                        'C304/C306/C307/C308 use 100nF 50V X7R 0603 C14663',
                                        'All existing exact C-number parts use reviewed shared symbols and dedicated footprints'],
        'remaining_TBD_references': sorted(ref for ref, r in after.items() if r['properties'].get('MPN') == 'TBD'),
        'limits': ['No PCB placement or mechanical mating validation.', 'No dynamic/thermal/prototype validation.',
                   'Baseline circuit Values, physical pins and DNP are unchanged.'],
    })
    export_xml(AFTER_XML)
    print('Migrated 20 exact-part references. Backup:', archive)


def load_netlist(path):
    root = ET.parse(path).getroot()
    comps = {x.get('ref'): x for x in root.findall('./components/comp')}
    pin_net = {}
    groups = set()
    for net in root.findall('./nets/net'):
        nodes = frozenset((n.get('ref'), n.get('pin')) for n in net.findall('node'))
        groups.add(nodes)
        for node in nodes:
            assert node not in pin_net
            pin_net[node] = net.get('name')
    return comps, pin_net, groups


def verify():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    before, bp, bg = load_netlist(BEFORE_XML)
    after, ap, ag = load_netlist(AFTER_XML)
    assert before.keys() == after.keys() and len(after) == 47
    assert bp.keys() == ap.keys(), ('Physical pin set mismatch', set(bp) - set(ap), set(ap) - set(bp))
    assert bg == ag, ('Physical connectivity partitions differ', bg - ag, ag - bg)
    mismatches = [{'ref': r, 'pin': p, 'before': n, 'after': ap[(r, p)]}
                  for (r, p), n in bp.items() if n != ap[(r, p)]]
    assert not mismatches, mismatches
    expected = {r['ref']: r for r in manifest['adopted_references']}
    for ref, actual in after.items():
        assert actual.findtext('value') == before[ref].findtext('value'), ref
        assert (actual.find("property[@name='dnp']") is not None) == (before[ref].find("property[@name='dnp']") is not None), ref
        if ref in expected:
            assert actual.findtext('footprint') == expected[ref]['after_footprint'], ref
            ls = actual.find('libsource')
            assert ls.get('lib') + ':' + ls.get('part') == expected[ref]['after_symbol'], ref
        else:
            assert actual.findtext('footprint') == before[ref].findtext('footprint'), ref
    dnp = sorted(r for r, c in after.items() if c.find("property[@name='dnp']") is not None)
    assert dnp == ['C83', 'C84', 'Y1']
    contract = json.loads((REPO / 'docs/daughterboard_pin_contract.json').read_text(encoding='utf-8'))
    checks = []
    for ref in ('J101', 'J102'):
        for pin, want in contract[ref].items():
            want = contract['supply_alias'].get(want, {}).get('controller', want)
            assert ap[(ref, pin)].rsplit('/', 1)[-1] == want, (ref, pin, ap[(ref, pin)], want)
            checks.append([ref, int(pin), want])
    exposed = [row for rows in contract['pins'].values() for row in rows if row['kind'] == 'mcu_signal']
    assert len(exposed) == 52
    for row in exposed:
        assert ap[('U30', str(row['mcu_pad']))].rsplit('/', 1)[-1] == row['net'], row
    assert len([p for r, p in ap if r == 'U30']) == 64
    report = {
        'result': 'PASS', 'revision': 'E-minimum-core-draft',
        'physical_references': len(after), 'active_pages': 7,
        'physical_pin_nodes_compared': len(ap), 'pin_net_mismatches': [],
        'physical_connectivity_partition_equal': True,
        'DNP_refs': dnp, 'adopted_references': len(expected),
        'header_contacts_checked': checks, 'mcu_package_pins_checked': 64,
        'mcu_signal_pads_exposed': 52, 'wires_labels_junctions_NC_unchanged': True,
        'after_xml_sha256': sha(AFTER_XML),
        'remaining_TBD_references': manifest['remaining_TBD_references'],
        'limits': ['Core-only current-baseline equivalence. Root owns combined base/core truth-table and system validation.',
                   'ERC and final visual QA recorded separately.'],
    }
    dump_json(REVIEW / 'pin_equivalence.json', report)
    print('PASS:', len(after), 'references,', len(ap), 'physical pin nodes, 64 contacts and 52 signal pads.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.apply:
        apply()
    if args.verify:
        verify()
    if not (args.apply or args.verify):
        parser.error('Choose --apply and/or --verify')

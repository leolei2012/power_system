"""One revision-specific, pin-preserving library migration of the Rev E base.

Reads the immutable active-sheet backup. Never runs historical generators and
never modifies the shared library, controller, PCB, project rules, or BOM.
Usage: python tools/migrate_shared_parts_2026_11_11.py --apply
"""
from pathlib import Path
from zipfile import ZipFile
import argparse
import collections
import copy
import csv
import hashlib
import json
import math
import re
import uuid
import xml.etree.ElementTree as ET
import sexpdata as sx

BASE = Path(__file__).resolve().parents[1]
LIB = BASE.parents[2] / 'kicad_library'
BACKUP = BASE / 'history/rev_e_before_shared_parts_2026-11-11_000310.zip'
REVIEW = BASE / 'review/shared_parts_2026-11-11'


def tag(v, name):
    return isinstance(v, list) and v and str(v[0]) == name


def children(v, name):
    return [x for x in v if tag(x, name)]


def child(v, name):
    return next(iter(children(v, name)), None)


def props(v):
    return {p[1]: p[2] for p in children(v, 'property')}


def native_text(v):
    # A newline per top-level object preserves readable native files without
    # reinterpreting or flattening any electrical object.
    return '(' + str(v[0]) + '\n' + '\n'.join(sx.dumps(x) for x in v[1:]) + ')\n'


def pins(lib, unit):
    return {str(child(p, 'number')[1]): tuple(child(p, 'at')[1:])
            for s in children(lib, 'symbol')
            if int(s[1].rsplit('_', 2)[1]) in (0, unit)
            for p in children(s, 'pin')}


def pin_xy(inst, lib):
    x, y, a = child(inst, 'at')[1:]
    mirror = child(inst, 'mirror')
    out = {}
    for n, (px, py, _) in pins(lib, int(child(inst, 'unit')[1])).items():
        if mirror:
            if str(mirror[1]) == 'x':
                py = -py
            if str(mirror[1]) == 'y':
                px = -px
        rad = math.radians(a)
        out[n] = (round(x + px*math.cos(rad) - py*math.sin(rad), 5),
                  round(y - px*math.sin(rad) - py*math.cos(rad), 5))
    return out


def set_prop(inst, name, value):
    old = next((x for x in children(inst, 'property') if x[1] == name), None)
    if old:
        old[2] = str(value)
    else:
        x, y = child(inst, 'at')[1:3]
        inst.append(sx.loads(f'(property {json.dumps(name)} {json.dumps(str(value))} '
                            f'(at {x} {y} 0) (hide yes) '
                            '(effects (font (size 0.9 0.9))))'))


def wire(a, b, token):
    assert a[0] == b[0] or a[1] == b[1], (a, b)
    ident = uuid.uuid5(uuid.NAMESPACE_URL, 'power_system/shared_parts_2026_11_11/' + token)
    return sx.loads(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) '
                    f'(stroke (width 0) (type default)) (uuid "{ident}"))')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    catalog = list(csv.DictReader((LIB/'parts.csv').open(encoding='utf-8-sig', newline='')))
    by_code = {p['Supplier_PN']: p for p in catalog}
    shared = sx.load((LIB/'symbols/MyParts.kicad_sym').open(encoding='utf-8'))
    definitions = {x[1]: x for x in children(shared, 'symbol')}
    z = ZipFile(BACKUP)
    source_hashes = json.loads(z.read('snapshot_manifest.json'))
    last_report = REVIEW/'migration.json'
    previous_result = json.loads(last_report.read_text(encoding='utf-8')).get('result_sha256', {}) if last_report.exists() else {}
    top = sx.loads(z.read('inverter.kicad_sch').decode('utf-8-sig'))
    files = ['inverter.kicad_sch'] + [props(s)['Sheetfile'] for s in children(top, 'sheet')]
    assert len(files) == 20
    before = ET.parse(REVIEW/'before.net.xml').getroot()
    before_components = {c.attrib['ref']: c for c in before.findall('./components/comp')}
    assert len(before_components) == 317
    before_nets = {(x.attrib['ref'], x.attrib['pin']): n.attrib['name']
                   for n in before.findall('./nets/net') for x in n.findall('node')}
    changes = []
    cad_files = []
    outputs = {}
    cap_refs = []
    # Metadata only: preserving already-established domestic URLs takes priority
    # over older international URLs present in a reviewed library record.
    sync_keys = ['MPN', 'Manufacturer', 'Supplier', 'Supplier_PN', 'Verification',
                 'Library_Revision', 'Datasheet_Revision', 'ki_keywords', 'ki_fp_filters']
    for fn in files:
        data = sx.loads(z.read(fn).decode('utf-8-sig'))
        lib_node = child(data, 'lib_symbols')
        libmap = {x[1]: x for x in children(lib_node, 'symbol')}
        touched = False
        for inst in children(data, 'symbol'):
            fields = props(inst)
            ref = fields['Reference']
            row = by_code.get(fields.get('Supplier_PN'))
            selected_cap = (fields.get('Value') == '100n'
                            and fields.get('Footprint') == 'Capacitor_SMD:C_0603_1608Metric'
                            and fields.get('MPN', 'TBD') == 'TBD')
            if selected_cap:
                assert fields.get('Voltage_Rating') == '25V', fields
                row = by_code['C14663']
                cap_refs.append(ref)
            if not row:
                continue
            assert row['Verification'] == 'reviewed', row['MPN']
            old_id = child(inst, 'lib_id')[1]
            new_id = row['Symbol']
            new_lib = copy.deepcopy(definitions[new_id.split(':', 1)[1]])
            assert child(new_lib, 'extends') is None
            new_lib[1] = new_id
            old_lib = libmap[old_id]
            unit = int(child(inst, 'unit')[1])
            old_pins = pins(old_lib, unit)
            new_pins = pins(new_lib, unit)
            assert old_pins.keys() == new_pins.keys(), (ref, old_pins, new_pins)
            old_at = copy.deepcopy(child(inst, 'at')[1:])
            before_xy = pin_xy(inst, old_lib)
            if old_pins != new_pins:
                # Only the dual common-cathode symbol changes electrical drawing
                # geometry. K goes right; the two anodes remain explicitly joined.
                assert ref == 'D1', (ref, old_pins, new_pins)
                child(inst, 'at')[3] = 90
            after_xy = pin_xy(inst, new_lib)
            if ref != 'D1':
                assert before_xy == after_xy, (ref, before_xy, after_xy)
            if ref.startswith('Q') and ref != 'Q8':
                assert ref in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7']
                assert set(new_pins) == set('12345678')
                assert len({before_nets[ref, n] for n in '123'}) == 1
                assert len({before_nets[ref, n] for n in '5678'}) == 1
                fp = sx.load((LIB/'footprints/MyFootprints.pretty'/
                              (row['Footprint'].split(':', 1)[1]+'.kicad_mod')).open(encoding='utf-8'))
                assert {str(p[1]) for p in children(fp, 'pad') if p[1]} == set('12345678')
            if new_id not in libmap:
                lib_node.append(new_lib)
                libmap[new_id] = new_lib
            else:
                idx = lib_node.index(libmap[new_id])
                lib_node[idx] = new_lib
                libmap[new_id] = new_lib
            child(inst, 'lib_id')[1] = new_id
            source_fields = props(new_lib)
            for key in sync_keys:
                if key in source_fields:
                    set_prop(inst, key, source_fields[key])
            set_prop(inst, 'Footprint', row['Footprint'])
            set_prop(inst, 'Datasheet', row['Datasheet_URL'])
            set_prop(inst, 'Description', row['Description'])
            prior_url = fields.get('Purchase_URL', '')
            purchase = row['Purchase_URL']
            if 'item.szlcsc.com/' in prior_url and 'item.szlcsc.com/' not in purchase:
                purchase = prior_url
            if row['Supplier_PN'] == 'C1850289':
                # Root verified this exact official LCSC productId/model mapping;
                # the domestic page body is restricted and stock is not claimed.
                purchase = 'https://item.szlcsc.com/1941102.html'
                set_prop(inst, 'Purchase_URL_Verification', 'Official LCSC productId1941102 / C1850289 / exact MPN mapping; domestic page body restricted; inventory not verified')
            if row['Supplier_PN'] == 'C14663':
                purchase = 'https://item.szlcsc.com/15331.html'
            if row['Supplier_PN'] == 'C2903482':
                purchase = 'https://so.szlcsc.com/global.html?k=C2903482'
                set_prop(inst, 'Purchase_URL_Verification', 'Exact supplier code retained; domestic product detail URL pending verification; search link is not inventory evidence')
            set_prop(inst, 'Purchase_URL', purchase)
            set_prop(inst, 'Application_Verification', 'Unverified; reviewed applies to library definition only')
            if selected_cap:
                set_prop(inst, 'Voltage_Rating', '50V')
                set_prop(inst, 'Tolerance', '10%')
                set_prop(inst, 'Dielectric', 'X7R')
                set_prop(inst, 'Selection_Status', 'C14663; 50V X7R covers original 25V local decoupling/bootstrap requirement; application transient and DC-bias verification pending')
            if ref == 'D1':
                for p in children(inst, 'property'):
                    if p[1] in ['Reference', 'Value']:
                        child(p, 'at')[1:] = [132.08, 36.83 if p[1] == 'Reference' else 39.37, 90]
            touched = True
            changes.append({'ref': ref, 'unit': unit, 'sheet': fn, 'old_symbol': old_id,
                            'new_symbol': new_id, 'old_footprint': fields.get('Footprint'),
                            'new_footprint': row['Footprint'], 'code': row['Supplier_PN'],
                            'old_at': old_at, 'new_at': child(inst, 'at')[1:],
                            'old_pin_xy': before_xy, 'new_pin_xy': after_xy})
        if fn == 'bus_brake.kicad_sch':
            remove = {'04211aca-fe48-54cf-8788-a1fa23e62036',
                      '324cb74a-43ee-54c3-82a3-dab84e959d53',
                      'ade9ce56-68d7-5d76-89bf-81b46ab3f6c5',
                      '2cb200e9-8aba-51f8-b0c8-1a502b3987b3'}
            found = [x for x in data if isinstance(x, list) and child(x, 'uuid')
                     and child(x, 'uuid')[1] in remove]
            assert len(found) == len(remove)
            for x in found:
                data.remove(x)
            paths = [((116.84,55.88),(116.84,48.26)),
                     ((116.84,48.26),(132.08,48.26)),
                     ((116.84,55.88),(116.84,63.5)),
                     ((116.84,63.5),(132.08,63.5)),
                     ((137.16,55.88),(157.48,55.88))]
            data.extend(wire(a, b, 'D1/'+str(i)) for i, (a,b) in enumerate(paths))
        if touched:
            used = {child(i, 'lib_id')[1] for i in children(data, 'symbol')}
            # Historical unused embedded definitions are removed only from the
            # active sheet cache, never from a library or historical .sch file.
            lib_node[:] = lib_node[:1] + [s for s in children(lib_node, 'symbol') if s[1] in used]
            text = native_text(data)
            cad_files.append(fn)
            current_hash = hashlib.sha256((BASE/fn).read_bytes()).hexdigest()
            assert current_hash in [source_hashes[fn], previous_result.get(fn)], ('Source changed after this migration snapshot', fn)
            outputs[fn] = text
    assert len(set(cap_refs)) == 17, cap_refs
    report = {'source_backup': str(BACKUP.resolve()), 'modified_files': cad_files,
              'updated_instances': len(changes), 'updated_refs': len({x['ref'] for x in changes}),
              'selected_100n_0603_refs': cap_refs,
              'missing_selection': 'Remaining TBD resistors, capacitors and five LEDs unchanged.',
              'shared_parts_csv_sha256': hashlib.sha256((LIB/'parts.csv').read_bytes()).hexdigest(),
              'shared_symbols_sha256': hashlib.sha256((LIB/'symbols/MyParts.kicad_sym').read_bytes()).hexdigest(),
              'changes': changes}
    REVIEW.mkdir(exist_ok=True)
    if args.apply:
        for fn, text in outputs.items():
            (BASE/fn).write_text(text, encoding='utf-8')
        report['result_sha256'] = {f: hashlib.sha256((BASE/f).read_bytes()).hexdigest() for f in cad_files}
        (REVIEW/'migration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['changes','result_sha256']},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

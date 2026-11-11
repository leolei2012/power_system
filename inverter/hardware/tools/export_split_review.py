"""Export review records from the two current Rev E KiCad XML netlists.

This does not author circuits, change shared libraries or release manufacturing
data. Historical integrated-board records remain in the immutable Rev C ZIP.
"""
from pathlib import Path
from collections import Counter
import csv
import argparse
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
import sexpdata as sx

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[1]
CORE = REPO / 'controller/hardware/g431_core'
LIBRARY = REPO.parent / 'kicad_library'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--date', default='2026-11-11')
parser.add_argument('--revision', default='E-shared-library-draft')
args = parser.parse_args()


def child(node, key):
    return next((v for v in node if isinstance(v, list) and v and str(v[0]) == key), None)


def children(node, key):
    return [v for v in node if isinstance(v, list) and v and str(v[0]) == key]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def native_pages(root):
    pages = []
    def visit(path, sheet_path='/'):
        data = sx.loads(path.read_text(encoding='utf-8'))
        title = child(child(data, 'title_block'), 'title')[1]
        pages.append({'file': str(path.relative_to(root.parent)), 'title': title,
                      'sheet_path': sheet_path, 'sha256': digest(path)})
        for sheet in children(data, 'sheet'):
            props = {p[1]: p[2] for p in children(sheet, 'property')}
            visit(path.parent / props['Sheetfile'], sheet_path + props['Sheetname'] + '/')
    visit(root)
    return pages


with (LIBRARY / 'parts.csv').open(encoding='utf-8-sig', newline='') as f:
    public_rows = list(csv.DictReader(f))
    public = {r['MPN']: r for r in public_rows}
    public_codes = {r['Supplier_PN']: r for r in public_rows}


def procurement_part(row):
    return not row['Reference'].startswith('TP') and row['MPN'] != 'PCB solder holes / wire assembly'

columns = ['Reference', 'Value', 'Quantity', 'DNP', 'Sheet', 'Manufacturer', 'MPN',
           'Supplier_PN', 'Purchase_URL', 'Footprint', 'Voltage_Rating', 'Tolerance',
           'Design_Note', 'Selection_Status', 'Verification']
summary = {}
for board, name, xml, erc in [
    (CORE, 'controller', CORE / 'review/controller.net.xml', CORE / 'review/erc.json'),
    (BASE, 'inverter', BASE / 'review/inverter.net.xml', BASE / 'review/erc.json'),
]:
    root = ET.parse(xml).getroot()
    rows = []
    for comp in root.findall('./components/comp'):
        fields = {f.attrib['name']: f.text or '' for f in comp.findall('./fields/field')}
        props = {p.attrib['name']: p.attrib.get('value', '') for p in comp.findall('property')}
        row = {c: fields.get(c, '') for c in columns}
        row.update(Reference=comp.attrib['ref'], Value=comp.findtext('value'), Quantity=1,
                   DNP='yes' if 'dnp' in props else 'no',
                   Sheet=comp.find('sheetpath').attrib['names'],
                   Footprint=comp.findtext('footprint') or '')
        rows.append(row)
    for path in [board / 'bom/bom.csv', board / 'review/bom.csv']:
        write_csv(path, rows, columns)

    pending = [r for r in rows if procurement_part(r) and (not r['MPN'] or 'TBD' in r['MPN'].upper())]
    write_csv(board / 'bom/selection_pending.csv', pending, columns)
    intake = []
    grouped = {}
    for row in rows:
        if not procurement_part(row):
            continue
        mpn = row['MPN']
        if not mpn or 'TBD' in mpn.upper() or mpn.upper() in ['N/A', 'NONE', 'NOT APPLICABLE']:
            continue
        existing = public_codes.get(row['Supplier_PN']) or public.get(mpn)
        if existing and existing['Verification'] in ['reviewed', 'prototype_verified']:
            continue
        grouped.setdefault((row['Manufacturer'], mpn, row['Supplier_PN'], row['Footprint']), []).append(row)
    for (maker, mpn, code, footprint), group in sorted(grouped.items()):
        intake.append({'Manufacturer': maker, 'MPN': mpn, 'Supplier_PN': code,
                       'Purchase_URL': group[0]['Purchase_URL'], 'Footprint': footprint,
                       'References': ' '.join(r['Reference'] for r in group),
                       'DNP_Count': sum(r['DNP'] == 'yes' for r in group),
                       'Status': 'project candidate; shared-library intake pending'})
    write_csv(board / 'bom/library_intake.csv', intake,
              ['Manufacturer', 'MPN', 'Supplier_PN', 'Purchase_URL', 'Footprint',
               'References', 'DNP_Count', 'Status'])

    erc_data = json.loads(erc.read_text(encoding='utf-8'))
    severities = Counter(v['severity'] for s in erc_data['sheets'] for v in s['violations'])
    assert not severities, severities
    pages = native_pages(board / (name + '.kicad_sch'))
    sources = [board / (name + '.kicad_pro'), board / 'sym-lib-table', board / 'fp-lib-table']
    sources += sorted(board.glob('*.kicad_sym'))
    sources += sorted(board.glob('*.kicad_dru'))
    sources += sorted((board / 'Inverter_Compact.pretty').glob('*.kicad_mod'))
    pcb = board / (name + '.kicad_pcb')
    manifest = {
        'revision': args.revision, 'date': args.date,
        'board_role': 'STM32G431 minimum-system plug-in core' if board == CORE else 'Inverter application and power baseboard',
        'native_project': name + '.kicad_pro', 'native_schematic': name + '.kicad_sch',
        'pcb_status': ('Rev E PCB 0.1 layout review draft; routing/DRC progress is recorded separately. Not released for manufacture.'
                       if pcb.exists() else 'Not designed for this revision; old integrated PCB archived separately.'),
        'component_count': len(rows), 'DNP_count': sum(r['DNP'] == 'yes' for r in rows),
        'pages': pages, 'page_count': len(pages),
        'erc': {'errors': 0, 'warnings': 0, 'date': erc_data['date'],
                'kicad_version': erc_data['kicad_version'], 'ignored_checks': erc_data['ignored_checks']},
        'netlist': {'file': str(xml.relative_to(board)), 'sha256': digest(xml)},
        'project_sources': {str(p.relative_to(board)): digest(p) for p in sources},
        'shared_library_sha256': {'parts.csv': digest(LIBRARY / 'parts.csv'),
                                  'symbols/MyParts.kicad_sym': digest(LIBRARY / 'symbols/MyParts.kicad_sym')},
        'selection_pending_references': len(pending), 'library_intake_candidate_models': len(intake),
        'manufacturing_release': False,
        'limits': ['Schematic connection checks and PCB layout review are separate; no assembly or prototype qualification.',
                   'Common-ground non-isolated interface; clamps do not guarantee MCU survival after a power-stage failure.',
                   'Exact passive MPNs, mating connector mechanics, transient behavior and thermal performance require completion.'],
    }
    if pcb.exists():
        manifest['pcb'] = {'file': pcb.name, 'sha256': digest(pcb),
                           'stack_contract': '../../docs/pcb_stack_contract_rev_e.json' if board == BASE
                           else '../../../docs/pcb_stack_contract_rev_e.json',
                           'review': '../../../docs/pcb_review_2026-11-11.md' if board == CORE
                           else '../../docs/pcb_review_2026-11-11.md',
                           'manufacturing_release': False}
    (board / 'review/design_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary[name] = {k: manifest[k] for k in ['component_count', 'DNP_count', 'page_count',
                                            'selection_pending_references', 'library_intake_candidate_models']}

# Conventional entry points above already name the current baseboard exports.
system = json.loads((CORE / 'review/system_check.json').read_text(encoding='utf-8'))
(BASE / 'review/connectivity_check.json').write_text(json.dumps(system, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))

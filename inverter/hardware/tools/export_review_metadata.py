"""Regenerate review BOM from the current KiCad XML export (never draw circuits)."""
from pathlib import Path
import csv
import hashlib
import json
import xml.etree.ElementTree as ET

B=Path(__file__).resolve().parents[1]
tree=ET.parse(B/'review/inverter.net.xml').getroot()
cols=['Reference','Value','Quantity','DNP','Sheet','Manufacturer','MPN','Supplier_PN','Purchase_URL',
      'Footprint','Voltage_Rating','Tolerance','Design_Note','Selection_Status']
rows=[]
for comp in tree.findall('./components/comp'):
    fields={v.attrib['name']:v.text or '' for v in comp.findall('./fields/field')}
    properties={v.attrib['name']:v.attrib.get('value','') for v in comp.findall('property')}
    row={k:fields.get(k,'') for k in cols}
    sheet=comp.find('sheetpath').attrib['names'].strip('/')
    row.update(Reference=comp.attrib['ref'],Value=comp.findtext('value'),Quantity=1,
               DNP='yes' if 'dnp' in properties else 'no',Sheet=sheet,
               Footprint=comp.findtext('footprint') or '')
    rows.append(row)
for file in [B/'review/bom.csv',B/'bom/bom.csv']:
    with file.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
manifest=json.loads((B/'review/design_manifest.json').read_text(encoding='utf-8'))
manifest['component_count']=len(rows)
(B/'review/design_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
files=[B/'InverterLocal.kicad_sym',B.parents[2]/'kicad_library/symbols/MyParts.kicad_sym',
       Path('C:/Program Files/KiCad/10.0/share/kicad/symbols/MCU_ST_STM32G4.kicad_sym')]
sources=json.loads((B/'review/library_sources.json').read_text(encoding='utf-8'))
for file in files:sources[file.as_posix()]={'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
(B/'review/library_sources.json').write_text(json.dumps(sources,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'components':len(rows),'DNP':[r['Reference'] for r in rows if r['DNP']=='yes']},ensure_ascii=False))

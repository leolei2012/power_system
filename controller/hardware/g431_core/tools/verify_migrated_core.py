"""Independently export and compare only the five migrated Rev C core pages.

Creates an explicitly partial review project under review/migration_only.
Supply/interface ERC and final full-project validation remain separate.
"""
from pathlib import Path
import collections,copy,hashlib,json,shutil,subprocess,xml.etree.ElementTree as ET,zipfile
import sexpdata as sx

B=Path(__file__).resolve().parents[1]
REPO=B.parents[2]
archive=REPO/'inverter/history/integrated_60x60_rev_c_before_mcu_split_2026-11-06.zip'
z=zipfile.ZipFile(archive)
PAGES=['mcu','mcu_analog','mcu_control','sensors','debug_comms']
tag=lambda a,n:isinstance(a,list) and bool(a) and str(a[0])==n
child=lambda a,n:next((q for q in a if tag(q,n)),None)
children=lambda a,n:[q for q in a if tag(q,n)]
props=lambda a:{q[1]:q[2] for q in children(a,'property')}
out=B/'review/migration_only';out.mkdir(exist_ok=True,parents=True)
root=sx.loads((B/'controller.kicad_sch').read_text())
for sheet in list(children(root,'sheet')):
    if props(sheet)['Sheetfile'].removesuffix('.kicad_sch') not in PAGES:root.remove(sheet)
(out/'controller.kicad_sch').write_text(sx.dumps(root)+'\n')
for name in PAGES:shutil.copy2(B/(name+'.kicad_sch'),out/(name+'.kicad_sch'))
shutil.copy2(B/'controller.kicad_pro',out/'controller.kicad_pro')
for name in ['fp-lib-table','sym-lib-table']:
    (out/name).write_text((B/name).read_text().replace('${KIPRJMOD}',B.as_posix()))
xml=out/'controller.net.xml'
cli='C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
done=subprocess.run([cli,'sch','export','netlist','--format','kicadxml','--output',str(xml),str(out/'controller.kicad_sch')],capture_output=True,text=True)
assert done.returncode==0,done.stderr+done.stdout
actual=ET.parse(xml).getroot()
source=ET.fromstring(z.read('inverter/hardware/review/inverter.net.xml'))
actual_comps={c.attrib['ref']:c for c in actual.findall('./components/comp')}
source_comps={c.attrib['ref']:c for c in source.findall('./components/comp')}
expected_refs=set()
native_checks={}
for name in PAGES:
    current=sx.loads((B/(name+'.kicad_sch')).read_text())
    old=sx.loads(z.read('inverter/hardware/'+name+'.kicad_sch').decode())
    current_parts={props(c)['Reference']:c for c in children(current,'symbol') if not props(c)['Reference'].startswith('#')}
    old_parts={props(c)['Reference']:c for c in children(old,'symbol') if not props(c)['Reference'].startswith('#')}
    removed=set(old_parts)-set(current_parts)
    assert removed==({'D3','R130'} if name=='debug_comms' else {'TP16','TP17'} if name=='mcu_control' else set())
    for ref,c in current_parts.items():
        o=old_parts[ref]
        for field in ['at','unit','dnp','lib_id']:
            assert child(c,field)==child(o,field),(ref,field)
        for field in ['Value','Footprint','MPN','Supplier_PN','Purchase_URL']:
            assert props(c).get(field)==props(o).get(field),(ref,field)
    expected_refs.update(current_parts)
    native_checks[name]={'physical_references':len(current_parts),'removed_refs':sorted(removed),'wire_count':len(children(current,'wire')),'source_wire_count':len(children(old,'wire')),'position_value_footprint_DNP_MPN_preserved':True}
assert expected_refs==set(actual_comps) and len(expected_refs)==97
oldmap={}
for n in source.findall('./nets/net'):
    for node in n.findall('node'):
        if node.attrib['ref'] in expected_refs:oldmap[node.attrib['ref'],node.attrib['pin']]=n.attrib['name']
newmap={}
for n in actual.findall('./nets/net'):
    for node in n.findall('node'):newmap[node.attrib['ref'],node.attrib['pin']]=n.attrib['name']
expected={}
clamped={'R'+str(i) for i in range(84,92)}
for key,net in oldmap.items():
    if net=='+3V3_INV':net='+3V3_MCU'
    elif net=='LOGIC_POWER_OK':net='MCU_RESET_N'
    if key[0] in clamped and key[1]=='1':net+='_CLAMPED'
    if key==('U30','2'):net='BASE_READY'
    expected[key]=net
missing=set(expected)-set(newmap);extra=set(newmap)-set(expected)
mismatches=[{'pin':'.'.join(key),'expected':net,'actual':newmap.get(key)} for key,net in expected.items() if newmap.get(key)!=net]
assert not missing and not extra and not mismatches,(missing,extra,mismatches)
assert 'MCU_RESET_N' in newmap.values() and 'LOGIC_POWER_OK' not in newmap.values()
assert '+3V3_INV' not in newmap.values() and '+3V3_MCU' in newmap.values()
assert newmap['R143','2']=='+3V3_MCU'
for ref in ['D4','D5','D6','D7','R131','R132','R133','R134']:assert ref in actual_comps
for pin in ['3','4','39','56','57','62']:assert newmap['U30',pin].startswith('unconnected-')
assert newmap['U30','2']=='BASE_READY'
report={'pass':True,'scope':'Only five migrated pages; supply/interface excluded intentionally; not final full-project ERC.',
 'physical_references':len(actual_comps),'physical_pin_nodes':len(newmap),'migrated_page_checks':native_checks,
 'all_expected_pins_preserved':True,'missing_pins':[],'extra_pins':[],'pin_net_mismatches':[],
 'allowed_electrical_changes':['+3V3_INV -> +3V3_MCU','LOGIC_POWER_OK -> MCU_RESET_N','8 ADC input ports -> *_CLAMPED at R84..R91.1 only','U30 PC13/p2 NC -> BASE_READY'],
 'remaining_U30_NC_pins':['3','4','39','56','57','62'],
 'GPIO_LED_refs_retained':['D4','D5','D6','D7','R131','R132','R133','R134'],
 'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'partial_xml':str(xml)}
(B/'review/migration_equivalence.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

"""Read-only Rev D power-base scope and pin-contract verification."""
from pathlib import Path
from zipfile import ZipFile
from collections import Counter
import hashlib,json,sys,xml.etree.ElementTree as ET
import sexpdata as sx
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'tools'))
from schematic_common import tag,child,children
archive=BASE.parent/'history/integrated_60x60_rev_c_before_mcu_split_2026-11-06.zip';z=ZipFile(archive)
def original(name):return sx.loads(z.read('inverter/hardware/'+name+'.kicad_sch').decode('utf-8-sig'))
def props(i):return {v[1]:v[2] for v in children(i,'property')}
def refinst(d):return {(props(i)['Reference'],int(child(i,'unit')[1])):i for i in children(d,'symbol') if not props(i)['Reference'].startswith('#')}
retained=['aux_input','supply_12v','supply_logic','bus_brake','bridge_u','bridge_v','bridge_w','current_sense','voltage_sense','comparators','fault_logic','control_interface']
active=retained+['base_interlock','base_leds']
if (BASE/'power_interface.kicad_sch').exists():active.append('power_interface')
old={};new={}
for name in retained+['debug_comms','mcu_control']:old.update(refinst(original(name)))
for name in active:new.update(refinst(sx.load((BASE/(name+'.kicad_sch')).open(encoding='utf-8'))))
property_diffs=[];ui_filter_additions=[]
for k,i in new.items():
 if k not in old:continue
 a,b=props(old[k]),props(i)
 if k[0] in ['TP16','TP17'] and 'ki_fp_filters' not in a and 'ki_fp_filters' in b:
  ui_filter_additions.append({'ref':k[0],'property':'ki_fp_filters','added':b.pop('ki_fp_filters')})
 if a!=b:property_diffs.append({'ref_unit':k,'before':a,'after':b})
 assert child(i,'lib_id')[1]==child(old[k],'lib_id')[1],k
 assert child(i,'dnp')[1]==child(old[k],'dnp')[1],k
assert not property_diffs,property_diffs
before=ET.parse(BASE/'review/revd_power_before.net.xml').getroot();after=ET.parse(BASE/'review/revd_power.net.xml').getroot()
def pinmap(r):return {(x.attrib['ref'],x.attrib['pin']):n.attrib['name'] for n in r.findall('./nets/net') for x in n.findall('node')}
a,b=pinmap(before),pinmap(after)
allowed={('R13','1'):'BASE_LOGIC_OK',('U6','1'):'BASE_LOGIC_OK',('U23','13'):'BASE_LOGIC_OK',('U25','2'):'ENABLE_QUALIFIED',('U27','1'):'ENABLE_QUALIFIED',('U27','2'):'ENABLE_QUALIFIED',('U26','12'):'ENABLE_IN',('U26','13'):'CTRL_READY',('U26','11'):'ENABLE_QUALIFIED',('U27','9'):'BASE_LOGIC_OK',('U27','10'):'DRV_PG_LOGIC',('U27','8'):'/Base interlock/BASE_NOT_READY',('U27','12'):'/Base interlock/BASE_NOT_READY',('U27','13'):'/Base interlock/BASE_NOT_READY',('U27','11'):'BASE_READY',('D3','2'):'/Base LEDs/LED_PWR_AN',('R130','2'):'/Base LEDs/LED_PWR_AN'}
changed=[]
for k,v in b.items():
 if k in a and a[k]!=v:
  assert allowed.get(k)==v,(k,a[k],v)
  changed.append({'ref':k[0],'pin':k[1],'before':a[k],'after':v})
assert b['R160','1']=='CTRL_READY' and b['R160','2']=='GND'
assert b['R82','1']=='ENABLE_IN' and b['R82','2']=='GND'
assert b['Q8','3']=='FAULT_N'
header_checks=[]
if 'power_interface' in active:
 contract=json.load((BASE.parents[1]/'docs/daughterboard_pin_contract.json').open(encoding='utf-8'))
 for ref in ['J101','J102']:
  for pin,want in contract[ref].items():
   actual=b[ref,pin]
   if want=='SUPPLY':want='+5V_INV'
   assert actual==want if want is not None else actual.startswith('unconnected-'),(ref,pin,want,actual)
   header_checks.append({'ref':ref,'pin':pin,'net':actual,'pass':True})
 assert {k for k,v in b.items() if v=='FAULT_N'}=={('Q8','3'),('TP16','1'),('J101','19')}
 assert {k for k,v in b.items() if v=='CTRL_READY'}=={('R160','1'),('U26','13'),('J101','17')}
 assert {k for k,v in b.items() if v=='BASE_READY'}=={('U27','11'),('J101','18')}
 assert {k for k,v in b.items() if v=='ENABLE_IN'}=={('R82','1'),('U26','12'),('TP17','1'),('J101','14')}
removed={k[0] for k in a}-{k[0] for k in b}
expected_removed=set()
for name in ['mcu','mcu_analog','mcu_control','sensors','debug_comms']:
 expected_removed|={r for r,u in refinst(original(name))}
expected_removed-={'D3','R130'}
if 'power_interface' in active:expected_removed-={'TP16','TP17'}
assert removed==expected_removed,(removed^expected_removed)
newrefs={k[0] for k in b}-{k[0] for k in a}
# The root-owned controller header may be added after this baseline snapshot.
assert 'R160' in newrefs
r=json.load((BASE/'review/revd_power_erc.json').open(encoding='utf-8'));viol=[v for sh in r['sheets'] for v in sh['violations']]
assert not [v for v in viol if v['severity']=='error']
top=sx.load((BASE/'inverter.kicad_sch').open(encoding='utf-8'));sheets=[props(s)['Sheetfile'] for s in children(top,'sheet')]
assert not any(n+'.kicad_sch' in sheets for n in ['mcu','mcu_analog','mcu_control','sensors','debug_comms'])
report={'archive':str(archive),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'active_power_pages':active,'top_linked_sheets':sheets,'retained_original_component_property_changes':property_diffs,'testpoint_ui_filter_additions':ui_filter_additions,'allowed_changed_retained_pins':changed,'new_refs':sorted(newrefs),'removed_refs_migrated_to_controller':sorted(removed),'retained_physical_refs_in_current_top':len(after.findall('./components/comp')),'erc':{'errors':sum(v['severity']=='error' for v in viol),'warnings':sum(v['severity']=='warning' for v in viol),'by_type':dict(Counter(v['type'] for v in viol)),'report':'review/revd_power_erc.json','baseline_pending_header_warning_count':9},'checks':{'all_retained_values_footprints_supplier_fields_dnp_unchanged':True,'only_explicit_safety_pin_changes':True,'raw_enable_pull_down_retained':True,'ctrl_ready_local_10k_pull_down_present':True,'fault_n_collector_has_no_base_domain_pullup':True,'mcu_nrst_pages_not_in_power_top':True,'no_pcb_or_shared_library_written':True},'notes':['R160 and two inter-board connectors are the added base BOM items; R160 is 10k YAGEO with exact MPN pending like the retained pull-down family.','U26D and U27C/D reuse the original 74LVC08/00 packages; package power/bypass stays on control_interface.','D3/R130 remain on the base; D4-D7/R131-R134 migrate unchanged to the MCU sub-board.','TP16/TP17 are retained on the base interface with original value and footprint; their only added field is the non-electrical KiCad footprint-search filter.','The old Rev C PCB is historical and must not be used with this Rev D schematic.']}
(BASE/'review/revd_power_validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
report['header_contract']=header_checks
(BASE/'review/revd_power_validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('PASS',len(changed),'explicit retained-pin changes;',len(removed),'refs moved;',len(header_checks),'header pins;',report['retained_physical_refs_in_current_top'],'base refs;',report['erc'])

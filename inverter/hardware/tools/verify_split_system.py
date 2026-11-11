"""Independent readback of both Rev D XMLs, mating pins and shutdown logic."""
from pathlib import Path
import csv,json,hashlib,xml.etree.ElementTree as ET
BASE=Path(__file__).resolve().parents[1];REPO=BASE.parents[1];CORE=REPO/'controller/hardware/g431_core'

def load(file):
    r=ET.parse(file).getroot();parts={c.attrib['ref']:c for c in r.findall('./components/comp')};pins={}
    for net in r.findall('./nets/net'):
        name=net.attrib['name'].rsplit('/',1)[-1]
        for node in net.findall('node'):pins[node.attrib['ref'],node.attrib['pin']]=name
    return parts,pins
cp,c=load(CORE/'review/controller.net.xml');bp,b=load(BASE/'review/revd_power.net.xml')
contract=json.loads((REPO/'docs/daughterboard_pin_contract.json').read_text(encoding='utf-8'))
checks=[]
for ref in ['J101','J102']:
    for pin,want in contract[ref].items():
        cv,bv=c[ref,pin],b[ref,pin]
        if want is None:assert cv.startswith('unconnected-') and bv.startswith('unconnected-')
        elif want=='SUPPLY':assert cv=='+5V_CORE_IN' and bv=='+5V_INV'
        else:assert cv==bv==want,(ref,pin,cv,bv,want)
        checks.append([ref,int(pin),cv,bv])
assert not any(c['J101',str(p)].startswith('+3V3') for p in range(1,21))
assert 'U30' in cp and 'U30' not in bp
assert c['R143','1']=='FAULT_N_MCU' and c['R143','2']=='+3V3_MCU'
assert c['R209','1']=='BASE_READY_MCU' and c['R209','2']=='GND'
for idx,(raw,dest) in enumerate([('BASE_READY','BASE_READY_MCU'),('FAULT_N','FAULT_N_MCU')]):
    ref='R'+str(210+idx);d='D'+str(209+idx)
    assert {c[ref,'1'],c[ref,'2']}=={raw,dest}
    assert cp[ref].findtext('value')=='1k'
    assert [c[d,str(p)] for p in [1,2,3]]==['GND','+3V3_MCU',dest]
adc=['I_U_PORT','I_V_PORT','I_W_PORT','V_DC_PORT','V_U_PORT','V_V_PORT','V_W_PORT','TEMP_NTC']
for i,raw in enumerate(adc):
    rr='R'+str(201+i);dd='D'+str(201+i)
    assert {c[rr,'1'],c[rr,'2']}=={raw,raw+'_CLAMPED'}
    assert cp[rr].findtext('value')=='360'
    assert [c[dd,str(p)] for p in [1,2,3]]==['GND','+3V3_MCU',raw+'_CLAMPED']
    assert c['R'+str(84+i),'1']==raw+'_CLAMPED'
    assert cp['R'+str(84+i)].findtext('value')=='100'
    assert cp['C'+str(69+i)].findtext('value')=='1n'
# Generate a real pin-by-pin deliverable, preserving the reviewed peripheral AFs.
rows=list(csv.DictReader((BASE/'STM32G431RBT6_pin_plan.csv').open(encoding='utf-8-sig')))
for row in rows:
    actual=c['U30',row['Pin']];actual='NC' if actual.startswith('unconnected-') else actual
    want=row['Net'].replace('+3V3_INV','+3V3_MCU').replace('LOGIC_POWER_OK','MCU_RESET_N')
    if want=='FAULT_N':want='FAULT_N_MCU'
    if row['Pin']=='2':
        want='BASE_READY_MCU';row.update(Function='GPIO input',AF='',Notes='PC13 reads base supply-ready after 1k/clamp protection; R209 pulls LOW if absent.')
    assert actual==want,(row['Pin'],actual,want);row['Net']=actual
with (CORE/'STM32G431RBT6_pin_plan.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
assert sum(r['Net']=='NC' for r in rows)==6
assert not any(n=='MCU_RESET_N' for n in b.values())
assert {q for q,n in b.items() if n=='FAULT_N'}=={('Q8','3'),('TP16','1'),('J101','19')}
assert b['R160','1']=='CTRL_READY' and b['R160','2']=='GND'
assert b['R82','1']=='ENABLE_IN' and b['R82','2']=='GND'
assert b['R16','1']=='BRAKE_IN' and b['R16','2']=='GND'
# Evaluate the gates found in the actual power XML, including the new ready gates.
units=[(1,2,3),(4,5,6),(9,10,8),(12,13,11)];gates=[]
for ref,kind in [(f'U{i}','AND') for i in range(22,27)]+[('U27','NAND')]:
    assert b[ref,'7']=='GND' and b[ref,'14']=='+3V3_INV'
    for aa,bb,yy in units:
        out=b.get((ref,str(yy)),'unconnected-')
        if not out.startswith('unconnected-'):gates.append((b[ref,str(aa)],b[ref,str(bb)],out,kind))
def evaluate(inputs):
    v={'GND':False,'+3V3_INV':True}|inputs
    for _ in range(len(gates)+1):
        changed=False
        for a,z,y,k in gates:
            if y not in v and a in v and z in v:v[y]=(v[a] and v[z]) if k=='AND' else not(v[a] and v[z]);changed=True
        if not changed:break
    return v
healthy=[f'OC_{p}_{s}_OK' for p in 'UVW' for s in ['HIGH','LOW']]+['BUS_OV_OK','DRV_UV_OK','BASE_LOGIC_OK','DRV_PG_LOGIC','AUX_FLT_N']
cases=0
for mask in range(1<<len(healthy)):
    h={net:bool(mask&(1<<i)) for i,net in enumerate(healthy)}
    for en in [False,True]:
        for core in [False,True]:
            for latch in [False,True]:
                v=evaluate(h|{'ENABLE_IN':en,'CTRL_READY':core,'NO_LATCH':not latch}|{f'PWM_{p}_IN':True for p in ['UH','UL','VH','VL','WH','WL']})
                all_ok=all(h.values());qualified=en and core;permit=all_ok and qualified and not latch
                assert v['ENABLE_QUALIFIED']==qualified
                assert v['HEALTH_ALL']==all_ok and v['RESET_REQUEST']==(all_ok and not qualified)
                assert v['BASE_READY']==(h['BASE_LOGIC_OK'] and h['DRV_PG_LOGIC'])
                assert v['DRIVE_PERMIT']==permit
                for p in 'UVW':assert v[p+'_HIN']==v[p+'_LIN']==permit
                cases+=1
for en in [False,True]:
    for core in [False,True]:
        for mask in range(64):
            raw={f'PWM_{p}_IN':bool(mask&(1<<i))for i,p in enumerate(['UH','UL','VH','VL','WH','WL'])}
            v=evaluate({s:True for s in healthy}|{'ENABLE_IN':en,'CTRL_READY':core,'NO_LATCH':True}|raw)
            for i,p in enumerate(['UH','UL','VH','VL','WH','WL']):assert v[p[0]+('_HIN' if p[1]=='H' else '_LIN')]==(en and core and bool(mask&(1<<i)))
report={'result':'PASS','revision':'D-modular-draft','core_components':len(cp),'base_components':len(bp),'mated_pins_checked':checks,'MCU_package_pins':64,'MCU_NC':6,'logic_truth_cases':cases,'PWM_patterns_with_enable_ready_cases':256,'checks':['40 physical header pins match including supply aliases and NC','Independent 3V3 rails and local NRST','8 ADC 360R/clamp ->100R/1n paths and 2 protected digital returns','FAULT pullup only in MCU domain; ready/enable/brake physical pull-downs','Actual-gate core-ready/default-disable and hardware fault/latch truth table'],'limits':['Non-isolated common-GND prototype; no guarantee that a power-stage failure leaves the core undamaged.','Static netlist/logic checks do not validate analog transient dynamics, timing, thermal performance or a built board.']}
(CORE/'review/system_check.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
(CORE/'review/system_check.txt').write_text('PASS\n'+json.dumps({k:v for k,v in report.items()if k!='mated_pins_checked'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PASS:',len(cp),'core refs,',len(bp),'base refs, 40 connector pins, 64 MCU pins,',cases,'logic cases')

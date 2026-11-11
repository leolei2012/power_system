"""Independent current-netlist verification against the immutable Rev D snapshot."""
from pathlib import Path
from collections import defaultdict
import csv,io,json,zipfile,xml.etree.ElementTree as E

BASE=Path(__file__).resolve().parents[1];REPO=BASE.parents[1];CORE=REPO/'controller/hardware/g431_core'
Z=zipfile.ZipFile(REPO/'inverter/history/daughterboard_rev_d_before_minimum_core_2026-11-07.zip')

def load(data):
    root=E.fromstring(data);parts={c.get('ref'):c for c in root.findall('./components/comp')};nets={};pins={}
    for n in root.findall('./nets/net'):
        key=n.get('code');nets[key]=[(v.get('ref'),v.get('pin')) for v in n.findall('node')]
        for node in nets[key]:pins[node]=(key,n.get('name').rsplit('/',1)[-1])
    return parts,nets,pins

old={};new={}
for role,prefix,file in [('core','controller/hardware/g431_core/','controller.net.xml'),('base','inverter/hardware/','inverter.net.xml')]:
    old[role]=load(Z.read(prefix+'review/'+file))
    new[role]=load((REPO/prefix/'review'/file).read_bytes())
cp,cn,c=new['core'];bp,bn,b=new['base']
net=lambda p,ref,pin:p[(ref,str(pin))][1]
contract=json.loads((REPO/'docs/daughterboard_pin_contract.json').read_text(encoding='utf-8'))
assert len(cp)==47 and len(bp)==317
assert sum(x.find("property[@name='dnp']") is not None for x in cp.values())==3
assert sum(x.find("property[@name='dnp']") is not None for x in bp.values())==14
assert {r for r in cp if r.startswith('J')}=={'J101','J102'}
assert {'SW2','SW3','U30','U101','U102','U103','U105'}<=cp.keys()
assert 'U30' not in bp and {'J9','J10','J11','J12','J13','J14'}<=bp.keys()
checked=[]
for ref in ['J101','J102']:
    for pin,want in contract[ref].items():
        cv,bv=net(c,ref,pin),net(b,ref,pin)
        cw=contract['supply_alias'][want]['controller'] if want in contract['supply_alias'] else want
        bw=contract['supply_alias'][want]['inverter'] if want in contract['supply_alias'] else want
        assert cv==cw,(ref,pin,cv,cw)
        assert bv.startswith('unconnected-') if want in contract['base_unassigned_ports'] else bv==bw,(ref,pin,bv,bw)
        checked.append([ref,int(pin),cv,bv])

# Every GPIO-capable package pad is directly present on exactly one core header.
gpio={str(v['mcu_pad']):v['net'] for rows in contract['pins'].values() for v in rows if v['kind']=='mcu_signal'}
assert len(gpio)==52 and len(set(gpio.values()))==52
for pin,want in gpio.items():assert net(c,'U30',pin)==want,(pin,want,net(c,'U30',pin))
assert not any(net(c,'U30',p).startswith('unconnected-') for p in map(str,range(1,65)))
assert [net(c,'SW2',p) for p in [1,2]]==['NRST','GND']
assert net(c,'SW3',1)=='+3V3_MCU'
assert net(c,'SW3',2)==net(c,'R401',1) and net(c,'R401',2)=='PB8_BOOT0'
assert [net(c,'R122',p) for p in [1,2]]==['PB8_BOOT0','GND']
assert cp['R401'].findtext('value')=='1k' and cp['R122'].findtext('value')=='10k'
assert [net(c,'U105',p) for p in [1,2,3,4,5]]==['CORE_RESET_OK','PC7','GND','CTRL_READY','+3V3_MCU']
assert [net(c,'U103',p) for p in [2,3,4,5]]==['NRST','GND','CORE_RESET_OK','+3V3_MCU']
assert [net(c,'R402',p) for p in [1,2]]==['PC7','GND'] and cp['R402'].findtext('value')=='10k'
assert net(c,'C308',1)=='+3V3_MCU' and net(c,'C308',2)=='GND'
assert net(c,'R301',1)=='+5V_CORE_IN' and net(c,'U102',1)=='NRST'
assert net(c,'U102',3)=='CORE_MR_5V_PRESENT'

# The moved analog and status paths retain both their resistors and rail clamps.
adcs=[('I_U_PORT','PC0'),('I_V_PORT','PC1'),('I_W_PORT','PC2'),('V_DC_PORT','PC3'),('V_U_PORT','PA4'),('V_V_PORT','PB0'),('V_W_PORT','PB1'),('TEMP_NTC','PB2')]
for i,(raw,port) in enumerate(adcs):
    rr,dd,last,cap='R'+str(201+i),'D'+str(201+i),'R'+str(84+i),'C'+str(69+i)
    assert net(b,rr,1)==raw
    assert net(b,rr,2)==net(b,dd,3)==net(b,last,1)
    assert net(b,last,2)==net(b,cap,1)==port and net(b,cap,2)=='GND'
    assert net(b,dd,1)=='GND' and net(b,dd,2)=='+3V3_CORE_REF'
    assert bp[rr].findtext('value')=='360' and bp[last].findtext('value')=='100' and bp[cap].findtext('value')=='1n'
for i,(raw,port) in enumerate([('BASE_READY','PC13'),('FAULT_N','PB12')]):
    rr,dd='R'+str(210+i),'D'+str(209+i)
    assert [net(b,rr,p) for p in [1,2]]==[raw,port]
    assert [net(b,dd,p) for p in [1,2,3]]==['GND','+3V3_CORE_REF',port]
assert [net(b,'R143',p) for p in [1,2]]==['PB12','+3V3_CORE_REF']
assert [net(b,'R209',p) for p in [1,2]]==['PC13','GND']
assert net(b,'J13',1)=='+3V3_CORE_REF' and net(b,'J13',5)=='NRST'
assert net(b,'U4',5)=='+3V3_INV'  # base regulator OUT is not core clamp rail
assert not any(net(b,r,p)=='NRST' for r in ['U22','U23','U24','U25','U26','U27'] for p in range(1,15))

class UF:
    def __init__(self):self.parent={}
    def root(self,a):
        self.parent.setdefault(a,a)
        if self.parent[a]!=a:self.parent[a]=self.root(self.parent[a])
        return self.parent[a]
    def join(self,a,b):self.parent[self.root(a)]=self.root(b)

def system_groups(data,old_contract=False):
    u=UF()
    for role,(parts,nets,pins) in data.items():
        for ns in nets.values():
            nodes=[(role,ref,pin) for ref,pin in ns if ref in parts]
            for node in nodes:u.join(nodes[0],node)
    for ref in ['J101','J102']:
        for pin in map(str,range(1,21 if old_contract else 33)):
            a=('core',ref,pin);z=('base',ref,pin)
            if not old_contract and net(data['base'][2],ref,pin).startswith('unconnected-'):continue
            u.join(a,z)
    return u

# Compare complete physical connectivity partitions, independent of net names.
# Explicit intentional changes are moved peripheral supply rails and U103's
# output now feeding the additional ARM gate. New button/gate parts are additive.
ou=system_groups(old,True);nu=system_groups(new)
old_nodes=[];dest={};metadata=[]
for role,(parts,nets,pins) in old.items():
    for ref,part in parts.items():
        if ref in ['J101','J102']:continue
        owner='base' if role=='base' or ref not in cp else 'core'
        actual=new[owner][0][ref]
        for field in ['value','footprint']:
            assert part.findtext(field)==actual.findtext(field),(role,ref,field)
        assert (part.find("property[@name='dnp']") is not None)==(actual.find("property[@name='dnp']") is not None),(role,ref,'DNP')
        metadata.append([role,ref,owner])
        for rr,pin in pins:
            if rr==ref:
                node=(role,ref,pin);old_nodes.append(node);dest[node]=(owner,ref,pin)
old_base_rail=next(ou.root(('base',r,p)) for (r,p),(code,name) in old['base'][2].items() if name=='+3V3_INV' and r not in ['J101','J102'])
expected=defaultdict(set);actual=defaultdict(set);rail_changes=[]
for node in old_nodes:
    role,ref,pin=node;group=ou.root(node)
    if role=='core' and dest[node][0]=='base' and net(old['core'][2],ref,pin)=='+3V3_MCU' and ref not in ['R143'] and not (ref.startswith('D2') and 201<=int(ref[1:])<=210) and not(ref=='J13' and pin=='1'):
        group=old_base_rail;rail_changes.append([ref,pin])
    if node==('core','U103','4'):group=('new','CORE_RESET_OK')
    expected[group].add(node);actual[nu.root(dest[node])].add(node)
es={frozenset(v) for v in expected.values()};ac={frozenset(v) for v in actual.values()}
if es!=ac:
    diff={'expected_only':[sorted(v) for v in es-ac],'actual_only':[sorted(v) for v in ac-es]}
    (CORE/'review/minimum_core_partition_diff.json').write_text(json.dumps(diff,indent=2)+'\n',encoding='utf-8')
    raise AssertionError('Physical connectivity differs: see minimum_core_partition_diff.json')

# Evaluate actual AND/NAND netlists with the core permission gate included.
gates=[]
for ref,kind in [(f'U{i}','AND') for i in range(22,27)]+[('U27','NAND')]:
    for a,z,y in [(1,2,3),(4,5,6),(9,10,8),(12,13,11)]:
        out=net(b,ref,y)
        if not out.startswith('unconnected-'):gates.append((net(b,ref,a),net(b,ref,z),out,kind))
def evaluate(values):
    v={'GND':False,'+3V3_INV':True}|values
    for _ in range(len(gates)+1):
        for a,z,y,k in gates:
            if y not in v and a in v and z in v:v[y]=(v[a] and v[z]) if k=='AND' else not(v[a] and v[z])
    return v
healthy=[f'OC_{p}_{s}_OK' for p in 'UVW' for s in ['HIGH','LOW']]+['BUS_OV_OK','DRV_UV_OK','BASE_LOGIC_OK','DRV_PG_LOGIC','AUX_FLT_N']
cases=0
for mask in range(1<<len(healthy)):
    h={n:bool(mask&(1<<i)) for i,n in enumerate(healthy)}
    for reset in [False,True]:
        for arm in [False,True]:
            for enable in [False,True]:
                for latch in [False,True]:
                    ready=reset and arm
                    v=evaluate(h|{'ENABLE_IN':enable,'CTRL_READY':ready,'NO_LATCH':not latch}|{f'PWM_{p}_IN':True for p in ['UH','UL','VH','VL','WH','WL']})
                    permit=all(h.values()) and ready and enable and not latch
                    assert v['DRIVE_PERMIT']==permit
                    for p in 'UVW':assert v[p+'_HIN']==v[p+'_LIN']==permit
                    cases+=1

rows=list(csv.DictReader((BASE/'STM32G431RBT6_pin_plan.csv').open(encoding='utf-8-sig')))
for row in rows:
    row['Net']=net(c,'U30',row['Pin'])
    if row['Pin'] in gpio:
        row['Notes']+='; Raw MCU pad exposed on GPIO header; application conditioning is on base.'
    if row['Pin']=='39':row.update(Function='GPIO RUN_ARM',AF='',Notes='PC7 defaults LOW via local 10k. Inverter application explicitly arms after safe initialization; G431 ROM loader does not use PC7.')
    elif row['Pin']=='2':row.update(Function='GPIO base-ready input',AF='',Notes='PC13 receives protected base-ready from application base; raw MCU pad remains exposed.')
    elif row['Function']=='NC':row.update(Function='GPIO expansion reserve',AF='',Notes='Raw unused application GPIO exposed on core header; corresponding base socket pad is NC.')
with (CORE/'STM32G431RBT6_pin_plan.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
report={'result':'PASS','revision':'E-minimum-core-draft','core_components':len(cp),'base_components':len(bp),'core_DNP':3,'base_DNP':14,'mated_pins_checked':checked,'MCU_package_pins':64,'MCU_signal_pads_exposed':52,'MCU_NC':0,'base_unused_socket_contacts':9,'logic_truth_cases':cases,'original_component_records_preserved':len(metadata),'original_physical_pin_partition_nodes':len(old_nodes),'intentional_peripheral_supply_rail_changes':rail_changes,'checks':['All 52 signal pads appear once on core headers, including special reset/boot/HSE pads','64 positions match, with explicit nine unused base socket NCs','Original component value/footprint/DNP preserved except four replaced header parts','Complete old-pin connectivity partitions preserved except explicit peripheral power transfer and U103 output split','8 ADC and 2 status paths retain current limiting and core-referenced rail clamps','NRST Schmitt conditioning and PC7 ARM required before CTRL_READY','ROM/default ARM LOW blocks all six PWM paths for every enumerated base health/enable/latch state'],'limits':['Schematic and static digital checks only, not dynamic/thermal/assembly validation.','Common-ground interface, power off both boards before insertion/removal; no blown-power-stage immunity guarantee.','PC7 is reserved for ARM in inverter use; this is not a watchdog.']}
for name in ['system_check.json','minimum_core_validation.json']:(CORE/'review'/name).write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(CORE/'review/system_check.txt').write_text('PASS\n'+json.dumps({k:v for k,v in report.items() if k!='mated_pins_checked'},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('PASS',len(cp),'core,',len(bp),'base, 52 signal pads, 64 contacts,',len(old_nodes),'baseline pins,',cases,'logic cases')

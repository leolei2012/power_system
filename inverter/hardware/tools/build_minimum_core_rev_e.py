"""One-time Rev E migration from immutable Rev D functional daughterboard.

Authoring record, not a general regeneration command. Shared library read only.
"""
from pathlib import Path
import copy,csv,json,math,uuid,zipfile,sys
import sexpdata as sx
import schematic_common as s

BASE=Path(__file__).resolve().parents[1];REPO=BASE.parents[1]
CORE=REPO/'controller/hardware/g431_core'
ARCHIVE=REPO/'inverter/history/daughterboard_rev_d_before_minimum_core_2026-11-07.zip'
Z=zipfile.ZipFile(ARCHIVE)
CR='9dba1312-bd1c-50b2-9df7-fc81461aaf77';BR='c6bbe498-7a84-5001-ab1e-dd9afbac55ac'
S=sx.Symbol;tag=s.tag;child=s.child;children=s.children
props=lambda n:{p[1]:p[2] for p in children(n,'property')}
uid=lambda key:str(uuid.uuid5(uuid.NAMESPACE_URL,'power_system/minimum-core-rev-e/'+key))
read=lambda board,name:sx.loads(Z.read(('controller/hardware/g431_core/' if board=='core' else 'inverter/hardware/')+name+'.kicad_sch').decode('utf-8-sig'))
proposal=json.loads((CORE/'review/minimum_core_pin_proposal.json').read_text(encoding='utf-8'))
PADMAP={str(v['mcu_pad']):v['net'] for hs in proposal['headers'].values() for v in hs if v['kind']=='mcu_signal'}
oldrows=list(csv.DictReader((BASE/'STM32G431RBT6_pin_plan.csv').open(encoding='utf-8-sig')))
ALIASES={r['Net']:PADMAP[r['Pin']] for r in oldrows if r['Pin'] in PADMAP and r['Net']!='NC'}
ALIASES.update(BASE_READY_MCU='PC13',FAULT_N_MCU='PB12',MCU_RESET_N='NRST')

def walk(n):
    if isinstance(n,list):
        yield n
        for x in n:yield from walk(x)

def rename(n,mapping):
    for x in walk(n):
        for i,v in enumerate(x):
            if type(v) is str and v in mapping:x[i]=mapping[v]

def save(base,name,r,title=None):
    tb=child(r,'title_block')
    child(tb,'date')[1]='2026-11-07';child(tb,'rev')[1]='E-core-draft'
    if title:child(tb,'title')[1]=title
    (base/(name+'.kicad_sch')).write_text('('+str(r[0])+'\n'+'\n'.join(sx.dumps(n) for n in r[1:])+')\n',encoding='utf-8')

def page(base,name,title):
    s.BASE=base;s.PROJECT='controller' if base==CORE else 'inverter';s.ROOT=CR if base==CORE else BR;s.NS=uuid.uuid5(uuid.NAMESPACE_URL,'power_system/rev-e/'+s.PROJECT)
    p=s.Page(name,title,6 if base==CORE else 20)
    p.uuid=uid(('core/' if base==CORE else 'base/')+name)
    p.path='/'+s.ROOT+'/'+uid(('core/' if base==CORE else 'base/')+'sheet/'+name)
    return p

def finish(p,base,title=None):
    p.write();r=sx.loads((base/(p.name+'.kicad_sch')).read_text(encoding='utf-8'))
    if p.name=='core_signal_protection':
        for symbol in children(r,'symbol'):
            v=props(symbol)
            if v.get('Reference','').startswith('D'):
                at=child(symbol,'at')
                for key,dy in [('Reference',-5.08),('Value',-2.54)]:
                    prop=next(n for n in children(symbol,'property') if n[1]==key)
                    child(prop,'at')[1:3]=[at[1],at[2]+dy]
    save(base,p.name,r,title)
    return r

def comp(source,ref):return next(n for n in children(source,'symbol') if props(n).get('Reference')==ref)
def clone_instance(p,source,ref,x,y,angle=0):
    n=comp(source,ref);v=props(n)
    return p.inst(child(n,'lib_id')[1],ref,v['Value'],x,y,angle,fp=v.get('Footprint',''),fields={k:v for k,v in v.items() if k not in ['Reference','Value','Footprint']},dnp=child(n,'dnp')[1]==S('yes'))
def fields_note(note):return {'Manufacturer':'YAGEO','MPN':'TBD','Tolerance':'1%','Selection_Status':'exact YAGEO MPN pending','Design_Note':note}
def allpins(inst,mapping):
    for pin,net in mapping.items():inst.connect(pin,net,5.08)
def raw_page(base,name,r,title):
    root=CR if base==CORE else BR
    child(r,'uuid')[1]=uid(('core/' if base==CORE else 'base/')+name)
    newpath='/'+root+'/'+uid(('core/' if base==CORE else 'base/')+'sheet/'+name)
    for n in walk(r):
        if tag(n,'project'):n[1]='controller' if base==CORE else 'inverter'
        if tag(n,'path') and len(n)>2 and children(n,'reference'):n[1]=newpath
    save(base,name,r,title)

def coords(n):
    if tag(n,'wire'):return [tuple(v[1:3]) for v in child(n,'pts')[1:]]
    at=child(n,'at');return [tuple(at[1:3])] if at else []

# Core MCU: preserve the package and decoupling, label every signal by port.
r=read('core','mcu');rename(r,ALIASES)
m=comp(r,'U30');mx,my,angle=child(m,'at')[1:];libid=child(m,'lib_id')[1]
lib=next(n for n in children(child(r,'lib_symbols'),'symbol') if n[1]==libid)
for unit in children(lib,'symbol'):
    for pin in children(unit,'pin'):
        num=str(child(pin,'number')[1])
        if num not in ['3','4','39','56','57','62']:continue
        px,py,pa=child(pin,'at')[1:];point=(round(mx+px,4),round(my-py,4))
        r[:]=[n for n in r if not(tag(n,'no_connect') and coords(n)==[point])]
        end=(round(point[0]-math.cos(math.radians(pa))*7.62,4),round(point[1]+math.sin(math.radians(pa))*7.62,4))
        r.append(sx.loads(f'(wire (pts (xy {point[0]} {point[1]}) (xy {end[0]} {end[1]})) (stroke (width 0) (type default)) (uuid "{uid("mcu-wire-"+num)}"))'))
        r.append(sx.loads(f'(global_label "{PADMAP[num]}" (shape passive) (at {end[0]} {end[1]} {180 if end[0]<point[0] else 0}) (effects (font (size .88 .88)) (justify {"right" if end[0]<point[0] else "left"})) (uuid "{uid("mcu-label-"+num)}"))'))
for t in children(r,'text'):
    if t[1].startswith('CROSS-SHEET'):t[1]='ALL MCU SIGNAL PADS -> GPIO HEADERS\nPA/PB/PC names denote raw MCU-side nets.\nPG10 remains NRST; PB8 remains BOOT0.\nPC7 is RUN_ARM when fitted to the inverter base.'
    elif t[1].startswith('Keep outputs'):t[1]='All 52 GPIO-capable pads are exposed; PG10 is retained as NRST.\nPF0/PF1 are shared with the optional local HSE.\nApplication interfaces and signal conditioning reside on the baseboard.'
raw_page(CORE,'mcu',r,'Minimum core - STM32G431RBT6 and decoupling')

# Retain only the local analog supply section on the core.
r=read('core','mcu_analog');keep=[]
for n in r[1:]:
    if tag(n,'symbol') and props(n).get('Reference') in ['R84','R85','R86','R87','R88','R89','R90','R91','C69','C70','C71','C72','C73','C74','C75','C76']:continue
    if str(n[0]) in ['wire','global_label','label','junction','polyline','text','symbol'] and coords(n) and max(y for x,y in coords(n))<190:continue
    keep.append(n)
r=[r[0]]+keep
for t in children(r,'text'):
    if '360' in t[1] or t[1].startswith('ADC filtering'):t[1]='Application ADC filters and clamps are on the inverter baseboard; this page contains local VDDA / VREF only.'
for item in r[1:]:
    if str(item[0]) in ['symbol','wire','global_label','label','junction','polyline','text']:
        for n in walk(item):
            if tag(n,'at') or tag(n,'xy'):n[2]=round(n[2]-170.18,4)
raw_page(CORE,'mcu_analog',r,'Minimum core - local VDDA and VREF')

# Local RESET / BOOT / optional HSE, no functional external connectors.
debug=read('core','debug_comms');control=read('core','mcu_control')
p=page(CORE,'mcu_control','Minimum core - RESET BOOT and optional HSE')
p.section('LOCAL OPEN-DRAIN RESET',20.32,20.32,175)
sw=clone_instance(p,debug,'SW2',66.04,55.88)
c=clone_instance(p,debug,'C81',121.92,55.88)
p.wire(sw.pt(1),(53.34,55.88));p.label('NRST',(53.34,55.88),180)
p.wire((53.34,55.88),(53.34,40.64));p.wire((53.34,40.64),(121.92,40.64));p.wire((121.92,40.64),c.pt(1))
p.wire(sw.pt(2),(96.52,55.88));p.wire((96.52,55.88),(96.52,76.2));p.wire((96.52,76.2),(121.92,76.2));p.wire(c.pt(2),(121.92,76.2));p.label('GND',(121.92,76.2))
p.text('SW2 pulls NRST LOW. Pull-up / supervisor remain on the supply page.',20.32,81.28,1.05)
p.section('BOOT0 / PB8 / BUTTON DEFAULT RELEASED',215.9,20.32,175)
sw=clone_instance(p,debug,'SW2',254,55.88);sw.ref='SW3';sw.fields['Reference']='SW3';sw.value='BOOT';sw.fields['Value']='BOOT';sw.uuid=uid('SW3')
sw.connect(1,'+3V3_MCU',5.08)
rr=p.inst('Device:R','R401','1k',294.64,55.88,90,fp='Resistor_SMD:R_0603_1608Metric',fields=fields_note('BOOT button limiting; PB8 remains an exposed GPIO-capable pad.'))
p.wire(sw.pt(2),rr.pt(1))
pd=clone_instance(p,debug,'R122',335.28,68.58)
tp=clone_instance(p,debug,'TP15',368.3,55.88)
p.wire(rr.pt(2),(335.28,55.88));p.wire((335.28,55.88),pd.pt(1));p.junction((335.28,55.88));p.wire((335.28,55.88),tp.pt(1));p.wire((335.28,55.88),(335.28,45.72));p.label('PB8_BOOT0',(335.28,45.72));pd.connect(2,'GND',5.08)
p.text('Hold BOOT, press/release RESET, then release BOOT. Requires option-byte setup.\nBOOT alone does not reset. PC7/RUN_ARM defaults LOW during ROM boot.',215.9,91.44,1.02)
p.section('OPTIONAL HSE / DEFAULT DNP',20.32,139.7,375)
y=clone_instance(p,control,'Y1',147.32,185.42)
for ref,x,net in [('C83',83.82,'HSE_IN'),('C84',213.36,'HSE_OUT')]:
    c=clone_instance(p,control,ref,x,205.74)
    p.wire(y.pt(1 if ref=='C83' else 3),(x,185.42));p.wire((x,185.42),c.pt(1));p.label(net,(x,185.42));p.wire(c.pt(2),(x,223.52))
p.wire((83.82,223.52),(213.36,223.52))
p.junction((213.36,223.52))
for a in sorted({y.pt(pin) for pin in [2,4]}):
    p.wire(a,(a[0],223.52));p.junction((a[0],223.52))
p.label('GND',(147.32,223.52))
p.text('HSE is also present on PF0/PF1 header pads. Do not drive them externally with the crystal fitted.\nHSI16 / PLL may be used initially. Select actual crystal CL / ESR / drive before fitting.',20.32,248.92,1.05)
finish(p,CORE)

# Supply is kept intact; append a firmware ARM gate after the Schmitt buffer.
r=read('core','core_supply');rename(r,{'MCU_RESET_N':'NRST','CTRL_READY':'CORE_RESET_OK'})
for t in children(r,'text'):
    t[1]=t[1].replace('Only CTRL_READY crosses to baseboard; baseboard has a 10k pulldown.','CORE_RESET_OK goes to the separate RUN_ARM gate.').replace('CTRL_READY indicates power/reset readiness, not successful firmware self-test.','PC7/RUN_ARM is required before CTRL_READY can be HIGH.')
    t[1]=t[1].replace('Local reset button / SWD / C81 remain on debug page.','RESET and C81 stay on the core support page; SWD is on the base.')
raw_page(CORE,'core_supply',r,'Minimum core - independent power and local reset')
# Add the small ARM block on its own page, preserving the reviewed supply drawing.
p=page(CORE,'core_arm','Minimum core - application run permission')
p.section('SCHMITT RESET OK AND EXPLICIT APPLICATION ARM',20.32,20.32,375)
u=p.inst('74xGxx:74LVC1G08','U105','SN74LVC1G08DBVR',172.72,78.74,fp='Package_TO_SOT_SMD:SOT-23-5',fields={'Manufacturer':'TI','MPN':'SN74LVC1G08DBVR','Supplier_PN':'C7666','Purchase_URL':'https://www.lcsc.com/product-detail/C7666.html','Verification':'project_draft','Design_Note':'Ioff AND after U103 Schmitt reset buffer; PC7 held LOW unless application explicitly arms.'})
u.connect(1,'CORE_RESET_OK',5.08);u.connect(4,'CTRL_READY',5.08)
rr=p.inst('Device:R','R402','10k',121.92,104.14,fp='Resistor_SMD:R_0603_1608Metric',fields=fields_note('Local RUN_ARM pull-down. Inverter application reserves PC7; ROM bootloader leaves it undriven.'))
p.wire(u.pt(2),(121.92,81.28));p.wire((121.92,81.28),(101.6,81.28));p.label('PC7',(101.6,81.28),180);p.wire((121.92,81.28),rr.pt(1));p.junction((121.92,81.28));rr.connect(2,'GND',5.08)
c=p.inst('Device:C','C308','100n',238.76,78.74,fp='Capacitor_SMD:C_0603_1608Metric',fields={'Manufacturer':'YAGEO','MPN':'TBD','Voltage_Rating':'16V','Selection_Status':'exact YAGEO MPN pending'})
p.wire(u.pt(5),(172.72,63.5));p.wire((172.72,63.5),(238.76,63.5));p.wire((238.76,63.5),c.pt(1));p.label('+3V3_MCU',(172.72,63.5))
p.wire(u.pt(3),(172.72,99.06));p.wire((172.72,99.06),(238.76,99.06));p.wire(c.pt(2),(238.76,99.06));p.label('GND',(172.72,99.06))
p.text('CTRL_READY = CORE_RESET_OK AND PC7. U103 retains Schmitt conditioning of the slow NRST RC.\nROM boot can configure pins used as inverter PWM / ENABLE. PC7 is not used by the G431 ROM loader.\nAt reset or while running ROM, R402 holds PC7 LOW and the power base remains disabled.\nFirmware must initialize safe PWM / BKIN first, then explicitly assert RUN_ARM and ENABLE.\nClear RUN_ARM before software jumping to ROM. This is not a watchdog or CPU-halt detector.',20.32,165.1,1.3)
finish(p,CORE)

# Application interface pages migrate to the baseboard; they see the raw GPIO names.
for name,title in [('sensors','Baseboard - encoders and SPI'),('debug_comms','Baseboard - SWD TTL optional CAN and status LEDs')]:
    r=read('core',name);rename(r,ALIASES|{'+3V3_MCU':'+3V3_INV'})
    for symbol in children(r,'symbol'):
        ref=props(symbol).get('Reference','')
        if not ref.startswith('#'):
            original_value=props(comp(read('core',name),ref))['Value']
            next(v for v in children(symbol,'property') if v[1]=='Value')[2]=original_value
    if name=='debug_comms':
        remove_refs={'SW2','C81','R122','TP15','#PWR30803','#PWR30804'}
        r[:]=[n for n in r if not(tag(n,'symbol') and props(n).get('Reference') in remove_refs)]
        r[:]=[n for n in r if not(str(n[0]) in ['wire','junction','global_label','label'] and coords(n) and all(x<=210 and 80<=y<=132 for x,y in coords(n)) and not(tag(n,'global_label') and n[1]=='NRST') and not(tag(n,'wire') and coords(n)==[(55.88,60.96),(55.88,91.44)]))]
        # The NRST wire from SWD ends at its retained label, with no local RC.
        # SWD VTREF senses the core rail; other application circuits use base 3V3.
        for n in children(r,'symbol'):
            if props(n).get('Reference')=='#PWR30801':
                n[1:]=copy.deepcopy(n[1:]);rename(n,{'+3V3_INV':'+3V3_CORE_REF'})
        for t in children(r,'text'):
            if t[1].startswith('VTREF is sense only.'):t[1]='VTREF senses the core 3V3 reference. NRST goes only to the core reset domain.\nRESET / BOOT buttons are on the minimum-system core.\nExisting TTL PB10/PB11 is application UART, not the ROM USART3 pin pair.'
    raw_page(BASE,name,r,title)

# Eight series resistors and the protected fault pull-up return to the base.
r=read('core','mcu_control');rename(r,ALIASES|{'+3V3_MCU':'+3V3_CORE_REF'})
r[:]=[n for n in r if not(str(n[0]) in ['wire','global_label','label','junction','polyline','text','symbol','no_connect'] and coords(n) and min(y for x,y in coords(n))>=220)]
for t in children(r,'text'):
    if t[1].startswith('FAULT_N from'):t[1]='Protected PB12 is TIM1 BKIN; pull-up uses the exported core 3V3 reference.\nNRST is debug-only; it is not a power-stage fault output.\nSix PWM, ENABLE and BRAKE series resistors remain local to the base.'
raw_page(BASE,'mcu_coupling',r,'Baseboard - GPIO command coupling and fault pull-up')

# All application return conditioning sits on the baseboard next to the core socket.
orig_if=read('core','core_interface');orig_analog=read('core','mcu_analog')
p=page(BASE,'core_signal_protection','Baseboard - ADC and status return conditioning')
p.section('STATUS RETURN LIMITING / CORE-REFERENCED CLAMPS',20.32,17.78,375)
for i,(raw,dest,x) in enumerate([('BASE_READY','PC13',55.88),('FAULT_N','PB12',254)]):
    y=50.8;r=clone_instance(p,orig_if,'R'+str(210+i),x,y,90);r.connect(1,raw,5.08)
    d=clone_instance(p,orig_if,'D'+str(209+i),x+35.56,y-12.7);d.connect(1,'GND',2.54);d.connect(2,'+3V3_CORE_REF',2.54)
    node=(d.pt(3)[0],y);p.wire(r.pt(2),node);p.wire(node,d.pt(3));p.junction(node);end=(x+83.82,y);p.wire(node,end);p.label(dest,end)
r=clone_instance(p,orig_if,'R209',147.32,66.04);allpins(r,{1:'PC13',2:'GND'})
p.section('8 ADC PATHS / 360R CLAMP + 100R / 1n AT CORE SOCKET',20.32,86.36,375)
adc=[('I_U_PORT','PC0'),('I_V_PORT','PC1'),('I_W_PORT','PC2'),('V_DC_PORT','PC3'),('V_U_PORT','PA4'),('V_V_PORT','PB0'),('V_W_PORT','PB1'),('TEMP_NTC','PB2')]
for i,(raw,dest) in enumerate(adc):
    x=40.64+(i//4)*198.12;y=116.84+(i%4)*38.1
    p.text(raw+' -> '+dest,20.32+(i//4)*198.12,y-22.86,1.05)
    rr=clone_instance(p,orig_if,'R'+str(201+i),x,y,90);rr.connect(1,raw,5.08)
    dd=clone_instance(p,orig_if,'D'+str(201+i),x+30.48,y-12.7);dd.connect(1,'GND',2.54);dd.connect(2,'+3V3_CORE_REF',2.54)
    node=(dd.pt(3)[0],y);p.wire(rr.pt(2),node);p.wire(node,dd.pt(3));p.junction(node)
    last=clone_instance(p,orig_analog,'R'+str(84+i),x+66.04,y,90);p.wire(node,last.pt(1))
    cc=clone_instance(p,orig_analog,'C'+str(69+i),x+99.06,y+12.7)
    at=(cc.pt(1)[0],y);p.wire(last.pt(2),at);p.wire(at,cc.pt(1));p.junction(at);p.wire(at,(x+139.7,y));p.label(dest,(x+139.7,y));cc.connect(2,'GND',2.54)
p.text('Clamp upper rail returns ONLY through core 3V3_REF pins; never join it to base +3V3_INV. Power off both boards before mating.',20.32,270.51,1.0)
finish(p,BASE)

# Replace old 40-pin functional headers with matching GPIO-only 64-pin headers.
contract={'revision':'E-minimum-core-draft','pitch_mm':2.54,'pin_count':64,'mcu_signal_pads':52,'J101':{},'J102':{},'supply_alias':{'SUPPLY':{'controller':'+5V_CORE_IN','inverter':'+5V_INV'},'CORE_REF':{'controller':'+3V3_MCU','inverter':'+3V3_CORE_REF'}},'pins':proposal['headers'],'note':'Not compatible with Rev D 40-pin headers. 52 GPIO-capable pads include dedicated NRST and shared BOOT/HSE/debug. PC7 is RUN_ARM in inverter use.'}
contract['base_unassigned_ports']=['PB3','PB4','PB8_BOOT0','PB9','PC7','PC14','PC15','HSE_IN','HSE_OUT']
contract['mechanical_stack']={
    'board_size_mm': {'controller': [60, 60], 'inverter': [60, 60]},
    'upper_board': 'inverter power/application',
    'lower_board': 'controller minimum system',
    'core_header': 'male, core upper face, pins upward',
    'power_socket': 'female, power lower face, openings downward',
    'component_orientation_plan': 'Power MOSFETs/electrolytics upward on the upper power board. MCU, RESET SW2 and BOOT SW3 on the UPPER face of the LOWER controller board, toward the inter-board gap. Buttons sit near the controller board edge for finger access from the side. Other controller parts depend on thermal/assembly layout. Mating gap and assembled operating clearance pending PCB.',
    'core_buttons': {
        'references': ['SW2', 'SW3'],
        'functions': ['RESET', 'BOOT'],
        'pcb_face': 'TOP',
        'same_face_as_mcu': True,
        'actuation_direction': 'downward onto the controller PCB top face',
        'access_plan': 'Near the lower controller board edge; allow fingers to reach from the inter-board side and press from above, including holding BOOT while operating RESET. Keep the approach, press travel and release clear of the upper board, headers, four-corner supports and wiring. Check clearance with the final mating gap and actual button dimensions.',
        'status': 'placement requirement; no current PCB or assembled access verification',
    },
    'mounting_plan': 'Aligned outlines and four-corner M2 supports; hole coordinates, anti-reverse guidance and spacing pending PCB/thermal/mating checks.',
    'status': 'mechanical plan; no current PCB for either board',
}
for ref,items in proposal['headers'].items():
    for v in items:contract[ref][str(v['pin'])]='SUPPLY' if v['kind']=='power_in' else 'CORE_REF' if v['net']=='3V3_CORE_REF' else v['net']
for base,name in [(CORE,'core_interface'),(BASE,'power_interface')]:
    core=base==CORE;p=page(base,name,'Minimum core GPIO headers' if core else 'Baseboard minimum-core sockets')
    for i,ref in enumerate(['J101','J102']):
        x=91.44+i*200.66
        mpn='PZ254V-12-32P' if core else 'PM254V-12-32-H85';code='C22465940' if core else 'C46595991'
        j=p.inst('Connector_Generic:Conn_02x16_Odd_Even',ref,mpn,x,66.04,fp=('Connector_PinHeader_2.54mm:PinHeader_2x16_P2.54mm_Vertical' if core else 'Connector_PinSocket_2.54mm:PinSocket_2x16_P2.54mm_Vertical'),fields={'Manufacturer':'XFCN','MPN':mpn,'Supplier_PN':code,'Purchase_URL':'https://www.lcsc.com/product-detail/'+code+'.html','Verification':'project_draft','Selection_Status':'P2.54 2x16 candidate; actual mating height, pin1 and land pattern pending','Design_Note':'Core TOP male faces UP into power board BOTTOM socket facing DOWN. Both boards 60x60mm; power above core. Recheck physical pin1/rotation; not Rev D 40-pin compatible.'})
        p.section(ref+' / '+('PA0-15 + PB0-7' if i==0 else 'PB8-15 + PC0-15 + PD/PF/NRST'),20.32+i*200.66,17.78,175)
        for pin,net in contract[ref].items():
            if not core and net in contract['base_unassigned_ports']:
                j.nc(pin);continue
            if net in ['SUPPLY','CORE_REF']:net=contract['supply_alias'][net]['controller' if core else 'inverter']
            j.connect(pin,net,7.62)
    p.text('64 contacts: 52 MCU signal pads + 2 core 5V feed + 2 core 3V3 reference + CTRL_READY + 7 GND.',20.32,116.84,1.25)
    p.text('All MCU GPIOs are exposed by port name. PG10 stays NRST; PF0/PF1 share optional HSE; PB8 shares BOOT.',20.32,132.08,1.15)
    p.text('PC7 is RUN_ARM when plugged into this power base. CTRL_READY = Schmitt-reset-ok AND PC7; default LOW.',20.32,147.32,1.15)
    p.text('Standalone core: regulated 4.75-5.25V at J101 pins1/3 and GND. Do not parallel independent 5V sources.',20.32,162.56,1.15)
    p.text('3V3 reference is core -> base clamps / fault pull-up / SWD sense only. Never parallel base and core regulators.',20.32,177.8,1.15)
    p.text('Application ABZ / SPI / UART / SWD / CAN / LEDs / ADC filters all reside on the power baseboard.',20.32,193.04,1.15)
    p.text('60x60 POWER ABOVE / 60x60 CORE BELOW. Core TOP male -> power BOTTOM socket. Board gap / thermal / button access pending PCB.',20.32,208.28,1.0)
    if not core:
        flag=p.inst('power:PWR_FLAG','#FLG950','PWR_FLAG',365.76,231.14);flag.connect(1,'+3V3_CORE_REF',5.08)
        old=read('base','power_interface')
        for ref,net,x in [('TP16','FAULT_N',76.2),('TP17','ENABLE_IN',238.76)]:t=clone_instance(p,old,ref,x,231.14);t.connect(1,net,5.08)
        p.text('Nine unused socket contacts are NC on this base only; all corresponding GPIO pads remain exposed on the core.',20.32,259.08,1.0)
    finish(p,base)
(REPO/'docs/daughterboard_pin_contract.json').write_text(json.dumps(contract,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def update_top(base,root,names):
    old=read('core' if base==CORE else 'base','controller' if base==CORE else 'inverter')
    old[:]=[n for n in old if not tag(n,'sheet') and not tag(n,'text')]
    for i,(name,title) in enumerate(names):
        x=20.32+(i%3)*127;y=38.1+(i//3)*30.48
        text=(base/(name+'.kicad_sch')).read_text(encoding='utf-8');r=sx.loads(text)
        path='/'+root+'/'+uid(('core/' if base==CORE else 'base/')+'sheet/'+name)
        if base==BASE and name not in ['mcu_coupling','core_signal_protection','sensors','debug_comms','power_interface']:
            # Preserve existing paths for reviewed power sheets, changing only title revision.
            src=read('base','inverter');prior=next(n for n in children(src,'sheet') if props(n).get('Sheetfile')==name+'.kicad_sch')
            sh=copy.deepcopy(prior)
            at=child(sh,'at');dx=x-at[1];dy=y-at[2]
            for n in walk(sh):
                if tag(n,'at'):n[1]+=dx;n[2]+=dy
            for p in children(sh,'property'):
                if p[1]=='Sheetname':p[2]=title
            inst=child(child(sh,'instances'),'project');child(child(inst,'path'),'page')[1]=str(i+2)
            old.append(sh);save(base,name,r);continue
        ident=path.rsplit('/',1)[-1]
        sh=sx.loads(f'(sheet (at {x} {y}) (size 111.76 20.32) (stroke (width .254) (type default)) (fill (color 0 0 0 0)) (uuid "{ident}") (property "Sheetname" "{title}" (at {x} {y-1.27} 0) (effects (font (size 1.27 1.27)) (justify left bottom))) (property "Sheetfile" "{name}.kicad_sch" (at {x} {y+21.59} 0) (effects (font (size 1.0 1.0)) (justify left top))) (instances (project "{"controller" if base==CORE else "inverter"}" (path "/{root}" (page "{i+2}")))))')
        old.append(sh)
    title='STM32G431 minimum-system plug-in core' if base==CORE else 'Inverter base with GPIO minimum-system core'
    save(base,'controller' if base==CORE else 'inverter',old,title)

update_top(CORE,CR,[(n,t) for n,t in [('mcu','MCU and decoupling'),('mcu_analog','Local VDDA and VREF'),('mcu_control','RESET BOOT and optional HSE'),('core_supply','Local power and reset'),('core_arm','Application run permission'),('core_interface','64-pin GPIO headers')]])
bt=read('base','inverter');oldnames=[(props(n)['Sheetfile'].removesuffix('.kicad_sch'),props(n)['Sheetname']) for n in children(bt,'sheet') if props(n)['Sheetfile']!='power_interface.kicad_sch']
update_top(BASE,BR,oldnames+[('mcu_coupling','GPIO command coupling'),('core_signal_protection','ADC and status returns'),('sensors','Encoders and SPI'),('debug_comms','SWD UART CAN and status'),('power_interface','64-pin core sockets')])
print('Authored minimum-system core and application base; 64-pin contract written')

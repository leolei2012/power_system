"""Author the independent controller supply sheet only.

Project-draft selection; do not rerun over later manual edits without review.
This script never writes the controller top, other pages, inverter or public library.
"""
from pathlib import Path
import copy, importlib.util, json, re, sys
import sexpdata as sx

BASE=Path(__file__).resolve().parents[1]
REPO=BASE.parents[2]
spec=importlib.util.spec_from_file_location('supply_author',REPO/'inverter/hardware/tools/schematic_common.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.BASE=BASE; m.LIB=REPO.parent/'kicad_library'; m.PROJECT='controller'
m.ROOT='9dba1312-bd1c-50b2-9df7-fc81461aaf77'
tag, child, children=m.tag,m.child,m.children

# Derivatives use installed, public KiCad geometry. Pin maps are checked below.
derivatives=[]
def derivative(source,name,mpn,fp,maker,lcsc,ds,description):
    z=copy.deepcopy(m.libsymbol(source)); old=source.split(':')[1]
    z[1]=name
    for a in children(z,'symbol'): a[1]=name+a[1][len(old):]
    for key,value in {'Value':mpn,'Footprint':fp,'Datasheet':ds,'Description':description,
                      'Manufacturer':maker,'MPN':mpn,'Supplier':'LCSC','Supplier_PN':lcsc,
                      'Purchase_URL':f'https://www.lcsc.com/product-detail/{lcsc}.html',
                      'Selection_Status':'project_draft; manufacturer pin map checked; no hardware validation',
                      'Symbol_Source':source}.items():
        p=child(z,'property') if False else next((v for v in children(z,'property') if v[1]==key),None)
        if p:p[2]=value
        else:z.append([sx.Symbol('property'),key,value,[sx.Symbol('at'),0,0,0],
                       [sx.Symbol('hide'),sx.Symbol('yes')],
                       [sx.Symbol('effects'),[sx.Symbol('font'),[sx.Symbol('size'),1,1]]]])
    derivatives.append(copy.deepcopy(z))
    z[1]='CoreProtection:'+name; m.cache[z[1]]=z
    return z[1]

buf=derivative('74xGxx:74LVC1G17','SN74LVC1G17DBVR','SN74LVC1G17DBVR',
    'Package_TO_SOT_SMD:SOT-23-5','Texas Instruments','C7836',
    'https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf',
    'Schmitt buffer, Ioff partial power down; DBV pins 1 NC 2 A 3 GND 4 Y 5 VCC')
shunt=derivative('Reference_Voltage:TL431DBZ','TL431BIDBZR','TL431BIDBZR',
    'Package_TO_SOT_SMD:SOT-23','Texas Instruments','C41283',
    'https://www.ti.com/lit/ds/symlink/tl431.pdf','0.5% adjustable shunt; DBZ pins 1 K 2 REF 3 A')
tvs=derivative('Device:D_Zener','SMF6_0A_TP','SMF6.0A-TP',
    'Diode_SMD:D_SOD-123F','MCC','C914434',
    'https://datasheet.lcsc.com/datasheet/pdf/3fdd4d54224eceb5fff57c8ce808199a.pdf?productCode=C914434',
    'Unidirectional TVS; 6V stand-off; 10.3V max at specified 19.4A 10/1000us; not a DC OVP switch')
input_diode=derivative('Device:D','S1A_13_F','S1A-13-F',
    'Diode_SMD:D_SMA','Diodes Incorporated','C150735','https://www.diodes.com/datasheet/download/S1M.pdf',
    '50V 1A low-leakage silicon rectifier; pin 1 cathode / stripe, pin 2 anode')
reverse_diode=derivative('Device:D_Schottky','PMEG2010ER_115','PMEG2010ER,115',
    'Diode_SMD:Nexperia_CFP3_SOD-123W','Nexperia','C82288','https://assets.nexperia.com/documents/data-sheet/PMEG2010ER.pdf',
    '20V 1A low-VF reverse-stress bypass; VF max 250mV at 100mA/25C; pin 1 K 2 A')
lib='(kicad_symbol_lib (version 20250114) (generator "power_system_core_supply")\n'+\
    '\n'.join(sx.dumps(z) for z in derivatives)+')\n'
(BASE/'CoreProtection.kicad_sym').write_text(lib,encoding='utf8')

p=m.Page('core_supply','Controller core - local power and readiness',7)
p.path='/'+m.ROOT+'/743a2735-b1d2-5b0c-8d64-29042bda2c46'
p.uuid='807f7785-23e5-53c6-a409-e4c5cf5723c2'
pos={}; expected={}
orig_render=m.Instance.render
def render(c):
    z=sx.loads(orig_render(c))
    for a in children(z,'property'):
        key=a[1]
        if key in ('Reference','Value'):
            xy=pos.get(c.ref,{}).get(key)
            if xy: child(a,'at')[1:]=[xy[0],xy[1],c.angle%180]
    # Power symbols must not become physical BOM entries.
    if c.ref.startswith('#'):
        child(z,'in_bom')[1]=sx.Symbol('no'); child(z,'on_board')[1]=sx.Symbol('no')
        for a in children(z,'property'):
            if a[1]=='Reference' and not child(a,'hide'):a.append([sx.Symbol('hide'),sx.Symbol('yes')])
    if c.ref.startswith('#FLG'):
        a=next(a for a in children(z,'property') if a[1]=='Value')
        if not child(a,'hide'):a.append([sx.Symbol('hide'),sx.Symbol('yes')])
    return sx.dumps(z)
m.Instance.render=render

def at(c,rx,ry,vx=None,vy=None):
    pos[c.ref]={'Reference':(rx,ry),'Value':(rx if vx is None else vx,ry+2.54 if vy is None else vy)}
    return c
def wire(*pts):
    for a,b in zip(pts,pts[1:]):p.wire(a,b)
def label(net,pt,global_=False,angle=0):p.label(net,pt,angle,global_)
def power(net,pt):
    n=len([c for c in p.components if c.ref.startswith('#PWR')])+73101
    q=p.inst('power:GND' if net=='GND' else 'power:VCC',f'#PWR{n}',net,*pt)
    at(q,pt[0],pt[1]+3.81 if net=='GND' else pt[1]-3.81)
    return q
def flag(pt):
    n=len([c for c in p.components if c.ref.startswith('#FLG')])+73101
    q=p.inst('power:PWR_FLAG',f'#FLG{n}','PWR_FLAG',*pt);at(q,pt[0],pt[1]-3.81);return q
def resistor(ref,value,x,y,angle=0,mpn=None,lcsc=None,fp='Resistor_SMD:R_0603_1608Metric',tol='1%',note=''):
    fields={'Manufacturer':'YAGEO','Supplier':'LCSC','MPN':mpn or 'TBD',
            'Selection_Status':'project_draft' if mpn else 'value assigned; exact YAGEO MPN/LCSC pending',
            'Tolerance':tol,'Design_Note':note}
    if lcsc:fields.update(Supplier_PN=lcsc,Purchase_URL=f'https://www.lcsc.com/product-detail/{lcsc}.html')
    c=p.inst('Device:R',ref,value,x,y,angle,fp=fp,fields=fields)
    return at(c,x+5.08,y-1.27) if angle==0 else at(c,x,y-7.62)
def cap(ref,value,x,y,fp='Capacitor_SMD:C_0603_1608Metric',voltage='16V',note='',mpn=None,lcsc=None,polar=False):
    fields={'Manufacturer':'KEMET' if polar else 'YAGEO','MPN':mpn or 'TBD',
            'Supplier':'LCSC','Voltage_Rating':voltage,'Design_Note':note,
            'Selection_Status':'project_draft' if mpn else 'value assigned; exact YAGEO MPN/LCSC/DC-bias verification pending'}
    if lcsc:fields.update(Supplier_PN=lcsc,Purchase_URL=f'https://www.lcsc.com/product-detail/{lcsc}.html')
    return at(p.inst('Device:C_Polarized' if polar else 'Device:C',ref,value,x,y,fp=fp,fields=fields),x+5.08,y-1.27)
def connect(c,pin,net):expected[(c.ref,str(pin))]=net
def expect(c,mp):
    for a,b in mp.items():connect(c,a,b)

p.section('5 V INPUT / INDEPENDENT 3.3 V MCU RAIL',20.32,17.78,370)
p.text('Regulated baseboard supply: +5V_CORE_IN = 4.75-5.25 V at header. Shared GND; no galvanic isolation.\n100 mA continuous core budget; optional CAN/sensors require a fresh load and thermal budget.',20.32,27.94,1.1)
r301=resistor('R301','0.47',45.72,63.5,90,fp='Resistor_SMD:R_0805_2012Metric',note='Damped input filter; not a surge-rated fuse')
wire((25.4,63.5),r301.pt(1));label('+5V_CORE_IN',(25.4,63.5),True,180)
d101=at(p.inst(tvs,'D101','SMF6.0A-TP',71.12,78.74,270),82.55,76.2)
wire(r301.pt(2),(71.12,63.5),(96.52,63.5))
wire((71.12,63.5),d101.pt(1));wire(d101.pt(2),(71.12,96.52));power('GND',(71.12,96.52));p.junction((71.12,63.5))
c301=cap('C301','4.7u',96.52,78.74,fp='Capacitor_SMD:C_0805_2012Metric',voltage='25V',note='Effective >=2.2uF at 5.25V; protected 5V input decoupling')
wire((96.52,63.5),c301.pt(1));wire(c301.pt(2),(96.52,96.52));power('GND',(96.52,96.52))
d102=at(p.inst(input_diode,'D102','S1A-13-F',124.46,63.5,180),124.46,53.34)
wire((96.52,63.5),d102.pt(2));p.junction((96.52,63.5));label('CORE_5V_TVS',(96.52,63.5))
wire(d102.pt(1),(149.86,63.5),(177.8,63.5))
c302=cap('C302','4.7u',149.86,78.74,fp='Capacitor_SMD:C_0805_2012Metric',voltage='25V',note='Effective >=2.2uF at 5.25V; directly adjacent U101 IN/GND')
wire((149.86,63.5),c302.pt(1));wire(c302.pt(2),(149.86,96.52));power('GND',(149.86,96.52));p.junction((149.86,63.5))
label('CORE_LDO_IN',(177.8,63.5));flag((177.8,63.5))
u101=at(p.inst('MyParts:TLV76733DRVR','U101','TLV76733DRVR',218.44,66.04,
    fields={'Selection_Status':'project_draft; shared reviewed component reused; application not hardware validated'}),218.44,43.18)
wire((177.8,63.5),u101.pt(6));wire(u101.pt(4),(200.66,66.04),(200.66,63.5));p.junction((200.66,63.5))
wire(u101.pt(1),(246.38,63.5),(269.24,63.5),(297.18,63.5),(327.66,63.5))
wire(u101.pt(2),(238.76,66.04),(238.76,63.5));p.junction((238.76,63.5));power('+3V3_MCU',(327.66,63.5))
wire(u101.pt(3),(218.44,96.52));wire(u101.pt(7),(215.9,96.52),(218.44,96.52));power('GND',(218.44,96.52));p.junction((218.44,96.52))
d103=at(p.inst(reverse_diode,'D103','PMEG2010ER,115',213.36,50.8),185.42,40.64)
wire(d103.pt(1),(185.42,50.8),(185.42,63.5));p.junction((185.42,63.5))
wire(d103.pt(2),(246.38,50.8),(246.38,63.5));p.junction((246.38,63.5))
c303=cap('C303','4.7u',269.24,78.74,fp='Capacitor_SMD:C_0805_2012Metric',note='Effective >=2.2uF at 3.3V; U101 OUT capacitor')
c304=cap('C304','100n',297.18,78.74)
for c in [c303,c304]:wire((c.x,63.5),c.pt(1));wire(c.pt(2),(c.x,96.52));power('GND',(c.x,96.52));p.junction((c.x,63.5))
p.text('D102 prevents output/injection current returning to the 5 V header.\nD103 bypasses LDO reverse stress when OUT remains charged.\nTVS clamp is 10.3 V at its specified pulse: U101 accepts up to 16 V.\nNo sustained 24/60 V miswire or IEC surge qualification is claimed.',20.32,109.22,1.05)
p.text('U101 SNS (pin 2) connects to OUT, GND pins 3/5 and EP7 to GND.\nInput/output capacitors and EP thermal copper stay on the core.\nThe 1 A IC rating does not increase the header/core 100 mA budget.',213.36,109.22,1.05)

# Bounded rail absorption: TL431 is normally off, independent of LDO's source-only behavior.
p.section('ADC CLAMP-CURRENT ABSORBER / LOCAL 3.3 V BULK',20.32,139.7,170)
r302=resistor('R302','3.83k 0.1%',55.88,165.1,mpn='RT0603BRD073K83L',lcsc='C861384',tol='0.1%')
r303=resistor('R303','10k 0.1%',55.88,187.96,mpn='RT0603BRD0710KL',lcsc='C95204',tol='0.1%')
u104=at(p.inst(shunt,'U104','TL431BIDBZR',106.68,177.8,90),119.38,174)
wire((55.88,154.94),r302.pt(1));power('+3V3_MCU',(55.88,154.94))
wire(r302.pt(2),(55.88,177.8),r303.pt(1));wire((55.88,177.8),u104.pt(2));p.junction((55.88,177.8));label('CORE_SHUNT_REF',(55.88,177.8))
wire(u104.pt(1),(106.68,154.94),(55.88,154.94));p.junction((55.88,154.94))
wire(u104.pt(3),(106.68,200.66),(55.88,200.66),r303.pt(2));power('GND',(106.68,200.66));p.junction((106.68,200.66))
c305=cap('C305','47u 10% 10V',160.02,177.8,
    fp='Capacitor_Tantalum_SMD:CP_EIA-3528-21_Kemet-B',voltage='10V',
    note='Populate. MnO2 tantalum bulk retains capacitance under bias. TL431 stability compensation; not interchangeable with a nominal MLCC without analysis.',
    mpn='T491B476K010AT',lcsc='C116617',polar=True)
wire(c305.pt(1),(160.02,154.94),(106.68,154.94));p.junction((106.68,154.94))
wire(c305.pt(2),(160.02,200.66),(106.68,200.66))
p.text('Nominal clamp: 2.495 x (1 + 3.83k/10k) + IREF x 3.83k ~ 3.46 V.\nPositive transient injection budget <=50 mA; no hard current limit.\n8 ADC paths: 360R; BASE_READY / FAULT_N: 1k each.\nInputs 5.25 V, rail >=3.25 V, zero diode Vf, resistors -1%: total 48.93 mA.\nThe downstream 100R does not limit rail injection.\nADC RC: (360+100)R x 1nF = 0.46 us; add external source impedance.\nC305 required for shunt stability; validate startup/pulse/ringing on prototype.\nNo sustained 60 V fault immunity is claimed.',20.32,213.36,1.0)

# Supply-valid supervisor has independent 5 V presence gating to resist phantom powering.
p.section('LOCAL RESET / BUFFERED ACTIVE-HIGH PERMISSION',213.36,139.7,177.8)
u102=at(p.inst('MyParts:TPS3808G33DBVR','U102','TPS3808G33DBVR',279.4,182.88,
    fields={'Selection_Status':'project_draft; shared reviewed component reused; application not hardware validated'}),279.4,160.02)
r304=resistor('R304','1k',233.68,172.72)
r305=resistor('R305','1.1k',233.68,195.58)
wire(r304.pt(1),(233.68,160.02));label('CORE_5V_TVS',(233.68,160.02))
wire(r304.pt(2),(233.68,182.88),r305.pt(1));wire((233.68,182.88),u102.pt(3));p.junction((233.68,182.88));label('CORE_MR_5V_PRESENT',(233.68,182.88))
wire(r305.pt(2),(233.68,210.82));power('GND',(233.68,210.82))
wire(u102.pt(6),(279.4,154.94),(314.96,154.94),(355.6,154.94));power('+3V3_MCU',(279.4,154.94))
wire(u102.pt(5),(259.08,180.34),(259.08,154.94),(279.4,154.94));p.junction((279.4,154.94));u102.nc(4)
c306=cap('C306','100n',314.96,167.64)
wire((314.96,154.94),c306.pt(1));wire(c306.pt(2),(314.96,210.82));power('GND',(314.96,210.82));p.junction((314.96,154.94))
wire(u102.pt(2),(279.4,210.82));power('GND',(279.4,210.82))
r306=resistor('R306','10k',327.66,167.64)
wire(r306.pt(1),(327.66,154.94));p.junction((327.66,154.94))
wire(u102.pt(1),(327.66,182.88),r306.pt(2));p.junction((327.66,182.88));label('MCU_RESET_N',(327.66,182.88),True)
u103=at(p.inst(buf,'U103','SN74LVC1G17DBVR',360.68,182.88),360.68,160.02)
wire((327.66,182.88),u103.pt(2));wire(u103.pt(5),(355.6,154.94));p.junction((355.6,154.94))
wire(u103.pt(3),(355.6,210.82));power('GND',(355.6,210.82));u103.nc(1)
wire(u103.pt(4),(388.62,182.88));label('CTRL_READY',(388.62,182.88),True)
c307=cap('C307','100n',383.54,167.64)
wire(c307.pt(1),(383.54,154.94),(355.6,154.94));wire(c307.pt(2),(383.54,210.82));power('GND',(383.54,210.82))
p.text('RESET is open drain; CT open gives nominal 20 ms release delay.\nMR divider requires 5 V presence even if ADC clamps back-power 3.3 V.\nLocal reset button / SWD / C81 remain on debug page.\nOnly CTRL_READY crosses to baseboard; baseboard has a 10k pulldown.\nCTRL_READY indicates power/reset readiness, not successful firmware self-test.',213.36,223.52,1.0)

expect(r301,{1:'+5V_CORE_IN',2:'CORE_5V_TVS'})
expect(d101,{1:'CORE_5V_TVS',2:'GND'});expect(d102,{1:'CORE_LDO_IN',2:'CORE_5V_TVS'});expect(d103,{1:'CORE_LDO_IN',2:'+3V3_MCU'})
expect(u101,{1:'+3V3_MCU',2:'+3V3_MCU',3:'GND',4:'CORE_LDO_IN',5:'GND',6:'CORE_LDO_IN',7:'GND'})
expect(u102,{1:'MCU_RESET_N',2:'GND',3:'CORE_MR_5V_PRESENT',5:'+3V3_MCU',6:'+3V3_MCU'})
expect(u103,{2:'MCU_RESET_N',3:'GND',4:'CTRL_READY',5:'+3V3_MCU'})
expect(u104,{1:'+3V3_MCU',2:'CORE_SHUNT_REF',3:'GND'})
expect(r302,{1:'+3V3_MCU',2:'CORE_SHUNT_REF'});expect(r303,{1:'CORE_SHUNT_REF',2:'GND'})
expect(r304,{1:'CORE_5V_TVS',2:'CORE_MR_5V_PRESENT'});expect(r305,{1:'CORE_MR_5V_PRESENT',2:'GND'});expect(r306,{1:'+3V3_MCU',2:'MCU_RESET_N'})
for c,rail in [(c301,'CORE_5V_TVS'),(c302,'CORE_LDO_IN'),(c303,'+3V3_MCU'),(c304,'+3V3_MCU'),(c305,'+3V3_MCU'),(c306,'+3V3_MCU'),(c307,'+3V3_MCU')]:expect(c,{1:rail,2:'GND'})
flag((71.12,96.52))
p.write()
f=BASE/'core_supply.kicad_sch';s=f.read_text(encoding='utf8')
s=s.replace('(date "2026-11-01") (rev "A-draft")','(date "2026-11-06") (rev "D-split-draft")')
s=s.replace('INVERTER | non-isolated laboratory draft | 12-60 V bus | separate 12-24 V auxiliary','CONTROLLER | local regulated 5 V input | independent 3.3 V | common ground')
f.write_text(s,encoding='utf8')
(BASE/'review/core_supply_expected.json').write_text(json.dumps({
    'pin_nets':{f'{ref}.{pin}':net for (ref,pin),net in expected.items()},
    'no_connect':['U102.4','U103.1'],
    'selected_parts':[{**c.fields,'ref':c.ref} for c in p.components if not c.ref.startswith('#')],
    'supply_budget':{'input_at_header_V':[4.75,5.25],'continuous_core_mA':100,
    'maximum_short_positive_injection_mA':50,'regulator_silicon_rating_A':1,
    'sustained_24V_60V_miswire_protection':False}},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(f'Wrote {f}; {len([c for c in p.components if not c.ref.startswith(chr(35))])} physical components, {len(expected)} pin-net assertions')

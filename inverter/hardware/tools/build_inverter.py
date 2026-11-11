"""Historical Rev A creation record, superseded by integrated Rev B."""
if __name__ == '__main__':
    raise SystemExit('Historical Rev A only. Current native Rev B must not be overwritten; use the archived Rev A to study this record.')
from schematic_common import *

FP_TO263='Package_TO_SOT_SMD:TO-263-3_TabPin2'
def make_local(source,name,properties):
    sym=copy.deepcopy(libsymbol(source)); old=source.split(':')[1]; sym[1]='InverterLocal:'+name
    for s in children(sym,'symbol'): s[1]=s[1].replace(old+'_',name+'_')
    props={p[1]:p for p in children(sym,'property')}
    defaults={'Value':name,'Verification':'project_draft','Library_Revision':'A','Selection_Status':'project draft; public library not modified',
              'ki_keywords':name,'ki_fp_filters':'*','Supplier':'LCSC','Supplier_PN':'','Purchase_URL':''}
    for k,v in (defaults|properties).items():
        if k in props: props[k][2]=v
        else: sym.append(sx.loads(f'(property {q(k)} {q(v)} (at 0 0 0) (hide yes) {effects(1)})'))
    cache['InverterLocal:'+name]=sym
    return sym

locals_=[
make_local('MyParts:IRFB4227PBF','IRFS4227TRLPBF',{
 'Manufacturer':'Infineon','MPN':'IRFS4227TRLPBF','Supplier_PN':'C146578','Footprint':FP_TO263,
 'Datasheet':'https://www.infineon.com/assets/row/public/documents/24/49/infineon-irfs4227-datasheet-en.pdf',
 'Description':'200 V N-MOSFET; IRFS D2PAK; 1 Gate 2 Drain 3 Source; tab is Drain; project draft pin/footprint adaptation','Datasheet_Revision':'PD-96131A (12/06/08)',
 'Selection_Status':'selected MOS; exact G1 D2 S3 and D2PAK confirmed; domestic URL/library review pending'}),
make_local('Transistor_BJT:Q_NPN_BEC','MMBT3904LT1G',{
 'Manufacturer':'onsemi','MPN':'MMBT3904LT1G','Supplier_PN':'C81464','Purchase_URL':'https://item.szlcsc.com/82615.html',
 'Footprint':'Package_TO_SOT_SMD:SOT-23','Datasheet':'https://www.onsemi.com/pdf/datasheet/mmbt3904lt1-d.pdf',
 'Description':'NPN fault output transistor; B1 E2 C3; onsemi SOT-23; project symbol'}),
make_local('Device:D_Schottky_AKA','STPS40150CG_TR_CANDIDATE',{
 'Manufacturer':'STMicroelectronics','MPN':'STPS40150CG-TR','Footprint':FP_TO263,
 'Datasheet':'https://www.st.com/resource/en/datasheet/stps40150c.pdf',
 'Description':'Dual 150 V Schottky; A1=1 K=2 A2=3; tied anodes; main input blocking candidate',
 'Selection_Status':'candidate only; domestic LCSC availability and thermal/current sharing not frozen'}),
]
libout=copy.deepcopy(locals_)
for s in libout: s[1]=s[1].split(':')[1]
(BASE/'InverterLocal.kicad_sym').write_text('(kicad_symbol_lib (version 20251024) (generator "power_system_inverter") (generator_version "1.0")\n'+'\n'.join(sx.dumps(s) for s in libout)+'\n)\n',encoding='utf-8')

names=[('inverter','Inverter - overview and review boundaries'),('aux_input','Inverter - 12-24 V auxiliary input protection'),
('supply_12v','Inverter - regulated 12 V driver supply'),('supply_logic','Inverter - 5 V, 3.3 V and controller supply'),
('bus_brake','Inverter - DC bus input, bulk capacitors and brake'),
('bridge_u','Inverter - U half bridge and low-side shunt'),('bridge_v','Inverter - V half bridge and low-side shunt'),('bridge_w','Inverter - W half bridge and low-side shunt'),
('current_sense','Inverter - three current channels and references'),('voltage_sense','Inverter - voltage and NTC sensing'),
('comparators','Inverter - current, bus voltage and driver rail comparators'),('fault_logic','Inverter - fault aggregation and reset latch'),
('control_interface','Inverter - 24-pin control and six PWM hardware gates')]
pages=[Page(name,title,i+1) for i,(name,title) in enumerate(names)]
overview,aux,drv,logic,bus,bu,bv,bw,current,voltage,comp,fault,interface=pages
manifest={'pages':[dict(name=p.name,title=p.title,page=p.number) for p in pages],'ports':{},'bridges':{},'gates':[],
          'comparators':[],'signals':{},'values':{},'checks_scope':'review draft, not a manufacturing release'}
def conn(p,ref_,x,y,n_,value):
    return p.inst(f'Connector_Generic:Conn_01x{n_:02d}',ref_,value,x,y,fp='',fields={'MPN':'TBD','Supplier':'LCSC','Selection_Status':'connector mechanics, rated current and footprint pending'})
def cap(p,x,y,value,a,b='GND',volts='25V',fp=CFP,dnp=False):
    c=capacitor(p,x,y,value,fp=fp,dnp=dnp);c.fields['Voltage_Rating']=volts
    c.connect(1,a,2.54);c.connect(2,b,2.54);return c
def res(p,x,y,value,a,b,angle=0,fp=RFP,precision='1%',notes='',dnp=False):
    r=resistor(p,x,y,value,angle,dnp,notes);r.fields['Footprint']=fp;r.fields['Tolerance']=precision
    r.connect(1,a,5.08 if angle==90 else 2.54);r.connect(2,b,5.08 if angle==90 else 2.54);return r
def ic(p,name,ref_,x,y,unit=1,**kw): return p.inst('MyParts:'+name,ref_,name.replace('_118',',118'),x,y,unit=unit,**kw)
def flag(p,x,y,net):
    f=p.inst('power:PWR_FLAG',f'#FLG{ref("PF")[2:]}','PWR_FLAG',x,y);f.connect(1,net,2.54)
def supply(p,ref_,libid,x,y,pins):
    u=ic(p,libid,ref_,x,y)
    handled=set()
    for pin,net in pins.items():
        if net is None: u.nc(pin)
        elif u.pt(pin) not in handled: u.connect(pin,net,7.62); handled.add(u.pt(pin))
        else: p.expected.append((ref_,str(pin),net))
    return u
def note(p,text,x=20.32,y=265.43): p.text(text,x,y,1.05)
def add_gate(p,package,unit,kind,a,b,out,x,y):
    name='74LVC08APW_118' if kind=='AND' else '74LVC00APW_118'
    u=ic(p,name,package,x,y,unit)
    pins=sorted(u.pins,key=lambda n_:int(n_))
    ins=[n_ for n_ in pins if next(z[1] for sub in children(u.lib,'symbol') for z in children(sub,'pin') if str(child(z,'number')[1])==n_)==sx.Symbol('input')]
    outs=[n_ for n_ in pins if n_ not in ins]
    assert len(ins)==2 and len(outs)==1
    u.connect(ins[0],a,5.08);u.connect(ins[1],b,5.08)
    if out is None: u.nc(outs[0])
    else: u.connect(outs[0],out,5.08)
    manifest['gates'].append(dict(ref=package,unit=unit,type=kind,a=a,b=b,out=out,pins=[ins[0],ins[1],outs[0]]))
    return u

# 1. Native hierarchy, all named signals use global labels.
overview.section('INVERTER / REV A HARDWARE REVIEW',20.32,17.78,370)
overview.text('12-60 V DC bus / input <=10 A / phase 10 Arms design target / bridge PWM 20 kHz.\nATK-PD6010B-inspired integrated power board; separate auxiliary input and independent hardware trips.',20.32,27.94,1.3)
brief=['TPS26600; RTN separate from GND','TPS55165 buck-boost; VOS_FB = VREG','AP63205 + TPS7A20 + TPS2553 + supervisor',
       '2 x 220 uF + 2 x 2.2 uF; external brake resistor','IRFS4227 x 2 + 2ED2182 + 5 mOhm shunt',
       'IRFS4227 x 2 + 2ED2182 + 5 mOhm shunt','IRFS4227 x 2 + 2ED2182 + 5 mOhm shunt',
       'INA241A1 x 3; 1.65 V and trip references','50:1 divider + buffer x 4; external 10k NTC',
       '6 current windows + bus OV + driver UV','Fault-first latch; delayed reset clock; FAULT_N',
       'Signal-only 24-pin port; six AND-gated PWM']
for i,p in enumerate(pages[1:]):
    x=25.4+(i%3)*127;y=55.88+(i//3)*45.72
    overview.items.append(f'(sheet (at {n(x)} {n(y)}) (size 106.68 22.86) (stroke (width .254) (type default)) (fill (color 0 0 0 0)) (uuid {q(uid("sheet/"+p.name))}) (property "Sheetname" {q(p.title.split(" - ")[1])} (at {n(x)} {n(y-2.54)} 0) {effects(1,"left")}) (property "Sheetfile" {q(p.name+".kicad_sch")} (at {n(x)} {n(y+25.4)} 0) {effects(.9,"left")}) (instances (project "inverter" (path {q("/"+ROOT)} (page {q(p.number)})))))')
    overview.text(brief[i],x+3.81,y+7.62,.95)
note(overview,'No dedicated main-bus precharge/inrush management or discharge resistor. Brake remains controller-commanded.\nRaw PWM U/V/W outputs, following ATK. Optional AC-source LC is NOT silently populated in this draft.\nAll ports are non-isolated / same-reference laboratory use. Connectors, clamp energy and thermal limits remain review items.\nReview design_review.md before PCB. This drawing is not a validated 600 W / 10 Arms operating guarantee.',20.32,243.84)

# 2. Auxiliary eFuse; RTN is intentionally NOT GND.
aux.section('12-24 V AUXILIARY INPUT / SEPARATE FROM THE DC BUS',20.32,17.78,370)
j=conn(aux,'J2',40.64,58.42,2,'AUX: +12..24V / GND');j.connect(1,'AUX_IN');j.connect(2,'GND')
f=aux.inst('Device:Fuse','F2','2A / DC rated TBD',78.74,53.34,angle=90,fp='',fields={'Selection_Status':'auxiliary branch fuse candidate; voltage/I2t/footprint pending'})
f.connect(1,'AUX_IN');f.connect(2,'AUX_FUSED')
cap(aux,106.68,88.9,'1u','AUX_FUSED',volts='100V',fp='Capacitor_SMD:C_0805_2012Metric')
e=supply(aux,'U1','TPS26600PWPR',198.12,88.9,{1:'AUX_FUSED',2:'AUX_FUSED',3:'AUX_UV_DIV',4:None,5:'AUX_OV_DIV',6:'AUX_MODE',7:'AUX_SHDN_N',8:'EFUSE_RTN',9:'GND',10:None,11:'AUX_ILIM',12:'AUX_DVDT',13:None,14:'AUX_FLT_N',15:'AUX_PROTECTED',16:'AUX_PROTECTED',17:'EFUSE_RTN'})
flag(aux,45.72,88.9,'AUX_FUSED');flag(aux,63.5,88.9,'GND')
res(aux,66.04,152.4,'78.7k','AUX_FUSED','AUX_UV_DIV',precision='0.1%')
res(aux,66.04,177.8,'10k','AUX_UV_DIV','EFUSE_RTN',precision='0.1%')
res(aux,124.46,152.4,'221k','AUX_FUSED','AUX_OV_DIV',precision='0.1%')
res(aux,124.46,177.8,'10k','AUX_OV_DIV','EFUSE_RTN',precision='0.1%')
res(aux,182.88,152.4,'402k','AUX_MODE','EFUSE_RTN',notes='402k selects current-limit latch-off; direct RTN would select auto-retry')
res(aux,241.3,152.4,'7.87k','AUX_ILIM','EFUSE_RTN',notes='Nominal 11.8k/R -> 1.50 A; tolerance/SOA/startup review')
cap(aux,299.72,152.4,'22n','AUX_DVDT','EFUSE_RTN')
res(aux,299.72,88.9,'10k','AUX_FLT_N','+3V3_INV')
cap(aux,353.06,88.9,'10u','AUX_PROTECTED',volts='50V',fp='Capacitor_SMD:C_1206_3216Metric')
res(aux,241.3,205.74,'100k','AUX_FUSED','AUX_SHDN_N')
sw=aux.inst('Switch:SW_Push','SW1','AUX_RESET',299.72,210.82,fp='');sw.connect(1,'AUX_SHDN_N');sw.connect(2,'EFUSE_RTN')
note(aux,'RTN / EP (8/17) form a LOCAL eFuse reference island. Do not short to GND (pin 9).\nAll eFuse setting parts return to RTN. MODE uses 402k for latch-off; SHDN button resets AUX supply only.\nNominal UV rising 10.56 V / OV 27.49 V; current limit ~1.50 A; 24 V ramp ~4.22 ms with 22 nF.\nAuxiliary surge source/clamp and AP63205 32 V input coordination remain a release-blocking review item.',20.32,245.11)

# 3. Buck boost 12 V. Use exactly the fixed-12 V application connections.
drv.section('REGULATED 12 V / TPS55165-Q1',20.32,17.78,370)
u=supply(drv,'U2','TPS55165QPWPRQ1',198.12,88.9,{1:'GND',2:'BB_L1',3:'BB_BST1',4:'AUX_PROTECTED',5:'AUX_PROTECTED',6:'AUX_PROTECTED',7:'GND',8:'GND',9:'GND',10:'BB_PG_DLY',11:'BB_VREG',12:'BB_VREG',13:'GND',14:'BB_VREG',15:'DRV_PG_NOM',16:'+12V_DRV',17:'+12V_DRV',18:'GND',19:'BB_BST2',20:'BB_L2',21:'GND'})
l=drv.inst('Device:L','L1','4.7uH / Isat>=5A / DCR<=40m',198.12,43.18,angle=90,fp='',fields={'MPN':'TBD','Supplier':'LCSC','Selection_Status':'Isat target >=5A covers TI 4.5A max internal current limit; exact part/pad/thermal pending'})
l.connect(1,'BB_L1');l.connect(2,'BB_L2')
cap(drv,116.84,66.04,'100n','BB_BST1','BB_L1')
cap(drv,281.94,66.04,'100n','BB_BST2','BB_L2')
cap(drv,55.88,83.82,'10u','AUX_PROTECTED',volts='50V',fp='Capacitor_SMD:C_1206_3216Metric')
cap(drv,55.88,121.92,'470n','AUX_PROTECTED',volts='50V',fp='Capacitor_SMD:C_0805_2012Metric')
cap(drv,335.28,83.82,'22u','+12V_DRV',volts='25V',fp='Capacitor_SMD:C_1210_3225Metric')
cap(drv,335.28,121.92,'100n','+12V_DRV')
cap(drv,116.84,160.02,'4.7u','BB_VREG',volts='10V',fp='Capacitor_SMD:C_0805_2012Metric')
res(drv,198.12,170.18,'100k','BB_PG_DLY','GND')
# 12 V configuration datasheet calls for external 5 V PG pull-up. Divide to 3.3 V logic.
res(drv,281.94,165.1,'10k','+5V_INV','DRV_PG_NOM')
res(drv,335.28,170.18,'10k','DRV_PG_NOM','DRV_PG_LOGIC',angle=90)
res(drv,363.22,195.58,'20k','DRV_PG_LOGIC','GND')
testpoint(drv,91.44,215.9,'+12V_DRV');testpoint(drv,170.18,215.9,'BB_VREG');testpoint(drv,248.92,215.9,'DRV_PG_LOGIC')
note(drv,'VREG_Q and VOS_FB both connect to VREG; VOUT_SENSE connects to the 12 V output. VREG is NOT a load supply.\nIGN follows protected auxiliary input; PS/IGN_PWRL/SS_EN tied low. No MCU boot dependency.\nPG pull-up: 5 V through 10k, then 10k/20k divider -> 2.5 V HIGH (including the pull-up).\nNormal-mode 12 V output budget 0.25 A; low-input capability is 0.6 A subject to datasheet conditions.\n100k PG_DLY uses the documented resistor configuration; timing and inductor DCR/Isat require review.',20.32,246.38)

# 4. 5 V, inverter 3.3 V and independent controller output.
logic.section('5 V BUCK / AP63205',20.32,17.78,165.1)
u=supply(logic,'U3','AP63205WU-7',106.68,66.04,{1:'+5V_INV',2:'AUX_PROTECTED',3:'AUX_PROTECTED',4:'GND',5:'BUCK_SW',6:'BUCK_BST'})
cap(logic,40.64,96.52,'10u','AUX_PROTECTED',volts='50V',fp='Capacitor_SMD:C_1206_3216Metric')
cap(logic,99.06,116.84,'100n','BUCK_BST','BUCK_SW')
l=logic.inst('Device:L','L2','4.7uH / Isat>=5A',154.94,101.6,angle=90,fp='',fields={'MPN':'TBD','Supplier':'LCSC','Selection_Status':'Isat >=5A target; check AP63205 peak/valley limits and short-circuit overshoot; exact part pending'})
l.connect(1,'BUCK_SW');l.connect(2,'+5V_INV')
cap(logic,40.64,144.78,'22u','+5V_INV',volts='16V',fp='Capacitor_SMD:C_1206_3216Metric')
cap(logic,99.06,154.94,'22u','+5V_INV',volts='16V',fp='Capacitor_SMD:C_1206_3216Metric')
flag(logic,172.72,139.7,'+5V_INV')
logic.section('3.3 V LDO + SUPERVISOR',223.52,17.78,165.1)
supply(logic,'U4','TPS7A2033PDBVR',279.4,60.96,{1:'+5V_INV',2:'GND',3:'+5V_INV',4:None,5:'+3V3_INV'})
cap(logic,236.22,99.06,'1u','+5V_INV')
cap(logic,335.28,99.06,'2.2u','+3V3_INV')
supply(logic,'U6','TPS3808G33DBVR',279.4,144.78,{1:'LOGIC_POWER_OK',2:'GND',3:'+3V3_INV',4:None,5:'+3V3_INV',6:'+3V3_INV'})
res(logic,350.52,147.32,'10k','LOGIC_POWER_OK','+3V3_INV')
cap(logic,350.52,185.42,'100n','+3V3_INV')
logic.section('PROTECTED 5 V TO CONTROLLER / INDEPENDENT OF ENABLE',20.32,190.5,180)
supply(logic,'U5','TPS2553QDBVRQ1',106.68,223.52,{1:'+5V_INV',2:'GND',3:'+5V_INV',4:'CTRL_PWR_FLT_N',5:'CTRL_ILIM',6:'+5V_CTRL_OUT'})
res(logic,40.64,259.08,'49.9k','CTRL_ILIM','GND',notes='~0.475..0.582 A datasheet min/max formula at nominal R; resistor tolerance adds error')
res(logic,172.72,248.92,'10k','CTRL_PWR_FLT_N','+3V3_INV')
cap(logic,236.22,223.52,'10u','+5V_CTRL_OUT',volts='16V',fp='Capacitor_SMD:C_0805_2012Metric')
j=conn(logic,'J7',353.06,223.52,2,'CTRL POWER: 5V / GND');j.connect(1,'+5V_CTRL_OUT');j.connect(2,'GND')
testpoint(logic,259.08,241.3,'CTRL_PWR_FLT_N')
note(logic,'3.3 V monitor nominal threshold 3.07 V; CT intentionally open.\nNo motor ENABLE in auxiliary power path. Only one inverter may feed controller J1.\nTPS2553 limit supports a 0.5 A branch budget; select one 5 V source, never parallel two outputs.',20.32,275.59)

# 5. Main bus and separate software-commanded brake power stage.
bus.section('MAIN DC INPUT / NO PRECHARGE OR DEDICATED BLEEDER',20.32,17.78,370)
j=conn(bus,'J3',40.64,53.34,2,'DC INPUT: + / -');j.connect(1,'DC_INPUT_POS');j.connect(2,'GND')
f=bus.inst('Device:Fuse','F1','15A / DC fuse TBD',93.98,48.26,angle=90,fp='',fields={'Selection_Status':'candidate; DC voltage, breaking capacity and I2t pending'})
f.connect(1,'DC_INPUT_POS');f.connect(2,'DC_FUSED')
d=bus.inst('InverterLocal:STPS40150CG_TR_CANDIDATE','D1','STPS40150CG-TR / CANDIDATE',175.26,53.34,angle=180)
d.connect(1,'DC_FUSED');d.connect(3,'DC_FUSED');d.connect(2,'VBUS')
for x in [248.92,304.8]:
    c=bus.inst('MyParts:EKYB101ELL221MK25S',ref('C'),'220u / 100V',x,60.96);c.connect(1,'VBUS');c.connect(2,'GND')
for x in [248.92,304.8]:
    c=bus.inst('MyParts:CS1210KKX7R0BB225',ref('C'),'2.2u / 100V X7R',x,111.76);c.connect(1,'VBUS');c.connect(2,'GND')
tv=bus.inst('Device:D_TVS','D2','SMCJ60CA / CANDIDATE DNP',175.26,106.68,angle=90,fp='Diode_SMD:D_SMC',dnp=True,
    fields={'Manufacturer':'SMC (Sangdest)','MPN':'SMCJ60CA','Supplier_PN':'C3719686','Purchase_URL':'https://item.szlcsc.com/4287506.html',
            'Selection_Status':'DNP candidate; manufacturer datasheet/clamp energy/layout and 100V cap margin require review'})
tv.connect(1,'VBUS');tv.connect(2,'GND')
j=conn(bus,'J4',365.76,109.22,3,'RAW PWM: U / V / W')
for i,ph in enumerate('UVW',1): j.connect(i,ph+'_PHASE')
note(bus,'D1 blocking diode is a new thermal/procurement candidate, not the ATK parallel SS510 copied without review.\nD2 is DNP pending surge/energy verification: 60 V standoff is NOT a 60 V clamp. Candidate clamp 96.8 V gives little 100 V cap margin.\nDirect U/V/W PWM outputs. Optional AC-source LC has not been frozen; external filtering is required for sine-wave source use.',20.32,139.7)
bus.section('BRAKE: EXTERNAL RESISTOR / SEPARATE CONTROL CONNECTOR',20.32,177.8,370)
j=conn(bus,'J5',365.76,213.36,2,'BRAKE POWER: BR+ / BR_SW');j.connect(1,'VBUS');j.connect(2,'BR_SW')
j=conn(bus,'J6',40.64,213.36,2,'BRAKE CTRL: CTRL / GND');j.connect(1,'BRAKE_IN');j.connect(2,'GND')
res(bus,86.36,220.98,'10k','BRAKE_IN','GND')
supply(bus,'U29','UCC27517DBVR',154.94,215.9,{1:'+12V_DRV',2:'GND',3:'BRAKE_IN',4:'GND',5:'BR_DRV'})
cap(bus,101.6,254,'1u','+12V_DRV');cap(bus,157.48,254,'100n','+12V_DRV')
q7=bus.inst('InverterLocal:IRFS4227TRLPBF','Q7','IRFS4227TRLPBF',279.4,220.98)
q7.connect(1,'BR_GATE');q7.connect(2,'BR_SW');q7.connect(3,'GND')
res(bus,220.98,200.66,'15','BR_DRV','BR_GATE',angle=90,fp='Resistor_SMD:R_0805_2012Metric')
res(bus,238.76,251.46,'10k','BR_GATE','GND')
note(bus,'BR+ is DC+; BR_SW is the MOS drain, NOT DC-. External resistor across BR+/BR_SW only; unused port OPEN, never shorted.\n5.6 ohm +/-5%, 1 kW is an external reference target, not a validated continuous rating. BRAKE stays independent of bridge ENABLE/fault.',20.32,278.13)

# 6/7/8. Three physically independent COM/source nodes. No shared COM-to-GND bypass.
for page,ph,dr,high,low,rs in [(bu,'U','U7','Q1','Q2','RS1'),(bv,'V','U8','Q3','Q4','RS2'),(bw,'W','U9','Q5','Q6','RS3')]:
    page.section(f'{ph} HALF BRIDGE / SAME INVERTER PCB',20.32,17.78,370)
    source=f'{ph}_SOURCE';phase=f'{ph}_PHASE'
    supply(page,dr,'2ED2182S06FXUMA1',109.22,86.36,{1:f'{ph}_HIN',2:f'{ph}_LIN',3:source,4:f'{ph}_LO',5:'+12V_DRV',6:phase,7:f'{ph}_HO',8:f'{ph}_BOOT'})
    qh=page.inst('InverterLocal:IRFS4227TRLPBF',high,'IRFS4227TRLPBF',287.02,71.12)
    ql=page.inst('InverterLocal:IRFS4227TRLPBF',low,'IRFS4227TRLPBF',287.02,144.78)
    qh.connect(1,f'{ph}_GATE_H');qh.connect(2,'VBUS')
    ql.connect(1,f'{ph}_GATE_L')
    page.wire(qh.pt(3),(289.56,109.22));page.wire((289.56,109.22),ql.pt(2))
    page.label(phase,(289.56,109.22),0)
    page.expected.extend([(high,'3',phase),(low,'2',phase)])
    res(page,220.98,66.04,'15',f'{ph}_HO',f'{ph}_GATE_H',90,fp='Resistor_SMD:R_0805_2012Metric')
    res(page,220.98,139.7,'15',f'{ph}_LO',f'{ph}_GATE_L',90,fp='Resistor_SMD:R_0805_2012Metric')
    res(page,350.52,76.2,'10k',f'{ph}_GATE_H',phase)
    res(page,350.52,149.86,'10k',f'{ph}_GATE_L',source)
    cap(page,45.72,139.7,'2.2u',f'{ph}_BOOT',phase,'25V','Capacitor_SMD:C_1206_3216Metric')
    cap(page,101.6,139.7,'100n',f'{ph}_BOOT',phase)
    cap(page,45.72,190.5,'4.7u','+12V_DRV',source,'25V','Capacitor_SMD:C_0805_2012Metric')
    cap(page,101.6,190.5,'100n','+12V_DRV',source)
    res(page,170.18,185.42,'10k',f'{ph}_HIN',source)
    res(page,226.06,185.42,'10k',f'{ph}_LIN',source)
    sh=page.inst('Device:R',rs,'5m / 3W / 1%',289.56,210.82,fp='Resistor_SMD:R_2512_6332Metric',fields={
        'Manufacturer':'Milliohm','MPN':'HoJLR2512-3W-5mR-1%','Supplier_PN':'C2903482','Supplier':'LCSC',
        'Selection_Status':'candidate from local manufacturer series datasheet; domestic product URL and thermal/pulse review pending',
        'Design_Note':'2-terminal resistor with Kelvin sense traces; no ground bypass across pads'})
    page.wire(ql.pt(3),(289.56,180.34));page.wire((289.56,180.34),sh.pt(1))
    page.label(source,(289.56,180.34),0)
    page.expected.extend([(low,'3',source),(rs,'1',source)])
    sh.connect(2,'GND')
    flag(page,45.72,231.14,source);flag(page,101.6,231.14,f'{ph}_BOOT')
    testpoint(page,170.18,231.14,phase);testpoint(page,226.06,231.14,source)
    manifest['bridges'][ph]=dict(driver=dr,high=high,low=low,shunt=rs,source=source,phase=phase)
    note(page,'COM goes ONLY to this low MOS source / shunt HIGH pad. Shared AUX return and DC- are on the shunt LOW side.\nLocal VCC capacitors return to SOURCE, bootstrap caps to PHASE, high-gate pulldown to PHASE, low-gate pulldown to SOURCE.\nIntegrated bootstrap diode: no redundant external diode fitted. Bootstrap effective C target >=1 uF; startup recharge/duty limit must be verified.\nGate R=15 ohm initial value; 12 V worst-case gate voltage, gate ringing, deadtime and short-circuit response remain bench checks.',20.32,256.54)

# 9. Three current amplifiers and ratiometric threshold references.
current.section('THREE LOW-SIDE KELVIN CURRENT CHANNELS',20.32,17.78,370)
for i,(ph,ref_) in enumerate(zip('UVW',['U10','U11','U12'])):
    x=81.28+i*124.46
    u=supply(current,ref_,'INA241A1IDDFR',x,76.2,{1:'GND',5:'I_'+ph,6:'+3V3_INV',8:ph+'_SOURCE'})
    u.connect(2,'GND',10.16);current.expected.append((ref_,'4','GND'))
    current.wire(u.pt(3),(x,88.9));current.wire((x,88.9),(x+2.54,88.9));current.wire(u.pt(7),(x+2.54,88.9))
    current.junction((x+2.54,88.9));current.label('VBIAS_1V65',(x+2.54,88.9),0)
    current.expected.extend([(ref_,'3','VBIAS_1V65'),(ref_,'7','VBIAS_1V65')])
    res(current,x,104.14,'47','I_'+ph,'I_'+ph+'_PORT',angle=90,notes='Output isolation at amplifier; trip comparators sense before resistor')
    cap(current,x,124.46,'100n','+3V3_INV')
    testpoint(current,x,154.94,'I_'+ph)
    manifest['signals']['I_'+ph]=dict(ref=ref_,out='5',gain=10,shunt=.005)
current.section('BIAS + CURRENT WINDOW REFERENCES / ALL FROM THE SAME 3.3 V RAIL',20.32,175.26,370)
res(current,45.72,200.66,'10k','+3V3_INV','VBIAS_DIV',precision='0.1%')
res(current,45.72,231.14,'10k','VBIAS_DIV','GND',precision='0.1%')
cap(current,106.68,208.28,'100n','VBIAS_DIV')
supply(current,'U13','TLV9001IDCKR',170.18,210.82,{1:'VBIAS_DIV',2:'GND',3:'VBIAS_1V65',4:'VBIAS_1V65',5:'+3V3_INV'})
cap(current,170.18,248.92,'100n','+3V3_INV')
res(current,254,200.66,'39k','+3V3_INV','OC_LO_MID',precision='0.1%')
res(current,254,220.98,'1.8k','OC_LO_MID','OC_LOW_REF',precision='0.1%')
res(current,254,241.3,'10k','OC_LOW_REF','GND',precision='0.1%')
res(current,350.52,200.66,'10k','+3V3_INV','OC_HIGH_REF',precision='0.1%')
res(current,350.52,220.98,'1.8k','OC_HIGH_REF','OC_HI_MID',precision='0.1%')
res(current,350.52,241.3,'39k','OC_HI_MID','GND',precision='0.1%')
note(current,'I output = 1.65 V + 50 mV/A, positive for shunt current SOURCE -> GND; phase-out sign must be calibrated.\nOC nominal references 0.649606 / 2.650394 V -> +/-20.008 A. Thresholds track local 3.3 V; not precision absolute references.\nLow-side measurement has switching-state blind intervals; the circuit does not guarantee full-cycle short-circuit coverage.',20.32,273.05)

# 10. Four buffered voltage dividers, bus OV reference and external NTC.
voltage.section('FOUR 50:1 VOLTAGE CHANNELS / BUFFERED',20.32,17.78,370)
for i,(sig,source,ref_) in enumerate([('V_DC','VBUS','U14'),('V_U','U_PHASE','U15'),('V_V','V_PHASE','U16'),('V_W','W_PHASE','U17')]):
    x=45.72+i*91.44
    res(voltage,x,55.88,'240k',source,sig+'_DIV1',precision='0.1%',fp='Resistor_SMD:R_0805_2012Metric')
    res(voltage,x,83.82,'240k',sig+'_DIV1',sig+'_DIV2',precision='0.1%',fp='Resistor_SMD:R_0805_2012Metric')
    res(voltage,x,111.76,'10k',sig+'_DIV2',sig+'_DIV',precision='0.1%')
    res(voltage,x,139.7,'10k',sig+'_DIV','GND',precision='0.1%')
    cap(voltage,x+35.56,139.7,'100p' if sig=='V_DC' else '1n',sig+'_DIV')
    supply(voltage,ref_,'TLV9001IDCKR',x+10.16,187.96,{1:sig+'_DIV',2:'GND',3:sig,4:sig,5:'+3V3_INV'})
    res(voltage,x+10.16,210.82,'47',sig,sig+'_PORT',angle=90,notes='Local follower feedback before output isolator; cable and controller ADC RC after resistor')
    cap(voltage,x+10.16,226.06,'100n','+3V3_INV')
    manifest['signals'][sig]=dict(ref=ref_,out='4',ratio=50,raw=source)
voltage.section('65 V OV REFERENCE / EXTERNAL NTC',20.32,246.38,170)
res(voltage,50.8,264.16,'20k','+3V3_INV','OV_REF_1V30',precision='0.1%')
res(voltage,121.92,264.16,'13k','OV_REF_1V30','GND',precision='0.1%')
j=conn(voltage,'J8',274.32,261.62,2,'EXTERNAL 10k NTC');j.connect(1,'TEMP_NTC');j.connect(2,'GND')
res(voltage,223.52,241.3,'10k','+3V3_INV','TEMP_NTC')
cap(voltage,350.52,241.3,'10n','TEMP_NTC')
note(voltage,'Raw phase sense before any external LC; not a filtered AC-source measurement.\nBus RC ~0.98 us; phase RC ~9.8 us. NTC beta, placement and cable protection TBD.',20.32,280.67)

# 11. Healthy-high comparators: no push-pull outputs wired together.
comp.section('EIGHT INDEPENDENT HEALTHY-HIGH COMPARATOR OUTPUTS',20.32,17.78,370)
cmp_defs=[]
for i,ph in enumerate('UVW'):
    cmp_defs.extend([(f'OC_{ph}_HIGH_OK','OC_HIGH_REF','I_'+ph,f'U{18+i}',1),(f'OC_{ph}_LOW_OK','I_'+ph,'OC_LOW_REF',f'U{18+i}',2)])
cmp_defs += [('BUS_OV_OK','OV_REF_1V30','V_DC','U21',1),('DRV_UV_OK','DRV_UV_DIV','OV_REF_1V30','U21',2)]
for i,(out,plus,minus,ref_,unit) in enumerate(cmp_defs):
    x=91.44+(i%4)*91.44;y=66.04+(i//4)*76.2
    u=ic(comp,'TLV3202AIDGK',ref_,x,y,unit)
    mp={'1':out,'2':minus,'3':plus} if unit==1 else {'5':plus,'6':minus,'7':out}
    for pin,net in mp.items(): u.connect(pin,net,5.08)
    manifest['comparators'].append(dict(ref=ref_,unit=unit,plus=plus,minus=minus,out=out,pins=mp))
    comp.text(out,x-20.32,y+17.78,1.05)
for i,ref_ in enumerate(['U18','U19','U20','U21']):
    u=ic(comp,'TLV3202AIDGK',ref_,91.44+i*91.44,208.28,3);u.connect(4,'GND');u.connect(8,'+3V3_INV')
    cap(comp,45.72+i*91.44,208.28,'100n','+3V3_INV')
res(comp,91.44,259.08,'76.1k','+12V_DRV','DRV_UV_DIV',precision='0.1%')
res(comp,182.88,259.08,'10k','DRV_UV_DIV','GND',precision='0.1%')
note(comp,'Healthy = HIGH. Any current outside the window, bus above ~65 V, or driver rail below ~11.193 V drives its own output LOW.\nComparator outputs are push-pull and each enters a separate AND input. No wired-AND connection.\nNo intentional comparator hysteresis in Rev A; hardware latches the first event. Noise/threshold spread/total delay need validation.',20.32,275.59)

# 12. Protection logic. Async /R stays HIGH; fault only uses /S, clock clears Q with D=0.
fault.section('FAULT AGGREGATION / EVERY INPUT HEALTHY-HIGH',20.32,17.78,370)
health=[v[0] for v in cmp_defs]+['LOGIC_POWER_OK','DRV_PG_LOGIC','AUX_FLT_N']
counter=0
and_alloc=[]
for i in range(10):
    a=health[0] if i==0 else f'HEALTH_CHAIN_{i}'
    b=health[i+1]
    out='HEALTH_ALL' if i==9 else f'HEALTH_CHAIN_{i+1}'
    package=f'U{22+i//4}';unit=i%4+1
    add_gate(fault,package,unit,'AND',a,b,out,76.2+(i%5)*73.66,55.88+(i//5)*45.72)
add_gate(fault,'U27',1,'NAND','ENABLE_IN','ENABLE_IN','ENABLE_N',60.96,157.48)
add_gate(fault,'U24',3,'AND','HEALTH_ALL','ENABLE_N','RESET_REQUEST',134.62,157.48)
res(fault,198.12,157.48,'10k','RESET_REQUEST','RESET_CLK',angle=90)
cap(fault,238.76,172.72,'10n','RESET_CLK')
u=ic(fault,'74LVC74AD_118','U28',299.72,157.48,1)
for pin,net in {1:'+3V3_INV',2:'GND',3:'RESET_CLK',4:'HEALTH_ALL',5:'FAULT_LATCH',6:'NO_LATCH'}.items():u.connect(pin,net,5.08)
add_gate(fault,'U24',4,'AND','HEALTH_ALL','NO_LATCH','HEALTH_UNLATCHED',60.96,215.9)
add_gate(fault,'U25',1,'AND','HEALTH_UNLATCHED','ENABLE_IN','DRIVE_PERMIT',134.62,215.9)
add_gate(fault,'U27',2,'NAND','HEALTH_ALL','NO_LATCH','FAULT_ACTIVE',208.28,215.9)
res(fault,269.24,215.9,'10k','FAULT_ACTIVE','FAULT_BASE',angle=90)
q8=fault.inst('InverterLocal:MMBT3904LT1G','Q8','MMBT3904LT1G',350.52,215.9)
q8.connect(1,'FAULT_BASE');q8.connect(2,'GND');q8.connect(3,'FAULT_N')
res(fault,299.72,238.76,'100k','FAULT_BASE','GND')
testpoint(fault,350.52,124.46,'FAULT_LATCH')
note(fault,'/R permanently HIGH; /S=HEALTH_ALL, D=0. Illegal /S=/R=LOW is structurally avoided.\nFault asynchronously sets Q=1. Healthy AND ENABLE=LOW charges reset CLK through 10k/10n (100 us nominal RC).\nClock has Schmitt inputs per Nexperia Rev 13. Fault removal precedes the delayed clearing edge.\nFault and power loss block DRIVE_PERMIT directly; ENABLE held HIGH cannot restart on recovery.\nHold ENABLE LOW >=1 ms after fault removal. Very short faults during a reset may require a new deliberate disable cycle.\nFAULT_N is an NPN open-collector notification; a fully unpowered inverter cannot assert it. No power-present/connector detection claimed.',20.32,245.11)

# 13. Connector wiring matches controller Rev A. Six AND gates have local input pull-downs at driver pages.
interface.section('SIGNAL-ONLY 24-PIN PORT / MATCHES CONTROLLER REV A',20.32,17.78,180)
j=conn(interface,'J1',81.28,76.2,24,'CTRL 24P / 0.5mm TBD')
mapping={1:'PWM_UH_IN',2:'PWM_UL_IN',3:'GND',4:'PWM_VH_IN',5:'PWM_VL_IN',6:'GND',7:'PWM_WH_IN',8:'PWM_WL_IN',9:'GND',10:'ENABLE_IN',11:'FAULT_N',12:None,13:'GND',14:'I_U_PORT',15:'I_V_PORT',16:'I_W_PORT',17:'GND',18:'V_DC_PORT',19:'V_U_PORT',20:'V_V_PORT',21:'GND',22:'V_W_PORT',23:'TEMP_NTC',24:None}
for pin,net in mapping.items():
    if net is None:j.nc(pin)
    else:j.connect(pin,net)
manifest['ports']['J1']={str(k):v for k,v in mapping.items()}
interface.section('HARDWARE PWM GATES / ALL SIX COMMANDS BLOCKED',208.28,17.78,180)
for i,suffix in enumerate(['UH','UL','VH','VL','WH','WL']):
    out=f'{suffix[0]}_{"HIN" if suffix[1]=="H" else "LIN"}'
    # AND indices 13..18 after thirteen aggregate/reset/permit gates.
    index=13+i
    add_gate(interface,f'U{22+index//4}',index%4+1,'AND',f'PWM_{suffix}_IN','DRIVE_PERMIT',out,302.26,55.88+i*27.94)
    res(interface,365.76,55.88+i*27.94,'10k',f'PWM_{suffix}_IN','GND')
res(interface,160.02,63.5,'10k','ENABLE_IN','GND')
res(interface,160.02,101.6,'100k','DRIVE_PERMIT','GND')
interface.text('GND contacts: 3/6/9/13/17/21. Reserved 12/24 remain NC.\nNo supply on this port. Local analog outputs feed controller RC inputs.\nAll grounds share this inverter DC- only in the same-reference draft.\nFAULT_N pull-up is on controller. This port is not an isolation barrier.',20.32,127.0,1.0)
interface.section('LOGIC POWER / UNUSED UNITS DEFINED',20.32,162.56,180)
for i,ref_ in enumerate(['U22','U23','U24','U25','U26','U27']):
    x=40.64+(i%3)*66.04;y=195.58+(i//3)*45.72
    name='74LVC00APW_118' if ref_=='U27' else '74LVC08APW_118'
    u=ic(interface,name,ref_,x,y,5);u.connect(7,'GND');u.connect(14,'+3V3_INV')
    cap(interface,x+30.48,y,'100n','+3V3_INV')
# One AND gate and two NAND gates unused; inputs tied, outputs left explicitly NC.
add_gate(interface,'U26',4,'AND','GND','GND',None,248.92,241.3)
add_gate(interface,'U27',3,'NAND','GND','GND',None,302.26,241.3)
add_gate(interface,'U27',4,'NAND','GND','GND',None,360.68,241.3)
# Unused latch and latch power on the protection sheet (kept out of the PWM drawing grid).
u=ic(current,'74LVC74AD_118','U28',152.4,129.54,2)
for pin,net in {10:'+3V3_INV',11:'GND',12:'GND',13:'+3V3_INV'}.items():u.connect(pin,net,2.54)
u.nc(8);u.nc(9)
u=ic(current,'74LVC74AD_118','U28',281.94,134.62,3);u.connect(7,'GND',2.54);u.connect(14,'+3V3_INV',2.54)
cap(current,281.94,160.02,'100n','+3V3_INV')

# Persist native sheets, designator BOM and topology metadata.
for p in pages:p.write()
(BASE/'inverter.kicad_pro').write_text('{}\n',encoding='utf-8')
(BASE/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "MyParts") (type "KiCad") (uri "${KIPRJMOD}/../../../kicad_library/symbols/MyParts.kicad_sym") (options "") (descr "Shared library; read only")) (lib (name "InverterLocal") (type "KiCad") (uri "${KIPRJMOD}/InverterLocal.kicad_sym") (options "") (descr "Explicit project draft parts; not public reviewed library")))\n',encoding='utf-8')
(BASE/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "MyFootprints") (type "KiCad") (uri "${KIPRJMOD}/../../../kicad_library/footprints/MyFootprints.pretty") (options "") (descr "Shared footprints")))\n',encoding='utf-8')
out=BASE/'review';out.mkdir(exist_ok=True)
unique={}
for p in pages:
    for c in p.components:
        if c.ref.startswith('#'):continue
        unique.setdefault(c.ref,(p,c))
with (out/'bom.csv').open('w',encoding='utf-8-sig',newline='') as f:
    fields=['Reference','Value','Quantity','DNP','Sheet','Manufacturer','MPN','Supplier_PN','Purchase_URL','Footprint','Voltage_Rating','Tolerance','Design_Note','Selection_Status']
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for p,c in unique.values():w.writerow(dict(Reference=c.ref,Value=c.value,Quantity=1,DNP='yes' if c.dnp else 'no',Sheet=p.name,**{k:c.fields.get(k,'') for k in fields[5:]}))
with (out/'expected_pin_nets.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['Sheet','Reference','Pin','Net'])
    for p in pages:w.writerows((p.name,*r) for r in p.expected if not r[0].startswith('#'))
manifest['component_count']=len(unique)
(out/'design_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sources={}
for libid in cache:
    nick=libid.split(':')[0]
    p=LIB/'symbols/MyParts.kicad_sym' if nick=='MyParts' else BASE/'InverterLocal.kicad_sym' if nick=='InverterLocal' else STD/f'{nick}.kicad_sym'
    sources[p.as_posix()]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(out/'library_sources.json').write_text(json.dumps(sources,indent=2)+'\n',encoding='utf-8')
print(f'Created {len(pages)} sheets, {len(unique)} physical component records; project-only draft symbols saved.')

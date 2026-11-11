"""Create the reviewable Rev A controller schematic using installed KiCad libraries.

Authoring helper only. Do not rerun over subsequent manual KiCad edits without review.
Requires Python + sexpdata; KiCad CLI is used separately for ERC and export.
"""
from pathlib import Path
from collections import Counter
import copy
import csv
import hashlib
import json
import math
import uuid
import sexpdata as sx

BASE = Path(__file__).resolve().parents[1]
LIB = BASE.parents[2] / 'kicad_library'
STD = Path('C:/Program Files/KiCad/10.0/share/kicad/symbols')
PROJECT = 'controller'
NS = uuid.UUID('b7372029-c19b-46c0-9a81-17032c28b346')
def uid(key): return str(uuid.uuid5(NS, key))
def q(s): return json.dumps(str(s), ensure_ascii=False)
def n(v): return f'{v:.4f}'.rstrip('0').rstrip('.') if isinstance(v, float) else str(v)
def tag(x, name): return isinstance(x, list) and len(x) and str(x[0]) == name
def child(x, name): return next((v for v in x if tag(v, name)), None)
def children(x, name): return [v for v in x if tag(v, name)]
def effects(size=1.0, justify='', bold=False):
    return f'(effects (font (size {size} {size}) {"(bold yes)" if bold else ""}) {f"(justify {justify})" if justify else ""})'

cache = {}
library_files = {}
def libsymbol(libid):
    if libid in cache: return cache[libid]
    nick, name = libid.split(':', 1)
    p = LIB/'symbols/MyParts.kicad_sym' if nick == 'MyParts' else STD/f'{nick}.kicad_sym'
    if p not in library_files: library_files[p] = sx.load(p.open(encoding='utf-8'))
    data = library_files[p]
    v = copy.deepcopy(next(x for x in data if tag(x, 'symbol') and x[1] == name))
    if child(v, 'extends'):
        raise ValueError(f'Inherited symbol must be resolved explicitly: {libid}')
    v[1] = libid
    cache[libid] = v
    return v

class Instance:
    def __init__(self, page, libid, ref, value, x, y, angle=0, unit=1, fp=None, fields=None, dnp=False):
        self.page, self.libid, self.ref, self.value = page, libid, ref, value
        self.x, self.y, self.angle, self.unit = x, y, angle, unit
        self.uuid = uid(f'{page.name}/{ref}/{unit}')
        self.lib = libsymbol(libid)
        self.fields = {str(p[1]): str(p[2]) for p in children(self.lib, 'property')}
        self.fields.update(fields or {})
        self.fields.update(Reference=ref, Value=value)
        if fp is not None: self.fields['Footprint'] = fp
        self.dnp = dnp
        self.pins = {}
        for sym in children(self.lib, 'symbol'):
            symunit = int(sym[1].rsplit('_', 2)[1])
            if symunit not in (0, unit): continue
            for pin in children(sym, 'pin'):
                number = str(child(pin, 'number')[1])
                px, py, pa = child(pin, 'at')[1:]
                a = math.radians(angle)
                self.pins[number] = (round(x+px*math.cos(a)-py*math.sin(a), 4),
                                     round(y-px*math.sin(a)-py*math.cos(a), 4), (pa+angle)%360)
        page.components.append(self)
    def pt(self, pin): return self.pins[str(pin)][:2]
    def connect(self, pin, net, length=5.08, global_=True):
        px, py, pa = self.pins[str(pin)]
        dx = -math.cos(math.radians(pa))*length
        dy = math.sin(math.radians(pa))*length
        end = (round(px+dx, 4), round(py+dy, 4))
        self.page.wire((px,py), end)
        self.page.label(net, end, 180 if dx<=0 else 0, global_)
        self.page.expected.append((self.ref, str(pin), net))
    def nc(self, pin): self.page.nc(self.pt(pin))
    def render(self):
        out = [f'(symbol (lib_id {q(self.libid)}) (at {n(self.x)} {n(self.y)} {self.angle}) (unit {self.unit})',
               f'(in_bom yes) (on_board yes) (dnp {"yes" if self.dnp else "no"}) (uuid {q(self.uuid)})']
        for key, value in self.fields.items():
            visible = key in ('Reference','Value')
            px, py = self.x, self.y-8.89
            if self.libid == 'Device:R' or self.libid == 'Device:C':
                px, py = (self.x, self.y-4.445) if self.angle == 90 else (self.x+3.81, self.y-1.27)
            elif self.libid.startswith('Connector_Generic:'):
                loc = child(next(s for s in children(self.lib,'symbol') if children(s,'pin')), 'pin')
                miny = min(p[1] for p in self.pins.values())
                px, py = self.x, miny-7.62
            elif self.libid == 'MyParts:LKS32MC451VCT8': px, py = self.x, self.y-27.94
            if key == 'Value': py += 2.54
            out.append(f'(property {q(key)} {q(value)} (at {n(px)} {n(py)} {self.angle}) {"" if visible else "(hide yes)"} {effects(1.0 if visible else 0.9)})')
        for pin in self.pins: out.append(f'(pin {q(pin)} (uuid {q(uid(self.uuid+"/pin/"+pin))}))')
        out.append(f'(instances (project {q(PROJECT)} (path {q(self.page.path)} (reference {q(self.ref)}) (unit {self.unit})))) )')
        return '\n'.join(out)

ROOT = uid('controller-root')
class Page:
    def __init__(self, name, title, number):
        self.name, self.title, self.number = name, title, str(number)
        self.uuid = ROOT if name=='controller' else uid('page/'+name)
        self.path = '/'+ROOT if name=='controller' else '/'+ROOT+'/'+uid('sheet/'+name)
        self.components, self.items, self.expected = [], [], []
        self.seq=0
    def id(self):
        self.seq+=1
        return uid(f'{self.name}/item/{self.seq}')
    def wire(self, a, b):
        if a==b: return
        self.items.append(f'(wire (pts (xy {n(a[0])} {n(a[1])}) (xy {n(b[0])} {n(b[1])})) (stroke (width 0) (type default)) (uuid {q(self.id())}))')
    def junction(self, p): self.items.append(f'(junction (at {n(p[0])} {n(p[1])}) (diameter 0) (color 0 0 0 0) (uuid {q(self.id())}))')
    def nc(self, p): self.items.append(f'(no_connect (at {n(p[0])} {n(p[1])}) (uuid {q(self.id())}))')
    def label(self, net, p, angle=0, global_=True):
        kind = 'global_label' if global_ else 'label'
        self.items.append(f'({kind} {q(net)} {"(shape passive)" if global_ else ""} (at {n(p[0])} {n(p[1])} {angle}) {effects(.88,"left" if angle==0 else "right")} (uuid {q(self.id())}))')
    def text(self, text, x, y, size=1.15, bold=False):
        self.items.append(f'(text {q(text)} (at {n(x)} {n(y)} 0) {effects(size,"left top",bold)} (uuid {q(self.id())}))')
    def line(self,x1,y1,x2,y2):
        self.items.append(f'(polyline (pts (xy {n(x1)} {n(y1)}) (xy {n(x2)} {n(y2)})) (stroke (width .254) (type default)) (fill (type none)) (uuid {q(self.id())}))')
    def section(self,text,x,y,w=170):
        self.text(text,x,y,1.6,True); self.line(x,y+5.08,x+w,y+5.08)
    def inst(self,*args,**kw): return Instance(self,*args,**kw)
    def write(self):
        symbols = {c.libid:c.lib for c in self.components}
        content=[f'(kicad_sch (version 20250114) (generator "power_system_controller") (generator_version "1.0") (uuid {q(self.uuid)}) (paper "A3")',
        f'(title_block (title {q(self.title)}) (date "2026-11-01") (rev "A-draft") (company "power_system") (comment 1 "HARDWARE REVIEW DRAFT - NOT RELEASED FOR PCB") (comment 2 "LKS32MC451VCT8 | single reference GND | 5 V input only"))',
        '(lib_symbols '+'\n'.join(sx.dumps(v) for v in symbols.values())+')']
        content+=self.items+[c.render() for c in self.components]
        if self.name=='controller': content+=['(sheet_instances (path "/" (page "1")))']
        content+=['(embedded_fonts no))']
        (BASE/f'{self.name}.kicad_sch').write_text('\n'.join(content)+'\n',encoding='utf-8')

counts=Counter()
def ref(prefix): counts[prefix]+=1; return f'{prefix}{counts[prefix]}'
RFP='Resistor_SMD:R_0603_1608Metric'
CFP='Capacitor_SMD:C_0603_1608Metric'
def resistor(p,x,y,value='10k',angle=0,dnp=False,notes=''):
    return p.inst('Device:R',ref('R'),value,x,y,angle,fp=RFP,fields={'Manufacturer':'YAGEO','MPN':'TBD','Supplier':'LCSC','Selection_Status':'value assigned; exact MPN/LCSC pending','Design_Note':notes},dnp=dnp)
def capacitor(p,x,y,value='100n',fp=CFP,dnp=False,notes=''):
    return p.inst('Device:C',ref('C'),value,x,y,fp=fp,fields={'Manufacturer':'YAGEO','MPN':'TBD','Voltage_Rating':'16 V minimum','Design_Note':notes,'Supplier':'LCSC','Selection_Status':'value assigned; DC bias/MPN/LCSC pending'},dnp=dnp)
def shunt(p,x,y,net,value='100n',**kw):
    c=capacitor(p,x,y,value,**kw); c.connect(1,net,1.27); c.connect(2,'GND',1.27); return c
def pull(p,x,y,net,rail='GND',value='10k',dnp=False):
    r=resistor(p,x,y,value,dnp=dnp); r.connect(1,net,2.54); r.connect(2,rail,2.54); return r
def series(p,x,y,a,b,value='33',dnp=False):
    r=resistor(p,x,y,value,90,dnp); r.connect(1,a,5.08); r.connect(2,b,5.08); return r
def connector(p,x,y,count,name,fp='',dnp=False):
    return p.inst(f'Connector_Generic:Conn_01x{count:02d}',ref('J'),name,x,y,fp=fp,dnp=dnp,
        fields={'MPN':'TBD','Supplier':'LCSC','Selection_Status':'pin order draft; exact connector/footprint pending'})
def testpoint(p,x,y,net):
    t=p.inst('Connector:TestPoint',ref('TP'),net,x,y,fp='TestPoint:TestPoint_Pad_D1.5mm')
    t.connect(1,net,2.54); return t

def output_with_pull(p,x,y,net,port,rail='GND',value='33',pull_value='10k'):
    r=resistor(p,x,y,value,90)
    r.connect(1,net,7.62)
    rx=x+63.5
    rp=resistor(p,rx,y+6.35,pull_value)
    p.wire(r.pt(2),(rx,y)); p.wire((rx,y),rp.pt(1)); p.junction((rx,y))
    p.label(port,(rx,y),0)
    rp.connect(2,rail,1.27)
    p.expected.extend([(r.ref,'2',port),(rp.ref,'1',port)])
    return r,rp

def adc_filter(p,x,y,port,net):
    r=resistor(p,x,y,'100',90)
    r.connect(1,port,7.62)
    cx=x+50.8
    c=capacitor(p,cx,y+6.35,'1n',notes='Provisional RC; source impedance/acquisition and overvoltage protection review pending')
    p.wire(r.pt(2),(cx,y)); p.wire((cx,y),c.pt(1)); p.junction((cx,y))
    p.label(net,(cx,y),0)
    c.connect(2,'GND',1.27)
    p.expected.extend([(r.ref,'2',net),(c.ref,'1',net)])
    return r,c

pages=[Page('controller','Controller - Overview and design boundaries',1),
       Page('power','Controller - 5 V input, 3.3 V and supervision',2),
       Page('mcu','Controller - LKS32MC451VCT8 signal assignment',3),
       Page('inverter_1','Controller - Inverter 1 signal port and brake',4),
       Page('inverter_2','Controller - Inverter 2 signal port and brake',5),
       Page('pfc','Controller - Dedicated Boost / Vienna control port',6),
       Page('sensors','Controller - ABZ encoder ports',7),
       Page('spi','Controller - Two independent SPI expansion ports',8),
       Page('debug_comms','Controller - SWD, UART, CAN and status LEDs',9)]
overview,power,mcu,inv1,inv2,pfc,sensors,spi,debug=pages
plan=list(csv.DictReader((BASE/'LKS32MC451VCT8_pin_plan.csv').open(encoding='utf-8-sig')))
by_pin={r['Pin']:r for r in plan}

# Overview: native hierarchy is navigable; named global nets connect functional pages.
overview.section('CONTROLLER / REV A HARDWARE REVIEW',20.32,17.78,370)
overview.text('One LKS32MC451VCT8; 2 inverter ports + 1 dedicated PFC port. No LLC, USB or Hall.\nAll sheets share the explicitly named global nets. All external ports are NON-ISOLATED in this draft.',20.32,27.94,1.4)
for i,p in enumerate(pages[1:]):
    x=25.4+(i%3)*127; y=63.5+(i//3)*58.42
    name=p.title.split(' - ')[1]
    overview.items.append(f'(sheet (at {n(x)} {n(y)}) (size 106.68 25.4) (stroke (width .254) (type default)) (fill (color 0 0 0 0)) (uuid {q(uid("sheet/"+p.name))}) (property "Sheetname" {q(name)} (at {n(x)} {n(y-2.54)} 0) {effects(1.15,"left")}) (property "Sheetfile" {q(p.name+".kicad_sch")} (at {n(x)} {n(y+27.94)} 0) {effects(1,"left")}) (instances (project "controller" (path {q("/"+ROOT)} (page {q(p.number)})))))')
    descriptions={
        'power':'5 V input -> TLV76733 -> 3.3 V\nTPS3808G33 reset and MCU decoupling',
        'mcu':'U1A/B/C + crystal + reserved test pads\nPhysical pin numbers follow the 100-pin CSV',
        'inverter_1':'J2: six PWM + enable + fault + eight ADC\nJ3: separate brake command',
        'inverter_2':'J4: six PWM + enable + fault + eight ADC\nJ5: separate brake command',
        'pfc':'J6: six gate commands + nine ADC\nEnable, fault and future precharge command',
        'sensors':'J7/J8: independent A/B/Z inputs\n3.3 V single-ended draft; optional power DNP',
        'spi':'J9/J10: independent SPI_A / SPI_B\nCS pull-ups; optional sensor power DNP',
        'debug_comms':'J11 SWD / J12 UART / J13 CAN option\nReset, five status LEDs; CAN defaults DNP'}
    overview.text(descriptions[p.name],x+5.08,y+7.62,1.0)
overview.text('REVIEW BOUNDARIES\n1. Only a regulated 5 V source enters J1; select one inverter supply. No parallel supplies.\n2. Three 24-pin ports carry signals only; no bus power or sensor supply on these ports.\n3. GND/AGND contact positions share controller GND. Different power reference domains require isolation.\n4. ABZ is provisionally 3.3 V single-ended. Do not connect 5 V / differential encoders directly.\n5. Connector mechanics, crystal loading, ESD/clamps and component procurement remain review items.\n6. PFC timing / ADC scheduling are not proven by this schematic. See design_review.md.',20.32,239,1.1)

# Power and reset.
power.section('5 V AUXILIARY INPUT -> 3.3 V',20.32,17.78)
j=connector(power,40.64,48.26,2,'5V_IN_ONLY')
j.connect(1,'+5V_CTRL'); j.connect(2,'GND')
for net,x in [('+5V_CTRL',60.96),('GND',76.2)]:
    f=power.inst('power:PWR_FLAG',f'#FLG0{1 if net=="+5V_CTRL" else 2}','PWR_FLAG',x,38.1)
    f.connect(1,net,2.54)
cin=capacitor(power,71.12,60.96,'10u',fp='Capacitor_SMD:C_0805_2012Metric')
cin_hf=capacitor(power,96.52,60.96,'100n')
ldo=power.inst('MyParts:TLV76733DRVR','U2','TLV76733DRVR',139.7,50.8)
power.label('+5V_CTRL',(60.96,48.26),180)
for a,b in [(60.96,71.12),(71.12,96.52),(96.52,124.46),(124.46,132.08)]: power.wire((a,48.26),(b,48.26))
power.wire(ldo.pt(4),(124.46,50.8)); power.wire((124.46,50.8),(124.46,48.26)); power.junction((124.46,48.26))
cout=capacitor(power,175.26,60.96,'10u',fp='Capacitor_SMD:C_0805_2012Metric')
cout_hf=capacitor(power,200.66,60.96,'100n')
for a,b in [(147.32,160.02),(160.02,175.26),(175.26,200.66)]: power.wire((a,48.26),(b,48.26))
power.label('+3V3_MCU',(200.66,48.26),0)
power.wire(ldo.pt(2),(160.02,50.8)); power.wire((160.02,50.8),(160.02,48.26)); power.junction((160.02,48.26))
for c,net in [(cin,'+5V_CTRL'),(cin_hf,'+5V_CTRL'),(cout,'+3V3_MCU'),(cout_hf,'+3V3_MCU')]:
    power.wire((c.x,48.26),c.pt(1)); power.junction((c.x,48.26)); c.connect(2,'GND',2.54)
    power.expected.append((c.ref,'1',net))
power.wire(ldo.pt(7),(137.16,66.04)); power.wire((137.16,66.04),(139.7,66.04))
power.wire(ldo.pt(3),(139.7,66.04)); power.junction((139.7,66.04)); power.label('GND',(139.7,66.04),0)
power.expected.extend([('U2','6','+5V_CTRL'),('U2','4','+5V_CTRL'),('U2','1','+3V3_MCU'),('U2','2','+3V3_MCU'),('U2','3','GND'),('U2','5','GND'),('U2','7','GND')])
power.text('U2: EN follows input; SNS tied to OUT. All GND pins and EP go to GND.\nCIN/COUT: 10 uF X7R/X5R, >=16 V, 0805; verify effective C >=1 uF.\nBudget: 250 mA -> (5-3.3)*0.25 = 0.425 W. Copper/EP thermal review required.\n5 V input protection/current limit is on the designated inverter (TPS2553 branch).',20.32,88.9,1.15)
power.section('POWER MONITOR / MCU RESET',231.14,17.78,157.48)
supervisor=power.inst('MyParts:TPS3808G33DBVR','U3','TPS3808G33DBVR',297.18,55.88)
for pin,net in [(1,'MCU_NRST'),(2,'GND'),(3,'RESET_BUTTON_N'),(5,'+3V3_MCU'),(6,'+3V3_MCU')]: supervisor.connect(pin,net)
supervisor.nc(4)  # Datasheet explicit open-CT delay selection, not an unfinished pin.
shunt(power,340.36,45.72,'+3V3_MCU')
pull(power,340.36,76.2,'MCU_NRST','+3V3_MCU')
pull(power,264.16,96.52,'RESET_BUTTON_N','+3V3_MCU')
sw=power.inst('Switch:SW_Push','SW1','RESET',299.72,101.6,fp='')
sw.connect(1,'RESET_BUTTON_N'); sw.connect(2,'GND')
power.text('G33 nominal falling threshold 3.07 V. CT intentionally open: 20 ms nominal release.\nSW1 drives MR; SWD NRST also directly pulls MCU_NRST low.\nRESET is open-drain, with 10k pull-up. No large reset capacitor on the SWD line.',231.14,124.46,1.05)
power.section('MCU POWER UNIT / LOCAL DECOUPLING',20.32,144.78,370)
u=power.inst('MyParts:LKS32MC451VCT8','U1','LKS32MC451VCT8',86.36,205.74,unit=4)
for pin in u.pins:
    r=by_pin[pin]
    if r['State']=='nc': u.nc(pin)
    else: u.connect(pin,r['Net'])
for i,pin in enumerate([14,42,71,92,93]):
    x=160.02+i*45.72
    shunt(power,x,193.04,'+3V3_MCU','100n',notes=f'Place next to U1 AVDD pin {pin}')
    power.text(f'AVDD pin {pin}',x-10.16,212.09,.95)
shunt(power,160.02,241.3,'+3V3_MCU','4.7u',fp='Capacitor_SMD:C_0805_2012Metric')
for net,x in [('+5V_CTRL',208.28),('+3V3_MCU',254),('GND',299.72)]: testpoint(power,x,240.03,net)
power.text('All five AVDD pins connect to the same 3.3 V rail. Continuous ground plane; no split return slit.\nEach 100 nF at its own AVDD/VSS pair. NC 5/29/60/72 remain unconnected.\nREF (74) and LDO12 (85) are multiplexed test outputs, not supply inputs.',20.32,262.89,1.05)

# MCU physical pin plan, three visible GPIO units. Reserved pins go to dedicated test pads.
mcu.section('EXACT PHYSICAL PIN ASSIGNMENT / THREE GPIO UNITS',20.32,17.78,370)
for unit,x,y in [(1,109.22,76.2),(2,302.26,76.2),(3,109.22,175.26)]:
    u=mcu.inst('MyParts:LKS32MC451VCT8','U1','LKS32MC451VCT8',x,y,unit=unit)
    for pin in u.pins: u.connect(pin,by_pin[pin]['Net'],5.08)
mcu.section('RESERVED DEBUG / ANALOG TEST OUTPUTS',223.52,132.08,165.1)
for i,net in enumerate(['DEBUG_nTRST_RESERVED','DEBUG_TDI_RESERVED','DEBUG_TDO_RESERVED','REF_TEST_RESERVED','LDO12_TEST_RESERVED']):
    testpoint(mcu,266.7,157.48+i*15.24,net)
mcu.text('Keep SWDMUX=0, RST_IO=0 and TRACEMUX=0 for this allocation.\nReserved test outputs are high-impedance pads only; no attached load or capacitor.\nADC pin mapping and selected AF remain in LKS32MC451VCT8_pin_plan.csv.\nNo board identification circuit consumes the reserved connector pins.',223.52,243.84,1.05)
mcu.section('EXTERNAL CRYSTAL',20.32,224.79,175.26)
y=mcu.inst('Device:Crystal_GND24','Y1','12MHz / CL TBD',99.06,248.92,fp='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',fields={'MPN':'TBD','Supplier':'LCSC','Design_Note':'12 MHz; internal oscillator capacitors; ESR/CL/startup pending'})
y.connect(1,'OSC_IN'); y.connect(3,'OSC_OUT'); y.connect(2,'GND'); y.connect(4,'GND')
mcu.text('DS v1.71 section 8: oscillator amplifier and load capacitors are internal.\nNo external load capacitors populated. Select crystal CL/ESR after vendor confirmation.\nKeep both crystal traces short, symmetric, and away from gate/PWM routing.',20.32,266.7,1.0)

def power_port(page,prefix,number):
    page.section(f'{prefix} / 24-PIN SIGNAL CONNECTOR',20.32,17.78,170)
    j=connector(page,81.28,71.12,24,f'{prefix}_24P / 0.5mm TBD')
    mapping={1:'PWM_UH',2:'PWM_UL',3:'GND',4:'PWM_VH',5:'PWM_VL',6:'GND',7:'PWM_WH',8:'PWM_WL',9:'GND',10:'ENABLE',11:'FAULT_N',12:None,13:'GND',14:'I_U',15:'I_V',16:'I_W',17:'GND',18:'V_DC',19:'V_U',20:'V_V',21:'GND',22:'V_W',23:'TEMP_NTC',24:None}
    if prefix=='PFC': mapping.update({1:'PWM_A1',2:'PWM_A2',4:'PWM_B1',5:'PWM_B2',7:'PWM_C1',8:'PWM_C2',12:'V_BUS_LOWER',14:'I_A',15:'I_B',16:'I_C',18:'V_BUS_UPPER',19:'V_A',20:'V_B',22:'V_C',24:'PRECHARGE'})
    outputs=[1,2,4,5,7,8,10]+([24] if prefix=='PFC' else [])
    analogs=[12,14,15,16,18,19,20,22,23] if prefix=='PFC' else [14,15,16,18,19,20,22,23]
    for pin,suffix in mapping.items():
        if suffix is None: j.nc(pin); continue
        net='GND' if suffix=='GND' else f'{prefix}_{suffix}'
        if pin in outputs+analogs+[11]: net+='_PORT'
        j.connect(pin,net,5.08)
    page.text('Contacts 3/6/9/13/17/21 -> controller GND. AGND is a return name, not isolation.\nNo auxiliary power on this connector. Footprint, latch and cable contact orientation TBD.\nUse same-reference laboratory boards only until the isolation architecture is reviewed.',20.32,116.84,1.05)
    page.section('DIGITAL COMMANDS / RESET DEFAULT LOW',203.2,17.78,185.42)
    for i,pin in enumerate(outputs):
        suffix=mapping[pin]; net=f'{prefix}_{suffix}'; y=43.18+i*20.32
        output_with_pull(page,259.08,y,net,net+'_PORT')
    fy=228.6
    page.section('FAULT INPUT / ACTIVE LOW OPEN-DRAIN',203.2,208.28,185.42)
    output_with_pull(page,259.08,fy,prefix+'_FAULT_N',prefix+'_FAULT_N_PORT','+3V3_MCU','100','4.7k')
    page.text('No RC delay in fast fault path. Local power board protection acts first.\nFAULT pull-up alone does not detect an unplugged cable.',203.2,251.46,1.05)
    page.section('ADC INPUTS / PROVISIONAL RC',20.32,142.24,170)
    for i,pin in enumerate(analogs):
        suffix=mapping[pin]; net=f'{prefix}_{suffix}'; y=162.56+i*12.7
        adc_filter(page,91.44,y,net+'_PORT',net)
    if prefix!='PFC':
        # Separate braking connector and control signal, independent of ENABLE.
        page.text('I: 1.65 V +/-50 mV/A; V: 50:1, NTC scale TBD.\nInputs must remain within 0..3.3 V while controller is powered.\n100R/1nF: tau=100 ns, fc=1.59 MHz; validate source + ADC settling.\nNo overvoltage / power-off backfeed protection claimed by this RC.',20.32,275.59,.86)
        page.section('SEPARATE BRAKE CONTROL',203.2,172.72,185.42)
        jb=connector(page,383.54,193.04,2,f'BRAKE_{number}')
        output_with_pull(page,259.08,193.04,f'BRAKE_{number}',f'BRAKE_{number}_PORT')
        jb.connect(1,f'BRAKE_{number}_PORT'); jb.connect(2,'GND')
    else:
        page.text('Boost uses A1; Vienna gate pairing / timing remains a validation task.\nPFC PRECHARGE remains reserved; inverter precharge was cancelled.\nADC 100R/1nF: tau=100 ns. PFC scaling / NTC / source impedance TBD.\nADC input clamps, unpowered pin injection and cross-domain isolation TBD.',20.32,278.13,.86)
    return j
power_port(inv1,'INV1',1)
power_port(inv2,'INV2',2)
power_port(pfc,'PFC',3)

# Sensor interfaces are a clearly bounded 3.3 V single-ended lab draft.
sensors.section('ABZ INCREMENTAL ENCODERS / 3.3 V SINGLE-ENDED DRAFT',20.32,17.78,370)
for k,x in [(1,25.4),(2,223.52)]:
    j=connector(sensors,x+50.8,55.88,5,f'ENC{k}: A B Z GND VOPT')
    for i,sig in enumerate('ABZ'):
        net=f'ENC{k}_{sig}'
        j.connect(i+1,net+'_PORT')
        series(sensors,x+53.34,88.9+i*17.78,net+'_PORT',net,'100')
        pull(sensors,x+142.24,90.17+i*17.78,net,'GND','100k')
    j.connect(4,'GND'); j.connect(5,f'ENC{k}_VOPT')
    series(sensors,x+58.42,147.32,'+3V3_MCU',f'ENC{k}_VOPT','0',True)
    shunt(sensors,x+142.24,147.32,f'ENC{k}_VOPT','100n',dnp=True)
    sensors.text('VOPT link + bypass DNP: no sensor power by default.\n3.3 V push-pull ABZ only; no differential receiver or 5 V conversion.\nExternal supply reference must be GND; do not backfeed this port.',x,165.1,.95)
spi.section('TWO INDEPENDENT SPI MASTERS / 3.3 V',20.32,17.78,370)
for k,x in [('A',25.4),('B',223.52)]:
    j=connector(spi,x+157.48,66.04,6,f'SPI_{k}: SCK MOSI MISO CS GND VOPT')
    for i,sig in enumerate(['SCK','MOSI','MISO','CS_N']):
        net=f'SPI_{k}_{sig}'
        j.connect(i+1,net+'_PORT')
        a,b=(net+'_PORT',net) if sig=='MISO' else (net,net+'_PORT')
        series(spi,x+48.26,101.6+i*20.32,a,b,'33')
    j.connect(5,'GND'); j.connect(6,f'SPI_{k}_VOPT')
    pull(spi,x+137.16,163.83,f'SPI_{k}_CS_N_PORT','+3V3_MCU','10k')
    series(spi,x+48.26,198.12,'+3V3_MCU',f'SPI_{k}_VOPT','0',True)
    shunt(spi,x+137.16,198.12,f'SPI_{k}_VOPT','100n',dnp=True)
spi.text('VOPT: optional 3.3 V power link and bypass are DNP. No sensor power is supplied by default.\nCS_N has 10k pull-up; both SPI peripherals remain unselected during MCU reset.\nPeripheral current budget, ESD, power sequencing, cable rate/termination and final pin order remain open.\nShort internal cables only; do not connect 5 V logic or drive unpowered controller pins.',20.32,236.22,1.15)
sensors.text('ENCODER INTERFACE REVIEW\nThe five-pin connector is a provisional schematic assignment, not a frozen production connector.\nActual encoder model / output stage / cable length / pulse rate must be selected before PCB.\nA 5 V TTL, open-collector, RS-422 or other differential encoder needs an appropriate input stage.\nThe eight reserved sensor-power parts on the ABZ/SPI sheets are not enabled by merely fitting connectors.',20.32,210.82,1.15)

# SWD + UART + CAN + five LEDs.
debug.section('SWD / RESET',20.32,17.78,165.1)
j=connector(debug,81.28,53.34,5,'SWD: VTREF IO CLK GND NRST')
for pin,net in [(1,'+3V3_MCU'),(2,'SWDIO_PORT'),(3,'SWCLK_PORT'),(4,'GND'),(5,'MCU_NRST')]: j.connect(pin,net)
series(debug,101.6,78.74,'SWDIO_PORT','SWDIO','33')
series(debug,101.6,96.52,'SWCLK_PORT','SWCLK','33')
pull(debug,165.1,78.74,'SWDIO','+3V3_MCU','10k')
pull(debug,165.1,96.52,'SWCLK','GND','10k')
debug.text('VTREF is target-voltage reference, not a power input.\nNo SWO; preserve reserved JTAG group pins.\nMCU_NRST open-drain pull-up is on power sheet.',20.32,111.76,1.05)
debug.section('3.3 V TTL UART / NO POWER PIN',223.52,17.78,165.1)
j=connector(debug,378.46,55.88,3,'UART: TX RX GND')
j.connect(1,'UART_TX_PORT'); j.connect(2,'UART_RX_PORT'); j.connect(3,'GND')
series(debug,287.02,50.8,'UART_TX','UART_TX_PORT','100')
series(debug,287.02,71.12,'UART_RX_PORT','UART_RX','100')
pull(debug,350.52,88.9,'UART_RX','+3V3_MCU','10k')
debug.text('TX/RX directions relative to controller. Cross TX to peer RX.\n3.3 V logic only; no RS-232 / RS-485 transceiver.',223.52,111.76,1.05)
debug.section('CLASSIC CAN / OPTIONAL ASSEMBLY BLOCK',20.32,139.7,370)
can=debug.inst('MyParts:SN65HVD232DR','U4','SN65HVD232DR',101.6,177.8,dnp=True)
can.connect(1,'CAN_TX_PHY'); can.connect(4,'CAN_RX_PHY'); can.connect(3,'+3V3_MCU'); can.connect(2,'GND'); can.nc(5); can.nc(8)
can.connect(6,'CAN_L'); can.connect(7,'CAN_H')
series(debug,38.1,167.64,'CAN_TX','CAN_TX_PHY','0',True)
series(debug,38.1,195.58,'CAN_RX_PHY','CAN_RX','0',True)
pull(debug,167.64,182.88,'CAN_TX_PHY','+3V3_MCU','10k',True)
shunt(debug,167.64,157.48,'+3V3_MCU','100n',dnp=True)
j=connector(debug,271.78,175.26,4,'CAN: H L GND NC',dnp=True)
j.connect(1,'CAN_H'); j.connect(2,'CAN_L'); j.connect(3,'GND'); j.nc(4)
rt=series(debug,238.76,203.2,'CAN_H','CAN_L','120',True)
rt.fields['Design_Note']='Fit only at a physical bus end; 0603 thermal review at bus fault required'
debug.text('DNP block: U4, two 0R links, TX pull-up, bypass, J and termination.\nPopulate the entire transceiver block together; 120R only at a bus end.\nSN65HVD232 pins 5/8 are NC; no standby GPIO.\nPin 4 at connector is NC; no supply output. ESD/protection TBD.',294.64,160.02,1.0)
debug.section('FIVE INDICATORS / LOW-ACTIVE GPIO LEDS',20.32,220.98,370)
for i,(name,color) in enumerate([('PWR','GREEN'),('LED_RUN1','GREEN'),('LED_RUN2','GREEN'),('LED_FAULT','RED'),('LED_COMM','BLUE')]):
    x=40.64+i*58.42
    rr=resistor(debug,x,241.3,'2.2k')
    rr.connect(1,'+3V3_MCU',2.54)
    led=debug.inst('Device:LED',ref('D'),f'{name} / {color}',x,261.62,angle=90,fp='LED_SMD:LED_0603_1608Metric',fields={'MPN':'TBD','Supplier':'LCSC','Design_Note':'Low-current visible LED; check Vf / brightness'})
    debug.wire(rr.pt(2),(x,251.46)); debug.wire((x,251.46),led.pt(2))
    debug.label(f'{name}_ANODE',(x,251.46),0)
    debug.expected.extend([(rr.ref,'2',f'{name}_ANODE'),(led.ref,'2',f'{name}_ANODE')])
    led.connect(1,'GND' if name=='PWR' else name,2.54)
debug.text('Indicative LED current <=(3.3-1.6)/2.2k=0.77 mA. LEDs do not grant hardware PWM permission.\nExact LEDs and switch are procurement TODOs.',20.32,279.4,.95)

for p in pages: p.write()
(BASE/'controller.kicad_pro').write_text('{}\n',encoding='utf-8')
(BASE/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "MyParts") (type "KiCad") (uri "${KIPRJMOD}/../../../kicad_library/symbols/MyParts.kicad_sym") (options "") (descr "Shared reviewed component library; read only")))\n',encoding='utf-8')
(BASE/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "MyFootprints") (type "KiCad") (uri "${KIPRJMOD}/../../../kicad_library/footprints/MyFootprints.pretty") (options "") (descr "Shared component footprints")))\n',encoding='utf-8')
out=BASE/'review'; out.mkdir(exist_ok=True)
with (out/'expected_pin_nets.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f); w.writerow(['Sheet','Reference','Pin','Expected_Net'])
    for p in pages:
        w.writerows((p.name,*v) for v in p.expected)
unique={}
for p in pages:
    for c in p.components:
        if c.ref.startswith('#'): continue
        if c.ref not in unique: unique[c.ref]=(p,c)
with (out/'bom.csv').open('w',encoding='utf-8-sig',newline='') as f:
    fields=['Reference','Value','Quantity','DNP','Sheet','Manufacturer','MPN','Supplier_PN','Purchase_URL','Footprint','Design_Note','Selection_Status']
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for p,c in unique.values():
        w.writerow(dict(Reference=c.ref,Value=c.value,Quantity=1,DNP='yes' if c.dnp else 'no',Sheet=p.name,**{k:c.fields.get(k,'') for k in fields[5:]}))
sources={}
for libid in cache:
    nick=libid.split(':')[0]; path=LIB/'symbols/MyParts.kicad_sym' if nick=='MyParts' else STD/f'{nick}.kicad_sym'
    sources[path.as_posix()]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(out/'library_sources.json').write_text(json.dumps(sources,indent=2)+'\n',encoding='utf-8')
print(f'Created {len(pages)} native KiCad sheets, {len(unique)} physical components; {sum(len(p.expected) for p in pages)} explicit pin-net assertions.')

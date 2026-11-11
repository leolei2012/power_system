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
PROJECT = 'inverter'
NS = uuid.UUID('63c306cd-ce7c-4d9a-b9d6-27cd5658a39a')
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
    p = LIB/'symbols/MyParts.kicad_sym' if nick == 'MyParts' else BASE/'InverterLocal.kicad_sym' if nick == 'InverterLocal' else STD/f'{nick}.kicad_sym'
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
            px, py = self.x, min((p[1] for p in self.pins.values()),default=self.y)-13.97
            passive = self.libid in ('Device:R','Device:C','MyParts:EKYB101ELL221MK25S','MyParts:CS1210KKX7R0BB225')
            if passive:
                px, py = (self.x, self.y-4.445) if self.angle == 90 else (self.x+3.81, self.y-1.27)
            elif self.libid.startswith('Connector_Generic:'):
                loc = child(next(s for s in children(self.lib,'symbol') if children(s,'pin')), 'pin')
                miny = min(p[1] for p in self.pins.values())
                px, py = self.x, miny-7.62
            elif self.libid == 'MyParts:LKS32MC451VCT8': px, py = self.x, self.y-27.94
            if key == 'Value': py += 2.54
            align = 'left' if visible and passive and self.angle == 0 else ''
            out.append(f'(property {q(key)} {q(value)} (at {n(px)} {n(py)} {self.angle%180}) {"" if visible else "(hide yes)"} {effects(1.0 if visible else 0.9,align)})')
        for pin in self.pins: out.append(f'(pin {q(pin)} (uuid {q(uid(self.uuid+"/pin/"+pin))}))')
        out.append(f'(instances (project {q(PROJECT)} (path {q(self.page.path)} (reference {q(self.ref)}) (unit {self.unit})))) )')
        return '\n'.join(out)

ROOT = uid('inverter-root')
class Page:
    def __init__(self, name, title, number):
        self.name, self.title, self.number = name, title, str(number)
        self.uuid = ROOT if name=='inverter' else uid('page/'+name)
        self.path = '/'+ROOT if name=='inverter' else '/'+ROOT+'/'+uid('sheet/'+name)
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
        content=[f'(kicad_sch (version 20250114) (generator "power_system_inverter") (generator_version "1.0") (uuid {q(self.uuid)}) (paper "A3")',
        f'(title_block (title {q(self.title)}) (date "2026-11-01") (rev "A-draft") (company "power_system") (comment 1 "HARDWARE REVIEW DRAFT - NOT RELEASED FOR PCB") (comment 2 "INVERTER | non-isolated laboratory draft | 12-60 V bus | separate 12-24 V auxiliary"))',
        '(lib_symbols '+'\n'.join(sx.dumps(v) for v in symbols.values())+')']
        content+=self.items+[c.render() for c in self.components]
        if self.name=='inverter': content+=['(sheet_instances (path "/" (page "1")))']
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


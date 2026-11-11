"""Graphical redraw helpers. Original electrical contract comes from a fixed snapshot.

Only native symbol placement and wiring are changed. Never recreate the BOM.
"""
from schematic_common import *
from zipfile import ZipFile
from collections import defaultdict
import xml.etree.ElementTree as ET

SNAPSHOT=BASE.parent/'history/rev_b_before_readability_2026-11-06.zip'
assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()=='4707965c1ec31571342266a5411a525cbb4ade161b6f2436d08c4f4103130e0e'
SNAP=ZipFile(SNAPSHOT)
def read_original(name):return sx.loads(SNAP.read('hardware/'+name+'.kicad_sch').decode('utf-8-sig'))
XML=ET.fromstring(SNAP.read('hardware/review/inverter.net.xml'))
PIN_NET={}
for net_ in XML.findall('./nets/net'):
    for node in net_.findall('node'):PIN_NET[node.attrib['ref'],node.attrib['pin']]=net_.attrib['name']
def properties(item):return {p[1]:p[2] for p in children(item,'property')}
def symbol_pins(lib,unit):
    result={}
    for sub in children(lib,'symbol'):
        if int(sub[1].rsplit('_',2)[1]) not in [0,unit]:continue
        for p in children(sub,'pin'):result[str(child(p,'number')[1])]=tuple(child(p,'at')[1:])
    return result

ORIGINALS={Path(n).stem:read_original(Path(n).stem) for n in SNAP.namelist() if n.endswith('.kicad_sch')}
NET_PAGES=defaultdict(set)
for page_,data_ in ORIGINALS.items():
    libs_={v[1]:v for v in children(child(data_,'lib_symbols'),'symbol')}
    for inst_ in children(data_,'symbol'):
        ref_=properties(inst_)['Reference'];unit_=int(child(inst_,'unit')[1])
        for pin_ in symbol_pins(libs_[child(inst_,'lib_id')[1]],unit_):
            net_=PIN_NET.get((ref_,pin_))
            if net_:NET_PAGES[net_].add(page_)

class Part:
    def __init__(self,sheet,item,x,y,angle,mirror=None):
        self.sheet=sheet;self.item=copy.deepcopy(item)
        self.ref=properties(item)['Reference'];self.unit=int(child(item,'unit')[1])
        self.libid=child(item,'lib_id')[1];self.x=x;self.y=y;self.angle=angle
        child(self.item,'at')[1:]=[x,y,angle]
        for m in children(self.item,'mirror'):self.item.remove(m)
        if mirror:self.item.append([sx.Symbol('mirror'),sx.Symbol(mirror)])
        self.pins={}
        for pin,(px,py,pa) in symbol_pins(sheet.libs[self.libid],self.unit).items():
            if mirror=='y':px=-px;pa=(180-pa)%360
            if mirror=='x':py=-py;pa=(-pa)%360
            a=math.radians(angle)
            self.pins[pin]=(round(x+px*math.cos(a)-py*math.sin(a),4),round(y-px*math.sin(a)-py*math.cos(a),4),(pa+angle)%360)
        miny=min(pt[1] for pt in self.pins.values())
        passive=self.libid in ['Device:R','Device:C'] or self.ref.startswith(('R','C','RS'))
        for pr in children(self.item,'property'):
            if pr[1] not in ['Reference','Value']:continue
            px,py=x,miny-7.62+(2.54 if pr[1]=='Value' else 0)
            if passive:
                px,py=(x,y-5.08+(2.54 if pr[1]=='Value' else 0)) if angle%180==90 else (x+3.81,y-1.27+(2.54 if pr[1]=='Value' else 0))
            child(pr,'at')[1:]=[round(px,4),round(py,4),angle%180]
            ef=child(pr,'effects')
            if ef:
                for j in children(ef,'justify'):ef.remove(j)
                if passive and angle%360==0:ef.append([sx.Symbol('justify'),sx.Symbol('left')])
    def pt(self,pin):return self.pins[str(pin)][:2]
    def field(self,key,x,y,angle=None):
        pr=next(p for p in children(self.item,'property') if p[1]==key)
        child(pr,'at')[1:]=[x,y,self.angle%180 if angle is None else angle]
    def stub(self,pin,length=5.08,net=None,side=None):
        pin=str(pin);x,y,pa=self.pins[pin]
        if side is None:side=(-math.cos(math.radians(pa)),math.sin(math.radians(pa)))
        end=(round(x+side[0]*length,4),round(y+side[1]*length,4))
        net=net or self.sheet.net(self.ref,pin)
        self.sheet.line(net,(x,y),end);self.sheet.label(net,end,180 if side[0]<0 else 0)
        return end

class Sheet:
    def __init__(self,name):
        self.name=name;self.original=copy.deepcopy(ORIGINALS[name])
        self.libs={v[1]:copy.deepcopy(v) for v in children(child(self.original,'lib_symbols'),'symbol')}
        self.instances={(properties(i)['Reference'],int(child(i,'unit')[1])):i for i in children(self.original,'symbol')}
        self.parts={};self.items=[];self.seq=0;self.points=defaultdict(list);self.marked=set();self.nc_done=set()
        self.power_index=list(ORIGINALS).index(name)*100+30000
    def uuid(self):
        self.seq+=1;return uid(f'readability/{self.name}/{self.seq}')
    def net(self,ref,pin):return PIN_NET.get((ref,str(pin)))
    def place(self,ref,x,y,angle=0,unit=1,mirror=None):
        key=(ref,int(unit));assert key not in self.parts,('duplicate placement',key)
        part=Part(self,self.instances[key],x,y,angle,mirror);self.parts[key]=part;return part
    def line(self,net,a,b):
        a=tuple(round(v,4) for v in a);b=tuple(round(v,4) for v in b)
        if a==b:return
        assert a[0]==b[0] or a[1]==b[1],('non-orthogonal',net,a,b)
        self.items.append(sx.loads(f'(wire (pts (xy {n(a[0])} {n(a[1])}) (xy {n(b[0])} {n(b[1])})) (stroke (width 0) (type default)) (uuid {q(self.uuid())}))'))
        self.points[net].extend([a,b])
    def path(self,net,points):
        for a,b in zip(points,points[1:]):self.line(net,a,b)
    def junction(self,pt):
        self.items.append(sx.loads(f'(junction (at {n(pt[0])} {n(pt[1])}) (diameter 0) (color 0 0 0 0) (uuid {q(self.uuid())}))'))
    def label(self,net,pt,angle=0,global_=None):
        assert net and not net.startswith('unconnected-'),net
        if global_ is None:global_=len(NET_PAGES[net])>1
        kind='global_label' if global_ else 'label'
        self.items.append(sx.loads(f'({kind} {q(net)} {"(shape passive)" if global_ else ""} (at {n(pt[0])} {n(pt[1])} {angle}) {effects(.9,"right" if angle==180 else "left")} (uuid {q(self.uuid())}))'))
        self.points[net].append(tuple(pt));self.marked.add(net)
    def mark(self,net,pt,angle=0):
        if net not in self.marked:self.label(net,pt,angle)
    def power(self,net,pt,angle=0):
        libid='power:GND' if net=='GND' else 'power:VCC'
        if libid not in self.libs:self.libs[libid]=copy.deepcopy(libsymbol(libid))
        self.power_index+=1
        symbol=copy.deepcopy(self.libs[libid]);reference=f'#PWR{self.power_index}'
        self.items.append(sx.loads(f'(symbol (lib_id {q(libid)}) (at {n(pt[0])} {n(pt[1])} {angle}) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {q(self.uuid())}) (property "Reference" {q(reference)} (at {n(pt[0])} {n(pt[1])} 0) (hide yes) {effects(.9)}) (property "Value" {q(net)} (at {n(pt[0])} {n(pt[1]+(3.81 if net=="GND" else -3.81))} 0) {"(hide yes)" if net=="GND" else ""} {effects(.9)}) (pin "1" (uuid {q(self.uuid())})) (instances (project "inverter" (path {q("/"+ROOT+"/"+uid("sheet/"+self.name))} (reference {q(reference)}) (unit 1)))))'))
        self.points[net].append(tuple(pt));self.marked.add(net)
    def gnd(self,pt):self.power('GND',pt)
    def flag(self,net,pt):
        libid='power:PWR_FLAG'
        if libid not in self.libs:self.libs[libid]=copy.deepcopy(libsymbol(libid))
        self.power_index+=1;reference=f'#FLG{self.power_index}'
        self.items.append(sx.loads(f'(symbol (lib_id {q(libid)}) (at {n(pt[0])} {n(pt[1])} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {q(self.uuid())}) (property "Reference" {q(reference)} (at {n(pt[0])} {n(pt[1])} 0) (hide yes) {effects(.9)}) (property "Value" "PWR_FLAG" (at {n(pt[0])} {n(pt[1]-5.08)} 0) (hide yes) {effects(.9)}) (pin "1" (uuid {q(self.uuid())})) (instances (project "inverter" (path {q("/"+ROOT+"/"+uid("sheet/"+self.name))} (reference {q(reference)}) (unit 1)))))'))
        self.points[net].append(tuple(pt))
    def nc(self,ref,pin,unit=None):
        if unit is None:
            matches=[p for (r,u),p in self.parts.items() if r==ref and str(pin) in p.pins]
            assert len(matches)==1,(ref,pin);part=matches[0]
        else:part=self.parts[ref,unit]
        pt=part.pt(pin)
        if (ref,str(pin)) in self.nc_done:return
        self.items.append(sx.loads(f'(no_connect (at {n(pt[0])} {n(pt[1])}) (uuid {q(self.uuid())}))'))
        self.nc_done.add((ref,str(pin)))
    def text(self,text,x,y,size=1.1,bold=False):
        self.items.append(sx.loads(f'(text {q(text)} (at {n(x)} {n(y)} 0) {effects(size,"left top",bold)} (uuid {q(self.uuid())}))'))
    def section(self,text,x,y,w=370):
        self.text(text,x,y,1.6,True)
        self.items.append(sx.loads(f'(polyline (pts (xy {n(x)} {n(y+5.08)}) (xy {n(x+w)} {n(y+5.08)})) (stroke (width .254) (type default)) (fill (type none)) (uuid {q(self.uuid())}))'))
    def save(self):
        # Retain original ERC power flags, attached to the same named net.
        for key,inst in self.instances.items():
            if key in self.parts:continue
            assert key[0].startswith('#'),('Unplaced physical symbol',self.name,key)
            pin='1';net=self.net(key[0],pin)
            # Power flags are omitted by XML nodes; use the original stub label.
            if not net:
                x,y,_=child(inst,'at')[1:]
                for lab in children(self.original,'global_label'):
                    lx,ly=child(lab,'at')[1:3]
                    if abs(lx-x)<.01 and abs(abs(ly-y)-2.54)<.01:net=lab[1];break
            assert net in self.points,('Missing power-flag net',key,net)
            x,y=self.points[net][0];part=self.place(key[0],x,y,unit=key[1])
            for prop in children(part.item,'property'):
                if prop[1] in ['Reference','Value'] and not child(prop,'hide'):prop.append([sx.Symbol('hide'),sx.Symbol('yes')])
        for key,part in self.parts.items():
            for pin in part.pins:
                net=self.net(part.ref,pin)
                if net and net.startswith('unconnected-'):self.nc(part.ref,pin,part.unit)
        # One retained name per connected internal network; explicit mark() is preferred.
        for net,points in self.points.items():
            if net not in self.marked:self.label(net,points[0],0)
        ignored={'symbol','wire','label','global_label','junction','no_connect','text','polyline','lib_symbols'}
        data=[v for v in self.original if not isinstance(v,list) or str(v[0]) not in ignored]
        title=child(data,'title_block');child(title,'rev')[1]='B-readable-draft'
        data.append([sx.Symbol('lib_symbols')]+list(self.libs.values()))
        data.extend(self.items);data.extend(p.item for p in self.parts.values())
        path=BASE/(self.name+'.kicad_sch')
        path.write_text('('+str(data[0])+'\n'+'\n'.join(sx.dumps(v) if isinstance(v,list) else str(v) for v in data[1:])+')\n',encoding='utf-8')
        print(self.name,len(self.parts),'original symbol units;',len(children(data,'wire')),'wires;',len(children(data,'global_label')),'global labels')

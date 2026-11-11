"""Rev D power-base split, authored from the immutable integrated Rev C archive.
Preserves all retained component fields/pins; moves three spare gate units only.
Does not edit a PCB, project rules, shared libraries or the source archive.
"""
from pathlib import Path
from zipfile import ZipFile
import copy,hashlib,json,math,sys,uuid
import sexpdata as sx
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'tools'))
from schematic_common import tag,child,children,uid,q,n,effects,ROOT
ARCHIVE=BASE.parent/'history/integrated_60x60_rev_c_before_mcu_split_2026-11-06.zip'
Z=ZipFile(ARCHIVE)
def original(name):return sx.loads(Z.read('inverter/hardware/'+name+'.kicad_sch').decode('utf-8-sig'))
def props(i):return {v[1]:v[2] for v in children(i,'property')}
def write(name,d):
 title=child(d,'title_block');child(title,'date')[1]='2026-11-06';child(title,'rev')[1]='D-split-draft'
 (BASE/(name+'.kicad_sch')).write_text('('+str(d[0])+'\n'+'\n'.join(sx.dumps(v) if isinstance(v,list) else str(v) for v in d[1:])+')\n',encoding='utf-8')
def rename(d,old,new):
 for kind in ['label','global_label']:
  for v in children(d,kind):
   if v[1]==old:v[1]=new
 for v in children(d,'text'):v[1]=v[1].replace(old,new)
def getinst(d,ref,unit=1):return next(x for x in children(d,'symbol') if props(x).get('Reference')==ref and child(x,'unit')[1]==unit)
def pinpts(d,inst):
 lib=next(l for l in children(child(d,'lib_symbols'),'symbol') if l[1]==child(inst,'lib_id')[1]);unit=int(child(inst,'unit')[1]);x,y,a=child(inst,'at')[1:];ang=math.radians(a);out={}
 for sub in children(lib,'symbol'):
  if int(sub[1].rsplit('_',2)[1]) not in [0,unit]:continue
  for pin in children(sub,'pin'):
   px,py,pa=child(pin,'at')[1:];out[str(child(pin,'number')[1])]=(round(x+px*math.cos(ang)-py*math.sin(ang),4),round(y-px*math.sin(ang)-py*math.cos(ang),4))
 return out
class NewPage:
 def __init__(self,name,title,paper='A3'):
  self.name=name;self.seq=0;self.libs={};self.path='/'+ROOT+'/'+uid('sheet/'+name)
  self.data=sx.loads(f'(kicad_sch (version 20250114) (generator "power_system_inverter") (generator_version "1.0") (uuid {q(uid("page/"+name))}) (paper {q(paper)}) (title_block (title {q(title)}) (date "2026-11-06") (rev "D-split-draft") (company "power_system") (comment 1 "POWER BASE | COMMON GND | SCHEMATIC REVIEW DRAFT") (comment 2 "Existing Rev C PCB is historical and does not match Rev D")) (lib_symbols) (embedded_fonts no))')
 def id(self):self.seq+=1;return uid(f'revd/{self.name}/{self.seq}')
 def add(self,text):self.data.append(sx.loads(text))
 def line(self,a,b):
  if a==b:return
  assert a[0]==b[0] or a[1]==b[1],(a,b)
  self.add(f'(wire (pts (xy {n(a[0])} {n(a[1])}) (xy {n(b[0])} {n(b[1])})) (stroke (width 0) (type default)) (uuid {q(self.id())}))')
 def path_(self,*points):
  for a,b in zip(points,points[1:]):self.line(a,b)
 def label(self,net,pt,angle=0,global_=True):
  kind='global_label' if global_ else 'label';self.add(f'({kind} {q(net)} {"(shape passive)" if global_ else ""} (at {n(pt[0])} {n(pt[1])} {angle}) {effects(1.0,"right" if angle==180 else "left")} (uuid {q(self.id())}))')
 def text(self,text,x,y,size=1.1,bold=False):self.add(f'(text {q(text)} (at {n(x)} {n(y)} 0) {effects(size,"left top",bold)} (uuid {q(self.id())}))')
 def section(self,text,x,y,w=250):
  self.text(text,x,y,1.6,True);self.add(f'(polyline (pts (xy {x} {y+5.08}) (xy {x+w} {y+5.08})) (stroke (width .254) (type default)) (fill (type none)) (uuid {q(self.id())}))')
 def junction(self,pt):self.add(f'(junction (at {n(pt[0])} {n(pt[1])}) (diameter 0) (color 0 0 0 0) (uuid {q(self.id())}))')
 def move(self,source,ref,x,y,unit=1,newref=None):
  orig=getinst(source,ref,unit);i=copy.deepcopy(orig);ox,oy,a=child(i,'at')[1:];child(i,'at')[1:]=[x,y,a]
  for pr in children(i,'property'):
   at=child(pr,'at');at[1]+=x-ox;at[2]+=y-oy
  libid=child(i,'lib_id')[1];self.libs[libid]=copy.deepcopy(next(z for z in children(child(source,'lib_symbols'),'symbol') if z[1]==libid))
  for project in children(child(i,'instances'),'project'):
   for path in children(project,'path'):
    path[1]=self.path
    if newref:child(path,'reference')[1]=newref
  if newref:
   next(z for z in children(i,'property') if z[1]=='Reference')[2]=newref;child(i,'uuid')[1]=uid(f'revd/{self.name}/{newref}/{unit}')
   for pin in children(i,'pin'):child(pin,'uuid')[1]=uid(f'revd/{self.name}/{newref}/pin/'+str(pin[1]))
  self.data.append(i);return pinpts(source if not newref else source,i)
 def power(self,source,net,pt,ref):
  libid='power:GND' if net=='GND' else 'power:VCC';orig=next(i for i in children(source,'symbol') if child(i,'lib_id')[1]==libid);r=props(orig)['Reference'];pins=self.move(source,r,*pt,newref=ref)
  i=self.data[-1];next(z for z in children(i,'property') if z[1]=='Value')[2]=net
 def save(self):child(self.data,'lib_symbols')[1:]=list(self.libs.values());write(self.name,self.data)

kept=['aux_input','supply_12v','supply_logic','bus_brake','bridge_u','bridge_v','bridge_w','current_sense','voltage_sense','comparators','fault_logic','control_interface']
# The retained power pages start as exact Rev C native data.  Only safety nets,
# titles/notes, and the formerly spare units are changed below.
for name in kept:
 d=original(name);rename(d,'LOGIC_POWER_OK','BASE_LOGIC_OK')
 if name=='fault_logic':
  rename(d,'ENABLE_IN','ENABLE_QUALIFIED')
  for v in children(d,'text'):
   if 'FAULT_N is open collector' in v[1]:v[1]=v[1].replace('a fully unpowered inverter cannot assert LOW.','core-domain pull-up is on the MCU sub-board.\nBASE_READY must be checked separately; an unpowered base cannot assert FAULT_N LOW.')
 if name=='supply_logic':
  for v in children(d,'text'):
   v[1]=v[1].replace('3.3 V MCU / ANALOG SUPPLY','3.3 V BASE LOGIC / ANALOG SUPPLY')
   v[1]=v[1].replace('3.3 V SUPERVISOR / LOCAL MCU RESET','3.3 V SUPERVISOR / LOCAL BASE PERMISSION')
   v[1]=v[1].replace('The 3.3 V LDO is shared by MCU, analog, logic and optional CAN; budget and temperature still require verification.','U4 supplies only base analog and safety logic. BASE_LOGIC_OK never connects to controller NRST.\nThe removable MCU board regulates its own 3.3 V; local current budget and temperature require verification.')
 if name=='bus_brake':
  for v in children(d,'text'):
   v[1]=v[1].replace('LOCAL MCU COMMAND','CONTROLLER HEADER COMMAND')
   v[1]=v[1].replace('MCU reset defaults the command low.','The base-side input pull-down defaults a missing controller command LOW.')
 if name=='control_interface':
  # Clear only the known spare-unit block; all six PWM gates, pulls and power
  # units retain exact geometry, fields, nets and UUIDs.
  spare={('U26',4),('U27',3),('U27',4)}
  new=[]
  for v in d:
   if tag(v,'symbol') and (props(v).get('Reference'),int(child(v,'unit')[1])) in spare:continue
   if isinstance(v,list) and str(v[0]) in ['wire','junction','no_connect','text','polyline']:
    if tag(v,'wire'):ys=[xy[2] for xy in children(child(v,'pts'),'xy')];xs=[xy[1] for xy in children(child(v,'pts'),'xy')]
    elif tag(v,'polyline'):ys=[xy[2] for xy in children(child(v,'pts'),'xy')];xs=[xy[1] for xy in children(child(v,'pts'),'xy')]
    else:at=child(v,'at');xs=[at[1]] if at else [];ys=[at[2]] if at else []
    if xs and min(xs)>220 and min(ys)>210:continue
   if tag(v,'symbol') and props(v).get('Reference','').startswith('#') and child(v,'at')[1]>220 and child(v,'at')[2]>210:continue
   new.append(v)
  d=new
  t=sx.loads(f'(text "U26D / U27C / U27D are used on the Base interlock page.\nR76-R81 default PWM LOW; R82 raw ENABLE default LOW.\nNo MCU on this board; CTRL_READY must qualify ENABLE before any latch reset or DRIVE_PERMIT." (at 223.52 223.52 0) {effects(1.05,"left top")} (uuid {q(uid("revd/control/spares-note"))}))');d.append(t)
  for v in children(d,'text'):v[1]=v[1].replace('while MCU outputs are Hi-Z','while the controller is disconnected or Hi-Z')
 write(name,d)

src=original('control_interface')
p=NewPage('base_interlock','Power base - controller readiness and local supply interlock')
p.section('REMOVABLE CONTROLLER / DEFAULT DISABLE',20.32,17.78,370)
p.text('Common GND, 3.3 V logic. CTRL_READY comes from the controller reset-health buffer.\nThe power base owns all PWM pull-downs and hardware permission; no MCU firmware is required to block a missing controller.',20.32,27.94,1.15)
u=p.move(src,'U26',121.92,68.58,unit=4)
r=p.move(src,'R82',76.2,93.98,newref='R160')
p.path_((35.56,u['12'][1]),u['12']);p.label('ENABLE_IN',(35.56,u['12'][1]),180)
p.path_((35.56,u['13'][1]),u['13']);p.label('CTRL_READY',(35.56,u['13'][1]),180)
p.line((76.2,u['13'][1]),r['1']);p.junction((76.2,u['13'][1]));p.path_(r['2'],(76.2,104.14));p.power(src,'GND',(76.2,104.14),'#PWR90160')
p.path_(u['11'],(160.02,u['11'][1]));p.label('ENABLE_QUALIFIED',(160.02,u['11'][1]))
p.text('R160 = 10k. Unplugged, controller reset or lost controller power => ENABLE_QUALIFIED LOW.\nOnly ENABLE_QUALIFIED enters the latch reset and DRIVE_PERMIT logic. Raw ENABLE_IN keeps its original local R82 pull-down.',20.32,114.3,1.15)
p.section('BASE SUPPLY PRESENCE / INDEPENDENT OF OPEN-COLLECTOR FAULT',20.32,142.24,370)
a=p.move(src,'U27',121.92,185.42,unit=3);b=p.move(src,'U27',228.6,185.42,unit=4)
p.path_((35.56,a['9'][1]),a['9']);p.label('BASE_LOGIC_OK',(35.56,a['9'][1]),180)
p.path_((35.56,a['10'][1]),a['10']);p.label('DRV_PG_LOGIC',(35.56,a['10'][1]),180)
p.path_(a['8'],(198.12,185.42),(198.12,b['12'][1]),b['12'])
p.path_((198.12,185.42),(198.12,b['13'][1]),b['13']);p.junction((198.12,185.42));p.label('BASE_NOT_READY',(160.02,185.42),global_=False)
p.path_(b['11'],(281.94,b['11'][1]));p.label('BASE_READY',(281.94,b['11'][1]))
p.text('BASE_READY = BASE_LOGIC_OK AND DRV_PG_LOGIC. The MCU sub-board provides its receiver pull-down.\nFAULT_N remains Q8 open collector with a pull-up only in the MCU 3.3 V domain. A high FAULT_N alone does not prove base power.\nU26/U27 package power and 100 nF bypass stay on Hardware PWM gates. No added logic package.',20.32,223.52,1.15)
p.save()

# Only D3/R130 remain on the power base; D4..D7 migrate unchanged to core.
dbg=original('debug_comms');led=NewPage('base_leds','Power base - local power indication',paper='A4')
led.section('LOCAL POWER INDICATOR / NO MCU LED SIGNALS ACROSS HEADER',20.32,17.78,250)
r=led.move(dbg,'R130',76.2,60.96);d=led.move(dbg,'D3',76.2,81.28)
led.path_((76.2,48.26),r['1']);led.power(src,'+3V3_INV',(76.2,48.26),'#PWR90161')
led.path_(r['2'],d['2']);led.label('LED_PWR_AN',(76.2,71.12),global_=False)
led.path_(d['1'],(76.2,93.98));led.power(src,'GND',(76.2,93.98),'#PWR90162')
led.text('D3: base 3.3 V present. This lamp alone does not indicate driver power or protection permission.\nD4..D7 and R131..R134 belong to the removable MCU sub-board: RUN / FAULT / COMM / AUX.\nThe power base has no MCU-run or communication LED nets on its board-to-board header.',20.32,116.84,1.15)
led.save()

# Top-level manifest: retained pages keep their sheet UUID/path.  Header page is
# added by the root agent after its 40-pin native page is ready.
top=original('inverter');entries=[]
for s in children(top,'sheet'):
 pp=props(s)
 if Path(pp.get('Sheetfile','')).stem in kept:entries.append(s)
top=[v for v in top if not isinstance(v,list) or str(v[0]) not in ['sheet','text','polyline']]
child(child(top,'title_block'),'title')[1]='Inverter power base - removable STM32G431 controller'
def addtop(text,x,y,size=1.1,bold=False):top.append(sx.loads(f'(text {q(text)} (at {x} {y} 0) {effects(size,"left top",bold)} (uuid {q(uid("revd/top/"+str(x)+"/"+str(y)))}))'))
addtop('POWER BASE / REMOVABLE MCU SUB-BOARD / REV D REVIEW',20.32,17.78,1.6,True)
addtop('Common-ground plug-in controller. Power base retains one three-phase bridge, brake, analogue sensing and all hardware protection.\n12-60 V bus / DC input <=10 A / phase 10 Arms design target / separate 12-24 V auxiliary.',20.32,27.94,1.15)
for i,s in enumerate(entries):
 x=20.32+(i%4)*96.52;y=55.88+(i//4)*43.18;oldat=child(s,'at');ox,oy=oldat[1:];oldat[1:]=[x,y]
 for pr in children(s,'property'):
  at=child(pr,'at');at[1]+=x-ox;at[2]+=y-oy
 for project in children(child(s,'instances'),'project'):
  for path in children(project,'path'):child(path,'page')[1]=str(i+2)
 top.append(s)
 desc={
  'aux_input':'eFuse / separate 12-24 V auxiliary',
  'supply_12v':'12 V buck-boost / driver power good',
  'supply_logic':'5 V / local 3.3 V / base supervisor',
  'bus_brake':'12-60 V bus / one external-resistor brake',
  'bridge_u':'U driver / TDSON8 half bridge / shunt',
  'bridge_v':'V driver / TDSON8 half bridge / shunt',
  'bridge_w':'W driver / TDSON8 half bridge / shunt',
  'current_sense':'3 x INA241 / 1.65 V reference',
  'voltage_sense':'DC bus / three phases / NTC',
  'comparators':'Current windows / bus OV / driver UV',
  'fault_logic':'Health chain / latch / reset / FAULT_N',
  'control_interface':'Six PWM AND gates / local pull-downs',
 }[Path(props(s)['Sheetfile']).stem]
 addtop(desc,x+2.54,y+6.35,.85)
extra_pages=[('base_interlock','Base interlock','CTRL_READY / ENABLE_QUALIFIED / BASE_READY'),('base_leds','Base LEDs','D3 power lamp only')]
if (BASE/'power_interface.kicad_sch').exists():
 extra_pages.append(('power_interface','POWER-CORE HEADERS','2 x 20 pins / 5 V / common GND / 3.3 V signals'))
for i,(name,title,desc) in enumerate(extra_pages,len(entries)):
 x=20.32+(i%4)*96.52;y=55.88+(i//4)*43.18;path='/'+ROOT
 s=sx.loads(f'(sheet (at {x} {y}) (size 86.36 20.32) (stroke (width .254) (type default)) (fill (color 0 0 0 0)) (uuid {q(uid("sheet/"+name))}) (property "Sheetname" {q(title)} (at {x} {y-2.54} 0) {effects(.95,"left")}) (property "Sheetfile" {q(name+".kicad_sch")} (at {x} {y+22.86} 0) {effects(.85,"left")}) (instances (project "inverter" (path {q(path)} (page {q(str(i+2))})))))');top.append(s);addtop(desc,x+2.54,y+6.35,.85)
addtop('MCU / SWD / TTL / CAN / encoder / SPI live on the removable controller board. No shared NRST net.\nBASE_LOGIC_OK is local base-supply reset permission, not the controller NRST.\nCTRL_READY LOW or missing controller blocks ENABLE; BASE_READY separately reports local logic plus driver supply.\nThis schematic supersedes the archived integrated Rev C design; the old PCB is not valid for Rev D.',20.32,250.19,1.05)
write('inverter',top)
print('Archive kept:',ARCHIVE,'sha256',hashlib.sha256(ARCHIVE.read_bytes()).hexdigest())
print('Power top pages:',len(children(top,'sheet')))

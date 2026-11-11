import pcbnew as p, json, math, itertools, hashlib
from pathlib import Path
B=Path(__file__).resolve().parents[1]
OUT=B/'tools/compact_control_placement.json'
data=json.loads(OUT.read_text(encoding="utf-8"))
board=p.LoadBoard(str(B/'review/compact_work/inverter.kicad_pcb'))
fps={f.GetReference():f for f in board.GetFootprints()}
owned=set(data['owned_refs']); groups={r:g for g,rs in data['group_refs'].items() for r in rs}
V=lambda x,y:p.VECTOR2I(round(x*1e6),round(y*1e6))
xy=lambda x:(p.ToMM(x.x),p.ToMM(x.y))
def oriented(ref,side,angle):
 f=p.Cast_to_FOOTPRINT(fps[ref].Duplicate(False))
 if f.IsFlipped()!=(side=='B'):f.Flip(f.GetPosition(),False)
 f.SetOrientationDegrees(angle);f.SetPosition(V(0,0));f.BuildCourtyardCaches()
 q=f.GetCourtyard(p.B_CrtYd if side=='B' else p.F_CrtYd).BBox()
 bb=tuple(p.ToMM(v) for v in (q.GetX(),q.GetY(),q.GetRight(),q.GetBottom()))
 pads=[]
 for a in f.Pads():
  if a.GetAttribute() in (p.PAD_ATTRIB_PTH,p.PAD_ATTRIB_NPTH):
   x,y=xy(a.GetPosition());sx,sy=xy(a.GetSize());pads.append((x,y,max(sx,sy)/2+.25))
 return bb,pads
cache={}
def geom(ref,side,angle):
 key=(ref,side,angle)
 if key not in cache:cache[key]=oriented(*key)
 return cache[key]
def box(ref,x,y,side,angle):
 q,_=geom(ref,side,angle);return [q[0]+x,q[1]+y,q[2]+x,q[3]+y]
def intersects(a,b,g=.06):return a[0]<b[2]+g and a[2]>b[0]-g and a[1]<b[3]+g and a[3]>b[1]-g
def circlehit(bb,x,y,r,g=.06):
 return math.hypot(max(bb[0]-x,0,x-bb[2]),max(bb[1]-y,0,y-bb[3]))<r+g
obs={'F':[],'B':[]};circles={'F':[],'B':[]};placed={};logs=[]
# Actual immutable power courtyards, plus opposite-side plated-pad reserves.
power=json.loads((B/'tools/compact_power_placement.json').read_text())
for ref,w in power['placements'].items():
 for side,bb in w.get('courtyard_bbox_mm',{}).items():obs[side].append((ref,bb))
 if ref in fps:
  _,pads=geom(ref,w['side'],w['rotation_deg'])
  for px,py,r in pads:
   for side in ('F','B'):circles[side].append((ref,w['x']+px,w['y']+py,max(r,1.5) if ref in ('C19','C20') else r))
for x,y in [(3,3),(57,3),(57,57),(3,57)]:
 for s in ('F','B'):circles[s].append(('M2',x,y,2.25))
obs['B'] += [('aux-reservation',[3,37,31,56]),('ldo-reservation',[20,35,30,40])]
obs['F'] += [('efuse-reservation',[3.8,43,31,55.5])]
# Locations always denote native footprint origin. Flip first, then rotate.
def bounds_for(ref,side):
 if ref.startswith('J'):return [[.3,.3,59.7,59.7]]
 if groups[ref]=='status_leds' and ref.startswith('D'):return [[3,15,32,20],[24,57,34,59.7]]
 if ref=='SW2':return [[3,15,25,19]]
 return [[3.8,.5,33.85,36]] if side=='B' else [[3.8,15,32,41]]
def valid(ref,x,y,side,angle):
 bb=box(ref,x,y,side,angle)
 if not any(bb[0]>=a and bb[1]>=b and bb[2]<=c and bb[3]<=d for a,b,c,d in bounds_for(ref,side)):return False,'bounds'
 for name,ob in obs[side]:
  if intersects(bb,ob):return False,name
 for name,cx,cy,r in circles[side]:
  if circlehit(bb,cx,cy,r):return False,name+'-hole'
 # Our through hole pads also reserve space against already-placed back parts.
 _,pads=geom(ref,side,angle)
 for px,py,r in pads:
  other='B' if side=='F' else 'F'
  for name,ob in obs[other]:
   if circlehit(ob,x+px,y+py,r):return False,name+'-backpad'
 return True,''
def put(ref,x,y,side='B',angle=0,strict=True):
 good,why=valid(ref,x,y,side,angle)
 if not good:
  if strict:raise RuntimeError((ref,x,y,side,angle,why))
  return False
 bb=box(ref,x,y,side,angle);_,pads=geom(ref,side,angle)
 placed[ref]={'side':side,'x':round(x,3),'y':round(y,3),'rotation_deg':angle,'group':groups[ref],'courtyard_bbox_mm':bb,'footprint':fps[ref].GetFPIDAsString()}
 obs[side].append((ref,bb))
 other='B' if side=='F' else 'F'
 for px,py,r in pads:circles[other].append((ref,x+px,y+py,r))
 return True
def near(ref,target,sides=('B',),angles=(0,90),step=.25,maxdist=100):
 tx,ty=target; candidates=[]
 for side in sides:
  for a in angles:
   for bounds in bounds_for(ref,side):
    x0,y0,x1,y1=bounds
    for xi in range(math.ceil(x0/step),math.floor(x1/step)+1):
     x=xi*step
     for yi in range(math.ceil(y0/step),math.floor(y1/step)+1):
      y=yi*step;score=(x-tx)**2+(y-ty)**2
      if score<=maxdist**2:candidates.append((score,0 if side==sides[0] else 100,0 if a==angles[0] else .01,side,a,x,y))
 candidates.sort(key=lambda z:z[:3])
 for _,_,_,s,a,x,y in candidates:
  if put(ref,x,y,s,a,False):return
 raise RuntimeError(('NO ROOM',ref,target,sides))
# Connectors: left starts below bus solder terminal/fuse; CAN occupies clear top-right edge.
for r,x,y,a in [('J9',2,22.7,0),('J10',2,30.25,0),('J11',2,37.8,0),('J12',2,46.62,0),('J13',7,58,90),('J14',15.3,58,90),('J8',21,58,90),('J15',46,2,90)]:put(r,x,y,'F',a)
# Principal ICs. Dense fault logic stays independent on front.
put('U30',16.5,23.5,'B',180)
for r,x,y in [('U22',8.35,24.3),('U23',16.45,24.3),('U24',24.55,24.3),('U25',8.35,30.4),('U26',16.45,30.4),('U27',24.55,30.4)]:put(r,x,y,'F',0)
put('U28',16.5,37.1,'F',90)
near('SW2',(13.5,17.0),('F',),(0,),.1)
near('U31',(12.1,3.2),('B',),(0,),.1)
near('U6',(6.2,17),('B',),(0,),.1)
# Four voltage followers face the quiet right-hand strip on front, comparator below.
for r,t in [('U14',(30.4,17.1)),('U15',(30.4,22)),('U16',(30.4,27)),('U17',(25.4,37.2))]:near(r,t,('F',),(90,),.1)
near('U21',(30.1,37.2),('F',),(90,),.1)
near('U13',(22.5,17.4),('F',),(0,),.1)
near('Q8',(24.5,38.7),('F',),(0,),.1)
for r,t,side in [('TP14',(6.3,35.1),'F'),('TP15',(6,25.5),'B'),('TP16',(6,29),'B'),('TP17',(6,32.5),'B')]:near(r,t,(side,),(0,),.1)
# DNP crystal remains close to MCU OSC pins; critical ADC and supply capacitors placed before generic RC.
near('Y1',(26.1,17.9),('B',),(0,90),.1)
critical=[('C69',(25.5,22)),('C70',(25.5,23.4)),('C71',(25.5,24.8)),('C72',(25.5,26.2)),('R84',(28,22)),('R85',(28,23.4)),('R86',(28,24.8)),('R87',(28,26.2)),('C63',(24.5,28)),('C64',(11.3,30.9)),('C65',(8.5,19.8)),('C66',(20.5,15)),('C67',(24.5,19.5)),('C77',(13.4,30.9)),('C79',(15.8,30.9)),('C73',(19.5,32.0)),('C74',(17.1,32.0)),('C75',(14.7,32.0)),('C76',(12.3,32.0)),('R88',(19.5,34)),('R89',(17.1,34)),('R90',(14.7,34)),('R91',(12.3,34)),('C78',(13.5,35.1)),('C80',(17.2,35.1)),('C68',(27.5,29)),('C17',(6,13)),('C81',(6,21.5))]
for r,t in critical:near(r,t,('B',),(180,0,90) if r=='C64' else (0,90),.1)
put('C59',8.5,28.5,'B',180)
put('C60',21.5,31,'B',0)
# Retained0805/0603 high voltage divider ladders; near associated follower, not MCU crystal.
for idx,rs in enumerate([['R48','R49','R50','R51'],['R53','R54','R55','R56'],['R58','R59','R60','R61'],['R63','R64','R65','R66']]):
 tx,ty=[(29.8,11.8),(30.2,20.8),(30.2,28.4),(29.7,33.0)][idx]
 for i,r in enumerate(rs):near(r,(tx-(i%2)*3.6,ty+(i//2)*3),('B','F'),(90,0),.2)
# Front local protection decouplers target each package VCC end; no deletion or optionalization.
for r,t in [('C56',(11.5,20.1)),('C57',(19.6,20.1)),('C58',(27.7,20.1)),('C59',(11.5,27)),('C60',(19.6,27)),('C61',(27.7,27)),('C62',(10.5,34.5)),('C55',(9.5,38.6))]:
 if r not in placed:near(r,t,('F',),(0,90),.1)
# LEDs fitted on visible front perimeter; keep Q7 and auxiliary body clear.
for r,t in [('D3',(18.3,16.1)),('D4',(18.3,18.1)),('D5',(25.6,58.1)),('D6',(29,58.1)),('D7',(32.3,58.1))]:near(r,t,('F',),(0,),.1)
# Remaining passives, prioritized analog local networks before digital pullups.
targets={
 'current_bias':('F',(23,18.8)), 'current_thresholds':('F',(30,30)),
 'voltage_DC':('F',(30,18)), 'voltage_U':('F',(30,22)), 'voltage_V':('F',(30,27)), 'voltage_W':('F',(25.5,36)),
 'bus_ov_driver_uv':('F',(29,36)), 'hardware_fault_logic':('F',(8,36)),
 'reset_boot':('B',(6,19)), 'mcu_core':('B',(23,16)), 'mcu_analog_reference':('B',(11,33)),
 'hse_dnp_reserve':('B',(26,18)), 'can_dnp':('B',(14,9.8)),
 'encoder_a':('B',(6,23)), 'encoder_b':('B',(6,29)),
 'spi_a':('B',(7,33)), 'spi_b':('B',(10,34)), 'swd':('B',(9,35)), 'ttl_uart':('B',(17,35)),
 'mcu_pwm_fault':('B',(25,32)), 'status_leds':('B',(25,33)), 'ntc_connector':('B',(20,34))}
order=['current_bias','current_thresholds','voltage_DC','voltage_U','voltage_V','voltage_W','bus_ov_driver_uv','hardware_fault_logic','hse_dnp_reserve','reset_boot','mcu_analog_reference','can_dnp','status_leds','encoder_a','encoder_b','spi_a','spi_b','swd','ttl_uart','mcu_pwm_fault','ntc_connector']
for g in order:
 print('PACK',g,len(placed),flush=True)
 refs=[r for r in data['group_refs'][g] if r in owned and r not in placed]
 for r in refs:
  side,t=targets[g]
  sides=(side,) if g in ['status_leds','hardware_fault_logic'] else (side,'F' if side=='B' else 'B')
  near(r,t,sides,(0,90),.25)
assert set(placed)==owned,('missing',sorted(owned-set(placed)))
# Physical bbox proof: actual current target footprints, all reserved bodies/holes included during packing.
report={'owned_placed':len(placed),'missing':[],'same_side_courtyard_intersections':[],'reserved_geometry_intersections':[],'grid_mm':.1,'courtyard_min_pack_gap_mm':.06,'checks':'Exact KiCad target courtyard bounding boxes (stroke-inclusive), plus plated drill/pad reservations on opposite side, bulk-cap holes radius1.5mm, M2 radius2.25mm, current83power placements, fixed auxiliary bounds. Rectangles are conservative for nonrectangular courtyard. No route or thermal proof.'}
result=dict(data);result.update(stage='all184_actual_coordinates_geometrically_packed',placements=placed,pending_placement_refs=[],validation=report)
result['coordinate_convention']='Top-view millimetres; native footprint origin; side first with Flip(origin,False), then SetOrientationDegrees(rotation_deg).'
result['notes']=[
 'All184 owned references are placed, including complete hard protection and DNP options;18 current sense/window refs are excluded and remain root-owned.',
 'Original MCU LQFP64, all7hard protection logic packages, four voltage followers and separate OV/UV comparator are retained.89 ordinary resistors and40 small capacitors use the previously explicit0402 list;16 voltage-divider resistors and reference/bulk capacitors keep their sizes.',
 'Front quiet strip is used by voltage followers/protection; back MCU/ADC quiet region stays x<34,y<36. The front strip y15..18 and LED perimeter y57..59.7 are additional real empty board space beyond the main y18..41 control partition.',
 'J9..J12 left headers start below the bus terminal/fuse, J13/J14/J8 are bottom, J15 CAN is at clear top-right edge. All original physical pin numbers and net assignments are preserved; CAN remains DNP.',
 'This is complete candidate placement, not production routing approval. Dense local analog routes, voltage divider guard/clearance, per-pin decoupling and access for probes require inspection after routing. All target copper clearance and assembly checks still need actual KiCad DRC of merged board.'
]
result['partitions']={k:{'sides':sorted(set(placed[r]['side'] for r in rs if r in placed)),'refs':rs,'bbox_by_side':{s:[min(placed[r]['courtyard_bbox_mm'][0] for r in rs if r in placed and placed[r]['side']==s),min(placed[r]['courtyard_bbox_mm'][1] for r in rs if r in placed and placed[r]['side']==s),max(placed[r]['courtyard_bbox_mm'][2] for r in rs if r in placed and placed[r]['side']==s),max(placed[r]['courtyard_bbox_mm'][3] for r in rs if r in placed and placed[r]['side']==s)] for s in sorted(set(placed[r]['side'] for r in rs if r in placed))}} for k,rs in data['group_refs'].items()}
OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PLACED',len(placed),'F',sum(w['side']=='F' for w in placed.values()),'B',sum(w['side']=='B' for w in placed.values()))
for r in ['U6','U13','U14','U15','U16','U17','U21','U28','U30','U31','Y1','SW2']:print(r,placed[r])







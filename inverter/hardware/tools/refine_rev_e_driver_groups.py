"""Local group placement of drivers/bootstraps before recreating review copper."""
from pathlib import Path
import json,math
import pcbnew as p
from layout_rev_e_pcb import courtyard,overlap,move,pad_box

B=Path(__file__).resolve().parents[1];F=B/'review/pcb_rev_e_2026-11-11/work/inverter.kicad_pcb';R=F.parents[1]


def main():
 pro=F.with_suffix('.kicad_pro').read_bytes();b=p.LoadBoard(str(F));fps={f.GetReference():f for f in b.GetFootprints()};spec={}
 for i,yy in enumerate([117.4,132.4,147.4]):
  spec['U'+str(7+i)]={'side':'B','x':148,'y':yy+3.1,'rotation_deg':180}
  spec['R'+str(19+6*i)]={'side':'B','x':140,'y':yy-.95,'rotation_deg':0}
  spec['R'+str(20+6*i)]={'side':'B','x':152.85,'y':yy-.5,'rotation_deg':90}
  spec['C'+str(25+4*i)]={'side':'B','x':140.5,'y':yy+2.465,'rotation_deg':270}
  spec['C'+str(26+4*i)]={'side':'B','x':143.3,'y':yy+2.465,'rotation_deg':270}
  spec['C'+str(27+4*i)]={'side':'F','x':147 if i<2 else 145.6,'y':yy+6.6 if i<2 else 155.6,'rotation_deg':0}
  spec['C'+str(28+4*i)]={'side':'B' if i<2 else 'F','x':144 if i<2 else 146,'y':yy+7 if i<2 else 152.8,'rotation_deg':0 if i<2 else 180}
 spec['U29']={'side':'B','x':142,'y':156.2,'rotation_deg':0}
 spec['R20']['y']=117.9
 spec['TP11']={'side':'B','x':151.5,'y':125.0,'rotation_deg':0}
 spec['TP12']={'side':'B','x':151.5,'y':140.0,'rotation_deg':0}
 spec['TP13']={'side':'B','x':134.5,'y':132.0,'rotation_deg':0}
 spec['D203']={'side':'B','x':122.0,'y':116.0,'rotation_deg':90}
 spec['F1']={'side':'F','x':129.0,'y':104.0,'rotation_deg':0}
 spec['J14']={'side':'F','x':129.8,'y':108.0,'rotation_deg':90}
 spec['R138']={'side':'B','x':124.5,'y':112.5,'rotation_deg':0}
 spec['R55']={'side':'B','x':126.0,'y':115.5,'rotation_deg':90}
 moving=set(spec);evicted=set();placed=[];old={}
 reserved_back_banks=[(130.1,102.4,132.8,105.6),(150.3,126.9,152.7,129.1),(150.3,141.9,152.7,144.1),(148.8,156.9,151.2,159.1)]
 def setwhere(f,s):
  if f.IsFlipped()!=(s['side']=='B'):f.Flip(f.GetPosition(),False)
  move(f,s['x'],s['y'],s['rotation_deg'])
 geom_cache={}
 def geometry(f):
  pos=f.GetPosition();key=(f.m_Uuid.AsString(),pos.x,pos.y,f.GetOrientationDegrees(),f.IsFlipped())
  if key not in geom_cache:
   f.BuildCourtyardCaches();boxes={}
   for layer in [p.F_CrtYd,p.B_CrtYd]:
    sh=f.GetCourtyard(layer)
    if sh.OutlineCount():
     box=sh.BBox();boxes[layer]=tuple(p.ToMM(v) for v in [box.GetX(),box.GetY(),box.GetRight(),box.GetBottom()])
   geom_cache[key]=(boxes,[pad_box(q) for q in f.Pads() if q.GetAttribute()==p.PAD_ATTRIB_PTH])
  return geom_cache[key]
 def conflict(f,other):
  aa,apads=geometry(f);bb,bpads=geometry(other)
  for layer in [p.F_CrtYd,p.B_CrtYd]:
   if layer in aa and layer in bb and overlap(aa[layer],bb[layer]):return True
  active=aa.get(p.B_CrtYd if f.IsFlipped() else p.F_CrtYd)
  if active is None:active=courtyard(f)
  if any(overlap(active,q) for q in bpads):return True
  other_active=bb.get(p.B_CrtYd if other.IsFlipped() else p.F_CrtYd)
  if other_active is None:other_active=courtyard(other)
  if any(overlap(other_active,q) for q in apads):return True
  return False
 def valid_edges(f):
  z=courtyard(f)
  if not(100.5<=z[0] and 100.5<=z[1] and z[2]<=159.5 and z[3]<=159.5):return False
  if f.GetReference() in {'U25','U26'} and z[2]>134.0:return False
  if f.IsFlipped() and any(overlap(z,a,0) for a in reserved_back_banks):return False
  for h in ['H1','H2','H3','H4']:
   pt=fps[h].GetPosition();x,y=p.ToMM(pt.x),p.ToMM(pt.y);near=(max(z[0],min(x,z[2])),max(z[1],min(y,z[3])))
   if math.dist(near,(x,y))<2.8:return False
  return True
 for ref,f in fps.items():
  if ref not in moving and f.IsFlipped() and ref.startswith(('R','C','TP','D20','D21')) and any(overlap(courtyard(f),a,0) for a in reserved_back_banks):evicted.add(ref)
 for ref,s in spec.items():
  f=fps[ref];old[ref]={'x':p.ToMM(f.GetPosition().x),'y':p.ToMM(f.GetPosition().y),'rotation_deg':f.GetOrientationDegrees(),'side':'B' if f.IsFlipped() else 'F'};setwhere(f,s)
  assert valid_edges(f),('edge',ref)
  for other in placed:assert not conflict(f,other),('new group overlap',ref,other.GetReference())
  for rr,o in fps.items():
   if rr in moving or rr in evicted or rr.startswith('H'):continue
   if conflict(f,o):
    assert rr.startswith(('R','C','TP')) or rr in {'U25','U26'} or (rr.startswith('D2') and len(rr)>2),('new driver group hits fixed IC/connector',ref,rr)
    evicted.add(rr)
  placed.append(f)
 fixed=[f for ref,f in fps.items() if ref not in evicted]
 def eviction_order(ref):
  box=courtyard(fps[ref])
  return (0 if ref.startswith('U') else 1, -(box[2]-box[0])*(box[3]-box[1]),ref)
 protected=set(spec)
 for filename in ['compact_power_placement.json','compact_aux_placement.json']:
  protected.update(json.loads((B/'tools'/filename).read_text(encoding='utf-8'))['placements'])
 pending=sorted(evicted,key=eviction_order)
 while pending:
  ref=pending.pop(0)
  f=fps[ref];ox,oy=p.ToMM(f.GetPosition().x),p.ToMM(f.GetPosition().y);old[ref]={'x':ox,'y':oy,'rotation_deg':f.GetOrientationDegrees(),'side':'B' if f.IsFlipped() else 'F'};found=False
  if ref in {'U25','U26'}:
   best=None
   original_side='B' if f.IsFlipped() else 'F';angle=f.GetOrientationDegrees()
   for side in [original_side,'F' if original_side=='B' else 'B']:
    for xi in range(218,263):
     for yi in range(208,307):
      x,y=xi/2,yi/2
      setwhere(f,{'x':x,'y':y,'side':side,'rotation_deg':angle})
      if not valid_edges(f):continue
      blocked=[o for o in fixed if o is not f and conflict(f,o)]
      if any(o.GetReference() in protected or not o.GetReference().startswith(('R','C','TP','D20','D21')) for o in blocked):continue
      score=6*len(blocked)+math.dist((x,y),(ox,oy))+(2 if side!=original_side else 0)
      if best is None or score<best[0]:best=(score,x,y,side,blocked)
   assert best,('no quiet logic location with passive evacuation',ref)
   _,x,y,side,blocked=best;setwhere(f,{'x':x,'y':y,'side':side,'rotation_deg':angle})
   for o in blocked:
    rr=o.GetReference();fixed.remove(o)
    if rr not in evicted:evicted.add(rr);pending.append(rr)
   found=True
  for rad in [] if found else [.3*i for i in range(1,61)]:
   for k in range(32):
    x=round(ox+rad*math.cos(k*math.pi/16),3);y=round(oy+rad*math.sin(k*math.pi/16),3);move(f,x,y)
    if not valid_edges(f) or any(conflict(f,o) for o in fixed if o is not f):continue
    found=True;break
   if found:break
  if not found:
   f.Flip(f.GetPosition(),False)
   for rad in [.4*i for i in range(1,101)]:
    for k in range(32):
     x=round(ox+rad*math.cos(k*math.pi/16),3);y=round(oy+rad*math.sin(k*math.pi/16),3);move(f,x,y)
     if not valid_edges(f) or any(conflict(f,o) for o in fixed if o is not f):continue
     found=True;break
    if found:break
  assert found,('cannot relocate passive',ref)
  spec[ref]={'side':'B' if f.IsFlipped() else 'F','x':p.ToMM(f.GetPosition().x),'y':p.ToMM(f.GetPosition().y),'rotation_deg':f.GetOrientationDegrees()};fixed.append(f)
 b.BuildConnectivity();p.SaveBoard(str(F),b);F.with_suffix('.kicad_pro').write_bytes(pro)
 (R/'driver_group_refinements.json').write_text(json.dumps({'placements':spec,'before':old,'moved_secondary_passives':sorted(evicted)},indent=2),encoding='utf-8');print('Refined',len(spec),'drivers/caps/passives',sorted(evicted),flush=True)


if __name__=='__main__':main()

"""Private, no-save per-net In3 rip-up trials against actual filled VBUS."""
from pathlib import Path
import pcbnew as p,hashlib,json,collections,time
BASE=Path(__file__).resolve().parent
SOURCE=BASE.parent/'plane_priority_fix/inverter.kicad_pcb'
snapshot=BASE/'input.kicad_pcb';snapshot.write_bytes(SOURCE.read_bytes())
snapshot.with_suffix('.kicad_pro').write_bytes(SOURCE.with_suffix('.kicad_pro').read_bytes())
sha=hashlib.sha256(snapshot.read_bytes()).hexdigest()
layers=[p.F_Cu,p.In1_Cu,p.In2_Cu,p.In3_Cu,p.In4_Cu,p.B_Cu]
def objects(board):
 return [a for f in board.GetFootprints() for a in f.Pads() if a.GetNumber()]+list(board.GetTracks())
def evaluate(board):
 fps={f.GetReference():f for f in board.GetFootprints()}
 required={r+'.'+pin:next(a for a in fps[r].Pads() if a.GetNumber()==pin) for r,pin in [('D1','2'),('C19','1'),('C20','1'),('C21','1'),('C22','1'),('J5','1')]}
 code=required['D1.2'].GetNetCode();nodes=[];uids={}
 for item in objects(board):
  if item.GetNetCode()!=code:continue
  shapes={ly:item.GetEffectiveShape(ly) for ly in layers if item.IsOnLayer(ly)}
  if shapes:uids[item.m_Uuid.AsString()]=len(nodes);nodes.append(shapes)
 islands=[]
 for raw in board.Zones():
  z=raw if isinstance(raw,p.ZONE) else p.Cast_to_ZONE(raw)
  if z.GetIsRuleArea() or z.GetNetCode()!=code:continue
  for ly in layers:
   if not z.IsOnLayer(ly):continue
   poly=z.GetFilledPolysList(ly)
   for i in range(poly.OutlineCount()):
    shape=poly.UnitSet(i);nodes.append({ly:shape})
    if ly==p.In3_Cu:
     bb=shape.BBox();islands.append([p.ToMM(v) for v in [bb.GetLeft(),bb.GetTop(),bb.GetRight(),bb.GetBottom()]])
 parent=list(range(len(nodes)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 boxes=[{ly:sh.BBox() for ly,sh in ss.items()} for ss in nodes]
 for i,a in enumerate(nodes):
  for j in range(i):
   z=nodes[j]
   if any(boxes[i][ly].Intersects(boxes[j][ly]) and a[ly].Collide(z[ly],0) for ly in a.keys()&z.keys()):parent[root(i)]=root(j)
 refroots={ref:root(uids[a.m_Uuid.AsString()]) for ref,a in required.items()};d=refroots['D1.2']
 return {'terminal_components':len(set(refroots.values())),'to_D1':{r:v==d for r,v in refroots.items()},'In3_islands':len(islands),'In3_island_bboxes':islands}
def trial(nets):
 b=p.LoadBoard(str(snapshot));removed=[]
 for t in list(b.GetTracks()):
  if not isinstance(t,p.PCB_VIA) and not t.IsLocked() and t.GetLayer()==p.In3_Cu and t.GetNetname() in nets:
   removed.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname(),'a':[p.ToMM(t.GetStart().x),p.ToMM(t.GetStart().y)],'b':[p.ToMM(t.GetEnd().x),p.ToMM(t.GetEnd().y)],'width':p.ToMM(t.GetWidth())});b.Remove(t)
 filler=p.ZONE_FILLER(b);filler.Fill(b.Zones());b.BuildConnectivity()
 return evaluate(b),removed
b=p.LoadBoard(str(snapshot));nets=collections.Counter(t.GetNetname() for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and not t.IsLocked() and t.GetLayer()==p.In3_Cu)
result={'source':str(SOURCE),'source_sha':sha,'removed_layers':['In3.Cu'],'only_unlocked_tracks':True,'net_track_counts':dict(nets),'baseline':evaluate(b),'trials':[]}
for label,ns in [('ALL',set(nets))]+[(n,{n}) for n in nets]:
 st=time.monotonic();out,removed=trial(ns);row={'net':label,'result':out,'removed':removed,'seconds':round(time.monotonic()-st,3)};result['trials'].append(row)
 (BASE/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(label,out['terminal_components'],out['to_D1'],out['In3_islands'],round(time.monotonic()-st,3),flush=True)
result['source_unchanged']=hashlib.sha256(SOURCE.read_bytes()).hexdigest()==sha
(BASE/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')

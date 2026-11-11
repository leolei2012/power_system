"""Independent additive candidate for seven ties and local BB attachments."""
from pathlib import Path
import sys,json,hashlib,shutil,math,fnmatch
import pcbnew as p

BASE=Path(__file__).resolve().parent
SOURCE=BASE.parent/'fourth_finish/inverter.kicad_pcb'
sys.path.insert(0,str(BASE.parents[2]/'tools'))
from reve_local_astar import route
MM=p.FromMM
V=lambda q:p.VECTOR2I(MM(q[0]),MM(q[1]))
XY=lambda q:[p.ToMM(q.x),p.ToMM(q.y)]
SHA=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
sha=SHA(SOURCE)
candidate=BASE/'inverter.kicad_pcb'
shutil.copy2(SOURCE,candidate)
project=SOURCE.with_suffix('.kicad_pro').read_bytes()
candidate.with_suffix('.kicad_pro').write_bytes(project)
for name in ['fp-lib-table','sym-lib-table']:
 (BASE/name).write_text((SOURCE.parent/name).read_text(encoding='utf-8').replace('${KIPRJMOD}',SOURCE.parent.as_posix()),encoding='utf-8')
b=p.LoadBoard(str(candidate))
pads={(f.GetReference(),a.GetNumber()):a for f in b.GetFootprints() for a in f.Pads() if a.GetNumber()}
proj=json.loads(project);classes={c['name']:c['clearance'] for c in proj['net_settings']['classes']}
def clear(n):return max([.15]+[classes[x['netclass']] for x in proj['net_settings']['netclass_patterns'] if fnmatch.fnmatchcase(n,x['pattern'])])
def line_ok(net,layer,width,a,z):
 ly=b.GetLayerID(layer);code=b.FindNet(net).GetNetCode();shape=p.SHAPE_SEGMENT(V(a),V(z),MM(width))
 for q in [a for f in b.GetFootprints() for a in f.Pads()]+list(b.GetTracks()):
  if q.GetNetCode()==code:continue
  if q.IsOnLayer(ly) and q.GetEffectiveShape(ly).Collide(shape,MM(max(clear(net),clear(q.GetNetname())))):return False
  if isinstance(q,p.PAD) and q.GetDrillSize().x and q.GetEffectiveHoleShape().Collide(shape,MM(.25)):return False
 for raw in b.Zones():
  zz=raw if isinstance(raw,p.ZONE) else p.Cast_to_ZONE(raw)
  if zz.GetIsRuleArea() and zz.GetDoNotAllowTracks() and zz.IsOnLayer(ly) and zz.Outline().Collide(shape,0):return False
 return True
patch={'source_sha':sha,'source_board':str(SOURCE),'ripup_uuids':[],'paths':[],'vias':[],'placements':{},'unresolved':[]}
def add(net,ly,width,pts,refs=None,reason=''):
 assert all(line_ok(net,ly,width,a,z) for a,z in zip(pts,pts[1:])),(net,pts)
 for a,z in zip(pts,pts[1:]):
  if a==z:continue
  t=p.PCB_TRACK(b);t.SetStart(V(a));t.SetEnd(V(z));t.SetWidth(MM(width));t.SetLayer(b.GetLayerID(ly));t.SetNet(b.FindNet(net));b.Add(t)
 patch['paths'].append({'net':net,'layer':ly,'width':width,'points':pts,'endpoint_refs':refs,'reason':reason,'locked':False})
def via_ok(net,at):
 code=b.FindNet(net).GetNetCode();circle=p.SHAPE_CIRCLE(V(at),MM(.3));drill=p.SHAPE_CIRCLE(V(at),MM(.15))
 for q in [a for f in b.GetFootprints() for a in f.Pads()]+list(b.GetTracks()):
  if q.GetNetCode()!=code:
   for ly in b.GetEnabledLayers().CuStack():
    if q.IsOnLayer(ly) and q.GetEffectiveShape(ly).Collide(circle,MM(max(clear(net),clear(q.GetNetname())))):return False
  if isinstance(q,p.PAD):
   if q.GetAttribute()==p.PAD_ATTRIB_SMD:
    for ly in [p.F_Cu,p.B_Cu]:
     if q.IsOnLayer(ly) and q.GetEffectiveShape(ly).Collide(circle,MM(.05)):return False
   if q.GetDrillSize().x and q.GetEffectiveHoleShape().Collide(drill,MM(.25)):return False
  elif isinstance(q,p.PCB_VIA) and q.GetEffectiveHoleShape().Collide(drill,MM(.25)):return False
 for raw in b.Zones():
  zz=raw if isinstance(raw,p.ZONE) else p.Cast_to_ZONE(raw)
  if zz.GetIsRuleArea() and zz.GetDoNotAllowVias() and zz.Outline().Collide(circle,0):return False
 return True
def via(net,at):
 assert via_ok(net,at)
 q=p.PCB_VIA(b);q.SetPosition(V(at));q.SetWidth(MM(.6));q.SetDrill(MM(.3));q.SetViaType(p.VIATYPE_THROUGH);q.SetLayerPair(p.F_Cu,p.B_Cu);q.SetNet(b.FindNet(net));b.Add(q)
 patch['vias'].append({'net':net,'x':at[0],'y':at[1],'diameter':.6,'drill':.3})

net='/Driver supply/BB_L1'; start=[124.525,135.3]
for goal in [[127.376,141.749],[127.25,141.70],[126.9,141.56]]:
 pts,info=route(b,net,'B.Cu',.6,start,goal,margin=5,limit=12,step=.05)
 print(net,goal,info,flush=True)
 if not pts:continue
 try:add(net,'B.Cu',.6,pts,['L1.1','existing BB_L1 via/locked feeder'],'new-source local actual-shape A* attachment')
 except AssertionError:continue
 break
else:patch['unresolved'].append({'net':net,'reason':'No .6 local B route found'})
filler=p.ZONE_FILLER(b);filler.Fill(b.Zones());b.BuildConnectivity();p.SaveBoard(str(candidate),b);candidate.with_suffix('.kicad_pro').write_bytes(project)
assert SHA(SOURCE)==sha
patch['candidate']=str(candidate);patch['candidate_sha']=SHA(candidate);patch['source_unchanged']=True
(BASE/'patch.json').write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8')
print('Saved',len(patch['paths']),'paths',len(patch['vias']),'vias',flush=True)

"""Independent additive candidate for seven ties and local BB attachments."""
from pathlib import Path
import sys,json,hashlib,shutil,math,fnmatch
import pcbnew as p

BASE=Path(__file__).resolve().parent
SOURCE=BASE.parent/'full_route/inverter.kicad_pcb'
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

for ref in ['U22','U23','U24','U15','U16','U17','U13']:
 a,z=pads[ref,'3'],pads[ref,'4'];assert a.GetNetCode()==z.GetNetCode()
 add(a.GetNetname(),'F.Cu',.15,[XY(a.GetPosition()),XY(z.GetPosition())],[ref+'.3',ref+'.4'],'same-package local tie')

cases=[('/Driver supply/BB_L1','B.Cu',.6,[124.525,135.3],[127.376,141.749],['L1.1','existing BB_L1 through-via']),
       ('/Driver supply/BB_VREG','B.Cu',.2,[119.6,144.475],[119.6,145.775],['U2.14','U2.12'])]
for net,ly,width,start,goal,refs in cases:
 pts,info=route(b,net,ly,width,start,goal,margin=4,limit=15,step=.05)
 print(net,info,flush=True)
 if pts:
  try:add(net,ly,width,pts,refs,'local actual-shape A* attachment')
  except AssertionError:patch['unresolved'].append({'net':net,'reason':'conservative final native geometry rejected A* proposal'})
 else:patch['unresolved'].append({'net':net,'reason':info})

net='/Driver supply/BB_VREG';tp=XY(pads['TP2','1'].GetPosition());start=[116.55,148.2]
for dx,dy in [(1.5,2),(0,2),(2,2),(-1.5,2),(2,0),(0,-2),(0,2.5),(2.5,2),(0,-1),(1,0),(-1,0),(0,1),(1,-1),(-1,-1),(1,1),(-1,1),(0,-1.5),(1.5,0),(-1.5,0),(3,0),(-3,0),(0,3)]:
 at=[tp[0]+dx,tp[1]+dy]
 if not via_ok(net,at) or not line_ok(net,'F.Cu',.2,at,tp):continue
 pts,info=route(b,net,'B.Cu',.2,start,at,margin=4,limit=6,step=.1)
 if not pts:continue
 try:add(net,'B.Cu',.2,pts,['C10.1','new testpoint via'],'local VREG testpoint branch')
 except AssertionError:continue
 via(net,at);add(net,'F.Cu',.2,[at,tp],['new testpoint via','TP2.1'],'testpoint terminal connection')
 print('VREG TP2',info,at,flush=True);break
else:patch['unresolved'].append({'net':net,'reason':'No simple TP2 via/branch found'})

filler=p.ZONE_FILLER(b);filler.Fill(b.Zones());b.BuildConnectivity();p.SaveBoard(str(candidate),b);candidate.with_suffix('.kicad_pro').write_bytes(project)
assert SHA(SOURCE)==sha
patch['candidate']=str(candidate);patch['candidate_sha']=SHA(candidate);patch['source_unchanged']=True
(BASE/'patch.json').write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8')
print('Saved',len(patch['paths']),'paths',len(patch['vias']),'vias',flush=True)

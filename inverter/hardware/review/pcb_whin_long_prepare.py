from pathlib import Path
import pcbnew as p,json,shutil,hashlib
B=Path(__file__).resolve().parents[1];R=B/'review';src=B/'inverter.kicad_pcb';dst=R/'inverter_whin_long_candidate.kicad_pcb'
shutil.copy2(src,dst);shutil.copy2(B/'inverter.kicad_pro',R/'inverter_whin_long_candidate.kicad_pro');b=p.LoadBoard(str(dst));sha=hashlib.sha256(src.read_bytes()).hexdigest()
MM=p.FromMM;V=lambda a:p.VECTOR2I(MM(a[0]),MM(a[1]));L={'F.Cu':p.F_Cu,'In2.Cu':p.In2_Cu,'B.Cu':p.B_Cu}
nets={q.GetNetname():q for q in b.GetNetsByNetcode().values()}
def apply(d):
 ids=set(d['ripup_uuids'])
 for q in list(b.GetTracks()):
  if q.m_Uuid.AsString() in ids:b.Delete(q)
 for s in d['paths']:
  for a,z in zip(s['points'],s['points'][1:]):
   t=p.PCB_TRACK(b);t.SetStart(V(a));t.SetEnd(V(z));t.SetWidth(MM(s['width']));t.SetLayer(L[s['layer']]);t.SetNet(nets[s['net']]);b.Add(t)
 for s in d.get('vias',[]):
  v=p.PCB_VIA(b);v.SetPosition(V([s['x'],s['y']]));v.SetWidth(MM(s['diameter']));v.SetDrill(MM(s['drill']));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(nets[s['net']]);v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);b.Add(v)
deps=[]
for f in ['pcb_final_whin_routes.json','pcb_final_power_routes.json']:
 d=json.loads((B/'tools'/f).read_text(encoding='utf-8'));assert d['source_sha']==sha;apply(d);deps.append(f)
rip=[]
for q in list(b.GetTracks()):
 if not isinstance(q,p.PCB_VIA) and q.GetNetname()=='W_HIN' and q.GetLayer()==p.B_Cu:
  assert not q.IsLocked();rip.append(q.m_Uuid.AsString());b.Delete(q)
objects=[];xy=lambda q:[p.ToMM(q.x),p.ToMM(q.y)]
def clear(net):return .4 if net in ['VBUS','U_PHASE','V_PHASE','W_PHASE','/Bus and brake/BR_SW','/Bus and brake/DC_FUSED','/Bus and brake/DC_INPUT_POS'] else .2
for q in b.GetTracks():
 if q.GetNetname()=='W_HIN':continue
 if isinstance(q,p.PCB_VIA):objects.append({'kind':'circle','net':q.GetNetname(),'layers':[0,1,2],'at':xy(q.GetPosition()),'radius':p.ToMM(q.GetWidth(p.F_Cu))/2,'clear':clear(q.GetNetname())})
 else:
  layer=next((i for i,x in enumerate([p.F_Cu,p.In2_Cu,p.B_Cu]) if x==q.GetLayer()),None)
  # In1 traces still need to block through vias.
  objects.append({'kind':'line','net':q.GetNetname(),'layers':[layer] if layer is not None else [],'via_only':layer is None,'a':xy(q.GetStart()),'b':xy(q.GetEnd()),'radius':p.ToMM(q.GetWidth())/2,'clear':clear(q.GetNetname())})
for f in b.GetFootprints():
 for q in f.Pads():
  if q.GetNetname()=='W_HIN':continue
  box=q.GetBoundingBox();layers=[i for i,ly in enumerate([p.F_Cu,p.In2_Cu,p.B_Cu]) if q.IsOnLayer(ly)]
  objects.append({'kind':'rect','net':q.GetNetname(),'layers':layers,'box':[p.ToMM(box.GetX()),p.ToMM(box.GetY()),p.ToMM(box.GetRight()),p.ToMM(box.GetBottom())],'clear':clear(q.GetNetname())})
for z in b.Zones():
 if z.GetLayer()==p.B_Cu and z.GetNetname().endswith('_PHASE'):
  bb=z.Outline().BBox();objects.append({'kind':'rect','net':z.GetNetname(),'layers':[2],'zone':True,'box':[p.ToMM(bb.GetX()),p.ToMM(bb.GetY()),p.ToMM(bb.GetRight()),p.ToMM(bb.GetBottom())],'clear':.4})
# Reserve sibling's planned VBUS feeder; it is not committed in this patch.
objects.append({'kind':'line','net':'VBUS','layers':[2],'a':[134.025,71.5],'b':[158.625,71.5],'radius':1,'clear':.4,'zone':True})
b.BuildConnectivity();p.SaveBoard(str(dst),b)
data={'source_sha':sha,'dependencies':deps,'ripup_uuids':rip,'objects':objects,'start':[156.117,50.9682],'goal':[145.513,81.3195]}
(R/'pcb_whin_long_obstacles.json').write_text(json.dumps(data),encoding='utf-8');print('objects',len(objects),'rip',len(rip))

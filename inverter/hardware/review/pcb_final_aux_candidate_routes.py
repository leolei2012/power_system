from pathlib import Path
import pcbnew as p,shutil,json,hashlib
B=Path(__file__).resolve().parents[1];R=B/'review'
src=B/'inverter.kicad_pcb';dest=R/'inverter_final_aux_candidate.kicad_pcb'
shutil.copy2(src,dest);shutil.copy2(B/'inverter.kicad_pro',R/'inverter_final_aux_candidate.kicad_pro')
sha=hashlib.sha256(src.read_bytes()).hexdigest();b=p.LoadBoard(str(dest))
rip=['0a72b7fe-8a2a-4bf7-be8f-f27e59ea1717','a9185f03-f5f6-417e-9b43-f5151a74b05b','2e0c3c23-ea33-4c5d-a196-9fd140de1def']
seen=[]
for q in list(b.GetTracks()):
 if q.m_Uuid.AsString() in rip:seen.append(q.m_Uuid.AsString());b.Delete(q)
assert set(seen)==set(rip)
net=next(n for n in b.GetNetsByNetcode().values() if n.GetNetname()=='+5V_INV')
paths=[{'net':'+5V_INV','layer':'F.Cu','width':.6,'points':[[87.8625,126.65],[87.8625,129]],'locked':False},{'net':'+5V_INV','layer':'F.Cu','width':.6,'points':[[91.475,119],[91.475,117.6]],'locked':False},{'net':'+5V_INV','layer':'In2.Cu','width':.6,'points':[[91.475,117.6],[91.475,129],[87.8625,129]],'locked':False}]
for spec in paths:
 for a,z in zip(spec['points'],spec['points'][1:]):
  t=p.PCB_TRACK(b);t.SetStart(p.VECTOR2I(p.FromMM(a[0]),p.FromMM(a[1])));t.SetEnd(p.VECTOR2I(p.FromMM(z[0]),p.FromMM(z[1])));t.SetWidth(p.FromMM(spec['width']));t.SetLayer({'F.Cu':p.F_Cu,'In2.Cu':p.In2_Cu,'B.Cu':p.B_Cu}[spec['layer']]);t.SetNet(net);b.Add(t)
vias=[]
for x,y in [[91.475,117.6],[87.8625,129]]:
 v=p.PCB_VIA(b);v.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)));v.SetWidth(p.FromMM(.8));v.SetDrill(p.FromMM(.4));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(net);v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);b.Add(v)
 vias.append({'net':'+5V_INV','x':x,'y':y,'diameter':.8,'drill':.4,'tented':True})
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();p.SaveBoard(str(dest),b)
patch={'source_sha':sha,'ripup_uuids':rip,'paths':paths,'vias':vias,'placements':{},'candidate':str(dest)}
(R/'pcb_final_aux_candidate_geometry.json').write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8')
print('candidate unconnected',b.GetConnectivity().GetUnconnectedCount(False))

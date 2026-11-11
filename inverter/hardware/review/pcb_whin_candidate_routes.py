from pathlib import Path
import pcbnew as p,shutil,json,hashlib
B=Path(__file__).resolve().parents[1];R=B/'review';src=B/'inverter.kicad_pcb';dest=R/'inverter_whin_candidate.kicad_pcb'
shutil.copy2(src,dest);shutil.copy2(B/'inverter.kicad_pro',R/'inverter_whin_candidate.kicad_pro')
sha=hashlib.sha256(src.read_bytes()).hexdigest();b=p.LoadBoard(str(dest))
rip=['bc8a773f-0a51-4a6d-9f90-f95211199bfa','52a79afc-9078-4f6f-9173-9b22d104ceae','be91ee5a-6d88-484c-b73e-63187eae5bed','5d84fb0a-e2a7-4f59-970e-cd8c073fad07','0e8b9c00-ce51-4621-a8d0-c1b007ce731e','04cc6d5b-a069-4837-bc7b-0295f28b2f70']
removed=[]
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in rip:
  assert not t.IsLocked();assert t.GetNetname()=='W_SOURCE';removed.append(t.m_Uuid.AsString());b.Delete(t)
assert set(removed)==set(rip)
nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()}
paths=[{'net':'W_HIN','layer':'In2.Cu','width':.2,'points':[[156.117,50.9682],[156.117,48.5],[158.9,48.5]],'locked':False},
 {'net':'W_HIN','layer':'F.Cu','width':.2,'points':[[158.9,48.5],[159.7,48.5],[159.7,49.595],[160.925,49.595]],'locked':False},
 {'net':'W_SOURCE','layer':'F.Cu','width':.2,'points':[[158.825,49.6],[158.2,49.6]],'locked':False},
 {'net':'W_SOURCE','layer':'B.Cu','width':.2,'points':[[158.2,49.6],[158.825,52.135]],'locked':False},
 {'net':'W_SOURCE','layer':'F.Cu','width':.2,'points':[[158.825,52.135],[159.694,52.135]],'locked':False}]
V=lambda a:p.VECTOR2I(p.FromMM(a[0]),p.FromMM(a[1]))
for s in paths:
 for a,z in zip(s['points'],s['points'][1:]):
  t=p.PCB_TRACK(b);t.SetStart(V(a));t.SetEnd(V(z));t.SetWidth(p.FromMM(s['width']));t.SetLayer({'F.Cu':p.F_Cu,'B.Cu':p.B_Cu,'In2.Cu':p.In2_Cu}[s['layer']]);t.SetNet(nets[s['net']]);b.Add(t)
vias=[]
for netname,x,y in [['W_SOURCE',158.2,49.6],['W_SOURCE',158.825,52.135],['W_HIN',158.9,48.5]]:
 v=p.PCB_VIA(b);v.SetPosition(V([x,y]));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(nets[netname]);v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);b.Add(v)
 vias.append({'net':netname,'x':x,'y':y,'diameter':.6,'drill':.3,'tented':True})
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();p.SaveBoard(str(dest),b)
patch={'source_sha':sha,'ripup_uuids':rip,'paths':paths,'vias':vias,'placements':{},'candidate':str(dest)}
(R/'pcb_whin_candidate_geometry.json').write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8');print('candidate unconnected',b.GetConnectivity().GetUnconnectedCount(False))

from pathlib import Path
import pcbnew as p,json
R=Path(__file__).resolve().parent;dest=R/'inverter_whin_long_candidate.kicad_pcb';b=p.LoadBoard(str(dest));d=json.loads((R/'pcb_whin_long_geometry.json').read_text(encoding='utf-8'))
# Move lower crossover clear of the reserved future2mm VBUS feeder endpoint.
old=[159.45,72.95];new=[159.6,73.1]
for s in d['paths']:
 s['points']=[new if q==old else q for q in s['points']]
for v in d['vias']:
 if [v['x'],v['y']]==old:v['x'],v['y']=new
n=next(q for q in b.GetNetsByNetcode().values() if q.GetNetname()=='W_HIN');MM=p.FromMM;V=lambda a:p.VECTOR2I(MM(a[0]),MM(a[1]));layers={'F.Cu':p.F_Cu,'In2.Cu':p.In2_Cu,'B.Cu':p.B_Cu}
for s in d['paths']:
 for a,z in zip(s['points'],s['points'][1:]):
  if a==z:continue
  t=p.PCB_TRACK(b);t.SetStart(V(a));t.SetEnd(V(z));t.SetWidth(MM(s['width']));t.SetLayer(layers[s['layer']]);t.SetNet(n);b.Add(t)
for s in d['vias']:
 v=p.PCB_VIA(b);v.SetPosition(V([s['x'],s['y']]));v.SetWidth(MM(s['diameter']));v.SetDrill(MM(s['drill']));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(n);v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);b.Add(v)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();p.SaveBoard(str(dest),b);(R/'pcb_whin_long_applied_geometry.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print('unconnected',b.GetConnectivity().GetUnconnectedCount(False))

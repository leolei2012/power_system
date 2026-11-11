from pathlib import Path
import pcbnew as p, shutil, json, hashlib
B=Path(__file__).resolve().parents[1]
R=B/'review'
source=B/'inverter.kicad_pcb'
candidate=R/'inverter_aux_candidate.kicad_pcb'
shutil.copy2(source,candidate)
shutil.copy2(B/'inverter.kicad_pro',R/'inverter_aux_candidate.kicad_pro')
source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
board=p.LoadBoard(str(candidate))
fps={f.GetReference():f for f in board.GetFootprints()}
nets={n.GetNetname():n for n in board.GetNetsByNetcode().values()}
MM=p.FromMM
V=lambda x,y:p.VECTOR2I(MM(x),MM(y))
def pad(ref,num):return next(q for q in fps[ref].Pads() if q.GetNumber()==str(num))
def pt(ref,num):
 q=pad(ref,num).GetPosition();return [round(p.ToMM(q.x),6),round(p.ToMM(q.y),6)]
paths=[];vias=[];ripup=[]
for t in list(board.GetTracks()):
 name=t.GetNetname()
 if name.endswith(('/AUX_ILIM','/AUX_OV_DIV','/AUX_MODE','/AUX_SHDN_N')) or t.m_Uuid.AsString()=='92c8d919-5ded-4cb4-b3a0-dd986e8f88e7':
  ripup.append(t.m_Uuid.AsString());board.Delete(t);continue
 if name=='GND':
  if isinstance(t,p.PCB_VIA):
   q=t.GetPosition();coords=[(p.ToMM(q.x),p.ToMM(q.y))]
  else:coords=[(p.ToMM(q.x),p.ToMM(q.y)) for q in [t.GetStart(),t.GetEnd()]]
  if all(49.5<=x<=53 and 115<=y<=118.8 for x,y in coords):
   ripup.append(t.m_Uuid.AsString());board.Delete(t)
def path(ref,num,layer,width,points):
 net=pad(ref,num).GetNetname()
 points=[pt(*q) if isinstance(q,tuple) and isinstance(q[0],str) else list(q) for q in points]
 for a,b in zip(points,points[1:]):
  if a==b:continue
  t=p.PCB_TRACK(board);t.SetStart(V(*a));t.SetEnd(V(*b));t.SetWidth(MM(width));t.SetLayer({'F.Cu':p.F_Cu,'In2.Cu':p.In2_Cu,'B.Cu':p.B_Cu}[layer]);t.SetNet(nets[net]);board.Add(t)
 paths.append(dict(net=net,layer=layer,width=width,points=points,locked=False))
def via(ref,num,x,y):
 net=pad(ref,num).GetNetname();v=p.PCB_VIA(board);v.SetPosition(V(x,y));v.SetWidth(MM(.6));v.SetDrill(MM(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(nets[net]);v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);board.Add(v)
 vias.append(dict(net=net,x=x,y=y,diameter=.6,drill=.3,tented=True))
# Short local branches; preserve the existing routed network at each endpoint.
path('U1',12,'F.Cu',.2,[('U1',12),('C2',1)])
path('U2',3,'F.Cu',.2,[('U2',3),(50,117.375),('C4',1)])
path('U2',2,'F.Cu',.3,[('U2',2),(51.2,116.725)])
path('U2',2,'F.Cu',.6,[(51.2,116.725),(51.2,115.225),('C4',2)])
path('U1',11,'F.Cu',.2,[('U1',11),(32.95,119.475),(32.95,119.9),(33.3,120.25)])
via('U1',11,33.3,120.25)
path('U1',11,'F.Cu',.2,[('R6',1),(33,123.225)])
via('U1',11,33,123.225)
path('U1',11,'In2.Cu',.2,[(33.3,120.25),(33,120.55),(33,123.225)])
path('U2',1,'F.Cu',.2,[('U2',1),(51.8,116.075),(51.8,114.2)])
via('U2',1,51.8,114.2)
path('C7',2,'F.Cu',.2,[('C7',2),(50,119.3)])
via('C7',2,50,119.3)
# FLT locally returns to its pullup; the remote logic route is separate scope.
path('U1',14,'F.Cu',.2,[('U1',14),(33,117.525)])
via('U1',14,33,117.525)
path('U1',14,'F.Cu',.2,[('R7',1),(35.0,124)])
via('U1',14,35,124)
path('U1',14,'In2.Cu',.2,[(33,117.525),(35,119.525),(35,124)])
# Rebuild OV/MODE fanout to clear the UV/SHDN entry corridor.
path('U1',1,'F.Cu',.6,[(22.9512,116.748),(22.9512,115.5),(25.5,115.5),(25.5,116.225),('U1',1)])
path('U1',1,'F.Cu',.3,[('U1',1),('U1',2)])
path('U1',3,'F.Cu',.2,[('U1',3),(25.1,117.525),(24.6,117.025),(24.6,116.7)])
via('U1',3,24.6,116.7)
path('U1',3,'F.Cu',.2,[('R1',2),(23.825,118)])
via('U1',3,23.825,118)
path('U1',3,'In2.Cu',.2,[(24.6,116.7),(23.825,117.475),(23.825,118)])
path('U1',3,'F.Cu',.2,[('R1',2),(23.825,120),(22.175,120),('R2',1)])
path('U1',5,'F.Cu',.2,[('U1',5),(25.025,118.825),(24.7,118.5)])
via('U1',5,24.7,118.5)
path('U1',5,'F.Cu',.2,[('R3',2),(23.825,122.2)])
via('U1',5,23.825,122.2)
path('U1',5,'In2.Cu',.2,[(24.7,118.5),(23.3,119.9),(23.3,122.2),(23.825,122.2)])
path('U1',5,'F.Cu',.2,[('R3',2),(24.7,123),(24.7,124),(22.175,124),('R4',1)])
path('U1',6,'F.Cu',.2,[('U1',6),(25,119.475)])
via('U1',6,25,119.475)
path('U1',6,'F.Cu',.2,[('R5',1),(28,126.325)])
via('U1',6,28,126.325)
path('U1',6,'In2.Cu',.2,[(25,119.475),(27,121.475),(27,126.325),(28,126.325)])
path('U1',7,'F.Cu',.2,[('U1',7),(24.8,120.125),(24.8,120.3)])
via('U1',7,24.8,120.3)
path('U1',7,'F.Cu',.2,[('R8',2),(28.8,113)])
via('U1',7,28.8,113)
path('U1',7,'B.Cu',.2,[(28.8,113),(20,113),(20,120.3),(24.8,120.3)])
path('U1',7,'F.Cu',.2,[('SW1',1),(10,123.5)])
via('U1',7,10,123.5)
path('U1',7,'B.Cu',.2,[(10,123.5),(10,121.5),(20,121.5),(20,120.3)])
path('U1',7,'F.Cu',.2,[(11,123.5),(17.5,123.5)])
board.BuildConnectivity();p.ZONE_FILLER(board).Fill(board.Zones());board.BuildConnectivity()
p.SaveBoard(str(candidate),board)
patch=dict(source_sha=source_sha,ripup_uuids=ripup,paths=paths,vias=vias,placements={},candidate=str(candidate))
(R/'pcb_aux_candidate_geometry.json').write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8')
print('candidate',candidate,'paths',len(paths),'vias',len(vias),'unconnected',board.GetConnectivity().GetUnconnectedCount(False))

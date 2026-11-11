from pathlib import Path
import pcbnew as p,json,shutil,hashlib,sys
B=Path(__file__).resolve().parents[1];R=B/'review';src=B/'inverter.kicad_pcb';dst=R/'inverter_necks_candidate.kicad_pcb'
shutil.copy2(src,dst);shutil.copy2(B/'inverter.kicad_pro',R/'inverter_necks_candidate.kicad_pro');b=p.LoadBoard(str(dst));sha=hashlib.sha256(src.read_bytes()).hexdigest();MM=p.FromMM;mm=p.ToMM
xy=lambda q:[round(mm(q.x),6),round(mm(q.y),6)];V=lambda a:p.VECTOR2I(MM(a[0]),MM(a[1]));nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()};rip=[];new=[];unique=set();groups={}
keep_c22='--keep-c22-positive' in sys.argv
for t in list(b.GetTracks()):
 if isinstance(t,p.PCB_VIA) or not t.IsLocked() or t.GetLayer()!=p.F_Cu:continue
 a=xy(t.GetStart());z=xy(t.GetEnd());w=round(mm(t.GetWidth()),6);net=t.GetNetname();group=None
 if net in ['U_PHASE','V_PHASE','W_PHASE'] and w==1.1 and min(a[1],z[1])>=45.539 and max(a[1],z[1])<=47.341 and abs(a[0]-z[0])<.00001:group=net+'_high_source_common_neck'
 if net=='VBUS' and w==1.3 and min(a[1],z[1])>=67.499 and max(a[1],z[1])<=71.501:
  group='C21_positive' if max(a[0],z[0])<146 else 'C22_positive'
  if group=='C22_positive' and keep_c22:continue
  if group=='C21_positive' and abs(a[0]-z[0])>.00001:continue
 if net=='GND' and w==.7 and min(a[1],z[1])>=67.499 and max(a[1],z[1])<=72.001 and min(a[0],z[0])>136 and max(a[0],z[0])<165:group='C21_negative' if max(a[0],z[0])<150 else 'C22_negative'
 if group is None:continue
 rip.append(t.m_Uuid.AsString());groups.setdefault(group,{'old_width':w,'new_width':2.0,'original_segments':0});groups[group]['original_segments']+=1;b.Delete(t)
 if group=='C21_negative':continue
 key=(net,*sorted([tuple(a),tuple(z)]))
 if key in unique:continue
 unique.add(key);s={'net':net,'layer':'F.Cu','width':2.0,'points':[a,z],'locked':True,'group':group};new.append(s)
if 'C21_negative' in groups:
 for width,a,z in [(2,[136.975,67.5],[139.825,67.5]),(2,[139.825,67.5],[139.825,71]),(.7,[139.825,71],[139.825,72])]:new.append({'net':'GND','layer':'F.Cu','width':width,'points':[a,z],'locked':True,'group':'C21_negative'})
for s in new:
 a,z=s['points'];t=p.PCB_TRACK(b);t.SetStart(V(a));t.SetEnd(V(z));t.SetWidth(MM(s['width']));t.SetLayer(p.F_Cu);t.SetNet(nets[s['net']]);t.SetLocked(True);b.Add(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity();p.SaveBoard(str(dst),b)
retained={'C22_positive':{'width_mm':1.3,'reason':'W_HIN shortF crossover andI_V_PORT clearance prevent2mm widening; no core component moved.'},'C21_positive_bank_arms':{'width_mm':1.3,'reason':'Keep left bank short arm clear ofVBIAS via.'},'C21_negative_second_via_branch':{'width_mm':.7,'length_mm':1,'reason':'Only individual second-via tail remains narrow to keep clear ofVBIAS horizontal trace; common trunk widened to2mm.'},'phase_individual_via_arms':{'width_mm':1.1,'reason':'Short individual arms retain width to preserveHO/LIN clearance; all common source vertical necks widened to2mm.'}}
patch={'source_sha':sha,'ripup_uuids':rip,'paths':new,'vias':[],'placements':{},'candidate':str(dst),'width_changes':groups,'retained':retained}
(R/'pcb_necks_candidate_geometry.json').write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8');print('groups',groups,'unconnected',b.GetConnectivity().GetUnconnectedCount(False))

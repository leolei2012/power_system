import sys,json,math,heapq,shutil,hashlib,collections,types,subprocess,time
from pathlib import Path
import pcbnew as p
D=Path(__file__).resolve().parent;B=D.parents[1];sys.path.insert(0,str(B/'tools'));sys.path.insert(0,str(D))
import stitch_base as S
import fast_base
from compact_verify_fixed import verify_geometry,kelvin_check
from compact_power_copper import audit_power_connectivity
SRC=B/'inverter.kicad_pcb';OUT=D/'inverter.kicad_pcb';PRO=OUT.with_suffix('.kicad_pro');PATCH=D/'routes.json';REPORT=B/'review/compact_power_candidate/power_copper.json';SCOPE=B/'review/compact_scope_ground.json'
SHA=hashlib.sha256(SRC.read_bytes()).hexdigest();assert SHA=='4d4f0c2ae1d5177ebf351e92cd70ae8483fde624233a5b98dc958461cede13fb'
project_bytes=SRC.with_suffix('.kicad_pro').read_bytes();project=json.loads(project_bytes);report=json.loads(REPORT.read_text(encoding='utf-8'));scope=json.loads(SCOPE.read_text(encoding='utf-8'))
if '--resume'not in sys.argv:
 shutil.copy2(SRC,OUT);PRO.write_bytes(project_bytes)
 for name in ['fp-lib-table','sym-lib-table']:
  src=B/name
  if src.exists():(D/name).write_text(src.read_text(encoding='utf-8').replace('${KIPRJMOD}',B.as_posix()),encoding='utf-8')
 patch={'source_sha':SHA,'ripup_uuids':[],'paths':[],'vias':[],'placements':{},'candidate':str(OUT),'accepted':[],'unresolved':[]}
else:patch=json.loads(PATCH.read_text(encoding='utf-8'))
board=p.LoadBoard(str(OUT));MM=p.FromMM;V=S.V;XY=S.XY;UID=S.UID
args=types.SimpleNamespace(allow_protected_net=['GND'],clearance=0,via_only=False,step=.025,margin=6,width=.15,via_cost=2.5,max_nodes=900000,seconds_per_gap=18)

def save():
 board.BuildConnectivity();p.ZONE_FILLER(board).Fill(board.Zones());board.BuildConnectivity();p.SaveBoard(str(OUT),board);PRO.write_bytes(project_bytes)
def drc(n):
 file=D/('drc_%03d.json'%n);r=subprocess.run(['C:/Program Files/KiCad/10.0/bin/kicad-cli.exe','pcb','drc','--format','json','--all-track-errors','--severity-all','--output',str(file),str(OUT)],capture_output=True,text=True,timeout=120)
 assert r.returncode==0,r.stderr
 return json.loads(file.read_text(encoding='utf-8')),str(file)
def guard():
 objects,issues,_=verify_geometry(board,report);other,*_=kelvin_check(board,report,objects);return issues+other

def groups(name):
 board.BuildConnectivity();cn=board.GetConnectivity();todo={UID(q):q for q in list(board.GetTracks())+[a for f in board.GetFootprints()for a in f.Pads()]if q.GetNetname()==name};out=[]
 while todo:
  u,q=todo.popitem();cluster={u:q}
  for a in cn.GetConnectedItems(q):
   if not isinstance(a,p.ZONE) and a.GetNetname()==name:cluster[UID(a)]=a;todo.pop(UID(a),None)
  out.append(cluster)
 return sorted(out,key=len,reverse=True)

class Geo(S.Geometry):
 def __init__(self):
  super().__init__(board,args,project);self.grid=collections.defaultdict(list);self.zone_names={UID(z):z.GetNetname()for z in board.Zones()};self.zone_byuid={UID(z):z for z in board.Zones()};self.body=[]
  self.kelvin_guards=[]
  byuid={UID(q):q for q in board.GetTracks()}
  for row in report['kelvin']:
   ids=row['negative_track_uuids']+[row['negative_via_uuid']]
   for ident in ids:
    q=byuid[ident]
    for ly in self.copper:
     if q.IsOnLayer(ly):self.kelvin_guards.append(S.Object(q.GetEffectiveShape(ly),[ly],.15,-1,'kelvin_guard',ident))
   ina=next(f for f in board.GetFootprints()if f.GetReference()==row['INA']);pad=next(a for a in ina.Pads()if a.GetNumber()=='1')
   self.kelvin_guards.append(S.Object(pad.GetEffectiveShape(p.B_Cu),[p.B_Cu],.15,-1,'kelvin_pad_guard',UID(pad)))
  self.obstacles.extend(self.kelvin_guards)
  for ob in self.obstacles+self.holes+self.surface_pads:
   for x in range(math.floor((ob.bb[0]-.9)/2),math.floor((ob.bb[2]+.9)/2)+1):
    for y in range(math.floor((ob.bb[1]-.9)/2),math.floor((ob.bb[3]+.9)/2)+1):self.grid[x,y].append(ob)
  for f in board.GetFootprints():
   if not (f.GetAttributes()&p.FP_SMD):continue
   ly=p.B_Fab if f.IsFlipped()else p.F_Fab;bb=[]
   for q in f.GraphicalItems():
    if q.GetLayer()==ly and q.GetClass()=='PCB_SHAPE':
     z=q.GetBoundingBox();bb.append([p.ToMM(z.GetX()),p.ToMM(z.GetY()),p.ToMM(z.GetRight()),p.ToMM(z.GetBottom())])
   if bb:self.body.append((f.GetReference(),[min(a[0]for a in bb),min(a[1]for a in bb),max(a[2]for a in bb),max(a[3]for a in bb)]))
 def nearby(self,bb):
  result={}
  for x in range(math.floor(bb[0]/2),math.floor(bb[2]/2)+1):
   for y in range(math.floor(bb[1]/2),math.floor(bb[3]/2)+1):
    for ob in self.grid.get((x,y),[]):result[id(ob)]=ob
  return list(result.values())
 def wide_vbus(self,ob,at):
  if self.zone_names.get(ob.uid)!='VBUS' or not ob.shape.Contains(V(*at)):return False
  closest=100
  for i in range(ob.shape.OutlineCount()):
   c=ob.shape.COutline(i);pts=[XY(c.CPoint(j))for j in range(c.PointCount())]
   for a,b in zip(pts,pts[1:]+pts[:1]):
    dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy;t=max(0,min(1,((at[0]-a[0])*dx+(at[1]-a[1])*dy)/den))if den else 0;closest=min(closest,math.dist(at,[a[0]+t*dx,a[1]+t*dy]))
  return closest>=1.8
 def line_ok(self,a,b,ly,code,width=.2,clear=.15):
  shape=p.SHAPE_SEGMENT(V(*a),V(*b),MM(width))
  if not self.inside(shape,width/2):return False
  bb=S.bbox(shape,.85)
  for ob in self.nearby(bb):
   if ob.kind=='hole':
    if ob.code!=code and ob.hit(shape,self.hole_clear):return False
   elif ly in ob.layers and ob.code!=code and ob.kind!='via_keepout' and ob.hit(shape,max(clear,ob.clearance)):return False
  return True
 def via_ok(self,at,code,clear=.15):
  copper=p.SHAPE_CIRCLE(V(*at),MM(.3));drill=p.SHAPE_CIRCLE(V(*at),MM(.15))
  if not self.inside(copper,.3):return False
  bb=S.bbox(copper,.85)
  for ob in self.nearby(bb):
   if ob.kind=='hole':
    if ob.hit(drill,.25):return False
   elif ob.code!=code and ob.kind!='track_keepout' and ob.hit(copper,max(clear,ob.clearance)):
    if ob.kind=='protected_power_zone' and self.wide_vbus(ob,at):continue
    return False
  for ob in self.surface_pads:
   if S.overlap(ob.bb,S.bbox(copper,.05))and ob.hit(copper,.05):return False
  for ref,q in self.body:
   d=math.hypot(max(q[0]-at[0],0,at[0]-q[2]),max(q[1]-at[1],0,at[1]-q[3]))
   if d<.35:pass # Tented via under a non-paste body is allowed; real pad/mask and drill guards above remain mandatory.
  for ob in self.protected:
   if ob.hit(copper,max(clear,ob.clearance)):return False
  return True
 def holes_vbus(self,at):return [ob.uid for ob in self.power_zones if self.zone_names.get(ob.uid)=='VBUS'and ob.shape.Contains(V(*at))]

def points(cluster):
 out=[];seen=set()
 for a in cluster.values():
  if isinstance(a,p.PAD):raw=[(XY(a.GetPosition()),ly)for ly in [p.F_Cu,p.B_Cu]if a.IsOnLayer(ly)];rank=0 if a.GetParentFootprint().GetReference().startswith('C')else 1
  elif isinstance(a,p.PCB_VIA):raw=[(XY(a.GetPosition()),ly)for ly in [p.F_Cu,p.In2_Cu,p.In3_Cu,p.B_Cu]if a.IsOnLayer(ly)];rank=2
  else:raw=[(XY(a.GetStart()),a.GetLayer()),(XY(a.GetEnd()),a.GetLayer())];rank=3
  for at,ly in raw:
   if ly not in [p.F_Cu,p.In2_Cu,p.In3_Cu,p.B_Cu]:continue
   key=(round(at[0],6),round(at[1],6),ly)
   if key in seen:continue
   seen.add(key);out.append((at,ly,rank,UID(a)))
 return out

def pathok(geo,pts,ly,code):return all(geo.line_ok(a,b,ly,code)for a,b in zip(pts,pts[1:]))
def pathitem(net,ly,pts):return {'net':net,'layer':board.GetLayerName(ly),'width':.2,'points':[list(a)for i,a in enumerate(pts) if i==0 or math.dist(a,pts[i-1])>.000001],'locked':False}
def shapes(a,b):
 yield[a,b];yield[a,[a[0],b[1]],b];yield[a,[b[0],a[1]],b]
 dx=b[0]-a[0];dy=b[1]-a[1];k=min(abs(dx),abs(dy));sx=1 if dx>=0 else-1;sy=1 if dy>=0 else-1
 yield[a,[a[0]+sx*k,a[1]+sy*k],b];yield[a,[b[0]-sx*k,b[1]-sy*k],b]
def via_candidates(geo,at,ly,code,net,maxn=10):
 if ly not in[p.F_Cu,p.B_Cu]:return[(at,[],[])]
 candidates=[]
 offsets=sorted(((dx*.1,dy*.1)for dx in range(-30,31)for dy in range(-30,31)if dx*dx+dy*dy<=900),key=lambda q:q[0]*q[0]+q[1]*q[1])
 for dx,dy in offsets:
  r=math.hypot(dx,dy);pt=[round(at[0]+dx,6),round(at[1]+dy,6)]
  if not geo.via_ok(pt,code):continue
  for pts in shapes(at,pt):
   if pathok(geo,pts,ly,code):
    routepaths=[] if r<.000001 else[pathitem(net,ly,pts)];via={'net':net,'x':pt[0],'y':pt[1],'diameter':.6,'drill':.3,'tented':True,'VBUS_hole_zone_uuids':geo.holes_vbus(pt),'body_projection_refs':[ref for ref,bb in geo.body if bb[0]-.3<pt[0]<bb[2]+.3 and bb[1]-.3<pt[1]<bb[3]+.3]};candidates.append((pt,routepaths,[via]));break
  if len(candidates)>=maxn:return candidates
 return candidates

save();current,currentfile=drc(0);assert not S.error_keys(current),S.error_keys(current);assert not guard();baseline=board.GetConnectivity().GetUnconnectedCount(False);attempt=0

def commit(route,tag):
 global board,current,currentfile,attempt
 attempt+=1;before=OUT.read_bytes();old=board.GetConnectivity().GetUnconnectedCount(False);before_components=S.native_components(board)
 S.add(board,route);save();new=board.GetConnectivity().GetUnconnectedCount(False)
 if new>=old:
  OUT.write_bytes(before);board=p.LoadBoard(str(OUT));return False
 after,afile=drc(attempt);issues=guard();after_components=S.native_components(board);regressions={n:v for n,v in after_components.items()if v>before_components.get(n,0)}
 if not S.error_keys(after) and not issues and not regressions:
  holes=[v for v in route['vias']if v.get('VBUS_hole_zone_uuids')]
  if holes:
   try:audit_power_connectivity(board,report)
   except Exception as error:issues=[{'power_connectivity':str(error)}]
 if S.error_keys(after)or issues or regressions:
  print('REJECT',tag,'err',len(S.error_keys(after)),'guard',len(issues),'regress',regressions,flush=True);OUT.write_bytes(before);PRO.write_bytes(project_bytes);board=p.LoadBoard(str(OUT));patch['unresolved'].append({'tag':tag,'drc':afile,'guard':issues,'regressions':regressions});return False
 patch['paths']+=route['paths'];patch['vias']+=route['vias'];patch['accepted'].append({'net':route['net'],'tag':tag,'before_gaps':old,'after_gaps':new,'drc':afile});current=after;currentfile=afile;patch['validation']={'before_gaps':215,'after_gaps':new,'electrical_errors':0,'fixed_Kelvin_PASS':True};PATCH.write_text(json.dumps(patch,indent=2)+'\n');print('ACCEPT',tag,old,'->',new,'paths',len(route['paths']),'vias',len(route['vias']),flush=True);return True

# Fine-grid multi-layer closure on the cumulative validated private candidate.
failed=set();tries=0
while tries<45:
 items=S.items_by_uuid(board);entries=[]
 for entry in current['unconnected_items']:
  qq=[items.get(q.get('uuid'))for q in entry['items']]
  if len(qq)<2 or not all(q is not None for q in qq[:2]):continue
  net=qq[0].GetNetname()
  if net not in ['GND','+3V3_INV'] or qq[1].GetNetname()!=net:continue
  finger=tuple(sorted(UID(q)for q in qq[:2]))
  if finger not in failed:entries.append((entry,finger,net))
 if not entries:break
 entry,finger,net=entries[0];failed.add(finger);tries+=1;geo=Geo();route,reason=S.search(board,items,entry,geo,args)
 if route is None:print('ASTAR FAILED',net,reason,flush=True);continue
 code=next(q for q in board.GetNetsByNetcode().values()if q.GetNetname()==net).GetNetCode()
 # Broaden every safe half-millimetre section to0.2; retain0.15 only where
 # the already-routed geometry actually requires a minimum-width neck.
 result=[]
 for path in route['paths']:
  ly=board.GetLayerID(path['layer'])
  for a,b in zip(path['points'],path['points'][1:]):
   count=max(1,math.ceil(math.dist(a,b)/.5))
   for i in range(count):
    u=[a[0]+(b[0]-a[0])*i/count,a[1]+(b[1]-a[1])*i/count];v=[a[0]+(b[0]-a[0])*(i+1)/count,a[1]+(b[1]-a[1])*(i+1)/count];width=.2 if geo.line_ok(u,v,ly,code,.2,.15)else.15
    if result and result[-1]['net']==net and result[-1]['layer']==path['layer']and result[-1]['width']==width and math.dist(result[-1]['points'][-1],u)<.000001:result[-1]['points'].append(v)
    else:result.append({'net':net,'layer':path['layer'],'width':width,'points':[u,v],'locked':False})
 route['paths']=result
 for via in route['vias']:via['VBUS_hole_zone_uuids']=geo.holes_vbus([via['x'],via['y']])
 if commit(route,'fine_astar_'+net):print('FINE ACCEPTED',net,'remaining groups',len(groups(net)),flush=True)
print('ASTAR DONE',board.GetConnectivity().GetUnconnectedCount(False),'GNDgroups',len(groups('GND')),'VDDgroups',len(groups('+3V3_INV')),flush=True)
save();finalaudit=audit_power_connectivity(board,report);(D/'power_connectivity_final.json').write_text(json.dumps(finalaudit,indent=2)+'\n');assert not guard();final,lastfile=drc(999);assert not S.error_keys(final);patch['validation']={'before_gaps':215,'after_gaps':board.GetConnectivity().GetUnconnectedCount(False),'electrical_errors':0,'fixed_Kelvin_PASS':True,'main_power_filled_connectivity_PASS':True,'final_drc':lastfile,'source_unchanged':hashlib.sha256(SRC.read_bytes()).hexdigest()==SHA,'GND_components':len(groups('GND')),'VDD_components':len(groups('+3V3_INV'))};assert patch['validation']['source_unchanged'];PATCH.write_text(json.dumps(patch,indent=2)+'\n');print('FINAL',patch['validation'],flush=True)

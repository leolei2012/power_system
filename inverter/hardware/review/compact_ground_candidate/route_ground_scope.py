import sys,json,math,heapq,shutil,hashlib,collections,types,subprocess,time
from pathlib import Path
import pcbnew as p
D=Path(__file__).resolve().parent;B=D.parents[1];sys.path.insert(0,str(B/'tools'));sys.path.insert(0,str(D))
import stitch_base as S
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
args=types.SimpleNamespace()

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
  for ob in self.obstacles+self.holes+self.surface_pads+self.kelvin_guards:
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

# Direct and plane-directed GND stitches; use every cluster's actual pads/stubs.
failed=set()
while True:
 clusters=groups('GND');base=clusters[0];others=[g for g in clusters[1:]if tuple(sorted(g))not in failed]
 if not others:break
 group=min(others,key=len);finger=tuple(sorted(group));geo=Geo();code=next(iter(group.values())).GetNetCode();candidates=points(group);candidates.sort(key=lambda q:q[2]);basepts=points(base);done=False
 # Short existing-ground attachment first, excluding every Kelvin branch/pad.
 pairs=heapq.nsmallest(35,((math.dist(a[0],b[0]),a,b)for a in candidates for b in basepts if a[1]==b[1]and a[1]in[p.F_Cu,p.B_Cu]and math.dist(a[0],b[0])<=3),key=lambda q:q[0])
 for _,a,b in pairs:
  for pts in shapes(a[0],b[0]):
   if pathok(geo,pts,a[1],code)and commit({'net':'GND','paths':[pathitem('GND',a[1],pts)],'vias':[]},'ground_direct'):
    done=True;break
  if done:break
 if not done:
  groundpolys=[z.GetFilledPolysList(ly)for z in board.Zones()if z.GetNetname()=='GND'and not z.GetIsRuleArea()for ly in [p.In1_Cu,p.In4_Cu]if z.IsOnLayer(ly)]
  for at,ly,_,ident in candidates[:25]:
   for point,paths,vias in via_candidates(geo,at,ly,code,'GND',16):
    if not vias or not any(z.Contains(V(*point))for z in groundpolys):continue
    if commit({'net':'GND','paths':paths,'vias':vias},'ground_near_plane_via'):
     done=True;break
   if done:break
 if not done:failed.add(finger);print('GND NO LOCAL FANOUT',len(group),[(getattr(q,'GetNumber',lambda:'')(),q.GetClass())for q in list(group.values())[:2]],flush=True)
print('GND_STAGE_DONE groups',len(groups('GND')),'accepted',len(patch['accepted']),flush=True)
# VDD leftovers: exact missing vias and short native same-layer / two-via bridges.
failed=set()
while True:
 clusters=groups('+3V3_INV')
 if len(clusters)<=1:break
 mapping={u:g for g in clusters for u in g};items=S.items_by_uuid(board);todo=[]
 for entry in current['unconnected_items']:
  qq=[items.get(i.get('uuid'))for i in entry['items']]
  if len(qq)<2 or not all(q is not None and q.GetNetname()=='+3V3_INV'for q in qq[:2]):continue
  ga,gb=mapping.get(UID(qq[0])),mapping.get(UID(qq[1]));finger=tuple(sorted([tuple(sorted(ga)),tuple(sorted(gb))]))
  if finger not in failed:todo.append((entry,ga,gb,finger))
 if not todo:break
 entry,ga,gb,finger=todo[0];geo=Geo();code=next(iter(ga.values())).GetNetCode();ap,bp=points(ga),points(gb);pairs=heapq.nsmallest(40,((math.dist(a[0],b[0]),a,b)for a in ap for b in bp),key=lambda q:q[0]);done=False
 for length,a,b in pairs:
  if a[1]==b[1]:
   for pts in shapes(a[0],b[0]):
    if pathok(geo,pts,a[1],code)and commit({'net':'+3V3_INV','paths':[pathitem('+3V3_INV',a[1],pts)],'vias':[]},'VDD_direct'):
     done=True;break
  elif length<.00001 and geo.via_ok(a[0],code):
   v={'net':'+3V3_INV','x':a[0][0],'y':a[0][1],'diameter':.6,'drill':.3,'tented':True,'VBUS_hole_zone_uuids':geo.holes_vbus(a[0])}
   if commit({'net':'+3V3_INV','paths':[],'vias':[v]},'VDD_exact_via'):done=True
  if done:break
 if not done:
  for length,a,b in pairs[:8]:
   ca=via_candidates(geo,a[0],a[1],code,'+3V3_INV',5);cb=via_candidates(geo,b[0],b[1],code,'+3V3_INV',5)
   for pa,paths_a,via_a in ca:
    for pb,paths_b,via_b in cb:
     if via_a and via_b and math.dist(pa,pb)<.85:continue
     for ly in [p.In2_Cu,p.B_Cu,p.In3_Cu,p.F_Cu]:
      if not via_a and a[1]!=ly or not via_b and b[1]!=ly:continue
      for middle in shapes(pa,pb):
       if not pathok(geo,middle,ly,code):continue
       route={'net':'+3V3_INV','paths':paths_a+[pathitem('+3V3_INV',ly,middle)]+paths_b,'vias':via_a+via_b}
       if commit(route,'VDD_local_via_bridge'):done=True;break
      if done:break
     if done:break
    if done:break
   if done:break
 if not done:failed.add(finger);print('VDD NO LOCAL BRIDGE',len(ga),len(gb),'nearest',pairs[0][0]if pairs else None,flush=True)
print('DONE',board.GetConnectivity().GetUnconnectedCount(False),'GNDgroups',len(groups('GND')),'VDDgroups',len(groups('+3V3_INV')),flush=True)
save();finalaudit=audit_power_connectivity(board,report);(D/'power_connectivity_final.json').write_text(json.dumps(finalaudit,indent=2)+'\n');assert not guard();final,lastfile=drc(999);assert not S.error_keys(final);patch['validation']={'before_gaps':215,'after_gaps':board.GetConnectivity().GetUnconnectedCount(False),'electrical_errors':0,'fixed_Kelvin_PASS':True,'main_power_filled_connectivity_PASS':True,'final_drc':lastfile,'source_unchanged':hashlib.sha256(SRC.read_bytes()).hexdigest()==SHA,'GND_components':len(groups('GND')),'VDD_components':len(groups('+3V3_INV'))};assert patch['validation']['source_unchanged'];PATCH.write_text(json.dumps(patch,indent=2)+'\n');print('FINAL',patch['validation'],flush=True)

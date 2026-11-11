"""Conservative, additive signal stitches for an actual KiCad DRC remainder.

Run with KiCad's bundled Python (pcbnew + numpy), for example:
  python compact_stitch_signals.py --board review/compact_work/inverter.kicad_pcb \
    --drc review/compact_work/drc.json --out review/stitch_example.json \
    --net ADC_I_V --max-connections 2

Never writes the input board/project. A sibling <outstem>.work directory owns the
candidate PCB, exact project/rule copies and fresh before/after DRC reports.
Only accepted geometry is exported in the established source_sha/paths/vias
patch format. There is no automatic rip-up, part movement, rule relaxation or
power-net routing. KiCad DRC + zone fill is the final acceptance test.
"""
from __future__ import annotations
import argparse, collections, fnmatch, hashlib, heapq, json, math, re, shutil
import subprocess, sys, time
from pathlib import Path
sys.path.insert(0, 'D:\\workspace\\power_system\\inverter\\hardware\\tools')
import pcbnew as p
import numpy as np

MM=p.FromMM
V=lambda x,y:p.VECTOR2I(MM(float(x)),MM(float(y)))
XY=lambda v:(p.ToMM(v.x),p.ToMM(v.y))
UID=lambda a:a.m_Uuid.AsString()
ALLOWED_NAMES=('F.Cu','In2.Cu','In3.Cu','B.Cu')
PROTECTED=re.compile(r'(^|/)(VBUS|[UVW]_PHASE|BR_SW|DC_FUSED|DC_INPUT_POS|[UVW]_SOURCE|[UVW]_SHUNT_K[PN]|[UVW]_GATE_[HL]|[UVW]_[HL]O|BR_GATE|[UVW]_BOOT|BB_L[12]|AUX_IN|AUX_FUSED|AUX_PROTECTED|\+12V_DRV|\+5V_INV|\+5V_SENSOR)$')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def net_name(a):return a.GetNetname() if hasattr(a,'GetNetname') else ''
def netcode(a):return a.GetNetCode() if hasattr(a,'GetNetCode') else 0
def bbox(shape,extra=0):
 b=shape.BBox();return [p.ToMM(b.GetX())-extra,p.ToMM(b.GetY())-extra,p.ToMM(b.GetRight())+extra,p.ToMM(b.GetBottom())+extra]
def overlap(a,b):return a[0]<=b[2] and a[2]>=b[0] and a[1]<=b[3] and a[3]>=b[1]
def error_keys(report):
 # UUIDs distinguish a newly introduced error even if its count is unchanged.
 return collections.Counter((v.get('type',''),v.get('description',''),tuple(sorted(i.get('uuid','') for i in v.get('items',[])))) for v in report.get('violations',[]) if v.get('severity')=='error')
def unresolved_count(report,net=None,items=None):
 if net is None:return len(report.get('unconnected_items',[]))
 count=0
 for entry in report.get('unconnected_items',[]):
  found={net_name(items[i['uuid']]) for i in entry.get('items',[]) if items and i.get('uuid') in items}
  if net in found or any('['+net+']' in i.get('description','') for i in entry.get('items',[])):count+=1
 return count


class Object:
 def __init__(self,shape,layers,clearance=0,code=-1,kind='copper',uid=''):
  self.shape=shape;self.layers=set(layers);self.clearance=clearance;self.code=code;self.kind=kind;self.uid=uid;self.bb=bbox(shape)
 def hit(self,shape,clearance):
  if not overlap(self.bb,bbox(shape,clearance)):return False
  return self.shape.Collide(shape,MM(clearance))


class Geometry:
 """Real native shapes; no rectangular substitution for pads or power pours."""
 def __init__(self,board,args,project):
  self.board=board;self.args=args
  self.layers=[board.GetLayerID(n) for n in ALLOWED_NAMES if board.GetLayerID(n) in board.GetEnabledLayers().Seq()]
  if not self.layers:raise RuntimeError('No allowed signal layers')
  self.names={board.GetLayerID(n):n for n in ALLOWED_NAMES}
  self.copper=list(board.GetEnabledLayers().CuStack())
  rules=project.get('board',{}).get('design_settings',{}).get('rules',{})
  self.edge_clear=max(.5,rules.get('min_copper_edge_clearance',.5))
  self.hole_clear=max(.25,rules.get('min_hole_clearance',.25))
  self.hole_gap=max(.25,rules.get('min_hole_to_hole',.25))
  self.default_clear=max(.15,rules.get('min_clearance',0))
  self.obstacles=[];self.holes=[];self.surface_pads=[];self.protected=[];self.power_zones=[]
  self.outline=p.SHAPE_POLY_SET()
  if not board.GetBoardPolygonOutlines(self.outline,False):raise RuntimeError('Actual closed Edge.Cuts outline is required')
  self.edge=[]
  for i in range(self.outline.OutlineCount()):
   contours=[self.outline.COutline(i)]+[self.outline.CHole(i,h) for h in range(self.outline.HoleCount(i))]
   for contour in contours:
    pts=[contour.CPoint(j) for j in range(contour.PointCount())]
    self.edge.extend(p.SHAPE_SEGMENT(a,b,0) for a,b in zip(pts,pts[1:]+pts[:1]))
  for f in board.GetFootprints():
   for a in f.Pads():
    layers=[ly for ly in self.copper if a.IsOnLayer(ly)]
    for ly in layers:
     shape=a.GetEffectiveShape(ly)
     cl=max(self.default_clear,p.ToMM(a.GetOwnClearance(ly)))
     ob=Object(shape,[ly],cl,netcode(a),'pad',UID(a));self.obstacles.append(ob)
     if a.GetAttribute()==p.PAD_ATTRIB_SMD:self.surface_pads.append(ob)
    if max(a.GetDrillSize().x,a.GetDrillSize().y)>0:
     self.holes.append(Object(a.GetEffectiveHoleShape(),self.copper,0,netcode(a),'hole',UID(a)))
  for a in board.GetTracks():
   layers=[ly for ly in self.copper if a.IsOnLayer(ly)]
   for ly in layers:
    self.obstacles.append(Object(a.GetEffectiveShape(ly),[ly],max(self.default_clear,p.ToMM(a.GetOwnClearance(ly))),netcode(a),'via' if isinstance(a,p.PCB_VIA) else 'track',UID(a)))
   if isinstance(a,p.PCB_VIA):self.holes.append(Object(a.GetEffectiveHoleShape(),self.copper,0,netcode(a),'hole',UID(a)))
  graphics=list(board.GetDrawings())+[q for f in board.GetFootprints() for q in f.GraphicalItems()]
  for a in graphics:
   if a.GetLayer() in self.copper and hasattr(a,'GetEffectiveShape'):
    self.obstacles.append(Object(a.GetEffectiveShape(a.GetLayer()),[a.GetLayer()],self.default_clear,-1,'drawing',UID(a)))
  for z in board.Zones():
   layers=[ly for ly in self.copper if z.IsOnLayer(ly)]
   if z.GetIsRuleArea():
    if z.GetDoNotAllowTracks():self.obstacles.append(Object(z.Outline(),layers,0,-1,'track_keepout',UID(z)))
    if z.GetDoNotAllowVias():self.protected.append(Object(z.Outline(),self.copper,0,-1,'via_keepout',UID(z)))
   elif PROTECTED.search(net_name(z)):
    # A trace is blocked ONLY on this zone's actual copper layer(s).
    # Do not project an In3 VBUS island into B/In2 trace masks. Through-via
    # checks below still see every layer's full original outline.
    ob=Object(z.Outline(),layers,max(.4,self.default_clear),-1,'protected_power_zone',UID(z))
    self.obstacles.append(ob);self.power_zones.append(ob)

 def inside(self,shape,radius):
  a=shape.GetCenter() if isinstance(shape,p.SHAPE_CIRCLE) else shape.GetStart()
  z=a if isinstance(shape,p.SHAPE_CIRCLE) else shape.GetEnd()
  if not self.outline.Contains(a) or not self.outline.Contains(z):return False
  return not any(e.Collide(shape,MM(self.edge_clear)) for e in self.edge)

 def line_ok(self,a,b,ly,code,width,clear):
  shape=p.SHAPE_SEGMENT(V(*a),V(*b),MM(width))
  if not self.inside(shape,width/2):return False
  for ob in self.obstacles:
   # Layer-local zone obstacle for traces; other layers may cross its XY
   # projection with intervening GND planes, never cut this layer's copper.
   if ly in ob.layers and ob.code!=code and ob.kind!='via_keepout' and ob.hit(shape,max(clear,ob.clearance)):return False
  for h in self.holes:
   if h.code!=code and h.hit(shape,self.hole_clear):return False
  return True

 def via_ok(self,at,code,clear):
  copper=p.SHAPE_CIRCLE(V(*at),MM(.3));drill=p.SHAPE_CIRCLE(V(*at),MM(.15))
  if not self.inside(copper,.3):return False
  for ob in self.obstacles:
   # A through via spans ALL copper layers: no layer filter here.
   if ob.code!=code and ob.kind!='track_keepout' and ob.hit(copper,max(clear,ob.clearance)):return False
  for ob in self.protected:
   if ob.hit(copper,max(clear,ob.clearance)):return False
  # Even same-net surface pads cannot silently become via-in-pad/mask-overlap.
  if any(ob.hit(copper,.05) for ob in self.surface_pads):return False
  if any(h.hit(drill,self.hole_gap) for h in self.holes):return False
  return True

 def masks(self,domain,step,code,width,clear):
  x0,y0,x1,y1=domain;nx=round((x1-x0)/step)+1;ny=round((y1-y0)/step)+1
  blocked=np.zeros((len(self.layers),ny,nx),bool);via=np.zeros((ny,nx),bool)
  # A full half-cell diagonal guard makes line interpolation conservative.
  guard=step/math.sqrt(2)+.005
  def paint(ob,target,radius):
   bb=bbox(ob.shape,radius)
   ax=max(0,math.floor((bb[0]-x0)/step));bx=min(nx-1,math.ceil((bb[2]-x0)/step))
   ay=max(0,math.floor((bb[1]-y0)/step));by=min(ny-1,math.ceil((bb[3]-y0)/step))
   rr=MM(radius)
   for y in range(ay,by+1):
    yy=y0+y*step
    for x in range(ax,bx+1):
     if not target[y,x] and ob.shape.Collide(V(x0+x*step,yy),rr):target[y,x]=True
  for ob in self.obstacles:
   if ob.code==code:continue
   if ob.kind!='via_keepout':
    for i,ly in enumerate(self.layers):
     if ly in ob.layers:paint(ob,blocked[i],width/2+max(clear,ob.clearance)+guard)
   if ob.kind!='track_keepout':paint(ob,via,.3+max(clear,ob.clearance)+guard)
  for ob in self.protected:paint(ob,via,.3+max(clear,ob.clearance)+guard)
  for ob in self.surface_pads:paint(ob,via,.35+guard)
  for h in self.holes:
   paint(h,via,.15+self.hole_gap+guard)
   if h.code!=code:
    for mask in blocked:paint(h,mask,width/2+self.hole_clear+guard)
  # Edge margin is global and checks actual outline, including cutouts.
  for y in range(ny):
   for x in range(nx):
    pt=V(x0+x*step,y0+y*step)
    if not self.outline.Contains(pt):blocked[:,y,x]=True;via[y,x]=True;continue
    if any(e.Collide(pt,MM(self.edge_clear+width/2+guard)) for e in self.edge):blocked[:,y,x]=True
    if any(e.Collide(pt,MM(self.edge_clear+.3+guard)) for e in self.edge):via[y,x]=True
  return blocked,via


def item_points(item,layers,toward):
 if isinstance(item,p.PCB_VIA):return [(XY(item.GetPosition()),ly) for ly in layers if item.IsOnLayer(ly)]
 if isinstance(item,p.PAD):return [(XY(item.GetPosition()),ly) for ly in layers if item.IsOnLayer(ly)]
 if isinstance(item,p.PCB_TRACK):
  ly=item.GetLayer()
  if ly not in layers:return []
  a=np.array(XY(item.GetStart()));b=np.array(XY(item.GetEnd()));length=np.linalg.norm(b-a)
  n=min(40,max(1,math.ceil(length/.8)))
  points=[tuple(a+(b-a)*i/n) for i in range(n+1)]
  if length>0:
   t=float(np.clip(np.dot(np.array(toward)-a,b-a)/length**2,0,1));points.append(tuple(a+t*(b-a)))
  return [(pt,ly) for pt in points]
 return []


def cluster(board,item):
 # Do not use a whole zone as one graph node: distinct filled islands must not
 # collapse into a fictitious single connected cluster.
 result={UID(item):item};todo=[item];cn=board.GetConnectivity();code=netcode(item)
 while todo:
  a=todo.pop()
  for q in cn.GetConnectedItems(a):
   if isinstance(q,p.ZONE) or netcode(q)!=code:continue
   uid=UID(q)
   if uid not in result:result[uid]=q;todo.append(q)
 return list(result.values())


def adapters(points,toward,geometry,blocked,domain,step,code,width,clear,max_bases=32):
 x0,y0,_,_=domain;nl,ny,nx=blocked.shape;out={};seen=set()
 points=sorted(points,key=lambda z:math.dist(z[0],toward))
 for at,ly in points:
  key=(round(at[0],5),round(at[1],5),ly)
  if key in seen:continue
  seen.add(key)
  if len(seen)>max_bases:break
  zi=geometry.layers.index(ly);cx=round((at[0]-x0)/step);cy=round((at[1]-y0)/step)
  radius=math.ceil(2.5/step)
  cells=[(dx*dx+dy*dy,dx,dy) for dx in range(-radius,radius+1) for dy in range(-radius,radius+1) if dx*dx+dy*dy<=radius*radius]
  cells.sort();got=0
  for _,dx,dy in cells:
   x=cx+dx;y=cy+dy
   if x<0 or y<0 or x>=nx or y>=ny or blocked[zi,y,x]:continue
   pt=(x0+x*step,y0+y*step)
   if not geometry.line_ok(at,pt,ly,code,width,clear):continue
   state=(zi,x,y);cost=math.dist(at,pt)/step
   if state not in out or cost<out[state][0]:out[state]=(cost,at)
   got+=1
   if got>=12:break
 return out


def search(board,items,entry,geometry,args):
 aa=[items[i.get('uuid')] for i in entry['items'] if i.get('uuid') in items]
 if len(aa)<2:return None,'DRC endpoints are absent/stale'
 a,b=aa[:2];code=netcode(a);name=net_name(a)
 if code<=0 or netcode(b)!=code:return None,'Endpoints do not identify one actual net'
 if (name=='GND' or PROTECTED.search(name)) and name not in args.allow_protected_net:return None,'Protected power/ground/Kelvin/gate net skipped'
 if isinstance(a,p.ZONE) or isinstance(b,p.ZONE):return None,'Zone-island endpoint requires manual/native connectivity review'
 ca=cluster(board,a);cb=cluster(board,b)
 if set(map(UID,ca))&set(map(UID,cb)):return None,'Already one native same-net copper cluster'
 at=XY(a.GetPosition());bt=XY(b.GetPosition())
 ap=[q for item in ca for q in item_points(item,geometry.layers,bt)]
 bp=[q for item in cb for q in item_points(item,geometry.layers,at)]
 clear=max(args.clearance,geometry.default_clear,max((p.ToMM(q.GetOwnClearance(q.GetLayer())) for q in [a,b] if hasattr(q,'GetOwnClearance')),default=.15))
 # An exact missing via is useful even when the ordinary coarse grid is dense.
 for pa,la in ap:
  for pb,lb in bp:
   if la!=lb and math.dist(pa,pb)<.000001 and geometry.via_ok(pa,code,clear):
    return {'net':name,'paths':[],'vias':[{'net':name,'x':pa[0],'y':pa[1],'diameter':.6,'drill':.3,'tented':True}],'method':'exact_same_xy_via'},None
 if args.via_only:return None,'No geometrically legal exact same-XY via'
 if not ap or not bp:return None,'No endpoints on enabled F/In2/In3/B copper'
 # Full board search is available, but crop to the endpoints plus a generous
 # margin first; a second enlarged domain can be requested with --margin.
 bb=geometry.outline.BBox();boardbox=[p.ToMM(bb.GetX()),p.ToMM(bb.GetY()),p.ToMM(bb.GetRight()),p.ToMM(bb.GetBottom())]
 coords=[z[0] for z in ap+bp];step=args.step
 domain=[max(boardbox[0],math.floor((min(q[0] for q in coords)-args.margin)/step)*step),max(boardbox[1],math.floor((min(q[1] for q in coords)-args.margin)/step)*step),min(boardbox[2],math.ceil((max(q[0] for q in coords)+args.margin)/step)*step),min(boardbox[3],math.ceil((max(q[1] for q in coords)+args.margin)/step)*step)]
 print(' raster',name,domain,'step',step,flush=True);started=time.monotonic()
 blocked,via=geometry.masks(domain,step,code,args.width,clear)
 starts=adapters(ap,bt,geometry,blocked,domain,step,code,args.width,clear)
 goals=adapters(bp,at,geometry,blocked,domain,step,code,args.width,clear)
 if not starts or not goals:return None,'No legal pad/cluster-to-grid fanout; try --step .05 or larger --margin'
 nl,ny,nx=blocked.shape;yy,xx=np.ogrid[:ny,:nx];heur=np.full((ny,nx),np.inf)
 for _,x,y in goals:np.minimum(heur,np.hypot(xx-x,yy-y),out=heur)
 dist=np.full(blocked.shape,np.inf);parent={};queue=[]
 for (z,x,y),(cost,_) in starts.items():dist[z,y,x]=cost;heapq.heappush(queue,(cost+heur[y,x],cost,z,x,y))
 end=None;expanded=0;deadline=time.monotonic()+args.seconds_per_gap
 while queue and expanded<args.max_nodes and time.monotonic()<deadline:
  _,g,z,x,y=heapq.heappop(queue)
  if g>dist[z,y,x]+1e-9:continue
  expanded+=1;state=(z,x,y)
  if state in goals:end=state;break
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   u=x+dx;v=y+dy
   if u<0 or v<0 or u>=nx or v>=ny or blocked[z,v,u]:continue
   if dx and dy and (blocked[z,y,u] or blocked[z,v,x]):continue
   gg=g+(math.sqrt(2) if dx and dy else 1)
   if gg<dist[z,v,u]:dist[z,v,u]=gg;parent[(z,u,v)]=state;heapq.heappush(queue,(gg+heur[v,u],gg,z,u,v))
  if not via[y,x]:
   for zz in range(nl):
    if zz==z or blocked[zz,y,x]:continue
    gg=g+args.via_cost/step
    if gg<dist[zz,y,x]:dist[zz,y,x]=gg;parent[(zz,x,y)]=state;heapq.heappush(queue,(gg+heur[y,x],gg,zz,x,y))
 if end is None:return None,'No path within conservative grid/node/time budget (%d nodes)'%expanded
 states=[end]
 while states[-1] in parent:states.append(parent[states[-1]])
 states.reverse();x0,y0,_,_=domain
 def point(state):return [round(x0+state[1]*step,7),round(y0+state[2]*step,7)]
 chunks=[];vias=[];pts=[list(starts[states[0]][1]),point(states[0])];lay=states[0][0]
 for prev,state in zip(states,states[1:]):
  pt=point(state)
  if state[0]!=lay:
   chunks.append((lay,pts));pts=[pt];lay=state[0]
   vias.append({'net':name,'x':pt[0],'y':pt[1],'diameter':.6,'drill':.3,'tented':True})
  else:pts.append(pt)
 pts.append(list(goals[end][1]));chunks.append((lay,pts));paths=[]
 for zi,pts in chunks:
  clean=[]
  for pt in pts:
   if not clean or math.dist(pt,clean[-1])>.000001:clean.append(pt)
  reduced=[]
  for pt in clean:
   while len(reduced)>1:
    a0,a1=reduced[-2:];cross=(a1[0]-a0[0])*(pt[1]-a1[1])-(a1[1]-a0[1])*(pt[0]-a1[0])
    if abs(cross)>.0000001:break
    reduced.pop()
   reduced.append(pt)
  if len(reduced)>1:paths.append({'net':name,'layer':geometry.names[geometry.layers[zi]],'width':args.width,'points':reduced,'locked':False})
 # Native continuous-segment validation also covers both non-grid adapters.
 for path in paths:
  ly=board.GetLayerID(path['layer'])
  if any(not geometry.line_ok(u,v,ly,code,args.width,clear) for u,v in zip(path['points'],path['points'][1:])):return None,'Native final segment clearance failed; no geometry emitted'
 if any(not geometry.via_ok([q['x'],q['y']],code,clear) for q in vias):return None,'Native final through-via clearance/hole check failed'
 return {'net':name,'paths':paths,'vias':vias,'method':'multisource_multilayer_astar','search':{'grid_mm':step,'expanded':expanded,'seconds':round(time.monotonic()-started,3),'start_candidates':len(starts),'goal_candidates':len(goals)}},None


def add(board,route):
 nets={q.GetNetname():q for q in board.GetNetsByNetcode().values()}
 for w in route['paths']:
  assert w['layer'] in ALLOWED_NAMES
  for a,b in zip(w['points'],w['points'][1:]):
   t=p.PCB_TRACK(board);t.SetStart(V(*a));t.SetEnd(V(*b));t.SetWidth(MM(w['width']));t.SetLayer(board.GetLayerID(w['layer']));t.SetNet(nets[w['net']]);board.Add(t)
 for w in route['vias']:
  v=p.PCB_VIA(board);v.SetPosition(V(w['x'],w['y']));v.SetWidth(MM(.6));v.SetDrill(MM(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(nets[w['net']]);v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED);board.Add(v)


def original_geometry(board):
 signature={}
 for a in board.GetTracks():
  signature[UID(a)]=('via' if isinstance(a,p.PCB_VIA) else 'track',netcode(a),a.GetLayer(),tuple(XY(a.GetStart())),tuple(XY(a.GetEnd())),(a.GetWidth(p.F_Cu) if isinstance(a,p.PCB_VIA) else a.GetWidth()),a.IsLocked(),a.GetDrill() if isinstance(a,p.PCB_VIA) else 0)
 for f in board.GetFootprints():
  signature[UID(f)]=('footprint',f.GetReference(),tuple(XY(f.GetPosition())),f.GetOrientationDegrees(),f.IsFlipped(),f.IsLocked())
  for a in f.Pads():signature[UID(a)]=('pad',netcode(a),tuple(XY(a.GetPosition())),a.GetNumber())
 return signature


def native_components(board):
 board.BuildConnectivity();cn=board.GetConnectivity();groups=collections.defaultdict(dict)
 for a in list(board.GetTracks())+[q for f in board.GetFootprints() for q in f.Pads()]:
  if netcode(a)>0:groups[net_name(a)][UID(a)]=a
 result={}
 for name,remaining in groups.items():
  count=0
  while remaining:
   _,a=remaining.popitem();count+=1
   for q in cn.GetConnectedItems(a):
    if not isinstance(q,p.ZONE):remaining.pop(UID(q),None)
  result[name]=count
 return result


def items_by_uuid(board):
 return {UID(q):q for q in list(board.GetTracks())+list(board.Zones())+[a for f in board.GetFootprints() for a in f.Pads()]}



def quick_search(board,items,entry,geometry,args):
 aa=[items[i.get('uuid')] for i in entry['items'] if i.get('uuid') in items]
 if len(aa)<2:return None,'stale endpoints'
 a,b=aa[:2];code=netcode(a);name=net_name(a)
 if code<=0 or netcode(b)!=code:return None,'different net'
 if (name=='GND' or PROTECTED.search(name)) and name not in args.allow_protected_net:return None,'protected net'
 if isinstance(a,p.ZONE) or isinstance(b,p.ZONE):return None,'zone endpoint requires manual review'
 ca=cluster(board,a);cb=cluster(board,b)
 if set(map(UID,ca))&set(map(UID,cb)):return None,'already connected'
 at=XY(a.GetPosition());bt=XY(b.GetPosition())
 def unique(points,toward):
  out=[];seen=set()
  for q,ly in sorted(points,key=lambda z:math.dist(z[0],toward)):
   key=(round(q[0],6),round(q[1],6),ly)
   if key not in seen:out.append((q,ly));seen.add(key)
   if len(out)>=20:break
  return out
 ap=unique([q for item in ca for q in item_points(item,geometry.layers,bt)],bt)
 bp=unique([q for item in cb for q in item_points(item,geometry.layers,at)],at)
 clear=max(args.clearance,geometry.default_clear,max((p.ToMM(q.GetOwnClearance(q.GetLayer())) for q in [a,b] if hasattr(q,'GetOwnClearance')),default=.15))
 def polylines(a,b):
  dx=b[0]-a[0];dy=b[1]-a[1];sx=1 if dx>=0 else -1;sy=1 if dy>=0 else -1;k=min(abs(dx),abs(dy))
  candidates=[]
  if min(abs(dx),abs(dy))<1e-6 or abs(abs(dx)-abs(dy))<1e-6 or math.dist(a,b)<.6:candidates.append([a,b])
  candidates += [[a,(a[0]+sx*k,a[1]+sy*k),b],[a,(b[0]-sx*k,b[1]-sy*k),b],[a,(b[0],a[1]),b],[a,(a[0],b[1]),b]]
  seen=set()
  for qs in candidates:
   pts=[]
   for q in qs:
    q=(round(q[0],6),round(q[1],6))
    if not pts or math.dist(q,pts[-1])>1e-6:pts.append(q)
   key=tuple(pts)
   if len(pts)>1 and key not in seen:seen.add(key);yield pts
 def route(a,b,ly):
  if math.dist(a,b)<1e-6:return []
  for pts in polylines(a,b):
   if all(geometry.line_ok(u,v,ly,code,args.width,clear) for u,v in zip(pts,pts[1:])):return [{'net':name,'layer':geometry.names[ly],'width':args.width,'points':pts,'locked':False}]
  return None
 def result(paths,vs,method):return {'net':name,'paths':paths,'vias':[{'net':name,'x':q[0],'y':q[1],'diameter':.6,'drill':.3,'tented':True} for q in vs],'method':method},None
 pairs=sorted([(math.dist(x,y),x,lx,y,ly) for x,lx in ap for y,ly in bp])
 for _,x,lx,y,ly in pairs[:96]:
  if lx==ly:
   rr=route(x,y,lx)
   if rr is not None:return result(rr,[],'native_exact_octilinear')
 def via_candidates(x,y):
  toward=(math.atan2(y[1]-x[1],y[0]-x[0]))
  out=[]
  for r in [.65,.85,1.15,1.6]:
   for delta in [0,math.pi/4,-math.pi/4,math.pi/2,-math.pi/2,math.pi,3*math.pi/4,-3*math.pi/4]:
    ang=toward+delta;q=(round(x[0]+r*math.cos(ang),3),round(x[1]+r*math.sin(ang),3))
    if geometry.via_ok(q,code,clear):out.append(q)
    if len(out)>=10:return out
  return out
 # THT/via source clusters already expose all signal layers; one local via
 # at the far end often avoids a full-board grid and preserves exact fanout.
 for _,x,lx,y,ly in pairs[:28]:
  if lx==ly:continue
  vv=via_candidates(y,x)+via_candidates(x,y)
  for q in vv[:16]:
   p1=route(x,q,lx)
   if p1 is None:continue
   p2=route(q,y,ly)
   if p2 is not None:return result(p1+p2,[q],'native_octilinear_one_via')
 # Two reviewed through-vias plus one clear signal-layer corridor.
 for _,x,lx,y,ly in pairs[:8]:
  va=via_candidates(x,y)[:4];vb=via_candidates(y,x)[:4]
  starts=[(q,rr) for q in va if (rr:=route(x,q,lx)) is not None]
  ends=[(q,rr) for q in vb if (rr:=route(q,y,ly)) is not None]
  for q1,p1 in starts:
   for q2,p2 in ends:
    for mid in geometry.layers:
     rr=route(q1,q2,mid)
     if rr is not None:return result(p1+rr+p2,[q1,q2],'native_octilinear_two_vias')
 return None,'No legal native exact octilinear/one-via/two-via candidate'


def main():
 parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 parser.add_argument('--board',required=True,type=Path);parser.add_argument('--drc',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
 parser.add_argument('--net',action='append',default=[],help='Repeatable exact net name or shell glob; default all ordinary DRC signal nets')
 parser.add_argument('--power-report',type=Path,help='Authoritative fixed-copper/Kelvin report; verify before routing and after every candidate fill.')
 parser.add_argument('--allow-protected-net',action='append',default=[],help='Explicit exact net for reviewed auxiliary/gate/sense attachment only; requires fixed power report.')
 parser.add_argument('--clearance',type=float,default=0,help='Additional minimum for a scoped netclass (mm); native DRC still governs.')
 parser.add_argument('--via-only',action='store_true');parser.add_argument('--max-connections',type=int,default=4)
 parser.add_argument('--width',type=float,choices=[.15,.2,.4,.6],default=.15);parser.add_argument('--step',type=float,default=.15)
 parser.add_argument('--margin',type=float,default=8);parser.add_argument('--via-cost',type=float,default=2.5)
 parser.add_argument('--max-nodes',type=int,default=700000);parser.add_argument('--seconds-per-gap',type=float,default=30)
 parser.add_argument('--cli',type=Path,default=Path(p.__file__).resolve().parent/'kicad-cli.exe')
 args=parser.parse_args();args.board=args.board.resolve();args.drc=args.drc.resolve();args.out=args.out.resolve()
 if args.allow_protected_net and not args.power_report:parser.error('--allow-protected-net requires --power-report and fixed-copper verification')
 if args.step<.025 or args.step>.5:parser.error('--step must be .025..0.5mm; .05 is useful for dense fanout')
 if not args.cli.exists():
  fallback=Path(sys.executable).parent/'kicad-cli.exe'
  if fallback.exists():args.cli=fallback
  else:parser.error('kicad-cli is required; pass --cli')
 source_sha=sha(args.board);project_source=args.board.with_suffix('.kicad_pro')
 if not project_source.exists():raise RuntimeError('Exact same-name source .kicad_pro is required')
 project_bytes=project_source.read_bytes();project=json.loads(project_bytes)
 rules=project.get('board',{}).get('design_settings',{}).get('rules',{})
 if args.width<rules.get('min_track_width',.15) or .6<rules.get('min_via_diameter',.5) or .3<rules.get('min_through_hole_diameter',.3):raise RuntimeError('Requested geometry violates existing project minima; rules will not be lowered')
 requested=json.loads(args.drc.read_text(encoding='utf-8'))
 fixed_report=json.loads(args.power_report.read_text(encoding='utf-8')) if args.power_report else None
 def fixed_guard(board):
  if fixed_report is None:return []
  from compact_verify_fixed import verify_geometry,kelvin_check
  objects,geometry_issues,_=verify_geometry(board,fixed_report)
  topology_issues,_,_,_=kelvin_check(board,fixed_report,objects)
  return geometry_issues+topology_issues
 work=args.out.parent/(args.out.stem+'.work');work.mkdir(parents=True,exist_ok=True)
 candidate=work/args.board.name
 if candidate.resolve()==args.board:raise RuntimeError('Private candidate path equals source')
 shutil.copy2(args.board,candidate);pro=candidate.with_suffix('.kicad_pro');pro.write_bytes(project_bytes)
 for suffix in ['.kicad_dru']:
  src=args.board.with_suffix(suffix)
  if src.exists():shutil.copy2(src,candidate.with_suffix(suffix))
 for table in ['fp-lib-table','sym-lib-table']:
  src=args.board.parent/table
  if src.exists():(work/table).write_text(src.read_text(encoding='utf-8').replace('${KIPRJMOD}',args.board.parent.as_posix()),encoding='utf-8')
 def save(board):
  board.BuildConnectivity();p.ZONE_FILLER(board).Fill(board.Zones());board.BuildConnectivity();p.SaveBoard(str(candidate),board);pro.write_bytes(project_bytes)
 def drc(index):
  report=work/('drc_%03d.json'%index)
  completed=subprocess.run([str(args.cli),'pcb','drc','--format','json','--all-track-errors','--severity-all','--output',str(report),str(candidate)],capture_output=True,text=True,timeout=180)
  if completed.returncode or not report.exists():raise RuntimeError('KiCad DRC failed: '+completed.stderr+completed.stdout)
  return json.loads(report.read_text(encoding='utf-8')),str(report)
 board=p.LoadBoard(str(candidate));immutable=original_geometry(board);save(board);current,current_path=drc(0);baseline=current
 baseline_native=board.GetConnectivity().GetUnconnectedCount(False)
 initial_fixed_issues=fixed_guard(board)
 if initial_fixed_issues:raise RuntimeError('Source fails authoritative fixed-copper/Kelvin verification: '+json.dumps(initial_fixed_issues[:5],ensure_ascii=False))
 requested_nets=set()
 initial_items=items_by_uuid(board)
 requested_uuids={q.get('uuid') for entry in requested.get('unconnected_items',[]) for q in entry.get('items',[])}
 resolved_uuids=requested_uuids&set(initial_items)
 if requested_uuids and not resolved_uuids:raise RuntimeError('Supplied DRC UUIDs do not belong to this board; regenerate the scope DRC for the current revision')
 for entry in requested.get('unconnected_items',[]):
  for q in entry.get('items',[]):
   if q.get('uuid') in initial_items:requested_nets.add(net_name(initial_items[q['uuid']]))
 if args.net:requested_nets={n for n in requested_nets if any(fnmatch.fnmatchcase(n,pat) for pat in args.net)}
 if args.net and not requested_nets:print('WARNING: net filters match no valid endpoint in the supplied scope DRC (a large DRC list can be capped)',flush=True)
 patch={'source_sha':source_sha,'ripup_uuids':[],'paths':[],'vias':[],'placements':{},'candidate':str(candidate),'accepted':[],'unresolved':[],'validation':{'source_drc_endpoint_uuids':len(requested_uuids),'resolved_source_drc_endpoint_uuids':len(resolved_uuids),'source_drc_sha':sha(args.drc),'source_project_sha':sha(project_source),'source_drc':str(args.drc),'before_actual_drc':current_path,'allowed_signal_layers':ALLOWED_NAMES,'fixed_power_report_sha':sha(args.power_report) if args.power_report else None,'protected_zone_policy':'Traces block full PHASE/BR_SW/VBUS outline only on the zone actual copper layer(s); an In3 outline is not projected onto B/In2. Through-vias check full outlines across ALL copper layers. In1/In4 never receive signal tracks. Locked original items are never changed.','invariants':'No ripup, no net changes, no placement changes, no rule changes. Native pad/track shapes, all-layer via copper, hole spacing, mask/via-in-pad guard; actual zone fill + no new KiCad errors + strict target-net native component/global-unconnected improvement and no other-net native component regression required. DRC airwire lists can be capped; native counts govern connectivity.'}}
 attempts=0;attempted=set()
 while len(patch['accepted'])<args.max_connections:
  board.BuildConnectivity();items=items_by_uuid(board);chosen=None
  for entry in current.get('unconnected_items',[]):
   names={net_name(items[q['uuid']]) for q in entry.get('items',[]) if q.get('uuid') in items}
   key=tuple(sorted(q.get('uuid','') for q in entry.get('items',[])))
   if names&requested_nets and key not in attempted:chosen=(entry,key);break
  if chosen is None:break
  entry,key=chosen;attempted.add(key);attempts+=1
  geometry=Geometry(board,args,project)
  route,reason=quick_search(board,items,entry,geometry,args)
  if route is None:patch['unresolved'].append({'items':key,'reason':reason});print(' skip',reason,flush=True);continue
  (work/('proposal_%03d.json'%attempts)).write_text(json.dumps(route,indent=2)+'\n',encoding='utf-8')
  before=candidate.read_bytes();before_errors=error_keys(current);name=route['net'];before_components=native_components(board);before_net=before_components.get(name,0);before_total=board.GetConnectivity().GetUnconnectedCount(False)
  add(board,route);save(board);after,after_path=drc(attempts)
  extra=error_keys(after)-before_errors
  after_components=native_components(board);after_net=after_components.get(name,0);after_total=board.GetConnectivity().GetUnconnectedCount(False)
  regressions={n:[before_components.get(n,0),v] for n,v in after_components.items() if n!=name and v>before_components.get(n,0)}
  fixed_issues=fixed_guard(board)
  if extra or fixed_issues or regressions or after_net>=before_net or after_total>=before_total:
   candidate.write_bytes(before);pro.write_bytes(project_bytes);board=p.LoadBoard(str(candidate))
   patch['unresolved'].append({'net':name,'items':key,'reason':'Actual filled-board DRC rejected candidate','new_error_count':sum(extra.values()),'fixed_copper_Kelvin_issues':fixed_issues,'native_other_net_component_regressions':regressions,'before_net_components':before_net,'after_net_components':after_net,'before_total_gaps':before_total,'after_total_gaps':after_total,'drc':after_path})
   print(' rejected',name,'new errors',sum(extra.values()),'gaps',before_total,'->',after_total,flush=True);continue
  patch['paths'].extend(route['paths']);patch['vias'].extend(route['vias']);patch['accepted'].append({k:v for k,v in route.items() if k not in ('paths','vias')}|{'before_net_components':before_net,'after_net_components':after_net,'drc':after_path})
  current=after;current_path=after_path;print(' accepted',name,'gaps',before_total,'->',after_total,flush=True)
  args.out.write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 final_signature=original_geometry(board)
 original_changes=[uid for uid,value in immutable.items() if final_signature.get(uid)!=value]
 assert not original_changes,('Original geometry changed unexpectedly',original_changes)
 patch['validation']['original_geometry_changes']=original_changes
 patch['validation'].update(before_unconnected=baseline_native,after_unconnected=board.GetConnectivity().GetUnconnectedCount(False),before_drc_listed_unconnected=unresolved_count(baseline),after_drc_listed_unconnected=unresolved_count(current),drc_airwire_list_may_be_truncated=unresolved_count(baseline)!=baseline_native,after_actual_drc=current_path,new_error_count=sum((error_keys(current)-error_keys(baseline)).values()),actual_remaining_error_count=sum(error_keys(current).values()),source_unchanged=sha(args.board)==source_sha,source_project_unchanged=project_source.read_bytes()==project_bytes)
 assert patch['validation']['source_unchanged'] and patch['validation']['source_project_unchanged']
 args.out.write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Patch:',args.out,'accepted',len(patch['accepted']),'paths',len(patch['paths']),'vias',len(patch['vias']),'source unchanged',True)
 return 0

if __name__=='__main__':raise SystemExit(main())


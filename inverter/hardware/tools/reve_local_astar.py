"""Local actual-shape A*; copied as authoring helper, no board mutation."""
import pcbnew as p,heapq,math,time,json,fnmatch
from pathlib import Path

def route(board,net,layer_name,width,start,goal,margin=5,limit=15,step=.25,ignore_uuids=(),protected_uuids=()):
 U=p.FromMM(1); layer=board.GetLayerID(layer_name); proj=json.loads(Path('D:/workspace/power_system/inverter/hardware/inverter.kicad_pro').read_text(encoding='utf-8'));ns=proj['net_settings'];classes={c['name']:c['clearance'] for c in ns['classes']}
 def clearance(n):return next((classes[c['netclass']] for c in ns['netclass_patterns'] if fnmatch.fnmatchcase(n,c['pattern'])),classes['Default'])
 own_clear=clearance(net); fixed=[];cells={};cell=2.; skip=set(ignore_uuids);protected=set(protected_uuids)
 objects=[q for fp in board.GetFootprints() for q in fp.Pads()]+list(board.GetTracks())
 for o in objects:
  oid=o.m_Uuid.AsString()
  if oid in skip or (str(o.GetNetname())==net and oid not in protected) or not o.IsOnLayer(layer):continue
  cl=max(own_clear,clearance(str(o.GetNetname())),p.ToMM(o.GetOwnClearance(layer)),.25 if oid in protected else 0);bb=o.GetBoundingBox();v=(bb.GetX()/U,bb.GetY()/U,(bb.GetX()+bb.GetWidth())/U,(bb.GetY()+bb.GetHeight())/U);inflate=width/2+cl
  ix=len(fixed);fixed.append((o.GetEffectiveShape(layer),p.FromMM(cl),v))
  for x in range(math.floor((v[0]-inflate)/cell),math.floor((v[2]+inflate)/cell)+1):
   for y in range(math.floor((v[1]-inflate)/cell),math.floor((v[3]+inflate)/cell)+1):cells.setdefault((x,y),set()).add(ix)
 def free(a,b):
  candidates=set()
  for x in range(math.floor(min(a[0],b[0])/cell),math.floor(max(a[0],b[0])/cell)+1):
   for y in range(math.floor(min(a[1],b[1])/cell),math.floor(max(a[1],b[1])/cell)+1):candidates.update(cells.get((x,y),()))
  if not candidates:return True
  s=p.SHAPE_SEGMENT(p.VECTOR2I(p.FromMM(a[0]),p.FromMM(a[1])),p.VECTOR2I(p.FromMM(b[0]),p.FromMM(b[1])),p.FromMM(width))
  return not any(shape.Collide(s,cl) for shape,cl,_ in (fixed[i] for i in candidates))
 start=tuple(start);goal=tuple(goal);S=(round(start[0]/step),round(start[1]/step));T=(round(goal[0]/step),round(goal[1]/step));xy=lambda t:(t[0]*step,t[1]*step)
 if free(start,goal):return [start,goal],{'direct_shape_checked':True,'minimum_clearance':own_clear}
 def escape(point,node):
  choices=sorted([(node[0]+dx,node[1]+dy) for dx in [-1,0,1] for dy in [-1,0,1]],key=lambda q:math.dist(point,xy(q)))
  return next((q for q in choices if free(point,xy(q))),None)
 S=escape(start,S);T=escape(goal,T)
 if S is None or T is None:return None,{'reason':'endpoint clearance blocked'}
 x0=math.floor((min(start[0],goal[0])-margin)/step);x1=math.ceil((max(start[0],goal[0])+margin)/step);y0=math.floor((min(start[1],goal[1])-margin)/step);y1=math.ceil((max(start[1],goal[1])+margin)/step)
 queue=[(math.dist(S,T),0,S)];best={S:0};prev={};closed=set();st=time.monotonic(); edges={};visited=0
 while queue and time.monotonic()-st<limit:
  _,cost,a=heapq.heappop(queue)
  if a in closed:continue
  closed.add(a);visited+=1
  if a==T:
   pts=[T]
   while pts[-1]!=S:pts.append(prev[pts[-1]])
   pts=[start]+[xy(v) for v in reversed(pts)]+[goal];pts=[v for i,v in enumerate(pts) if not i or v!=pts[i-1]]
   out=[pts[0]];i=0
   while i<len(pts)-1:
    j=len(pts)-1
    while j>i+1 and not free(pts[i],pts[j]):j-=1
    out.append(pts[j]);i=j
   return out,{'visited':visited,'elapsed':time.monotonic()-st,'fixed_other_net_objects':len(fixed),'minimum_clearance':own_clear,'step':step}
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   b=(a[0]+dx,a[1]+dy)
   if b in closed or not(x0<=b[0]<=x1 and y0<=b[1]<=y1):continue
   new=cost+math.hypot(dx,dy)
   if new>=best.get(b,float('inf')):continue
   key=tuple(sorted((a,b)))
   if key not in edges:edges[key]=free(xy(a),xy(b))
   if not edges[key]:continue
   best[b]=new;prev[b]=a;heapq.heappush(queue,(new+math.dist(b,T),new,b))
 return None,{'reason':'no route within search limit','visited':visited,'elapsed':time.monotonic()-st}


from pathlib import Path
import json,math,heapq,time
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent;d=json.loads((R/'pcb_whin_long_obstacles.json').read_text(encoding='utf-8'))
step=.15;x0=123;y0=47;x1=169;y1=86;nx=int((x1-x0)/step)+1;ny=int((y1-y0)/step)+1
imgs=[Image.new('1',(nx,ny),0) for _ in range(3)];vi=Image.new('1',(nx,ny),0)
draw=[ImageDraw.Draw(a) for a in imgs];vd=ImageDraw.Draw(vi)
def cell(p):return ((p[0]-x0)/step,(p[1]-y0)/step)
def paint(dr,o,extra):
 z=(o['clear']+extra+.035)/step
 if o['kind']=='rect':
  a,b,c,e=o['box'];dr.rectangle([(a-x0)/step-z,(b-y0)/step-z,(c-x0)/step+z,(e-y0)/step+z],fill=1)
 elif o['kind']=='circle':
  x,y=cell(o['at']);r=o['radius']/step+z;dr.ellipse([x-r,y-r,x+r,y+r],fill=1)
 else:
  a=cell(o['a']);b=cell(o['b']);r=o['radius']/step+z;dr.line([a,b],fill=1,width=math.ceil(2*r))
  for x,y in [a,b]:dr.ellipse([x-r,y-r,x+r,y+r],fill=1)
for o in d['objects']:
 for lay in o['layers']:paint(draw[lay],o,.1)
 paint(vd,o,.3)
blocked=np.array([np.asarray(a,dtype=bool) for a in imgs]);via=np.asarray(vi,dtype=bool)
xy=lambda p:(round((p[0]-x0)/step),round((p[1]-y0)/step))
start=xy(d['start']);goal=xy(d['goal']);dist=np.full((3,ny,nx),np.inf);prev={};q=[]
heur=lambda x,y:math.hypot(x-goal[0],y-goal[1])
for z in range(3):
 if not blocked[z,start[1],start[0]]:dist[z,start[1],start[0]]=0;heapq.heappush(q,(heur(*start),0,z,start[0],start[1]))
print('domain',nx,ny,'initial',len(q),flush=True);t0=time.monotonic();end=None;n=0
while q:
 f,g,z,x,y=heapq.heappop(q)
 if g>dist[z,y,x]+1e-8:continue
 n+=1
 if (x,y)==goal:end=(z,x,y);break
 for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
  xx=x+dx;yy=y+dy
  if xx<0 or yy<0 or xx>=nx or yy>=ny or blocked[z,yy,xx]:continue
  if dx and dy and (blocked[z,y,xx] or blocked[z,yy,x]):continue
  gg=g+(1.41421356237 if dx and dy else 1)
  if gg+1e-8<dist[z,yy,xx]:dist[z,yy,xx]=gg;prev[(z,xx,yy)]=(z,x,y);heapq.heappush(q,(gg+heur(xx,yy),gg,z,xx,yy))
 if not via[y,x]:
  for zz in range(3):
   if zz==z or blocked[zz,y,x]:continue
   gg=g+25
   if gg+1e-8<dist[zz,y,x]:dist[zz,y,x]=gg;prev[(zz,x,y)]=(z,x,y);heapq.heappush(q,(gg+heur(x,y),gg,zz,x,y))
print('expanded',n,'seconds',time.monotonic()-t0,'end',end,flush=True)
assert end,'No route in conservative grid'
nodes=[end]
while nodes[-1] in prev:nodes.append(prev[nodes[-1]])
nodes.reverse();chunks=[];vias=[];cur=[];lay=nodes[0][0]
for k,(z,x,y) in enumerate(nodes):
 pt=[round(x0+x*step,5),round(y0+y*step,5)]
 if z!=lay:
  chunks.append((lay,cur));cur=[pt];lay=z;vias.append({'net':'W_HIN','x':pt[0],'y':pt[1],'diameter':.6,'drill':.3,'tented':True})
 else:cur.append(pt)
chunks.append((lay,cur));paths=[]
for i,(z,pts) in enumerate(chunks):
 out=[pts[0]]
 for a,b,c in zip(pts,pts[1:],pts[2:]):
  u=(round(b[0]-a[0],5),round(b[1]-a[1],5));v=(round(c[0]-b[0],5),round(c[1]-b[1],5))
  if u!=v:out.append(b)
 out.append(pts[-1])
 if i==0:out.insert(0,d['start'])
 if i==len(chunks)-1:out.append(d['goal'])
 paths.append({'net':'W_HIN','layer':['F.Cu','In2.Cu','B.Cu'][z],'width':.2,'points':out,'locked':False})
patch={'source_sha':d['source_sha'],'ripup_uuids':d['ripup_uuids'],'paths':paths,'vias':vias,'placements':{},'validation_dependencies':d['dependencies'],'search':{'step':step,'expanded':n,'seconds':time.monotonic()-t0}}
(R/'pcb_whin_long_geometry.json').write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8');print('result paths',len(paths),'vias',len(vias),flush=True)

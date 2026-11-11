"""Same native-DRC-validated stitcher with vectorized polygon/board masks.

Only grid painting changes. Actual native shape, line, via, fixed-copper and
filled-zone DRC acceptance checks remain in compact_stitch_signals.
"""
import math
import time
import numpy as np
import pcbnew as p
import compact_stitch_signals as s

def polygon_mask(shape,xx,yy,radius):
    result=np.zeros(np.broadcast_shapes(xx.shape,yy.shape),bool)
    boundary=np.zeros_like(result)
    for i in range(shape.OutlineCount()):
        value=None
        for contour in [shape.COutline(i)]+[shape.CHole(i,h) for h in range(shape.HoleCount(i))]:
            pts=[(p.ToMM(contour.CPoint(k).x),p.ToMM(contour.CPoint(k).y)) for k in range(contour.PointCount())]
            inside=np.zeros_like(result)
            for (ax,ay),(bx,by) in zip(pts,pts[1:]+pts[:1]):
                if by!=ay:inside^=((ay>yy)!=(by>yy))&(xx<(bx-ax)*(yy-ay)/(by-ay)+ax)
                vx=bx-ax;vy=by-ay;den=vx*vx+vy*vy
                if den:
                    u=np.clip(((xx-ax)*vx+(yy-ay)*vy)/den,0,1)
                    boundary|=(xx-(ax+u*vx))**2+(yy-(ay+u*vy))**2<=radius*radius
            value=inside if value is None else value&~inside
        if value is not None:result|=value
    return result|boundary

def shape_mask(shape,xx,yy,radius):
    kind=shape.Type();radius+=.000002
    if kind==p.SH_SEGMENT:
        seg=p.Cast_to_SHAPE_SEGMENT(shape);a=seg.GetStart();b=seg.GetEnd()
        ax=p.ToMM(a.x);ay=p.ToMM(a.y);vx=p.ToMM(b.x-a.x);vy=p.ToMM(b.y-a.y);den=vx*vx+vy*vy
        u=np.clip(((xx-ax)*vx+(yy-ay)*vy)/den,0,1) if den else 0
        return (xx-(ax+u*vx))**2+(yy-(ay+u*vy))**2<=(radius+p.ToMM(seg.GetWidth())/2)**2
    if kind==p.SH_CIRCLE:
        circle=p.Cast_to_SHAPE_CIRCLE(shape);at=circle.GetCenter()
        return (xx-p.ToMM(at.x))**2+(yy-p.ToMM(at.y))**2<=(radius+p.ToMM(circle.GetRadius()))**2
    if kind==p.SH_RECT:
        bb=s.bbox(shape);dx=np.maximum(np.maximum(bb[0]-xx,xx-bb[2]),0);dy=np.maximum(np.maximum(bb[1]-yy,yy-bb[3]),0)
        return dx*dx+dy*dy<=radius*radius
    if kind==p.SH_POLY_SET:return polygon_mask(p.Cast_to_SHAPE_POLY_SET(shape),xx,yy,radius)
    if kind==p.SH_COMPOUND:
        value=np.zeros(np.broadcast_shapes(xx.shape,yy.shape),bool)
        for sub in p.Cast_to_SHAPE_COMPOUND(shape).GetSubshapes():value|=shape_mask(sub,xx,yy,radius)
        return value
    return None

def masks(self,domain,step,code,width,clear):
    started=time.monotonic()
    x0,y0,x1,y1=domain;nx=round((x1-x0)/step)+1;ny=round((y1-y0)/step)+1
    blocked=np.zeros((len(self.layers),ny,nx),bool);via=np.zeros((ny,nx),bool)
    guard=getattr(self,'mask_guard_mm',.005) # Sampling only; native continuous shape/DRC acceptance still governs.
    def paint(ob,target,radius):
        bb=s.bbox(ob.shape,radius)
        ax=max(0,math.floor((bb[0]-x0)/step));bx=min(nx-1,math.ceil((bb[2]-x0)/step))
        ay=max(0,math.floor((bb[1]-y0)/step));by=min(ny-1,math.ceil((bb[3]-y0)/step))
        if ax>bx or ay>by:return
        xx=x0+np.arange(ax,bx+1)[None,:]*step;yy=y0+np.arange(ay,by+1)[:,None]*step
        painted=shape_mask(ob.shape,xx,yy,radius)
        if painted is not None:
            target[ay:by+1,ax:bx+1]|=painted
            return
        rr=s.MM(radius)
        for y in range(ay,by+1):
            yy=y0+y*step
            for x in range(ax,bx+1):
                if not target[y,x] and ob.shape.Collide(s.V(x0+x*step,yy),rr):target[y,x]=True
    for ob in self.obstacles:
        if ob.code==code:continue
        if ob.kind!='via_keepout':
            for i,ly in enumerate(self.layers):
                if ly in ob.layers:paint(ob,blocked[i],width/2+max(clear,ob.clearance)+guard)
        if ob.kind!='track_keepout':
            if ob.kind=='protected_power_zone' and getattr(self,'zone_names',{}).get(ob.uid)=='VBUS':
                # Scoped exception: allow a small antipad only in a broad VBUS
                # interior. Boundary strips and locked flow tracks stay blocked.
                bb=s.bbox(ob.shape,.3+max(clear,ob.clearance)+guard)
                ax=max(0,math.floor((bb[0]-x0)/step));bx=min(nx-1,math.ceil((bb[2]-x0)/step));ay=max(0,math.floor((bb[1]-y0)/step));by=min(ny-1,math.ceil((bb[3]-y0)/step))
                if ax<=bx and ay<=by:
                    xx=x0+np.arange(ax,bx+1)[None,:]*step;yy=y0+np.arange(ay,by+1)[:,None]*step
                    full=shape_mask(ob.shape,xx,yy,.3+max(clear,ob.clearance)+guard);inside=polygon_mask(ob.shape,xx,yy,0);edge=np.zeros_like(inside)
                    for i in range(ob.shape.OutlineCount()):
                        contour=ob.shape.COutline(i);pts=[(p.ToMM(contour.CPoint(k).x),p.ToMM(contour.CPoint(k).y))for k in range(contour.PointCount())]
                        for (a,b),(c,d)in zip(pts,pts[1:]+pts[:1]):
                            vx=c-a;vy=d-b;den=vx*vx+vy*vy;u=np.clip(((xx-a)*vx+(yy-b)*vy)/den,0,1)if den else 0;edge|=(xx-(a+u*vx))**2+(yy-(b+u*vy))**2<=(1.8+guard)**2
                    via[ay:by+1,ax:bx+1]|=full&~(inside&~edge)
            else:paint(ob,via,.3+max(clear,ob.clearance)+guard)
    for ob in self.protected:paint(ob,via,.3+max(clear,ob.clearance)+guard)
    for ob in self.surface_pads:paint(ob,via,.35+guard)
    for h in self.holes:
        paint(h,via,.15+self.hole_gap+guard)
        if h.code!=code:
            for mask in blocked:paint(h,mask,width/2+self.hole_clear+guard)
    rectangular=False
    if self.outline.OutlineCount()==1 and self.outline.HoleCount(0)==0:
        contour=self.outline.COutline(0)
        if contour.PointCount()==4:
            points=[(p.ToMM(contour.CPoint(k).x),p.ToMM(contour.CPoint(k).y)) for k in range(4)]
            rectangular=all(a[0]==b[0] or a[1]==b[1] for a,b in zip(points,points[1:]+points[:1]))
            if rectangular:
                xs=x0+np.arange(nx)[None,:]*step;ys=y0+np.arange(ny)[:,None]*step
                left=min(q[0] for q in points);right=max(q[0] for q in points);top=min(q[1] for q in points);bottom=max(q[1] for q in points)
                for target,margin in [(blocked,self.edge_clear+width/2+guard),(via,self.edge_clear+.3+guard)]:
                    edge=(xs<=left+margin)|(xs>=right-margin)|(ys<=top+margin)|(ys>=bottom-margin)
                    target|=edge
    if not rectangular:
        for y in range(ny):
            for x in range(nx):
                pt=s.V(x0+x*step,y0+y*step)
                if not self.outline.Contains(pt):blocked[:,y,x]=True;via[y,x]=True;continue
                if any(e.Collide(pt,s.MM(self.edge_clear+width/2+guard)) for e in self.edge):blocked[:,y,x]=True
                if any(e.Collide(pt,s.MM(self.edge_clear+.3+guard)) for e in self.edge):via[y,x]=True
    print(' vector mask seconds',round(time.monotonic()-started,3),flush=True)
    return blocked,via

def near(self,field,shape,clear):
    cache=getattr(self,'_fast_spatial',None)
    if cache is None:cache={};self._fast_spatial=cache
    objects=getattr(self,field)
    if not objects:return []
    if field not in cache:cache[field]=(np.array([o.bb for o in objects]),np.array([o.clearance for o in objects]))
    boxes,cl=cache[field];radius=np.maximum(clear,cl);a=s.bbox(shape)
    ix=np.flatnonzero((boxes[:,0]<=a[2]+radius)&(boxes[:,2]>=a[0]-radius)&(boxes[:,1]<=a[3]+radius)&(boxes[:,3]>=a[1]-radius))
    return [objects[int(i)] for i in ix]

def line_ok(self,a,b,ly,code,width,clear):
    shape=p.SHAPE_SEGMENT(s.V(*a),s.V(*b),s.MM(width))
    if not self.inside(shape,width/2):return False
    for ob in near(self,'obstacles',shape,clear):
        if ly in ob.layers and ob.code!=code and ob.kind!='via_keepout' and ob.shape.Collide(shape,s.MM(max(clear,ob.clearance))):return False
    for h in near(self,'holes',shape,self.hole_clear):
        if h.code!=code and h.shape.Collide(shape,s.MM(self.hole_clear)):return False
    return True

def via_ok(self,at,code,clear):
    copper=p.SHAPE_CIRCLE(s.V(*at),s.MM(.3));drill=p.SHAPE_CIRCLE(s.V(*at),s.MM(.15))
    if not self.inside(copper,.3):return False
    for ob in near(self,'obstacles',copper,clear):
        if ob.code!=code and ob.kind!='track_keepout' and ob.shape.Collide(copper,s.MM(max(clear,ob.clearance))):return False
    for ob in near(self,'protected',copper,clear):
        if ob.shape.Collide(copper,s.MM(max(clear,ob.clearance))):return False
    if any(ob.shape.Collide(copper,s.MM(.05)) for ob in near(self,'surface_pads',copper,.05)):return False
    if any(h.shape.Collide(drill,s.MM(self.hole_gap)) for h in near(self,'holes',drill,self.hole_gap)):return False
    return True


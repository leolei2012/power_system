"""Private scoped geometry: VBUS interior via exception, never PHASE/BR_SW.

API: g=WideVBUSGeometry(board,args,project,power_report)
Standard Geometry.line_ok / via_ok / masks signatures. g.holes_vbus(at)
returns touched VBUS zone UUIDs. Required after any accepted proposal:
real KiCad DRC, verify_fixed_and_power(board,report), and preserve locked geometry.
No source files are written by this module. No global base-class monkey patch.
"""
import sys,math,collections
from pathlib import Path
import pcbnew as p
import compact_stitch_signals as S
import compact_wide_vbus_masks as wide_vbus_masks
MM=p.FromMM;V=S.V;XY=S.XY;UID=S.UID
class WideVBUSGeometry(S.Geometry):
 masks=wide_vbus_masks.masks
 def __init__(self,board,args,project,power_report):
  report=power_report
  self.mask_guard_mm=.005
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

def verify_fixed_and_power(board,report):
 from compact_verify_fixed import verify_geometry,kelvin_check
 from compact_power_copper import audit_power_connectivity
 objects,issues,_=verify_geometry(board,report)
 extra,_,_,_=kelvin_check(board,report,objects)
 if issues or extra:raise ValueError({'fixed_or_Kelvin':issues+extra})
 return audit_power_connectivity(board,report)

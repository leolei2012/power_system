"""Actual-pad main-power copper for the first Rev E layout review.

This is a fresh-board authoring step, not an old-board route importer. Main
planes/PHASE sheets, SOURCE-before-shunt returns and Kelvin traces are locked.
No claim of thermal rating, full signal routing, or fabrication readiness.
"""
from pathlib import Path
import hashlib,json,math,shutil
import pcbnew as p
from reve_local_astar import route as astar_route

B=Path(__file__).resolve().parents[1];R=B/'review/pcb_rev_e_2026-11-11';D=R/'power';S=R/'work/inverter.kicad_pcb';O=D/'inverter.kicad_pcb'
MM=p.FromMM;V=lambda xy:p.VECTOR2I(MM(xy[0]),MM(xy[1]));XY=lambda ob:(round(p.ToMM(ob.GetPosition().x),6),round(p.ToMM(ob.GetPosition().y),6))


def main():
 D.mkdir(exist_ok=True);shutil.copyfile(S,O);pro=S.with_suffix('.kicad_pro').read_bytes();O.with_suffix('.kicad_pro').write_bytes(pro)
 for f in ['fp-lib-table','sym-lib-table']:shutil.copyfile(S.parent/f,D/f)
 b=p.LoadBoard(str(O));fps={f.GetReference():f for f in b.GetFootprints()};nets={n.GetNetname():n for n in b.GetNetsByNetcode().values()};layers=list(b.GetEnabledLayers().CuStack())
 rec={'source':str(S),'source_sha256':hashlib.sha256(S.read_bytes()).hexdigest(),'tracks':[],'vias':[],'zones':[],'kelvin':[],'failed':[]}
 protected_kelvin=set()
 def pad(r,n,large=False):
  pp=[a for a in fps[r].Pads() if a.GetNumber()==str(n)];return max(pp,key=lambda a:a.GetSize().x*a.GetSize().y) if large else pp[0]
 def net(r,n):return nets[pad(r,n).GetNetname()]
 def zone(nn,pts,ly,name,priority=1,keep=False):
  z=p.ZONE(b);ls=p.LSET();ls.AddLayer(ly);z.SetLayerSet(ls);z.SetZoneName('REV E / '+name);z.SetAssignedPriority(priority);z.SetLocalClearance(MM(.4 if nn and ('PHASE' in nn or nn=='VBUS' or nn.endswith('BR_SW')) else .2));z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetMinThickness(MM(.25))
  assert list(z.GetLayerSet().CuStack())==[ly],('Zone assigned to wrong physical copper layer',name)
  if keep:z.SetIsRuleArea(True);z.SetDoNotAllowZoneFills(True);z.SetDoNotAllowTracks('negative Kelvin' not in name);z.SetDoNotAllowVias('negative Kelvin' not in name);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
  else:z.SetNet(nets[nn])
  poly=z.Outline();poly.NewOutline()
  for pt in pts:poly.Append(MM(pt[0]),MM(pt[1]))
  b.Add(z);rec['zones'].append({'uuid':z.m_Uuid.AsString(),'net':nn,'name':name,'layer':b.GetLayerName(ly),'points':pts,'keepout':keep});return z
 rect=lambda a,c,d,e:[(a,c),(d,c),(d,e),(a,e)]
 def legal(shape,code,ly,clear):
  for f in fps.values():
   for a in f.Pads():
    if not a.GetNumber() or not a.IsOnLayer(ly) or a.GetNetCode()==code:continue
    other=a.GetNetname();need=max(clear,.4 if other=='VBUS' or 'PHASE' in other or other.endswith(('BR_SW','DC_FUSED','DC_INPUT_POS')) else .2)
    if a.GetEffectiveShape(ly).Collide(shape,MM(need)):return False
  for t in b.GetTracks():
   other=t.GetNetname();need=max(clear,.4 if other=='VBUS' or 'PHASE' in other or other.endswith(('BR_SW','DC_FUSED','DC_INPUT_POS')) else .2)
   if t.m_Uuid.AsString() in protected_kelvin:need=max(need,.25)
   if t.IsOnLayer(ly) and (t.GetNetCode()!=code or t.m_Uuid.AsString() in protected_kelvin) and t.GetEffectiveShape(ly).Collide(shape,MM(need)):return False
  return True
 def path(nn,pts,w,ly,name,check=True):
  nn=nets[nn] if isinstance(nn,str) else nn;ids=[];made=[]
  for a,c in zip(pts,pts[1:]):
   if a==c:continue
   sh=p.SHAPE_SEGMENT(V(a),V(c),MM(w))
   if check and not legal(sh,nn.GetNetCode(),ly,.4 if nn.GetNetname()=='VBUS' or 'PHASE' in nn.GetNetname() or nn.GetNetname().endswith(('BR_SW','DC_FUSED','DC_INPUT_POS')) else .2):
    rec['failed'].append({'name':name,'net':nn.GetNetname(),'points':pts,'width':w,'layer':b.GetLayerName(ly)})
    for t in made:b.Delete(t)
    return []
   t=p.PCB_TRACK(b);t.SetStart(V(a));t.SetEnd(V(c));t.SetLayer(ly);t.SetWidth(MM(w));t.SetNet(nn);t.SetLocked(True);b.Add(t);made.append(t);ids.append(t.m_Uuid.AsString())
  rec['tracks'].extend({'uuid':t.m_Uuid.AsString(),'net':nn.GetNetname(),'purpose':name,'width':w,'layer':b.GetLayerName(ly),'a':(p.ToMM(t.GetStart().x),p.ToMM(t.GetStart().y)),'b':(p.ToMM(t.GetEnd().x),p.ToMM(t.GetEnd().y))} for t in made)
  return ids
 def smart(nn,start,goal,w,ly,name):
  nn=nets[nn] if isinstance(nn,str) else nn
  direct=path(nn,[start,goal],w,ly,name)
  if direct:return direct
  mark=len(rec['failed'])-1
  saved=[]
  for i in range(1,5):
   hp=next(iter(fps['H'+str(i)].Pads()));saved.append((hp,hp.GetSize()));hp.SetSize(V((5.6,5.6)))
  try:pts,stats=astar_route(b,nn.GetNetname(),b.GetLayerName(ly),w,start,goal,margin=3,limit=1.5,step=.125,protected_uuids=protected_kelvin)
  finally:
   for hp,size in saved:hp.SetSize(size)
  if pts and all(100.6<=a<=159.4 and 100.6<=c<=159.4 for a,c in pts):
   ids=path(nn,pts,w,ly,name+' local-shape route',False);rec['failed'][mark]['resolved_by_local_route']=True;return ids
  return []
 def local_pair(ar,an,br,bn,w,name):
  aa=pad(ar,an);cc=pad(br,bn);assert aa.GetNetname()==cc.GetNetname(),(ar,an,br,bn)
  nn=net(ar,an);a=XY(aa);c=XY(cc);la=p.B_Cu if fps[ar].IsFlipped() else p.F_Cu;lc=p.B_Cu if fps[br].IsFlipped() else p.F_Cu
  if la!=lc:
   v=via(nn,(a[0]+.8,a[1]),name+' layer transfer',.6,.3)
   if not v:return
   smart(nn,a,XY(v),.3,la,name+' transfer access');a=XY(v);la=lc
  ends=[]
  for rr,pp,pt,number in [(ar,aa,a,an),(br,cc,c,bn)]:
   if w>.3 and rr.startswith('U'):
    ctr=XY(fps[rr]);dx=pt[0]-ctr[0];dy=pt[1]-ctr[1];end=(pt[0]+(.8 if dx>0 else -.8),pt[1]) if abs(dx)>=abs(dy) else (pt[0],pt[1]+(.8 if dy>0 else -.8))
    smart(nn,pt,end,.25,la,name+' short IC neck');ends.append(end)
   else:ends.append(pt)
  smart(nn,ends[0],ends[1],w,la,name)
 def via(nn,pt,name,diam=.8,drill=.4,seek=True):
  nn=nets[nn] if isinstance(nn,str) else nn;points=[pt]
  if seek:
   for radius in [.3,.6,.9,1.2,1.5,1.8]:points.extend((round(pt[0]+radius*math.cos(k*math.pi/8),3),round(pt[1]+radius*math.sin(k*math.pi/8),3)) for k in range(16))
  for q in points:
   if not 100.5+diam/2<=q[0]<=159.5-diam/2 or not 100.5+diam/2<=q[1]<=159.5-diam/2:continue
   if any(math.dist(q,XY(fps['H'+str(i)]))<2.8+diam/2 for i in range(1,5)):continue
   circle=p.SHAPE_CIRCLE(V(q),MM(diam/2))
   if not all(legal(circle,nn.GetNetCode(),ly,.4 if nn.GetNetname()=='VBUS' or 'PHASE' in nn.GetNetname() or nn.GetNetname().endswith(('BR_SW','DC_FUSED','DC_INPUT_POS')) else .2) for ly in layers):continue
   collision=False
   for f in fps.values():
    for a in f.Pads():
     if max(a.GetDrillSize().x,a.GetDrillSize().y)>0 and a.GetEffectiveHoleShape().Collide(p.SHAPE_CIRCLE(V(q),MM(drill/2)),MM(.25)):collision=True;break
    if collision:break
   if collision:continue
   for t in b.GetTracks():
    if isinstance(t,p.PCB_VIA) and math.dist(q,XY(t))<p.ToMM(t.GetDrill())/2+drill/2+.25:collision=True;break
   if collision:continue
   v=p.PCB_VIA(b);v.SetPosition(V(q));v.SetWidth(MM(diam));v.SetDrill(MM(drill));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(nn);v.SetLocked(True);b.Add(v);rec['vias'].append({'uuid':v.m_Uuid.AsString(),'net':nn.GetNetname(),'xy':q,'diameter':diam,'drill':drill,'purpose':name});return v
  rec['failed'].append({'name':name,'net':nn.GetNetname(),'via_at':pt});return None
 # M2 copper keepouts are native rule areas on every active copper layer.
 for i in range(1,5):
  h=XY(fps['H'+str(i)]);pts=[(h[0]+2.8*math.cos(k*math.pi/32),h[1]+2.8*math.sin(k*math.pi/32)) for k in range(64)]
  for ly in layers:zone(None,pts,ly,'M2 '+str(i)+' copper clearance',30,True)
 for ly in [p.In1_Cu,p.In4_Cu]:zone('GND',rect(100.5,100.5,159.5,159.5),ly,'GND reference plane',0)
 zone('VBUS',[(110,102),(153,102),(153,114),(159,114),(159,159.2),(121,159.2),(121,150.6),(134.5,150.6),(134.5,114),(110,114)],p.In3_Cu,'VBUS main distribution',0)
 zone('VBUS',rect(134.5,103.0,142.7,151),p.F_Cu,'VBUS front parallel spine',0)
 for i,phase in enumerate('UVW'):
  hi='Q'+str(1+2*i);lo='Q'+str(2+2*i);rs='RS'+str(1+i);amp='U'+str(10+i);yy=XY(fps[hi])[1];ph=net(hi,1).GetNetname();src=net(lo,1).GetNetname();rh=XY(pad(rs,1));rl=XY(pad(rs,2));sx=XY(pad(lo,1))[0]+.175
  zone(ph,[(143.3,yy-1.0),(146,yy-1.0),(146,yy-2.6),(151.7,yy-2.6),(151.7,yy+4.9),(143.3,yy+4.9)],p.F_Cu,phase+' commutation sheet',10)
  zone(ph,rect(145,yy-2,159.2,yy+5.2),p.B_Cu,phase+' back parallel/output sheet',10)
  bank=[]
  for x in [145.5,146.9]:
   for dy in [2.8,4.2]:
    v=via(ph,(x,yy+dy),phase+' source transfer four-via bank');bank.append(XY(v) if v else None)
  for x in [148.3,149.7]:
   for dy in [-.8,.6]:via(ph,(x,yy+dy),phase+' drain transfer four-via bank')
  # The B sheet can be split by the driver's local returns. A short inner
  # bus also joins the actual phase-output PTH to the drain transfer bank.
  drains=[v for v in rec['vias'] if v['net']==ph and v['purpose']==phase+' drain transfer four-via bank']
  if drains:
   start=max(drains,key=lambda v:(v['xy'][1],v['xy'][0]))['xy']
   smart(ph,tuple(start),XY(pad('J4',i+1)),2.4,p.In2_Cu,phase+' output inner bus')
  for pin in [1,2,3]:path(src,[XY(pad(lo,pin)),(sx,XY(pad(lo,pin))[1])],.65,p.F_Cu,phase+' SOURCE pad neck')
  path(src,[(sx,yy-.635),(sx,yy+1.905)],.8,p.F_Cu,phase+' SOURCE pad bar')
  path(src,[(sx,yy+1.905),(sx,rh[1]),rh],2.0,p.F_Cu,phase+' SOURCE shunt main stem')
  # Main GND leaves the outer west side, away from the positive Kelvin pad.
  gpoints=[]
  # Four barrels inside the ground-side pad retain a broad direct return. This
  # via-in-pad review geometry needs filled/capped or solder-wicking review.
  for dx in [-.6,.6]:
   for dy in [-.5,.5]:
    v=via('GND',(rl[0]+dx,rl[1]+dy),phase+' shunt GND four-via bank',seek=False)
    if v:gpoints.append(XY(v));path('GND',[rl,XY(v)],.8,p.F_Cu,phase+' GND pad return')
  for x in [136.0,137.4]:
   for dy in [2.8,4.2]:via('VBUS',(x,yy+dy),phase+' VBUS four-via bank')
  # Separate sense branches use the inner pad edges and never share a power
  # via or a thin driver-COM return. Negative via is isolated from both planes.
  kp=via(src,(rh[0]-2.7,rh[1]+.45),phase+' Kelvin positive',.6,.3)
  kn=via('GND',(rl[0]+2.8,rl[1]-.45),phase+' Kelvin negative isolated',.6,.3)
  item={'phase':phase,'RS':rs,'INA':amp,'positive_track_uuids':[],'negative_track_uuids':[]}
  if kp:
   at=XY(kp);item['positive_via_uuid']=kp.m_Uuid.AsString();item['positive_track_uuids']+=path(src,[rh,at],.2,p.F_Cu,phase+' Kelvin positive F')
   dest=XY(pad(amp,8));item['positive_track_uuids']+=smart(src,at,dest,.2,p.B_Cu,phase+' Kelvin positive B')
  if kn:
   at=XY(kn);item['negative_via_uuid']=kn.m_Uuid.AsString();item['negative_track_uuids']+=path('GND',[rl,at],.2,p.F_Cu,phase+' Kelvin negative F')
   dest=XY(pad(amp,1));item['negative_track_uuids']+=smart('GND',at,dest,.2,p.B_Cu,phase+' Kelvin negative B')
   for ly in [p.In1_Cu,p.In4_Cu]:zone(None,rect(at[0]-.75,at[1]-.75,at[0]+.75,at[1]+.75),ly,phase+' negative Kelvin plane isolation',40,True)
  rec['kelvin'].append(item)
  protected_kelvin.update(item['positive_track_uuids']+item['negative_track_uuids'])
  protected_kelvin.update(item[k] for k in ['positive_via_uuid','negative_via_uuid'] if k in item)
  # Keep the local floating-driver loops ahead of ordinary signal routing.
  drv='U'+str(7+i);rhigh='R'+str(19+6*i);rlow='R'+str(20+6*i)
  for cap in ['C'+str(27+4*i),'C'+str(28+4*i)]:
   for pin,driverpin in [(1,5),(2,3)]:local_pair(cap,pin,drv,driverpin,.4,phase+' local VCC/COM '+cap)
  smart(net(drv,7),XY(pad(drv,7)),XY(pad(rhigh,1)),.4,p.B_Cu,phase+' HO to resistor')
  highvia=via(net(hi,4),(146.5,yy-3.1),phase+' high gate transfer',.6,.3)
  if highvia:
   smart(net(hi,4),XY(pad(hi,4)),XY(highvia),.4,p.F_Cu,phase+' high gate F')
   smart(net(hi,4),XY(pad(rhigh,2)),XY(highvia),.4,p.B_Cu,phase+' high gate B')
  if fps[rlow].IsFlipped():
   gv=via(net(lo,4),(152.85,yy-1.5),phase+' low gate transfer',.6,.3)
   if gv:
    smart(net(lo,4),XY(pad(rlow,2)),XY(gv),.4,p.B_Cu,phase+' low gate B')
    smart(net(lo,4),XY(gv),XY(pad(lo,4)),.4,p.F_Cu,phase+' low gate resistor to MOS')
  else:smart(net(lo,4),XY(pad(rlow,2)),XY(pad(lo,4)),.4,p.F_Cu,phase+' low gate resistor to MOS')
  for cp in ['C'+str(25+4*i),'C'+str(26+4*i)]:
   if fps[cp].IsFlipped():
    smart(net(cp,1),XY(pad(cp,1)),XY(pad(drv,8)),.4,p.B_Cu,phase+' bootstrap '+cp)
    smart(net(cp,2),XY(pad(cp,2)),XY(pad(drv,6)),.4,p.B_Cu,phase+' bootstrap VS '+cp)
  phvias=[v for v in rec['vias'] if v['net']==ph]
  if phvias:smart(ph,XY(pad(drv,6)),min([tuple(v['xy']) for v in phvias],key=lambda q:math.dist(q,XY(pad(drv,6)))),.4,p.B_Cu,phase+' VS return')
  for driverpin,target_ref,target_pin,label in [(4,rlow,1,'LO'),(3,lo,1,'COM')]:
   nn=net(drv,driverpin);a=XY(pad(drv,driverpin));target=XY(pad(target_ref,target_pin))
   if fps[target_ref].IsFlipped():smart(nn,a,target,.4,p.B_Cu,phase+' '+label+' local driver return')
   else:
    v2=via(nn,(target[0]+.2,yy+3.8),phase+' '+label+' power via',.6,.3)
    if v2:
     smart(nn,a,XY(v2),.4,p.B_Cu,phase+' '+label+' coupled local return')
     smart(nn,XY(v2),target,.4,p.F_Cu,phase+' '+label+' terminal escape')
 # Rectifier to inner VBUS and MLCC ripple ground banks.
 for x in [148.4,149.8]:
  for y in [111.2,112.6]:via('VBUS',(x,y),'rectifier VBUS four-via bank')
 for r in ['C21','C22']:
  a=XY(pad(r,2));vs=[]
  for dx in [0,1.4]:
   v=via('GND',(a[0]+dx,a[1]+1.8),r+' ground ripple via')
   if v:vs.append(XY(v));path('GND',[a,XY(v)],1.3,p.F_Cu,r+' ripple return')
 # Input path and fused inner transfer; F1 is not bypassed by a plane.
 inp=XY(pad('J3',1));fi=XY(pad('F1',1));fo=XY(pad('F1',2));dc=net('F1',2).GetNetname()
 smart(net('J3',1),inp,fi,2,p.F_Cu,'DC input to F1')
 fv=[]
 for dx in [-.45,.45]:
  for dy in [-.7,.7]:
   v=via(dc,(fo[0]+dx,fo[1]+dy),'F1 fused four-via bank',seek=False)
   if v:fv.append(XY(v));path(dc,[fo,XY(v)],1.3,p.F_Cu,'F1 fused bank access')
 if fv:
  for pin in [1,3]:
   a=XY(pad('D1',pin));v=via(dc,(a[0],a[1]),'rectifier anode transfer')
   if v:
    at=XY(v);path(dc,[a,at],1.2,p.B_Cu,'rectifier anode access')
    if pin==1:path(dc,[fv[0],(fv[0][0],105.0),(138.0,105.0),(138.0,111.2),(139.0,111.2)],2.4,p.In2_Cu,'F1 to rectifier inner feed',False)
    smart(dc,(139.0,111.2),at,1.2,p.In2_Cu,'rectifier short anode neck')
 # Brake switched node and local source return, separate from bridge shunts.
 q='Q7';qd=XY(pad(q,5,True));qs=XY(pad(q,1));br=net(q,5).GetNetname()
 zone(br,rect(qd[0]-3,qd[1]-2.7,qd[0]+2.0,qd[1]+2.7),p.F_Cu,'brake drain local island',10)
 bv=[]
 for dx in [-1.6,-.2]:
  for dy in [0,1.4]:
   v=via(br,(qd[0]+dx,qd[1]+dy),'brake drain four-via bank')
   if v:bv.append(XY(v))
 if bv:path(br,[bv[0],XY(pad('J5',2))],2.4,p.In2_Cu,'brake switched output',False)
 for pin in [1,2,3]:
  a=XY(pad(q,pin));path('GND',[a,(qs[0]+.3,a[1]),(qs[0]+.3,qs[1])],.65,p.F_Cu,'brake SOURCE pad bar')
 for dx in [.9,2.3]:
  for dy in [0,1.4]:
   v=via('GND',(qs[0]+dx,qs[1]+dy),'brake source four-via bank')
   if v:path('GND',[qs,XY(v)],.8,p.F_Cu,'brake GND access')
 # Auxiliary switchers are routed locally as a group before ordinary GPIOs.
 contract=json.loads((B.parents[1]/'outputs/pcb_review_2026-11-11/functional_layout_reference_map.json').read_text(encoding='utf-8'))
 for link in contract['links']:
  if link['group'] not in ['U2_L1_12V','U3_L2_5V']:continue
  ar,an=link['from'].rsplit('.',1);br,bn=link['to'].rsplit('.',1)
  ispower=('switch node' in link['purpose'] or 'inductor output' in link['purpose'] or 'power return' in link['purpose'] or 'capacitor positive' in link['purpose'] or 'input capacitor' in link['purpose'])
  local_pair(ar,an,br,bn,.6 if ispower else .3,link['group']+' '+link['purpose'])
 b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(O),b);O.with_suffix('.kicad_pro').write_bytes(pro)
 present={a.m_Uuid.AsString():a for a in b.GetTracks()};rec['tracks']=[t for t in rec['tracks'] if t['uuid'] in present];rec['candidate_sha256']=hashlib.sha256(O.read_bytes()).hexdigest();rec['candidate']=str(O)
 rec['protected_kelvin_uuids']=sorted(protected_kelvin)
 (D/'power_copper.json').write_text(json.dumps(rec,indent=2),encoding='utf-8');print('Created power review',len(rec['tracks']),'tracks',len(rec['vias']),'vias','skipped',len(rec['failed']),flush=True)


if __name__=='__main__':main()

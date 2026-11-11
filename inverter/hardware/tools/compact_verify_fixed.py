"""Read-only fixed-copper and Kelvin-star verification after SES import.

KiCad Python, no third-party modules:
  python compact_verify_fixed.py --board candidate/inverter.kicad_pcb \
    --power-report candidate/power_copper.json --out review/fixed_check.json

Expected UUID, net and geometric dimensions come from the power report. A
candidate file/model/metadata hash change is allowed: every reported track,
via and zone is checked individually. Zone fills are recomputed IN MEMORY;
no PCB or project is ever saved. Contact checks use actual native shapes and
filled copper, not bounding-box coincidence or whole-net connectivity.

Same-net contacts with a Kelvin branch are allowed only for its own members,
its physical RS pickup pad and its physical INA1/8 pad. A different already
locked return conductor is allowed only on the RS pad's layer and only when
the entire contact region is inside that pickup pad. In particular, a GND
track/via entering the INA input pad, a tap in a B-side branch, and a ground
pour touching the negative via on In1/In4 are failures even though ordinary
DRC cannot distinguish them from an intended same-net connection.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, sys
from pathlib import Path
import pcbnew as p

MM=p.FromMM
V=lambda x,y:p.VECTOR2I(MM(float(x)),MM(float(y)))
XY=lambda q:[p.ToMM(q.x),p.ToMM(q.y)]
UID=lambda q:q.m_Uuid.AsString()
EPS_MM=.000002
POLY_ERROR_MM=.00001

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def distance(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])
def close(a,b):return abs(float(a)-float(b))<=EPS_MM

def canonical_ring(points):
 clean=[]
 for point in points:
  q=tuple(round(float(x)/EPS_MM) for x in point)
  if not clean or clean[-1]!=q:clean.append(q)
 if len(clean)>1 and clean[0]==clean[-1]:clean.pop()
 if not clean:return ()
 sequences=[]
 for seq in [clean,list(reversed(clean))]:
  for i in range(len(seq)):sequences.append(tuple(seq[i:]+seq[:i]))
 return min(sequences)

def rings_equal(first,second):
 def clean(points):
  out=[]
  for point in points:
   if not out or distance(point,out[-1])>EPS_MM:out.append(point)
  if len(out)>1 and distance(out[0],out[-1])<=EPS_MM:out.pop()
  return out
 a,b=clean(first),clean(second)
 if len(a)!=len(b):return False
 if not a:return True
 for candidate in [b,list(reversed(b))]:
  for shift in range(len(candidate)):
   if all(distance(a[i],candidate[(i+shift)%len(candidate)])<=EPS_MM for i in range(len(a))):return True
 return False


def outlines(poly):
 return {'outlines':[[XY(poly.COutline(i).CPoint(j)) for j in range(poly.COutline(i).PointCount())] for i in range(poly.OutlineCount())],
         'holes':[[[XY(poly.CHole(i,h).CPoint(j)) for j in range(poly.CHole(i,h).PointCount())] for h in range(poly.HoleCount(i))] for i in range(poly.OutlineCount())]}

def bounds(shape):
 bb=shape.BBox();return [p.ToMM(bb.GetX()),p.ToMM(bb.GetY()),p.ToMM(bb.GetRight()),p.ToMM(bb.GetBottom())]
def boxes_touch(a,b):return a[0]<=b[2]+EPS_MM and a[2]>=b[0]-EPS_MM and a[1]<=b[3]+EPS_MM and a[3]>=b[1]-EPS_MM

def identity(item,board):
 out={'uuid':UID(item),'class':item.GetClass(),'net':item.GetNetname() if hasattr(item,'GetNetname') else '', 'locked':bool(item.IsLocked())}
 if isinstance(item,p.PAD):out.update(ref=item.GetParentFootprint().GetReference(),pin=item.GetNumber(),at=XY(item.GetPosition()))
 elif isinstance(item,p.ZONE):out.update(name=item.GetZoneName(),layers=[board.GetLayerName(ly) for ly in item.GetLayerSet().Seq()],keepout=bool(item.GetIsRuleArea()))
 elif isinstance(item,p.PCB_VIA):out.update(at=XY(item.GetPosition()),diameter_mm=p.ToMM(item.GetWidth(p.F_Cu)),drill_mm=p.ToMM(item.GetDrill()))
 elif isinstance(item,p.PCB_TRACK):out.update(layer=board.GetLayerName(item.GetLayer()),a=XY(item.GetStart()),b=XY(item.GetEnd()),width_mm=p.ToMM(item.GetWidth()))
 return out


def verify_geometry(board,report):
 objects={UID(q):q for q in list(board.GetTracks())+list(board.Zones())};issues=[];checks=[]
 def problem(kind,uid,field,expected,actual):issues.append({'kind':kind,'uuid':uid,'field':field,'expected':expected,'actual':actual})
 seen=set()
 for kind in ['tracks','vias','zones']:
  for record in report.get(kind,[]):
   ident=record['uuid'];q=objects.get(ident)
   if ident in seen:problem(kind,ident,'duplicate_report_uuid','unique','duplicate')
   seen.add(ident)
   if q is None:problem(kind,ident,'uuid','present','missing');continue
   actual=identity(q,board);local_before=len(issues)
   if actual['net']!=(record['net'] or ''):problem(kind,ident,'net',record['net'],actual['net'])
   if kind=='tracks':
    if q.GetClass()!='PCB_TRACK':problem(kind,ident,'class','PCB_TRACK',q.GetClass());continue
    if not q.IsLocked():problem(kind,ident,'locked',True,False)
    if board.GetLayerName(q.GetLayer())!=record['layer']:problem(kind,ident,'layer',record['layer'],board.GetLayerName(q.GetLayer()))
    if not close(p.ToMM(q.GetWidth()),record['width_mm']):problem(kind,ident,'width_mm',record['width_mm'],p.ToMM(q.GetWidth()))
    a,b=XY(q.GetStart()),XY(q.GetEnd());expected=[record['a'],record['b']]
    if not ((distance(a,expected[0])<=EPS_MM and distance(b,expected[1])<=EPS_MM) or (distance(a,expected[1])<=EPS_MM and distance(b,expected[0])<=EPS_MM)):problem(kind,ident,'endpoints_mm',expected,[a,b])
   elif kind=='vias':
    if not isinstance(q,p.PCB_VIA):problem(kind,ident,'class','PCB_VIA',q.GetClass());continue
    if not q.IsLocked():problem(kind,ident,'locked',True,False)
    if distance(XY(q.GetPosition()),record['xy'])>EPS_MM:problem(kind,ident,'position_mm',record['xy'],XY(q.GetPosition()))
    if not close(p.ToMM(q.GetDrill()),record['drill_mm']):problem(kind,ident,'drill_mm',record['drill_mm'],p.ToMM(q.GetDrill()))
    for ly in board.GetEnabledLayers().CuStack():
     if not q.IsOnLayer(ly) or not close(p.ToMM(q.GetWidth(ly)),record['diameter_mm']):problem(kind,ident,'diameter_on_'+board.GetLayerName(ly),record['diameter_mm'],p.ToMM(q.GetWidth(ly)) if q.IsOnLayer(ly) else 'absent')
    if q.GetViaType()!=p.VIATYPE_THROUGH or q.TopLayer()!=p.F_Cu or q.BottomLayer()!=p.B_Cu:problem(kind,ident,'via_span','through F.Cu..B.Cu',[q.GetViaType(),board.GetLayerName(q.TopLayer()),board.GetLayerName(q.BottomLayer())])
   else:
    if not isinstance(q,p.ZONE):problem(kind,ident,'class','ZONE',q.GetClass());continue
    actual['outline']=outlines(q.Outline());actual['priority']=q.GetAssignedPriority()
    actual['clearance_mm']=None if q.GetLocalClearance() is None else p.ToMM(q.GetLocalClearance())
    if set(actual['layers'])!={record['layer']}:problem(kind,ident,'layers',[record['layer']],actual['layers'])
    if bool(q.GetIsRuleArea())!=bool(record.get('keepout',False)):problem(kind,ident,'keepout',record.get('keepout',False),q.GetIsRuleArea())
    shape=actual['outline']
    if len(shape['outlines'])!=1 or any(shape['holes']) or not rings_equal(shape['outlines'][0],record['points']):problem(kind,ident,'outline_mm',record['points'],shape)
    if record.get('clearance_mm') is not None and (actual['clearance_mm'] is None or not close(record['clearance_mm'],actual['clearance_mm'])):problem(kind,ident,'clearance_mm',record['clearance_mm'],actual['clearance_mm'])
    if record.get('priority') is not None and q.GetAssignedPriority()!=record['priority']:problem(kind,ident,'priority',record['priority'],q.GetAssignedPriority())
    if record.get('keepout') and not q.GetDoNotAllowZoneFills():problem(kind,ident,'copper_pour_keepout',True,False)
   checks.append({'kind':kind,'uuid':ident,'pass':len(issues)==local_before,'actual':actual})
 return objects,issues,checks


class Copper:
 def __init__(self,item,layer,board,filled=False):
  self.item=item;self.layer=layer;self.board=board;self.filled=filled
  self.shape=item.GetFilledPolysList(layer) if filled else item.GetEffectiveShape(layer)
  self.box=bounds(self.shape);self._poly=None
 def poly(self):
  if self._poly is None:
   if self.filled:self._poly=p.SHAPE_POLY_SET(self.shape)
   else:
    self._poly=p.SHAPE_POLY_SET();self.item.TransformShapeToPolygon(self._poly,self.layer,0,MM(POLY_ERROR_MM),p.ERROR_OUTSIDE)
  return self._poly


def contact_region(a,b):
 # Native collision is the authority. Circumscribed polygons are only used to
 # classify WHERE an already-detected contact lies and provide a witness.
 region=p.SHAPE_POLY_SET();region.BooleanIntersection(a.poly(),b.poly())
 if region.IsEmpty():return {'empty':True,'area_mm2':0,'bbox_mm':None,'sample_mm':None},region
 bb=bounds(region);sample=None
 if region.OutlineCount() and region.COutline(0).PointCount():sample=XY(region.COutline(0).CPoint(0))
 return {'empty':False,'area_mm2':region.Area()/1e12,'bbox_mm':bb,'sample_mm':sample},region


def kelvin_check(board,report,objects):
 issues=[];contacts=[];plane_checks=[];branches=[];layers=list(board.GetEnabledLayers().CuStack());by_net_layer=collections.defaultdict(list);fps={q.GetReference():q for q in board.GetFootprints()}
 for q in list(board.GetTracks())+[a for f in board.GetFootprints() for a in f.Pads()]:
  if not hasattr(q,'GetNetname') or not q.GetNetname():continue
  for ly in layers:
   if q.IsOnLayer(ly):by_net_layer[q.GetNetname(),ly].append(Copper(q,ly,board))
 for q in board.Zones():
  if q.GetIsRuleArea():continue
  for ly in layers:
   if q.IsOnLayer(ly):
    if not q.IsFilled() or not q.HasFilledPolysForLayer(ly):issues.append({'kind':'zone_fill_unavailable','uuid':UID(q),'net':q.GetNetname(),'layer':board.GetLayerName(ly),'reason':'Cannot prove Kelvin isolation without an actual filled polygon'});continue
    shape=q.GetFilledPolysList(ly)
    if shape.IsEmpty():issues.append({'kind':'zone_fill_empty','uuid':UID(q),'net':q.GetNetname(),'layer':board.GetLayerName(ly),'reason':'Empty copper is not accepted as an isolation proof'});continue
    by_net_layer[q.GetNetname(),ly].append(Copper(q,ly,board,True))
 for row in report.get('kelvin',[]):
  phase=row['phase'];rs=row['RS'];ina=row['INA']
  if rs not in fps or ina not in fps:issues.append({'kind':'missing_Kelvin_footprint','phase':phase,'RS':rs,'INA':ina});continue
  rs_pads={q.GetNumber():q for q in fps[rs].Pads()};ina_pads={q.GetNumber():q for q in fps[ina].Pads()}
  for polarity,rs_pin,ina_pin,net in [('positive','1','8',phase+'_SOURCE'),('negative','2','1','GND')]:
   member_ids=row[polarity+'_track_uuids']+[row[polarity+'_via_uuid']];members=[objects[q] for q in member_ids if q in objects]
   branch={'phase':phase,'polarity':polarity,'net':net,'members':member_ids,'RS_pad':rs+'-'+rs_pin,'INA_pad':ina+'-'+ina_pin};branches.append(branch)
   if len(members)!=len(member_ids) or rs_pin not in rs_pads or ina_pin not in ina_pads:issues.append({'kind':'incomplete_Kelvin_branch','branch':branch});continue
   pickup=rs_pads[rs_pin];target=ina_pads[ina_pin];allowed_pad_ids={UID(pickup),UID(target)}
   expected_rs=row['source_pad' if polarity=='positive' else 'ground_pad'];expected_ina=row[polarity+'_B_path'][-1]
   for pad,expected in [(pickup,expected_rs),(target,expected_ina)]:
    if pad.GetNetname()!=net or distance(XY(pad.GetPosition()),expected)>EPS_MM:issues.append({'kind':'Kelvin_pad_geometry_or_net_changed','phase':phase,'polarity':polarity,'expected_net':net,'expected_xy':expected,'actual':identity(pad,board)})
   pickup_poly={ly:Copper(pickup,ly,board).poly() for ly in layers if pickup.IsOnLayer(ly)}
   # Continuity graph contains only selected branches plus the two allowed
   # physical pad shapes. The whole net/ground plane cannot hide a break.
   nodes=[];edges=[]
   for q in members:
    if isinstance(q,p.PCB_VIA):
     base=len(nodes);nodes.extend((ly,q.GetPosition()) for ly in layers if q.IsOnLayer(ly));edges.extend((base,i) for i in range(base+1,len(nodes)))
    else:
     base=len(nodes);nodes.extend([(q.GetLayer(),q.GetStart()),(q.GetLayer(),q.GetEnd())]);edges.append((base,base+1))
   parent=list(range(len(nodes)))
   def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
   def union(i,j):parent[find(i)]=find(j)
   for a,b in edges:union(a,b)
   for i,(ly,a) in enumerate(nodes):
    for j,(lz,b) in enumerate(nodes[:i]):
     if ly==lz and distance(XY(a),XY(b))<=EPS_MM:union(i,j)
   reached=[]
   for pad in [pickup,target]:
    hit=[i for i,(ly,a) in enumerate(nodes) if pad.IsOnLayer(ly) and pad.GetEffectiveShape(ly).Collide(a,0)]
    reached.append(bool(hit))
    for i in hit[1:]:union(hit[0],i)
   if not all(reached) or len({find(i) for i in range(len(nodes))})!=1:issues.append({'kind':'disconnected_Kelvin_branch','phase':phase,'polarity':polarity,'pickup_target_reached':reached,'components':len({find(i) for i in range(len(nodes))})})
   branch['continuous_to_actual_pads']=all(reached) and len({find(i) for i in range(len(nodes))})==1
   # Report every external same-net physical contact, including allowed pad
   # contacts. Never silently whitelist an arbitrary same-net track near INA.
   for subject in members:
    for ly in layers:
     if not subject.IsOnLayer(ly):continue
     a=Copper(subject,ly,board)
     for b in by_net_layer[net,ly]:
      other=b.item
      if UID(other) in member_ids or not boxes_touch(a.box,b.box):continue
      if not a.shape.Collide(b.shape,0):continue
      details,region=contact_region(a,b);allowed=False;reason='Unexpected same-net copper attachment to fixed Kelvin branch'
      if UID(other) in allowed_pad_ids:
       allowed=True;reason='Actual RS pickup pad' if UID(other)==UID(pickup) else 'Actual INA sense input pad only'
      elif ly in pickup_poly and other.IsLocked() and isinstance(other,p.PCB_TRACK) and not details['empty']:
       remaining=p.SHAPE_POLY_SET(region);pad_boundary=p.SHAPE_POLY_SET(pickup_poly[ly]);pad_boundary.Inflate(MM(POLY_ERROR_MM*2),p.CORNER_STRATEGY_ROUND_ALL_CORNERS,MM(POLY_ERROR_MM))
       remaining.BooleanSubtract(pad_boundary)
       if remaining.IsEmpty():allowed=True;reason='Already-locked return copper; entire contact is inside RS pickup pad'
      record={'phase':phase,'polarity':polarity,'net':net,'layer':board.GetLayerName(ly),'subject_uuid':UID(subject),'other':identity(other,board),'allowed':allowed,'reason':reason,'contact':details}
      contacts.append(record)
      if not allowed:issues.append({'kind':'Kelvin_same_net_attachment','contact':record})
   if polarity=='negative':
    via=objects.get(row['negative_via_uuid'])
    for layer_name in ['In1.Cu','In4.Cu']:
     ly=board.GetLayerID(layer_name);zone_copper=[q for q in by_net_layer['GND',ly] if q.filled]
     hits=[]
     if via is None or not zone_copper:issues.append({'kind':'negative_Kelvin_ground_plane_proof_missing','phase':phase,'layer':layer_name});continue
     via_shape=via.GetEffectiveShape(ly)
     for c in zone_copper:
      if boxes_touch(bounds(via_shape),c.box) and via_shape.Collide(c.shape,0):hits.append(UID(c.item))
     check={'phase':phase,'negative_via_uuid':UID(via),'layer':layer_name,'filled_GND_zone_uuids':[UID(c.item) for c in zone_copper],'actual_filled_shape_contacts':hits,'isolated':not hits};plane_checks.append(check)
     if hits:issues.append({'kind':'negative_Kelvin_GND_plane_attachment','check':check})
 return issues,contacts,plane_checks,branches


def main():
 parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 parser.add_argument('--board',required=True,type=Path);parser.add_argument('--power-report',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
 args=parser.parse_args();args.board=args.board.resolve();args.power_report=args.power_report.resolve();args.out=args.out.resolve()
 if args.out in [args.board,args.power_report]:parser.error('Output report must be distinct from all input files')
 watched=[args.board,args.power_report];project=args.board.with_suffix('.kicad_pro')
 if project.exists():watched.append(project)
 hashes={str(q):sha(q) for q in watched};report=json.loads(args.power_report.read_text(encoding='utf-8'));board=p.LoadBoard(str(args.board))
 _,pre_issues,_=verify_geometry(board,report)
 # Fill only this in-memory board. Never SaveBoard: native source copper and
 # project metadata remain untouched. Verify net ownership both before/after.
 board.BuildConnectivity();p.ZONE_FILLER(board).Fill(board.Zones());board.BuildConnectivity()
 objects,geometry_issues,geometry_checks=verify_geometry(board,report)
 topology_issues,contacts,plane_checks,branches=kelvin_check(board,report,objects)
 issues=[];seen=set()
 for q in pre_issues+geometry_issues+topology_issues:
  key=json.dumps(q,sort_keys=True,ensure_ascii=False)
  if key not in seen:seen.add(key);issues.append(q)
 unchanged={path:sha(path)==value for path,value in hashes.items()}
 if not all(unchanged.values()):issues.append({'kind':'source_changed_during_read_only_verification','files':unchanged})
 output={'pass':not issues,'board':str(args.board),'board_sha256':hashes[str(args.board)],'power_report':str(args.power_report),'power_report_sha256':hashes[str(args.power_report)],'reference_candidate_sha256':report.get('candidate_sha256'),'candidate_hash_match_required':False,'reference_candidate_hash_matches':hashes[str(args.board)]==report.get('candidate_sha256'),'read_only_source_hashes_unchanged':unchanged,'refilled_only_in_memory':True,'geometry_tolerance_mm':EPS_MM,'contact_polygon_max_error_mm':POLY_ERROR_MM,'fixed_geometry_counts':{kind:len(report.get(kind,[])) for kind in ['tracks','vias','zones']},'fixed_geometry_checks':geometry_checks,'Kelvin_branches':branches,'same_net_contacts':contacts,'negative_Kelvin_ground_plane_checks':plane_checks,'issues':issues,'summary':{'fixed_geometry_issue_count':sum(q.get('kind') in ['tracks','vias','zones'] for q in issues),'allowed_contacts':sum(q['allowed'] for q in contacts),'suspicious_contacts':sum(not q['allowed'] for q in contacts),'negative_via_plane_checks':len(plane_checks),'negative_via_plane_contacts':sum(bool(q['actual_filled_shape_contacts']) for q in plane_checks)},'scope':'UUID/net/geometric dimensions encoded by the power report; no dependence on file/model/metadata hash. Actual saved track/via topology plus fresh in-memory filled-zone copper determines external same-net Kelvin attachments. Native DRC and thermal/switching validation remain separate.'}
 args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Fixed geometry:',output['fixed_geometry_counts'],'Kelvin allowed contacts',output['summary']['allowed_contacts'],'suspicious',output['summary']['suspicious_contacts'],'negative via plane checks',len(plane_checks),'issues',len(issues),'PASS',output['pass'])
 print('Report:',args.out)
 for q in issues[:8]:print(json.dumps(q,ensure_ascii=False))
 return 0 if output['pass'] else 1

if __name__=='__main__':raise SystemExit(main())

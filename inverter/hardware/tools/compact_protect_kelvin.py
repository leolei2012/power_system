"""Keep fixed shunt Kelvin branches private to the native PCB during routing.

KiCad bundled Python; no sexpdata dependency. Only --out DSN and its .json audit
are written. The input PCB, project, power report and DSN remain untouched.
Example:
  python compact_protect_kelvin.py --board power/inverter.kicad_pcb \
    --dsn exported.dsn --power-report power/power_copper.json --out guarded.dsn

The parser preserves original byte spans and handles KiCad's (string_quote ")
directive. A stale DSN/report is rejected before an output is written. Native
Kelvin tracks/vias stay locked and are not removed from the PCB. SES import must
retain those UUIDs; an empty-SES probe with KiCad10 confirmed that behavior.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math, re
from dataclasses import dataclass,field
from pathlib import Path
import pcbnew as p

@dataclass
class Token:
 start:int;end:int;value:str
@dataclass
class Node:
 start:int;end:int=0;tokens:list=field(default_factory=list);children:list=field(default_factory=list)
 @property
 def head(self):return self.tokens[0].value if self.tokens else ''
 @property
 def values(self):return [t.value for t in self.tokens]
 def child(self,name):
  found=[q for q in self.children if q.head==name]
  if len(found)!=1:raise ValueError('Expected exactly one '+name+' in '+self.head)
  return found[0]

def parse(source):
 stack=[];roots=[];i=0
 while i<len(source):
  ch=source[i]
  if ch.isspace():i+=1;continue
  if ch==';':
   e=source.find('\n',i);i=len(source) if e<0 else e+1;continue
  if ch=='(':
   node=Node(i)
   if stack:stack[-1].children.append(node)
   else:roots.append(node)
   stack.append(node);i+=1;continue
  if ch==')':
   if not stack:raise ValueError('Unexpected closing parenthesis at '+str(i))
   stack.pop().end=i+1;i+=1;continue
  if not stack:raise ValueError('Token outside DSN scope')
  a=i
  if ch=='"':
   # This is a one-character grammar directive, not an unterminated string.
   if stack[-1].head=='string_quote':i+=1;value='"'
   else:
    i+=1;chars=[]
    while i<len(source):
     if source[i]=='"':i+=1;break
     if source[i]=='\\' and i+1<len(source) and source[i+1] in ['"','\\']:
      chars.append(source[i+1]);i+=2
     else:chars.append(source[i]);i+=1
    else:raise ValueError('Unterminated quoted token at '+str(a))
    value=''.join(chars)
  else:
   while i<len(source) and not source[i].isspace() and source[i] not in '()':i+=1
   value=source[a:i]
  stack[-1].tokens.append(Token(a,i,value))
 if stack:raise ValueError('Unclosed DSN scopes')
 if len(roots)!=1 or roots[0].head!='pcb':raise ValueError('Exactly one pcb DSN root is required')
 return roots[0]

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def uid(a):return a.m_Uuid.AsString()
def xy(a):return [p.ToMM(a.x),p.ToMM(a.y)]
def dist(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])
def merge(intervals,tol):
 out=[]
 for a,b in sorted(intervals):
  if b-a<=tol/100:continue
  if out and a<=out[-1][1]+tol:out[-1][1]=max(out[-1][1],b)
  else:out.append([a,b])
 return out

def overlap_segment(a,b,c,d,tol):
 vx=b[0]-a[0];vy=b[1]-a[1];length=math.hypot(vx,vy)
 if length<=tol:return None
 if abs(vx*(c[1]-a[1])-vy*(c[0]-a[0]))/length>tol or abs(vx*(d[1]-a[1])-vy*(d[0]-a[0]))/length>tol:return None
 u=((c[0]-a[0])*vx+(c[1]-a[1])*vy)/length
 v=((d[0]-a[0])*vx+(d[1]-a[1])*vy)/length
 lo=max(0,min(u,v));hi=min(length,max(u,v))
 return (lo,hi) if hi-lo>tol/100 else None

def point(a,b,length):
 whole=dist(a,b)
 return [a[0]+(b[0]-a[0])*length/whole,a[1]+(b[1]-a[1])*length/whole]
def key(net,layer,width):return net,layer,round(width,5)
def descend(node):
 yield node
 for child in node.children:yield from descend(child)
def convex(points):
 pts=sorted(set((round(x,10),round(y,10)) for x,y in points))
 cross=lambda a,b,c:(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 lower=[]
 for q in pts:
  while len(lower)>1 and cross(lower[-2],lower[-1],q)<=0:lower.pop()
  lower.append(q)
 upper=[]
 for q in reversed(pts):
  while len(upper)>1 and cross(upper[-2],upper[-1],q)<=0:upper.pop()
  upper.append(q)
 return lower[:-1]+upper[:-1]
def guard_polygon(a,b,radius):
 # Convex hull of two circumscribed octagons encloses the true round capsule.
 rr=radius/math.cos(math.pi/8)
 return convex([(c[0]+rr*math.cos(math.pi/8+i*math.pi/4),c[1]+rr*math.sin(math.pi/8+i*math.pi/4)) for c in [a,b] for i in range(8)])


def main():
 ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 ap.add_argument('--board',required=True,type=Path);ap.add_argument('--dsn',required=True,type=Path);ap.add_argument('--power-report',required=True,type=Path);ap.add_argument('--out',required=True,type=Path)
 ap.add_argument('--allow-routed-source',action='store_true',help='Allow candidate file SHA mismatch after ordinary routing/metadata changes; all reported fixed geometry/net and native-to-DSN wiring must still match.')
 ap.add_argument('--guard-mm',type=float,default=.15,help='Per-side expansion; minimum .15mm. A .2mm Kelvin track produces an at-least .5mm-wide keepout.')
 args=ap.parse_args()
 if args.guard_mm<.15:ap.error('Kelvin guard must not be reduced below .15mm per side')
 for n in ['board','dsn','power_report','out']:setattr(args,n,getattr(args,n).resolve())
 if args.out in [args.board,args.dsn,args.power_report]:raise ValueError('Output must be a distinct routing-only DSN')
 before={str(q):digest(q) for q in [args.board,args.dsn,args.power_report]}
 report=json.loads(args.power_report.read_text(encoding='utf-8'));source=args.dsn.read_bytes().decode('utf-8');eol='\r\n' if '\r\n' in source else '\n';root=parse(source)
 if report.get('candidate_sha256') and before[str(args.board)]!=report['candidate_sha256'] and not args.allow_routed_source:raise ValueError('Power report candidate_sha256 does not match the actual input board; use the matched candidate/report revision')
 structure=root.child('structure');wiring=root.child('wiring');network=root.child('network');library=root.child('library')
 unit=root.child('unit').values[1] if any(q.head=='unit' for q in root.children) else root.child('resolution').values[1]
 scale={'mm':1,'um':1000,'mil':1000/25.4,'inch':1/25.4,'in':1/25.4}.get(unit)
 if scale is None:raise ValueError('Unsupported DSN unit: '+unit)
 resolution=root.child('resolution').values
 precision=float(resolution[2]) if resolution[1]==unit else 1
 tol=max(.000001,1.51/(scale*precision))
 board=p.LoadBoard(str(args.board))
 from compact_verify_fixed import verify_geometry
 _,fixed_geometry_issues,fixed_geometry_checks=verify_geometry(board,report)
 if fixed_geometry_issues:raise ValueError('Fixed power geometry/net differs from authoritative report: '+json.dumps(fixed_geometry_issues[:8],ensure_ascii=False))
 all_items={uid(q):q for q in board.GetTracks()};fps={q.GetReference():q for q in board.GetFootprints()}
 # Report net names express intended electrical ownership; native BuildConnectivity
 # can propagate a wrong net across overlapping copper, so matching only a DSN
 # exported after propagation would hide that error. Fail on every stale record.
 intended_records=report.get('tracks',[])+report.get('vias',[])
 if not intended_records:raise ValueError('Power report lacks intended track/via records')
 for rec in intended_records:
  q=all_items.get(rec['uuid'])
  if q is None:raise ValueError('Power report references a removed/stale native UUID '+rec['uuid'])
  if q.GetNetname()!=rec['net']:raise ValueError('Native net disagrees with intended power-report net for '+rec['uuid']+': '+q.GetNetname()+' != '+rec['net'])
 layers=[board.GetLayerName(ly) for ly in board.GetEnabledLayers().CuStack()]
 dsn_layers=[q.values[1] for q in structure.children if q.head=='layer']
 if layers!=dsn_layers:raise ValueError('DSN/native copper layer stack mismatch')
 branch_specs=[];selected=set();target_pins={};selected_info=[]
 rows=report.get('kelvin',[])
 if len(rows)!=3 or {r.get('phase') for r in rows}!={'U','V','W'}:raise ValueError('Expected all three Kelvin report phases')
 placements={q.values[1]:q for q in descend(root.child('placement')) if q.head=='place'}
 for row in rows:
  phase=row['phase'];rs=row['RS'];ina=row['INA']
  for ref in [rs,ina]:
   if ref not in fps or ref not in placements:raise ValueError('Missing native/DSN placement '+ref)
   pp=placements[ref].values;at=[float(pp[2])/scale,-float(pp[3])/scale]
   if dist(at,xy(fps[ref].GetPosition()))>tol:raise ValueError('Stale DSN placement for '+ref)
  pads={q.GetNumber():q for q in fps[ina].Pads()}
  rs_pads={q.GetNumber():q for q in fps[rs].Pads()}
  for polarity,pin,rs_pin,net in [('positive','8','1',phase+'_SOURCE'),('negative','1','2','GND')]:
   if pads[pin].GetNetname()!=net or rs_pads[rs_pin].GetNetname()!=net:raise ValueError('Unexpected RS/INA physical pin net '+ina+'-'+pin)
   track_ids=row[polarity+'_track_uuids'];via_id=row[polarity+'_via_uuid'];ids=track_ids+[via_id]
   if any(q in selected for q in ids):raise ValueError('Repeated Kelvin UUID')
   selected.update(ids)
   for ident in ids:
    q=all_items.get(ident)
    if q is None:raise ValueError('Stale power report: native UUID missing '+ident)
    if not q.IsLocked() or q.GetNetname()!=net:raise ValueError('Kelvin item must remain locked on expected net: '+ident)
   if not isinstance(all_items[via_id],p.PCB_VIA) or any(isinstance(all_items[q],p.PCB_VIA) for q in track_ids):raise ValueError('Kelvin report track/via type mismatch')
   if any(all_items[q].GetClass()!='PCB_TRACK' for q in track_ids):raise ValueError('Arc Kelvin branch is not supported; refuse to approximate')
   if any(board.GetLayerName(all_items[q].GetLayer()) not in ['F.Cu','B.Cu'] for q in track_ids):raise ValueError('Kelvin branch unexpectedly uses an internal routing layer')
   # Actual endpoint coverage: both pins must be reached by the reported branch,
   # without relying on stale report coordinates or the whole GND cluster.
   def reaches(pad):
    return any(pad.IsOnLayer(all_items[t].GetLayer()) and pad.GetEffectiveShape(all_items[t].GetLayer()).Collide(v,0) for t in track_ids for v in [all_items[t].GetStart(),all_items[t].GetEnd()])
   if not reaches(pads[pin]) or not reaches(rs_pads[rs_pin]):raise ValueError('Reported branch does not reach actual RS/INA pad geometry')
   # The selected segments themselves must form one continuous branch through
   # the actual via. Never infer this from the global GND/SOURCE copper cluster.
   nodes=[];edges=[]
   for ident in track_ids:
    q=all_items[ident];i=len(nodes);nodes.extend([(q.GetLayer(),q.GetStart()),(q.GetLayer(),q.GetEnd())]);edges.append((i,i+1))
   via=all_items[via_id];base=len(nodes)
   nodes.extend((ly,via.GetPosition()) for ly in board.GetEnabledLayers().CuStack() if via.IsOnLayer(ly))
   edges.extend((base,j) for j in range(base+1,len(nodes)))
   parent=list(range(len(nodes)))
   def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
   def union(i,j):parent[find(i)]=find(j)
   for i,j in edges:union(i,j)
   for i,(ly,a) in enumerate(nodes):
    for j,(lz,b) in enumerate(nodes[:i]):
     if ly==lz and dist(xy(a),xy(b))<=tol:union(i,j)
   for pad in [pads[pin],rs_pads[rs_pin]]:
    hits=[i for i,(ly,a) in enumerate(nodes) if pad.IsOnLayer(ly) and pad.GetEffectiveShape(ly).Collide(a,0)]
    for i in hits[1:]:union(hits[0],i)
   if len({find(i) for i in range(len(nodes))})!=1:raise ValueError('Kelvin UUID set contains disconnected branch fragments for '+ina+'-'+pin)
   target_pins[ina+'-'+pin]=net
   branch_specs.append({'phase':phase,'polarity':polarity,'net':net,'tracks':track_ids,'via':via_id,'INA_pin':ina+'-'+pin,'RS_pin':rs+'-'+rs_pin})
 # Source-board/DSN equality proof uses all native fixed wiring, not only six
 # selected branches. Native UUIDs are authoritative; DSN has no UUID field.
 native_tracks=[];native_vias=[];native_by_key=collections.defaultdict(list)
 for ident,q in all_items.items():
  if isinstance(q,p.PCB_VIA):
   native_vias.append({'uuid':ident,'net':q.GetNetname(),'at':xy(q.GetPosition()),'diameter':p.ToMM(q.GetWidth(p.F_Cu)),'drill':p.ToMM(q.GetDrill()),'layers':[ly for ly in layers if q.IsOnLayer(board.GetLayerID(ly))]})
  else:
   if q.GetClass()!='PCB_TRACK':raise ValueError('Native arc wiring is unsupported; export a straight-segment routing candidate')
   item={'uuid':ident,'net':q.GetNetname(),'layer':board.GetLayerName(q.GetLayer()),'width':p.ToMM(q.GetWidth()),'a':xy(q.GetStart()),'b':xy(q.GetEnd())}
   native_tracks.append(item);native_by_key[key(item['net'],item['layer'],item['width'])].append(item)
 padsizes={}
 for stack in library.children:
  if stack.head!='padstack':continue
  circles=[q.values for q in descend(stack) if q.head=='circle']
  if circles:padsizes[stack.values[1]]={q[1]:float(q[2])/scale for q in circles}
 coverage=collections.defaultdict(list);via_matches={};wire_changes=[];removed_wire_count=0;split_wire_count=0
 wire_nodes=[q for q in wiring.children if q.head=='wire'];via_nodes=[q for q in wiring.children if q.head=='via'];unmodified_wire_spans=[]
 for wire in wire_nodes:
  path=wire.child('path');v=path.values
  if len(v)<7 or (len(v)-3)%2:raise ValueError('Unexpected DSN wire path form')
  layer=v[1];width=float(v[2])/scale;net=wire.child('net').values[1];points=[[float(v[i])/scale,-float(v[i+1])/scale] for i in range(3,len(v),2)]
  choices=native_by_key.get(key(net,layer,width),[]);keep=[];changed=False
  for a,b in zip(points,points[1:]):
   length=dist(a,b)
   if length<=tol:continue
   matched=[];remove=[]
   for item in choices:
    ov=overlap_segment(a,b,item['a'],item['b'],tol)
    if ov is None:continue
    matched.append(ov)
    start=point(a,b,ov[0]);end=point(a,b,ov[1]);iv=overlap_segment(item['a'],item['b'],start,end,tol)
    if iv:coverage[item['uuid']].append(iv)
    if item['uuid'] in selected:remove.append(ov)
   spans=merge(matched,tol)
   if not spans or spans[0][0]>tol or spans[-1][1]<length-tol or any(y[0]-x[1]>tol for x,y in zip(spans,spans[1:])):raise ValueError('Stale DSN/native wiring mismatch on '+net+' '+layer+' '+str([a,b]))
   rm=merge(remove,tol)
   if not rm:keep.append((a,b));continue
   changed=True;cursor=0
   for lo,hi in rm:
    if lo-cursor>tol:keep.append((point(a,b,cursor),point(a,b,lo)))
    cursor=max(cursor,hi)
   if length-cursor>tol:keep.append((point(a,b,cursor),b))
  if not changed:unmodified_wire_spans.append(source[wire.start:wire.end]);continue
  chunks=[]
  for a,b in keep:
   if chunks and dist(chunks[-1][-1],a)<=tol:chunks[-1].append(b)
   else:chunks.append([a,b])
  replacements=[]
  def number(z):return ('%.6f'%z).rstrip('0').rstrip('.') or '0'
  for pts in chunks:
   coordinates='  '.join(number(q[0]*scale)+' '+number(-q[1]*scale) for q in pts)
   newpath='(path '+v[1]+' '+v[2]+'  '+coordinates+')'
   replacements.append(source[wire.start:path.start]+newpath+source[path.end:wire.end])
  wire_changes.append((wire.start,wire.end,(eol+'    ').join(replacements)));removed_wire_count+=not chunks;split_wire_count+=bool(chunks)
 for item in native_tracks:
  length=dist(item['a'],item['b']);spans=merge(coverage[item['uuid']],tol)
  if length>tol and (not spans or spans[0][0]>tol or spans[-1][1]<length-tol or any(y[0]-x[1]>tol for x,y in zip(spans,spans[1:]))):raise ValueError('Native track missing from DSN export: '+item['uuid'])
 for node in via_nodes:
  v=node.values;stack=v[1];at=[float(v[2])/scale,-float(v[3])/scale];net=node.child('net').values[1];shape=padsizes.get(stack,{})
  matches=[q for q in native_vias if q['net']==net and dist(q['at'],at)<=tol and set(shape)==set(q['layers']) and all(abs(shape[ly]-q['diameter'])<=tol for ly in q['layers'])]
  if len(matches)!=1:raise ValueError('Stale or ambiguous DSN/native via '+str([net,at,stack]))
  ident=matches[0]['uuid']
  if ident in via_matches:raise ValueError('Duplicate DSN via instance '+ident)
  via_matches[ident]=node
  if ident in selected:wire_changes.append((node.start,node.end,''))
 if set(via_matches)!=set(q['uuid'] for q in native_vias):raise ValueError('Native via set is not completely represented in the DSN')
 # Remove only the already-fixed INA sense pads from SOURCE/GND net pin lists.
 net_nodes={q.values[1]:q for q in network.children if q.head=='net'};pin_changes=[];removed_pins=[]
 before_pinsets={name:[t.value for t in node.child('pins').tokens[1:]] for name,node in net_nodes.items()}
 for pin,net in target_pins.items():
  if net not in net_nodes:raise ValueError('Missing net '+net)
  pins=net_nodes[net].child('pins');tokens=[t for t in pins.tokens[1:] if t.value==pin]
  if len(tokens)!=1:raise ValueError('Expected exactly one still-unprotected sense pin '+pin+' on '+net)
  t=tokens[0];pin_changes.append((t.start,t.end,''));removed_pins.append({'pin':pin,'net':net})
 def number(z):return ('%.6f'%z).rstrip('0').rstrip('.') or '0'
 guards=[]
 for ident in sorted(selected):
  q=all_items[ident]
  if isinstance(q,p.PCB_VIA):at=xy(q.GetPosition());radius=p.ToMM(q.GetWidth(p.F_Cu))/2+args.guard_mm;polygon=guard_polygon(at,at,radius);guard_layers=layers
  else:radius=p.ToMM(q.GetWidth())/2+args.guard_mm;polygon=guard_polygon(xy(q.GetStart()),xy(q.GetEnd()),radius);guard_layers=[board.GetLayerName(q.GetLayer())]
  for layer in guard_layers:
   pts=polygon+[polygon[0]];coords='  '.join(number(a*scale)+' '+number(-b*scale) for a,b in pts)
   guards.append('    (keepout "kelvin_'+ident+'_'+layer+'" (polygon '+layer+' 0  '+coords+'))')
 changes=wire_changes+pin_changes+[(structure.end-1,structure.end-1,eol+eol.join(guards)+eol+'  ')]
 changes.sort(key=lambda q:q[0]);assert all(a[1]<=b[0] for a,b in zip(changes,changes[1:])), 'Overlapping text edits'
 output=source
 for start,end,text in reversed(changes):output=output[:start]+text+output[end:]
 final=parse(output);after_network=final.child('network');after_pinsets={q.values[1]:[t.value for t in q.child('pins').tokens[1:]] for q in after_network.children if q.head=='net'}
 expected={name:[pin for pin in pins if target_pins.get(pin)!=name] for name,pins in before_pinsets.items()}
 if after_pinsets!=expected:raise AssertionError('Unrelated network/pin list changed')
 if len(before_pinsets['GND'])-len(after_pinsets['GND'])!=3:raise AssertionError('Exactly three GND sense pins, not a ground net, must be removed')
 for ina in [r['INA'] for r in rows]:
  for pin in ['2','4']:
   if ina+'-'+pin not in after_pinsets['GND']:raise AssertionError('INA ordinary GND pin must remain routed')
 # Every wire not selected for modification must remain byte-identical.
 after_wire_texts=collections.Counter(output[n.start:n.end] for n in final.child('wiring').children if n.head=='wire')
 if collections.Counter(unmodified_wire_spans)-after_wire_texts:raise AssertionError('Non-Kelvin wire text changed')
 checks={'all_reported_fixed_geometry_and_nets_match':True,'all_reported_intended_net_UUIDs_match_native':True,'Kelvin_selected_branch_continuity':True,'all_native_track_geometry_matches_dsn':True,'all_native_vias_match_dsn':True,'only_six_selected_net_pins_removed':True,'ordinary_GND_and_SOURCE_pins_preserved':True,'non_Kelvin_wires_byte_identical':True,'native_board_unchanged':True,'input_dsn_unchanged':True,'input_report_unchanged':True}
 for path,h in before.items():
  if digest(path)!=h:raise RuntimeError('Input changed during protection operation: '+path)
 args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(output.encode('utf-8'))
 audit={'allow_routed_source':args.allow_routed_source,'fixed_geometry_checked_counts':{kind:len(report.get(kind,[])) for kind in ['tracks','vias','zones']},'board':str(args.board),'board_sha256':before[str(args.board)],'dsn':str(args.dsn),'dsn_sha256':before[str(args.dsn)],'power_report':str(args.power_report),'power_report_sha256':before[str(args.power_report)],'report_source_sha256':report.get('source_sha256'),'report_candidate':report.get('candidate'),'output':str(args.out),'output_sha256':digest(args.out),'units':unit,'native_match_tolerance_mm':tol,'guard_mm_per_side':args.guard_mm,'intended_power_report_uuid_count':len(intended_records),'selected_native_uuid_count':len(selected),'selected_native_track_count':sum(not isinstance(all_items[q],p.PCB_VIA) for q in selected),'selected_native_via_count':sum(isinstance(all_items[q],p.PCB_VIA) for q in selected),'dsn_wires_removed':removed_wire_count,'dsn_mixed_wires_rewritten':split_wire_count,'dsn_vias_removed':sum(uid in selected for uid in via_matches),'structure_keepouts_added':len(guards),'removed_pins':removed_pins,'native_kelvin_uuid_must_survive_SES_import':sorted(selected),'branches':branch_specs,'checks':checks,'note':'Routing-only transformation. Full native wiring is geometrically matched before editing, so an older DSN is rejected even if six Kelvin UUIDs still exist. Do not delete native locked branches when importing the SES; keep/check their UUID, net and geometry. A plane is never removed by this tool.'}
 audit_path=args.out.with_suffix(args.out.suffix+'.json');audit_path.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Protected Kelvin:',audit['selected_native_track_count'],'tracks +',audit['selected_native_via_count'],'vias;',len(guards),'keepouts;',len(removed_pins),'sense pins removed from router network only')
 print('Output',args.out,'audit',audit_path)
 return 0

if __name__=='__main__':raise SystemExit(main())

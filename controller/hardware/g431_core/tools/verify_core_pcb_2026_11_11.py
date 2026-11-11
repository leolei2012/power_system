"""Independent, read-only validation of the current 47-reference core PCB.

Load the saved PCB again; never trust builder objects or its success message.
Compare physical pad/net/value/DNP/footprint data to the actual exported XML and
every header/hole centre to the common mechanical contract. Native CLI DRC is
reported separately and remains required for copper clearance acceptance.
"""
from pathlib import Path
import argparse,collections,hashlib,json,math,xml.etree.ElementTree as E
import pcbnew as p

BASE=Path(__file__).resolve().parents[1]
REPO=BASE.parents[2]
MM=p.FromMM
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
XY=lambda q:(p.ToMM(q.x),p.ToMM(q.y))


def bbox(fp):
    fp.BuildCourtyardCaches()
    s=fp.GetCourtyard(p.B_CrtYd if fp.GetLayer()==p.B_Cu else p.F_CrtYd)
    bb=s.BBox() if s.OutlineCount() else fp.GetBoundingBox(False,False)
    return [p.ToMM(v) for v in [bb.GetLeft(),bb.GetTop(),bb.GetRight(),bb.GetBottom()]]


def overlap(a,z):
    return min(a[2],z[2])-max(a[0],z[0])>.001 and min(a[3],z[3])-max(a[1],z[1])>.001


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board',type=Path,default=BASE/'controller.kicad_pcb')
    ap.add_argument('--out',type=Path,default=BASE/'review/pcb_2026-11-11/pcb_check.json')
    ap.add_argument('--drc',type=Path)
    ap.add_argument('--require-connected',action='store_true')
    args=ap.parse_args();board_path=args.board.resolve();start_hash=sha(board_path)
    b=p.LoadBoard(str(board_path));b.BuildConnectivity()
    xml=BASE/'review/controller.net.xml';tree=E.parse(xml).getroot()
    comps={c.get('ref'):c for c in tree.findall('./components/comp')}
    expected={}
    for n in tree.findall('./nets/net'):
        for a in n.findall('node'):expected[a.get('ref'),a.get('pin')]=n.get('name')
    contract_path=REPO/'docs/pcb_stack_contract_rev_e.json'
    contract=json.loads(contract_path.read_text(encoding='utf-8'))
    all_fps=list(b.GetFootprints());counts=collections.Counter(f.GetReference() for f in all_fps)
    fps={f.GetReference():f for f in all_fps};errors=[]
    if any(v!=1 for v in counts.values()):errors.append(['duplicate references',dict(counts)])
    hole_refs={h['reference'] for h in contract['mounting_holes']}
    if set(fps)!=set(comps)|hole_refs:errors.append(['reference set',sorted(set(fps)^ (set(comps)|hole_refs))])
    if len(comps)!=47:errors.append(['expected physical source count',len(comps)])
    actual=collections.defaultdict(list);checks=[]
    for ref,c in comps.items():
        if ref not in fps:continue
        f=fps[ref];want_dnp=c.find("property[@name='dnp']") is not None
        if f.GetValue()!=c.findtext('value'):errors.append([ref,'value',f.GetValue(),c.findtext('value')])
        if f.GetFPID().GetUniStringLibId()!=c.findtext('footprint'):errors.append([ref,'footprint ID'])
        if f.IsDNP()!=want_dnp:errors.append([ref,'DNP'])
        for a in f.Pads():
            num=a.GetNumber()
            if not num:continue
            actual[ref,num].append(a.GetNetname())
            if (ref,num) not in expected:errors.append([ref,num,'extra physical pad'])
            elif a.GetNetname()!=expected[ref,num]:errors.append([ref,num,'pad-net mismatch',a.GetNetname(),expected[ref,num]])
        checks.append({'ref':ref,'footprint':f.GetFPID().GetUniStringLibId(),'DNP':f.IsDNP(),
                       'side':'B' if f.GetLayer()==p.B_Cu else 'F','courtyard':bbox(f)})
    for key in set(expected)-set(actual):errors.append([*key,'no physical footprint pad'])
    if b.GetCopperLayerCount()!=4:errors.append(['copper layers',b.GetCopperLayerCount()])
    if abs(p.ToMM(b.GetDesignSettings().GetBoardThickness())-1.6)>.0001:errors.append(['thickness'])
    header_checks=[]
    for ref,h in contract['headers'].items():
        f=fps[ref]
        if f.GetLayer()!=p.F_Cu or abs(f.GetOrientationDegrees())>.001:errors.append([ref,'must remain top and zero degrees'])
        for pad in f.Pads():
            if not pad.GetNumber():continue
            n=int(pad.GetNumber());row=(n-1)//2
            want=(h['pad_1_x'] if n%2 else h['pad_2_x'],h['pad_1_y']+row*h['row_step_y'])
            at=XY(pad.GetPosition())
            if math.dist(at,want)>.00001:errors.append([ref,n,'mechanical mating coordinate',at,want])
            header_checks.append([ref,n,*at])
    for ref in ['U30','SW2','SW3']:
        if fps[ref].GetLayer()!=p.F_Cu:errors.append([ref,'must remain top'])
    hole_checks=[]
    for h in contract['mounting_holes']:
        f=fps[h['reference']];at=XY(f.GetPosition());pads=list(f.Pads())
        if math.dist(at,(h['x'],h['y']))>.00001:errors.append([h['reference'],'hole position'])
        if len(pads)!=1 or pads[0].GetAttribute()!=p.PAD_ATTRIB_NPTH or abs(p.ToMM(pads[0].GetDrillSize().x)-h['drill'])>.00001:errors.append([h['reference'],'hole type/drill'])
        hole_checks.append({'ref':h['reference'],'xy':at,'drill':p.ToMM(pads[0].GetDrillSize().x)})
    edge_points={}
    for e in b.GetDrawings():
        if e.GetLayer()==p.Edge_Cuts and isinstance(e,p.PCB_SHAPE):
            for at in [e.GetStart(),e.GetEnd()]:edge_points[XY(at)]=True
    if set(edge_points)!={(100.,100.),(160.,100.),(160.,160.),(100.,160.)}:errors.append(['outline vertices',list(edge_points)])
    collisions=[];outside=[]
    for i,f in enumerate(all_fps):
        bb=bbox(f)
        if bb[0]<100 or bb[1]<100 or bb[2]>160 or bb[3]>160:outside.append([f.GetReference(),bb])
        for z in all_fps[i+1:]:
            if f.GetLayer()==z.GetLayer() and overlap(bb,bbox(z)):collisions.append([f.GetReference(),z.GetReference()])
    if collisions:errors.append(['same-side courtyard collisions',collisions])
    if outside:errors.append(['outside outline',outside])
    referenced_models=[];missing=[];no_models=[]
    for ref,f in fps.items():
        if not len(f.Models()) and ref in comps:no_models.append(ref)
        for m in f.Models():
            name=m.m_Filename
            if name.startswith('${KIPRJMOD}'):
                actual_path=Path(name.replace('${KIPRJMOD}',str(board_path.parent)))
                exists=actual_path.is_file()
                referenced_models.append({'ref':ref,'saved_path':name,'resolved':str(actual_path.resolve()),'exists':exists})
                if not exists:missing.append([ref,name])
    if missing:errors.append(['persisted project-relative 3D model path missing',missing])
    tracks=[];vias=[];layer_lengths=collections.Counter();net_lengths=collections.Counter()
    for t in b.GetTracks():
        if isinstance(t,p.PCB_VIA):vias.append(t)
        else:
            tracks.append(t);length=math.dist(XY(t.GetStart()),XY(t.GetEnd()))
            layer_lengths[p.LayerName(t.GetLayer())]+=length;net_lengths[t.GetNetname()]+=length
            if t.GetLayer()==p.In1_Cu and t.GetNetname()!='GND':errors.append(['signal on continuous reference layer',t.m_Uuid.AsString()])
    gap_count=b.GetConnectivity().GetUnconnectedCount(False)
    if args.require_connected and gap_count:errors.append(['routing not complete',gap_count])
    drc=None
    if args.drc:
        raw=json.loads(args.drc.read_text(encoding='utf-8'))
        drc={'path':str(args.drc),'violations':len(raw.get('violations',[])),
             'electrical_geometry_errors':[v for v in raw.get('violations',[]) if v.get('severity')=='error'],
             'unconnected_items':len(raw.get('unconnected_items',[])),
             'schematic_parity':len(raw.get('schematic_parity',[])),
             'categories':dict(collections.Counter(v.get('type') for v in raw.get('violations',[])))}
        if drc['electrical_geometry_errors']:errors.append(['native DRC has electrical/geometry errors',len(drc['electrical_geometry_errors'])])
    assert sha(board_path)==start_hash,'Read-only checker changed source PCB'
    report={'result':'FAIL' if errors else 'PASS','routing_status':'CONNECTED REVIEW' if not gap_count else 'ROUTING INCOMPLETE',
            'source_pcb':str(board_path),'source_sha256':start_hash,'xml_sha256':sha(xml),'contract_sha256':sha(contract_path),
            'physical_schematic_refs':len(comps),'footprints_with_holes':len(fps),
            'symbol_physical_pin_nodes':len(expected),'numbered_pad_occurrences':sum(map(len,actual.values())),
            'duplicate_numbered_pads':{'.'.join(k):len(v) for k,v in actual.items() if len(v)>1},
            'DNP_refs':sorted(r for r,c in comps.items() if c.find("property[@name='dnp']") is not None),
            'header_contacts':header_checks,'mounting_holes':hole_checks,'copper_layers':b.GetCopperLayerCount(),
            'size_mm':[60,60],'board_thickness_mm':1.6,'courtyard_collisions':collisions,'outside':outside,
            'tracks':len(tracks),'vias':len(vias),'native_unconnected':gap_count,
            'layer_length_mm':dict(layer_lengths),'net_track_length_mm':dict(net_lengths),
            'persisted_project_relative_models':referenced_models,'no_3d_model_refs':sorted(no_models),
            'native_drc':drc,'component_checks':checks,'errors':errors,
            'limits':['Review PCB only; no fabrication/assembly release.',
                      'Library/pad mapping, mechanical coordinate checks and native DRC do not establish thermal or prototype validation.']}
    args.out.parent.mkdir(exist_ok=True,parents=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    args.out.with_suffix('.txt').write_text(json.dumps({k:v for k,v in report.items() if k not in ['component_checks','header_contacts','net_track_length_mm','persisted_project_relative_models']},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['result','routing_status','physical_schematic_refs','numbered_pad_occurrences','tracks','vias','native_unconnected','courtyard_collisions','errors']},indent=2))
    raise SystemExit(1 if errors else 0)


if __name__=='__main__':main()

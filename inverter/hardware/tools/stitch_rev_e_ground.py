"""Add conservative ground-plane stitches on an isolated Rev E candidate.

The planes and critical Kelvin geometry are read-only. Vias are adjacent to
surface pads, outside mounting margins, and checked against actual copper on
all layers. Native refill/DRC is still required after this authoring step.
"""
from pathlib import Path
import argparse,json,math,fnmatch,shutil,time
import pcbnew as p
from reve_local_astar import route
from compact_route import fixed_geometry
ROOT=Path(__file__).resolve().parents[3];MM=p.FromMM
V=lambda xy:p.VECTOR2I(MM(xy[0]),MM(xy[1]))
xy=lambda q:(p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y))
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--board',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
ap.add_argument('--net',default='GND',choices=['GND','+3V3_INV'])
ap.add_argument('--add-quiet-3v3-plane',action='store_true',help='In3 low-voltage area only; existing copper/keepouts retain priority.')
ap.add_argument('--logic-plane-x-max',type=float,default=134.,help='Conservative right boundary of the quiet In3 logic pour.')
a=ap.parse_args();assert a.board.resolve()!=a.out.resolve()
a.out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.board,a.out)
pro=a.board.with_suffix('.kicad_pro').read_bytes();a.out.with_suffix('.kicad_pro').write_bytes(pro)
for f in ['sym-lib-table','fp-lib-table']:
    if (a.board.parent/f).exists():shutil.copyfile(a.board.parent/f,a.out.parent/f)
b=p.LoadBoard(str(a.out));b.BuildConnectivity();fixed=fixed_geometry(b)
fps={f.GetReference():f for f in b.GetFootprints()};layers=list(b.GetEnabledLayers().CuStack())
net=b.FindNet(a.net)
if a.add_quiet_3v3_plane:
    assert a.net=='+3V3_INV'
    assert not any(z.GetZoneName()=='REV E / quiet 3V3 logic supply' for z in b.Zones())
    # Preserve the already-qualified bus sheet when these areas overlap.
    # The logic sheet must never carve a higher-priority channel through VBUS.
    for existing in b.Zones():
        if not existing.GetIsRuleArea() and existing.IsOnLayer(p.In3_Cu) and existing.GetNetname()=='VBUS':
            existing.SetAssignedPriority(max(2,existing.GetAssignedPriority()))
    z=p.ZONE(b);ls=p.LSET();ls.AddLayer(p.In3_Cu);z.SetLayerSet(ls);z.SetNet(net)
    z.SetZoneName('REV E / quiet 3V3 logic supply');z.SetLocalClearance(MM(.20));z.SetMinThickness(MM(.20))
    z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetAssignedPriority(1)
    z.Outline().NewOutline()
    assert 130<=a.logic_plane_x_max<=142.5
    for v in [(100.75,100.75),(a.logic_plane_x_max,100.75),(a.logic_plane_x_max,159.25),(100.75,159.25)]:z.Outline().Append(V(v))
    b.Add(z);p.ZONE_FILLER(b).Fill(b.Zones());b.BuildConnectivity()
master=next(q for q in fps['J3'].Pads() if q.GetNumber()=='2') if a.net=='GND' else next(q for q in fps['C17'].Pads() if q.GetNumber()=='1')
assert master.GetNetname()==a.net
rec=json.loads((ROOT/'inverter/hardware/review/pcb_rev_e_2026-11-11/power/power_copper.json').read_text(encoding='utf-8'))
protected=set(rec['protected_kelvin_uuids'])
protected.update(q.m_Uuid.AsString() for ref in ['U10','U11','U12'] for q in fps[ref].Pads() if q.GetNumber() in ['1','8'])
settings=json.loads(pro)['net_settings'];classes={c['name']:c['clearance'] for c in settings['classes']}
def clearance(n):return next((classes[v['netclass']] for v in settings['netclass_patterns'] if fnmatch.fnmatchcase(n,v['pattern'])),classes['Default'])
objects=[q for f in b.GetFootprints() for q in f.Pads()]+list(b.GetTracks())
zones=[z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname()==a.net]
def in_plane(v):
    return any(z.IsOnLayer(l) and z.HasFilledPolysForLayer(l) and z.GetFilledPolysList(l).Collide(V(v)) for z in zones for l in ([p.In1_Cu,p.In4_Cu] if a.net=='GND' else [p.In3_Cu]))
def safe_via(v):
    if not (100.9<=v[0]<=159.1 and 100.9<=v[1]<=159.1):return False
    if any(math.dist(v,h)<3.25 for h in [(104,104),(156,104),(104,156),(156,156)]):return False
    if not in_plane(v):return False
    shape=p.SHAPE_CIRCLE(V(v),MM(.3))
    for o in objects:
        uid=o.m_Uuid.AsString()
        # Hole-to-hole separation applies even where the copper net is equal.
        drill=p.ToMM(o.GetDrillValue()) if isinstance(o,p.PCB_VIA) else max(p.ToMM(o.GetDrillSize().x),p.ToMM(o.GetDrillSize().y)) if isinstance(o,p.PAD) else 0
        if drill and math.dist(v,xy(o))<.15+drill/2+.27:return False
        if o.GetNetname()==a.net and uid not in protected:continue
        cl=max(.15,clearance(o.GetNetname()),.25 if uid in protected else 0)
        bb=o.GetBoundingBox();d=MM(.3+cl)
        if v[0]*1e6<bb.GetX()-d or v[0]*1e6>bb.GetRight()+d or v[1]*1e6<bb.GetY()-d or v[1]*1e6>bb.GetBottom()+d:continue
        if any(o.IsOnLayer(l) and o.GetEffectiveShape(l).Collide(shape,MM(max(cl,p.ToMM(o.GetOwnClearance(l))))) for l in layers):return False
    return True
def connected():return {q.m_Uuid.AsString() for q in b.GetConnectivity().GetConnectedItems(master)}|{master.m_Uuid.AsString()}
done=connected();pending=[]
for ref,f in fps.items():
    for q in f.Pads():
        if not q.GetNumber() or q.GetNetname()!=a.net or q.m_Uuid.AsString() in done or q.GetAttribute()!=p.PAD_ATTRIB_SMD:continue
        # Amplifier negative inputs are deliberate single-point Kelvin returns.
        if ref in ['U10','U11','U12'] and q.GetNumber()=='1':continue
        pending.append((ref,q))
report={'source':str(a.board),'net':a.net,'added_quiet_3v3_plane':a.add_quiet_3v3_plane,'added':[],'failed':[],'initial_unconnected_SMD_pads':len(pending)}
for ref,q in pending:
    if q.m_Uuid.AsString() in connected():continue
    start=xy(q);ly=p.F_Cu if q.IsOnLayer(p.F_Cu) else p.B_Cu;layer=b.GetLayerName(ly);success=False
    for radius in [.8,1.,1.25,1.5,1.8,2.2,2.8]:
        for k in range(16):
            v=(round(start[0]+radius*math.cos(k*math.pi/8),3),round(start[1]+radius*math.sin(k*math.pi/8),3))
            if not safe_via(v):continue
            pts,detail=route(b,a.net,layer,.20,start,v,margin=1.2,limit=.4,step=.1,protected_uuids=protected)
            if not pts:continue
            tracks=[]
            for x,y in zip(pts,pts[1:]):
                if math.dist(x,y)<1e-6:continue
                t=p.PCB_TRACK(b);t.SetStart(V(x));t.SetEnd(V(y));t.SetLayer(ly);t.SetWidth(MM(.20));t.SetNet(net);b.Add(t);objects.append(t);tracks.append(t.m_Uuid.AsString())
            via=p.PCB_VIA(b);via.SetPosition(V(v));via.SetWidth(MM(.6));via.SetDrill(MM(.3));via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetNet(net);b.Add(via);objects.append(via)
            b.BuildConnectivity();report['added'].append({'ref':ref,'pin':q.GetNumber(),'net':a.net,'layer':layer,'width':.2,'points':pts,'via':v,'tracks':tracks,'via_uuid':via.m_Uuid.AsString()});success=True;break
        if success:break
    if not success:report['failed'].append(ref+'.'+q.GetNumber())
    print(ref,q.GetNumber(),'stitch' if success else 'no safe access',flush=True)
assert fixed_geometry(b)==fixed
p.SaveBoard(str(a.out),b);a.out.with_suffix('.kicad_pro').write_bytes(pro)
a.out.with_suffix('.stitches.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('Added',len(report['added']),a.net,'stitches; failed',len(report['failed']),flush=True)

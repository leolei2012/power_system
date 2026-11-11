"""Conservative same-layer authoring for native airwires on private PCB copies."""
from pathlib import Path
import argparse,shutil,json,math,fnmatch,hashlib
import pcbnew as p
from compact_route import fixed_geometry
from reve_local_astar import route
ROOT=Path(__file__).resolve().parents[3]
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--board',type=Path,required=True);ap.add_argument('--drc',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
ap.add_argument('--max-length',type=float,default=5);ap.add_argument('--seconds-per-gap',type=float,default=.7)
a=ap.parse_args();assert a.board.resolve()!=a.out.resolve();a.out.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(a.board,a.out);pro=a.board.with_suffix('.kicad_pro').read_bytes();a.out.with_suffix('.kicad_pro').write_bytes(pro)
for f in ['sym-lib-table','fp-lib-table']:
    if (a.board.parent/f).exists():shutil.copyfile(a.board.parent/f,a.out.parent/f)
b=p.LoadBoard(str(a.out));b.BuildConnectivity();fixed=fixed_geometry(b)
items={q.m_Uuid.AsString():q for f in b.GetFootprints() for q in f.Pads()};items.update({q.m_Uuid.AsString():q for q in b.GetTracks()})
rec=json.loads((ROOT/'inverter/hardware/review/pcb_rev_e_2026-11-11/power/power_copper.json').read_text(encoding='utf-8'));protected=set(rec['protected_kelvin_uuids'])
ns=json.loads(pro)['net_settings'];classes={c['name']:c for c in ns['classes']}
def cls(net):return next((classes[x['netclass']] for x in ns['netclass_patterns'] if fnmatch.fnmatchcase(net,x['pattern'])),classes['Default'])
def xy(v):return p.ToMM(v.x),p.ToMM(v.y)
def points(obj,peer):
    if isinstance(obj,p.PCB_VIA) or isinstance(obj,p.PAD):return [xy(obj.GetPosition())]
    st,en=xy(obj.GetStart()),xy(obj.GetEnd());other=xy(peer.GetPosition());dx,dy=en[0]-st[0],en[1]-st[1];ll=dx*dx+dy*dy
    t=max(0,min(1,((other[0]-st[0])*dx+(other[1]-st[1])*dy)/ll)) if ll else 0
    return [st,en,(st[0]+t*dx,st[1]+t*dy)]
gaps=[]
for gap in json.loads(a.drc.read_text(encoding='utf-8'))['unconnected_items']:
    if len(gap['items'])!=2:continue
    uu=[x['uuid'] for x in gap['items']]
    if any(u not in items or u in protected for u in uu):continue
    x,y=[items[u] for u in uu];nn=x.GetNetname()
    if nn!=y.GetNetname() or nn in ['GND','+3V3_INV'] or cls(nn)['name']=='HV':continue
    pairs=sorted([(math.dist(u,v),u,v) for u in points(x,y) for v in points(y,x)])
    if pairs[0][0]<=a.max_length:gaps.append((pairs[0][0],x,y,pairs,nn))
report={'source':str(a.board),'source_sha256':hashlib.sha256(a.board.read_bytes()).hexdigest(),'added':[],'failed':[]}
for dist,x,y,pairs,nn in sorted(gaps,key=lambda v:v[0]):
    if y.m_Uuid.AsString() in {q.m_Uuid.AsString() for q in b.GetConnectivity().GetConnectedItems(x)}:continue
    width=cls(nn)['track_width']
    if nn.endswith('_SOURCE'):width=max(width,.30)
    ok=False
    for ly in [p.F_Cu,p.B_Cu,p.In2_Cu,p.In3_Cu]:
        if not (x.IsOnLayer(ly) and y.IsOnLayer(ly)):continue
        for _,start,end in pairs[:3]:
            pts,detail=route(b,nn,b.GetLayerName(ly),width,start,end,margin=2,limit=a.seconds_per_gap,step=.1,protected_uuids=protected)
            if not pts:continue
            # All authoring geometry stays inside the current board margins.
            if any(not(100.5+width/2<=u<=159.5-width/2 and 100.5+width/2<=v<=159.5-width/2) for u,v in pts):continue
            ids=[]
            for st,en in zip(pts,pts[1:]):
                if math.dist(st,en)<1e-6:continue
                t=p.PCB_TRACK(b);t.SetStart(p.VECTOR2I(p.FromMM(st[0]),p.FromMM(st[1])));t.SetEnd(p.VECTOR2I(p.FromMM(en[0]),p.FromMM(en[1])));t.SetLayer(ly);t.SetWidth(p.FromMM(width));t.SetNet(x.GetNet());b.Add(t);ids.append(t.m_Uuid.AsString())
            b.BuildConnectivity();report['added'].append({'net':nn,'width':width,'layer':b.GetLayerName(ly),'points':pts,'tracks':ids,'endpoints':[x.m_Uuid.AsString(),y.m_Uuid.AsString()]});ok=True;break
        if ok:break
    if not ok:report['failed'].append({'net':nn,'distance':dist,'endpoints':[x.m_Uuid.AsString(),y.m_Uuid.AsString()]})
    print(nn,'joined' if ok else 'blocked',round(dist,3),flush=True)
assert fixed==fixed_geometry(b)
p.SaveBoard(str(a.out),b);a.out.with_suffix('.kicad_pro').write_bytes(pro)
a.out.with_suffix('.local_gaps.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('Joined',len(report['added']),'gaps; blocked',len(report['failed']),flush=True)

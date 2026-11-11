"""Extract a reviewed private native copper delta against a frozen baseline."""
from compact_route import *

def geometry(t):
    if isinstance(t,p.PCB_VIA):return ('via',t.GetNetname(),xy(t),t.GetWidth(p.F_Cu),t.GetDrillValue(),t.TopLayer(),t.BottomLayer(),t.IsLocked())
    return ('track',t.GetNetname(),t.GetLayer(),xy_start(t),xy_end(t),t.GetWidth(),t.IsLocked())
def xy_start(t):return (p.ToMM(t.GetStart().x),p.ToMM(t.GetStart().y))
def xy_end(t):return (p.ToMM(t.GetEnd().x),p.ToMM(t.GetEnd().y))
def footprint(f):
    return (f.GetFPIDAsString(),xy(f),f.GetOrientationDegrees(),f.IsFlipped(),f.IsDNP(),sorted((a.GetNumber(),xy(a),a.GetNetname()) for a in f.Pads()))
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',type=Path,required=True);ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
base=p.LoadBoard(str(args.base));candidate=p.LoadBoard(str(args.candidate))
assert {f.GetReference():footprint(f) for f in base.GetFootprints()}=={f.GetReference():footprint(f) for f in candidate.GetFootprints()},'Footprints/pads changed'
assert fixed_geometry(base).items()<=fixed_geometry(candidate).items(),'Original locked copper changed'
assert json.loads(args.base.with_suffix('.kicad_pro').read_text(encoding='utf-8'))==json.loads(args.candidate.with_suffix('.kicad_pro').read_text(encoding='utf-8')),'Project rules changed'
old={t.m_Uuid.AsString():t for t in base.GetTracks()};new={t.m_Uuid.AsString():t for t in candidate.GetTracks()}
ripup=[uid for uid,t in old.items() if uid not in new or geometry(t)!=geometry(new[uid])]
assert not any(old[uid].IsLocked() for uid in ripup)
patch={'source_sha':hashlib.sha256(args.base.read_bytes()).hexdigest(),'base':str(args.base),'candidate':str(args.candidate),'candidate_sha256':hashlib.sha256(args.candidate.read_bytes()).hexdigest(),'ripup_uuids':ripup,'paths':[],'vias':[],'placements':{}}
for uid,t in new.items():
    if uid in old and geometry(t)==geometry(old[uid]):continue
    if isinstance(t,p.PCB_VIA):
        assert t.TopLayer()==p.F_Cu and t.BottomLayer()==p.B_Cu
        patch['vias'].append({'net':t.GetNetname(),'point':xy(t),'diameter':p.ToMM(t.GetWidth(p.F_Cu)),'drill':p.ToMM(t.GetDrillValue()),'locked':t.IsLocked()})
    else:patch['paths'].append({'net':t.GetNetname(),'layer':candidate.GetLayerName(t.GetLayer()),'points':[xy_start(t),xy_end(t)],'width':p.ToMM(t.GetWidth()),'locked':t.IsLocked()})
args.out.write_text(json.dumps(patch,indent=2)+'\n',encoding='utf-8');print('Extracted',len(ripup),'rip-ups',len(patch['paths']),'segments',len(patch['vias']),'vias')

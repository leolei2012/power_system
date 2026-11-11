from pathlib import Path
import json,shutil,sys,argparse
import pcbnew as p
ROOT=Path(__file__).resolve().parents[5];R=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'inverter/hardware/tools'))
from compact_route import fixed_geometry
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=R/'local_gaps/inverter.kicad_pcb');ap.add_argument('--out',type=Path,default=R/'local_bb_merge/inverter.kicad_pcb');args=ap.parse_args()
P=args.source;O=args.out;assert P.resolve()!=O.resolve();O.parent.mkdir(exist_ok=True)
shutil.copyfile(P,O);pro=P.with_suffix('.kicad_pro').read_bytes();O.with_suffix('.kicad_pro').write_bytes(pro)
for f in ['sym-lib-table','fp-lib-table']:shutil.copyfile(P.parent/f,O.parent/f)
b=p.LoadBoard(str(O));fixed=fixed_geometry(b);d=json.loads((Path(__file__).with_name('patch.json')).read_text(encoding='utf-8'));made=[]
for item in d['paths']:
    if not item['net'].startswith('/Driver supply/BB_'):continue
    if item.get('endpoint_refs')==['U2.14','U2.12']:continue # already closed locally
    for a,c in zip(item['points'],item['points'][1:]):
        t=p.PCB_TRACK(b);t.SetStart(p.VECTOR2I(p.FromMM(a[0]),p.FromMM(a[1])));t.SetEnd(p.VECTOR2I(p.FromMM(c[0]),p.FromMM(c[1])));t.SetWidth(p.FromMM(item['width']));t.SetLayer(b.GetLayerID(item['layer']));t.SetNet(b.FindNet(item['net']));b.Add(t);made.append(t.m_Uuid.AsString())
for item in d['vias']:
    v=p.PCB_VIA(b);v.SetPosition(p.VECTOR2I(p.FromMM(item['x']),p.FromMM(item['y'])));v.SetWidth(p.FromMM(item['diameter']));v.SetDrill(p.FromMM(item['drill']));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(item['net']));b.Add(v);made.append(v.m_Uuid.AsString())
assert fixed_geometry(b)==fixed;b.BuildConnectivity();p.SaveBoard(str(O),b);O.with_suffix('.kicad_pro').write_bytes(pro)
(O.parent/'added.json').write_text(json.dumps(made,indent=2)+'\n',encoding='utf-8');print('Added',len(made),'objects')

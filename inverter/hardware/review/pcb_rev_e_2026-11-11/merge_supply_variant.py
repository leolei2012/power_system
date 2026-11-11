"""Private experiment: broaden quiet logic plane; validate each added branch."""
from pathlib import Path
import pcbnew as p,json,shutil
R=Path(__file__).resolve().parent;S=R/'hole_cleanup/inverter.kicad_pcb';O=R/'supply_variant_merge/inverter.kicad_pcb';O.parent.mkdir(exist_ok=True)
shutil.copyfile(S,O);pro=S.with_suffix('.kicad_pro').read_bytes();O.with_suffix('.kicad_pro').write_bytes(pro)
for f in ['sym-lib-table','fp-lib-table']:shutil.copyfile(S.parent/f,O.parent/f)
b=p.LoadBoard(str(O));by={t.m_Uuid.AsString():t for t in b.GetTracks()};b.Delete(by['c792b6ac-fbe6-464a-b062-6f086d4eba0d'])
z=next(z for z in b.Zones() if z.GetZoneName()=='REV E / quiet 3V3 logic supply')
z.Outline().RemoveAllContours();z.Outline().NewOutline()
V=lambda xy:p.VECTOR2I(p.FromMM(xy[0]),p.FromMM(xy[1]))
for v in [(100.75,100.75),(142.5,100.75),(142.5,159.25),(100.75,159.25)]:z.Outline().Append(V(v))
small=json.loads((R/'supply_stitch/inverter.stitches.json').read_text(encoding='utf-8'));large=json.loads((R/'supply_stitch_wide/inverter.stitches.json').read_text(encoding='utf-8'))
already={(i['ref'],i['pin']) for i in small['added']};records=[]
for row in large['added']:
    if (row['ref'],row['pin']) in already:continue
    ids=[]
    for a,c in zip(row['points'],row['points'][1:]):
        t=p.PCB_TRACK(b);t.SetStart(V(a));t.SetEnd(V(c));t.SetLayer(b.GetLayerID(row['layer']));t.SetWidth(p.FromMM(row['width']));t.SetNet(b.FindNet(row['net']));b.Add(t);ids.append(t.m_Uuid.AsString())
    v=p.PCB_VIA(b);v.SetPosition(V(row['via']));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(row['net']));b.Add(v);ids.append(v.m_Uuid.AsString())
    records.append({'ref':row['ref'],'pin':row['pin'],'uuids':ids})
b.BuildConnectivity();p.SaveBoard(str(O),b);O.with_suffix('.kicad_pro').write_bytes(pro)
(O.parent/'branches.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8');print('Added',len(records),'branches')

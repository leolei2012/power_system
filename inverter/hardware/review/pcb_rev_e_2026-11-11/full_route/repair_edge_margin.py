"""Move only the three ordinary +3V3_INV trace endpoints 35.2 um inward."""
from pathlib import Path
import pcbnew as p, json, shutil
P=Path(__file__).with_name('inverter.kicad_pcb')
shutil.copyfile(P,P.with_name('before_edge_margin.kicad_pcb'))
b=p.LoadBoard(str(P));changes=[];pro=P.with_suffix('.kicad_pro').read_bytes()
for t in b.GetTracks():
    if isinstance(t,p.PCB_VIA) or t.IsLocked() or t.GetNetname()!='+3V3_INV':continue
    for end in ['Start','End']:
        v=getattr(t,'Get'+end)()
        if abs(p.ToMM(v.x)-100.5648)<.0001:
            old=[p.ToMM(v.x),p.ToMM(v.y)];v.x=p.FromMM(100.60);getattr(t,'Set'+end)(v)
            changes.append({'uuid':t.m_Uuid.AsString(),'end':end,'before':old,'after':[p.ToMM(v.x),p.ToMM(v.y)]})
assert len(changes)==4,len(changes)
b.BuildConnectivity();p.SaveBoard(str(P),b);P.with_suffix('.kicad_pro').write_bytes(pro)
P.with_name('edge_margin_repairs.json').write_text(json.dumps(changes,indent=2)+'\n',encoding='utf-8')
print('Adjusted',len(changes),'endpoints; raw gaps',b.GetConnectivity().GetUnconnectedCount(False))

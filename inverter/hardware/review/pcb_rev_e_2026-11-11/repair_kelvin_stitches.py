"""Drop three experimental stitches before regenerating guarded GND fanout."""
from pathlib import Path
import json,shutil
import pcbnew as p
R=Path(__file__).resolve().parent;S=R/'local_gaps_long/inverter.kicad_pcb';O=R/'kelvin_repair_input/inverter.kicad_pcb'
O.parent.mkdir(exist_ok=True);shutil.copyfile(S,O);pro=S.with_suffix('.kicad_pro').read_bytes();O.with_suffix('.kicad_pro').write_bytes(pro)
for f in ['sym-lib-table','fp-lib-table']:shutil.copyfile(S.parent/f,O.parent/f)
b=p.LoadBoard(str(O));data=json.loads((R/'ground_stitch_fixed/inverter.stitches.json').read_text(encoding='utf-8'));bad=[v for v in data['added'] if (v['ref'],v['pin']) in [('U10','2'),('U12','2'),('U11','4')]]
assert len(bad)==3;ids={u for v in bad for u in v['tracks']+[v['via_uuid']]};existing={t.m_Uuid.AsString():t for t in b.GetTracks()}
for u in ids:b.Delete(existing[u])
b.BuildConnectivity();p.SaveBoard(str(O),b);O.with_suffix('.kicad_pro').write_bytes(pro)
(O.parent/'removed_branches.json').write_text(json.dumps(bad,indent=2)+'\n',encoding='utf-8');print('Removed',len(ids),'new ordinary copper items in',len(bad),'branches')

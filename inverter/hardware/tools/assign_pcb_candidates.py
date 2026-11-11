"""Assign only the explicitly recorded mechanical footprint candidates to empty fields."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import sexpdata as sx

B=Path(__file__).resolve().parents[1]
mapping=json.loads((B/'tools/pcb_footprint_candidates.json').read_text(encoding='utf-8'))['footprint_map']
snapshot=B.parent/'history/rev_b_before_pcb_2026-11-06.zip'
if not snapshot.exists():
    files=list(B.glob('*.kicad_sch'))+list(B.glob('*.kicad_pro'))+list(B.glob('*.kicad_sym'))
    files += [B/'review/inverter.net.xml',B/'bom/bom.csv',B/'review/erc.rpt',B/'review/readability_equivalence.json']
    with ZipFile(snapshot,'w',ZIP_DEFLATED) as z:
        for file in files:z.write(file,'hardware/'+file.relative_to(B).as_posix())

def children(a,name):return [v for v in a if isinstance(v,list) and v and str(v[0])==name]

seen=set()
for file in B.glob('*.kicad_sch'):
    data=sx.load(file.open(encoding='utf-8'));changed=False
    for sym in children(data,'symbol'):
        fields={v[1]:v for v in children(sym,'property')}
        ref=fields['Reference'][2]
        if ref not in mapping:continue
        assert 'Footprint' in fields,(ref,'missing field')
        assert fields['Footprint'][2] in ['',mapping[ref]],(ref,'already different footprint')
        fields['Footprint'][2]=mapping[ref];seen.add(ref);changed=True
    if changed:file.write_text('('+str(data[0])+'\n'+'\n'.join(sx.dumps(v) if isinstance(v,list) else str(v) for v in data[1:])+')\n',encoding='utf-8')
assert seen==set(mapping),set(mapping)-seen
print('Assigned',len(seen),'provisional mechanical footprints; no electrical fields changed.')

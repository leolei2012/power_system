"""Repair owning-project relative 3D paths without changing electrical CAD.

Missing model files are reported; no substitute body is silently presented as
an exact component. Use on a private preview or on the final owning PCB.
"""
from build_pcb import *
import argparse
import os

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--board',type=Path,default=BOARD_PATH)
ap.add_argument('--report',type=Path,default=REVIEW/'compact_model_audit.json')
args=ap.parse_args();target=args.board.resolve();pro=target.with_suffix('.kicad_pro')
contents=pro.read_bytes();board=p.LoadBoard(str(target));changes=[];missing=[]
shared=B.parents[2]/'kicad_library/3dmodels'
standard=Path('C:/Program Files/KiCad/10.0/share/kicad/3dmodels')
prefix='${KIPRJMOD}/'+Path(os.path.relpath(shared,target.parent)).as_posix()+'/'
for f in board.GetFootprints():
    for model in f.Models():
        before=model.m_Filename
        if 'kicad_library/3dmodels/' in before:
            model.m_Filename=prefix+before.split('kicad_library/3dmodels/',1)[1]
        if model.m_Filename!=before:changes.append({'ref':f.GetReference(),'before':before,'after':model.m_Filename})
        actual=model.m_Filename.replace('${KIPRJMOD}',target.parent.as_posix()).replace('${KICAD10_3DMODEL_DIR}',standard.as_posix())
        if not Path(actual).is_file():missing.append({'ref':f.GetReference(),'model':model.m_Filename})
for t in board.GetDrawings():
    if isinstance(t,p.PCB_TEXT) and t.GetText()=='INV60 / REV C / PCB0.2':
        t.SetLayer(p.F_Fab);t.SetTextSize(V(.8,.8))
p.SaveBoard(str(target),board);pro.write_bytes(contents)
# KiCad 10's Models() iterator exposes value copies. Persist model filenames in
# the native text too; pad/track/zone geometry is untouched by these exact fields.
source=target.read_text(encoding='utf-8')
for item in changes:
    source=source.replace('(model '+json.dumps(item['before']), '(model '+json.dumps(item['after']))
target.write_text(source,encoding='utf-8')
for item in changes:
    assert '(model '+json.dumps(item['before']) not in source,('3D path was not persisted',item)
args.report.write_text(json.dumps({'board':str(target),'changed_paths':changes,'missing_models':missing,'note':'Missing 3D models do not stand in for footprint or package checks. Native pad/courtyard geometry is the placement contract.'},indent=2)+'\n',encoding='utf-8')
print('3D path fixes',len(changes),'missing models',len(missing))

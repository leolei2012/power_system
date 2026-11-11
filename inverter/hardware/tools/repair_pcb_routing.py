"""Rip up only ordinary routes conflicting with updated fixed geometry.

Keep In1 a ground reference. Defer the B.Cu ground pour in the DSN only, so
signals can use B.Cu; the actual PCB ground zone remains and is refilled later.
"""
from route_pcb import *

board=p.LoadBoard(str(BOARD_PATH));drc=json.loads((REVIEW/'pcb_drc.json').read_text(encoding='utf-8'))
bad_ids=set()
for problem in drc.get('violations',[]):
    if problem.get('severity')=='error':bad_ids.update(x.get('uuid') for x in problem.get('items',[]))
removed=[]
for t in list(board.GetTracks()):
    bad=(not isinstance(t,p.PCB_VIA) and t.GetLayer()==p.In1_Cu and t.GetNetname()!='GND')
    conflict=t.m_Uuid.AsString() in bad_ids and not t.IsLocked()
    if bad or conflict:
        assert not t.IsLocked(),('would remove fixed copper',t.m_Uuid.AsString())
        removed.append({'net':t.GetNetname(),'layer':board.GetLayerName(t.GetLayer()),'uuid':t.m_Uuid.AsString()})
        board.Delete(t)
board.SetLayerType(p.In1_Cu,p.LT_POWER)
board.BuildConnectivity();save_board(board)
assert p.ExportSpecctraDSN(board,str(REVIEW/'inverter_route_resume.dsn'))
source=(REVIEW/'inverter_route_resume.dsn').read_text(encoding='utf-8')
pattern=re.compile(r'\(plane\s+(?:"GND"|GND)\s+\(polygon\s+(?:"B.Cu"|B.Cu)\b')
spans=[]
for match in pattern.finditer(source):
    depth=0;quoted=False;escaped=False
    for pos in range(match.start(),len(source)):
        c=source[pos]
        if quoted:
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
        elif c=='"':quoted=True
        elif c=='(':depth+=1
        elif c==')':
            depth-=1
            if depth==0:spans.append((match.start(),pos+1));break
for start,end in reversed(spans):source=source[:start]+source[end:]
assert spans,'B.Cu ground pour was not found in routing-only DSN'
# Let Specctra importers infer the solid GND reference in their usual way;
# native KiCad keeps the layer's power designation. Some router versions
# skip their plane-net initialization when the DSN already says type power.
source=re.sub(r'(\(layer In1\.Cu\s+\(type )power(\))',r'\1signal\2',source,count=1)
(REVIEW/'inverter_route_resume.dsn').write_text(source,encoding='utf-8')
(REVIEW/'pcb_routing_repair.json').write_text(json.dumps({'removed_unlocked_routes':removed,'reference_layer':'In1.Cu power / GND','routing_only_deferred_back_ground_areas':len(spans),'note':'Actual PCB B.Cu GND zone was not removed. Refill it after session import.'},indent=2)+'\n',encoding='utf-8')
print('Removed',len(removed),'ordinary routes; retained fixed power / Kelvin; exported continuation DSN')

"""Apply frozen-source copper patches to a named private or owning native PCB.

Native DRC/fixed-copper checks must follow. No footprint movement or rule edit.
"""
from compact_route import *
from route_pcb import via
import shutil

ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--board',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--patch',type=Path,action='append',required=True);args=ap.parse_args()
source=args.board.resolve();target=args.out.resolve();source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
point_xy=lambda v:(round(p.ToMM(v.x),6),round(p.ToMM(v.y),6))
board=p.LoadBoard(str(source));fixed=fixed_geometry(board);project=source.with_suffix('.kicad_pro').read_bytes()
nets={n.GetNetname():n for n in board.GetNetsByNetcode().values() if n.GetNetCode()};stats=[]
for file in args.patch:
    data=json.loads(file.read_text(encoding='utf-8'));assert data['source_sha']==source_sha,('Patch source mismatch',str(file));assert not data.get('placements')
    items={t.m_Uuid.AsString():t for t in board.GetTracks()}
    for uid in data.get('ripup_uuids',[]):
        uid=uid.get('uuid') if isinstance(uid,dict) else uid
        if uid not in items:continue
        assert not items[uid].IsLocked(),('Locked removal forbidden',uid);board.Delete(items[uid])
    keys=set()
    for t in board.GetTracks():
        if isinstance(t,p.PCB_VIA):keys.add(('via',t.GetNetname(),xy(t),t.GetWidth(p.F_Cu),t.GetDrillValue()))
        else:keys.add(('line',t.GetNetname(),t.GetLayer(),t.GetWidth(),tuple(sorted([point_xy(t.GetStart()),point_xy(t.GetEnd())]))))
    for item in data.get('paths',[]):
        layer=board.GetLayerID(item['layer']) if isinstance(item['layer'],str) else item['layer'];net=nets[item['net']];width=item.get('width',.15)
        assert width>=.15 and (layer not in [p.In1_Cu,p.In4_Cu] or item['net']=='GND')
        for a,b in zip(item['points'],item['points'][1:]):
            key=('line',item['net'],layer,MM(width),tuple(sorted([tuple(a),tuple(b)])))
            if key in keys:continue
            segment(board,net,tuple(a),tuple(b),width,layer,item.get('locked',False));keys.add(key)
    for item in data.get('vias',[]):
        point=item.get('point') or item.get('via') or [item['x'],item['y']];dia=item.get('diameter',.6);drill=item.get('drill',.3)
        key=('via',item['net'],tuple(point),MM(dia),MM(drill))
        if key in keys:continue
        v=via(board,nets[item['net']],point,dia,drill);v.SetLocked(item.get('locked',False));keys.add(key)
    stats.append(str(file))
intended={t.m_Uuid.AsString():t.GetNetname() for t in board.GetTracks()};net_mutations=[]
for attempt in range(4):
    board.BuildConnectivity()
    changed=[t for t in board.GetTracks() if t.GetNetname()!=intended[t.m_Uuid.AsString()]]
    if not changed:break
    for t in changed:
        uid=t.m_Uuid.AsString();assert uid not in fixed,('Collision changed original fixed copper net',uid)
        net_mutations.append({'uuid':uid,'expected':intended[uid],'propagated':t.GetNetname(),'action':'removed conflicting ordinary copper'})
        board.Delete(t)
else:raise AssertionError('Repeated automatic net mutation; candidate not saved')
assert fixed.items()<=fixed_geometry(board).items(),'Fixed copper changed during application'
target.parent.mkdir(parents=True,exist_ok=True);p.SaveBoard(str(target),board);target.with_suffix('.kicad_pro').write_bytes(project)
target.with_suffix('.net_mutations.json').write_text(json.dumps(net_mutations,indent=2)+'\n',encoding='utf-8')
for name in ['fp-lib-table','sym-lib-table']:
    content=(B/name).read_text(encoding='utf-8').replace('${KIPRJMOD}',B.as_posix())
    (target.parent/name).write_text(content,encoding='utf-8') if target.parent!=B else None
print('Applied',len(stats),'patches to',target,'raw gaps',board.GetConnectivity().GetUnconnectedCount(False))

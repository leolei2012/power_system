"""Remove the least ordinary copper needed to clear current DRC collisions.

Does not remove fixed power/Kelvin copper or change any design rule. Refill and
run DRC afterwards. Remaining gaps are routed from this new native revision.
"""
from compact_route import *

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--board',type=Path,default=BOARD_PATH)
ap.add_argument('--drc',type=Path,default=REVIEW/'pcb_drc.json')
ap.add_argument('--out',type=Path,default=REVIEW/'compact_ripup.json');args=ap.parse_args()
board=p.LoadBoard(str(args.board));project=args.board.with_suffix('.kicad_pro');saved=project.read_bytes()
fixed=fixed_geometry(board);items={t.m_Uuid.AsString():t for t in board.GetTracks()};removed={}
drc=json.loads(args.drc.read_text(encoding='utf-8'))
for v in drc.get('violations',[]):
    if v['severity']!='error':continue
    assert v['type'] in ['clearance','shorting_items','solder_mask_bridge'],('Unapproved automatic rip-up category',v['type'])
    ids={x['uuid'] for x in v['items']}
    if ids&removed.keys():continue
    options=[items[q] for q in ids if q in items and not items[q].IsLocked()]
    assert options,('DRC error has no ordinary route to remove',v)
    item=min(options,key=lambda t:(isinstance(t,p.PCB_VIA),t.GetLength() if not isinstance(t,p.PCB_VIA) else 1e20))
    uid=item.m_Uuid.AsString();removed[uid]={'net':item.GetNetname(),'layer':board.GetLayerName(item.GetLayer()),'because':v['type']}
    board.Delete(item)
board.BuildConnectivity();assert fixed==fixed_geometry(board),'Rip-up changed fixed copper'
p.SaveBoard(str(args.board),board);project.write_bytes(saved)
args.out.write_text(json.dumps({'removed':removed,'fixed_geometry_unchanged':True},indent=2)+'\n',encoding='utf-8')
print('Removed',len(removed),'ordinary route fragments; fixed copper unchanged')

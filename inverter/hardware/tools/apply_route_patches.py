"""Merge reviewed, region-scoped routing deltas into the owning native PCB."""
from route_pcb import *

board=p.LoadBoard(str(BOARD_PATH));fps={f.GetReference():f for f in board.GetFootprints()}
nets={n.GetNetname():n for n in board.GetNetsByNetcode().values() if n.GetNetCode()>0}
source_sha=hashlib.sha256(BOARD_PATH.read_bytes()).hexdigest()
short_names=collections.defaultdict(list)
for name,value in nets.items():short_names[name.rsplit('/',1)[-1]].append(value)
patches=[]
for filename in sys.argv[1:]:
    source=Path(filename);data=json.loads(source.read_text(encoding='utf-8'))
    assert data.get('source_sha')==source_sha,('patch source revision mismatch',str(source),data.get('source_sha'),source_sha)
    patches.append((source,data))

def net(name):
    value=nets.get(name)
    if value is None:
        matches=short_names.get(name,[])
        assert len(matches)==1,('unknown or ambiguous short net',name,len(matches))
        value=matches[0]
    assert value,('unknown net',name)
    return value

stats=[]
for source,data in patches:
    existing={t.m_Uuid.AsString():t for t in board.GetTracks()}
    removed=[];absent=[]
    for uid in data.get('ripup_uuids',[]):
        uid=uid.get('uuid') if isinstance(uid,dict) else uid
        if uid in existing:
            item=existing.pop(uid);board.Delete(item);removed.append(uid)
        else:absent.append(uid)
    for ref,where in data.get('placements',{}).items():
        assert ref in fps
        if 'rotation_deg' in where:fps[ref].SetOrientationDegrees(where['rotation_deg'])
        fps[ref].SetPosition(V(where['x'],where['y']))
    nlines=0;nvias=0
    for item in data.get('paths',[]):
        layer=item.get('layer','F.Cu');layer=board.GetLayerID(layer) if isinstance(layer,str) else layer
        assert layer!=p.In1_Cu or item['net']=='GND',('non-ground reference-layer route',item)
        points=item['points'];width=item.get('width',.2)
        for a,b in zip(points,points[1:]):
            t=segment(board,net(item['net']),tuple(a),tuple(b),width,layer,item.get('locked',False))
            if t:nlines+=1
    for item in data.get('vias',[]):
        point=item.get('point') or item.get('via') or [item['x'],item['y']]
        a=via(board,net(item['net']),point,item.get('diameter',.6),item.get('drill',.3))
        a.SetLocked(item.get('locked',False));nvias+=1
    stats.append({'patch':str(source),'removed':len(removed),'already_removed':absent,'added_segments':nlines,'added_vias':nvias,'placements':len(data.get('placements',{}))})
board.BuildConnectivity();save_board(board)
(REVIEW/'pcb_merged_routes.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf-8')
print(json.dumps(stats))

"""Space same-net fixed via banks to satisfy Specctra router pair spacing too.

KiCad allows touching same-net copper. Wider bank pitch also reduces ambiguous
foreign-router fixed-via diagnostics. All affected trace endpoints follow vias.
"""
from route_pcb import *

board=p.LoadBoard(str(BOARD_PATH));fps={f.GetReference():f for f in board.GetFootprints()}
changes=[]
for i,phase in enumerate('UVW'):
    h=xy(pad(fps,'Q'+str(2*i+1),3));d=xy(pad(fps,'Q'+str(2*i+2),2,True));hd=xy(pad(fps,'Q'+str(2*i+1),2,True));g=xy(pad(fps,'RS'+str(i+1),2))
    for old_dx,new_dx in zip([-1.5,-.5,.5,1.5],[-2.1,-.7,.7,2.1]):
        changes += [(phase+'_PHASE',(h[0]+old_dx,h[1]+1.8),(h[0]+new_dx,h[1]+1.8)),
                    (phase+'_PHASE',(d[0]+old_dx,d[1]+6.2),(d[0]+new_dx,d[1]+6.2)),
                    ('VBUS',(hd[0]+old_dx,hd[1]-7.2),(hd[0]+new_dx,hd[1]-7.2))]
    for old_dy,new_dy in zip([-1.2,-.4,.4,1.2],[.5,1.5,2.5,3.5]):
        changes.append(('GND',(g[0]+3,g[1]+old_dy),(g[0]+3,g[1]+new_dy)))
for ref in ['C21','C22']:
    a=xy(pad(fps,ref,1))
    for old_dx,new_dx in [(-.5,-.6),(.5,.6)]:changes.append(('VBUS',(a[0]+old_dx,71.5),(a[0]+new_dx,71.5)))

items=list(board.GetTracks());moved=[]
for name,old,new in changes:
    old_v=V(*old);new_v=V(*new)
    vias=[v for v in items if isinstance(v,p.PCB_VIA) and v.IsLocked() and v.GetNetname().rsplit('/',1)[-1]==name and (v.GetPosition()-old_v).EuclideanNorm()<5]
    if not vias:
        # Repeat runs are harmless only when the expected destination exists.
        assert any(isinstance(v,p.PCB_VIA) and v.IsLocked() and v.GetNetname().rsplit('/',1)[-1]==name and (v.GetPosition()-new_v).EuclideanNorm()<5 for v in items),(name,old,'missing bank via')
        continue
    assert len(vias)==1,(name,old,'duplicate bank via')
    for t in items:
        if isinstance(t,p.PCB_VIA) or t.GetNetname().rsplit('/',1)[-1]!=name:continue
        if (t.GetStart()-old_v).EuclideanNorm()<5:t.SetStart(new_v)
        if (t.GetEnd()-old_v).EuclideanNorm()<5:t.SetEnd(new_v)
    vias[0].SetPosition(new_v);moved.append({'net':name,'from':old,'to':new})
board.BuildConnectivity();save_board(board)
(REVIEW/'pcb_via_bank_spacing.json').write_text(json.dumps({'moved':moved,'phase_bus_pitch_mm':1.4,'shunt_ground_pitch_mm':1.0,'MLCC_bus_pitch_mm':1.2},indent=2)+'\n',encoding='utf-8')
print('Spaced',len(moved),'fixed power vias')

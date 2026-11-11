"""Initial power copper, plane setup and local autorouter interchange.

Run with KiCad Python: --prepare; then route the local DSN with Freerouting;
then --import-session. Native PCB is the editable design, not these scripts.
"""
from build_pcb import *
import shutil


def save_board(board):
    # KiCad's SWIG SaveBoard can flush a different in-memory PROJECT when a
    # board has been loaded from an archive path. Preserve the owning rules.
    project=B/'inverter.kicad_pro';contents=project.read_text(encoding='utf-8')
    p.SaveBoard(str(BOARD_PATH),board)
    project.write_text(contents,encoding='utf-8')


def via(board,net,point,diameter=.8,drill=.4):
    v=p.PCB_VIA(board);v.SetPosition(V(*point));v.SetWidth(MM(diameter));v.SetDrill(MM(drill))
    v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetViaType(p.VIATYPE_THROUGH);v.SetNet(net);v.SetLocked(True);board.Add(v)
    v.SetFrontTentingMode(p.TENTING_MODE_TENTED);v.SetBackTentingMode(p.TENTING_MODE_TENTED)
    return v


def prepare():
    placed=REVIEW/'inverter_placed.kicad_pcb'
    if not placed.exists():shutil.copy2(BOARD_PATH,placed)
    board=p.LoadBoard(str(BOARD_PATH));fps={f.GetReference():f for f in board.GetFootprints()}
    for item in list(board.GetTracks()):board.Delete(item)
    for item in list(board.Zones()):board.Delete(p.Cast_to_ZONE(item))
    # Keep the optional TVS clear of the dedicated VBUS-to-brake trunk.
    fps['D2'].SetPosition(V(145,29))
    nets={n.GetNetname().rsplit('/',1)[-1]:n for n in board.GetNetsByNetcode().values() if n.GetNetCode()>0}
    def track(net,points,width=.4,layer=p.F_Cu):path(board,nets[net],points,width,layer)
    def copper(net,points,layer,name,priority=0,clearance=.25):return make_zone(board,nets[net],points,layer,name,clearance,priority)
    # Solid quiet reference on In1. Power return and outer power routes use B.Cu.
    copper('GND',[(1,1),(199,1),(199,139),(1,139)],p.In1_Cu,'GND REFERENCE',0)
    copper('GND',[(1,1),(199,1),(199,139),(1,139)],p.B_Cu,'DC- POWER RETURN',0)
    copper('VBUS',[(122,21),(183,21),(183,49),(122,49)],p.F_Cu,'COMMON VBUS / HIGH SIDE DRAINS',5,.4)
    copper('VBUS',[(111,20),(184,20),(184,78),(111,78)],p.In2_Cu,'LOCAL DC LINK DISTRIBUTION',5,.4)

    critical=[]
    for i,phase in enumerate('UVW'):
        high='Q'+str(i*2+1);low='Q'+str(i*2+2);shunt='RS'+str(i+1)
        a=xy(pad(fps,high,3));d=xy(pad(fps,low,2,True));source=xy(pad(fps,low,3));rs=xy(pad(fps,shunt,1))
        # Separate SOURCE island above each shunt: no ground copper bridge.
        track(phase+'_SOURCE',[source,(source[0],rs[1]),rs],2.0)
        # Top/source fanout to a parallel row of through vias outside paste pads.
        vp=[(a[0]-1.5+j, a[1]+1.8) for j in range(4)]
        for v in vp:
            track(phase+'_PHASE',[a,(a[0],v[1]),v],1.1)
            via(board,nets[phase+'_PHASE'],v)
        right=d[0]+1.5;exit_y=d[1]+6.2
        for xx in [-1.5,-.5,.5,1.5]:
            v=(d[0]+xx,exit_y)
            track(phase+'_PHASE',[d,(d[0],exit_y),v],4.0)
            via(board,nets[phase+'_PHASE'],v)
        # Broad B.Cu island joins high source to low drain without crossing gates.
        copper(phase+'_PHASE',[(a[0]-2.4,a[1]-.7),(right+.6,a[1]-.7),(right+.6,exit_y+.6),(a[0]-2.4,exit_y+.6)],p.B_Cu,phase+' PHASE POWER',10,.4)
        # The main drain lead and tab have the same number but are distinct pads.
        for q in [high,low]:
            pads=[x for x in fps[q].Pads() if x.GetNumber()=='2']
            track(pads[0].GetNetname().rsplit('/',1)[-1],[xy(pads[0]),xy(pads[1])],.8)
        out=xy(pad(fps,'J4',i+1))
        if i==0:
            route=[(right,exit_y),(137.75,exit_y),(137.75,18),(out[0],18),out]
        elif i==1:
            route=[(right,exit_y),(161.75,exit_y),(161.75,37),(168,37),(168,23),(188,23),(188,out[1]),out]
        else:route=[(right,exit_y),(186,out[1]),out]
        track(phase+'_PHASE',route,4,p.B_Cu)
        critical.append({'phase':phase,'source':source,'shunt_high':rs,'phase_route_mm':route,'phase_width_mm':4,'source_width_mm':2,'phase_vias_per_transfer':4,'phase_transfers_in_series':2})
        # High-side drain connects to the local internal DC link plane with
        # a separate four-via bank; main DC current also has the wide F.Cu bus.
        hd=xy(pad(fps,high,2,True))
        for dx in [-1.5,-.5,.5,1.5]:
            v=(hd[0]+dx,hd[1]-7.2)
            track('VBUS',[hd,(hd[0],v[1]),v],3.0);via(board,nets['VBUS'],v)
        # Ground side of shunt spreads directly into DC- planes via four vias.
        g=xy(pad(fps,shunt,2))
        for dy in [-1.2,-.4,.4,1.2]:
            v=(g[0]+3,g[1]+dy);track('GND',[g,(v[0],g[1]),v],.7);via(board,nets['GND'],v,.7,.35)
        # Gate resistor-to-gate copper is short, fixed, and on the component side.
        for r,q in [('R'+str(19+6*i),high),('R'+str(20+6*i),low)]:
            start=xy(pad(fps,r,2));end=xy(pad(fps,q,1));n=pad(fps,q,1).GetNetname().rsplit('/',1)[-1]
            track(n,[start,(end[0],start[1]),end],.4)

    # Two shared bus MLCCs have dedicated connections to the paired DC-link
    # and ground layers, rather than relying on an ordinary autorouted trace.
    for ref in ['C21','C22']:
        plus=xy(pad(fps,ref,1));minus=xy(pad(fps,ref,2))
        for dx in [-.5,.5]:
            v=(plus[0]+dx,71.5);track('VBUS',[plus,(plus[0],v[1]),v],1.3);via(board,nets['VBUS'],v,.7,.35)
        gx=minus[0]+2.85
        for dy in [-.5,.5]:
            v=(gx,71.5+dy);track('GND',[minus,(gx,minus[1]),v],.7);via(board,nets['GND'],v,.7,.35)

    # Independent Kelvin branches originate at the shunt pads. The negative
    # branch deliberately skirts the high-current ground-via fanout; sharing
    # the GND name must not turn it into an arbitrary nearest-ground stub.
    kelvin=[]
    for i,phase in enumerate('UVW'):
        sh='RS'+str(i+1);amp='U'+str(10+i)
        hi=xy(pad(fps,sh,1));lo=xy(pad(fps,sh,2))
        ip=xy(pad(fps,amp,8));im=xy(pad(fps,amp,1))
        positive=[hi,(ip[0]-.8,hi[1]),(ip[0]-.8,ip[1]),ip]
        negative=[lo,(lo[0]+1.45,lo[1]),(lo[0]+1.45,im[1]),im]
        track(phase+'_SOURCE',positive,.2);track('GND',negative,.2)
        kelvin.append({'phase':phase,'positive':positive,'negative':negative,'trace_width_mm':.2})

    # External brake resistor has its own VBUS and switched-return branch.
    brp=xy(pad(fps,'J5',1));brs=xy(pad(fps,'J5',2));drain=xy(pad(fps,'Q7',2,True));g=xy(pad(fps,'Q7',3))
    track('VBUS',[(180,37),(185.5,37),(185.5,74),(190,74),(190,brp[1]),brp],4)
    track('BR_SW',[drain,(drain[0],100),(brs[0],100),brs],4)
    for a in [x for x in fps['Q7'].Pads() if x.GetNumber()=='2']:
        track('BR_SW',[xy(a),drain],.8)
    for dx in [-1.5,-.5,.5,1.5]:
        v=(g[0]+dx,g[1]+2);track('GND',[g,(g[0],v[1]),v],.8);via(board,nets['GND'],v)
    # Input copper keeps DC+ before and after fuse distinct.
    inp=xy(pad(fps,'J3',1));f_in=[xy(x) for x in fps['F1'].Pads() if x.GetNumber()=='1'];f_out=[xy(x) for x in fps['F1'].Pads() if x.GetNumber()=='2']
    for target in f_in:track('DC_INPUT_POS',[inp,(target[0],inp[1]),target],4)
    anodes=[xy(x) for x in fps['D1'].Pads() if x.GetNumber() in ['1','3']]
    track('DC_FUSED',[f_out[0],(192,f_out[0][1]),(192,32)],4)
    for target in anodes:track('DC_FUSED',[(192,target[1]),target],1.1)
    for target in f_out[1:]:track('DC_FUSED',[f_out[0],target],4)

    # Keep power geometry in native CAD. Filled areas are exported as router obstacles.
    # The branch helpers deliberately share some stems; keep one native
    # segment for each exact geometry so downstream routers do not oscillate.
    seen=set()
    for item in list(board.GetTracks()):
        if isinstance(item,p.PCB_VIA):continue
        ends=tuple(sorted([(item.GetStart().x,item.GetStart().y),(item.GetEnd().x,item.GetEnd().y)]))
        key=(item.GetNetCode(),item.GetLayer(),item.GetWidth(),ends)
        if key in seen:board.Delete(item)
        else:seen.add(key)
    board.BuildConnectivity();save_board(board)
    (REVIEW/'pcb_power_copper.json').write_text(json.dumps({'status':'initial geometry; DRC and thermal review required','critical':critical,'kelvin_locked':kelvin,'outer_copper_target_um':70,'inner_copper_target_um':35,'power_output_width_mm':4,'limits':'Via current sharing, temperature rise, switch loops and emissions are not validated by connectivity checks.'},indent=2)+'\n',encoding='utf-8')
    print('Prepared power copper:',len(list(board.GetTracks())),'tracks/vias;',len(list(board.Zones())),'zones')


def export_dsn():
    board=p.LoadBoard(str(BOARD_PATH));board.BuildConnectivity()
    output=Path(sys.argv[sys.argv.index('--dsn')+1]) if '--dsn' in sys.argv else REVIEW/'inverter_route.dsn'
    assert p.ExportSpecctraDSN(board,str(output)),'DSN export failed'
    print('Exported local Specctra DSN')


def import_session():
    session=Path(sys.argv[sys.argv.index('--session')+1]) if '--session' in sys.argv else REVIEW/'inverter_route.ses'
    board=p.LoadBoard(str(BOARD_PATH));assert p.ImportSpecctraSES(board,str(session)),'SES import failed'
    board.BuildConnectivity();save_board(board)
    print('Imported session:',len(list(board.GetTracks())),'tracks/vias')


if __name__=='__main__':
    if '--prepare' in sys.argv:prepare()
    elif '--export-dsn' in sys.argv:export_dsn()
    elif '--import-session' in sys.argv:import_session()
    else:raise SystemExit('Choose --prepare, --export-dsn or --import-session')

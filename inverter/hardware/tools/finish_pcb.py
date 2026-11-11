"""Apply recorded local placement refinements / finish non-electrical board details."""
from route_pcb import *


def refine():
    board=p.LoadBoard(str(BOARD_PATH));fps={f.GetReference():f for f in board.GetFootprints()}
    changes={}
    for filename in ['pcb_control_refinements.json','pcb_control_copper_refinements.json','pcb_driver_refinements.json']:
        source=B/'tools'/filename
        if source.exists():changes.update(json.loads(source.read_text(encoding='utf-8'))['placements'])
    for ref,where in changes.items():
        fp=fps[ref];fp.SetOrientationDegrees(where.get('rotation_deg',fp.GetOrientationDegrees()));fp.SetPosition(V(where['x'],where['y']))
    place_references(fps);save_board(board)
    print('Applied',len(changes),'local placement refinements')


def silk():
    board=p.LoadBoard(str(BOARD_PATH));fps={f.GetReference():f for f in board.GetFootprints()}
    # Reference placement respects actual package courtyards. Dense designators
    # remain visible on F.Fab as an assembly aid instead of crossing solder pads.
    refs=[r for r,f in fps.items() if f.Reference().GetLayer()==p.F_Fab]
    drc_path=REVIEW/'pcb_drc.json'
    moved=[]
    if drc_path.exists():
        drc=json.loads(drc_path.read_text(encoding='utf-8'))
        for problem in drc.get('violations',[]):
            if problem['type'] not in ['silk_overlap','silk_over_copper']:continue
            ids={v.get('uuid') for v in problem.get('items',[])}
            fields=[f.Reference() for f in fps.values() if f.Reference().m_Uuid.AsString() in ids and f.Reference().GetLayer()==p.F_SilkS]
            if fields:
                field=fields[0];field.SetLayer(p.F_Fab);moved.append(field.GetText());continue
            for drawing in board.GetDrawings():
                if isinstance(drawing,p.PCB_TEXT) and drawing.m_Uuid.AsString() in ids and drawing.GetLayer()==p.F_SilkS:
                    # Connector labels are supplementary; retain them on the
                    # assembly layer if the edge has no readable silk space.
                    drawing.SetLayer(p.F_Fab);moved.append(drawing.GetText());break
    save_board(board)
    (REVIEW/'pcb_silkscreen.json').write_text(json.dumps({'assembly_layer_dense_refs':refs,'assembly_layer_conflicting_labels':moved},indent=2)+'\n',encoding='utf-8')
    print('Assembly-layer labels:',len(refs),'+',len(moved))


def labels():
    board=p.LoadBoard(str(BOARD_PATH));fps={f.GetReference():f for f in board.GetFootprints()}
    place_references(fps)
    for drawing in board.GetDrawings():
        if not isinstance(drawing,p.PCB_TEXT):continue
        value=drawing.GetText()
        if value=='POWER SYSTEM / G431 INVERTER':drawing.SetPosition(V(143,127))
        elif value=='REV B PCB 0.1 / REVIEW DRAFT':drawing.SetPosition(V(143,130))
        elif value in ['ENC A','ENC B','SPI A','SPI B']:
            ref={'ENC A':'J9','ENC B':'J10','SPI A':'J11','SPI B':'J12'}[value]
            bb=bbox(fps[ref]);drawing.SetPosition(V((bb[0]+bb[2])/2,6.5));drawing.SetText(value+' / 3V3 IO')
    if not any(isinstance(d,p.PCB_TEXT) and d.GetText()=='SENSOR I/O: 3V3 / POWER LINKS DNP' for d in board.GetDrawings()):
        text(board,'SENSOR I/O: 3V3 / POWER LINKS DNP',56,3.5,size=.8)
    for item in board.GetTracks():
        if isinstance(item,p.PCB_VIA):
            item.SetFrontTentingMode(p.TENTING_MODE_TENTED);item.SetBackTentingMode(p.TENTING_MODE_TENTED)
    save_board(board)
    print('Updated connector voltage legends, references and tented vias')


def power_returns():
    board=p.LoadBoard(str(BOARD_PATH));fps={f.GetReference():f for f in board.GetFootprints()}
    changes=[]
    for i,phase in enumerate('UVW'):
        hi=pad(fps,'RS'+str(i+1),1);lo=pad(fps,'RS'+str(i+1),2)
        h=xy(hi);g=xy(lo);ip=xy(pad(fps,'U'+str(10+i),8));im=xy(pad(fps,'U'+str(10+i),1))
        old_paths=[[h,(ip[0]-.8,h[1]),(ip[0]-.8,ip[1]),ip],
                   [g,(g[0]+1.45,g[1]),(g[0]+1.45,im[1]),im]]
        old_edges=[tuple(sorted([V(*a).Get(),V(*b).Get()])) for pts in old_paths for a,b in zip(pts,pts[1:])]
        removed=0;widened=0
        for item in list(board.GetTracks()):
            if isinstance(item,p.PCB_VIA) or item.GetLayer()!=p.F_Cu or not item.IsLocked():continue
            a=item.GetStart();b=item.GetEnd();ends=tuple(sorted([(a.x,a.y),(b.x,b.y)]))
            if item.GetWidth()==MM(.2) and ends in old_edges:
                board.Delete(item);removed+=1;continue
            if item.GetNetname()=='GND' and item.GetWidth()==MM(.7):
                ax,ay=p.ToMM(a.x),p.ToMM(a.y);bx,by=p.ToMM(b.x),p.ToMM(b.y)
                horizontal=abs(ay-g[1])<.00001 and abs(by-g[1])<.00001 and min(ax,bx)>=g[0]-.001 and max(ax,bx)<=g[0]+3.001
                vertical=abs(ax-g[0]-3)<.00001 and abs(bx-g[0]-3)<.00001 and min(ay,by)>=g[1]-.001 and max(ay,by)<=g[1]+3.501
                if horizontal or vertical:item.SetWidth(MM(2));widened+=1
        hb=hi.GetBoundingBox();lb=lo.GetBoundingBox()
        # Take the sense branch from the copper pad edge facing the resistor
        # body, away from the incoming/outgoing high-current stems.
        hp=(h[0],p.ToMM(hb.GetBottom())-.1);lp=(g[0],p.ToMM(lb.GetY())+.1)
        nets={n.GetNetname():n for n in board.GetNetsByNetcode().values()}
        positive=[hp,(ip[0]-.8,hp[1]),(ip[0]-.8,ip[1]),ip]
        negative=[lp,(im[0]-.8,lp[1]),(im[0]-.8,im[1]),im]
        path(board,nets[hi.GetNetname()],positive,.2);path(board,nets['GND'],negative,.2)
        changes.append({'phase':phase,'old_kelvin_segments_removed':removed,'return_segments_widened_to_2mm':widened,'positive_inner_pad_branch':positive,'negative_inner_pad_branch':negative})
    seen=set()
    for item in list(board.GetTracks()):
        if isinstance(item,p.PCB_VIA):continue
        ends=tuple(sorted([item.GetStart().Get(),item.GetEnd().Get()]))
        key=(item.GetNetCode(),item.GetLayer(),item.GetWidth(),ends)
        if key in seen:board.Delete(item)
        else:seen.add(key)
    board.BuildConnectivity();save_board(board)
    (REVIEW/'pcb_shunt_returns.json').write_text(json.dumps({'changes':changes,'note':'Sense branches originate at the resistor-facing pad edges; only pad copper is shared with the high-current return.'},indent=2)+'\n',encoding='utf-8')
    print('Widened shunt return stems and placed resistor-edge Kelvin branches')


def distribution():
    board=p.LoadBoard(str(BOARD_PATH));fps={f.GetReference():f for f in board.GetFootprints()}
    nets={n.GetNetname():n for n in board.GetNetsByNetcode().values() if n.GetNetCode()>0}
    for z in list(board.Zones()):
        zone=p.Cast_to_ZONE(z)
        if zone.GetZoneName()=='CONTROL 3V3 DISTRIBUTION':board.Delete(zone)
    make_zone(board,nets['+3V3_INV'],[(15,20),(100,20),(100,95),(90,95),(90,128),(70,128),(70,95),(15,95)],p.B_Cu,'CONTROL 3V3 DISTRIBUTION',clearance=.2,priority=3)
    if not any(isinstance(t,p.PCB_VIA) and t.GetNetname()=='+3V3_INV' and xy(t)==(83,120.5) for t in board.GetTracks()):
        a=xy(pad(fps,'C16',1));v=(83,120.5)
        path(board,nets['+3V3_INV'],[a,(a[0],v[1]),v],.3);via(board,nets['+3V3_INV'],v,.7,.35)
    save_board(board)
    project=B/'inverter.kicad_pro';pro=json.loads(project.read_text(encoding='utf-8'))
    patterns=[]
    for name in nets:
        s=name.rsplit('/',1)[-1]
        if s in ['VBUS','U_PHASE','V_PHASE','W_PHASE','BR_SW','DC_FUSED','DC_INPUT_POS']:nc='HV'
        elif any(t in s for t in ['GATE','HO_DRV','LO_DRV','H_DRV','L_DRV']) or s.endswith('_BOOT'):nc='Gate'
        elif s.startswith(('+12V','+5V')) or s in ['AUX_IN','AUX_FUSED','AUX_PROTECTED','BB_L1','BB_L2']:nc='Auxiliary'
        else:nc='Default'
        if nc!='Default':patterns.append({'netclass':nc,'pattern':name})
    pro['net_settings']['netclass_patterns']=patterns
    project.write_text(json.dumps(pro,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Added control 3.3V distribution pour; separated supply control nets from power-width class')


def stackup():
    # Preliminary copper target, not a vendor-approved manufacturing stackup.
    source=BOARD_PATH.read_text(encoding='utf-8')
    if '(stackup' in source:
        print('Existing explicit stackup retained');return
    stack='''		(stackup
			(layer "F.SilkS" (type "Top Silk Screen"))
			(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.07))
			(layer "dielectric 1" (type "prepreg") (thickness 0.18) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
			(layer "In1.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 2" (type "core") (thickness 1.01) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
			(layer "In2.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 3" (type "prepreg") (thickness 0.18) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.07))
			(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
			(layer "B.SilkS" (type "Bottom Silk Screen"))
		)
'''
    assert '\t(setup\n' in source
    source=source.replace('\t(setup\n','\t(setup\n'+stack,1)
    BOARD_PATH.write_text(source,encoding='utf-8')
    # A successful native reload is required; do not leave a text-only artifact.
    board=p.LoadBoard(str(BOARD_PATH));assert board.GetCopperLayerCount()==4
    print('Explicit draft stackup: 1.6mm incl mask, outer70um / inner35um')


def deadends():
    """Trim unlocked dead ends privately; accept only a filled, connected board.

    Removing a dangling via may temporarily expose another unused stub. Native
    DRC is therefore rerun at each step; an incomplete trial never replaces the
    owning board. Locked power and Kelvin copper is never removed.
    """
    import shutil
    import subprocess
    report=json.loads((REVIEW/'pcb_drc.json').read_text(encoding='utf-8'))
    assert not report['unconnected_items'] and not report['schematic_parity'], 'Finish connections and parity before dead-end cleanup'
    assert not any(v.get('severity')=='error' for v in report['violations']), 'Fix DRC errors first'
    source_sha=hashlib.sha256(BOARD_PATH.read_bytes()).hexdigest()
    trial_dir=REVIEW/'pcb_deadend_trial'/source_sha[:12];trial_dir.mkdir(parents=True,exist_ok=True)
    trial=trial_dir/'inverter.kicad_pcb';trial_pro=trial.with_suffix('.kicad_pro')
    project=(B/'inverter.kicad_pro').read_bytes()
    shutil.copyfile(BOARD_PATH,trial);shutil.copyfile(BOARD_PATH,trial_dir/'before_cleanup.kicad_pcb')
    trial_pro.write_bytes(project)
    table=(B/'fp-lib-table').read_text(encoding='utf-8').replace('${KIPRJMOD}',B.as_posix())
    (trial_dir/'fp-lib-table').write_text(table,encoding='utf-8')
    rounds=[];kept=set()
    def trim_track(board,item):
        # A dangling endpoint does not imply that the whole segment is unused:
        # another route may join halfway along it. Keep the span of all copper
        # contacts, and validate connectivity before accepting the shorter span.
        if item.GetClass()!='PCB_TRACK':return False
        a=xy(item);end=item.GetEnd();b=(p.ToMM(end.x),p.ToMM(end.y))
        dx=b[0]-a[0];dy=b[1]-a[1];length2=dx*dx+dy*dy
        if not length2:return False
        contacts=[];width=p.ToMM(item.GetWidth());layer=item.GetLayer()
        def project(point,radius):
            t=((point[0]-a[0])*dx+(point[1]-a[1])*dy)/length2
            if -.000001<=t<=1.000001:
                t=max(0,min(1,t));q=(a[0]+t*dx,a[1]+t*dy)
                if math.hypot(q[0]-point[0],q[1]-point[1])<=radius+.000001:contacts.append(t)
        for other in board.GetTracks():
            if other.m_Uuid.AsString()==item.m_Uuid.AsString() or other.GetNetCode()!=item.GetNetCode() or not other.IsOnLayer(layer):continue
            if other.GetClass()=='PCB_VIA':project(xy(other),width/2+p.ToMM(other.GetWidth(layer))/2);continue
            c=xy(other);end=other.GetEnd();d=(p.ToMM(end.x),p.ToMM(end.y))
            project(c,(width+p.ToMM(other.GetWidth()))/2);project(d,(width+p.ToMM(other.GetWidth()))/2)
            ex=d[0]-c[0];ey=d[1]-c[1];den=dx*ey-dy*ex
            if abs(den)>1e-10:
                t=((c[0]-a[0])*ey-(c[1]-a[1])*ex)/den
                u=((c[0]-a[0])*dy-(c[1]-a[1])*dx)/den
                if 0<=t<=1 and 0<=u<=1:contacts.append(t)
        for fp in board.GetFootprints():
            for pad_item in fp.Pads():
                if pad_item.GetNetCode()!=item.GetNetCode() or not pad_item.IsOnLayer(layer):continue
                if pad_item.HitTest(V(*a)):contacts.append(0)
                if pad_item.HitTest(V(*b)):contacts.append(1)
        if len(contacts)<2:return False
        lo=min(contacts);hi=max(contacts)
        if hi-lo<1e-6 or (lo<1e-6 and hi>1-1e-6):return False
        item.SetStart(V(a[0]+lo*dx,a[1]+lo*dy));item.SetEnd(V(a[0]+hi*dx,a[1]+hi*dy))
        return True
    for index in range(12):
        removed=[]
        for problem in report['violations']:
            if problem['type'] not in ['track_dangling','via_dangling']:continue
            for entry in problem.get('items',[]):
                board=p.LoadBoard(str(trial));items={t.m_Uuid.AsString():t for t in board.GetTracks()}
                item=items.get(entry['uuid'])
                if item is None:continue
                if item.IsLocked():kept.add(entry['uuid']);continue
                record={'uuid':entry['uuid'],'net':item.GetNetname(),'kind':item.GetClass(),
                        'start_mm':xy(item),'warning':problem['type'],'action':'remove'}
                board.Delete(item)
                board.BuildConnectivity()
                if board.GetConnectivity().GetUnconnectedCount(False):
                    board=p.LoadBoard(str(trial));item={t.m_Uuid.AsString():t for t in board.GetTracks()}[entry['uuid']]
                    if not trim_track(board,item):kept.add(entry['uuid']);continue
                    board.BuildConnectivity()
                    if board.GetConnectivity().GetUnconnectedCount(False):kept.add(entry['uuid']);continue
                    record['action']='trim unused span'
                p.SaveBoard(str(trial),board);trial_pro.write_bytes(project);removed.append(record)
        if not removed:break
        drc=trial_dir/('drc_%02d.json'%index)
        subprocess.run([str(Path(sys.executable).with_name('kicad-cli.exe')),'pcb','drc',str(trial),
                        '--format','json','--all-track-errors','--refill-zones','--save-board','-o',str(drc)],
                       check=True,capture_output=True)
        report=json.loads(drc.read_text(encoding='utf-8'))
        assert not any(v.get('severity')=='error' for v in report['violations']), 'Trial produced geometry errors; owning board unchanged'
        rounds.append({'removed':removed,'unconnected_after_fill':len(report['unconnected_items']),
                       'DRC_report':str(drc.relative_to(B))})
        print('Dead-end trial round',index+1,'removed',len(removed),'unconnected',len(report['unconnected_items']),flush=True)
    assert not report['unconnected_items'], 'Trial incomplete; owning board unchanged'
    assert hashlib.sha256(BOARD_PATH.read_bytes()).hexdigest()==source_sha, 'Owning board changed during trial'
    if rounds:shutil.copyfile(trial,BOARD_PATH)
    (REVIEW/'pcb_deadend_cleanup.json').write_text(json.dumps({'source_sha256':source_sha,'rounds':rounds,
        'retained_locked':sorted(kept),'final_trial_unconnected':0,
        'next_step':'Run full DRC with schematic parity in owning project'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Accepted private cleanup; rounds:',len(rounds),'retained locked:',len(kept))


if __name__=='__main__':
    if '--refine' in sys.argv:refine()
    elif '--labels' in sys.argv:labels()
    elif '--power-returns' in sys.argv:power_returns()
    elif '--distribution' in sys.argv:distribution()
    elif '--silk' in sys.argv:silk()
    elif '--stackup' in sys.argv:stackup()
    elif '--deadends' in sys.argv:deadends()
    else:raise SystemExit('Choose --refine, --labels, --power-returns, --distribution, --silk, --stackup or --deadends')

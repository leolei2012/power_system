"""Fixed main-power and Kelvin copper for the 60 mm inverter engineering draft.

Run with KiCad's bundled Python.  The source board is never saved.  A private
copy and its own .kicad_pro are created before pcbnew loads/saves the copy.
All terminal and IC endpoints are read from the actual footprint pads.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import math
import pcbnew as p

BASE = Path(__file__).resolve().parents[1]
MM = p.FromMM


def V(pt):
    return p.VECTOR2I(MM(pt[0]), MM(pt[1]))


def xy(item):
    pos = item.GetPosition()
    return (round(p.ToMM(pos.x), 6), round(p.ToMM(pos.y), 6))


def audit_power_connectivity(board, records):
    """Independent geometry union using actual saved copper/filled islands."""
    fps={f.GetReference():f for f in board.GetFootprints()}
    layers=[p.F_Cu,p.In1_Cu,p.In2_Cu,p.In3_Cu,p.In4_Cu,p.B_Cu]
    def pads(ref,pins):
        return [a for a in fps[ref].Pads() if a.GetNumber() in {str(v) for v in pins}]
    targets=[]
    targets.append(('DC_INPUT',pads('J3',[1])+pads('F1',[1])))
    targets.append(('DC_FUSED',pads('F1',[2])+pads('D1',[1,3])))
    targets.append(('VBUS',pads('D1',[2])+sum([pads(q,[5,6,7,8]) for q in ['Q1','Q3','Q5']],[])
                    +sum([pads(c,[1]) for c in ['C19','C20','C21','C22']],[])+pads('J5',[1])))
    targets.append(('GND_MAIN',pads('J3',[2])+sum([pads(r,[2]) for r in ['RS1','RS2','RS3']],[])
                    +pads('Q7',[1,2,3])+sum([pads(c,[2]) for c in ['C19','C20','C21','C22']],[])))
    targets.append(('BRAKE_SW',pads('Q7',[5,6,7,8])+pads('J5',[2])))
    for i,phase in enumerate('UVW'):
        targets.append((phase+'_PHASE',pads('Q'+str(1+2*i),[1,2,3])+pads('Q'+str(2+2*i),[5,6,7,8])+pads('J4',[i+1])))
        targets.append((phase+'_SOURCE',pads('Q'+str(2+2*i),[1,2,3])+pads('RS'+str(i+1),[1])+pads('U'+str(10+i),[8])))
        targets.append((phase+'_NEGATIVE_KELVIN',pads('RS'+str(i+1),[2])+pads('U'+str(10+i),[1])))
    all_items=[a for f in fps.values() for a in f.Pads() if a.GetNumber()]+list(board.GetTracks())
    connected={}; results={}
    for label,required in targets:
        code=required[0].GetNetCode()
        assert all(a.GetNetCode()==code for a in required),(label,'pad-net mismatch')
        if code not in connected:
            nodes=[]
            for item in all_items:
                if item.GetNetCode()!=code:continue
                shapes={layer:item.GetEffectiveShape(layer) for layer in layers if item.IsOnLayer(layer)}
                if shapes:nodes.append((item.m_Uuid.AsString(),shapes))
            for z in board.Zones():
                if z.GetIsRuleArea() or z.GetNetCode()!=code:continue
                for layer in layers:
                    if not z.IsOnLayer(layer):continue
                    poly=z.GetFilledPolysList(layer)
                    for k in range(poly.OutlineCount()):nodes.append((z.m_Uuid.AsString()+':'+str(layer)+':'+str(k),{layer:poly.UnitSet(k)}))
            parent=list(range(len(nodes)))
            def root(i):
                while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
                return i
            for i,(_,a) in enumerate(nodes):
                for j in range(i):
                    b=nodes[j][1]
                    if any(a[l].Collide(b[l]) for l in a.keys()&b.keys()):parent[root(i)]=root(j)
            connected[code]={uid:root(i) for i,(uid,_) in enumerate(nodes)}
        comp=connected[code]; roots={comp[a.m_Uuid.AsString()] for a in required}
        results[label]={'pass':len(roots)==1,'physical_pad_count':len(required),'components':len(roots)}
        assert len(roots)==1,('Fixed main power geometry is disconnected',label,results[label])
    plane_isolation=[]
    byuuid={a.m_Uuid.AsString():a for a in board.GetTracks()}
    for item in records['kelvin']:
        vv=byuuid[item['negative_via_uuid']]
        for layer in [p.In1_Cu,p.In4_Cu]:
            hit=any(z.GetNetname()=='GND' and not z.GetIsRuleArea() and z.IsOnLayer(layer)
                    and z.GetFilledPolysList(layer).Collide(vv.GetEffectiveShape(layer)) for z in board.Zones())
            plane_isolation.append({'phase':item['phase'],'layer':board.GetLayerName(layer),'isolated':not hit})
            assert not hit,('Negative Kelvin via contacts a GND plane',item['phase'],layer)
    return {'method':'Actual saved tracks/pads/vias and per-layer filled-zone islands; same-layer shape intersections plus plated through-layer links.',
            'critical_paths':results,'negative_kelvin_plane_isolation':plane_isolation}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', type=Path, default=BASE/'review/compact_work/inverter.kicad_pcb')
    ap.add_argument('--output', type=Path, default=BASE/'review/compact_power_candidate/inverter.kicad_pcb')
    ap.add_argument('--no-fill', action='store_true')
    ap.add_argument('--drc', action='store_true')
    args = ap.parse_args()
    source = args.board.resolve()
    output = args.output.resolve()
    assert source != output, 'Source board is read-only; choose a different private output.'
    assert output != (BASE/'inverter.kicad_pcb').resolve(), 'Refusing to write the main PCB.'
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)
    source_pro = source.with_suffix('.kicad_pro')
    private_pro = output.with_suffix('.kicad_pro')
    project_bytes = source_pro.read_bytes()
    private_pro.write_bytes(project_bytes)
    for name in ['fp-lib-table', 'sym-lib-table']:
        if (source.parent/name).exists():
            shutil.copyfile(source.parent/name, output.parent/name)
    board = p.LoadBoard(str(output))
    assert board.GetCopperLayerCount() == 6
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    nets = {n.GetNetname(): n for n in board.GetNetsByNetcode().values() if n.GetNetCode()}
    short = {name.rsplit('/', 1)[-1]: n for name, n in nets.items()}
    created = []
    records = {'tracks': [], 'vias': [], 'zones': [], 'kelvin': [], 'critical': [], 'placements': {}}

    # Root authorized moving a few small control resistors out of the fuse's
    # essential four-via fanout. Preserve their side, footprint, pins and nets.
    # Search actual courtyard polygons; do not pack them on top of B solder pads.
    def polygon(points):
        sh=p.SHAPE_POLY_SET();sh.NewOutline()
        for x,y in points:sh.Append(MM(x),MM(y))
        return sh
    fuse_reserve={p.F_CrtYd:polygon([(8,15),(10.9,15),(10.9,20.5),(8,20.5)]),
                  p.B_CrtYd:polygon([(8,15),(10.9,15),(10.9,18.3),(8,18.3)])}
    control_scope=set(json.loads((BASE/'tools/compact_control_placement.json').read_text(encoding='utf-8'))['owned_refs'])
    for f in fps.values():f.BuildCourtyardCaches()
    displaced=[]
    for ref in sorted(control_scope):
        f=fps[ref]
        if ref not in {'R98','R100','R122'}:continue
        layer=p.B_CrtYd if f.IsFlipped() else p.F_CrtYd
        cy=f.GetCourtyard(layer)
        if cy.OutlineCount() and cy.Collide(fuse_reserve[layer]):displaced.append(ref)
    for ref in displaced:
        f=fps[ref];origin=xy(f);side='B' if f.IsFlipped() else 'F'
        layer=p.B_CrtYd if f.IsFlipped() else p.F_CrtYd
        options=sorted((math.hypot(dx/4,dy/4),origin[0]+dx/4,origin[1]+dy/4)
                       for dx in range(-28,29) for dy in range(-28,29))
        found=False
        for _,xx,yy in options:
            if not (3.6<xx<33 and 4<yy<40):continue
            f.SetPosition(V((xx,yy)));f.BuildCourtyardCaches();cy=f.GetCourtyard(layer)
            if cy.Collide(fuse_reserve[layer]):continue
            if any(o.GetReference()!=ref and o.GetCourtyard(layer).OutlineCount()
                   and cy.Collide(o.GetCourtyard(layer)) for o in fps.values()):continue
            # Through-hole solder pads also exist on the unpopulated face.
            bad=False
            for o in fps.values():
                if o.GetReference()==ref:continue
                for a in o.Pads():
                    if a.GetAttribute()!=p.PAD_ATTRIB_PTH:continue
                    if cy.Collide(a.GetEffectiveShape(p.B_Cu if side=='B' else p.F_Cu),MM(.25)):
                        bad=True;break
                if bad:break
            if bad:continue
            found=True
            records['placements'][ref]={'x':xx,'y':yy,'rotation_deg':f.GetOrientationDegrees(),
                'side':side,'group':'fuse_fanout_clearance','previous_xy':origin}
            break
        assert found,('No safe local relocation for fuse fanout',ref)

    def pad(ref, number, largest=False):
        matches = [a for a in fps[ref].Pads() if a.GetNumber() == str(number)]
        assert matches, (ref, number)
        return max(matches, key=lambda a: a.GetSize().x*a.GetSize().y) if largest else matches[0]

    def net_of(ref, number):
        return pad(ref, number).GetNet()

    def net(value):
        return short[value] if isinstance(value, str) else value

    def path(n, points, width, layer=p.F_Cu, purpose='power'):
        n = net(n)
        result = []
        for a, b in zip(points, points[1:]):
            if a == b:
                continue
            t = p.PCB_TRACK(board)
            t.SetStart(V(a)); t.SetEnd(V(b)); t.SetWidth(MM(width))
            t.SetLayer(layer); t.SetNet(n); t.SetLocked(True); board.Add(t)
            created.append(t); result.append(t.m_Uuid.AsString())
            records['tracks'].append({'uuid': t.m_Uuid.AsString(), 'net': n.GetNetname(),
                'layer': board.GetLayerName(layer), 'width_mm': width, 'a': a, 'b': b, 'purpose': purpose})
        return result

    def via(n, point, diameter=.8, drill=.4, purpose='power'):
        n = net(n)
        v = p.PCB_VIA(board); v.SetPosition(V(point)); v.SetWidth(MM(diameter))
        v.SetDrill(MM(drill)); v.SetViaType(p.VIATYPE_THROUGH)
        v.SetLayerPair(p.F_Cu, p.B_Cu); v.SetNet(n); v.SetLocked(True)
        v.SetFrontTentingMode(p.TENTING_MODE_TENTED)
        v.SetBackTentingMode(p.TENTING_MODE_TENTED)
        board.Add(v); created.append(v)
        records['vias'].append({'uuid': v.m_Uuid.AsString(), 'net': n.GetNetname(),
            'xy': point, 'diameter_mm': diameter, 'drill_mm': drill, 'purpose': purpose})
        return v

    def zone(n, points, layer, name, clearance=.4, priority=5, keepout=False):
        z = p.ZONE(board); z.SetLayer(layer); z.SetZoneName('COMPACT_POWER / '+name)
        z.SetLocalClearance(MM(clearance)); z.SetPadConnection(p.ZONE_CONNECTION_FULL)
        z.SetMinThickness(MM(.2)); z.SetAssignedPriority(priority)
        if keepout:
            z.SetIsRuleArea(True); z.SetDoNotAllowZoneFills(True)
            z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False)
            z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        else:
            z.SetNet(net(n))
        outline = z.Outline(); outline.NewOutline()
        for point in points:
            outline.Append(MM(point[0]), MM(point[1]))
        board.Add(z); created.append(z)
        records['zones'].append({'uuid': z.m_Uuid.AsString(), 'net': None if keepout else net(n).GetNetname(),
            'layer': board.GetLayerName(layer), 'name': name, 'points': points,
            'clearance_mm': clearance, 'keepout': keepout})
        return z

    def rect(x0, y0, x1, y1):
        return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]

    # Source may already have planes, but this script owns only its own copper.
    # A fresh placed input is expected; never rip up unrelated signal routing.
    assert not any(z.GetZoneName().startswith('COMPACT_POWER /') for z in board.Zones()), \
        'Input already contains this generated copper; rerun from the placed source.'
    zone('GND', rect(.5,.5,59.5,59.5), p.In1_Cu, 'GND reference In1', .2, 0)
    zone('GND', rect(.5,.5,59.5,59.5), p.In4_Cu, 'GND reference In4', .2, 0)
    zone('VBUS', [(11,6),(50.5,6),(50.5,3),(53.8,3),(53.8,6),(55.8,6),(55.8,58.8),(34.8,58.8),(34.8,12),(11,12)],
         p.In3_Cu, 'VBUS inner distribution', .4)
    zone('VBUS', [(11,6),(42.8,6),(42.8,51.4),(34.8,51.4),(34.8,12),(11,12)],
         p.F_Cu, 'VBUS parallel front spine', .4)

    for index, phase in enumerate('UVW'):
        high = 'Q'+str(1+2*index); low = 'Q'+str(2+2*index)
        rs = 'RS'+str(index+1); amp = 'U'+str(10+index)
        high_d = xy(pad(high,5,True)); low_d = xy(pad(low,5,True)); y = high_d[1]
        ph = net_of(high,1); source_n = net_of(low,1)
        source1 = xy(pad(low,1)); rs_hi = xy(pad(rs,1)); rs_lo = xy(pad(rs,2))
        assert ph.GetNetCode() == net_of(low,5).GetNetCode()
        assert source_n.GetNetCode() == net_of(rs,1).GetNetCode()
        assert source_n.GetNetname() != 'GND'
        # Two parallel external PHASE sheets. Source and drain arrays are two
        # transfers in series, each with four parallel plated barrels.
        zone(ph, rect(44,y-2,59,y+5), p.B_Cu, phase+' PHASE back power', .4, 10)
        zone(ph, rect(43.1,y-1.0,52.0,y+4.9), p.F_Cu, phase+' PHASE front commutation', .4, 10)
        source_bank = [(45.1+dx,y+dy) for dx in [0,1.4] for dy in ([1.0,2.4] if index==2 else [1.4,2.8])]
        drain_bank = ([(47.9,y+4.8),(49.0,y+4.8),(47.9,y+5.9),(49.0,y+5.9)] if index==2
                      else [(47.5+dx,y+dy) for dx in [0,1.4] for dy in [3.0,4.4]])
        for pt in source_bank:via(ph,pt,purpose=phase+' PHASE source transfer')
        for pt in drain_bank:via(ph,pt,.7 if index==2 else .8,.35 if index==2 else .4,purpose=phase+' PHASE drain transfer')
        if index==2:
            for layer in [p.F_Cu,p.B_Cu]:
                zone(ph,rect(47.4,y+4.4,49.5,y+6.3),layer,'W drain-bank local extension',.4,11)
        # Fixed 4 mm B exit ensures the output never relies on the thin VS net.
        out = xy(pad('J4',index+1))
        path(ph,[low_d,(out[0],low_d[1]),out],4.0,p.B_Cu,phase+' main output')
        # Low-side SOURCE can only reach ground through this physical shunt.
        bar_x = source1[0]+.175
        for k in [1,2,3]:
            a = xy(pad(low,k))
            path(source_n,[a,(bar_x,a[1]),(bar_x,y+.635)],.65,p.F_Cu,phase+' SOURCE pin neck')
        path(source_n,[(bar_x,y+.635),(bar_x,rs_hi[1]),rs_hi],2.0,p.F_Cu,phase+' SOURCE main stem')
        # Four GND vias fan from a broad local branch on the OUTER side of RS.
        gnode = (rs_lo[0]+.5,rs_lo[1])
        path('GND',[rs_lo,gnode,(gnode[0],y+9.0)],2.0,p.F_Cu,phase+' shunt return main')
        for dy in [6.2,7.6,9.0,10.4]:
            pt=(53.4,y+dy); via('GND',pt,purpose=phase+' shunt return four-barrel bank')
            path('GND',[(gnode[0],y+9.0),pt],.8,p.F_Cu,phase+' shunt individual via spoke')
        # Front VBUS drain/MLCC access to the local In3 link plane. The lower W
        # comparator prevents reuse of U/V's rectangular bank on that phase.
        if index<2:
            hv_bank=[(35.6+dx,y+dy) for dx in [0,1.4] for dy in [3.7,5.1]]
        else:
            hv_bank=[(37.6,y+3.4),(39.0,y+3.4),(40.4,y+3.4),(38.5,y+4.8)]
        for pt in hv_bank:
            via('VBUS',pt,purpose=phase+' drain VBUS four-barrel bank')
        # Short component-side gate resistor branch (driver routing is separate).
        for rr,qq in [('R'+str(19+6*index),high),('R'+str(20+6*index),low)]:
            a=xy(pad(rr,2)); dest=xy(pad(qq,4))
            path(net_of(qq,4),[a,dest],.4,p.F_Cu,phase+' gate resistor to MOS')
        # Kelvin branches leave the INNER shunt-pad edges, independently of the
        # high-current SOURCE/right-hand GND copper above. GND sense through-via
        # is explicitly isolated from both ground pours by local rule areas.
        ip=xy(pad(amp,8)); im=xy(pad(amp,1))
        pv=(50.3 if index==2 else 49.2,y+6.2); nv=(49.0,y+(10.1 if index==2 else 10.2))
        padhalf=p.ToMM(pad(rs,1).GetSize().x)/2  # before270 pad x is the short dimension
        pos_origin=(rs_hi[0]-1.35,rs_hi[1]+.45)
        neg_origin=(rs_lo[0]-1.35,rs_lo[1]-.45)
        pos_ids=path(source_n,[pos_origin,pv],.2,p.F_Cu,phase+' positive Kelvin')
        neg_ids=path('GND',[neg_origin,nv],.2,p.F_Cu,phase+' negative Kelvin')
        pos_via=via(source_n,pv,.6,.3,phase+' positive Kelvin')
        neg_via=via('GND',nv,.6,.3,phase+' negative Kelvin isolated from planes')
        outer_x=ip[0]+.9625
        pos_back=[pv,(outer_x,pv[1]),(outer_x,ip[1]+.525),ip]
        neg_back=[nv,(im[0]+1.1375,nv[1]),im]
        pos_ids+=path(source_n,pos_back,.2,p.B_Cu,phase+' positive Kelvin')
        neg_ids+=path('GND',neg_back,.2,p.B_Cu,phase+' negative Kelvin')
        for plane in [p.In1_Cu,p.In4_Cu]:
            zone(None,rect(nv[0]-.7,nv[1]-.7,nv[0]+.7,nv[1]+.7),plane,
                 phase+' negative Kelvin plane isolation',0,20,True)
        records['kelvin'].append({'phase':phase,'RS':rs,'INA':amp,'source_pad':rs_hi,'ground_pad':rs_lo,
            'positive_origin':pos_origin,'negative_origin':neg_origin,
            'positive_via':pv,'negative_via':nv,'positive_B_path':pos_back,'negative_B_path':neg_back,
            'positive_track_uuids':pos_ids,'negative_track_uuids':neg_ids,
            'positive_via_uuid':pos_via.m_Uuid.AsString(),'negative_via_uuid':neg_via.m_Uuid.AsString(),
            'negative_via_ground_planes_isolated':True,'width_mm':.2})
        records['critical'].append({'phase':phase,'source_bank':source_bank,'drain_bank':drain_bank,
            'VBUS_bank':hv_bank,'vias_per_phase_transfer':4,'phase_transfers_in_series':2,
            'parallel_barrels_per_transfer':4,'SOURCE_common_width_mm':2,'B_output_width_mm':4})

    # Shared MLCC branches remain local to the actual pads and the broad link.
    for ref in ['C21','C22']:
        pp=xy(pad(ref,1)); gg=xy(pad(ref,2)); yy=pp[1]
        path('VBUS',[pp,(37.0,yy-.2)],2,p.F_Cu,ref+' VBUS wide access')
        # Two barrels here carry capacitor ripple; main shunt and bridge
        # transfers independently retain their four-barrel banks.
        for point in [(40.5,yy-1.9),(41.9,yy-1.9)]:
            via('GND',point,purpose=ref+' ripple GND')
            path('GND',[gg,(gg[0],point[1]),point],1.3,p.F_Cu,ref+' GND wide access')

    # DC input/fuse: F and In2 parallel conductors turn around DC- instead of
    # crossing the adjacent negative terminal. Each fuse transfer has four vias.
    inp=xy(pad('J3',1)); fi=xy(pad('F1',1)); fo=xy(pad('F1',2))
    dcpath=[inp,(1.5,inp[1]),(1.5,fi[1]),fi]
    path(net_of('J3',1),dcpath,2,p.F_Cu,'DC input outer conductor')
    path(net_of('J3',1),dcpath[:-1]+[(2.5,fi[1])],2,p.In2_Cu,'DC input parallel inner conductor')
    for point in [(1.1,fi[1]-1.4),(2.5,fi[1]-1.4),(1.1,fi[1]),(2.5,fi[1])]:
        via(net_of('J3',1),point,purpose='DC input fuse four-barrel transfer')
        path(net_of('J3',1),[fi,point],1,p.F_Cu,'DC input individual fuse-via spoke')
    fuse_bank=[(8.7,16.0),(9.9,16.0),(8.7,17.4),(9.9,17.4)]
    path(net_of('F1',2),[fo,(fo[0],17.4)],2,p.F_Cu,'fuse output broad common neck')
    for point in fuse_bank:
        via(net_of('F1',2),point,purpose='DC FUSED four-barrel transfer')
        path(net_of('F1',2),[(fo[0],17.4),point],.8,p.F_Cu,'fuse output individual parallel via spoke')
    path(net_of('F1',2),[(9.9,17.4),(9.9,15),(9.9,5),(46.8,5)],2.4,p.In2_Cu,'fused DC main feed')
    path(net_of('F1',2),[(9.9,17.4),(9.9,15),(9.9,5),(46.8,5)],2.4,p.In3_Cu,'fused DC parallel main feed')
    anode_upper=min([pad('D1',1),pad('D1',3)],key=lambda a:xy(a)[1])
    anode_lower=max([pad('D1',1),pad('D1',3)],key=lambda a:xy(a)[1])
    upper_bank=[(45.4,3.8),(46.8,3.8),(45.4,5.2),(46.8,5.2)]
    lower_bank=[(46.8,12.5),(48.2,12.5)]
    for point in upper_bank+lower_bank:
        via(net_of('F1',2),point,purpose='rectifier anode supply')
    zone(net_of('F1',2),rect(45.0,3.4,47.3,7.5),p.B_Cu,'upper rectifier anode via fanout',.4,5)
    path(net_of('F1',2),[(46.8,5),(46.8,5.2)],2.4,p.In2_Cu,'upper rectifier feed')
    path(net_of('F1',2),[(46.8,5),(48.2,5),(48.2,12.5),(46.8,12.5)],2,p.In2_Cu,'lower rectifier feed')
    path(net_of('F1',2),[(46.8,5),(46.8,5.2)],2.4,p.In3_Cu,'upper rectifier parallel feed')
    path(net_of('F1',2),[(46.8,5),(48.2,5),(48.2,12.5),(46.8,12.5)],2,p.In3_Cu,'lower rectifier parallel feed')
    path(net_of('F1',2),[(46.8,5.2),xy(anode_upper)],2,p.B_Cu,'upper rectifier anode')
    path(net_of('F1',2),[(46.8,12.5),xy(anode_lower)],2,p.B_Cu,'lower rectifier anode')
    path(net_of('F1',2),[xy(anode_lower),(48.2,12.5)],1.3,p.B_Cu,'lower rectifier second via spoke')
    cathode=xy(pad('D1',2,True))
    path('VBUS',[xy(pad('D1',2)),cathode],1.2,p.B_Cu,'rectifier cathode lead to tab')
    for point in [(51.5,3.8),(52.9,3.8),(51.5,5.2),(52.9,5.2)]:
        via('VBUS',point,purpose='rectifier cathode four-barrel transfer')
        path('VBUS',[cathode,(cathode[0],point[1]),point],3,p.B_Cu,'rectifier VBUS broad neck')

    # Brake drain has a wide In2 switched-return branch to the separate pad.
    qd=xy(pad('Q7',5,True)); qs=xy(pad('Q7',1)); brs=xy(pad('J5',2))
    zone(net_of('Q7',5),rect(26.3,qd[1]-2.6,qd[0]+2.6,57.4),p.F_Cu,'brake drain front island',.4)
    zone(net_of('Q7',5),rect(26.3,52,31.5,57.4),p.In2_Cu,'brake drain inner access',.4)
    for point in [(30.6,56.9),(29.0,56.9),(27.2,55.3),(26.8,56.7)]:
        via(net_of('Q7',5),point,purpose='brake drain four-barrel transfer')
    path(net_of('Q7',5),[(30.6,56.9),(30.6,52),(35.8,52),(37.2,53),(brs[0],53),brs],2.4,p.In2_Cu,'brake switched-return main')
    for k in [1,2,3]:
        a=xy(pad('Q7',k))
        path('GND',[a,(34.3,a[1]),(34.3,qs[1])],.65,p.F_Cu,'brake SOURCE pin neck')
    path('GND',[(34.05,qs[1]),(34.3,qs[1])],2,p.F_Cu,'brake GND broad common neck')
    for yy in [54.2,55.6,57.0,58.4]:
        point=(34.9,yy);via('GND',point,purpose='brake SOURCE GND four-barrel transfer')
        path('GND',[(34.3,qs[1]),point],.8,p.F_Cu,'brake individual GND via spoke')
    path(net_of('Q7',4),[xy(pad('R17',2)),xy(pad('Q7',4))],.4,p.F_Cu,'brake gate resistor to MOS')

    # Exact-duplicate helper branches need not burden downstream autorouting.
    seen=set()
    for t in list(board.GetTracks()):
        if isinstance(t,p.PCB_VIA):
            continue
        key=(t.GetNetCode(),t.GetLayer(),t.GetWidth(),tuple(sorted([(t.GetStart().x,t.GetStart().y),(t.GetEnd().x,t.GetEnd().y)])))
        if key in seen:
            board.Remove(t)
        else:
            seen.add(key)
    board.BuildConnectivity()
    if not args.no_fill:
        p.ZONE_FILLER(board).Fill(board.Zones())
    # KiCad connectivity can propagate a via's net across touching conductors.
    # Check intended identities explicitly: a reassigned PHASE via must never
    # turn a physical short into an apparently clean same-net DRC warning.
    expected={a['uuid']:a['net'] for a in records['tracks']+records['vias']+records['zones']
              if not a.get('keepout')}
    net_mutations=[]
    for item in list(board.GetTracks())+list(board.Zones()):
        uid=item.m_Uuid.AsString()
        if uid in expected and item.GetNetname()!=expected[uid]:
            net_mutations.append({'uuid':uid,'expected':expected[uid],'actual':item.GetNetname()})
    assert not net_mutations,('Connectivity changed intended fixed-net identities',net_mutations)
    p.SaveBoard(str(output),board)
    private_pro.write_bytes(project_bytes)
    report=output.with_name('power_copper.json')
    actual=p.LoadBoard(str(output))
    saved_items={a.m_Uuid.AsString():a for a in list(actual.GetTracks())+list(actual.Zones())}
    for uid,name in expected.items():
        if uid in saved_items:assert saved_items[uid].GetNetname()==name,('Saved net identity changed',uid,name)
    records['removed_exact_duplicate_track_uuids']=[a['uuid'] for a in records['tracks'] if a['uuid'] not in saved_items]
    records['tracks']=[a for a in records['tracks'] if a['uuid'] in saved_items]
    records['connectivity_audit']=audit_power_connectivity(actual,records) if not args.no_fill else {'skipped':'--no-fill debug run'}
    records.update(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),fixed_net_identity_mutations=net_mutations,
        candidate=str(output),status='power copper candidate; actual DRC and heat validation required',
        copper_um=35,layers=6,limitations=['Placement/DRC does not validate 10 A temperature rise, current sharing or switching overshoot.',
        'SOURCE pin fanout uses three short0.65mm necks before a2mm common stem.',
        'Each phase has four source-transfer vias and four drain-transfer vias IN SERIES, never eight parallel vias.',
        'No ordinary tracks use In1/In4; negative Kelvin GND vias have local pour keepouts on both planes.'])
    report.write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    print('Private candidate:',output,'tracks/vias',len(list(board.GetTracks())),'zones',len(list(board.Zones())),flush=True)
    if args.drc:
        cli=Path('C:/Program Files/KiCad/10.0/bin/kicad-cli.exe')
        drc=output.with_name('power_drc.json')
        result=subprocess.run([str(cli),'pcb','drc','--format','json','--output',str(drc),str(output)],capture_output=True,text=True)
        print(result.stdout,result.stderr,flush=True)
        if drc.exists():
            data=json.loads(drc.read_text(encoding='utf-8'))
            errors=[a for a in data.get('violations',[]) if a.get('severity')=='error']
            warnings=[a for a in data.get('violations',[]) if a.get('severity')=='warning']
            records['actual_drc']={'errors':len(errors),'warnings':len(warnings),
                'warning_types':sorted({a['type'] for a in warnings}),
                'unconnected_items':len(data.get('unconnected_items',[])),
                'file':str(drc),'candidate_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
            if not errors and not args.no_fill:
                records['status']='Fixed main-power and Kelvin geometry verified; ordinary signal routing remains incomplete.'
            report.write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
            print('Actual DRC electrical/geometry errors:',len(errors),'unconnected',len(data.get('unconnected_items',[])),flush=True)


if __name__=='__main__':
    main()

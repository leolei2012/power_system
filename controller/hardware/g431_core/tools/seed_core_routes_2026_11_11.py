"""Add native-geometry-checked local core routes and reference planes.

Run only on the placed, unrouted current Rev E core. Never touches schematics,
public libraries or another board. All accepted seed copper is locked so the
ordinary GPIO autorouter cannot silently replace the critical local paths.
"""
from pathlib import Path
import json,math,shutil
import pcbnew as p

BASE=Path(__file__).resolve().parents[1]
BOARD=BASE/'controller.kicad_pcb'
OUT=BASE/'review/pcb_2026-11-11'
MM=p.FromMM
V=lambda x,y:p.VECTOR2I(MM(x),MM(y))
XY=lambda q:(p.ToMM(q.x),p.ToMM(q.y))


def smd_copper_layer(pad):
    """Get the effective pad copper side, including flipped footprints.

    PAD.GetLayer() can retain F.Cu on a flipped SMD pad in KiCad 10; the
    effective layer set determines which side a physical stub must contact.
    """
    return p.B_Cu if pad.IsOnLayer(p.B_Cu) and not pad.IsOnLayer(p.F_Cu) else p.F_Cu


class Geometry:
    def __init__(self,board):
        self.board=board;self.layers=[p.F_Cu,p.In1_Cu,p.In2_Cu,p.B_Cu]
        self.objects=[];self.holes=[];self.smd=[];self.keep=[]
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetAttribute()==p.PAD_ATTRIB_NPTH:
                    continue
                for ly in self.layers:
                    if pad.IsOnLayer(ly):
                        self.objects.append((pad.GetEffectiveShape(ly),ly,pad.GetNetCode()))
                if pad.GetAttribute()==p.PAD_ATTRIB_SMD and any(pad.IsOnLayer(ly) for ly in self.layers):
                    self.smd.append(pad.GetEffectiveShape(smd_copper_layer(pad)))
                if pad.GetDrillSize().x:
                    self.holes.append((pad.GetEffectiveHoleShape(),pad.GetNetCode()))
        for item in board.GetTracks():self.add(item)
        for raw in board.Zones():
            z=p.Cast_to_ZONE(raw) if not isinstance(raw,p.ZONE) else raw
            if z.GetIsRuleArea():self.keep.append(z.Outline())

    def inside(self,at,r):
        return 100.5+r<=at[0]<=159.5-r and 100.5+r<=at[1]<=159.5-r

    def line_ok(self,a,b,ly,code,width):
        if not self.inside(a,width/2) or not self.inside(b,width/2):return False
        s=p.SHAPE_SEGMENT(V(*a),V(*b),MM(width))
        if any(o.Collide(s,0) for o in self.keep):return False
        if any(layer==ly and nc!=code and sh.Collide(s,MM(.15)) for sh,layer,nc in self.objects):return False
        return not any(nc!=code and sh.Collide(s,MM(.25)) for sh,nc in self.holes)

    def via_ok(self,at,code):
        if not self.inside(at,.3):return False
        s=p.SHAPE_CIRCLE(V(*at),MM(.3));drill=p.SHAPE_CIRCLE(V(*at),MM(.15))
        if any(sh.Collide(s,0) for sh in self.keep):return False
        if any(nc!=code and sh.Collide(s,MM(.15)) for sh,_,nc in self.objects):return False
        if any(sh.Collide(s,MM(.05)) for sh in self.smd):return False
        return not any(sh.Collide(drill,MM(.25)) for sh,_ in self.holes)

    def add(self,item):
        for ly in self.layers:
            if item.IsOnLayer(ly):self.objects.append((item.GetEffectiveShape(ly),ly,item.GetNetCode()))
        if isinstance(item,p.PCB_VIA):self.holes.append((item.GetEffectiveHoleShape(),item.GetNetCode()))


def main():
    OUT.mkdir(exist_ok=True,parents=True)
    b=p.LoadBoard(str(BOARD));assert not list(b.GetTracks()),'Seed is a one-time operation on an unrouted placed board.'
    pro=BOARD.with_suffix('.kicad_pro');project_bytes=pro.read_bytes()
    shutil.copy2(BOARD,OUT/'before_seed.kicad_pcb')
    fps={f.GetReference():f for f in b.GetFootprints()}
    # A 180-degree crystal reversal keeps the two oscillator paths in the same
    # order and avoids crossing them. Both load capacitors remain DNP.
    fps['Y1'].SetOrientationDegrees(90)
    fps['C83'].SetPosition(V(125.7,135.4));fps['C84'].SetPosition(V(124.7,128.8))
    pads={(f.GetReference(),a.GetNumber()):a for f in b.GetFootprints() for a in f.Pads() if a.GetNumber()}
    g=Geometry(b);paths=[];vias=[];fail=[]
    def pad(ref,num):return pads[ref,str(num)]
    def path(net,points,ly,width=.2,why=''):
        points=[tuple(map(float,pt)) for pt in points]
        ni=b.FindNet(net);assert ni and ni.GetNetCode()>0,net
        if not all(g.line_ok(a,z,ly,ni.GetNetCode(),width) for a,z in zip(points,points[1:])):return False
        for a,z in zip(points,points[1:]):
            if a==z:continue
            t=p.PCB_TRACK(b);t.SetStart(V(*a));t.SetEnd(V(*z));t.SetWidth(MM(width));t.SetLayer(ly);t.SetNet(ni);t.SetLocked(True);b.Add(t);g.add(t)
        paths.append({'net':net,'layer':p.LayerName(ly),'width':width,'points':points,'reason':why})
        return True
    def link(a,z,width=.2,points=None,why=''):
        aa,zz=pad(*a),pad(*z);assert aa.GetNetCode()==zz.GetNetCode(),(a,z)
        ly=smd_copper_layer(aa)
        if not zz.IsOnLayer(ly):fail.append({'from':a,'to':z,'reason':'different layers'});return False
        start,end=XY(aa.GetPosition()),XY(zz.GetPosition())
        candidates=[[start]+(points or [])+[end]] if points else []
        dx,dy=end[0]-start[0],end[1]-start[1];m=min(abs(dx),abs(dy));sx=1 if dx>=0 else -1;sy=1 if dy>=0 else -1
        candidates += [[start,end],[start,(start[0]+sx*m,start[1]+sy*m),end],
                       [start,(end[0]-sx*m,end[1]-sy*m),end],
                       [start,(end[0],start[1]),end],[start,(start[0],end[1]),end]]
        for offset in [.6,1.,1.5,2.]:
            candidates += [[start,(start[0],start[1]+sign*offset),(end[0],start[1]+sign*offset),end] for sign in [-1,1]]
            candidates += [[start,(start[0]+sign*offset,start[1]),(start[0]+sign*offset,end[1]),end] for sign in [-1,1]]
        for pts in candidates:
            if path(aa.GetNetname(),pts,ly,width,why):return True
        fail.append({'from':a,'to':z,'reason':'native clearance blocked direct/local doglegs','critical':why})
        return False
    def drop(a,preferred=None):
        aa=pad(*a);net=aa.GetNetname();code=aa.GetNetCode();at=XY(aa.GetPosition())
        if aa.GetAttribute()==p.PAD_ATTRIB_PTH:return True
        ly=smd_copper_layer(aa)
        # Prefer inward escape for the fine-pitch MCU; outward for passive parts.
        centre=XY(aa.GetParentFootprint().GetPosition())
        angle=math.atan2(centre[1]-at[1],centre[0]-at[0]) if a[0]=='U30' else math.atan2(at[1]-centre[1],at[0]-centre[0])
        choices=[preferred] if preferred else []
        for radius in [.85,1.,1.3,1.6,2.,2.5]:
            for k in [0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7,8]:
                t=angle+k*math.pi/8
                choices.append((round(at[0]+radius*math.cos(t),3),round(at[1]+radius*math.sin(t),3)))
        for pt in choices:
            if not g.via_ok(pt,code) or not g.line_ok(at,pt,ly,code,.2):continue
            via=p.PCB_VIA(b);via.SetPosition(V(*pt));via.SetWidth(MM(.6));via.SetDrill(MM(.3));via.SetViaType(p.VIATYPE_THROUGH);via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetNet(aa.GetNet());via.SetLocked(True)
            if not path(net,[at,pt],ly,.2,'local plane return/feed'):continue
            b.Add(via);g.add(via);vias.append({'net':net,'x':pt[0],'y':pt[1],'diameter':.6,'drill':.3,'from_pad':a})
            return True
        fail.append({'pad':a,'reason':'no short clearance-safe plane via'})
        return False

    for a,z,points in [
        (('U30',16),('C63',1),[(123.75,126.25),(124.38,126.88)]),
        (('U30',32),('C64',1),None),
        (('U30',64),('C66',1),None),
        (('U30',29),('C77',1),None),
        (('U30',28),('C79',1),[(114.75,123.2),(116,123.2)]),
        (('R92',2),('C78',1),None),(('R92',2),('R93',1),None),
        (('C78',1),('C77',1),None),(('R93',2),('C80',1),None),
        (('C80',1),('C79',1),[(115.4,120.725),(115.4,122.1),(115.7,122.63)]),
        (('U30',6),('Y1',3),None),
        (('U30',5),('Y1',1),[(123.25,131.75),(123.5,132),(125.95,132)]),
        (('Y1',3),('C84',1),None),(('Y1',1),('C83',1),None),
        (('D102',1),('C302',1),None),(('C302',1),('U101',6),None),
        (('U101',6),('U101',4),[(130.8,106.65),(130.8,105.35)]),
        (('U101',1),('U101',2),None),(('U101',1),('C303',1),None),
        (('C303',1),('C304',1),None),(('D103',2),('C304',1),None),
        (('D103',1),('U101',6),None),
        (('U101',5),('U101',7),None),(('U101',3),('U101',7),None),
        (('U102',5),('U102',6),None),(('U102',5),('C306',1),None),
        (('U103',5),('C307',1),None),(('U105',5),('C308',1),None),
        (('R302',2),('U104',2),None),(('R303',1),('U104',2),None),
        (('SW3',2),('R401',1),None),(('R401',2),('TP15',1),None),
        (('R301',2),('D101',1),None),
        (('D101',1),('D102',2),[(113.165,103.8),(118,103.8),(120.7,106.5)]),
        (('D102',2),('C301',1),[(120.7,109),(118.825,110.875)]),
        (('J101',1),('J101',3),None),
        (('J101',1),('R301',1),[(104.73,108.8),(111.2,108.8)]),
    ]:
        width=.15 if a[0]=='Y1' or z[0]=='Y1' else .25 if a[0] in ('D102','U101') else .2
        link(a,z,width,points,'critical local supply / oscillator / analog path')

    # Existing opposite-side decoupling and pulls get a local through-via,
    # avoiding hidden via-in-pad fabrication assumptions.
    for a,z,via in [(('U30',48),('C65',1),(112.0,134.5)),
                    (('U30',1),('C67',1),(120.6,132.5)),
                    (('U30',7),('C81',1),(120.0,130.75)),
                    (('U30',39),('R402',1),(112.0,128.2)),
                    (('U30',61),('R122',1),(118.75,137.0))]:
        aa,zz=pad(*a),pad(*z);assert aa.GetNetCode()==zz.GetNetCode()
        ni=aa.GetNet();start=XY(aa.GetPosition());end=XY(zz.GetPosition());code=aa.GetNetCode()
        if g.via_ok(via,code):
            alternatives=[[start,via],[start,(via[0],start[1]),via],[start,(start[0],via[1]),via]]
            ba=[[end,via],[end,(via[0],end[1]),via],[end,(end[0],via[1]),via]]
            first=next((q for q in alternatives if all(g.line_ok(x,y,p.F_Cu,code,.15) for x,y in zip(q,q[1:]))),None)
            second=next((q for q in ba if all(g.line_ok(x,y,p.B_Cu,code,.15) for x,y in zip(q,q[1:]))),None)
            if first and second:
                path(ni.GetNetname(),first,p.F_Cu,.15,'local MCU-to-backside decoupler/pull')
                path(ni.GetNetname(),second,p.B_Cu,.15,'local MCU-to-backside decoupler/pull')
                v=p.PCB_VIA(b);v.SetPosition(V(*via));v.SetWidth(MM(.6));v.SetDrill(MM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(ni);v.SetLocked(True);b.Add(v);g.add(v)
                vias.append({'net':ni.GetNetname(),'x':via[0],'y':via[1],'diameter':.6,'drill':.3,'reason':'MCU to B local component'})
                continue
        fail.append({'from':a,'to':z,'reason':'backside critical local link blocked'})

    # Ground return drops are prioritized before supply vias. Every via is
    # checked against real native copper, all through-holes and the M2 rules.
    for a in [('U30',15),('U30',27),('U30',31),('U30',47),('U30',63)]:drop(a)
    for key,aa in pads.items():
        if aa.GetNetname()=='GND' and key[0]!='U30':drop(key)
    for a in [('C63',1),('C64',1),('C65',1),('C66',1),('C67',1),('C68',1),
              ('R92',1),('C303',1),('C304',1),('C305',1),('C306',1),('C307',1),('C308',1),
              ('R302',1),('U104',1),('R306',1),('SW3',1)]:drop(a)

    for layer,net in [(p.In1_Cu,'GND'),(p.In2_Cu,'+3V3_MCU')]:
        z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet(net));z.SetZoneName('CORE '+net+' reference plane')
        z.SetLocalClearance(MM(.15));z.SetMinThickness(MM(.2));z.SetPadConnection(p.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(.2));z.SetThermalReliefSpokeWidth(MM(.3))
        o=z.Outline();o.NewOutline()
        for x,y in [(100.5,100.5),(159.5,100.5),(159.5,159.5),(100.5,159.5)]:o.Append(MM(x),MM(y))
        b.Add(z)
    p.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity();p.SaveBoard(str(BOARD),b);pro.write_bytes(project_bytes)
    report={'status':'CRITICAL SEED REVIEW','paths':paths,'vias':vias,'blocked_local_links':fail,
            'locked_seed_segments':sum(not isinstance(t,p.PCB_VIA) for t in b.GetTracks()),
            'locked_seed_vias':sum(isinstance(t,p.PCB_VIA) for t in b.GetTracks()),
            'native_unconnected':b.GetConnectivity().GetUnconnectedCount(False),
            'note':'HSE nets also remain exported on GPIO header; startup/load must account for those branches.'}
    (OUT/'seed_routes.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['paths','vias']},indent=2))


if __name__=='__main__':main()

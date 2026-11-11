"""Create the first review PCB from the actual KiCad XML and reviewed placement tables.

Run with KiCad's bundled Python. This is an authoring record, not a command to
rerun over a board edited by hand. No fabrication output is generated here.
"""
from pathlib import Path
import collections
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
import pcbnew as p

B = Path(__file__).resolve().parents[1]
STD = Path('C:/Program Files/KiCad/10.0/share/kicad/footprints')
SHARED = B.parents[2] / 'kicad_library/footprints/MyFootprints.pretty'
REVIEW = B / 'review'
MM = p.FromMM
V = lambda x, y: p.VECTOR2I(MM(x), MM(y))
BOARD_PATH = B / 'inverter.kicad_pcb'


def load_inputs():
    tree = ET.parse(REVIEW / 'inverter.net.xml').getroot()
    candidates = json.loads((B/'tools/pcb_footprint_candidates.json').read_text(encoding='utf-8'))
    positions = {}
    for filename in ['pcb_power_placement.json', 'pcb_control_placement.json']:
        data = json.loads((B/'tools'/filename).read_text(encoding='utf-8'))
        for ref, spec in data['placements'].items():
            assert ref not in positions, ('duplicate placement owner', ref)
            positions[ref] = spec
    return tree, candidates, positions


def text(board, value, x, y, layer=p.F_SilkS, size=1.0):
    t = p.PCB_TEXT(board); t.SetText(value); t.SetPosition(V(x,y))
    t.SetLayer(layer); t.SetTextSize(V(size,size)); t.SetTextThickness(MM(.15))
    board.Add(t)
    return t


def segment(board, net, a, b, width=.25, layer=p.F_Cu, locked=True):
    if a == b: return
    t = p.PCB_TRACK(board); t.SetStart(V(*a)); t.SetEnd(V(*b))
    t.SetWidth(MM(width)); t.SetLayer(layer); t.SetNet(net)
    t.SetLocked(locked); board.Add(t)
    return t


def path(board, net, points, width=.25, layer=p.F_Cu):
    for a,b in zip(points,points[1:]): segment(board,net,a,b,width,layer)


def xy(pad):
    a=pad.GetPosition(); return (round(p.ToMM(a.x),6),round(p.ToMM(a.y),6))


def pad(footprints, ref, number, largest=False):
    pads=[a for a in footprints[ref].Pads() if a.GetNumber()==str(number)]
    assert pads,(ref,number)
    return max(pads,key=lambda a:a.GetSize().x*a.GetSize().y) if largest else pads[0]


def bbox(fp, margin=0):
    shape=fp.GetCourtyard(p.F_CrtYd)
    bb=shape.BBox() if shape.OutlineCount() else fp.GetBoundingBox(False,False)
    return (p.ToMM(bb.GetX())-margin,p.ToMM(bb.GetY())-margin,
            p.ToMM(bb.GetRight())+margin,p.ToMM(bb.GetBottom())+margin)


def overlap(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>.001 and min(a[3],b[3])-max(a[1],b[1])>.001


def resolve_placement(fps, placements):
    """Keep anchors and large packages first; nudge small passives out of courtyards."""
    fixed=[]; moves=[]
    refs=sorted(fps,key=lambda r:(0 if r.startswith(('J','H','Q','U','L','F','SW','RS','Y')) else 1,
                                 -(bbox(fps[r])[2]-bbox(fps[r])[0])*(bbox(fps[r])[3]-bbox(fps[r])[1])))
    for ref in refs:
        fp=fps[ref]; origin=xy(fp); box=bbox(fp)
        conflict=any(overlap(box,bbox(other)) for other in fixed)
        inside=box[0]>=.5 and box[1]>=.5 and box[2]<=199.5 and box[3]<=139.5
        if not conflict and inside:
            fixed.append(fp); continue
        best=None
        for radius in [i*.5 for i in range(1,61)]:
            for dx,dy in [(radius,0),(-radius,0),(0,radius),(0,-radius)]+[(radius*math.cos(a*math.pi/8),radius*math.sin(a*math.pi/8)) for a in range(1,16)]:
                nx=round((origin[0]+dx)*4)/4;ny=round((origin[1]+dy)*4)/4
                fp.SetPosition(V(nx,ny)); box=bbox(fp)
                if box[0]<.5 or box[1]<.5 or box[2]>199.5 or box[3]>139.5: continue
                if any(overlap(box,bbox(other)) for other in fixed):continue
                best=(nx,ny);break
            if best:break
        assert best,('cannot place',ref,origin)
        moves.append({'ref':ref,'from':origin,'to':best});fixed.append(fp)
    return moves


def place_references(fps):
    """Find visible silk positions in free space; retain dense labels on assembly layer."""
    occupied=[bbox(fp,.1) for fp in fps.values()]; labels=[]; assembly=[]
    for ref,fp in sorted(fps.items(),key=lambda x:(not x[0].startswith(('U','Q','J','F','RS','L','H')),x[0])):
        box=bbox(fp);cx=(box[0]+box[2])/2;cy=(box[1]+box[3])/2
        field=fp.Reference();field.SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T));field.SetTextSize(V(.8,.8));field.SetTextThickness(MM(.12))
        width=max(.8,.65*.8*len(ref));height=.8;found=None
        for gap in [.65,1.25,1.85,2.45,3.05,3.65,4.25,4.85]:
            for x,y in [(cx,box[1]-gap),(cx,box[3]+gap),(box[0]-gap-width/2,cy),(box[2]+gap+width/2,cy)]:
                rect=(x-width/2-.12,y-height/2-.12,x+width/2+.12,y+height/2+.12)
                if rect[0]<.5 or rect[1]<.5 or rect[2]>199.5 or rect[3]>139.5:continue
                if any(overlap(rect,b) for b in occupied+labels):continue
                found=(x,y);labels.append(rect);break
            if found:break
        if found:field.SetPosition(V(*found));field.SetLayer(p.F_SilkS)
        else:field.SetPosition(V(cx,box[1]-.65));field.SetLayer(p.F_Fab);assembly.append(ref)
    return assembly


def make_zone(board, net, points, layer, name, clearance=.25, priority=0):
    z=p.ZONE(board);z.SetLayer(layer);z.SetNet(net);z.SetZoneName(name)
    z.SetLocalClearance(MM(clearance));z.SetThermalReliefGap(MM(.25))
    z.SetThermalReliefSpokeWidth(MM(.5));z.SetPadConnection(p.ZONE_CONNECTION_FULL)
    z.SetAssignedPriority(priority)
    poly=z.Outline();poly.NewOutline()
    for x,y in points:poly.Append(MM(x),MM(y))
    board.Add(z);return z


def create():
    assert not BOARD_PATH.exists() or '--replace-generated' in sys.argv, 'Refusing to overwrite existing PCB without explicit authoring flag'
    tree, candidates, placements=load_inputs()
    board=p.BOARD();board.SetFileName(str(BOARD_PATH));board.SetCopperLayerCount(4)
    ds=board.GetDesignSettings();ds.SetBoardThickness(MM(1.6))
    ds.m_MinClearance=MM(.15);ds.m_TrackMinWidth=MM(.15);ds.m_CopperEdgeClearance=MM(.5)
    ds.m_ViasMinSize=MM(.6);ds.m_ViasMinAnnularWidth=MM(.15)
    nets={}; classes={}
    for name,width,clearance in [('Default',.2,.15),('Gate',.4,.2),('Auxiliary',.6,.2),('HV',.6,.4)]:
        nc=p.NETCLASS(name);nc.SetTrackWidth(MM(width));nc.SetClearance(MM(clearance));nc.SetViaDiameter(MM(.7));nc.SetViaDrill(MM(.35))
        board.GetNetClasses()[name]=nc;classes[name]=nc
    def class_for(name):
        short=name.rsplit('/',1)[-1]
        if short in ['VBUS','U_PHASE','V_PHASE','W_PHASE','BR_SW','DC_FUSED','DC_INPUT_POS']:return 'HV'
        if any(t in short for t in ['GATE','HO_DRV','LO_DRV','H_DRV','L_DRV']) or short.endswith('_BOOT'):return 'Gate'
        if short.startswith(('+12V','+5V')) or short in ['AUX_IN','AUX_FUSED','AUX_PROTECTED','BB_L1','BB_L2']:return 'Auxiliary'
        return 'Default'
    pin_nets={}
    for node in tree.findall('./nets/net'):
        name=node.attrib['name']; n=p.NETINFO_ITEM(board,name,int(node.attrib['code']))
        board.Add(n);n.SetNetClass(classes[class_for(name)]);nets[name]=n
        for item in node.findall('node'):pin_nets[item.attrib['ref'],item.attrib['pin']]=name
    root_uuid=re.search(r'\(uuid "([^"]+)"\)',(B/'inverter.kicad_sch').read_text(encoding='utf-8')).group(1)
    fps={}; fallback=[]
    for c in tree.findall('./components/comp'):
        ref=c.attrib['ref'];fp_id=c.findtext('footprint') or candidates['footprint_map'].get(ref)
        assert fp_id,('missing footprint',ref)
        library,name=fp_id.split(':',1)
        directory=SHARED if library=='MyFootprints' else STD/(library+'.pretty')
        fp=p.FootprintLoad(str(directory),name);assert fp,('load failed',ref,fp_id)
        fp.SetFPID(p.LIB_ID(library,name));fp.SetReference(ref);fp.SetValue(c.findtext('value'))
        fp.SetSheetname(c.find('sheetpath').attrib['names']);fp.SetSheetfile(next((x.attrib.get('value','') for x in c.findall('property') if x.attrib['name']=='Sheetfile'),''))
        fp.SetPath(p.KIID_PATH('/'+root_uuid+c.find('sheetpath').attrib['tstamps']+c.findtext('tstamps').split()[0]))
        dnp=any(x.attrib['name']=='dnp' for x in c.findall('property'));fp.SetDNP(dnp)
        fp.SetExcludedFromBOM(False)
        for field in c.findall('./fields/field'):
            if field.attrib['name'] not in ['Footprint','Reference','Value']:fp.SetField(field.attrib['name'],field.text or '')
        for prop in c.findall('property'):
            if prop.attrib['name'] not in ['Sheetname','Sheetfile','dnp']:
                fp.SetField(prop.attrib['name'],prop.attrib.get('value',''))
        if ref in candidates['footprint_map']:fp.SetField('PCB_Mechanical_Status','provisional footprint; actual LCSC part not selected')
        loc=placements.get(ref)
        if not loc:
            fallback.append(ref);loc={'x':10+len(fallback)*5,'y':132,'rotation_deg':0,'group':'unassigned'}
        fp.SetOrientationDegrees(loc.get('rotation_deg',loc.get('angle',0)));fp.SetPosition(V(loc['x'],loc['y']))
        for a in fp.Pads():
            number=a.GetNumber()
            if not number:continue
            name_net=pin_nets.get((ref,number));assert name_net is not None,('extra footprint numbered pad',ref,number)
            a.SetNet(nets[name_net])
        board.Add(fp);fps[ref]=fp
        fp.Value().SetVisible(False)
        for f in fp.GetFields():
            if f.GetName() not in ['Reference','Value']:f.SetVisible(False)
    for i,(x,y) in enumerate([(5,5),(195,5),(195,135),(5,135)],1):
        fp=p.FootprintLoad(str(STD/'MountingHole.pretty'),'MountingHole_3.2mm_M3')
        fp.SetReference('H'+str(i));fp.SetPosition(V(x,y));fp.SetAttributes(fp.GetAttributes()|p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES)
        board.Add(fp);fps[fp.GetReference()]=fp;fp.Value().SetVisible(False)
    movements=resolve_placement(fps,placements)
    assembly_refs=place_references(fps)
    for a,b in [((0,0),(200,0)),((200,0),(200,140)),((200,140),(0,140)),((0,140),(0,0))]:
        edge=p.PCB_SHAPE(board);edge.SetShape(p.SHAPE_T_SEGMENT);edge.SetStart(V(*a));edge.SetEnd(V(*b));edge.SetLayer(p.Edge_Cuts);edge.SetWidth(MM(.05));board.Add(edge)
    text(board,'POWER SYSTEM / G431 INVERTER',74,134,size=1.4)
    text(board,'REV B PCB 0.1 / REVIEW DRAFT',73,137,size=1)
    text(board,'12-60V DC / INPUT 10A MAX',151,135,size=1.1)
    text(board,'200 x 140 mm / 4 LAYERS / MECHANICAL CANDIDATES',100,3,p.Dwgs_User,1)
    for ref,label in [('J2','AUX 12-24V'),('J3','DC BUS 12-60V'),('J4','U / V / W'),('J5','BRAKE RESISTOR'),('J9','ENC A'),('J10','ENC B'),('J11','SPI A'),('J12','SPI B'),('J13','SWD'),('J14','TTL 3V3'),('J15','CAN DNP')]:
        f=fps[ref];bb=bbox(f);text(board,label,(bb[0]+bb[2])/2,bb[3]+1.2,size=.9)
    board.BuildConnectivity()
    p.SaveBoard(str(BOARD_PATH),board)
    # Class assignments live in the project file in current KiCad formats.
    pro=json.loads((B/'inverter.kicad_pro').read_text(encoding='utf-8'))
    default=pro['net_settings']['classes'][0]
    result=[]
    for name,nc in classes.items():
        d=dict(default);d.update(name=name,track_width=p.ToMM(nc.GetTrackWidth()),clearance=p.ToMM(nc.GetClearance()),via_diameter=.7,via_drill=.35,priority=0 if name!='Default' else 2147483647);result.append(d)
    pro['net_settings']['classes']=result
    pro['net_settings']['netclass_patterns']=[{'netclass':class_for(n),'pattern':n} for n in nets if class_for(n)!='Default']
    pro['boards']=[{'name':'inverter.kicad_pcb'}]
    (B/'inverter.kicad_pro').write_text(json.dumps(pro,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'status':'PLACED REVIEW DRAFT','components':len(fps)-4,'mounting_holes':4,'size_mm':[200,140],'copper_layers':4,'candidate_footprints':19,'unassigned_placements':fallback,'collision_nudges':movements,'assembly_layer_references':assembly_refs,
            'placements':{r:{'x':xy(f)[0],'y':xy(f)[1],'rotation_deg':f.GetOrientationDegrees(),'footprint':f.GetFPID().GetUniStringLibId(),'group':placements.get(r,{}).get('group','mechanical')} for r,f in fps.items()}}
    (REVIEW/'pcb_placement.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    assert not fallback,('unassigned placements',fallback)
    print(json.dumps({k:report[k] for k in ['components','mounting_holes','size_mm','copper_layers','unassigned_placements']}))


if __name__=='__main__':create()

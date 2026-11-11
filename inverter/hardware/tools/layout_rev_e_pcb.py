"""Fresh Rev E base PCB from current XML; historical tables are XY seeds only.

Run with KiCad bundled Python. This writes only a new review work board and
placement registry. It never imports a historical board, copper, net or DRC.
"""
from pathlib import Path
import collections
import hashlib
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
import pcbnew as p

B=Path(__file__).resolve().parents[1]
ROOT=B.parents[1]
REVIEW=B/'review/pcb_rev_e_2026-11-11'
WORK=REVIEW/'work'
OUT=WORK/'inverter.kicad_pcb'
STD=Path('C:/Program Files/KiCad/10.0/share/kicad/footprints')
SHARED=B.parents[2]/'kicad_library/footprints/MyFootprints.pretty'
MM=p.FromMM
V=lambda x,y:p.VECTOR2I(MM(x),MM(y))


def xy(o):
    q=o.GetPosition();return (round(p.ToMM(q.x),6),round(p.ToMM(q.y),6))


def fp_load(key):
    lib,name=key.split(':',1)
    folder=SHARED if lib=='MyFootprints' else B/'Inverter_Compact.pretty' if lib=='Inverter_Compact' else STD/(lib+'.pretty')
    f=p.FootprintLoad(str(folder),name);assert f,key
    f.SetFPID(p.LIB_ID(lib,name));return f


def bb(shape):
    q=shape.BBox();return tuple(p.ToMM(v) for v in [q.GetX(),q.GetY(),q.GetRight(),q.GetBottom()])


def courtyard(f):
    f.BuildCourtyardCaches();shape=f.GetCourtyard(p.B_CrtYd if f.IsFlipped() else p.F_CrtYd)
    if shape.OutlineCount():return bb(shape)
    q=f.GetBoundingBox(False,False);return tuple(p.ToMM(v) for v in [q.GetX(),q.GetY(),q.GetRight(),q.GetBottom()])


def overlap(a,b,gap=.05):
    return a[0]<b[2]+gap and b[0]<a[2]+gap and a[1]<b[3]+gap and b[1]<a[3]+gap


def move(f,x,y,angle=None):
    if angle is not None:f.SetOrientationDegrees(angle)
    f.SetPosition(V(x,y))


def pad_box(a,extra=.12):
    box=bb(a.GetEffectiveShape(p.F_Cu));return (box[0]-extra,box[1]-extra,box[2]+extra,box[3]+extra)


def create():
    WORK.mkdir(parents=True,exist_ok=True)
    for name in ['fp-lib-table','sym-lib-table']:
        (WORK/name).write_text((B/name).read_text(encoding='utf-8').replace('${KIPRJMOD}',B.as_posix()),encoding='utf-8')
    original_pro=(B/'inverter.kicad_pro').read_bytes()
    backup=REVIEW/'schematic_project_before_pcb.kicad_pro'
    if not backup.exists():backup.write_bytes(original_pro)
    project=json.loads(original_pro)
    project['board']['design_settings']['rules'].update(min_clearance=.15,min_track_width=.15,min_via_diameter=.6,min_via_annular_width=.15,min_through_hole_diameter=.3,min_copper_edge_clearance=.5)
    for nc in project['net_settings']['classes']:
        if nc['name']=='Default':nc.update(clearance=.15,track_width=.15,via_diameter=.6,via_drill=.3)
    project['board']['design_settings']['drc_exclusions']=[]
    project['boards']=[{'name':'inverter.kicad_pcb'}]
    original_pro=(json.dumps(project,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    (WORK/'inverter.kicad_pro').write_bytes(original_pro)
    xml=B/'review/inverter.net.xml';tree=ET.parse(xml).getroot()
    components=tree.findall('./components/comp');assert len(components)==317
    contract=json.loads((ROOT/'docs/pcb_stack_contract_rev_e.json').read_text(encoding='utf-8'))
    board=p.BOARD();board.SetFileName(str(OUT));board.SetCopperLayerCount(6)
    settings=board.GetDesignSettings();settings.SetBoardThickness(MM(1.6))
    settings.m_TrackMinWidth=MM(.15);settings.m_MinClearance=MM(.15)
    settings.m_CopperEdgeClearance=MM(.5);settings.m_ViasMinSize=MM(.6)
    board.SetLayerType(p.In1_Cu,p.LT_POWER);board.SetLayerType(p.In4_Cu,p.LT_POWER)
    nets={};pin_nets={}
    for n in tree.findall('./nets/net'):
        net=p.NETINFO_ITEM(board,n.attrib['name'],int(n.attrib['code']));board.Add(net);nets[n.attrib['name']]=net
        for node in n.findall('node'):pin_nets[node.attrib['ref'],node.attrib['pin']]=n.attrib['name']
    seeds={}
    power_refs=set()
    aux_refs=set()
    for fn in ['compact_power_placement.json','compact_aux_placement.json','compact_control_placement.json']:
        data=json.loads((B/'tools'/fn).read_text(encoding='utf-8'))
        for ref,where in data['placements'].items():
            assert ref not in seeds,ref
            seeds[ref]={k:where[k] for k in ['x','y','rotation_deg','side','group'] if k in where}
            if fn=='compact_power_placement.json':power_refs.add(ref)
            if fn=='compact_aux_placement.json':aux_refs.add(ref)
    power_groups={'bridge_u','bridge_v','bridge_w','current_frontend_u','current_frontend_v','current_frontend_w','main_bus_bypass','phase_output'}
    for ref,where in seeds.items():
        if where.get('group') in power_groups:where['y']+=1.4
    seeds['C20'].update(x=42.9,y=7.4)
    seeds['F1'].update(x=12.3,y=19.5)
    seeds['D1'].update(x=50.4,y=10.3)
    seeds['RS3'].update(x=50.0,y=54.9)
    for ref in ['Q2','Q4','Q6']:seeds[ref]['x']=50.0
    seeds['J5'].update(x=24.5,y=56.7)
    seeds['Q7'].update(x=37.2,y=53.5)
    seeds['U29'].update(x=40.2,y=53.2)
    seeds['U20'].update(x=33.7,y=53.0)
    seeds['R17'].update(x=43.2,y=51.8,rotation_deg=180)
    for i,ref in enumerate(['R19','R25','R31']):
        seeds[ref].update(x=45.0,y=14.5+15*i,side='B',rotation_deg=0)
    # Place the two auxiliary switchers, inductors and capacitors as functional
    # clusters before ordinary signal logic. Move the original local groups
    # together into the space between the through-board connector columns.
    for ref in ['C4','C5','C6','C7','C8','C9','C10','R9','R10','R11','R12']:
        seeds[ref]['x']-=.9;seeds[ref]['y']-=5.0
    seeds['U2'].update(x=22.5,y=43.5)
    seeds['L1'].update(x=21.5,y=35.3)
    seeds['U3'].update(x=13.2,y=49.4)
    seeds['L2'].update(x=13.8,y=43.1)
    seeds['J14'].update(x=26.0,y=3.8)
    for ref in ['C11','C12','C13','C14']:
        seeds[ref]['x']+=6.8;seeds[ref]['y']+=3.5
    # Newly added conditioning circuitry starts in the quiet B signal field.
    for i in range(8):
        seeds['D'+str(201+i)]={'x':15+(i%4)*3.6,'y':21+(i//4)*5,'side':'B','rotation_deg':90,'group':'ADC_clamp'}
        seeds['R'+str(201+i)]={'x':15+(i%4)*3.6,'y':18.2+(i//4)*5,'side':'B','rotation_deg':90,'group':'ADC_clamp'}
    for i,ref in enumerate(['D209','D210','R209','R210','R211','R160','TP16','TP17']):
        seeds[ref]={'x':12+(i%4)*3.8,'y':30+(i//4)*3.5,'side':'B','rotation_deg':0,'group':'state_return'}
    root_uuid=re.search(r'\(uuid "([^"]+)"\)',(B/'inverter.kicad_sch').read_text(encoding='utf-8')).group(1)
    fps={};initial={}
    for index,c in enumerate(components):
        ref=c.attrib['ref'];key=c.findtext('footprint');f=fp_load(key)
        f.SetReference(ref);f.SetValue(c.findtext('value'));f.SetDNP(c.find("./property[@name='dnp']") is not None)
        f.SetSheetname(c.find('sheetpath').attrib['names']);f.SetSheetfile(next((x.attrib.get('value','') for x in c.findall('property') if x.attrib['name']=='Sheetfile'),''))
        f.SetPath(p.KIID_PATH('/'+root_uuid+c.find('sheetpath').attrib['tstamps']+c.findtext('tstamps').split()[0]))
        for field in c.findall('./fields/field'):
            if field.attrib['name'] not in ['Reference','Value','Footprint']:f.SetField(field.attrib['name'],field.text or '')
        for prop in c.findall('property'):
            if prop.attrib['name'] not in ['Sheetname','Sheetfile','dnp','ki_fp_filters']:f.SetField(prop.attrib['name'],prop.attrib.get('value',''))
        board.Add(f)
        for pad in f.Pads():
            if not pad.GetNumber():continue
            name=pin_nets.get((ref,pad.GetNumber()));assert name is not None,(ref,pad.GetNumber())
            pad.SetNet(nets[name])
        if ref in contract['headers']:
            spec=contract['headers'][ref]
            f.SetPosition(V(spec['pad_1_x'],spec['pad_1_y']))
            f.Flip(f.GetPosition(),False)  # Native orientation180 is essential.
            for pad in f.Pads():
                n=int(pad.GetNumber());expected=(spec['pad_1_x'] if n%2 else spec['pad_2_x'],spec['pad_1_y']+((n-1)//2)*2.54)
                assert math.dist(xy(pad),expected)<1e-5,(ref,n,xy(pad),expected)
        else:
            loc=seeds.get(ref)
            assert loc is not None,('No placement seed',ref)
            if loc.get('side')=='B':f.Flip(f.GetPosition(),False)
            move(f,100+loc['x'],100+loc['y'],loc.get('rotation_deg',0))
        f.Value().SetVisible(False)
        f.Reference().SetLayer(p.B_Fab if f.IsFlipped() else p.F_Fab)
        f.Reference().SetTextSize(V(.6,.6));f.Reference().SetTextThickness(MM(.1))
        for field in f.GetFields():
            if field.GetName() not in ['Reference','Value']:field.SetVisible(False)
        fps[ref]=f;initial[ref]={'at':xy(f),'angle':f.GetOrientationDegrees(),'side':'B' if f.IsFlipped() else 'F'}
    holes=[]
    for spec in contract['mounting_holes']:
        f=fp_load('MountingHole:MountingHole_2.2mm_M2');f.SetReference(spec['reference']);board.Add(f);move(f,spec['x'],spec['y'])
        f.SetAttributes(f.GetAttributes()|p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES)
        f.Value().SetVisible(False);f.Reference().SetLayer(p.F_Fab);holes.append(f);fps[f.GetReference()]=f
    # Keep same-side courtyards and opposite-side through-hole pad projections
    # clear.  Fixed main-power anchors are packed first; only small signal parts
    # are allowed to change side during this geometry pass.
    fixed=[fps['J101'],fps['J102']]+holes
    fixed_cache={}
    has_th={r:any(a.GetAttribute()==p.PAD_ATTRIB_PTH for a in f.Pads()) for r,f in fps.items()}
    def valid(f):
        box=courtyard(f)
        own_courts={}
        for layer in [p.F_CrtYd,p.B_CrtYd]:
            shape=f.GetCourtyard(layer)
            if shape.OutlineCount():own_courts[layer]=bb(shape)
        own_pads=[pad_box(a) for a in f.Pads() if a.GetAttribute()==p.PAD_ATTRIB_PTH] if has_th[f.GetReference()] else []
        flipped=f.IsFlipped()
        if box[0]<100.5 or box[1]<100.5 or box[2]>159.5 or box[3]>159.5:return False
        if f.GetReference() not in power_refs and f.GetReference() not in ['J101','J102']:
            # Keep application logic and ADC RC out of the physical commutation
            # field; old positions never outrank the new power-loop geometry.
            if not flipped and overlap(box,(137,114.0,159.3,159.4),0):return False
            if flipped and any(overlap(box,(145,y-2,159.2,y+5.2),0) for y in [117.4,132.4,147.4]):return False
        for h in holes:
            hx,hy=xy(h);near=(max(box[0],min(hx,box[2])),max(box[1],min(hy,box[3])))
            if math.dist(near,(hx,hy))<2.8:return False
        for other in fixed:
            if other is f or other in holes:continue
            ref=other.GetReference()
            if ref not in fixed_cache:
                other_box=courtyard(other)
                courts={layer:bb(other.GetCourtyard(layer)) for layer in [p.F_CrtYd,p.B_CrtYd] if other.GetCourtyard(layer).OutlineCount()}
                fixed_cache[ref]=(other_box,other.IsFlipped(),[pad_box(a) for a in other.Pads() if a.GetAttribute()==p.PAD_ATTRIB_PTH],courts)
            other_box,other_flipped,other_pads,other_courts=fixed_cache[ref]
            if any(overlap(own_courts[layer],other_courts[layer]) for layer in own_courts.keys()&other_courts.keys()):return False
            # THT bodies occupy their own side; opposite-side solder projections
            # retain enough room for assembly and signal escape.
            for pad in other_pads:
                if overlap(box,pad):return False
            for pad in own_pads:
                if overlap(other_box,pad):return False
        return True
    anchors={'Q1','Q2','Q3','Q4','Q5','Q6','Q7','RS1','RS2','RS3','J3','J4','J5','C19','C20','C21','C22','D1','F1','U7','U8','U9','U10','U11','U12'}
    priority=lambda r:(0 if r in power_refs|aux_refs else 1 if r.startswith(('U','L','J','F','SW')) else 2,
                       -(courtyard(fps[r])[2]-courtyard(fps[r])[0])*(courtyard(fps[r])[3]-courtyard(fps[r])[1]),r)
    moves=[]
    for ref in sorted((r for r in fps if r not in ['J101','J102'] and not r.startswith('H')),key=priority):
        f=fps[ref]
        if valid(f):fixed.append(f);continue
        origin=xy(f);angle=f.GetOrientationDegrees();side=f.IsFlipped();best=None
        angles=[angle] if ref in anchors else list(dict.fromkeys([angle,(angle+90)%360,(angle+180)%360,(angle+270)%360]))
        radii=[i*.4 for i in range(1,31)] if ref in anchors else [i*.5 for i in range(1,131)]
        for radius in radii:
            candidates=[]
            # Distance-ordered polar lattice, snapped to0.1mm for reviewability.
            for k in range(32):
                a=k*math.pi/16;candidates.append((round((origin[0]+radius*math.cos(a))*10)/10,round((origin[1]+radius*math.sin(a))*10)/10))
            for at in candidates:
                for aa in angles:
                    move(f,*at,aa)
                    if valid(f):best=(at,aa);break
                if best:break
            if best:break
        if not best and ref not in anchors and not ref.startswith(('J','L','F')):
            f.Flip(f.GetPosition(),False)
            for yy in [101+i*.8 for i in range(73)]:
                for xx in [101+i*.8 for i in range(73)]:
                    move(f,xx,yy,angle)
                    if valid(f):best=((xx,yy),angle);break
                if best:break
        if not best:
            (REVIEW/'placement_failure.json').write_text(json.dumps({'failed':ref,'origin':origin,'fixed':{a.GetReference():{'at':xy(a),'box':courtyard(a),'side':'B' if a.IsFlipped() else 'F'} for a in fixed},'moves':moves},indent=2),encoding='utf-8')
        assert best,('Cannot place footprint',ref,origin)
        moves.append({'ref':ref,'before':initial[ref],'after':{'at':xy(f),'angle':f.GetOrientationDegrees(),'side':'B' if f.IsFlipped() else 'F'}})
        fixed.append(f)
        print('placed',len(fixed),ref,xy(f),flush=True) if len(fixed)%40==0 else None
    for a,c in [((100,100),(160,100)),((160,100),(160,160)),((160,160),(100,160)),((100,160),(100,100))]:
        e=p.PCB_SHAPE(board);e.SetShape(p.SHAPE_T_SEGMENT);e.SetStart(V(*a));e.SetEnd(V(*c));e.SetLayer(p.Edge_Cuts);e.SetWidth(MM(.05));board.Add(e)
    t=p.PCB_TEXT(board);t.SetText('INVERTER / REV E PCB0.1 REVIEW');t.SetPosition(V(130,161.5));t.SetLayer(p.Dwgs_User);t.SetTextSize(V(.8,.8));t.SetTextThickness(MM(.12));board.Add(t)
    board.BuildConnectivity();p.SaveBoard(str(OUT),board)
    (WORK/'inverter.kicad_pro').write_bytes(original_pro)
    text=OUT.read_text(encoding='utf-8').replace('${KIPRJMOD}/kicad_library/','D:/workspace/kicad_library/')
    OUT.write_text(text,encoding='utf-8')
    registry={}
    for ref,f in fps.items():
        registry[ref]={'x':xy(f)[0],'y':xy(f)[1],'rotation_deg':f.GetOrientationDegrees(),'side':'B' if f.IsFlipped() else 'F','courtyard':courtyard(f),'footprint':f.GetFPIDAsString(),'pads':[{'pin':a.GetNumber(),'xy':xy(a),'net':a.GetNetname()} for a in f.Pads() if a.GetNumber()]}
    report={'source_xml_sha256':hashlib.sha256(xml.read_bytes()).hexdigest(),'components':317,'DNP':sum(f.IsDNP() for r,f in fps.items() if not r.startswith('H')),'mechanical':4,'placements':registry,'moved':moves,'board':str(OUT),'source':'Current Rev E XML; old JSON used only as position seeds, no historical net/board import.'}
    (REVIEW/'placement.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Created',OUT,'317 components +4 holes; moved',len(moves),flush=True)


if __name__=='__main__':create()

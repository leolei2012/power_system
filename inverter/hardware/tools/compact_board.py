"""Create the 60 x 60 mm native working board from actual exported KiCad XML.

KiCad bundled Python. This is a recorded revision operation, never a scaling
operation on the old routing. The immutable PCB0.1 archive remains untouched.
"""
from build_pcb import *
import shutil

WORK=REVIEW/'compact_work'
OUT=WORK/'inverter.kicad_pcb'

def inputs():
    tree=ET.parse(REVIEW/'inverter.net.xml').getroot()
    positions={}
    for name in ['compact_control_placement.json','compact_power_placement.json','compact_aux_placement.json']:
        file=B/'tools'/name
        if not file.exists():continue
        data=json.loads(file.read_text(encoding='utf-8'))
        for ref,where in data.get('placements',{}).items():
            if not isinstance(where,dict) or 'x' not in where or 'y' not in where:continue
            assert ref not in positions,('duplicate placement owner',ref)
            positions[ref]=where
    return tree,positions

def load_fp(fp_id):
    lib,name=fp_id.split(':',1)
    directory=(B/'Inverter_Compact.pretty') if lib=='Inverter_Compact' else SHARED if lib=='MyFootprints' else STD/(lib+'.pretty')
    f=p.FootprintLoad(str(directory),name);assert f,('footprint load failed',fp_id)
    f.SetFPID(p.LIB_ID(lib,name));return f

def initialize():
    WORK.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(B/'inverter.kicad_pro',WORK/'inverter.kicad_pro')
    for name in ['fp-lib-table','sym-lib-table']:
        source=(B/name).read_text(encoding='utf-8').replace('${KIPRJMOD}',B.as_posix())
        (WORK/name).write_text(source,encoding='utf-8')

def create():
    initialize();tree,placements=inputs();board=p.BOARD();board.SetFileName(str(OUT));board.SetCopperLayerCount(6)
    ds=board.GetDesignSettings();ds.SetBoardThickness(MM(1.6));ds.m_MinClearance=MM(.15);ds.m_TrackMinWidth=MM(.15)
    ds.m_CopperEdgeClearance=MM(.5);ds.m_ViasMinSize=MM(.6);ds.m_ViasMinAnnularWidth=MM(.15)
    board.SetLayerType(p.In1_Cu,p.LT_POWER);board.SetLayerType(p.In4_Cu,p.LT_POWER)
    nets={};pin_nets={}
    for entry in tree.findall('./nets/net'):
        name=entry.attrib['name'];net=p.NETINFO_ITEM(board,name,int(entry.attrib['code']));board.Add(net);nets[name]=net
        for node in entry.findall('node'):pin_nets[node.attrib['ref'],node.attrib['pin']]=name
    root_uuid=re.search(r'\(uuid "([^"]+)"\)',(B/'inverter.kicad_sch').read_text(encoding='utf-8')).group(1)
    fps={};parked=[]
    for index,c in enumerate(tree.findall('./components/comp')):
        ref=c.attrib['ref'];fp_id=c.findtext('footprint');f=load_fp(fp_id)
        f.SetReference(ref);f.SetValue(c.findtext('value'))
        for model in f.Models():
            model.m_Filename=model.m_Filename.replace('${KIPRJMOD}/kicad_library/', '${KIPRJMOD}/../../../kicad_library/')
        f.SetSheetname(c.find('sheetpath').attrib['names']);f.SetSheetfile(next((x.attrib.get('value','') for x in c.findall('property') if x.attrib['name']=='Sheetfile'),''))
        f.SetPath(p.KIID_PATH('/'+root_uuid+c.find('sheetpath').attrib['tstamps']+c.findtext('tstamps').split()[0]))
        f.SetDNP(any(x.attrib['name']=='dnp' for x in c.findall('property')));f.SetExcludedFromBOM(False)
        for field in c.findall('./fields/field'):
            if field.attrib['name'] not in ['Footprint','Reference','Value','ki_fp_filters']:f.SetField(field.attrib['name'],field.text or '')
        for prop in c.findall('property'):
            if prop.attrib['name'] not in ['Sheetname','Sheetfile','dnp','ki_fp_filters']:f.SetField(prop.attrib['name'],prop.attrib.get('value',''))
        for a in f.Pads():
            if not a.GetNumber():continue
            key=(ref,a.GetNumber());assert key in pin_nets,('extra physical footprint pad',key)
            a.SetNet(nets[pin_nets[key]])
        board.Add(f)
        where=placements.get(ref)
        if where is None:
            parked.append(ref);where={'x':70+(index%20)*10,'y':10+(index//20)*10,'side':'F','rotation_deg':0}
        if where.get('side',where.get('layer','F')) in ['B','B.Cu']:f.Flip(V(0,0),False)
        f.SetOrientationDegrees(where.get('rotation_deg',0));f.SetPosition(V(where['x'],where['y']))
        f.Value().SetVisible(False);f.Reference().SetLayer(p.B_Fab if f.IsFlipped() else p.F_Fab)
        f.Reference().SetTextSize(V(.6,.6));f.Reference().SetTextThickness(MM(.1))
        for field in f.GetFields():
            if field.GetName() not in ['Reference','Value']:field.SetVisible(False)
        fps[ref]=f
    if '--stage' not in sys.argv:assert not parked,('unfinished placement',parked)
    for i,(x,y) in enumerate([(3,3),(57,3),(57,57),(3,57)],1):
        f=load_fp('MountingHole:MountingHole_2.2mm_M2');f.SetReference('H'+str(i));f.SetPosition(V(x,y))
        f.SetAttributes(f.GetAttributes()|p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES)
        f.Value().SetVisible(False);f.Reference().SetLayer(p.F_Fab);board.Add(f);fps[f.GetReference()]=f
    for a,b in [((0,0),(60,0)),((60,0),(60,60)),((60,60),(0,60)),((0,60),(0,0))]:
        e=p.PCB_SHAPE(board);e.SetShape(p.SHAPE_T_SEGMENT);e.SetStart(V(*a));e.SetEnd(V(*b));e.SetLayer(p.Edge_Cuts);e.SetWidth(MM(.05));board.Add(e)
    text(board,'INV60 / REV C / PCB0.2',24,59,p.F_Fab,size=.8)
    text(board,'60 x 60 mm | 6 LAYERS | REVIEW DRAFT',30,63,p.Dwgs_User,.9)
    board.BuildConnectivity();project=(WORK/'inverter.kicad_pro').read_text(encoding='utf-8');p.SaveBoard(str(OUT),board)
    pro=json.loads(project)
    for nc in pro['net_settings']['classes']:
        if nc['name']=='Default':nc['track_width']=.15;nc['via_diameter']=.6;nc['via_drill']=.3
    pro['board']['design_settings']['rules']['min_track_width']=.15
    (WORK/'inverter.kicad_pro').write_text(json.dumps(pro,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Preliminary 1 oz stack avoids the old 2 oz / 0.15 mm pad-spacing conflict.
    # The 10 A target requires wide, parallel power copper and thermal validation.
    src=OUT.read_text(encoding='utf-8')
    # Models() yields copies in KiCad 10. Apply the path in serialized native CAD.
    import os
    shared_prefix='${KIPRJMOD}/'+Path(os.path.relpath(B.parents[2]/'kicad_library',OUT.parent)).as_posix()+'/'
    src=src.replace('${KIPRJMOD}/kicad_library/',shared_prefix)
    OUT.write_text(src,encoding='utf-8')
    if '(stackup' not in src:
        layers=[('F.SilkS','Top Silk Screen',None),('F.Mask','Top Solder Mask',.01),('F.Cu','copper',.035),
          ('dielectric 1','prepreg',.10),('In1.Cu','copper',.035),('dielectric 2','core',.40),
          ('In2.Cu','copper',.035),('dielectric 3','prepreg',.37),('In3.Cu','copper',.035),
          ('dielectric 4','core',.40),('In4.Cu','copper',.035),('dielectric 5','prepreg',.10),
          ('B.Cu','copper',.035),('B.Mask','Bottom Solder Mask',.01),('B.SilkS','Bottom Silk Screen',None)]
        stack='\t\t(stackup\n'+''.join('\t\t\t(layer '+json.dumps(name)+' (type '+json.dumps(kind)+')'+(' (thickness '+str(t)+')' if t is not None else '')+(' (material "FR4") (epsilon_r 4.5) (loss_tangent .02)' if name.startswith('dielectric') else '')+')\n' for name,kind,t in layers)+'\t\t)\n'
        src=src.replace('\t(setup\n','\t(setup\n'+stack,1);OUT.write_text(src,encoding='utf-8')
    actual=p.LoadBoard(str(OUT));assert actual.GetCopperLayerCount()==6
    registry={}
    for f in fps.values():
        f.BuildCourtyardCaches();shape=f.GetCourtyard(p.B_CrtYd if f.IsFlipped() else p.F_CrtYd);bb=shape.BBox()
        registry[f.GetReference()]={'footprint':f.GetFPIDAsString(),'side':'B' if f.IsFlipped() else 'F','x':xy(f)[0],'y':xy(f)[1],
            'rotation_deg':f.GetOrientationDegrees(),'courtyard_mm':[p.ToMM(bb.GetX()),p.ToMM(bb.GetY()),p.ToMM(bb.GetRight()),p.ToMM(bb.GetBottom())],
            'area_mm2':shape.Area()/1e12,'pads':[{'number':a.GetNumber(),'x':xy(a)[0],'y':xy(a)[1],'net':a.GetNetname()} for a in f.Pads() if a.GetNumber()]}
    (REVIEW/'compact_footprints.json').write_text(json.dumps({'board_mm':[60,60],'layers':6,'parked':parked,'footprints':registry},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Built compact working board:',len(fps),'footprints; parked',len(parked),'at',OUT)

if __name__=='__main__':create()

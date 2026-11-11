"""Author the first Rev E core PCB from its actual current 47-ref XML.

Run with KiCad 10 bundled Python. Only this core project is writable. This is a
review-board authoring record; never replay --replace over manual board edits.
The outline, holes and header pad centres come from the common stack contract.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import math
import re
import zipfile
import xml.etree.ElementTree as E
import pcbnew as p

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]
STD = Path('C:/Program Files/KiCad/10.0/share/kicad/footprints')
SHARED = REPO.parent / 'kicad_library/footprints/MyFootprints.pretty'
BOARD = BASE / 'controller.kicad_pcb'
REVIEW = BASE / 'review/pcb_2026-11-11'
CONTRACT = REPO / 'docs/pcb_stack_contract_rev_e.json'
XML = BASE / 'review/controller.net.xml'
MM = p.FromMM
V = lambda x, y: p.VECTOR2I(MM(x), MM(y))

# (x, y, angle, side). Header coordinates are overwritten from the contract.
PLACEMENT = {
    'U30': (116.5, 130, 180, 'F'),
    'C63': (125, 126.4, 90, 'F'), 'C64': (112.75, 122.15, 90, 'F'),
    'C65': (111.5, 133.75, 0, 'B'), 'C66': (120.25, 137.8, 270, 'F'),
    'C67': (121.4, 133.75, 0, 'B'), 'C68': (116, 139.2, 0, 'F'),
    'C77': (114.3, 122.15, 90, 'F'), 'C78': (113.8, 119.4, 0, 'F'),
    'C79': (116, 122.15, 90, 'F'), 'C80': (117.5, 119.4, 0, 'F'),
    'R92': (113.3, 116.8, 0, 'F'), 'R93': (116.9, 116.8, 0, 'F'),
    'C81': (121.5, 130.75, 0, 'B'), 'C83': (124.7, 128.8, 0, 'F'),
    'C84': (125.7, 135.4, 0, 'F'), 'R122': (118.75, 135.3, 90, 'B'),
    'R401': (146.2, 154.5, 90, 'F'),
    'SW2': (119, 156.5, 0, 'F'), 'SW3': (140, 156.5, 0, 'F'),
    'TP15': (146.5, 150, 0, 'F'), 'Y1': (125.1, 132, 270, 'F'),
    'C301': (118, 111.3, 180, 'F'), 'C302': (129, 106.65, 180, 'F'),
    'C303': (136, 106.65, 0, 'F'), 'C304': (136.5, 104, 0, 'F'),
    'C305': (122.4, 144.5, 0, 'F'), 'C306': (140, 112.5, 0, 'F'),
    'C307': (141, 116.5, 0, 'F'),
    'D101': (114.8, 106, 0, 'F'), 'D102': (122.7, 106.7, 180, 'F'),
    'D103': (132.5, 102.7, 0, 'F'),
    'R301': (111.2, 108, 90, 'F'), 'R302': (112.8, 142, 0, 'F'),
    'R303': (112.8, 145, 180, 'F'), 'R304': (135.8, 109.2, 0, 'F'),
    'R305': (139.5, 114.8, 0, 'F'), 'R306': (134.8, 117.5, 90, 'F'),
    'U101': (132.5, 106, 180, 'F'), 'U102': (135.8, 112.5, 0, 'F'),
    'U103': (137.8, 119.5, 0, 'F'), 'U104': (117, 143, 0, 'F'),
    'C308': (141.7, 125.7, 0, 'F'), 'R402': (112, 129.25, 0, 'B'),
    'U105': (137.5, 126.5, 0, 'F'),
    'J101': (104.73, 110.95, 0, 'F'), 'J102': (128.73, 110.95, 0, 'F'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def xy(obj):
    a = obj.GetPosition()
    return [round(p.ToMM(a.x), 6), round(p.ToMM(a.y), 6)]


def bbox(fp):
    fp.BuildCourtyardCaches()
    s = fp.GetCourtyard(p.B_CrtYd if fp.GetLayer() == p.B_Cu else p.F_CrtYd)
    bb = s.BBox() if s.OutlineCount() else fp.GetBoundingBox(False, False)
    return [p.ToMM(bb.GetLeft()), p.ToMM(bb.GetTop()), p.ToMM(bb.GetRight()), p.ToMM(bb.GetBottom())]


def overlap(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]) > .001 and min(a[3], b[3]) - max(a[1], b[1]) > .001


def add_text(board, value, x, y, size=.8, layer=p.F_SilkS):
    t = p.PCB_TEXT(board)
    t.SetText(value)
    t.SetPosition(V(x, y))
    t.SetLayer(layer)
    t.SetTextSize(V(size, size))
    t.SetTextThickness(MM(.12))
    board.Add(t)
    return t


def place_reference_fields(fps, contract):
    occupied = {r: bbox(f) for r, f in fps.items()}
    text_boxes = collections.defaultdict(list)
    hidden = []
    for ref, fp in sorted(fps.items(), key=lambda kv: (not kv[0].startswith(('U', 'J', 'SW', 'H')), kv[0])):
        side = fp.GetLayer()
        r = fp.Reference()
        r.SetTextAngle(p.EDA_ANGLE(0, p.DEGREES_T))
        r.SetTextSize(V(.8, .8))
        r.SetTextThickness(MM(.12))
        r.SetLayer(p.B_SilkS if side == p.B_Cu else p.F_SilkS)
        r.SetMirrored(side == p.B_Cu)
        box = occupied[ref]
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        w, h = max(.8, len(ref) * .8 * .72), .8
        found = None
        for gap in [.55, .95, 1.35, 1.8, 2.4, 3.0, 3.8]:
            for x, y in [(cx, box[1] - gap), (cx, box[3] + gap),
                         (box[0] - gap - w / 2, cy), (box[2] + gap + w / 2, cy)]:
                rect = [x-w/2-.12, y-h/2-.12, x+w/2+.12, y+h/2+.12]
                if min(rect[0], rect[1]) < 100.7 or max(rect[2], rect[3]) > 159.3:
                    continue
                if any(overlap(rect, bb) for other, bb in occupied.items()
                       if other != ref and fps[other].GetLayer() == side):
                    continue
                if any(overlap(rect, bb) for bb in text_boxes[side]):
                    continue
                found = (x, y)
                text_boxes[side].append(rect)
                break
            if found:
                break
        if found:
            r.SetPosition(V(*found))
        else:
            r.SetPosition(V(cx, cy))
            r.SetLayer(p.B_Fab if side == p.B_Cu else p.F_Fab)
            hidden.append(ref)
        fp.Value().SetVisible(False)
        for field in fp.GetFields():
            if field.GetName() not in ('Reference', 'Value'):
                field.SetVisible(False)
    return hidden


def copper_keepout(board, x, y, radius, name):
    z = p.ZONE(board)
    layers = p.LSET()
    for layer in (p.F_Cu, p.In1_Cu, p.In2_Cu, p.B_Cu):
        layers.AddLayer(layer)
    z.SetLayerSet(layers)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowZoneFills(True)
    # The mechanical NPTH itself is allowed; traces, vias and poured copper are not.
    z.SetDoNotAllowPads(False)
    z.SetZoneName(name)
    outline = z.Outline()
    outline.NewOutline()
    radius /= math.cos(math.pi / 64)
    for i in range(64):
        a = 2 * math.pi * i / 64
        outline.Append(MM(x + radius * math.cos(a)), MM(y + radius * math.sin(a)))
    board.Add(z)


def configure_project(pro, net_names):
    rules = pro['board']['design_settings']['rules']
    rules.update(min_clearance=.15, min_track_width=.15, min_via_diameter=.6,
                 min_through_hole_diameter=.3, min_via_annular_width=.15,
                 min_copper_edge_clearance=.5, min_hole_clearance=.25,
                 min_hole_to_hole=.25)
    template = pro['net_settings']['classes'][0]
    classes = []
    for name, width in [('Default', .15), ('CorePower', .4), ('CoreAnalog', .25)]:
        c = dict(template)
        c.update(name=name, clearance=.15, track_width=width, via_diameter=.6,
                 via_drill=.3, priority=2147483647 if name == 'Default' else 0)
        classes.append(c)
    pro['net_settings']['classes'] = classes
    pro['net_settings']['netclass_patterns'] = []
    for net in net_names:
        short = net.rsplit('/', 1)[-1]
        name = 'CorePower' if short in ['GND', '+5V_CORE_IN', 'CORE_5V_TVS', 'CORE_LDO_IN', '+3V3_MCU'] else \
               'CoreAnalog' if short in ['+3V3_A_MCU', 'VREF_MCU'] else None
        if name:
            pro['net_settings']['netclass_patterns'].append({'netclass': name, 'pattern': net})
    pro['boards'] = [{'name': 'controller.kicad_pcb'}]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--replace-generated', action='store_true')
    args = ap.parse_args()
    assert not BOARD.exists() or args.replace_generated, 'Refuse to overwrite an existing board without --replace-generated'
    REVIEW.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    assert contract['outline'] == {'min_x':100., 'min_y':100., 'max_x':160., 'max_y':160.}
    tree = E.parse(XML).getroot()
    comps = {c.get('ref'): c for c in tree.findall('./components/comp')}
    assert len(comps) == 47 and set(comps) == set(PLACEMENT)
    print('Read 47 components and common mechanical contract.', flush=True)
    original_pro = (BASE/'controller.kicad_pro').read_bytes()
    backup = BASE/'history/rev_e_before_pcb_2026-11-11.zip'
    if not backup.exists():
        backup.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(backup, 'w', zipfile.ZIP_DEFLATED) as z:
            for rel in ['controller.kicad_pro', 'review/controller.net.xml', 'fp-lib-table', 'sym-lib-table']:
                z.write(BASE/rel, rel)
            z.write(CONTRACT, 'pcb_stack_contract_rev_e.json')
            z.writestr('source_sha256.json', json.dumps({'project':sha(BASE/'controller.kicad_pro'),
                                                        'netlist':sha(XML), 'mechanical_contract':sha(CONTRACT)}, indent=2))
    board = p.BOARD()
    print('Created empty board.', flush=True)
    board.SetFileName(str(BOARD))
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(MM(contract['board_thickness']))
    ds.m_MinClearance=MM(.15)
    ds.m_TrackMinWidth=MM(.15)
    ds.m_CopperEdgeClearance=MM(.5)
    ds.m_ViasMinSize=MM(.6)
    ds.m_ViasMinAnnularWidth=MM(.15)
    ds.m_MinThroughDrill=MM(.3)
    classes = {}
    for name, width in [('Default', .15), ('CorePower', .4), ('CoreAnalog', .25)]:
        nc = p.NETCLASS(name)
        nc.SetTrackWidth(MM(width)); nc.SetClearance(MM(.15))
        nc.SetViaDiameter(MM(.6)); nc.SetViaDrill(MM(.3))
        board.GetNetClasses()[name] = nc
        classes[name] = nc
    nets={}; pin_nets={}
    for net in tree.findall('./nets/net'):
        name=net.get('name')
        ni=p.NETINFO_ITEM(board,name,int(net.get('code')))
        board.Add(ni)
        short=name.rsplit('/',1)[-1]
        cls='CorePower' if short in ['GND','+5V_CORE_IN','CORE_5V_TVS','CORE_LDO_IN','+3V3_MCU'] else \
            'CoreAnalog' if short in ['+3V3_A_MCU','VREF_MCU'] else 'Default'
        ni.SetNetClass(classes[cls]);nets[name]=ni
        for node in net.findall('node'):
            pin_nets[node.get('ref'),node.get('pin')]=name
    print('Assigned', len(nets), 'native nets.', flush=True)
    root_uuid=re.search(r'\(uuid "([^"]+)"\)',(BASE/'controller.kicad_sch').read_text(encoding='utf-8')).group(1)
    fps={}; model_fixes=[]; model_missing=[]
    for ref,c in comps.items():
        fp_id=c.findtext('footprint');lib,name=fp_id.split(':',1)
        directory=SHARED if lib=='MyFootprints' else BASE/'Inverter_Compact.pretty' if lib=='Inverter_Compact' else STD/(lib+'.pretty')
        fp=p.FootprintLoad(str(directory),name)
        assert fp,('Missing real footprint',ref,fp_id)
        # KiCad 10 Flip requires an owning BOARD (layer stack access).
        board.Add(fp)
        fp.SetFPID(p.LIB_ID(lib,name));fp.SetReference(ref);fp.SetValue(c.findtext('value'))
        fp.SetSheetname(c.find('sheetpath').get('names'))
        fp.SetSheetfile(next((n.get('value') for n in c.findall('property') if n.get('name')=='Sheetfile'),''))
        fp.SetPath(p.KIID_PATH('/'+root_uuid+c.find('sheetpath').get('tstamps')+c.findtext('tstamps').split()[0]))
        fp.SetDNP(c.find("property[@name='dnp']") is not None)
        fp.SetExcludedFromBOM(False)
        # Reserved filters are library metadata, not PCB user properties.
        excluded={'Reference','Value','Footprint','Sheetname','Sheetfile','dnp','ki_fp_filters'}
        for field in c.findall('./fields/field'):
            if field.get('name') not in excluded:fp.SetField(field.get('name'),field.text or '')
        for prop in c.findall('property'):
            if prop.get('name') not in excluded:fp.SetField(prop.get('name'),prop.get('value',''))
        loc=list(PLACEMENT[ref])
        if ref in contract['headers']:
            h=contract['headers'][ref]
            loc=[h['pad_1_x'],h['pad_1_y'],0,'F']
        fp.SetPosition(V(loc[0],loc[1]))
        if loc[3]=='B':fp.Flip(fp.GetPosition(),False)
        fp.SetOrientationDegrees(loc[2])
        for pad in fp.Pads():
            num=pad.GetNumber()
            if num:
                assert (ref,num) in pin_nets,('Unexpected numbered pad',ref,num)
                pad.SetNet(nets[pin_nets[ref,num]])
        models = fp.Models()
        for model_index in range(len(models)):
            model = models[model_index]
            old=model.m_Filename
            if old.startswith('${KIPRJMOD}/kicad_library/'):
                model.m_Filename=old.replace('${KIPRJMOD}/kicad_library/','${KIPRJMOD}/../../../../kicad_library/',1)
                # SWIG returns a model value copy, not a mutable vector element.
                models[model_index] = model
                model_fixes.append({'ref':ref,'before':old,'after':model.m_Filename})
            if model.m_Filename.startswith('${KIPRJMOD}'):
                actual=Path(model.m_Filename.replace('${KIPRJMOD}',str(BASE)))
                if not actual.is_file():model_missing.append({'ref':ref,'path':model.m_Filename})
        fps[ref]=fp
    print('Placed all schematic footprints.', flush=True)
    for hole in contract['mounting_holes']:
        print('Adding', hole['reference'], flush=True)
        fp=p.FootprintLoad(str(STD/'MountingHole.pretty'),'MountingHole_2.2mm_M2')
        fp.SetReference(hole['reference']);fp.SetValue('M2 NPTH 2.2mm')
        fp.SetPosition(V(hole['x'],hole['y']))
        fp.SetAttributes(fp.GetAttributes()|p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES)
        board.Add(fp);fps[hole['reference']]=fp
        copper_keepout(board,hole['x'],hole['y'],contract['mounting_copper_keepout_radius'],hole['reference']+' M2 copper exclusion')
    for a,b in [((100,100),(160,100)),((160,100),(160,160)),((160,160),(100,160)),((100,160),(100,100))]:
        edge=p.PCB_SHAPE(board);edge.SetShape(p.SHAPE_T_SEGMENT)
        edge.SetStart(V(*a));edge.SetEnd(V(*b));edge.SetLayer(p.Edge_Cuts);edge.SetWidth(MM(.05));board.Add(edge)
    hidden=place_reference_fields(fps,contract)
    print('Placed reference fields.', flush=True)
    add_text(board,'G431 CORE / REV E',145,143,1.1)
    add_text(board,'PCB 0.1 REVIEW',145,145, .8)
    add_text(board,'5V ONLY / COMMON GND',144.5,146.7,.8)
    add_text(board,'RESET',119,151.7,.8)
    add_text(board,'BOOT',140,151.7,.8)
    add_text(board,'60x60 mm / 4 LAYERS / 1oz CANDIDATE',130,102, .9,p.Dwgs_User)
    collisions=[];outside=[]
    for ref,fp in fps.items():
        bb=bbox(fp)
        if bb[0]<100 or bb[1]<100 or bb[2]>160 or bb[3]>160:outside.append([ref,bb])
        for other in fps:
            if other<=ref:continue
            if fp.GetLayer()==fps[other].GetLayer() and overlap(bb,bbox(fps[other])):
                collisions.append([ref,other])
    board.BuildConnectivity()
    assert p.SaveBoard(str(BOARD),board)
    persisted = p.LoadBoard(str(BOARD))
    persisted_models = []
    for footprint in persisted.GetFootprints():
        for model in footprint.Models():
            if model.m_Filename.startswith('${KIPRJMOD}'):
                actual = Path(model.m_Filename.replace('${KIPRJMOD}', str(BASE)))
                assert actual.is_file(), ('Persisted model missing', footprint.GetReference(), model.m_Filename)
                persisted_models.append({'ref': footprint.GetReference(), 'path': model.m_Filename})
    pro=json.loads(original_pro.decode('utf-8-sig'))
    configure_project(pro,nets)
    (BASE/'controller.kicad_pro').write_text(json.dumps(pro,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    report={
        'status':'PLACED REVIEW DRAFT; not yet routed','physical_schematic_refs':47,
        'mechanical_holes':4,'copper_layers':4,'size_mm':[60,60],'board_thickness_mm':1.6,
        'copper_weight':'1oz candidate, manufacturing stackup unqualified',
        'source_xml_sha256':sha(XML),'contract_sha256':sha(CONTRACT),
        'backup':str(backup),'project_before_sha256':json.loads(zipfile.ZipFile(backup).read('source_sha256.json'))['project'],
        'build_input_project_sha256':hashlib.sha256(original_pro).hexdigest(),
        'DNP_refs':sorted(r for r,c in comps.items() if c.find("property[@name='dnp']") is not None),
        'courtyard_collisions':collisions,'courtyard_outside_board':outside,
        'assembly_layer_only_references':hidden,'model_instance_path_fixes':model_fixes,
        'missing_model_files':model_missing,'persisted_models_reloaded_and_checked':persisted_models,
        'native_unconnected':board.GetConnectivity().GetUnconnectedCount(False),
        'placements':{r:{'x':xy(f)[0],'y':xy(f)[1],'angle':f.GetOrientationDegrees(),
                         'side':'B' if f.GetLayer()==p.B_Cu else 'F','courtyard':bbox(f),
                         'footprint':f.GetFPID().GetUniStringLibId()} for r,f in fps.items()},
    }
    write_json(REVIEW/'placement.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['placements','model_instance_path_fixes']},indent=2))


if __name__=='__main__':main()

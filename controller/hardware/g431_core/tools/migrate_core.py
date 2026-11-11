"""Migrate the frozen Rev C MCU pages into an independent G431 controller.

Only writes this new g431_core directory. The old LKS controller and inverter
source/archive are read only. External core_supply/core_interface pages are
owned by other authors and are never generated or overwritten here.
Authoring snapshot: do not rerun over later manual edits without reviewing.
"""
from pathlib import Path
import copy, hashlib, json, math, shutil, uuid, zipfile
import sexpdata as sx

BASE=Path(__file__).resolve().parents[1]
REPO=BASE.parents[2]
ARCHIVE=REPO/'inverter/history/integrated_60x60_rev_c_before_mcu_split_2026-11-06.zip'
ZIP=zipfile.ZipFile(ARCHIVE)
PREFIX='inverter/hardware/'
PROJECT='controller'
ROOT='9dba1312-bd1c-50b2-9df7-fc81461aaf77'
uid=lambda key:str(uuid.uuid5(uuid.NAMESPACE_URL,'power_system/g431_core/'+key+'/2026-11-06'))
sheet_id=lambda name:uid('sheet/'+name)
tag=lambda x,n:isinstance(x,list) and bool(x) and str(x[0])==n
child=lambda x,n:next((a for a in x if tag(a,n)),None)
children=lambda x,n:[a for a in x if tag(a,n)]
props=lambda x:{a[1]:a[2] for a in children(x,'property')}
read=lambda n:sx.loads(ZIP.read(PREFIX+n).decode('utf-8-sig'))
def write(name,root):
    (BASE/name).write_text('('+str(root[0])+'\n'+'\n'.join(sx.dumps(x) for x in root[1:])+')\n',encoding='utf-8')
def all_nodes(root):
    if isinstance(root,list):
        yield root
        for item in root:
            yield from all_nodes(item)
def wire_points(item):
    return [tuple(round(float(v),4) for v in a[1:]) for a in child(item,'pts')[1:] if tag(a,'xy')]
def at(item):
    value=child(item,'at')
    return tuple(round(float(v),4) for v in value[1:3]) if value else None
def new_uuid(item):
    value=child(item,'uuid')
    if value:value[1]=uid('new/'+value[1])
def replace_strings(root,mapping):
    for node in all_nodes(root):
        for index,value in enumerate(node):
            if type(value) is str:
                for old,new in mapping.items():value=value.replace(old,new)
                node[index]=value

PAGES={
 'mcu':('STM32G431 minimum system','MCU, supplies and local decoupling'),
 'mcu_analog':('MCU analog inputs','Eight final ADC RC filters / VDDA / VREF'),
 'mcu_control':('Command coupling and clock','Six PWM / ENABLE / BRAKE / FAULT / optional HSE'),
 'sensors':('Encoders and SPI','Two ABZ encoders and two SPI sensors'),
 'debug_comms':('Debug and communication','SWD / TTL / optional CAN / four MCU status LEDs'),
 'core_supply':('Controller power and readiness','Local 3.3 V / supervisor / buffered CTRL_READY'),
 'core_interface':('Power baseboard interface','Headers / ADC input protection / BASE_READY'),
}
source_top=read('inverter.kicad_sch')
oldroot=child(source_top,'uuid')[1]
old_sheets={props(a)['Sheetfile'].removesuffix('.kicad_sch'):child(a,'uuid')[1] for a in children(source_top,'sheet')}
report={'archive':str(ARCHIVE),'archive_sha256':hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
 'new_root':ROOT,'project':PROJECT,'sheet_ids':{n:sheet_id(n) for n in PAGES},'pages':{},
 'renamed_nets':{'+3V3_INV':'+3V3_MCU','LOGIC_POWER_OK':'MCU_RESET_N'},
 'adc_input_renames':{n:n+'_CLAMPED' for n in ['I_U_PORT','I_V_PORT','I_W_PORT','V_DC_PORT','V_U_PORT','V_V_PORT','V_W_PORT','TEMP_NTC']},
 'new_mcu_input':{'ref':'U30','pin':'2','gpio':'PC13','net':'BASE_READY'},
 'remaining_nc':{'3':'PC14','4':'PC15','39':'PC7','56':'PB3','57':'PB4','62':'PB9'},
 'external_page_ownership':'core_supply and core_interface are never overwritten by this script'}

for number,name in enumerate(list(PAGES)[:5],2):
    r=read(name+'.kicad_sch')
    original=copy.deepcopy(r)
    remove=[]
    if name=='debug_comms':
        # Remove only the baseboard power indicator branch; retain all four GPIO LEDs.
        for item in r[1:]:
            if tag(item,'symbol') and props(item).get('Reference') in ['D3','R130','#PWR30813']:remove.append(item)
            elif tag(item,'wire') and all(abs(pt[0]-43.18)<1e-6 and pt[1]>246 for pt in wire_points(item)):remove.append(item)
            elif tag(item,'junction') and at(item)==(43.18,246.38):remove.append(item)
            elif tag(item,'label') and item[1]=='LED_AN_0':remove.append(item)
        for item in children(r,'text'):
            if item[1].startswith('FIVE INDICATORS'):item[1]='FOUR MCU STATUS INDICATORS / ACTIVE LOW'
            if item[1].startswith('VTREF is sense only.'):
                item[1]='VTREF is sense only. MCU_RESET_N stays on this controller.\nA local supervisor supplies buffered CTRL_READY to the baseboard.\nPower-stage faults assert FAULT_N; they do not reset the MCU.'
    if name=='mcu_control':
        removed_wires={
            frozenset([(93.98,111.76),(93.98,124.46)]),
            frozenset([(93.98,124.46),(77.47,124.46)]),
            frozenset([(111.76,185.42),(111.76,198.12)]),
        }
        for item in r[1:]:
            if tag(item,'symbol') and props(item).get('Reference') in ['TP16','TP17']:remove.append(item)
            elif tag(item,'wire') and frozenset(wire_points(item)) in removed_wires:remove.append(item)
            elif tag(item,'junction') and at(item) in [(93.98,124.46),(111.76,198.12)]:remove.append(item)
        for item in children(r,'text'):
            if item[1].startswith('LOCAL COMMAND SERIES'):item[1]='CONTROLLER COMMAND SERIES RESISTORS / BASEBOARD SIGNALS'
            if item[1].startswith('Q8 open collector'):
                item[1]='FAULT_N from baseboard -> local pull-up -> PB12 / TIM1 BKIN.\nEnable defaults low on the power baseboard.\nHardware latch and PWM gates stay on the baseboard.\nMCU_RESET_N never leaves this controller.'
    for item in remove:r.remove(item)
    child(r,'uuid')[1]=uid('page/'+name)
    child(r,'generator')[1]='power_system_controller_core'
    tb=child(r,'title_block')
    child(tb,'title')[1]='Controller core - '+PAGES[name][0]
    child(tb,'rev')[1]='D-split-draft'
    for c in children(tb,'comment'):
        if c[1]==2:c[2]='CONTROLLER | STM32G431RBT6 | shared-ground replaceable MCU daughterboard'
    oldpath='/'+oldroot+'/'+old_sheets[name]
    newpath='/'+ROOT+'/'+sheet_id(name)
    for n in all_nodes(r):
        if tag(n,'project') and n[1]=='inverter':n[1]=PROJECT
        if tag(n,'path') and n[1]==oldpath:n[1]=newpath
    replace_strings(r,report['renamed_nets'])
    if name=='mcu_analog':
        for label in children(r,'global_label'):
            if label[1] in report['adc_input_renames']:
                label[1]=report['adc_input_renames'][label[1]]
        for text in children(r,'text'):
            if text[1].startswith('LOCAL ADC FILTERS'):
                text[1]='LOCAL ADC FILTERS / CLAMPED INPUT -> 100R -> 1nF RC NODE -> MCU'
            if text[1].startswith('VDDA AND VREF+'):
                text[1]='VDDA AND VREF+ / LOCAL FILTERED 3.3 V CORE SUPPLY'
    if name=='mcu':
        u=next(a for a in children(r,'symbol') if props(a).get('Reference')=='U30')
        lib=next(a for a in children(child(r,'lib_symbols'),'symbol') if a[1]==child(u,'lib_id')[1])
        pin=next(p for s in children(lib,'symbol') for p in children(s,'pin') if child(p,'number')[1]=='2')
        px,py,pa=child(pin,'at')[1:]
        ux,uy,angle=child(u,'at')[1:]
        angle=math.radians(angle)
        start=(round(ux+px*math.cos(angle)-py*math.sin(angle),4),round(uy-px*math.sin(angle)-py*math.cos(angle),4))
        marker=next(a for a in children(r,'no_connect') if at(a)==start)
        r.remove(marker)
        end=(round(start[0]-20.32,4),start[1])
        r.append(sx.loads(f'(wire (pts (xy {start[0]} {start[1]}) (xy {end[0]} {end[1]})) (stroke (width 0) (type default)) (uuid "{uid("base-ready-wire")}"))'))
        r.append(sx.loads(f'(global_label "BASE_READY" (shape input) (at {end[0]} {end[1]} 180) (effects (font (size .9 .9)) (justify right)) (uuid "{uid("base-ready-label")}"))'))
        for text in children(r,'text'):
            text[1]=text[1].replace('VSSA and VSS return to shunt LOW / DC-.','VSSA and VSS return to the local controller ground plane.').replace('VREF+ uses the external 3.3 V reference rail; VREFBUF OFF.','VDDA / VREF+ use the local filtered 3.3 V core rail; VREFBUF OFF.').replace('PWM / ENABLE / BRAKE -> local command and gate pages','PWM / ENABLE / BRAKE -> command coupling -> power-baseboard header').replace('Seven unused GPIOs remain explicit NC.','PC13 reads BASE_READY; six unused GPIOs remain explicit NC.')
    refs=sorted({props(a)['Reference'] for a in children(r,'symbol') if not props(a)['Reference'].startswith('#')})
    report['pages'][name]={'physical_count':len(refs),'refs':refs,'preserved_wire_count':len(children(r,'wire')),
        'source_wire_count':len(children(original,'wire')),'removed_item_uuids':[child(a,'uuid')[1] for a in remove if child(a,'uuid')]}
    write(name+'.kicad_sch',r)

assert sum(p['physical_count'] for p in report['pages'].values())==97

# Copy only the project-owned native library resources; shared library stays read only.
for entry in ZIP.namelist():
    if entry==PREFIX+'InverterLocal.kicad_sym' or entry.startswith(PREFIX+'Inverter_Compact.pretty/'):
        rel=entry.removeprefix(PREFIX)
        target=BASE/rel;target.parent.mkdir(parents=True,exist_ok=True)
        data=ZIP.read(entry).decode('utf-8-sig').replace('${KIPRJMOD}/../../../kicad_library','${KIPRJMOD}/../../../../kicad_library')
        target.write_text(data,encoding='utf-8')
(BASE/'fp-lib-table').write_text('(fp_lib_table (version 7)\n(lib (name "MyFootprints") (type "KiCad") (uri "${KIPRJMOD}/../../../../kicad_library/footprints/MyFootprints.pretty") (options "") (descr "Shared footprints; read only"))\n(lib (name "Inverter_Compact") (type "KiCad") (uri "${KIPRJMOD}/Inverter_Compact.pretty") (options "") (descr "Frozen Rev C project draft derivatives; migrated geometry")))\n',encoding='utf-8')
(BASE/'sym-lib-table').write_text('(sym_lib_table (version 7)\n(lib (name "MyParts") (type "KiCad") (uri "${KIPRJMOD}/../../../../kicad_library/symbols/MyParts.kicad_sym") (options "") (descr "Shared library; read only"))\n(lib (name "InverterLocal") (type "KiCad") (uri "${KIPRJMOD}/InverterLocal.kicad_sym") (options "") (descr "Frozen Rev C draft symbols; migrated unchanged"))\n(lib (name "CoreProtection") (type "KiCad") (uri "${KIPRJMOD}/CoreProtection.kicad_sym") (options "") (descr "Controller protection draft; project local")))\n',encoding='utf-8')
pro=json.loads(ZIP.read(PREFIX+'inverter.kicad_pro'))
pro['meta']['filename']='controller.kicad_pro'
pro['net_settings']['classes']=[c for c in pro['net_settings']['classes'] if c['name']=='Default']
pro['net_settings']['netclass_patterns']=[]
pro['net_settings']['netclass_assignments']={}
(BASE/'controller.kicad_pro').write_text(json.dumps(pro,indent=2)+'\n',encoding='utf-8')

# Top-level functional modules. Supply/interface files are separate ownership.
def quote(s):return json.dumps(s)
items=[f'(kicad_sch (version 20250114) (generator "power_system_controller_core") (generator_version "1.0") (uuid "{ROOT}") (paper "A3")',
 '(title_block (title "Controller - replaceable STM32G431 core") (date "2026-11-06") (rev "D-split-draft") (company "power_system") (comment 1 "SCHEMATIC REVIEW DRAFT - NOT RELEASED FOR PCB") (comment 2 "Common-ground daughterboard; power-baseboard protection remains local"))','(lib_symbols)']
def text(t,x,y,size=1.2):
    items.append(f'(text {quote(t)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left top)) (uuid "{uid("top-text/"+t)}"))')
text('REPLACEABLE G431 CONTROLLER / COMMON GROUND / REV D DRAFT',20.32,17.78,1.6)
text('One STM32G431RBT6 core; power MOSFETs, drivers, sensing front ends and hardware shutdown stay on the baseboard.\nMCU_RESET_N is local. CTRL_READY and BASE_READY carry buffered board readiness across the headers.',20.32,30.48)
for index,(name,(title,desc)) in enumerate(PAGES.items()):
    x=20.32+(index%3)*124.46;y=66.04+(index//3)*58.42
    items.append(f'(sheet (at {x} {y}) (size 111.76 25.4) (stroke (width .254) (type default)) (fill (color 0 0 0 0)) (uuid "{sheet_id(name)}") (property "Sheetname" {quote(title)} (at {x} {y-2.54} 0) (effects (font (size 1 1)) (justify left))) (property "Sheetfile" "{name}.kicad_sch" (at {x} {y+27.94} 0) (effects (font (size .9 .9)) (justify left))) (instances (project "controller" (path "/{ROOT}" (page "{index+2}")))))')
    text(desc,x+2.54,y+7.62,.95)
text('Retained: eight ADC filters, two ABZ, two SPI, TTL, SWD, optional DNP CAN/HSE and four MCU status LEDs.\nLocal 3.3 V and supervisor are independent from the power-baseboard 3.3 V rail. Sensor 5 V links remain DNP.\nThis common-ground design is replaceable but not galvanically isolated; electrical, fault, insertion and thermal review remain open.\nOld LKS controller files are historical and are not overwritten by this project.',20.32,254,1.05)
items+=['(sheet_instances (path "/" (page "1")))','(embedded_fonts no))']
(BASE/'controller.kicad_sch').write_text('\n'.join(items)+'\n',encoding='utf-8')
(BASE/'review').mkdir(exist_ok=True)
(BASE/'review/migration_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('Migrated',sum(p['physical_count'] for p in report['pages'].values()),'physical references into',BASE)
for name,page in report['pages'].items():print(name,page['physical_count'],'refs;',page['preserved_wire_count'],'wires')
print('External pages not modified: core_supply / core_interface')

"""Recorded, explicit component migration for the authorized 60 mm revision.

No circuit wires are redrawn. New MOS physical pins are stacked onto their
corresponding original G/D/S connection points. Run with system Python.
"""
from schematic_common import *

B=BASE
FPDIR=B/'Inverter_Compact.pretty'
FPSTD=Path('C:/Program Files/KiCad/10.0/share/kicad/footprints')

def dump(path,data):
    path.write_text('('+str(data[0])+'\n'+'\n'.join(sx.dumps(v) if isinstance(v,list) else str(v) for v in data[1:])+')\n',encoding='utf-8')

def setprop(data,key,value):
    item=next((x for x in children(data,'property') if x[1]==key),None)
    if item is None:
        item=sx.loads('(property '+q(key)+' '+q(value)+' (at 0 0 0) (hide yes) (effects (font (size 1 1))))')
        data.append(item)
    else:item[2]=str(value)

def new_symbol(old,new,properties,pinmap=None):
    result=copy.deepcopy(old);oldname=result[1];result[1]=new
    for block in children(result,'symbol'):
        block[1]=new+block[1][len(oldname):]
        if pinmap:
            expanded=[]
            for x in block:
                if not tag(x,'pin'):expanded.append(x);continue
                number=str(child(x,'number')[1])
                for index,target in enumerate(pinmap[number]):
                    clone=copy.deepcopy(x);child(clone,'number')[1]=str(target)
                    if index:clone.append([sx.Symbol('hide'),sx.Symbol('yes')])
                    expanded.append(clone)
            block[:]=expanded
    for key,value in properties.items():setprop(result,key,value)
    return result

def make_footprints():
    FPDIR.mkdir(exist_ok=True)
    src=FPSTD/'Package_SON.pretty/Infineon_PG-TDSON-8_6.15x5.15mm.kicad_mod'
    data=sx.load(src.open(encoding='utf-8'));name='BSC110N15NS5_TDSON8_8PhysicalPins';data[1]=name
    fingers=[a for a in children(data,'pad') if a[1]=='5' and 'F.Paste' in child(a,'layers')[1:]]
    assert len(fingers)==4
    for a,num,y in zip(sorted(fingers,key=lambda a:child(a,'at')[2],reverse=True),[5,6,7,8],[1.905,.635,-.635,-1.905]):
        a[1]=str(num);child(a,'at')[2]=y
    child(data,'descr')[1]='Project derivative of KiCad Infineon PG-TDSON-8. Eight physical lead numbers, 1.27 mm pitch; common drain tab numbered 5. Manufacturer DS Rev2.6 outline checked; prototype land pattern/thermal validation pending.'
    dump(FPDIR/(name+'.kicad_mod'),data)
    for count in [2,3,5,6]:
        src=FPSTD/('Connector_PinHeader_1.27mm.pretty/PinHeader_1x%02d_P1.27mm_Vertical.kicad_mod'%count)
        data=sx.load(src.open(encoding='utf-8'));name='PinHeader_HCTL_PZ127_1x%02d_P1.27mm_D0.70mm'%count;data[1]=name
        for a in children(data,'pad'):child(a,'drill')[1]=.70
        child(data,'descr')[1]='HCTL PZ127-1-N-Z project derivative; manufacturer drawing specifies 0.70 mm finished drill and 0.4 mm square pins. KiCad official geometry/3D reused.'
        dump(FPDIR/(name+'.kicad_mod'),data)
    for count,pitch in [(2,6),(3,15)]:
        name='WireSolder_%dP_P%.2fmm_D2.00mm'%(count,pitch)
        items=['(footprint '+q(name)+' (version 20260206) (generator pcbnew) (layer "F.Cu")',
               '(descr "Power wire solder holes; 2.0 mm finished hole, 4.5 mm copper. Cable/strain relief and current/thermal verification required.")',
               '(attr through_hole)',
               '(property "Reference" "J" (at 0 -3.5 0) (layer "F.Fab") (effects (font (size .7 .7))))',
               '(property "Value" '+q(name)+' (at 0 3.5 0) (layer "F.Fab") (effects (font (size .7 .7))))']
        for i in range(count):
            x=i*pitch
            items.append('(pad '+q(i+1)+' thru_hole '+('rect' if i==0 else 'circle')+' (at '+n(x)+' 0) (size 4.5 4.5) (drill 2) (layers "*.Cu" "*.Mask"))')
            for layer in ['F.CrtYd','B.CrtYd']:
                items.append('(fp_rect (start '+n(x-2.75)+' -2.75) (end '+n(x+2.75)+' 2.75) (stroke (width .05) (type default)) (fill none) (layer '+q(layer)+'))')
        items.append(')');(FPDIR/(name+'.kicad_mod')).write_text('\n'.join(items)+'\n',encoding='utf-8')
    table=B/'fp-lib-table';data=sx.load(table.open(encoding='utf-8'))
    if not any(child(v,'name')[1]=='Inverter_Compact' for v in children(data,'lib')):
        data.append(sx.loads('(lib (name "Inverter_Compact") (type "KiCad") (uri "${KIPRJMOD}/Inverter_Compact.pretty") (options "") (descr "60 mm project draft derivatives; no public library modification"))'))
        dump(table,data)

def main():
    make_footprints()
    power=json.loads((B/'tools/compact_power_parts.json').read_text(encoding='utf-8'))
    mechanical=json.loads((B/'tools/compact_mechanical_parts.json').read_text(encoding='utf-8'))
    control=json.loads((B/'tools/compact_control_placement.json').read_text(encoding='utf-8'))
    previous=json.loads((B/'tools/compact_design.json').read_text(encoding='utf-8'))['changes'] if (B/'tools/compact_design.json').exists() else {}
    # Full physical numbering is deliberately explicit, rather than hiding the
    # new package behind the old three-pin symbol/footprint contract.
    mospins={'1':[4],'2':[5,6,7,8],'3':[1,2,3]}
    local=sx.load((B/'InverterLocal.kicad_sym').open(encoding='utf-8'))
    lookup={x[1]:x for x in children(local,'symbol')}
    mosprops={'Value':'BSC110N15NS5','MPN':'BSC110N15NS5','Orderable_PN':'BSC110N15NS5ATMA1',
        'Footprint':'Inverter_Compact:BSC110N15NS5_TDSON8_8PhysicalPins','Manufacturer':'Infineon',
        'Supplier_PN':'C412739','Purchase_URL':'https://item.szlcsc.com/404529.html',
        'Datasheet':power['mosfet']['official_datasheet_url'],'Verification':'project_draft',
        'Datasheet_Revision':'Rev 2.6, 2022-11-07','Library_Revision':'C-compact-project','ki_keywords':'BSC110N15NS5 TDSON8 150V',
        'Selection_Status':'60mm layout candidate; physical 1-3 S,4 G,5-8 D; thermal/pulse/EMI pending',
        'Description':'150 V N MOSFET, TDSON-8; 1/2/3 Source,4 Gate,5/6/7/8 Drain; tab Drain. Project draft.'}
    diodeprops={'Value':'MBRD20150CT-13','MPN':'MBRD20150CT-13','Manufacturer':'Diodes',
        'Footprint':'Package_TO_SOT_SMD:TO-252-3_TabPin2','Supplier_PN':'C151357',
        'Purchase_URL':'https://item.szlcsc.com/162697.html','Datasheet':'https://www.diodes.com/datasheet/download/MBRD20150CT.pdf',
        'Verification':'project_draft','Selection_Status':'60mm input series-diode candidate; 1/3 A,2 K/tab visually checked Rev4-2 p1; thermal and production variant pending',
        'Datasheet_Revision':'DS37086 Rev 4-2, September 2026','Library_Revision':'C-compact-project','ki_keywords':'MBRD20150CT-13 DPAK Schottky 150V',
        'Description':'Dual 150 V common-cathode Schottky, TO252, 1/3 anode,2 cathode/tab; tied anodes retain original circuit.'}
    mos=new_symbol(lookup['IRFS4227TRLPBF'],'BSC110N15NS5',mosprops,mospins)
    diode=new_symbol(lookup['STPS40150CG_TR_CANDIDATE'],'MBRD20150CT_13',diodeprops)
    for sym in [mos,diode]:
        local[:]=[v for v in local if not(tag(v,'symbol') and v[1]==sym[1])];local.append(sym)
    dump(B/'InverterLocal.kicad_sym',local)
    changes={}
    for ref in ['Q1','Q2','Q3','Q4','Q5','Q6','Q7']:changes[ref]=dict(mosprops)
    changes['D1']=diodeprops
    for ref in ['F1','F2','L1','L2']:
        x=mechanical['parts'][ref]
        changes[ref]={'MPN':x['MPN'],'Manufacturer':x['manufacturer'],'Supplier_PN':x['Supplier_PN'],
                      'Purchase_URL':x['Purchase_URL'],'Datasheet':x['Datasheet'],
                      'Footprint':x['footprint'],'Selection_Status':x['selection_status']}
        if ref.startswith('F'):changes[ref]['Value']=x['MPN']
        else:changes[ref]['Value']='4.7uH'
    for ref in ['SW1','SW2']:
        x=mechanical['parts'][ref]
        changes[ref]={'MPN':x['MPN'],'Manufacturer':x['manufacturer'],'Supplier_PN':x['Supplier_PN'],
                      'Purchase_URL':x['Purchase_URL'],'Datasheet':x['Datasheet'],
                      'Footprint':x['footprint'],'Selection_Status':x['selection_status']}
    for ref,x in mechanical['connectors'].items():
        fp=x['footprint']
        if ref=='J4':fp='Inverter_Compact:WireSolder_3P_P15.00mm_D2.00mm'
        changes[ref]={'MPN':x.get('MPN') or 'PCB solder holes / wire assembly',
                      'Supplier_PN':x.get('Supplier_PN') or '', 'Purchase_URL':x.get('Purchase_URL') or '',
                      'Footprint':fp,'Selection_Status':'compact mechanical engineering candidate; original pin order retained'}
    # The owner supplies the exact, reviewed low-voltage list; no blanket
    # package shrinking of power shunts, bus dividers or large capacitors.
    shrink=control['resistor_capacitor_conversion']
    rs=shrink['resistor_0402_refs'];cs=shrink['capacitor_0402_refs']
    assert len(rs)==89 and len(cs)==40,('unexpected compact-passive list keys',control.keys(),len(rs),len(cs))
    for ref in rs:changes.setdefault(ref,{})['Footprint']='Resistor_SMD:R_0402_1005Metric'
    for ref in cs:changes.setdefault(ref,{})['Footprint']='Capacitor_SMD:C_0402_1005Metric'
    for ref in ['R19','R20','R25','R26','R31','R32','R17']:
        changes.setdefault(ref,{}).update(Footprint='Resistor_SMD:R_0805_2012Metric',
            Design_Note='Retain 0805 gate resistor; exact YAGEO pulse-rated MPN and gate waveform verification pending')
    for ref in ['C26','C28','C30','C32','C34','C36']:
        changes.setdefault(ref,{})['Footprint']='Capacitor_SMD:C_0603_1608Metric'
    changes['R8']={'Design_Note':'DNP: remove external 12..24V SHDN pullup. TPS26600 internal SHDN bias is nominal 2.7V, recommended SHDN 0..4V. SW1 still pulls to EFUSE_RTN.',
                   'Selection_Status':'compact revision electrical correction; retain footprint, do not populate'}
    seen=set()
    for file in B.glob('*.kicad_sch'):
        data=sx.load(file.open(encoding='utf-8'));libs=child(data,'lib_symbols');touched=False
        for sym in children(data,'symbol'):
            fields={v[1]:v for v in children(sym,'property')};ref=fields['Reference'][2]
            if ref not in changes:continue
            before={k:v[2] for k,v in fields.items()}
            if ref.startswith('Q') and ref!='Q8':
                child(sym,'lib_id')[1]='InverterLocal:BSC110N15NS5'
                sym[:]=[v for v in sym if not tag(v,'pin')]
                for pin in range(1,9):sym.append([sx.Symbol('pin'),str(pin),[sx.Symbol('uuid'),str(uuid.uuid4())]])
                libs[:]=[v for v in libs if not(tag(v,'symbol') and v[1]=='InverterLocal:BSC110N15NS5')]
                v=copy.deepcopy(mos);v[1]='InverterLocal:BSC110N15NS5';libs.append(v)
            if ref=='D1':
                child(sym,'lib_id')[1]='InverterLocal:MBRD20150CT_13'
                libs[:]=[v for v in libs if not(tag(v,'symbol') and v[1]=='InverterLocal:MBRD20150CT_13')]
                v=copy.deepcopy(diode);v[1]='InverterLocal:MBRD20150CT_13';libs.append(v)
            for key,value in changes[ref].items():setprop(sym,key,value)
            if ref=='R8':child(sym,'dnp')[1]=sx.Symbol('yes')
            changes[ref]['before_fields']=previous.get(ref,{}).get('before_fields') or {k:before.get(k,'') for k in changes[ref] if k!='before_fields'}
            seen.add(ref);touched=True
        title=child(data,'title_block')
        for note in children(data,'text'):
            if 'TO-263 / driver / shunt' in note[1]:note[1]=note[1].replace('TO-263 / driver / shunt','TDSON8 / driver / shunt');touched=True
        if title:
            child(title,'rev')[1]='C-compact-draft';child(title,'date')[1]='2026-11-06';touched=True
        if touched:dump(file,data)
    assert seen==set(changes),set(changes)-seen
    manifest={'revision':'C / PCB0.2','board_mm':[60,60],'snapshot':'inverter/history/pcb_0_1_200x140_before_60mm_2026-11-06.zip',
        'mos_pin_contract':{'G':[4],'D':[5,6,7,8],'S':[1,2,3]},'changes':changes,
        'DNP_changes':{'R8':{'from':False,'to':True,'reason':'Remove high-voltage SHDN pullup; use internal 2.7V bias, retain reset switch. TI TPS2660 RevG pp6-7,26.'}},
        'topology':'All original net connectivity preserved modulo explicit transistor physical terminal expansion',
        'fabrication_ready':False}
    (B/'tools/compact_design.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Migrated explicit component records:',len(changes),'no schematic wires changed')

if __name__=='__main__':main()

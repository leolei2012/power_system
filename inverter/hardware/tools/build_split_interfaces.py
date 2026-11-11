"""Recorded Rev D mating headers and MCU-side ADC protection authoring.

Uses the existing native drawing helper. Does not regenerate migrated sheets.
"""
from pathlib import Path
import sys,copy,json,uuid,zipfile,xml.etree.ElementTree as ET
import schematic_common as s

POWER=s.BASE;CORE=POWER.parents[1]/'controller/hardware/g431_core'
CORE_ROOT='9dba1312-bd1c-50b2-9df7-fc81461aaf77'
POWER_ROOT='c6bbe498-7a84-5001-ab1e-dd9afbac55ac'
DIGITAL={1:'SUPPLY',2:'GND',3:'SUPPLY',4:'GND',5:'PWM_UH_IN',6:'PWM_UL_IN',7:'GND',8:'PWM_VH_IN',9:'PWM_VL_IN',10:'GND',11:'PWM_WH_IN',12:'PWM_WL_IN',13:'GND',14:'ENABLE_IN',15:'BRAKE_IN',16:'GND',17:'CTRL_READY',18:'BASE_READY',19:'FAULT_N',20:'GND'}
ANALOG={1:'I_U_PORT',2:'GND',3:'I_V_PORT',4:'GND',5:'I_W_PORT',6:'GND',7:'V_DC_PORT',8:'GND',9:'V_U_PORT',10:'GND',11:'V_V_PORT',12:'GND',13:'V_W_PORT',14:'GND',15:'TEMP_NTC',16:'GND',17:'+5V_SENSOR',18:'+5V_SENSOR',19:None,20:None}

def page(base,project,root,name,path,title):
    s.BASE=base;s.PROJECT=project;s.ROOT=root;s.NS=uuid.uuid5(uuid.NAMESPACE_URL,'power_system/revd/'+project)
    p=s.Page(name,title,8 if project=='controller' else 16);p.path=path
    return p

def save(p):
    p.write();file=s.BASE/(p.name+'.kicad_sch');d=s.sx.load(file.open(encoding='utf-8'))
    t=s.child(d,'title_block');s.child(t,'date')[1]='2026-11-06';s.child(t,'rev')[1]='D-split-draft'
    s.children(t,'comment')[1][2]='NON-ISOLATED PLUG-IN SYSTEM / COMMON GND / 5 V FEED / NO HOT PLUG'
    if p.name=='core_interface':
        # Put each status-clamp caption above its own symbol, clear of the
        # preceding channel wire and the section heading.
        for symbol in s.children(d,'symbol'):
            props={v[1]:v for v in s.children(symbol,'property')}
            if props['Reference'][2] in ['D209','D210']:
                at=s.child(symbol,'at')
                s.child(props['Reference'],'at')[1:3]=[at[1],at[2]-5.08]
                s.child(props['Value'],'at')[1:3]=[at[1],at[2]-2.54]
    file.write_text('('+str(d[0])+'\n'+'\n'.join(s.sx.dumps(v) if isinstance(v,list) else str(v) for v in d[1:])+')\n',encoding='utf-8')

def headers(p,core):
    fp='Connector_PinHeader_2.54mm:PinHeader_2x10_P2.54mm_Vertical' if core else 'Connector_PinSocket_2.54mm:PinSocket_2x10_P2.54mm_Vertical'
    mpn='PZ254V-12-20P' if core else 'PM254V-12-20-H85';code='C492427' if core else 'C46595987'
    fields={'Manufacturer':'XFCN','MPN':mpn,'Supplier_PN':code,'Purchase_URL':'https://www.lcsc.com/product-detail/'+code+'.html',
      'Verification':'project_draft','Selection_Status':'2x10 P2.54 candidate; actual mating height, pin1 and land pattern verification pending',
      'Design_Note':'Signal/auxiliary header only. Controller male mounted toward base socket; physical pin1 mating must be checked in PCB. Never connect motor/DC bus.'}
    for idx,mapping in [(101,DIGITAL),(102,ANALOG)]:
        x=86.36 if idx==101 else 281.94
        p.section('J%d / %s'%(idx,'DIGITAL + CORE 5V' if idx==101 else 'ANALOG + SENSOR 5V'),20.32 if idx==101 else 215.9,17.78,175)
        j=p.inst('Connector_Generic:Conn_02x10_Odd_Even','J'+str(idx),mpn,x,53.34,fp=fp,fields=fields)
        for pin,net in mapping.items():
            if net=='SUPPLY':net='+5V_CORE_IN' if core else '+5V_INV'
            j.nc(pin) if net is None else j.connect(pin,net,7.62)
    p.text('Mate J101 pin-to-pin and J102 pin-to-pin; two separate connectors. No 3V3 rail or raw NRST crosses the interface.',20.32,76.2,1.05)

def core():
    p=page(CORE,'controller',CORE_ROOT,'core_interface','/'+CORE_ROOT+'/3014856e-ebdc-51b8-bbfc-2d79015f320d','Controller - mating headers and ADC interface protection')
    headers(p,True);p.section('ADC INPUT LIMITING / EXTERNAL SCHOTTKY CLAMPS / RC REMAINS NEXT TO MCU',20.32,86.36,375)
    for i,raw in enumerate([ANALOG[k] for k in range(1,16,2)]):
        col=i//4;row=i%4;x=55.88+203.2*col;y=109.22+38.1*row
        p.text(raw+' -> existing 100R / 1n RC',20.32+203.2*col,y-15.24,1.02)
        r=p.inst('Device:R','R'+str(201+i),'360',x,y+12.7,90,fp='Resistor_SMD:R_0603_1608Metric',fields={'Manufacturer':'YAGEO','MPN':'TBD','Tolerance':'1%','Selection_Status':'exact YAGEO MPN pending','Design_Note':'Input transient limiting; with original 100R gives 460R / 1n, tau about 0.46us. Not a 60V fault barrier.'})
        r.connect(1,raw,5.08)
        d=p.inst('Device:D_Schottky_Dual_Series_AKC','D'+str(201+i),'BAT54S,215',x+35.56,y,fp='Package_TO_SOT_SMD:SOT-23',fields={'Manufacturer':'Nexperia','MPN':'BAT54S,215','Supplier_PN':'C47546','Purchase_URL':'https://www.lcsc.com/product-detail/C47546.html','Datasheet':'https://assets.nexperia.com/documents/data-sheet/BAT54S.pdf','Verification':'project_draft','Design_Note':'DS 2022-07-01: pin1=A1 GND; pin2=K2 3V3_MCU; pin3=K1/A2 clamped signal. Basic transient clamps, no galvanic isolation.'})
        d.connect(1,'GND',2.54);d.connect(2,'+3V3_MCU',2.54)
        a=r.pt(2);b=d.pt(3);node=(b[0],a[1]);p.wire(a,node);p.wire(node,b);p.junction(node)
        end=(x+71.12,a[1]);p.wire(node,end);p.label(raw+'_CLAMPED',end)
    r=p.inst('Device:R','R209','10k',210.82,58.42,fp='Resistor_SMD:R_0603_1608Metric',fields={'Manufacturer':'YAGEO','MPN':'TBD','Design_Note':'BASE_READY_MCU reads LOW if unplugged or the base output is unpowered.'})
    # Keep return-status pins behind current limiting and rail clamps as well.
    r.connect(2,'GND',2.54)
    for idx,(raw,dest,y) in enumerate([('BASE_READY','BASE_READY_MCU',45.72),('FAULT_N','FAULT_N_MCU',71.12)]):
        rr=p.inst('Device:R','R'+str(210+idx),'1k',144.78,y,90,fp='Resistor_SMD:R_0603_1608Metric',fields={'Manufacturer':'YAGEO','MPN':'TBD','Tolerance':'1%','Design_Note':'Return-status transient limiting; 1k with the 10k local pull gives valid logic levels. No isolation.'})
        rr.connect(1,raw,5.08)
        dd=p.inst('Device:D_Schottky_Dual_Series_AKC','D'+str(209+idx),'BAT54S,215',177.8,y-12.7,fp='Package_TO_SOT_SMD:SOT-23',fields={'Manufacturer':'Nexperia','MPN':'BAT54S,215','Supplier_PN':'C47546','Purchase_URL':'https://www.lcsc.com/product-detail/C47546.html','Datasheet':'https://assets.nexperia.com/documents/data-sheet/BAT54S.pdf','Verification':'project_draft','Design_Note':'1 GND,2 3V3_MCU,3 protected return status. Fault pullup remains on the protected MCU side.'})
        dd.connect(1,'GND',2.54);dd.connect(2,'+3V3_MCU',2.54)
        node=(dd.pt(3)[0],rr.pt(2)[1]);p.wire(rr.pt(2),node);p.wire(node,dd.pt(3));p.junction(node)
        end=(210.82,y);p.wire(node,end);p.label(dest,end)
        if idx==0:p.wire(end,r.pt(1));p.junction(end)
    flag=p.inst('power:PWR_FLAG','#FLG901','PWR_FLAG',383.54,58.42)
    flag.connect(1,'+5V_SENSOR',2.54)
    p.text('Sensor 5V is supplied by the base',330.2,69.85,.95)
    p.text('PWM / ENABLE / BRAKE / CTRL_READY: core -> base. ADC / BASE_READY / FAULT_N: base -> core.',20.32,265.43,1.02)
    p.text('Clamps limit small-energy interface transients; common-ground faults can still damage the core. Not hot-pluggable.',20.32,270.51,1.02)
    p.text('3V3 rails are independent. Calibrate ADC offset/gain and allow the added RC settling time; no sustained bus-fault immunity claimed.',20.32,275.59,.95)
    save(p)

def power():
    p=page(POWER,'inverter',POWER_ROOT,'power_interface','/'+POWER_ROOT+'/dd750428-343f-5f14-ae26-2a2ef90fee57','Inverter power base - mating headers')
    p.uuid='c39ca4a6-4ba8-5608-aa25-320e580332a2';headers(p,False)
    p.section('LOCAL SHUTDOWN REMAINS ON THIS BOARD',20.32,104.14,375)
    p.text('ENABLE_IN AND CTRL_READY -> ENABLE_QUALIFIED. Both inputs have local pull-downs; unplugged/reset core disables the bridge.',20.32,116.84,1.2)
    p.text('BASE_READY = BASE_LOGIC_OK AND DRV_PG_LOGIC. FAULT_N is the Q8 open collector; its pull-up belongs to the controller 3V3 domain.',20.32,129.54,1.15)
    p.text('J101 1/3 deliver +5V_INV to the core. J102 17/18 separately deliver the current-limited +5V_SENSOR branch.',20.32,142.24,1.15)
    p.text('J101/J102 carry no DC bus or phase current. Signal grounds return locally; keep switching-current loops away from header returns.',20.32,154.94,1.15)
    with zipfile.ZipFile(POWER.parent/'history/integrated_60x60_rev_c_before_mcu_split_2026-11-06.zip') as archive:
        tree=ET.fromstring(archive.read('inverter/hardware/review/inverter.net.xml'))
    for ref,net,x in [('TP16','FAULT_N',76.2),('TP17','ENABLE_IN',203.2)]:
        c=next(c for c in tree.findall('./components/comp')if c.attrib['ref']==ref)
        fields={f.attrib['name']:f.text or ''for f in c.findall('./fields/field')}
        t=p.inst('Connector:TestPoint',ref,c.findtext('value'),x,198.12,fp=c.findtext('footprint'),fields=fields);t.connect(1,net,5.08)
    p.text('Mechanical review: bottom-facing male on core, top-facing socket on base; confirm pin1, rotations, standoffs and anti-misplug spacing.',20.32,241.3,1.05)
    p.text('Non-isolated laboratory prototype. Switch off both supplies before insertion/removal; interface clamps do not isolate a blown power stage.',20.32,254,1.05)
    save(p)

if __name__=='__main__':
    core();power()
    contract={'revision':'D-modular-draft','pitch_mm':2.54,'pin_count':40,'J101':{str(k):v for k,v in DIGITAL.items()},'J102':{str(k):v for k,v in ANALOG.items()},'supply_alias':{'controller':'SUPPLY = +5V_CORE_IN','inverter':'SUPPLY = +5V_INV'},'note':'Common GND; separate 3V3 rails; physical pin1/mating orientation must be checked in PCB.'}
    (POWER.parents[1]/'docs/daughterboard_pin_contract.json').write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8')
    print('Created both Rev D interface sheets and exact 40-pin contract')

"""One-time Rev A -> integrated STM32G431 Rev B drawing record.

Reads the archived Rev A, not build_inverter.py; preserves existing power circuits.
DO NOT rerun over later manual edits. --write is deliberately required.
"""
from schematic_common import *
import argparse
import io
import zipfile

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--write', action='store_true')
args=parser.parse_args()
assert args.write, 'Explicit --write required; this replaces the Rev B drawing.'
archive=BASE.parent/'history/split_rev_a_2026-11-06.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ddf02a894b393ae0f5daab146b57430e298ea2ed765a1c85b54617d7ed1a465e'
z=zipfile.ZipFile(archive)
def old(name):
    key=next(v for v in z.namelist() if v.replace('\\','/').endswith('/'+name))
    return z.read(key).decode('utf-8-sig')
def parse_old(name): return sx.loads(old(name))
def props(sym):return {str(v[1]):str(v[2]) for v in children(sym,'property')}
def native_write(name,data):
    (BASE/name).write_text('('+str(data[0])+'\n'+'\n'.join(sx.dumps(v) if isinstance(v,list) else str(v) for v in data[1:])+')\n',encoding='utf-8')
def change_strings(v,fn):
    if isinstance(v,list):return [change_strings(x,fn) for x in v]
    if isinstance(v,str):return fn(v)
    return v
def set_title(d,title):
    t=child(d,'title_block')
    child(t,'title')[1]=title;child(t,'date')[1]='2026-11-06';child(t,'rev')[1]='B-integrated-draft'
    return d

# New designators start after the existing drawing; all existing power refs survive.
old_bom=list(csv.DictReader(io.StringIO(old('review/bom.csv'))))
for prefix in ['R','C','J','D','TP','U','Y','SW','PF']:
    counts[prefix]=max([int(r['Reference'][len(prefix):]) for r in old_bom
                        if r['Reference'].startswith(prefix) and r['Reference'][len(prefix):].isdigit()]+[0])
counts['PF']=100  # Existing hidden power flags are not physical BOM records.
new_pages=[]
new_expected=[]

# Resolve KiCad's official inherited G431 symbol into a project-local full symbol.
mculib=sx.load((STD/'MCU_ST_STM32G4.kicad_sym').open(encoding='utf-8'))
base_symbol=copy.deepcopy(next(x for x in mculib if tag(x,'symbol') and x[1]=='STM32G431R_6-8-B_Tx'))
leaf=next(x for x in mculib if tag(x,'symbol') and x[1]=='STM32G431RBTx')
oldname=base_symbol[1];base_symbol[1]='InverterLocal:STM32G431RBT6'
for u in children(base_symbol,'symbol'):u[1]=u[1].replace(oldname+'_','STM32G431RBT6_')
for p in children(base_symbol,'property'):base_symbol.remove(p)
for p in children(leaf,'property'):base_symbol.append(copy.deepcopy(p))
local=sx.loads(old('InverterLocal.kicad_sym'))
meta={'Value':'STM32G431RBT6','Manufacturer':'STMicroelectronics','MPN':'STM32G431RBT6',
      'Supplier':'LCSC','Supplier_PN':'C431633','Purchase_URL':'https://item.szlcsc.com/428111.html',
      'Verification':'project_draft','Selection_Status':'Rev B drawing candidate; shared library intake not performed',
      'Datasheet':'https://www.st.com/resource/en/datasheet/stm32g431rb.pdf',
      'Design_Note':'LQFP64; physical pins per DS12589 Rev6 Fig10/Table12; no external VCAP pin'}
for k,v in meta.items():
    p=next((p for p in children(base_symbol,'property') if p[1]==k),None)
    if p:p[2]=v
    else:base_symbol.append(sx.loads(f'(property {q(k)} {q(v)} (at 0 0 0) (hide yes) {effects(1)})'))
cache[base_symbol[1]]=base_symbol
s=copy.deepcopy(base_symbol);s[1]='STM32G431RBT6';local.append(s)
native_write('InverterLocal.kicad_sym',local)

def cap(p,x,y,value,net,b='GND',notes='',dnp=False):
    c=capacitor(p,x,y,value,notes=notes,dnp=dnp);c.connect(1,net,2.54);c.connect(2,b,2.54);return c
def rr(p,x,y,value,a,b,angle=0,dnp=False,notes=''):
    r=resistor(p,x,y,value,angle,dnp,notes);r.fields['Tolerance']='1%'
    r.connect(1,a,5.08 if angle==90 else 2.54);r.connect(2,b,5.08 if angle==90 else 2.54);return r
def flag(p,x,y,net):
    c=p.inst('power:PWR_FLAG',f'#FLG{ref("PF")[2:]}','PWR_FLAG',x,y);c.connect(1,net,2.54)
def port(p,x,y,count,value,mapping,dnp=False):
    j=connector(p,x,y,count,value,dnp=dnp)
    for k,v in mapping.items():j.nc(k) if v is None else j.connect(k,v)
    return j
def note(p,text,x=20.32,y=269.24):p.text(text,x,y,1.02)

# Remove a connector and only the geometrically attached pin stubs. Global labels
# do not make the geometric walk jump across the drawing.
def remove_connector(d,reference):
    inst=next(s for s in children(d,'symbol') if props(s).get('Reference')==reference)
    lib=next(s for s in children(child(d,'lib_symbols'),'symbol') if s[1]==child(inst,'lib_id')[1])
    px,py,ang=child(inst,'at')[1:];unit=child(inst,'unit')[1]
    pts=set()
    for sub in children(lib,'symbol'):
        if int(sub[1].rsplit('_',2)[1]) not in [0,unit]:continue
        for pin in children(sub,'pin'):
            x,y,_=child(pin,'at')[1:];a=math.radians(ang)
            pts.add((round(px+x*math.cos(a)-y*math.sin(a),4),round(py-x*math.sin(a)-y*math.cos(a),4)))
    remove=[inst]
    changed=True
    while changed:
        changed=False
        for wire in children(d,'wire'):
            ends={tuple(v[1:]) for v in child(wire,'pts')[1:]}
            if ends & pts and wire not in remove:
                remove.append(wire);pts |= ends;changed=True
    for key in ['global_label','label','no_connect','junction']:
        for it in children(d,key):
            if tuple(child(it,'at')[1:3]) in pts:remove.append(it)
    return [v for v in d if v not in remove]

renames={'+5V_CTRL_OUT':'+5V_SENSOR','CTRL_ILIM':'SENSOR_ILIM','CTRL_PWR_FLT_N':'SENSOR_PWR_FLT_N'}
retained={}
for name in ['aux_input','supply_12v','supply_logic','bus_brake','bridge_u','bridge_v','bridge_w',
             'current_sense','voltage_sense','comparators','fault_logic','control_interface']:
    d=parse_old(name+'.kicad_sch')
    if name=='bus_brake':d=remove_connector(d,'J6')
    if name=='control_interface':d=remove_connector(d,'J1')
    d=change_strings(d,lambda s:renames.get(s,s))
    for t in children(d,'text'):
        t[1]=t[1].replace('cable and controller ADC RC','local MCU ADC RC').replace('cable/ADC','MCU ADC')
        if name=='supply_logic' and 'No motor ENABLE' in t[1]:
            t[1]='3.3 V supervisor also resets local G431; LOGIC_POWER_OK is the NRST net. CT left open.\nTPS2553 now supplies optional +5V_SENSOR, not another controller. Nominal 0.5 A branch target.\nTPS7A2033PDBVR rated 300 mA: MCU, analog, logic, CAN and LEDs share the available thermal/current budget. External sensor power defaults disconnected.'
        if name=='supply_logic' and 'PROTECTED 5 V TO CONTROLLER' in t[1]:t[1]='PROTECTED 5 V SENSOR BRANCH / INDEPENDENT OF ENABLE'
        if name=='bus_brake' and 'SEPARATE CONTROL CONNECTOR' in t[1]:t[1]='BRAKE: EXTERNAL RESISTOR / LOCAL MCU COMMAND'
        if name=='control_interface' and 'SIGNAL-ONLY 24-PIN' in t[1]:t[1]='LOCAL MCU / SIX COMPLEMENTARY TIM1 SIGNALS'
        if name=='control_interface' and 'GND contacts:' in t[1]:
            t[1]='STM32G431 on this PCB replaces the old 24-pin control cable.\nTIM1 -> 33R -> local PWM inputs -> independent AND gates -> drivers.\nENABLE has a physical pulldown. FAULT_N also enters TIM1 BKIN.\nBRAKE is independent TIM8_CH1; power-stage faults do not reset MCU.\nAll signals share this inverter DC-; this drawing has no isolation barrier.'
    if name=='supply_logic':
        j=next(s for s in children(d,'symbol') if props(s).get('Reference')=='J7')
        child(j,'dnp')[1]=sx.Symbol('yes')
        next(p for p in children(j,'property') if p[1]=='Value')[2]='OPTIONAL SENSOR 5V / GND'
        set_title(d,'Inverter - 5 V, 3.3 V and sensor power')
    else:set_title(d,{'control_interface':'Inverter - local six PWM hardware gates'}.get(name,child(child(d,'title_block'),'title')[1]))
    retained[name]=d

plan=list(csv.DictReader((BASE/'STM32G431RBT6_pin_plan.csv').open(encoding='utf-8-sig')))
assert len(plan)==64 and {int(r['Pin']) for r in plan}==set(range(1,65))
by_pin={str(r['Pin']):r for r in plan}

# 14. MCU: one VDD decoupler per physical pin, explicit analog/reference rails.
p=Page('mcu','Inverter - STM32G431 minimum system',14);new_pages.append(p)
p.section('LOCAL MCU / STM32G431RBT6 / LQFP64',20.32,17.78,370)
u=p.inst('InverterLocal:STM32G431RBT6','U30','STM32G431RBT6',111.76,134.62)
vdd=['1','16','32','48','64'];gy=200.66;vy=76.2
for pin in vdd:
    x,y=u.pt(pin);p.wire((x,y),(x,vy));p.expected.append(('U30',pin,'+3V3_INV'))
p.wire((106.68,vy),(116.84,vy))
for pin in vdd:
    x,_=u.pt(pin);p.junction((x,vy))
p.label('+3V3_INV',(106.68,vy),180)
for pin in ['15','31','47','63']:
    p.expected.append(('U30',pin,'GND'))
x,y=u.pt(15);p.wire((x,y),(x,gy));p.wire((x,gy),(132.08,gy));p.label('GND',(132.08,gy),0)
for pin in ['27','29']:
    x,y=u.pt(pin);end=(x,gy) if pin=='27' else (x,68.58)
    p.wire((x,y),end);p.label('GND' if pin=='27' else '+3V3_A_MCU',end,0)
    p.expected.append(('U30',pin,'GND' if pin=='27' else '+3V3_A_MCU'))
for pin,row in by_pin.items():
    if pin in vdd+['15','31','47','63','27','29']:continue
    if row['Net']=='NC':u.nc(pin)
    else:u.connect(pin,row['Net'],10.16)
p.text('TIM1: 3 complementary pairs + active-low BKIN\nTIM8 CH1: independent brake command\nTIM2 / TIM4: independent AB encoder counters\nSPI1 / SPI3: independent SPI ports\nUSART3: TTL; PA13/14: SWD\nFDCAN1: optional CLASSIC CAN PHY\n4 GPIO LEDs + one supply LED\n8 external ADC channels, 2 ADC converters',218.44,50.8,1.25)
p.text('INIT REQUIREMENTS\nENABLE/BRAKE remain low until supply and ADC checks pass.\nBKIN low-active; AOE disabled; configure before enabling MOE.\nKeep PG10 in reset mode, PA13/14 in SWD mode.\nRelease JTAG AF on PA15/PB3/PB4 when required.\nPB8 is BOOT0 only, with physical pulldown.\nThree current channels cannot be captured by three ADCs\nsimultaneously; injected conversion timing needs validation.',218.44,109.22,1.08)
p.section('VDD / VBAT DECOUPLING',20.32,226.06,370)
for i,pin in enumerate(['16','32','48','64','1']):
    x=40.64+i*55.88;c=cap(p,x,251.46,'100n','+3V3_INV');c.fields['Design_Note']='Place at U30 pin '+pin+'; return locally to VSS'
cap(p,350.52,251.46,'4.7u','+3V3_INV')
note(p,'VBAT tied to VDD; no battery or LSE. G431 LQFP64 has no external VCAP. Ground is shunt LOW / DC-, never a low-MOS SOURCE.\nVREF+ is externally driven from VDDA (about 3.3 V); keep internal VREFBUF disabled. 1.65 V current bias is NOT the ADC reference.',20.32,278.13)

# 15. Local analog filters and reference. Keep protection taps upstream.
p=Page('mcu_analog','Inverter - local ADC filters and analog supply',15);new_pages.append(p)
p.section('LOCAL ADC INPUT FILTERS / PROTECTION SENSES BEFORE 47R',20.32,17.78,370)
signals=['I_U','I_V','I_W','V_DC','V_U','V_V','V_W','TEMP_NTC']
for i,sig in enumerate(signals):
    x=55.88+(i%4)*93.98;y=60.96+(i//4)*68.58
    source=sig+'_PORT' if sig!='TEMP_NTC' else sig;dest='ADC_'+sig
    rr(p,x,y,'100',source,dest,90,notes='Local ADC isolation; 47R source isolator also present except NTC')
    cap(p,x+25.4,y+20.32,'1n',dest,notes='Provisional RC; acquisition time and PWM sampling window to be validated')
    p.text(sig+' -> '+next(r['GPIO'] for r in plan if r['Net']==dest),x-25.4,y-20.32,1.05)
p.section('ANALOG SUPPLY / EXTERNAL ADC REFERENCE',20.32,190.5,370)
rr(p,63.5,220.98,'0','+3V3_INV','+3V3_A_MCU',90,notes='Default 0R; no unvalidated ferrite LC inserted')
cap(p,127,226.06,'100n','+3V3_A_MCU');cap(p,172.72,226.06,'1u','+3V3_A_MCU')
rr(p,251.46,220.98,'0','+3V3_A_MCU','VREF_MCU',90,notes='External VREF supply; VREFBUF disabled')
cap(p,309.88,226.06,'100n','VREF_MCU');cap(p,355.6,226.06,'1u','VREF_MCU')
flag(p,172.72,259.08,'+3V3_A_MCU');flag(p,309.88,259.08,'VREF_MCU')
note(p,'Current gain stays 50 mV/A around 1.65 V; 50:1 voltage scaling unchanged. Comparator inputs remain on local analog nodes.\nNew 100R/1nF filters are provisional. NTC already has 10k pull-up/10nF upstream; choose a longer ADC sampling time.\nNo off-board analog/control cable. MCU/analog inputs and optional external sensors still require power-off injection / ESD review.',20.32,278.13)

# 16. Encoders and SPI. Keep historical 3.3 V single-ended interface boundary.
p=Page('sensors','Inverter - two ABZ and two SPI ports',16);new_pages.append(p)
p.section('TWO INDEPENDENT ABZ ENCODER PORTS / 3.3 V SINGLE-ENDED',20.32,17.78,370)
port_records={}
for i,ch in enumerate('AB'):
    x=60.96+i*190.5
    j=port(p,x,58.42,5,'ENC_'+ch+': PWR GND A B Z',{1:'ENC_'+ch+'_VCC',2:'GND',3:'ENC_'+ch+'_A_PORT',4:'ENC_'+ch+'_B_PORT',5:'ENC_'+ch+'_Z_PORT'})
    port_records[j.ref]=dict(type='ABZ',channel=ch,pins={1:'ENC_'+ch+'_VCC',2:'GND',3:'ENC_'+ch+'_A_PORT',4:'ENC_'+ch+'_B_PORT',5:'ENC_'+ch+'_Z_PORT'})
    for k,sig in enumerate('ABZ'):
        net='ENC_'+ch+'_'+sig;rr(p,x+38.1,88.9+k*15.24,'100',net+'_PORT',net,90)
        rr(p,x+93.98,88.9+k*15.24,'10k',net,'+3V3_INV',notes='For 3.3V open-collector/push-pull only; no 5V logic')
    rr(p,x+38.1,139.7,'0','+5V_SENSOR','ENC_'+ch+'_VCC',90,True,notes='DNP until encoder power/output stage selected; 5V supply is not 5V logic compatibility')
p.section('TWO INDEPENDENT SPI PORTS / 3.3 V LOGIC ONLY',20.32,165.1,370)
for i,ch in enumerate('AB'):
    x=60.96+i*190.5
    mp={1:'SPI_'+ch+'_VCC',2:'GND',3:'SPI_'+ch+'_SCK_PORT',4:'SPI_'+ch+'_MOSI_PORT',5:'SPI_'+ch+'_MISO_PORT',6:'SPI_'+ch+'_CS_PORT'}
    j=port(p,x,205.74,6,'SPI_'+ch+': PWR GND SCK MOSI MISO CS',mp)
    port_records[j.ref]=dict(type='SPI',channel=ch,pins=mp)
    for k,sig in enumerate(['SCK','MOSI','MISO','CS']):
        net='SPI_'+ch+'_'+sig;rr(p,x+38.1,185.42+k*20.32,'33',net,net+'_PORT',90)
    rr(p,x+104.14,238.76,'10k','SPI_'+ch+'_CS','+3V3_INV')
    rr(p,x+104.14,205.74,'0','+5V_SENSOR','SPI_'+ch+'_VCC',dnp=True,notes='DNP until external module is selected; IO stays 3.3V')
note(p,'A/B use TIM2 or TIM4 encoder mode; Z uses EXTI2/EXTI3 (no hardware index-reset claim). No Hall input.\nExternal power links default DNP. 0.5 A is the TOTAL shared 5V_SENSOR branch budget, not per port.\nDo not connect 5 V / differential encoder signals directly. Encoder line receivers and cable protection depend on the actual encoder.',20.32,278.13)

# 17. Debug, communication and local control coupling.
p=Page('debug_comms','Inverter - SWD TTL optional CAN and status',17);new_pages.append(p)
p.section('SWD / NRST / BOOT',20.32,17.78,180)
j=port(p,55.88,55.88,5,'SWD: VTREF IO CLK GND NRST',{1:'+3V3_INV',2:'SWDIO_PORT',3:'SWCLK_PORT',4:'GND',5:'LOGIC_POWER_OK'})
rr(p,109.22,48.26,'33','SWDIO_PORT','SWDIO',90);rr(p,109.22,66.04,'33','SWCLK_PORT','SWCLK',90)
sw=p.inst('Switch:SW_Push',ref('SW'),'MCU_RESET',63.5,93.98,fp='');sw.connect(1,'LOGIC_POWER_OK');sw.connect(2,'GND')
cap(p,127,93.98,'100n','LOGIC_POWER_OK',notes='NRST; TPS3808 and reset button/SWD share open-drain reset domain')
rr(p,172.72,93.98,'10k','BOOT0','GND');testpoint(p,172.72,121.92,'BOOT0')
p.text('VTREF is sense only; SWD probe must not power this rail.\nNRST = LOGIC_POWER_OK, already pulled up at U6.\nFAULT_N is NOT NRST; reset/boot default outputs are low.\nPB8 pulldown; set boot option bytes deliberately.',20.32,114.3,.97)
p.section('TTL UART / 3.3 V LOGIC',218.44,17.78,170)
j=port(p,256.54,55.88,3,'TTL: TX RX GND',{1:'UART_TX_PORT',2:'UART_RX_PORT',3:'GND'})
rr(p,325.12,48.26,'33','UART_TX','UART_TX_PORT',90);rr(p,325.12,66.04,'100','UART_RX_PORT','UART_RX',90)
rr(p,365.76,93.98,'10k','UART_RX','+3V3_INV')
p.text('USART3; directions relative to inverter MCU.\nNo supply pin, no RS-232 levels, no USB.',223.52,116.84,1.0)
p.section('OPTIONAL CLASSIC CAN / ENTIRE PHY BLOCK DNP',20.32,149.86,370)
can=p.inst('MyParts:SN65HVD232DR','U31','SN65HVD232DR',99.06,185.42,dnp=True)
for pin,net in {1:'CAN_TX_PHY',2:'GND',3:'+3V3_INV',4:'CAN_RX_PHY',6:'CAN_L',7:'CAN_H'}.items():can.connect(pin,net)
can.nc(5);can.nc(8)
rr(p,43.18,175.26,'0','CAN_TX','CAN_TX_PHY',90,True);rr(p,43.18,200.66,'0','CAN_RX_PHY','CAN_RX',90,True)
rr(p,154.94,190.5,'10k','CAN_TX_PHY','+3V3_INV',dnp=True);cap(p,154.94,165.1,'100n','+3V3_INV',dnp=True)
j=port(p,243.84,187.96,3,'CAN: H L GND',{1:'CAN_H',2:'CAN_L',3:'GND'},True)
rr(p,309.88,185.42,'120','CAN_H','CAN_L',90,True,notes='Fit only at bus end; CAN PHY is classic <=1Mbps, not CAN-FD rated')
p.text('FDCAN controller used in classic-CAN mode.\nPHY / links / pullup / bypass / connector default DNP.\nOptional 120R termination only at physical bus end.\nESD/common-mode/isolation review before field use.',218.44,207.01,1.0)
p.section('FIVE STATUS INDICATORS',20.32,238.76,370)
for i,net in enumerate(['GND','LED_RUN','LED_FAULT','LED_COMM','LED_AUX']):
    x=30.48+i*48.26
    rr(p,x,264.16,'2.2k','+3V3_INV','LED_AN_'+str(i))
    led=p.inst('Device:LED',ref('D'),'PWR' if i==0 else net, x+22.86,264.16,fp='LED_SMD:LED_0603_1608Metric',fields={'MPN':'TBD','Supplier':'LCSC','Selection_Status':'color/MPN pending'})
    led.connect(2,'LED_AN_'+str(i),2.54);led.connect(1,net,2.54)

# 18. Local TIM1 coupling and HSE on a separate uncluttered page.
p=Page('mcu_control','Inverter - PWM enable fault brake and HSE',18);new_pages.append(p)
p.section('MCU COMMANDS / PHYSICAL SERIES RESISTORS AND PULLDOWNS',20.32,17.78,370)
for i,suffix in enumerate(['UH','UL','VH','VL','WH','WL']):
    x=66.04+(i%3)*124.46;y=50.8+(i//3)*33.02
    rr(p,x,y,'33','MCU_PWM_'+suffix,'PWM_'+suffix+'_IN',90)
rr(p,66.04,129.54,'33','MCU_ENABLE','ENABLE_IN',90)
rr(p,190.5,129.54,'33','MCU_BRAKE','BRAKE_IN',90)
rr(p,312.42,129.54,'10k','FAULT_N','+3V3_INV',notes='Required local pullup; Q8 open collector drives TIM1 BKIN low on fault')
testpoint(p,355.6,99.06,'FAULT_N');testpoint(p,355.6,147.32,'ENABLE_IN')
note(p,'Six PWM input 10k pulldowns, ENABLE 10k, DRIVE_PERMIT 100k and BRAKE 10k remain on the power/gating sheets.\nIndependent hardware trips/latch/AND gates block the bridge without firmware; BKIN provides the local timer response.\nFault clear: healthy AND ENABLE low >=1ms, then explicit re-enable. Brake remains independent; reset defaults it off.',20.32,154.94)
p.section('OPTIONAL HSE CRYSTAL / DEFAULT DNP, INITIAL CLOCK HSI16',20.32,195.58,370)
y=p.inst('Device:Crystal_GND24','Y1','8MHz / CL TBD / DNP',157.48,236.22,fp='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',dnp=True,fields={'MPN':'TBD','Supplier':'LCSC','Selection_Status':'HSE candidate only; exact crystal CL/ESR/drive and startup gain not selected'})
y.connect(1,'HSE_IN',10.16);y.connect(3,'HSE_OUT',10.16);y.connect(2,'GND',5.08);y.connect(4,'GND',5.08)
cap(p,66.04,236.22,'18p / provisional','HSE_IN',dnp=True,notes='DNP; select from actual crystal CL and PCB stray capacitance')
cap(p,266.7,236.22,'18p / provisional','HSE_OUT',dnp=True,notes='DNP; select from actual crystal CL and PCB stray capacitance')
note(p,'HSE network is an option, not a validated crystal BOM. No 32.768kHz oscillator fitted.\nHSI16/PLL permits initial bring-up; CAN clock accuracy over temperature must be checked before CAN use.\nDo not populate Y1/load capacitors until crystal model and oscillator margin are reviewed.',20.32,269.24)

# Write new pages, retaining helper UUIDs; then normalize titles to this revision.
for p in new_pages:
    p.write();d=sx.load((BASE/(p.name+'.kicad_sch')).open(encoding='utf-8'));set_title(d,p.title)
    # MCU power bus sits above the body; keep ref/value clear of it.
    if p.name=='mcu':
        inst=next(s for s in children(d,'symbol') if props(s).get('Reference')=='U30')
        for key,y in [('Reference',43.18),('Value',46.99)]:
            pr=next(t for t in children(inst,'property') if t[1]==key);child(pr,'at')[1:]=[111.76,y,0]
    native_write(p.name+'.kicad_sch',d)
    new_expected.extend((p.name,*r) for r in p.expected if not r[0].startswith('#'))
for name,d in retained.items():native_write(name+'.kicad_sch',d)

titles=[('aux_input','Auxiliary input','eFuse / 12-24 V'),('supply_12v','Driver supply','12 V buck-boost'),
 ('supply_logic','Logic and sensors','5 V / 3.3 V / supervisor'),('bus_brake','Bus and brake','12-60 V / external resistor'),
 ('bridge_u','U half bridge','TO-263 / driver / shunt'),('bridge_v','V half bridge','TO-263 / driver / shunt'),
 ('bridge_w','W half bridge','TO-263 / driver / shunt'),('current_sense','Current sensing','3 x INA241 / 1.65 V bias'),
 ('voltage_sense','Voltage and NTC','Bus / 3 phases / NTC'),('comparators','Analog protection','Current / bus OV / driver UV'),
 ('fault_logic','Hardware latch','Healthy chain / reset / fault'),('control_interface','Hardware PWM gates','Six independent AND gates'),
 ('mcu','Local STM32G431','LQFP64 / VDD / pin plan'),('mcu_analog','MCU analog inputs','8 RC filters / VDDA / VREF'),
 ('sensors','Encoders and SPI','2 x ABZ / 2 x SPI'),('debug_comms','Debug and communication','SWD / TTL / optional CAN / LEDs'),
 ('mcu_control','Local command coupling','PWM / enable / fault / HSE option')]
root=Page('inverter','Inverter - integrated STM32G431 review draft',1)
root.section('INTEGRATED INVERTER / STM32G431 / REV B REVIEW',20.32,17.78,370)
root.text('One PCB / one MCU / one three-phase bridge / one external-resistor brake.\n12-60 V bus, DC input <=10 A; phase 10 Arms design target; bridge PWM 20 kHz; separate 12-24 V auxiliary.',20.32,27.94,1.2)
for i,(name,title,brief) in enumerate(titles):
    x=20.32+(i%4)*96.52;y=53.34+(i//4)*38.1
    root.items.append(f'(sheet (at {n(x)} {n(y)}) (size 86.36 20.32) (stroke (width .254) (type default)) (fill (color 0 0 0 0)) (uuid {q(uid("sheet/"+name))}) (property "Sheetname" {q(title)} (at {n(x)} {n(y-2.54)} 0) {effects(.95,"left")}) (property "Sheetfile" {q(name+".kicad_sch")} (at {n(x)} {n(y+22.86)} 0) {effects(.85,"left")}) (instances (project "inverter" (path {q("/"+ROOT)} (page {q(str(i+2))})))))')
    root.text(brief,x+2.54,y+6.35,.9)
note(root,'Native Rev B drawing is for circuit review; PCB placement/routing and rated operation have not been validated.\nIndependent comparators, latch and PWM gates retained; MCU added locally. No 24-pin controller cable or external brake-command cable.\nNo main-bus precharge/bleeder, USB, Hall or PFC/LLC power circuit. PFC power-board drawing is paused.\n3.3V single-ended encoder/SPI interfaces; exact external modules, connectors, passives, thermal and protection dynamics still need review.',20.32,250.19)
root.write();d=sx.load((BASE/'inverter.kicad_sch').open(encoding='utf-8'));set_title(d,root.title);native_write('inverter.kicad_sch',d)

# Preserve old assertions except deleted cable pins; add independent new pin assertions.
expected=list(csv.DictReader(io.StringIO(old('review/expected_pin_nets.csv'))))
with (BASE/'review/expected_pin_nets.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['Sheet','Reference','Pin','Net'])
    for r in expected:
        if r['Reference'] in ['J1','J6']:continue
        w.writerow([r['Sheet'],r['Reference'],r['Pin'],renames.get(r['Net'],r['Net'])])
    w.writerows(new_expected)
manifest=json.loads(old('review/design_manifest.json'))
manifest['revision']='B-integrated-draft';manifest['date']='2026-11-06'
manifest['pages']=[dict(name='inverter',title=root.title,page=1)]+[dict(name=name,title=title,page=i+2) for i,(name,title,brief) in enumerate(titles)]
manifest['ports']={};manifest['external_ports']=port_records
manifest['checks_scope']='Integrated schematic review draft, not PCB/manufacturing release'
manifest['source_archive']=str(archive.relative_to(BASE.parent))
(BASE/'review/design_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Rev B native schematic written: 18 sheets. Export a fresh KiCad netlist, then regenerate BOM and run independent checks.')

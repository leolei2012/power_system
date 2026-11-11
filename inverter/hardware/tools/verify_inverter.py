"""Independent checks of the actual KiCad XML netlist, not the authoring objects."""
from pathlib import Path
from collections import defaultdict
import csv
import json
import math
import xml.etree.ElementTree as ET

B=Path(__file__).resolve().parents[1]
tree=ET.parse(B/'review/inverter.net.xml').getroot()
components={c.attrib['ref']:c for c in tree.findall('./components/comp')}
nets={};members={}
for net in tree.findall('./nets/net'):
    # Same-sheet internal labels are scoped by KiCad as /Sheet/Name.
    # Require unique base names so this normalization cannot mask split nets.
    name=net.attrib['name'].rsplit('/',1)[-1]; nodes={(x.attrib['ref'],x.attrib['pin']) for x in net.findall('node')}
    assert name not in members, ('duplicate scoped net basename',net.attrib['name'])
    members[name]=nodes
    for node in nodes:
        assert node not in nets
        nets[node]=name
def at(ref,pin):return nets.get((ref,str(pin)))
def val(ref):return components[ref].findtext('value')
def end(ref,pin,net):assert at(ref,pin)==net, f'{ref}.{pin}: {at(ref,pin)} != {net}'
def nc(ref,pin):
    net=at(ref,pin)
    assert net is None or (net.startswith('unconnected-') and len(members[net])==1), f'{ref}.{pin} is not NC: {net}'
def links(a,b,value,prefix='R'):
    return [ref for ref in components if ref.startswith(prefix) and val(ref)==value and {at(ref,1),at(ref,2)}=={a,b}]
def link(a,b,value,prefix='R'):
    found=links(a,b,value,prefix);assert len(found)==1, (a,b,value,found)
    return found[0]
checks=[]
manifest=json.loads((B/'review/design_manifest.json').read_text(encoding='utf-8'))
assert len(tree.findall('./design/sheet'))==18
assert len(components)==manifest['component_count']==313
bom=list(csv.DictReader((B/'review/bom.csv').open(encoding='utf-8-sig')))
bomref={r['Reference']:r for r in bom};assert set(bomref)==set(components)
for row in csv.DictReader((B/'review/expected_pin_nets.csv').open(encoding='utf-8-sig')):end(row['Reference'],row['Pin'],row['Net'])
checks.append('18 native KiCad sheets / 313 unique component records; all explicit author pin-net assertions and BOM references match KiCad export.')

# New local MCU contract, written explicitly from the physical LQFP64 pinout.
# This does not import the drawing generator or derive expected nets from its CSV.
assert 'J1' not in components and 'J6' not in components
end('J7',1,'+5V_SENSOR');end('J7',2,'GND');assert bomref['J7']['DNP']=='yes'
end('J5',1,'VBUS');end('J5',2,'BR_SW')
pinmap={1:'+3V3_INV',5:'HSE_IN',6:'HSE_OUT',7:'LOGIC_POWER_OK',8:'ADC_I_U',9:'ADC_I_V',10:'ADC_I_W',11:'ADC_V_DC',
12:'ENC_A_A',13:'ENC_A_B',14:'ENC_A_Z',15:'GND',16:'+3V3_INV',17:'ENC_B_Z',18:'ADC_V_U',19:'SPI_A_SCK',20:'SPI_A_MISO',21:'SPI_A_MOSI',
22:'MCU_ENABLE',23:'LED_RUN',24:'ADC_V_V',25:'ADC_V_W',26:'ADC_TEMP_NTC',27:'GND',28:'VREF_MCU',29:'+3V3_A_MCU',
30:'UART_TX',31:'GND',32:'+3V3_INV',33:'UART_RX',34:'FAULT_N',35:'MCU_PWM_UL',36:'MCU_PWM_VL',37:'MCU_PWM_WL',38:'MCU_BRAKE',
40:'LED_FAULT',41:'SPI_B_CS',42:'MCU_PWM_UH',43:'MCU_PWM_VH',44:'MCU_PWM_WH',45:'CAN_RX',46:'CAN_TX',47:'GND',48:'+3V3_INV',
49:'SWDIO',50:'SWCLK',51:'SPI_A_CS',52:'SPI_B_SCK',53:'SPI_B_MISO',54:'SPI_B_MOSI',55:'LED_COMM',58:'LED_AUX',
59:'ENC_B_A',60:'ENC_B_B',61:'BOOT0',63:'GND',64:'+3V3_INV'}
nc_pins={2,3,4,39,56,57,62}
assert set(pinmap)|nc_pins==set(range(1,65))
assert components['U30'].findtext('value')=='STM32G431RBT6'
assert components['U30'].findtext('footprint')=='Package_QFP:LQFP-64_10x10mm_P0.5mm'
for pin,net in pinmap.items():end('U30',pin,net)
for pin in nc_pins:nc('U30',pin)
plan=list(csv.DictReader((B/'STM32G431RBT6_pin_plan.csv').open(encoding='utf-8-sig')))
for row in plan:
    pin=int(row['Pin']);assert row['Net']==pinmap.get(pin,'NC')
for suffix in ['UH','UL','VH','VL','WH','WL']:link('MCU_PWM_'+suffix,'PWM_'+suffix+'_IN','33')
link('MCU_ENABLE','ENABLE_IN','33');link('MCU_BRAKE','BRAKE_IN','33');link('FAULT_N','+3V3_INV','10k')
link('BOOT0','GND','10k');link('LOGIC_POWER_OK','GND','100n','C')
assert any(ref.startswith('SW') and {at(ref,1),at(ref,2)}=={'LOGIC_POWER_OK','GND'} for ref in components)
assert not any(ref=='U30' for ref,pin in members['VBIAS_1V65'])
link('+3V3_INV','+3V3_A_MCU','0');link('+3V3_A_MCU','VREF_MCU','0')
for net in ['+3V3_A_MCU','VREF_MCU']:
    link(net,'GND','100n','C');link(net,'GND','1u','C')
assert len(links('+3V3_INV','GND','100n','C'))>=5
for sig in ['I_U','I_V','I_W','V_DC','V_U','V_V','V_W','TEMP_NTC']:
    link(sig+'_PORT' if sig!='TEMP_NTC' else sig,'ADC_'+sig,'100')
    link('ADC_'+sig,'GND','1n','C')
for ref in ['U31','Y1']:assert bomref[ref]['DNP']=='yes'
for ch,jref in [('A','J9'),('B','J10')]:
    for pin,net in {1:f'ENC_{ch}_VCC',2:'GND',3:f'ENC_{ch}_A_PORT',4:f'ENC_{ch}_B_PORT',5:f'ENC_{ch}_Z_PORT'}.items():end(jref,pin,net)
    for sig in 'ABZ':
        link(f'ENC_{ch}_{sig}_PORT',f'ENC_{ch}_{sig}','100');link(f'ENC_{ch}_{sig}','+3V3_INV','10k')
    r=link('+5V_SENSOR',f'ENC_{ch}_VCC','0');assert bomref[r]['DNP']=='yes'
for ch,jref in [('A','J11'),('B','J12')]:
    for pin,net in {1:f'SPI_{ch}_VCC',2:'GND',3:f'SPI_{ch}_SCK_PORT',4:f'SPI_{ch}_MOSI_PORT',5:f'SPI_{ch}_MISO_PORT',6:f'SPI_{ch}_CS_PORT'}.items():end(jref,pin,net)
    for sig in ['SCK','MOSI','MISO','CS']:link(f'SPI_{ch}_{sig}',f'SPI_{ch}_{sig}_PORT','33')
    link(f'SPI_{ch}_CS','+3V3_INV','10k')
    r=link('+5V_SENSOR',f'SPI_{ch}_VCC','0');assert bomref[r]['DNP']=='yes'
for pin,net in {1:'+3V3_INV',2:'SWDIO_PORT',3:'SWCLK_PORT',4:'GND',5:'LOGIC_POWER_OK'}.items():end('J13',pin,net)
for pin,net in {1:'UART_TX_PORT',2:'UART_RX_PORT',3:'GND'}.items():end('J14',pin,net)
for pin,net in {1:'CAN_H',2:'CAN_L',3:'GND'}.items():end('J15',pin,net)
checks.append('All 64 G431 physical pins independently checked: 7 NC, 6 TIM1 commands, active-low BKIN, independent TIM8 brake, ENABLE, 8 ADC inputs, two ABZ, SPI1/SPI3, USART3, SWD and optional classic CAN. CSV matches actual netlist.')
checks.append('External controller J1 and brake-command J6 removed; local fault pullup, reset supervisor/button/SWD, BOOT pulldown, per-pin power connections, VDDA/VREF and eight local ADC RC filters checked. 1.65 V bias is not tied to MCU VREF.')
checks.append('Two ABZ and two independent SPI connectors plus SWD/TTL/CAN checked. Sensor power links, optional CAN PHY and HSE default DNP. External IO is 3.3 V single-ended; 5 V sensor power does not imply 5 V logic compatibility.')
for net in ['I_U','I_V','I_W','V_DC','V_U','V_V','V_W']:link(net,net+'_PORT','47')
checks.append('All seven amplified analog outputs retain local 47-ohm isolators before MCU RC; current/bus trip sensing stays on the local side of each resistor.')

# Actual package pins and shunt return paths.
def mos(ref,gate,drain,source):
    assert val(ref)=='BSC110N15NS5'
    assert components[ref].findtext('footprint')=='Inverter_Compact:BSC110N15NS5_TDSON8_8PhysicalPins'
    end(ref,4,gate)
    for pin in [1,2,3]:end(ref,pin,source)
    for pin in [5,6,7,8]:end(ref,pin,drain)

for ph,driver,high,low,rs,amp in [('U','U7','Q1','Q2','RS1','U10'),('V','U8','Q3','Q4','RS2','U11'),('W','U9','Q5','Q6','RS3','U12')]:
    source=ph+'_SOURCE';phase=ph+'_PHASE'
    mos(high,ph+'_GATE_H','VBUS',phase)
    mos(low,ph+'_GATE_L',phase,source)
    end(rs,1,source);end(rs,2,'GND');assert source!='GND' and source!=phase
    for pin,net in {1:ph+'_HIN',2:ph+'_LIN',3:source,4:ph+'_LO',5:'+12V_DRV',6:phase,7:ph+'_HO',8:ph+'_BOOT'}.items():end(driver,pin,net)
    link(ph+'_HO',ph+'_GATE_H','15');link(ph+'_LO',ph+'_GATE_L','15')
    link(ph+'_GATE_H',phase,'10k');link(ph+'_GATE_L',source,'10k')
    link(ph+'_HIN',source,'10k');link(ph+'_LIN',source,'10k')
    link(ph+'_BOOT',phase,'2.2u','C');link(ph+'_BOOT',phase,'100n','C')
    link('+12V_DRV',source,'4.7u','C');link('+12V_DRV',source,'100n','C')
    for pin,net in {1:'GND',2:'GND',3:'VBIAS_1V65',4:'GND',5:'I_'+ph,6:'+3V3_INV',7:'VBIAS_1V65',8:source}.items():end(amp,pin,net)
    # No shared power-ground pin accidentally landed on a source node.
    allowed_ref={driver,low,rs,amp}
    for ref,pin in members[source]:
        assert ref in allowed_ref or ref.startswith(('C','R','TP')), (ph,ref,pin)
mos('Q7','BR_GATE','BR_SW','GND')
for pin,net in {1:'+12V_DRV',2:'GND',3:'BRAKE_IN',4:'GND',5:'BR_DRV'}.items():end('U29',pin,net)
link('BRAKE_IN','GND','10k');link('BR_DRV','BR_GATE','15');link('BR_GATE','GND','10k')
checks.append('All seven compact BSC110N15NS5 S1/2/3,G4,D5/6/7/8 physical pins and project TDSON8 footprints checked. Every driver COM, LO reference, bootstrap and Kelvin input is on its own correct source/phase node; no direct shunt bypass.')
checks.append('Brake driver is a separate UCC27517 stage with IN- low and no bridge ENABLE/FAULT gating; BR+/BR_SW topology checked.')

# Auxiliary application circuits, including subtle ground/sense pins.
for pin,net in {1:'AUX_FUSED',2:'AUX_FUSED',3:'AUX_UV_DIV',5:'AUX_OV_DIV',6:'AUX_MODE',7:'AUX_SHDN_N',8:'EFUSE_RTN',9:'GND',11:'AUX_ILIM',12:'AUX_DVDT',14:'AUX_FLT_N',15:'AUX_PROTECTED',16:'AUX_PROTECTED',17:'EFUSE_RTN'}.items():end('U1',pin,net)
assert at('U1',8)!=at('U1',9)
assert bomref['R8']['DNP']=='yes','External high-voltage SHDN pullup must remain unpopulated; internal 2.7V bias used'
for pin in [4,10,13]:nc('U1',pin)
for net,value in [('AUX_MODE','402k'),('AUX_ILIM','7.87k')]:link(net,'EFUSE_RTN',value)
link('AUX_DVDT','EFUSE_RTN','22n','C')
for pin,net in {1:'GND',2:'BB_L1',3:'BB_BST1',4:'AUX_PROTECTED',5:'AUX_PROTECTED',6:'AUX_PROTECTED',7:'GND',8:'GND',9:'GND',10:'BB_PG_DLY',11:'BB_VREG',12:'BB_VREG',13:'GND',14:'BB_VREG',15:'DRV_PG_NOM',16:'+12V_DRV',17:'+12V_DRV',18:'GND',19:'BB_BST2',20:'BB_L2',21:'GND'}.items():end('U2',pin,net)
link('BB_BST1','BB_L1','100n','C');link('BB_BST2','BB_L2','100n','C')
assert {at('L1',1),at('L1',2)}=={'BB_L1','BB_L2'}
link('+5V_INV','DRV_PG_NOM','10k');link('DRV_PG_NOM','DRV_PG_LOGIC','10k');link('DRV_PG_LOGIC','GND','20k')
for pin,net in {1:'+5V_INV',2:'AUX_PROTECTED',3:'AUX_PROTECTED',4:'GND',5:'BUCK_SW',6:'BUCK_BST'}.items():end('U3',pin,net)
assert {at('L2',1),at('L2',2)}=={'BUCK_SW','+5V_INV'}
link('BUCK_BST','BUCK_SW','100n','C')
for pin,net in {1:'+5V_INV',2:'GND',3:'+5V_INV',5:'+3V3_INV'}.items():end('U4',pin,net)
nc('U4',4)
for pin,net in {1:'+5V_INV',2:'GND',3:'+5V_INV',4:'SENSOR_PWR_FLT_N',5:'SENSOR_ILIM',6:'+5V_SENSOR'}.items():end('U5',pin,net)
link('SENSOR_ILIM','GND','49.9k')
for pin,net in {1:'LOGIC_POWER_OK',2:'GND',3:'+3V3_INV',5:'+3V3_INV',6:'+3V3_INV'}.items():end('U6',pin,net)
nc('U6',4)
checks.append('eFuse RTN/EP isolated from GND and MODE=402k; TPS55165 VREG/VREG_Q/VOS_FB, switch nodes/boots, 5 V PG pull-up/divider, AP63205 fixed-output feedback, LDO and repurposed optional 5 V sensor switch checked.')

# Comparator polarity and latch truth table read directly from the pin-net maps.
healthy=[]
for idx,ph in enumerate('UVW',18):
    ref='U'+str(idx)
    for pin,net in {1:f'OC_{ph}_HIGH_OK',2:'I_'+ph,3:'OC_HIGH_REF',5:'I_'+ph,6:'OC_LOW_REF',7:f'OC_{ph}_LOW_OK',4:'GND',8:'+3V3_INV'}.items():end(ref,pin,net)
    healthy.extend([f'OC_{ph}_HIGH_OK',f'OC_{ph}_LOW_OK'])
for pin,net in {1:'BUS_OV_OK',2:'V_DC',3:'OV_REF_1V30',5:'DRV_UV_DIV',6:'OV_REF_1V30',7:'DRV_UV_OK',4:'GND',8:'+3V3_INV'}.items():end('U21',pin,net)
healthy += ['BUS_OV_OK','DRV_UV_OK','LOGIC_POWER_OK','DRV_PG_LOGIC','AUX_FLT_N']
for pin,net in {1:'+3V3_INV',2:'GND',3:'RESET_CLK',4:'HEALTH_ALL',5:'FAULT_LATCH',6:'NO_LATCH',7:'GND',14:'+3V3_INV',10:'+3V3_INV',11:'GND',12:'GND',13:'+3V3_INV'}.items():end('U28',pin,net)
nc('U28',8);nc('U28',9)
link('RESET_REQUEST','RESET_CLK','10k');link('RESET_CLK','GND','10n','C')
link('FAULT_ACTIVE','FAULT_BASE','10k');link('FAULT_BASE','GND','100k')
end('Q8',1,'FAULT_BASE');end('Q8',2,'GND');end('Q8',3,'FAULT_N')
pin_units=[(1,2,3),(4,5,6),(9,10,8),(12,13,11)]
gates=[]
for ref,kind in [(f'U{i}','AND') for i in range(22,27)]+[('U27','NAND')]:
    end(ref,7,'GND');end(ref,14,'+3V3_INV')
    for a,b,y in pin_units:
        if at(ref,y) is None or at(ref,y).startswith('unconnected-'):continue
        gates.append((at(ref,a),at(ref,b),at(ref,y),kind))
def evaluate(inputs):
    v={'GND':False,'+3V3_INV':True}|inputs
    for _ in range(len(gates)+1):
        progress=False
        for a,b,y,kind in gates:
            if y not in v and a in v and b in v:
                v[y]=(v[a] and v[b]) if kind=='AND' else not(v[a] and v[b]);progress=True
        if not progress:break
    return v
truth_cases=0
for mask in range(1<<len(healthy)):
    inputs={net:bool(mask&(1<<i)) for i,net in enumerate(healthy)}
    for en in [False,True]:
        for latched in [False,True]:
            v=evaluate(inputs|{'ENABLE_IN':en,'NO_LATCH':not latched}|{f'PWM_{s}_IN':True for s in ['UH','UL','VH','VL','WH','WL']})
            h=all(inputs.values())
            assert v['HEALTH_ALL']==h
            assert v['RESET_REQUEST']==(h and not en)
            assert v['FAULT_ACTIVE']==(not(h and not latched))
            permit=h and en and not latched
            assert v['DRIVE_PERMIT']==permit
            for p in 'UVW':assert v[p+'_HIN']==permit and v[p+'_LIN']==permit
            truth_cases+=1
for permit_enable in [False,True]:
    for mask in range(64):
        raw={f'PWM_{p}_IN':bool(mask&(1<<i)) for i,p in enumerate(['UH','UL','VH','VL','WH','WL'])}
        v=evaluate({s:True for s in healthy}|{'ENABLE_IN':permit_enable,'NO_LATCH':True}|raw)
        for i,p in enumerate(['UH','UL','VH','VL','WH','WL']):assert v[p[0]+('_HIN' if p[1]=='H' else '_LIN')]==(permit_enable and bool(mask&(1<<i)))
checks.append(f'Comparator input polarity checked. {truth_cases} actual-netlist logic cases passed: any active fault/power loss blocks every driver input; latched fault cannot restart with ENABLE high; reset only requested while all healthy and disabled.')
checks.append('All 64 raw PWM patterns tested with permit on/off. DFF /R fixed high, /S=HEALTH_ALL, D=0, delayed clock verified; illegal simultaneous asynchronous assertion structurally absent within the powered logic domain.')

# Divider values and buffer feedback are checked against the network, not comments.
for sig,raw,ref in [('V_DC','VBUS','U14'),('V_U','U_PHASE','U15'),('V_V','V_PHASE','U16'),('V_W','W_PHASE','U17')]:
    link(raw,sig+'_DIV1','240k');link(sig+'_DIV1',sig+'_DIV2','240k');link(sig+'_DIV2',sig+'_DIV','10k');link(sig+'_DIV','GND','10k')
    end(ref,1,sig+'_DIV');end(ref,3,sig);end(ref,4,sig);end(ref,2,'GND');end(ref,5,'+3V3_INV')
link('+3V3_INV','VBIAS_DIV','10k');link('VBIAS_DIV','GND','10k')
end('U13',1,'VBIAS_DIV');end('U13',3,'VBIAS_1V65');end('U13',4,'VBIAS_1V65')
for a,b,value in [('+3V3_INV','OC_LO_MID','39k'),('OC_LO_MID','OC_LOW_REF','1.8k'),('OC_LOW_REF','GND','10k'),('+3V3_INV','OC_HIGH_REF','10k'),('OC_HIGH_REF','OC_HI_MID','1.8k'),('OC_HI_MID','GND','39k'),('+3V3_INV','OV_REF_1V30','20k'),('OV_REF_1V30','GND','13k'),('+12V_DRV','DRV_UV_DIV','76.1k'),('DRV_UV_DIV','GND','10k')]:link(a,b,value)
for row in bom:
    if row['Reference'].startswith(('R','C')) and not row['Reference'].startswith('RS') and row['MPN'] not in ['EKYB101ELL221MK25S']:
        assert row['Manufacturer']=='YAGEO',row['Reference']
bulk=[r for r in bom if r['MPN']=='EKYB101ELL221MK25S'];bypass=[r for r in bom if r['MPN']=='CS1210KKX7R0BB225']
assert len(bulk)==2 and len(bypass)==2
assert bomref['D2']['DNP']=='yes'
for pin in [1,3]:end('D1',pin,'DC_FUSED')
end('D1',2,'VBUS')
assert not [r for r in bom if r['Reference'].startswith('K') or 'precharge' in r['Value'].lower()]
checks.append('Four 50:1 dividers/followers, 1.65 V bias, nominal +/-20.008 A / 65 V / 11.193 V divider values, 2x220uF and 2x2.2uF checked; ordinary small R/C are YAGEO. No precharge relay or dedicated bus bleeder added.')
values={'oc_low_v':3.3*10000/50800,'oc_high_v':3.3*40800/50800,'oc_abs_a':(3.3*40800/50800-1.65)/.05,
        'bus_ov_nominal_v':3.3*13000/33000*50,'driver_uv_nominal_v':3.3*13000/33000*8.61,
        'aux_uv_rising_nominal_v':1.19*(1+78700/10000),'aux_ov_nominal_v':1.19*(1+221000/10000),
        'aux_ilim_approx_a':11800/7870,'aux_ramp_24v_nominal_ms':8000*24*22e-9*1000,
        'sensor_ilim_min_a_nominal_r':25230/(49.9**1.016)/1000,'sensor_ilim_max_a_nominal_r':22980/(49.9**.94)/1000,
        'bus_stored_energy_at_60v_j':.5*440e-6*60**2,'bus_stored_energy_at_65v_j':.5*440e-6*65**2,
        'reset_rc_us':10000*10e-9*1e6,'pg_logic_high_nominal_v':5*20000/(10000+10000+20000)}
report={'result':'PASS','revision':'B-integrated-draft','sheets':18,'components':313,'logic_cases':truth_cases,'pwm_pattern_cases':128,'checks':checks,'nominal_calculations':values,
        'limitations':['Static connectivity and powered-domain Boolean logic only; no SPICE switching, gate waveform, timing/SOA/thermal or hardware test.',
        'RC reset edge requires analog recovery/pulse and noise validation; brief faults during reset may remain safely latched until another deliberate disable cycle.',
        'Main input diode/TVS/fuse, exact inductors/passives, connectors, gate-drive corner margin and isolation/source domain remain release blockers.',
        'G431 ADC sampling windows, 3.3 V LDO current/thermal budget, HSE/CAN clock accuracy, 3.3 V external IO protection and power-off injection remain design review items.']}
(B/'review/connectivity_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(B/'review/connectivity_check.txt').write_text('PASS\n\n'+'\n'.join('- '+x for x in checks)+'\n\nNOMINAL CALCULATIONS\n'+json.dumps(values,indent=2)+'\n\nLIMITATIONS\n'+'\n'.join(report['limitations'])+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['result','sheets','components','logic_cases','pwm_pattern_cases']}))

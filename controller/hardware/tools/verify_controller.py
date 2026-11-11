"""Check KiCad's exported netlist against the independent MCU/interface contract."""
from pathlib import Path
from collections import Counter
import csv
import json
import xml.etree.ElementTree as ET

BASE=Path(__file__).resolve().parents[1]
root=ET.parse(BASE/'review/controller.net.xml').getroot()
components={c.attrib['ref']:c for c in root.findall('./components/comp')}
nets={}
members={}
for net in root.findall('./nets/net'):
    name=net.attrib['name']
    nodes={(v.attrib['ref'],v.attrib['pin']) for v in net.findall('node')}
    members[name]=nodes
    for v in nodes:
        assert v not in nets, f'Multiple nets for {v}'
        nets[v]=name
def at(ref,pin): return nets.get((ref,str(pin)))
def val(ref): return components[ref].findtext('value')
def is_nc(ref,pin):
    name=at(ref,pin)
    return name is None or (name.startswith('unconnected-') and len(members[name])==1)
def endpoint(ref,pin,expected):
    actual=at(ref,pin)
    assert actual==expected, f'{ref}.{pin}: expected {expected}, got {actual}'
def links(a,b,value):
    return [ref for ref in components if ref.startswith('R') and val(ref)==value and {at(ref,1),at(ref,2)}=={a,b}]
def one_link(a,b,value):
    rr=links(a,b,value)
    assert len(rr)==1, f'{a} -- {value} -- {b}: {rr}'
    return rr[0]

plan=list(csv.DictReader((BASE/'LKS32MC451VCT8_pin_plan.csv').open(encoding='utf-8-sig')))
checks=[]
for row in plan:
    if row['State']=='nc': assert is_nc('U1',row['Pin'])
    else: endpoint('U1',row['Pin'],row['Net'])
checks.append('All 100 physical MCU pins match the independent pin-plan CSV (96 connected, 4 NC).')
gpio=[at('U1',r['Pin']) for r in plan if r['State'] in ['assigned','reserved']]
assert len(set(gpio))==84
checks.append('All 84 GPIO / reserved pad nets remain separate; no accidental ground or rail short.')
assert at('U2',1)==at('U2',2)=='+3V3_MCU'
for pin in [3,5,7]: endpoint('U2',pin,'GND')
for pin in [4,6]: endpoint('U2',pin,'+5V_CTRL')
for pin,net in [(1,'MCU_NRST'),(2,'GND'),(3,'RESET_BUTTON_N'),(5,'+3V3_MCU'),(6,'+3V3_MCU')]: endpoint('U3',pin,net)
assert is_nc('U3',4)
one_link('MCU_NRST','+3V3_MCU','10k')
one_link('RESET_BUTTON_N','+3V3_MCU','10k')
assert {at('SW1',1),at('SW1',2)}=={'RESET_BUTTON_N','GND'}
checks.append('LDO IN/EN, OUT/SNS, all GND/EP pins and supervisor/reset wiring match the application circuit.')

contracts={'INV1':'J2','INV2':'J4','PFC':'J6'}
grounds=[3,6,9,13,17,21]
analog_count=0
commands=[]
routes=[]
for row in plan:
    iface=row['Interface']
    for group,j in contracts.items():
        if not iface.startswith('J_'+group+'.'): continue
        pin=iface.split('.')[1]
        port=row['Net']+'_PORT'
        endpoint(j,pin,port)
        value='100' if row['Direction']=='ANALOG_IN' or row['Net'].endswith('FAULT_N') else '33'
        one_link(row['Net'],port,value)
        routes.append((j,pin,row['Pin'],row['Net']))
        if row['Direction']=='ANALOG_IN':
            analog_count+=1
            cc=[ref for ref in components if ref.startswith('C') and val(ref)=='1n' and {at(ref,1),at(ref,2)}=={row['Net'],'GND'}]
            assert len(cc)==1, f'Missing or duplicate ADC capacitor for {row["Net"]}'
        elif row['Direction']=='OUT':
            one_link(port,'GND','10k'); commands.append(port)
        elif row['Net'].endswith('FAULT_N'):
            one_link(port,'+3V3_MCU','4.7k')
            assert not [ref for ref in components if ref.startswith('C') and (at(ref,1) in [port,row['Net']] or at(ref,2) in [port,row['Net']])]
for group,j in contracts.items():
    for pin in grounds: endpoint(j,pin,'GND')
    for pin in range(1,25): assert at(j,pin) not in ['+3V3_MCU','+5V_CTRL']
for j in ['J2','J4']:
    for pin in [12,24]: assert is_nc(j,pin)
assert analog_count==25 and len(routes)==50
checks.append('50 signal paths across the three 24-pin ports match the pin-plan CSV through individual series resistors; all 25 ADC RC channels checked.')
checks.append('All 18 port ground contacts are GND; inverter contacts 12/24 stay NC; no power rail enters any 24-pin port.')
for k,j in [(1,'J3'),(2,'J5')]:
    endpoint(j,1,f'BRAKE_{k}_PORT'); endpoint(j,2,'GND')
    one_link(f'BRAKE_{k}',f'BRAKE_{k}_PORT','33'); one_link(f'BRAKE_{k}_PORT','GND','10k')
    commands.append(f'BRAKE_{k}_PORT')
assert len(commands)==24
checks.append('24 PWM / ENABLE / PFC PRECHARGE / BRAKE command lines each have a 10k external default-low pull-down; all three FAULT inputs have pull-ups and no delay capacitor.')
for net in ['DEBUG_nTRST_RESERVED','DEBUG_TDI_RESERVED','DEBUG_TDO_RESERVED','REF_TEST_RESERVED','LDO12_TEST_RESERVED']:
    assert len(members[net])==2
    assert sum(ref.startswith('TP') for ref,pin in members[net])==1
checks.append('Five reserved MCU debug/analog pins connect only to dedicated high-impedance test pads.')
for pin,net in [(1,'+3V3_MCU'),(2,'SWDIO_PORT'),(3,'SWCLK_PORT'),(4,'GND'),(5,'MCU_NRST')]: endpoint('J11',pin,net)
for net in ['SWDIO','SWCLK']: one_link(net,net+'_PORT','33')
for pin,net in [(1,'UART_TX_PORT'),(2,'UART_RX_PORT'),(3,'GND')]: endpoint('J12',pin,net)
checks.append('SWD VTREF/IO/CLK/GND/NRST and 3.3 V TTL TX/RX/GND contact order checked.')
for k,j in [(1,'J7'),(2,'J8')]:
    for pin,sig in enumerate('ABZ',1):
        endpoint(j,pin,f'ENC{k}_{sig}_PORT'); one_link(f'ENC{k}_{sig}_PORT',f'ENC{k}_{sig}','100')
        one_link(f'ENC{k}_{sig}','GND','100k')
    endpoint(j,4,'GND'); endpoint(j,5,f'ENC{k}_VOPT')
for k,j in [('A','J9'),('B','J10')]:
    for pin,sig in enumerate(['SCK','MOSI','MISO','CS_N'],1):
        endpoint(j,pin,f'SPI_{k}_{sig}_PORT'); one_link(f'SPI_{k}_{sig}_PORT',f'SPI_{k}_{sig}','33')
    one_link(f'SPI_{k}_CS_N_PORT','+3V3_MCU','10k')
    endpoint(j,5,'GND'); endpoint(j,6,f'SPI_{k}_VOPT')
checks.append('Both ABZ and both independent SPI connector paths match the MCU signals; both CS_N pull-ups checked.')
bom=list(csv.DictReader((BASE/'review/bom.csv').open(encoding='utf-8-sig')))
bom_by_ref={r['Reference']:r for r in bom}
for net in ['ENC1_VOPT','ENC2_VOPT','SPI_A_VOPT','SPI_B_VOPT']:
    r=one_link('+3V3_MCU',net,'0'); assert bom_by_ref[r]['DNP']=='yes'
for ref in ['U4','J13']: assert bom_by_ref[ref]['DNP']=='yes'
for net in ['CAN_TX','CAN_RX']:
    r=one_link(net,net+'_PHY','0'); assert bom_by_ref[r]['DNP']=='yes'
for pin in [5,8]: assert is_nc('U4',pin)
for pin,net in [(1,'CAN_TX_PHY'),(2,'GND'),(3,'+3V3_MCU'),(4,'CAN_RX_PHY'),(6,'CAN_L'),(7,'CAN_H')]: endpoint('U4',pin,net)
assert is_nc('J13',4)
checks.append('All four sensor power links default DNP; optional CAN transceiver block and its isolation links default DNP; CAN NC pins checked.')
assert set(bom_by_ref)==set(components), 'BOM / KiCad component mismatch'
assert len(bom_by_ref)==196
for r in bom:
    if r['Reference'].startswith(('R','C')): assert r['Manufacturer']=='YAGEO'
checks.append('All 196 BOM designators match KiCad components; all ordinary R/C entries specify YAGEO.')
rows=list(csv.DictReader((BASE/'review/expected_pin_nets.csv').open(encoding='utf-8-sig')))
rows=[r for r in rows if not r['Reference'].startswith('#')]
for row in rows: endpoint(row['Reference'],row['Pin'],row['Expected_Net'])
checks.append(f'{len(rows)} additional explicit component pin-net assertions checked against KiCad export.')
report={'result':'PASS','tool':'KiCad 10 exported XML netlist + independent Python assertions',
        'sheets':9,'components':196,'dnp_components':sum(r['DNP']=='yes' for r in bom),
        'mcu_pins':100,'adc_channels':analog_count,'port_signal_routes':len(routes),'command_default_low':len(commands),'checks':checks,
        'limits':['Static connectivity only; not an electrical/thermal/timing simulation.','DNP parts are included in the ERC/netlist; assembly power-link state checked separately.','Encoder voltage, crystal loading, connectors and external protection remain explicit draft items.']}
(BASE/'review/connectivity_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(BASE/'review/connectivity_check.txt').write_text('PASS\n\n'+'\n'.join(f'- {v}' for v in checks)+'\n\nLimits:\n'+'\n'.join(report['limits'])+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['checks','limits']},ensure_ascii=False))

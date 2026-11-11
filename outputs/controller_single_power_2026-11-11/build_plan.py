"""Single-power-port planning revision; never modifies native KiCad or library files."""
from pathlib import Path
import copy
import csv
import hashlib
import io
import json

ROOT=Path(__file__).resolve().parents[2]
DOCS=ROOT/'docs'; OUT=Path(__file__).resolve().parent
HIST=DOCS/'history/dual_power_ports_2026-11-11'
HIST.mkdir(parents=True,exist_ok=True)
snapshot_files=['README.md','docs/controller_daughterboard.md','docs/terminal_interface_plan.json',
 'docs/controller_dual_pwm_pin_plan.json','docs/controller_dual_pwm_pin_plan.csv','docs/controller_dual_pwm_ports.csv',
 'docs/controller_LQFP100_all_pins.csv','docs/controller_connector_inventory.json','docs/controller_connector_inventory.csv',
 'docs/controller_ADC_mode_examples.csv','docs/controller_60mm_fit_study.json']
manifest=[]
for rel in snapshot_files:
    src=ROOT/rel; dest=HIST/src.name
    if not dest.exists():dest.write_bytes(src.read_bytes())
    manifest.append({'original':rel,'snapshot':dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
(HIST/'manifest.json').write_text(json.dumps({'status':'Superseded dual-power-port planning snapshots; native Rev E was not changed.','files':manifest},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

old=json.loads((DOCS/'controller_dual_pwm_pin_plan.json').read_text(encoding='utf-8'))
with (ROOT/'controller/hardware/g431_core/STM32G431RBT6_pin_plan.csv').open(encoding='utf-8-sig',newline='') as f:
    package=list(csv.DictReader(f))
assert len(package)==64
names={int(r['Pin']):r['GPIO'].split('-')[0] for r in package}
pins={n:i for i,n in names.items() if n.startswith('P')}
assert len(pins)==52
bindings=[]
def bind(group,signal,gpio,function,af=None,notes=''):
    bindings.append(dict(group=group,signal=signal,gpio=gpio,mcu_pin=pins[gpio],function=function,af=af,status='planned',notes=notes))

contacts=[dict(pin=1,signal='GND',gpio=None,mcu_pin=None,function='GND',af=None)]
for i,(gpio,ch,af) in enumerate([('PA8','CH1',6),('PB13','CH1N',6),('PA9','CH2',6),('PB14','CH2N',6),('PA10','CH3',6),('PB15','CH3N',4)],2):
    bind('PWM',f'PWM_{ch}',gpio,f'TIM1_{ch}',af,'3.3V logic to power-board hardware-gated driver inputs.')
    contacts.append(dict(pin=i,signal=f'PWM_{ch}',gpio=gpio,mcu_pin=pins[gpio],function=f'TIM1_{ch}',af=af))
contacts.append(dict(pin=8,signal='GND',gpio=None,mcu_pin=None,function='GND',af=None))

adc=[]
for i,x in enumerate(old['ADC_inputs'],1):
    x=copy.deepcopy(x);x.pop('dual_motor_example_role',None)
    x.update(name=f'ADC{i:02}',mcu_pin=pins[x['gpio']])
    adc.append(x)
    bind('ADC',x['name'],x['gpio'],'/'.join(x['supported_channels']),notes=f"Alternative examples: motor={x['single_motor_example_role']}; Boost={x['Boost_example_role']}; Vienna={x['Vienna_example_role']}. One power application at a time.")

groups=[
 ('ENC',[('A','PB6','TIM4_CH1',2),('B','PB7','TIM4_CH2',2),('Z','PA3','GPIO_EXTI3',None)]),
 ('SPI',[('SCK','PA5','SPI1_SCK',5),('MISO','PA6','SPI1_MISO',5),('MOSI','PA7','SPI1_MOSI',5),('CS_N','PC9','GPIO_Output',None)]),
 ('I2C',[('SCL','PA15','I2C1_SCL',4),('SDA','PB9','I2C1_SDA',4)]),
 ('TTL',[('TX','PB10','USART3_TX',7),('RX','PB11','USART3_RX',7)]),
 ('CAN',[('RX','PA11','FDCAN1_RX',9),('TX','PA12','FDCAN1_TX',9)]),
 ('SWD',[('DIO','PA13','SWDIO',0),('CLK','PA14','SWCLK',0)]),
 ('CORE',[('HSE_IN','PF0','OSC_IN',None),('HSE_OUT','PF1','OSC_OUT',None),('NRST','PG10','NRST',None),('BOOT0','PB8','BOOT0',None)]),
 ('LED',[('RUN','PC5','GPIO_Output',None),('FAULT','PC8','GPIO_Output',None),('COMM','PD2','GPIO_Output',None),('AUX','PB5','GPIO_Output',None)]),
 ('POWER_CTRL',[('FAULT_N','PB12','TIM1_BKIN',6),('ENABLE','PC4','GPIO_Output',None),('BASE_READY','PC13','GPIO_Input',None),('RUN_ARM','PC7','GPIO_Output',None),('BRAKE','PC6','TIM8_CH1',4)])]
for group,rows in groups:
    for signal,gpio,function,af in rows:bind(group,f'{group}_{signal}',gpio,function,af)
assert len(bindings)==len({x['gpio'] for x in bindings})==len({x['mcu_pin'] for x in bindings})==44
free=[{'gpio':g,'mcu_pin':p} for g,p in sorted(pins.items(),key=lambda item:item[1]) if g not in {x['gpio'] for x in bindings}]
assert len(free)==8
rails={'VBAT':'+3V3_MCU','VDD':'+3V3_MCU','VSS':'GND','VSSA':'GND','VDDA':'+3V3_A_MCU','VREF+':'VREF_MCU'}
power=[dict(mcu_pin=i,pad=n,proposed_rail=rails[n]) for i,n in names.items() if n in rails]
assert len(power)==12
usage=copy.deepcopy(old['ADC_usage_examples']);usage['counts']={'single_motor':8,'single_boost':4,'single_Vienna':9}
usage['single_motor_spare_options']={k.replace('ADC_','ADC'):v for k,v in usage['single_motor_spare_options'].items()}
budget={k:copy.deepcopy(old['analog_input_budget'][k]) for k in ['single_motor_full','single_boost_PFC','single_Vienna_PFC']}
budget['assumptions']='One motor OR one PFC application; one power PWM port. Do not sum motor and PFC channels.'
budget['decision']='Keep ten independent analog connectors; motor8, Boost4, Vienna9. Dual-motor control is no longer the target.'

p={
 'revision':'G-single-power-terminal-planning','date':'2026-11-11',
 'status':'Current single-power-port planning proposal; native Rev E schematic/PCB/BOM and shared library unchanged.',
 'scope':{'explicit_user_change':'Reduce functionality; retain only one power PWM port.',
          'working_reduction':'PWM, CTRL, SPI, I2C and ABZ each reduced to one. ADC10, CAN1, TTL1, SWD1 and 5V input1 retained.',
          'ADC_reason':'Single Vienna example already uses9 inputs; ten analog ports are retained rather than halved.',
          'motor_and_PFC_simultaneous':False,'power_application':'One motor or one Boost/Vienna application, not dual motor.'},
 'recommended_MCU':{'MPN':'STM32G431RBT6','package':'LQFP64, 10x10mm body','status':'Recommended for this reduced planning scope; the saved native project already uses RBT6.',
    'library_present':True,'library_symbol':'MyParts:STM32G431RBT6','library_footprint':'MyFootprints:ST_LQFP-64_10x10mm_P0.5mm_Pad1.2x0.3mm',
    'LCSC_code':'C431633','domestic_URL':'https://item.szlcsc.com/428111.html','core':'170MHz / 128KB Flash / 32KB SRAM / two ADC instances; no new stock or price verification.'},
 'package_signal_pad_count':52,'power_pad_count':12,'planned_signal_pads':44,'unallocated_signal_pads':free,
 'power_pads':power,'bindings':bindings,'PWM_port':{'name':'PWM','timer':'TIM1','contacts':contacts,'contact_order_status':'Suggested logical order, mating-view drawing still pending.'},
 'ADC_inputs':adc,'ADC_usage_examples':usage,'analog_input_budget':budget,
 'unallocated_analog_capabilities':[{'gpio':'PA2','mcu_pin':pins['PA2'],'channels':['ADC1_IN3']}],
 'connector_inventory_record':'controller_connector_inventory.json','placement_study':'controller_60mm_single_power_fit.json',
 'control_notes':['One independent active-low TIM1_BKIN on PB12; local hardware fault cutoff remains on the power board.',
   'PC7 RUN_ARM plus reset qualification produces CTRL_READY. Default pulldowns keep the bridge disabled through reset/ROM.',
   'PC6 TIM8_CH1 brake is independent of TIM1 bridge fault/ENABLE; use reset/ARM startup permission without disabling needed post-fault braking.',
   'SPI CS PC9 defaults high; release PA15 JTDI for I2C while retaining PA13/PA14 SWD.',
   'Disable unused UCPD dead-battery pulls affecting PA9/PA10 PWM and PB6 encoder input.',
   'Encoder Z uses PA3 GPIO/EXTI3, not a promised hardware timer index-reset function.',
   'CANH/L needs the controller-side classic-CAN PHY; keep SPI/ABZ supply PWR unresolved until sensors are selected.',
   'Ten analog inputs share two ADCs; sample timing, front ends and the selected control loop still require validation.'],
 'native_migration':{'native_MCU':'STM32G431RBT6','native_interface':'Rev E headers','changed':False,
   'needed':'Migrate to functional terminals, one encoder/SPI/I2C, ten ADC receivers, one CTRL and new layout. Existing Rev E reports do not validate this plan.'},
 'sources':{'datasheet':'https://www.st.com/resource/en/datasheet/stm32g431rb.pdf','package_pool':'../controller/hardware/g431_core/STM32G431RBT6_pin_plan.csv',
   'library':'D:/workspace/kicad_library/parts.csv','history':'history/dual_power_ports_2026-11-11/manifest.json'}
}
def save_json(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def save_csv(path,rows,fields):
    b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=fields);w.writeheader();w.writerows(rows)
    path.write_text(b.getvalue(),encoding='utf-8-sig',newline='')
save_json(DOCS/'controller_single_power_pin_plan.json',p)
save_csv(DOCS/'controller_single_power_pin_plan.csv',bindings,['group','signal','gpio','mcu_pin','function','af','status','notes'])
save_csv(DOCS/'controller_power_port.csv',contacts,['pin','signal','gpio','mcu_pin','function','af'])
by_gpio={x['gpio']:x for x in bindings};all_pads=[]
for i,n in names.items():
    if n in rails:row=dict(mcu_pin=i,pad=n,role=rails[n],function='power/reference/ground',af=None,status='power')
    elif n in by_gpio:
        x=by_gpio[n];row=dict(mcu_pin=i,pad=n,role=x['signal'],function=x['function'],af=x['af'],status='planned')
    else:row=dict(mcu_pin=i,pad=n,role='Unallocated',function='Reserve',af=None,status='unallocated')
    all_pads.append(row)
save_csv(DOCS/'controller_LQFP64_all_pins.csv',all_pads,['mcu_pin','pad','role','function','af','status'])
mode_rows=[dict(port=x['name'],gpio=x['gpio'],mcu_pin=x['mcu_pin'],ADC_channels='/'.join(x['supported_channels']),single_motor=x['single_motor_example_role'],Boost=x['Boost_example_role'],Vienna=x['Vienna_example_role']) for x in adc]
save_csv(DOCS/'controller_ADC_mode_examples.csv',mode_rows,['port','gpio','mcu_pin','ADC_channels','single_motor','Boost','Vienna'])

inventory=json.loads((DOCS/'controller_connector_inventory.json').read_text(encoding='utf-8'))
for g in inventory['connector_groups']:
    if g['name'] in ['PWM','SPI','I2C','ABZ','CTRL']:g['quantity']=1
    if g['name']=='PWM':g['status']='Single8P power PWM port requested; suggested physical order in controller_power_port.csv.'
    if g['name']=='SPI':g['status']='Single SPI bus in the reduced plan; retain6P contact roles. Supply voltage/load/protection pending sensor selection.'
    if g['name']=='I2C':g['status']='Single independent I2C bus in the reduced plan;4P contact structure proposed.'
    if g['name']=='ABZ':g['status']='Single ABZ encoder port in the reduced plan; retain5P contact roles. Supply pending encoder selection.'
    if g['name']=='CTRL':g['status']='Proposed single6P CTRL; includes the only brake command. No second brake reservation.'
inventory.update(status='Current single-power-port planning inventory; native Rev E remains unchanged.',total_connector_bodies=19,total_connector_contacts=62,
 contact_note='62 physical contacts include repeated power/GND and hardware CTRL_READY; MCU assignment is44 signal/special pads, not62GPIOs.',
 GPIO_expansion_status='Eight unallocated MCU pads currently have no dedicated expansion connector.',
 sources=['controller_single_power_pin_plan.json','terminal_interface_plan.json','controller_signal_connector_candidates.json','../inverter/hardware/bom/bom.csv'])
assert sum(g['quantity'] for g in inventory['connector_groups'])==19
assert sum(g['quantity']*g['pins_each'] for g in inventory['connector_groups'])==62
save_json(DOCS/'controller_connector_inventory.json',inventory)
save_csv(DOCS/'controller_connector_inventory.csv',[dict(Interface=g['name'],Quantity=g['quantity'],Pins_each=g['pins_each'],Contact_roles=' / '.join(g['contents']),Status=g['status']) for g in inventory['connector_groups']],['Interface','Quantity','Pins_each','Contact_roles','Status'])

t=json.loads((DOCS/'terminal_interface_plan.json').read_text(encoding='utf-8'))
t['revision']=p['revision'];t['status']=p['status'];t.pop('dual_PWM_allocation',None)
t['single_power_allocation']={'user_request':p['scope']['explicit_user_change'],'working_reduction':p['scope']['working_reduction'],
 'recommended_MCU':'STM32G431RBT6, LQFP64; existing reviewed library material','plan_JSON':'controller_single_power_pin_plan.json',
 'full_pin_CSV':'controller_single_power_pin_plan.csv','package_pin_CSV':'controller_LQFP64_all_pins.csv','PWM_CSV':'controller_power_port.csv',
 'signal_pad_budget':'44 of52 signal/special pads used;8 free,12 power/reference/ground pads.'}
t['FOC_capacity_note']={'current_target_motor_count':1,'PWM_power_ports':1,'MCU':'STM32G431RBT6, LQFP64',
 'qualification':'One motor or one PFC application; no dual-motor or simultaneous motor/PFC target in this reduced plan. TIM1 is bridge PWM and TIM8_CH1 is the separate brake output.'}
t['confirmed']['PWM']={'connector_count':1,'connector_pins':8,'signal_count':6,'GND_pins':2,'signals':['CH1','CH1N','CH2','CH2N','CH3','CH3N'],
 'port':'TIM1 PA8/PB13, PA9/PB14, PA10/PB15; see controller_power_port.csv for pin-specific AF and physical pins.',
 'physical_pin_order':'Suggested: GND, CH1, CH1N, CH2, CH2N, CH3, CH3N, GND; mating-view drawing pending.'}
t['confirmed']['interface_counts']={'SPI':1,'I2C':1,'ABZ':1,'CAN':1,'TTL_UART':1}
t['reduction_interpretation']='User explicitly requested one power PWM port; related duplicated interfaces reduced to one under the communicated scope assumption. ADC ten retained for standalone Vienna.'
t['confirmed']['operating_modes']={'motor_and_PFC_simultaneous':False,'motor_mode':'One motor.',
 'PFC_mode':'One Boost or Vienna application, no motor control on the same MCU.','PWM_usage':'One physical power PWM connector; unused outputs disabled.',
 'ADC_usage':'Same ten generic ports reused for alternative motor/PFC applications.'}
t['proposed_ADC_connectors']['channels']=[{'name':x['name'],'planned_GPIO':x['gpio'],'single_motor_usage_example':x['single_motor_example_role'],'Boost_usage_example':x['Boost_example_role'],'Vienna_usage_example':x['Vienna_example_role']} for x in adc]
t['ADC_usage_examples']=copy.deepcopy(usage);t['ADC_usage_examples']['CSV']='controller_ADC_mode_examples.csv'
t['analog_budget_note']=budget
t['mechanical_fit_study']={'record':'controller_60mm_single_power_fit.json','status':'Single-face nominal-body/courtyard estimate; not native PCB placement/DRC.',
 'top_connector_count':19,'bottom_connector_count':0,'image':'../outputs/controller_single_power_2026-11-11/controller_60mm_single_power_study.png'}
t['history']='history/dual_power_ports_2026-11-11/manifest.json'
save_json(DOCS/'terminal_interface_plan.json',t)
c=json.loads((DOCS/'controller_signal_connector_candidates.json').read_text(encoding='utf-8'))
c['PWM_recommendation']['connector_count']=1
c['status']='Accepted XUNPU GH1.25 ADC2P and single PWM8P planning selection. Native/BOM/library migration pending.'
save_json(DOCS/'controller_signal_connector_candidates.json',c)

for filename in ['controller_dual_pwm_pin_plan.json','controller_60mm_fit_study.json']:
    f=DOCS/filename;x=json.loads(f.read_text(encoding='utf-8'))
    x['status']='SUPERSEDED planning: user reduced to one power PWM port.'
    x['superseded_by']='controller_single_power_pin_plan.json'
    save_json(f,x)

readme=ROOT/'README.md';s=readme.read_text(encoding='utf-8');lines=s.splitlines()
lines[2]='最新方案已收敛为**单功率PWM口**：PWM8P、CTRL、SPI、I²C、ABZ各一路，CAN/TTL/SWD各一路；保留10个独立ADC2P端子和5V输入。按重复功能各减一路的规划，共19个连接器；电机与PFC二选一。推荐沿用已有STM32G431RBT6（LQFP64）物料，44个功能脚已分配、剩8个。见 [当前引脚表](docs/controller_single_power_pin_plan.csv)、[连接器总表](docs/controller_connector_inventory.csv)和 [规划说明](docs/controller_daughterboard.md)。旧双功率口/100脚规划已归档，原生工程仍是Rev E排针版，尚未迁移到端子版。'
readme.write_text('\n'.join(lines)+'\n',encoding='utf-8')

doc=DOCS/'controller_daughterboard.md';prior=doc.read_text(encoding='utf-8');marker='## 以下为已保存的Rev E工程'
assert prior.count(marker)==1;tail=marker+prior.split(marker,1)[1]
intro='''# controller单功率口规划与Rev E工程

## 当前方案：单功率口，60×60mm

用户要求减少功能，只留一个功率PWM口。本轮按此收敛重复接口：PWM、CTRL、SPI、I²C、ABZ各一路，CAN、TTL、SWD和5V输入各一路；10个独立模拟端子保留，因为单独Vienna例需9路。电机和PFC应用二选一，当前不再规划双电机。四个GPIO指示灯、电源灯及顶面的RESET/BOOT按钮保留。

推荐沿用已有 **STM32G431RBT6 / LQFP64** 物料，无需为当前功能增加到100脚。经逐脚核对，52个信号/专用pad中用44个，余8个；12个电源/参考/地另计。MCU已有reviewed库物料，但新端子版没有实施原理图/PCB/BOM迁移，旧Rev E报告不验证本方案。双功率口/100脚规划见 [历史快照](history/dual_power_ports_2026-11-11/manifest.json)。

### 连接器总表

采用已接受的讯普GH1.25信号系列。按本轮收敛建议共 **19个板端连接器、62个触点**；触点包含重复电源/地和硬件CTRL_READY，不等于MCU GPIO数量。I²C4P、CTRL6P和5V输入2P仍是结构建议，完整针序、配套型号与封装待核对。

| 接口 | 数量 | 每口针数 | 内容 |
| --- | --- | --- | --- |
| PWM功率控制 | 1 | 8P | 6PWM＋2GND |
| ADC模拟输入 | 10 | 2P | 调理后的采样信号＋GND |
| SPI | 1 | 6P | SCK、MOSI、MISO、CS、PWR、GND |
| I²C | 1 | 建议4P | SCL、SDA、3.3V、GND |
| ABZ | 1 | 5P | A、B、Z、PWR、GND |
| CAN | 1 | 3P | CANH、CANL、GND |
| TTL | 1 | 3P | TX、RX、GND，3.3V逻辑 |
| SWD | 1 | 5P | VTREF、SWDIO、SWCLK、GND、NRST |
| CTRL | 1 | 建议6P | ENABLE、FAULT_N、BASE_READY、CTRL_READY、BRAKE、GND |
| 5V输入 | 1 | 建议2P | 受稳压的5V＋GND；选区别于ADC的插合外形 |

制动信号已在CTRL中，仅留一路制动；电阻功率端子、直流母线和U/V/W端子在inverter，不计controller连接器。SPI/ABZ的PWR供电电压、限流及负载预算待传感器选型，逻辑按3.3V；CAN需控制板上的收发器。SWD VTREF仅作目标电压参考。8个空闲MCU脚暂不另设扩展连接器。详见 [端子CSV](controller_connector_inventory.csv)和 [结构化清单](controller_connector_inventory.json)。

### PWM与外围引脚

| PWM针号 | 功能 | GPIO / RBT6物理脚号 | AF |
| --- | --- | --- | --- |
| 1 | GND | GND | — |
| 2 | TIM1_CH1 | PA8 / 42 | AF6 |
| 3 | TIM1_CH1N | PB13 / 35 | AF6 |
| 4 | TIM1_CH2 | PA9 / 43 | AF6 |
| 5 | TIM1_CH2N | PB14 / 36 | AF6 |
| 6 | TIM1_CH3 | PA10 / 44 | AF6 |
| 7 | TIM1_CH3N | PB15 / 37 | AF4 |
| 8 | GND | GND | — |

这是逻辑针序建议；接电机时为三组互补输出，接Boost/Vienna时按驱动拓扑重新配置，未用输出关闭。8P中不含电源、ADC或保护控制信号。完整物理pin见 [64脚总表](controller_LQFP64_all_pins.csv)、[44项功能表](controller_single_power_pin_plan.csv)、[PWM针序](controller_power_port.csv)及 [结构化规划](controller_single_power_pin_plan.json)。

| 功能 | 分配 |
| --- | --- |
| ABZ | PB6/PB7，TIM4 CH1/2 AF2；Z=PA3/EXTI3 |
| SPI | PA5/PA6/PA7，SPI1 AF5；CS=PC9 GPIO |
| I²C | PA15 SCL / PB9 SDA，I2C1 AF4 |
| TTL | PB10 TX / PB11 RX，USART3 AF7 |
| CAN | PA11 RX / PA12 TX，FDCAN1 AF9；现有PHY按经典CAN |
| SWD | PA13/PA14，保留NRST、VTREF、GND |
| FAULT | PB12 / TIM1_BKIN AF6，低有效，本地硬件关断仍在功率板 |
| ENABLE、READY | PC4输出 / PC13输入 |
| 本地ARM | PC7，经复位资格与门产生CTRL_READY，默认下拉 |
| 制动PWM | PC6 / TIM8_CH1 AF4，与TIM1桥故障独立；启动许可由复位/ARM控制 |
| GPIO指示灯 | RUN=PC5、FAULT=PC8、COMM=PD2、AUX=PB5 |
| HSE、RESET、BOOT | PF0/PF1、PG10、PB8；两个按钮仍在MCU顶面板边 |

空闲8脚为PA2、PB3、PB4、PC10、PC11、PC12、PC14、PC15，其中PA2具ADC1_IN3能力，但没有新增端子。初始化关闭影响PA9/PA10/PB6的UCPD dead-battery行为；PA15释放JTDI但保留SWD。Z只承诺GPIO中断；十个输入仍共享两ADC，转换序列和采样窗口待验证。依据 [ST DS12589表12/13](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf)。

### 十路模拟端子的用途假设

接口丝印采用ADC01～ADC10，同一套端子用于单电机、Boost或Vienna；每次选择一种应用。以下是用途假设，不是传感器电路或ADC时序定稿。

| 端子 | GPIO / 物理脚号 | 单电机 | Boost | Vienna |
| --- | --- | --- | --- | --- |
| ADC01 | PC0 / 8 | U电流 | 电感电流 | L1电流 |
| ADC02 | PC1 / 9 | V电流 | 备用 | L2电流 |
| ADC03 | PC2 / 10 | W电流 | 备用 | L3电流 |
| ADC04 | PC3 / 11 | U相电压 | 整流后输入电压 | 输入相1电压 |
| ADC05 | PA0 / 12 | V相电压 | 备用 | 输入相2电压 |
| ADC06 | PA1 / 13 | W相电压 | 备用 | 输入相3电压 |
| ADC07 | PA4 / 18 | 母线电压 | 输出电压 | 上半母线电压 |
| ADC08 | PB0 / 24 | 备用 | 备用 | 下半母线电压 |
| ADC09 | PB1 / 25 | 功率板NTC | 功率板NTC | 功率板NTC |
| ADC10 | PB2 / 26 | 备用 | 备用 | 备用 |
| 已用/剩余 | — | 8/2 | 4/6 | 9/1 |

前六路可接ADC1/2，PC0～3为IN6～9、PA0/1为IN1/2；后四路固定为ADC2_IN17、ADC1_IN15、ADC1_IN12、ADC2_IN12。电流、电压及NTC都由功率板前端转为参考兼容的低压电压，不能直接接母线、相线、分流器两端或裸NTC。单电机相电压沿用当前PWM相节点含义；Vienna上下半母线不得通过把物理中点接controller地来替代正确的测量前端。Vienna前8项参考 [TI测量结构](https://www.ti.com/lit/ug/tiducj0g/tiducj0g.pdf)，另加本项目NTC预算。详见 [用途CSV](controller_ADC_mode_examples.csv)。

### 60×60mm初步摆放

19个连接器的本体沿边总宽度暂按139.5mm估算（含未选5V座6mm占位），较旧24口方案减少约52.5mm；19口分四边、每相邻口留1mm后约154.5mm，另计按键和最终courtyard。一个全顶面的候选分组为：左5ADC＋ABZ、右5ADC＋I²C、上PWM＋CTRL＋SPI、下CAN＋TTL＋SWD＋5V输入＋RESET/BOOT。按GH本体和实际按键courtyard估算，四边跨度43.25/42/36.75/43.3mm，均在45mm边长内；MCU居中，两个按钮仍顶面靠边。

见 [单口尺寸草图](../outputs/controller_single_power_2026-11-11/controller_60mm_single_power_study.png)和 [空间估算数据](controller_60mm_single_power_fit.json)。这是可进入正式布局的几何候选，不是封装/插头/锁扣/线束/支柱/上下板干涉或布线DRC通过报告。按4层板候选继续设计；旧双面24口草图已不作为当前方案。

ADC采用已接受的讯普 [WAFER-GH1.25-2PWB / C3029377](https://item.szlcsc.com/3561389.html)，PWM采用单个 [WAFER-GH1.25-8PWB / C3029383](https://item.szlcsc.com/3561395.html)；板座和配套线束仍需库定义/封装核对。MCU沿用已有 [STM32G431RBT6 / C431633](https://item.szlcsc.com/428111.html)，共享库已存在，不新增VBT6物料。当前机器记录入口为 [terminal_interface_plan.json](terminal_interface_plan.json)。

'''
doc.write_text(intro+tail,encoding='utf-8')

before=json.loads((ROOT/'outputs/dual_pwm_pin_review_2026-11-11/native_before.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in before.items())
save_json(OUT/'validation.json',{'scope':'Planning only; no native ERC/DRC or runtime qualification.',
 'package_pads':64,'power_pads':12,'signal_pad_pool':52,'used_signal_pads':44,'unallocated':8,
 'connector_bodies':19,'contacts':62,'ADC_ports':10,'PWM_power_ports':1,'SPI':1,'I2C':1,'ABZ':1,'CAN':1,'TTL':1,
 'duplicates':False,'native_files_unchanged':True,'native_hashes':before,'mode_counts':{'motor':8,'Boost':4,'Vienna':9}})
print(json.dumps({'used_pads':44,'free':8,'connectors':19,'contacts':62,'native_unchanged':True},ensure_ascii=False))

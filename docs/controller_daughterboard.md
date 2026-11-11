# controller单功率口规划与Rev E工程

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

**ADC减口评估（未定稿）**：用户提出是否再减两个ADC口。现有10口中ADC10在单电机、Boost、Vienna三种示例里均备用，减到9口可以保持所有模拟测温配置。若减到8口，保留ADC01～08：单电机/Boost将NTC从旧ADC09改接ADC08；Vienna的8个电气反馈则占满这8口，温度需由功率板增加I²C测温前端（外置ADC读NTC或合适数字温度方案）回传，不能直接删掉温度功能。温度是慢速监测，不用I²C采电流环。9口是电路最少变动方案；8口是需要明确测温路径的减连接器方案。

对应预算为：9ADC→18个连接器、43个功能pad/余9；8ADC→17个连接器、42个功能pad/余10。完整8口用途假设见 [减口选项](controller_ADC_reduction_options.json)。这些是讨论选项，当前10口清单和尺寸草排尚未切换，避免把尚未决定的测温硬件当作已完成。

19个连接器的本体沿边总宽度暂按139.5mm估算（含未选5V座6mm占位），较旧24口方案减少约52.5mm；19口分四边、每相邻口留1mm后约154.5mm，另计按键和最终courtyard。一个全顶面的候选分组为：左5ADC＋ABZ、右5ADC＋I²C、上PWM＋CTRL＋SPI、下CAN＋TTL＋SWD＋5V输入＋RESET/BOOT。按GH本体和实际按键courtyard估算，四边跨度43.25/42/36.75/43.3mm，均在45mm边长内；MCU居中，两个按钮仍顶面靠边。

见 [单口尺寸草图](../outputs/controller_single_power_2026-11-11/controller_60mm_single_power_study.png)和 [空间估算数据](controller_60mm_single_power_fit.json)。这是可进入正式布局的几何候选，不是封装/插头/锁扣/线束/支柱/上下板干涉或布线DRC通过报告。按4层板候选继续设计；旧双面24口草图已不作为当前方案。

ADC采用已接受的讯普 [WAFER-GH1.25-2PWB / C3029377](https://item.szlcsc.com/3561389.html)，PWM采用单个 [WAFER-GH1.25-8PWB / C3029383](https://item.szlcsc.com/3561395.html)；板座和配套线束仍需库定义/封装核对。MCU沿用已有 [STM32G431RBT6 / C431633](https://item.szlcsc.com/428111.html)，共享库已存在，不新增VBT6物料。当前机器记录入口为 [terminal_interface_plan.json](terminal_interface_plan.json)。

## 以下为已保存的Rev E工程

2026-11-11更新 **G431最小系统子板＋应用功率底板** 原理图，接入已reviewed共享库器件；本轮交接及剩余采购料号见 [更新记录](schematic_update_2026-11-11.md)。子板只通过GPIO排针插到底板，也可经同一排针独立供电/调试；专用应用接口和应用采样/保护全部在底板。结构为共地、非隔离。

| 工程 | 当前交付 |
| --- | --- |
| [controller最小核](../controller/hardware/g431_core/README.md) | 7页、47个位号、3项HSE DNP；[KiCad](../controller/hardware/g431_core/controller.kicad_pro)、[PDF](../controller/hardware/g431_core/review/controller.pdf) |
| [inverter底板](../inverter/hardware/README.md) | 20页、317个位号、14项DNP；[KiCad](../inverter/hardware/inverter.kicad_pro)、[PDF](../inverter/hardware/review/inverter.pdf) |

双ERC为0错误、0警告；64针、52个信号pad、迁移物理pin连通及32768组静态保护/ARM逻辑检查通过。两板已建立60×60mm PCB 0.1布局审查稿，实际布线/DRC及预览见 [PCB交接](pcb_review_2026-11-11.md)；插合高度、制造叠层和实物装配仍待验证。

## 60×60 mm上下叠放规划

上层为应用功率板，下层为G431最小系统板，两块PCB均60×60mm，轮廓边线对齐。PCB 0.1采用四角2.2mm NPTH供M2支撑，孔心距52×52mm，距板边均4mm；两组排针集中在左侧，右侧留给功率桥。共同坐标见 [机械合同](pcb_stack_contract_rev_e.json)。器件干涉、支柱长度及实际装配仍须两板一起校核。旧45×45子板示意属于历史讨论。

下板顶面male排针朝上，上板底面female排母朝下。母座8.5 mm仅指塑高，不等于两块PCB间距；板距由完整插合几何、相向元件高度、公差以及通风/装配余量共同决定。pin1和针位沿用Rev E64针合同，不能按上下板俯视图自行镜像。

上板顶面的MOS/电解外露便于布置和维护，但BSC110N15NS5主要通过底部焊盘向PCB导热，需同时安排上板背面散热铜及风道。上下位置调整不能代替损耗/温升验证，也不保证10 Arms连续能力。

MCU放在下层控制板顶面、朝两板之间，避开上板热源及高dv/dt铜区投影。RESET（SW2）和BOOT（SW3）均在控制板顶面、与MCU同面，操作面朝上，靠板边从侧面伸入后向下按；与排针、M2支柱和线束错开。插合后侧向通道须允许按住BOOT的同时操作RESET。两键统一采用XKB Connection [TS-1101-C-W / C318938](https://item.szlcsc.com/300030.html)，已接入共享库符号及专用封装；操作净空须随板距、支撑及线束共同校核，当前尚未经机械验证。

## 分工与启动许可

子板仅保留STM32G431RBT6、去耦、VDDA/VREF、可选HSE、RESET/BOOT、本地5 V转3.3 V与监控、U103/U105 ARM联锁及两组GPIO排针。底板保留功率级、采样前端、比较器/锁存/PWM门控、制动、SWD/TTL/ABZ/SPI/CAN、五个LED，以及ADC末端RC和回传信号限流/钳位。

U103将NRST施密特缓冲成CORE_RESET_OK，U105将它与PC7相与产生CTRL_READY；R402 10k使PC7默认低。PC7在独立最小板上可作GPIO，插功率底板时必须保留RUN_ARM。应用先完成安全输出、BKIN和运行状态初始化，再主动拉高PC7；NRST释放及ROM启动均不自动取得运行许可。底板继续将CTRL_READY与ENABLE相与，原本地比较器、锁存及PWM封锁独立工作。

52是可GPIO/复用信号pad总数，不表示52个可同时自由使用GPIO。PG10保留NRST、PF0/PF1用于可选HSE、PB8用于BOOT0、PA13/PA14默认SWD。子板全部引出且GPIO无NC；本底板不用的9个socket脚PB3、PB4、PB8_BOOT0、PB9、PC7、PC14、PC15、HSE_IN、HSE_OUT显式NC。PC7仍在子板内部参与ARM，不能称为未用GPIO。

## 供电和应用保护

J101/1、3的供电在底板称+5V_INV、子板称+5V_CORE_IN。独立使用从这两针送入 **4.75～5.25 V**，并接GND；不新增独立电源连接器，不能同时并联独立5 V源和底板5 V。子板TLV76733DRVR产生本地3.3 V，总负载预算100 mA。

J101/22、32将子板+3V3_MCU作为底板+3V3_CORE_REF，**只供底板回传钳位/故障上拉及SWD VTREF检测，不能与底板+3V3_INV并联，也不作为其通用电源**。原始NRST现通过J102/32引到底板SWD，仍保留子板本地监控/按键；外部调试器仅开漏拉低，不能推挽驱动或反供电。

八路ADC在底板经360 Ω/BAT54S钳位后，再接100 Ω/1 nF，最终送到GPIO排针；子板不再放应用RC/钳位。七路缓冲源另带47 Ω，NTC还需计入其源阻和10 nF滤波，采样时间不能只按单个RC估算。BASE_READY/FAULT_N也在底板分别经1 kΩ/钳位后接PC13/PB12。钳位参考来自核心轨，短时总正向注入预算50 mA，不是硬限流或持续耐受承诺。

## 两组2×16接口

共64针为 **52个MCU信号pad＋2个5 V输入＋2个3.3 V核心参考＋CTRL_READY＋7地**。子板顶面朝上的male为XFCN [PZ254V-12-32P / C22465940](https://item.szlcsc.com/24163082.html)，功率板底面朝下的female为 [PM254V-12-32-H85 / C46595991](https://item.szlcsc.com/48735272.html)，P2.54；两者已接入reviewed共享符号与专用封装，仍需在PCB阶段校核实际插合、布局及净空，8.5 mm母座塑高不作为板距定稿。各板按同一针号插合，不使用IDC镜像排线；Rev E不可与旧40针Rev D混插。

| 针号 | J101 | J102 |
| --- | --- | --- |
| 1 | 5V_IN | PB8_BOOT0 |
| 2 | GND | PB9 |
| 3 | 5V_IN | PB10 |
| 4 | GND | PB11 |
| 5 | PA0 | PB12 |
| 6 | PA1 | PB13 |
| 7 | PA2 | PB14 |
| 8 | PA3 | PB15 |
| 9 | PA4 | GND |
| 10 | PA5 | CTRL_READY |
| 11 | PA6 | PC0 |
| 12 | PA7 | PC1 |
| 13 | PA8 | PC2 |
| 14 | PA9 | PC3 |
| 15 | PA10 | PC4 |
| 16 | PA11 | PC5 |
| 17 | PA12 | PC6 |
| 18 | PA13 | PC7 |
| 19 | PA14 | PC8 |
| 20 | PA15 | PC9 |
| 21 | GND | PC10 |
| 22 | 3V3_CORE_REF | PC11 |
| 23 | PB0 | PC12 |
| 24 | PB1 | PC13 |
| 25 | PB2 | PC14 |
| 26 | PB3 | PC15 |
| 27 | PB4 | GND |
| 28 | PB5 | PD2 |
| 29 | PB6 | HSE_IN |
| 30 | PB7 | HSE_OUT |
| 31 | GND | GND |
| 32 | 3V3_CORE_REF | NRST |

5V_IN与3V3_CORE_REF是表中的接口角色名，实际电源网名对应关系如上；其它端口见 [MCU脚表](../controller/hardware/g431_core/STM32G431RBT6_pin_plan.csv)。底板对未用socket脚NC，不能因此删去子板引出。机器合同为 [daughterboard_pin_contract.json](daughterboard_pin_contract.json)。两板丝印均需清楚标pin1、J101/J102及接口版本，并以实际插合视图核对，不按上下板俯视图自行镜像。

## SWD与ROM启动

底板SWD通过排针PA13/SWDIO、PA14/SWCLK、NRST、核心3.3 V VTREF和GND接子板；最小板独立使用从同一GPIO排针接调试器，不另加专用接口。

物理BOOT操作要求 **nSWBOOT0=1、nBOOT1=1、BOOT_LOCK=0**。按住BOOT，按下并释放RESET，再松开BOOT。ROM USART3入口为 **PC10_TX/PC11_RX**；现有TTL接口PB10/PB11是应用串口，不是这个ROM入口。PC10/PC11与应用SPI B复用，使用ROM串口时断开对应SPI外设。插功率底板时必须保持PC7的ARM职责，ROM阶段默认禁止功率桥。

## 验证与历史

当前交付为原理图与PCB布局审查稿。共地、非隔离结构不保证炸管后MCU存活；未证明带电插拔能力，按断电装拆维护。ERC及静态逻辑不能替代PCB回流、采样窗口、供电/保护动态、热及实际故障验证。

前一版应用接口在子板上的40针Rev D已 [整体归档](../inverter/history/daughterboard_rev_d_before_minimum_core_2026-11-07.zip)。更早的 [Rev C集成板](../inverter/history/integrated_rev_c_60x60/)与 [LKS controller](../controller/hardware/controller.kicad_sch)保留历史，旧针序、NC和PCB结论均不适用于Rev E。

MCU及两键顶面高度计入板间净空，并核对上板背面器件及装配余量。底面若装其它器件，再核对底部支撑净空；RESET/BOOT从侧面伸入的两键组合操作通道随PCB与结构一同核对。

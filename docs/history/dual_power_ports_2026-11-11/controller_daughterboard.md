# controller接口规划与Rev E工程

## 最新端子方案讨论（2026-11-11）

用户已改变板间连接方式：controller与inverter用端子和连接线连接，板间用铜柱机械固定；controller按ADC、I²C、SPI等功能引出接口。以下原生工程与既有64针合同仍为Rev E排针版本，尚未迁移到端子版，既有ERC/PCB报告不验证新接口。

本次已确认：controller设置**两个独立PWM功率控制口，每口8P，包含6路PWM和2根GND**；SPI、I²C、ABZ各两路，CAN和TTL各一路；**总共10个独立模拟端子，不是原8路再加10路**。用户选择保留外设接口和指示灯，评估更多引脚封装。本规划推荐 **STM32G431VBT6，LQFP100，14×14mm本体**；这是下一版的型号与引脚建议，现有原生工程仍为RBT6，未实施换型。

### controller板端连接器总清单

用户接受讯普GH1.25信号连接器方案：ADC每口2P，PWM每口8P。按既有接口角色及补全建议，规划共 **24个板端连接器**；它们不是已保存Rev E PCB上的实际接口。功能清单和针数状态见 [结构化总表](controller_connector_inventory.json)。表内信号列是角色集合，不能当作已经锁定的物理针序。

| 接口 | 数量 | 每口针数 | 信号/用途 | 针数依据 |
| --- | --- | --- | --- | --- |
| PWM功率控制 | 2 | 8P | 6路PWM＋2GND | 已确认 |
| ADC模拟输入 | 10 | 2P | 调理后的采样信号＋GND | 已接受2P推荐 |
| SPI | 2 | 6P | SCK、MOSI、MISO、CS、PWR、GND | 沿用已有6P角色 |
| I²C | 2 | 4P | SCL、SDA、3.3V、GND | 建议 |
| ABZ编码器 | 2 | 5P | A、B、Z、PWR、GND | 沿用已有5P角色 |
| CAN | 1 | 3P | CANH、CANL、GND | 沿用已有3P角色 |
| TTL串口 | 1 | 3P | TX、RX、GND，3.3V逻辑 | 沿用已有3P角色 |
| SWD | 1 | 5P | VTREF、SWDIO、SWCLK、GND、NRST | 沿用已有5P角色 |
| CTRL控制/保护 | 2 | 6P | ENABLE、FAULT_N、BASE_READY、CTRL_READY、BRAKE、GND | 建议，BRAKE_B仅预留 |
| controller供电输入 | 1 | 2P | 受稳压的5V＋GND | 建议，连接器型号待定 |

按上表共91个连接器触点，含重复的地、电源和共享CTRL_READY，不等于91个MCU GPIO。两个CTRL口已包括制动控制信号；制动电阻功率端子、DC母线端子和U/V/W端子属于inverter。RESET/BOOT是板载按钮，LED也是板载器件，不计连接器。旧inverter的独立可选5V传感器输出J7未确认迁到controller，不额外加口；USB和LLC口不增加。

SPI/ABZ的PWR暂不定为3.3V或5V：旧板通过默认DNP的0Ω预留到+5V_SENSOR，供电电压、限流和负载预算需随传感器确定；逻辑信号仍按3.3V。CAN需将收发器及接口侧电路迁到controller后才能引出CANH/CANL，SWD的VTREF只作目标电压参考。5V输入建议使用与ADC2P明显不同的插合外形；12～24V辅助输入仍由功率板处理，不直接送controller的5V口。

### 60×60mm空间估算

24个接口全部在同一面、沿四边单排侧插时，23个GH板座本体沿边宽度合计186mm，另加供电座暂按4～6mm，总本体宽度约190～192mm。按相邻接口只留1mm、四边各一排计算，20处间隔后需要约210～212mm；四角支柱和端部净空后，四边可用长度粗估仅176～184mm，尚未加入两个按键、最终焊盘/courtyard和插拔余量。这种全顶面摆法不适合直接定稿。

保留60×60mm有一个**尚未选定的双面接口候选**：顶面18个连接器（ADC10、PWM2、CTRL2、SPI2、ABZ2），底面6个（I²C2、CAN1、TTL1、SWD1、5V输入1）；MCU、RESET和BOOT仍在顶面。左/右各5个ADC＋1个CTRL，顶部两SPI＋两ABZ，底边两个PWM和两个按键；其余接口从控制板底面朝板边出线。

按GH名义本体、实际按键courtyard及MCU18×18mm估算预留区域检查，顶面四边占用跨度约44.5/44.5/43.5/38.3mm，无同面矩形或M2孔净空相交；该结果只说明**有几何摆放路径**。未验证GH最终封装、插合后胶壳、锁扣操作、线束弯折、上下板及底部离地净空，也未放置完整电源/去耦/保护/收发器及布线。供电座暂用6×6mm占位；实际型号仍待定。底面图采用同一装配XY坐标，不是制造用的背面镜像图。

见 [双面尺寸草图](../outputs/controller_60mm_fit_study_2026-11-11/controller_60mm_two_face_body_study.png)和 [空间估算数据](controller_60mm_fit_study.json)。原生PCB未修改，这不是PCB布局/DRC通过报告；底面接口方案也未作为新机械合同定稿。

两个口分别使用TIM1和TIM8，可按所接功率板配置电机或PFC输出模式。**同一块controller的电机应用与PFC应用二选一：控制PFC时不运行电机控制，不将两者的ADC和控制循环需求叠加。** 两口不是并联复制同一套PWM，也不把每口的三组互补输出承诺成六个任意独立时基；所选模式未使用的输出保持关闭。保存的inverter仍是一路电机，PFC功率板未开始绘制；不据此增加双PFC或恢复LLC目标。ST的 [EVSPIN32G4-DUAL参考板](https://www.st.com/en/evaluation-tools/evspin32g4-dual.html)不能代替本项目电机模式下双路20kHz、ThreadX和三分流采样验证。

**建议的8P逻辑针序**如下；针号待连接器型号与插合面图确定后再锁定。全口为3.3V控制逻辑及参考地，不连接MOS栅极或功率母线。

| 端子针号 | 通用功能 | PWM_A / TIM1 | LQFP100脚号 | PWM_B / TIM8 | LQFP100脚号 |
| --- | --- | --- | --- | --- | --- |
| 1 | GND | GND | — | GND | — |
| 2 | CH1 / 相1高侧 | PE9 / AF2 | 40 | PC6 / AF4 | 65 |
| 3 | CH1N / 相1低侧 | PE8 / AF2 | 39 | PC10 / AF4 | 79 |
| 4 | CH2 / 相2高侧 | PE11 / AF2 | 42 | PC7 / AF4 | 66 |
| 5 | CH2N / 相2低侧 | PE10 / AF2 | 41 | PC11 / AF4 | 80 |
| 6 | CH3 / 相3高侧 | PE13 / AF2 | 44 | PC8 / AF4 | 67 |
| 7 | CH3N / 相3低侧 | PE12 / AF2 | 43 | PC12 / AF4 | 81 |
| 8 | GND | GND | — | GND | — |

相1/2/3高低侧是接三相桥时的角色；Boost/Vienna的未用输出保持禁用，极性和同相/互补关系按实际驱动拓扑重新配置。两个8P口不包含ADC、ENABLE、FAULT、READY或供电，不能仅连接这八根线就驱动完整功率系统。

**独立控制与制动引脚**另行引出；CTRL端子建议每板6P：ENABLE、FAULT_N、BASE_READY、CTRL_READY、BRAKE和GND，具体针序待定。

| 功能 | A口相关 | B口相关 | 约束 |
| --- | --- | --- | --- |
| 硬件故障输入 | PE15 / TIM1_BKIN / AF2 / pin46 | PD2 / TIM8_BKIN / AF4 / pin84 | 两路独立、低有效；功率板本地硬件保护同时封锁驱动 |
| ENABLE | PD10 / pin57 | PD11 / pin58 | 外部下拉、复位默认关闭 |
| BASE_READY | PC13 / pin7 | PC14 / pin8 | 仅作输入；PC14不能同时使用LSE |
| 制动PWM | PF9 / TIM15_CH1 / AF3 / pin10 | PF10 / TIM15_CH2 / AF3 / pin11 | A沿用一路制动；B仅预留引脚，不表示已增加第二路功率电路；两通道共享频率、占空比分别可控 |

本地RUN_ARM改为 **PE7 / pin38**，通过复位监控和硬件与门产生共享CTRL_READY；每块功率板再与自身ENABLE及本地硬件OK形成许可。原Rev E的PC7 ARM布线必须迁移，不能仅改软件宏。制动使用复位/ARM启动许可，但不串接三相桥FAULT/ENABLE作为关断条件，以保留故障后的制动能力。G431的ROM会使用PWM_B上的PC8、PC10/PC11；BOOT/ROM必须保持硬件许可关闭，不能依赖应用尚未运行时的PWM脚电平。依据 [AN2606的G431配置表](https://www.st.com/resource/en/application_note/an2606-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf)。

**现有外围接口全部保留**，采用下表重排，不再与两个PWM口冲突。

| 外围 | GPIO规划 | 资源 |
| --- | --- | --- |
| ABZ编码器A | A=PD3，B=PD4，Z=PD5 | TIM2 CH1/CH2 AF2；Z=EXTI5 |
| ABZ编码器B | A=PB6，B=PB7，Z=PD6 | TIM4 CH1/CH2 AF2；Z=EXTI6 |
| SPI A | PA5/PA6/PA7，CS=PE0 | 独立SPI1 AF5 |
| SPI B | PB3/PB4/PB5，CS=PE1 | 独立SPI3 AF6 |
| I²C A | SCL=PA15，SDA=PB9 | 独立I2C1 AF4 |
| I²C B | SCL=PA9，SDA=PA8 | 独立I2C2 AF4，LQFP100 pin70/pin69 |
| TTL串口 | TX=PD8，RX=PD9 | USART3 AF7 |
| CAN | RX=PA11，TX=PA12 | FDCAN1 AF9；现有收发器仍按经典CAN使用 |
| SWD | PA13/PA14，加NRST/VTREF/GND | 保留SWD，释放PB3/PB4的JTAG/SWO复用 |
| 四个GPIO指示灯 | RUN=PE2，FAULT=PE3，COMM=PE4，AUX=PE5 | 禁用这些脚的TRACE功能；电源灯另接电源、不占GPIO |
| HSE、RESET、BOOT | PF0/PF1、PG10、PB8 | 保留晶振及两个按钮；option bytes仍需核对 |

ABZ两路定时器计数相互独立；Z只承诺GPIO中断，不承诺硬件自动清零计数器。两路SPI继续独立，不共用SCK/MISO/MOSI。两路I²C使用独立硬件总线，分别开漏输出、按各自负载配置3.3V上拉；初始化关闭PB6编码器和PA9/I2C2脚上不使用的UCPD dead-battery下拉行为。

完整分配见 [100个物理脚CSV（含电源与空闲脚）](controller_LQFP100_all_pins.csv)、[63项功能分配CSV](controller_dual_pwm_pin_plan.csv)、[两口16针CSV](controller_dual_pwm_ports.csv)和 [结构化规划](controller_dual_pwm_pin_plan.json)。LQFP100共有86个信号/专用pad（已包含NRST/HSE/BOOT/SWD），另14个电源/参考/地；62个规划功能引脚，加1个第二制动预留，共63个，剩23个未分配pad。未分配脚中有8个具备ADC能力，但未增加对应模拟端子；这23个空闲脚当前也未单独设置GPIO扩展连接器。该计数与物理pin映射、无重复分配已交叉检查，不是ERC/PCB验证。

14个电源/参考/地逐脚为：VBAT=6；VSSA=35、VREF+=36、VDDA=37；VDD=24/49/64/75/100；VSS=23/48/63/74/99。规划VBAT和VDD接本地3.3V，VDDA/VREF沿用独立滤波/旁路角色，VSSA/VSS按受控回流接地；五组VDD/VSS均须重新安排本地去耦。完整封装更新不能只迁移功能信号而漏掉新增电源脚。

VBT6在共享库中尚未建立。[国内立创C529359商品入口](https://item.szlcsc.com/549637.html)的型号及商品ID已核对，国内库存未核实。换型前需建立完整100脚物料、核对封装和新增电源去耦，不能将64脚符号改名使用。14×14mm本体在60×60mm板内具有几何空间，具体布线与连接器布局仍待新PCB验证。

10个模拟端子统一命名ADC01～ADC10，每个2P：采样信号和GND；用户已接受讯普GH1.25 2P推荐，物理针序与专用封装仍待核对。前六路选择都能连接ADC1/ADC2的pad，方便两套电流采样的窗口规划。下面按四种**替代用途假设分配**，不是固定端子功能、传感器电路定稿或ADC转换序列；各模式需匹配功率板前端量程、参考点与滤波。完整GPIO/ADC映射仍见引脚CSV，模式对照可直接查看 [模拟口用途CSV](controller_ADC_mode_examples.csv)。

| 模拟端子 | GPIO | 单电机示例 | 双电机示例 | 普通Boost示例 | Vienna示例 |
| --- | --- | --- | --- | --- | --- |
| ADC01 | PC0 | U相电流 | A电机U电流 | 电感电流 | L1电流 |
| ADC02 | PC1 | V相电流 | A电机V电流 | 备用 | L2电流 |
| ADC03 | PC2 | W相电流 | A电机W电流 | 备用 | L3电流 |
| ADC04 | PC3 | U相电压 | B电机U电流 | 整流后输入电压 | 输入相1电压 |
| ADC05 | PA0 | V相电压 | B电机V电流 | 备用 | 输入相2电压 |
| ADC06 | PA1 | W相电压 | B电机W电流 | 备用 | 输入相3电压 |
| ADC07 | PA4 | 母线电压 | A母线电压 | 输出电压 | 上半母线电压 |
| ADC08 | PB0 | 备用 | B母线电压 | 备用 | 下半母线电压 |
| ADC09 | PB1 | 功率板NTC | A功率板NTC | 功率板NTC | 功率板NTC |
| ADC10 | PB2 | 备用 | B功率板NTC | 备用 | 备用 |
| 已用/剩余 | — | 8/2 | 10/0 | 4/6 | 9/1 |

单电机的ADC08以后可考虑输入母线电流，ADC10可考虑电机NTC，但都需要新增匹配的前端，不视为现有传感器。单电机三相电压沿用当前inverter的PWM相节点测量含义，不称作滤波后正弦输出；若以后增加输出滤波器，采样点需重新决定。Vienna上下半母线是两段母线电容电压的调理结果，不能为了采样而把物理中点直接接成controller地。Boost的实际输入采样点随整流/功率级拓扑确定。

各口接功率板前端已调理的低压电压信号，不直接接母线、相线、分流器两端或裸NTC。PC4、PC5、PA2、PA3、PB11、PB12、PB14、PB15仍是有ADC能力的未分配MCU脚，没有对应模拟端子；可留给后续改版，但不能计入本版10口的线束能力。

**10口容量边界**按电机/PFC应用互斥、每种模式单独分配端子估算；表中数量均包含相应温度通道，不叠加电机＋PFC需求：

| 独立应用模式 | 模拟输入需求 | 10口是否够 |
| --- | --- | --- |
| 单电机，3电流＋母线＋3相电压＋NTC | 8 | 够，余2 |
| 双电机，各3电流＋母线＋NTC | 10 | 刚好，无余量，不含相电压 |
| 普通单相Boost PFC | 4 | 够，余6 |
| Vienna PFC | 9 | 够，余1 |
| 双电机，各再加三相电压 | 16 | 本版10口不覆盖这套测量配置 |

普通Boost的4路预算为电感电流、输入电压、输出电压和NTC。Vienna的9路预算为3电流、3输入电压、2半母线电压和NTC；前8项可对照 [TI Vienna参考设计](https://www.ti.com/lit/ug/tiducj0g/tiducj0g.pdf)，NTC为本项目额外温度预算。按已确认的互斥模式，**保留10个独立模拟端子即可**；之前电机＋Vienna叠加得到14/17路的扩容条件已不属于本controller需求。模拟前端量程、ADC时序及所选功率级控制仍需单独设计验证。

ADC端子不区分常规专用或注入专用：转换组与序列位置由软件选择，但GPIO通向哪颗ADC及哪一个模拟通道由芯片固定。前六路均有ADC1/ADC2接入能力；后四路分别固定为PA4→ADC2_IN17、PB0→ADC1_IN15、PB1→ADC1_IN12、PB2→ADC2_IN12。每颗ADC的注入序列最多4个转换位置，并不增加转换器数量；G431仅两颗ADC，三相电流不能因为都进入注入组就获得三路同一时刻的独立同步采样。具体触发、序列与有效窗口仍待规划。依据 [DS12589表12](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf)及 [RM0440第21.4.11节](https://www.st.com/resource/en/reference_manual/rm0440-stm32g4-series-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)。

此前的**单块inverter线束示例**：按ADC每路2P、CTRL6P及5V供电2P计算，PWM8P＋8×ADC2P＋CTRL6P＋供电2P共32根线，包含19路功能信号、1根5V和12根分组GND。它不是本次两个功率口的完整线数预算，两板使用的ADC数量及辅助供电方式还要另配。此示例以接收端ADC滤波/钳位、状态上拉保护和SWD迁到controller、取消跨板3V3_CORE_REF为前提；保护位置尚未落图。若以后选3P传感器口，第三脚电源及其预算另定。

机器可读讨论记录为 [terminal_interface_plan.json](terminal_interface_plan.json)；ST规格书原件及哈希保存在 [双PWM规划来源](../reference/ST_G431_dual_pwm/sources.json)。本次只更新规划与核对记录，下文Rev E电气/机械合同、RBT6原理图及PCB保持原样。

**信号连接器推荐方案**：采用国产讯普GH1.25卧贴系列，ADC每口建议2P（信号＋GND），PWM用同系列8P。用户已接受ADC2P/PWM8P及该系列推荐，但尚未接入原生BOM；物理针序、插合面图及其余针数的完整采购型号仍待核对。配套与来源记录见 [连接器候选清单](controller_signal_connector_candidates.json)。

| 用途 | 型号 | 国内立创 |
| --- | --- | --- |
| ADC板端2P | WAFER-GH1.25-2PWB | [C3029377](https://item.szlcsc.com/3561389.html) |
| ADC线端2P胶壳 | WAFER-GH1.25-2PJK | [C5360417](https://item.szlcsc.com/6178093.html) |
| 线端压接端子 | WAFER-GH1.25-DZ | [C5360426](https://item.szlcsc.com/6178102.html) |
| PWM板端8P | WAFER-GH1.25-8PWB | [C3029383](https://item.szlcsc.com/3561395.html) |

2P板座本体约5.75×5mm、高4.35mm，8P约13.25×5mm、高4.35mm；2P配套胶壳商品资料明确带锁扣，板座页面明确同系列胶壳及DZ端子配套。DZ端子标AWG28～32，建议先选28AWG正确压接的信号/GND线对。10个ADC口建议沿两条板边分为两组、每组5个，预留插头、锁扣操作、线缆弯折和支柱空间；两块60×60板的实际布局仍须检查。8P配套胶壳型号已识别，完整采购条目待继续补齐；不同厂商GH件不默认互插。以上型号目前未在共享库命中，板座仍需补符号/专用封装；线端胶壳、压接件另记入线束物料。未核实实时库存或价格，辅助供电和功率端子另行选型。

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

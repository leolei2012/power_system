# Controller 和 Inverter 器件建库清单

2026-11-05 架构变更：用户确定控制、驱动与逆变功率级合板，MCU 改为 **STM32G431**。当前依据见 [合板方案](integrated_board.md)。本文下方 LKS、独立 controller、24 脚板间接口及旧引脚/软件预算属于上一版记录；旧 KiCad/BOM/检查结果不代表新合板版本已完成。已确定每板一颗 MCU，分变频板与电源板，取消单 MCU 同时控制两路逆变和 PFC。LLC 在电源板恢复讨论，具体配置、接口和 MCU 完整后缀待评估。


2026-11-01 原理图交付时复核公共库：本清单 19 种中 18 种已为 reviewed（包含 UCC27517、NCC 电解、国巨旁路），IRFS4227 尚待公共入库。下文早期“新增三种待建库”记录由此更新取代；详细符号/封装见 CSV。inverter 新增候选 D1、D2、小信号管、分流及未定电感/连接器见实际 BOM，不包含在这 19 种历史清单内。


更新：2026-11-01。按 12～24 V 适配器进入 inverter、inverter 输出 5 V 给 controller 的供电结构选型。功率母线另接实验电源或自研直流模块。当前共列 19 种选型，MCU 已有库物料，不重复列入。其中原有 15 种已有 reviewed 库物料，新增贴片 MOS、制动驱动 UCC27517DBVR、母线电解 EKYB101ELL221MK25S 与国巨旁路 CS1210KKX7R0BB225 待建库；整板额定与保护电路仍需详细设计。

[建库 CSV](library_build_list.csv)包含完整后缀、厂家、封装、立创编号、商品页、原厂资料和数量参考。它记录当前物料和建库状态，数量不是采购数量；两块 inverter 使用同一种器件库物料。

通用贴片电阻和小电容统一 **YAGEO（国巨）**，按实际阻容值、精度、耐压/功率和封装选完整型号；常规去耦、滤波、上下拉等按此执行。采样分流、功率/制动电阻、母线大电解仍专项选型。此前村田高频旁路候选改为下表国巨型号，不修改或删除公共库已有物料。

## 辅助供电器件

| 功能与位置 | 完整型号 | 封装 | 立创商品 | 数量参考 |
| --- | --- | --- | --- | --- |
| inverter 辅助输入防反接、限流、过欠压切断 | TI TPS26600PWPR | HTSSOP-16-EP | [C544399](https://item.szlcsc.com/565050.html) | 每个独立辅助入口 1 |
| inverter 12～24 V 升降压到驱动 12 V | TI TPS55165QPWPRQ1 | HTSSOP-20-EP | [C2071629](https://item.szlcsc.com/2163212.html) | 每块 inverter 1 |
| inverter 辅助输入降压到 5 V | Diodes AP63205WU-7 | TSOT-23-6 | [C2071056](https://item.szlcsc.com/2162639.html) | 每块 inverter 1 |
| inverter 5 V 到采样及保护 3.3 V | TI TPS7A2033PDBVR | SOT-23-5 | [C2862740](https://item.szlcsc.com/3067417.html) | 每块 inverter 1 |
| inverter 到 controller 的 5 V 输出限流 | TI TPS2553QDBVRQ1 | SOT-23-6 | [C130055](https://item.szlcsc.com/141342.html) | 指定供电的 inverter 1 |
| controller 5 V 到 MCU 及逻辑 3.3 V | TI TLV76733DRVR | WSON-6，2×2 mm，散热焊盘 | [C2848334](https://item.szlcsc.com/3046559.html) | 每块 controller 1 |
| 3.3 V 监控及复位或硬件供电许可 | TI TPS3808G33DBVR | SOT-23-6 | [C43698](https://item.szlcsc.com/44691.html) | controller 1；每块 inverter 另预留 1 |

选两种 3.3 V LDO 是为了分别覆盖模拟低噪声负载和控制板较大的负载预算。1.65 V 沿用下表 TLV9001 分压缓冲，不增加第四种稳压器。

### 输入保护与转换器的配合

[TPS26600 规格书 Rev G](https://www.ti.com/lit/gpn/TPS2660)给出 4.2～60 V 输入、0.1～2.23 A 可调限流与可调过压切断。选择的是 TPS26600，不是固定约 38 V 钳位的 TPS26602。它只保护辅助电源入口，不能代替功率母线熔断器。限流故障模式按硬件封锁需求接线，不直接采用未审查的默认自动重试。

[AP63205 规格书 Rev 3-2](https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf)给出 3.8～32 V 输入、固定 5 V、2 A 器件额定。建议以 5 V 总负载 1 A 作为首轮设计预算，并核对散热。辅助过压切断初步研究 27～28 V，最终值应计入适配器容差、阈值误差、切断延迟和尖峰。TVS 的标称工作电压不等于钳位电压，不能用约 45 V 钳位直接证明 32 V 输入转换器得到保护。

### 12 V 驱动电源

[TPS55165-Q1 规格书 Rev A](https://www.ti.com/lit/ds/symlink/tps55165-q1.pdf)的 12 V 配置为 VOS_FB 接 VREG、VOUT_SENSE 检测输出。正常模式下，9.2～14 V 输入对应 600 mA 输出能力，14 V 以上为 800 mA，条件包含电感 DCR 不大于 40 mΩ。因此本项目 12～24 V 输入不能按商城标题的“1 A”预算 12 V 输出。

首轮按 12 V / 0.25 A 预算门极驱动及附加负载，需计入制动驱动后复核；首版已取消功率母线预充继电器，不计其线圈负载。4.7 µH 电感只作为计算起点，具体型号须同时满足 DCR、峰值/饱和电流与温升。IGN、IGN_PWRL、PS 的启动接法应让适配器上电后能够独立启动，不能依赖尚未上电的 MCU。12 V 模式的 PG 上拉按手册接合适的低压轨，不上拉到 12 V。

### 两块板的 3.3 V 与板间供电

[TPS7A20 规格书 Rev H](https://www.ti.com/lit/ds/symlink/tps7a20.pdf)用于 inverter 的 5 V 到 3.3 V，器件输入上限 6 V、输出能力 300 mA，不接 12～24 V。模拟及保护负载首轮以 30 mA 估算，最后按放大器、比较器与逻辑实际负载复核。

[TLV767 规格书 Rev D](https://www.ti.com/lit/ds/symlink/tlv767.pdf)用于 controller 的 5 V 到 3.3 V，器件额定 1 A。首轮按 0.25 A 控制板负载预算，LDO 损耗约 0.425 W；1 A 时约 1.7 W，不能将芯片额定直接写成整板持续能力。板间 5 V 压降也要满足 LDO 压差要求。

[TPS2553-Q1 规格书 Rev B](https://www.ti.com/lit/ds/symlink/tps2553-q1.pdf)用于 5 V 输出限流与反向电压保护，工作输入 2.5～6.5 V。初步研究 controller 分支 0.5 A 预算，限流电阻要兼顾容差和启动充电。选用高电平 EN 的 Q1 完整后缀，不以带 -1 的其他锁断型号直接替换。该器件虽然常用于 USB 配电，本项目只用其供电保护功能，控制板不增加 USB。

controller 的电源许可来自辅助供电条件，不随电机 ENABLE 关闭。双 inverter 初版只选一路给 controller 供电，不把两路稳压输出直接并联；TPS2553 也不作为完整双路电源选择器使用。5 V 与 GND 走独立电源接插件，24 脚口仍用于信号。

[TPS3808 规格书 Rev N](https://www.ti.com/lit/ds/symlink/tps3808.pdf)中 G33 的监测阈值为约 3.07 V，输出为开漏。controller 可用于 MCU NRST；inverter 可参与供电正常条件的判定。后者不新增接口 RESET_N，也不能单靠 3.3 V 监控器证明 12 V 驱动已正常。掉电时封锁默认态、12 V 欠压、MCU 最低工作电压与复位门限须联合审查。

## 功率桥与采样保护器件

| 功能 | 完整型号 | 封装 | 立创记录 | 每块 inverter 数量参考 |
| --- | --- | --- | --- | --- |
| 主桥及制动候选 200 V MOSFET | Infineon IRFS4227TRLPBF | TO-263 / D²PAK | C146578（国内商品页待核） | 每块 inverter 主桥 6＋制动候选 1；制动额定待核算 |
| 母线电解（首版暂用） | NCC EKYB101ELL221MK25S | 直插 D12.5×L25 mm，P5 mm | [C1585673](https://item.szlcsc.com/1676488.html) | 每块 2；220 µF/100 V 并联共 440 µF，两板合计 4；纹波/温升待验证 |
| 母线高频旁路 | YAGEO CS1210KKX7R0BB225 | 1210 / 3225，软端头 MLCC | [C5578983](https://item.szlcsc.com/6497372.html) | 每块 2；2.2 µF/100 V/±10%/X7R，两板合计 4；偏压/纹波待核 |
| 半桥栅极驱动 | Infineon 2ED2182S06FXUMA1 | PG-DSO-8 | [C1850289](https://item.szlcsc.com/1941102.html) | 3 |
| 制动低侧栅极驱动 | TI UCC27517DBVR | SOT-23-5 | [C99395](https://item.szlcsc.com/100609.html) | 1；两块合计 2，接稳压 12 V，BRAKE 3.3 V 高有效、默认下拉 |
| 低端电流采样，增益 10 | TI INA241A1IDDFR | SOT-23-8 | [C19712054](https://item.szlcsc.com/21022225.html) | 3 |
| 1.65 V 采样偏置缓冲 | TI TLV9001IDCKR | SC-70-5 | [C398362](https://item.szlcsc.com/380592.html) | 1 |
| 正负过流窗口及母线过压 | TI TLV3202AIDGK | VSSOP-8 | [C182416](https://item.szlcsc.com/193816.html) | 4，提供 8 个比较通道 |
| PWM 封锁及故障汇总与门 | Nexperia 74LVC08APW,118 | TSSOP-14 | [C6053](https://item.szlcsc.com/6519.html) | 六路 PWM 至少 2，汇总逻辑另计 |
| 故障锁存 | Nexperia 74LVC74AD,118 | SOIC-14 | [C6099](https://item.szlcsc.com/6565.html) | 1 起，随逻辑设计 |
| 故障逻辑反相及与非组合候选 | Nexperia 74LVC00APW,118 | TSSOP-14 | [C6045](https://item.szlcsc.com/6511.html) | 先预留 1，数量待逻辑审查 |

功率与采样器件的额定值和供电依据见 [inverter 首轮评估](../inverter/docs/component_selection.md)。[2ED2182 原厂规格书 V2.32](https://www.infineon.com/assets/row/public/documents/24/49/infineon-2ed2182-4-s06f-j-datasheet-en.pdf)已取得，可按完整型号核对符号与封装；国内商品页 [C1850289](https://item.szlcsc.com/1941102.html)已由商城搜索结果补核。

[74LVC00A 原厂规格书](https://assets.nexperia.com/documents/data-sheet/74LVC00A.pdf)对应新增的四路与非门。保护逻辑需满足活动故障优先于清锁存、ENABLE 上电默认无效、故障消除后不自动重启；74LVC74 的异步置位与清零不能同时有效。比较器为推挽输出，不得直接线与。FAULT_N 的开漏输出级和失电状态仍要设计，不能认为列出逻辑门后保护已闭环。

## Controller 通信预留器件

CAN 可先建 TI **SN65HVD232DR**，SOIC-8，[C30530](https://item.szlcsc.com/31287.html)，每块 controller 预留 1。它使用 3.3 V，支持经典 CAN 至 1 Mbps，5、8 脚为 NC，无需额外待机 GPIO；不提供总线隔离。[原厂规格书 Rev O](https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf)

CAN 的端接、接口防护与隔离边界随接口原理图确定。当前编码器物理电平尚未确定，不先选差分接收器；TTL 串口和 SWD 本身无需为建库增加收发器。

## 需要参数后再选完整型号的器件

| 项目 | 定型所需条件 |
| --- | --- |
| 两个开关电源的电感及电容 | 输入角点、纹波、峰值电流、饱和、DCR、直流偏压下有效容量及温升；不能只按标称 4.7 µH 建库 |
| 辅助输入 TVS、保险和接插件 | 适配器最大正常电压、浪涌能量、eFuse 耐压、下游 32/36 V 输入限制及反接工况 |
| 母线旁路、吸收/钳位、主熔断器 | 母线电解首版已选上表 2×220 µF/100 V，纹波/热验证保留；旁路与吸收/钳位按实际过冲设计，旧 150 V 工作电压 TVS 最大钳位约 243 V，不能默认保护 200 V MOSFET |
| 电流分流器 | 电流、Kelvin 布局、脉冲能量、散热与完整型号；首版功率母线预充/专用放电已取消，不再列预充电阻及旁路继电器 |
| 制动驱动外围及功率电阻、输出 LC | 驱动已选 UCC27517DBVR；仍需驱动去耦/栅极阻容、电阻阻值/功率/能量、负载和滤波模式 |
| 24 脚及编码器/SPI/电源连接器、NTC、晶振 | 排线结构与方向、接口电平和供电、安装方式、温度范围、时钟频率和负载 |

通用电阻、去耦与自举电容随原理图计算后补齐。上述项目不使用不完整型号冒充已选物料。

## 建库交付要求

按 kicad_library 的既有流程建立物料：用完整订货后缀匹配原厂引脚图、封装尺寸和散热焊盘，记录规格书版本、厂家与立创来源；优先复用经核对的 KiCad 官方符号/封装。SC-70、SOT-23、VSSOP、SOIC 及带散热焊盘的不同封装不可互换。

当前清单中原有 15 种取得国内商品页并已有 reviewed 库物料；新增贴片 MOS 待建库且国内商品页待补核；制动驱动 UCC27517DBVR（C99395）与母线电解 EKYB101ELL221MK25S（C1585673）的国内型号/封装记录和原厂资料已核对，库定义待建。国巨旁路 CS1210KKX7R0BB225（C5578983）已列入清单、库定义待建，偏压/纹波仍需验证。价格与库存未取得可核实记录。旧直插 IRFB4227PBF 保留在公共库中，当前工程不再使用其封装。reviewed 的范围是库定义核对，无实物装配验证。原理图交接仍以 [设计交接记录](schematic_handoff.md)为准。

原理图绘制可按 [任务书](schematic_agent_task.md)开始，新增贴片 MOS、制动驱动、母线电解及国巨旁路未建库期间先推进其他已确认部分。

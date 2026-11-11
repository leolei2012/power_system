# LKS32MC451VCT8 引脚规划草案 A

2026-11-05 架构变更：用户确定控制、驱动与逆变功率级合板，MCU 改为 **STM32G431**。当前依据见 [合板方案](../../docs/integrated_board.md)。本文下方 LKS、独立 controller、24 脚板间接口及旧引脚/软件预算属于上一版记录；旧 KiCad/BOM/检查结果不代表新合板版本已完成。已确定每板一颗 MCU，分变频板与电源板，取消单 MCU 同时控制两路逆变和 PFC。LLC 在电源板恢复讨论，具体配置、接口和 MCU 完整后缀待评估。


日期：2026-10-31。目标：一颗 MCU 同时控制两路三相变频与一路 PFC；PFC 为 Boost / Vienna 二选一。保留两路 A/B/Z、两路独立 SPI、两路制动、TTL、CAN 和 SWD。LLC、USB、霍尔不在当前范围。

本表已完成实际 LQFP100 脚号、GPIO 和复用功能的静态核对，没有重复分配物理引脚或外设输出。**这仍是规划草案，尚未验证 PFC PWM 时序、三套控制的 ADC 采样窗口、固件实时性能及上电行为，不作为直接制板依据。** 本轮只编写分配文档和 CSV，未修改器件库，也未创建应用原理图。

## 资料与核对范围

- 库内规格书：`D:/workspace/kicad_library/datasheets/LINKOSEMI_LKS32MC451VCT8_DS_v1.71.pdf`，图 3-1、表 3-1、表 3-2（印刷页 24–28，PDF 第 25–29 页）与第 25 章特殊 IO 复用。官网原文：[Datasheet v1.71](https://sjk.lksmcu.com/static/upload/file/20230113/LKS32MC45x_Datasheet_v1.71.pdf)。
- [库内 100 脚对照表](../../../kicad_library/docs/parts/LKS32MC451VCT8_pins.csv)与 `MyParts:LKS32MC451VCT8` 符号：核对封装编号、GPIO、符号名称和单元。
- [User Manual v1.98](https://sjk.lksmcu.com/static/upload/file/20230113/LKS32MC45x_User_Manual_v1.98.pdf)：SYS_IO_CFG、ADC 信号来源/触发、UTimer/QEP、MCPWM 时基与 FAIL 分组。核对用本地副本位于系统临时目录，不纳入工程依赖。
- [完整 100 脚 CSV](../hardware/LKS32MC451VCT8_pin_plan.csv)：按封装脚号排序，包含电源、地、NC、保留脚、网络名、接口位置与符号单元。

规格书表 3-1 末尾的特殊 IO 提示将 P0.10 误写成 P1.0；本表按图 3-1、表 3-2、第 25 章和用户手册的一致定义采用 P0.9～P0.13 为调试组，不把该处文字用于重新编号。

## 外设分工

| 资源 | 分工 | 约束 |
| --- | --- | --- |
| MCPWM0 CH0/1/2，时基 0 | 变频 1 六路 PWM | 死区、采样触发、FAIL012 硬件关断 |
| MCPWM1 CH0/1/2，时基 0 | 变频 2 六路 PWM | 与变频 1 独立的周期及保护 |
| MCPWM0 CH3P，时基 1 | BRAKE_1 | 只引出 P 输出；与电机 ENABLE 分开处理 |
| MCPWM1 CH3P，时基 1 | BRAKE_2 | 只引出 P 输出；不以电机停机代替制动保护 |
| Timer0 CH0/1 | PFC A1/A2 | 两路比较输出，不自动具有半桥互补/死区功能 |
| Timer1 CH0/1 | PFC B1/B2 | 与 Timer0/4 的同步及更新须验证 |
| Timer4 CH0/1 | PFC C1/C2 | 与 Timer0/1 的同步及更新须验证 |
| QEP2 / QEP3，Timer2/3 输入脚 | 编码器 1 / 2 | 各含 A/B/Z；不与 PFC 输出共享输入引脚 |
| SPI0 / SPI1 | SPI_A / SPI_B | 各 3 根硬件信号加 1 根 GPIO 片选 |
| UART0 / CAN | TTL / CAN 收发器 | CANH/CANL 在收发器侧 |

## 引脚占用与余量

| 项目 | 数量 |
| --- | ---: |
| 功能信号（含 6 路 PFC 命令及 SWDIO/SWCLK） | 72 |
| MCU 复位 | 1 |
| 外部晶振 | 2 |
| 可编程指示灯（建议，未冻结） | 4 |
| 额外保留的调试组引脚 | 3 |
| REF/LDO12 模拟测试预留（本草案选择） | 2 |
| GPIO 合计 | 84 |
| 电源和地 | 12 |
| NC | 4 |
| 封装合计 | 100 |

79 只 GPIO 已分配用途，另外 5 只明确保留；本草案没有未分配的通用 GPIO。REF/LDO12 两只不是强制电源脚，是本方案为模拟测试留出的可调整位置。若 Vienna 最终只需三路独立门极命令，可以释放 A2/B2/C2 三脚；也可以取消某个可编程灯释放 GPIO。BOARD_ID、CAN 待机控制、SPI 额外中断、制动故障/温度尚无独立分配，新增前须重新安排。

电源灯直接接电源，不占 GPIO。SPI 片选采用 GPIO 控制，不能因该脚存在 SPI_CS 别名就按硬件自动片选初始化。

## 两路变频

接口顺序沿用 [24 脚接口定义](connector.md)。GND 为 3/6/9/13，AGND 为 17/21，第 12/24 脚预留且不接 MCU。

### 变频 1：J_INV1

| 信号 | 封装脚 | GPIO | 外设功能 | 复用 | 连接位置 |
| --- | --- | --- | --- | --- | --- |
| INV1_PWM_UH | 24 | P1_2 | MCPWM0_CH0P | AF3 | J_INV1.1 |
| INV1_PWM_UL | 56 | P2_14 | MCPWM0_CH0N | AF3 | J_INV1.2 |
| INV1_PWM_VH | 26 | P1_4 | MCPWM0_CH1P | AF3 | J_INV1.4 |
| INV1_PWM_VL | 25 | P1_3 | MCPWM0_CH1N | AF3 | J_INV1.5 |
| INV1_PWM_WH | 83 | P4_4 | MCPWM0_CH2P | AF3 | J_INV1.7 |
| INV1_PWM_WL | 27 | P1_5 | MCPWM0_CH2N | AF3 | J_INV1.8 |
| INV1_ENABLE | 1 | P0_0 | GPIO | AF0 | J_INV1.10 |
| INV1_FAULT_N | 57 | P2_15 | MCPWM0_BKIN0 | AF3 | J_INV1.11 |
| INV1_I_U | 58 | P3_0 | ADC0_CH14 | AF0 | J_INV1.14 |
| INV1_I_V | 63 | P3_3 | ADC1_CH13 | AF0 | J_INV1.15 |
| INV1_I_W | 8 | P0_4 | ADC2_CH13 | AF0 | J_INV1.16 |
| INV1_V_DC | 84 | P4_5 | ADC0_CH11 | AF0 | J_INV1.18 |
| INV1_V_U | 96 | P4_13 | ADC0_CH10 | AF0 | J_INV1.19 |
| INV1_V_V | 80 | P4_1 | ADC1_CH10 | AF0 | J_INV1.20 |
| INV1_V_W | 68 | P3_8 | ADC2_CH10 | AF0 | J_INV1.22 |
| INV1_TEMP_NTC | 69 | P3_9 | ADC2_CH9 | AF0 | J_INV1.23 |

### 变频 2：J_INV2

| 信号 | 封装脚 | GPIO | 外设功能 | 复用 | 连接位置 |
| --- | --- | --- | --- | --- | --- |
| INV2_PWM_UH | 47 | P2_5 | MCPWM1_CH0P | AF3 | J_INV2.1 |
| INV2_PWM_UL | 50 | P2_8 | MCPWM1_CH0N | AF3 | J_INV2.2 |
| INV2_PWM_VH | 46 | P2_4 | MCPWM1_CH1P | AF3 | J_INV2.4 |
| INV2_PWM_VL | 49 | P2_7 | MCPWM1_CH1N | AF3 | J_INV2.5 |
| INV2_PWM_WH | 45 | P2_3 | MCPWM1_CH2P | AF3 | J_INV2.7 |
| INV2_PWM_WL | 48 | P2_6 | MCPWM1_CH2N | AF3 | J_INV2.8 |
| INV2_ENABLE | 3 | P5_2 | GPIO | AF0 | J_INV2.10 |
| INV2_FAULT_N | 43 | P2_2 | MCPWM1_BKIN0 | AF3 | J_INV2.11 |
| INV2_I_U | 59 | P3_1 | ADC0_CH13 | AF0 | J_INV2.14 |
| INV2_I_V | 64 | P3_4 | ADC1_CH12 | AF0 | J_INV2.15 |
| INV2_I_W | 9 | P0_5 | ADC2_CH12 | AF0 | J_INV2.16 |
| INV2_V_DC | 97 | P4_14 | ADC0_CH9 | AF0 | J_INV2.18 |
| INV2_V_U | 98 | P4_15 | ADC0_CH8 | AF0 | J_INV2.19 |
| INV2_V_V | 81 | P4_2 | ADC1_CH9 | AF0 | J_INV2.20 |
| INV2_V_W | 70 | P3_10 | ADC2_CH8 | AF0 | J_INV2.22 |
| INV2_TEMP_NTC | 75 | P3_12 | ADC2_CH6 | AF0 | J_INV2.23 |

UH/UL、VH/VL、WH/WL 分别为对应 MCPWM 通道的 P/N 输出。PWM 安全极性由驱动级确定，不能只按 P/N 名称判断电平；ENABLE 外部下拉，功率板自行执行硬件封锁。

INV1_FAULT_N 接 MCPWM0_BKIN0，INV2_FAULT_N 接 MCPWM1_BKIN0，按低有效配置 FAIL012。用户手册明确 FAIL012 与 FAIL3 分别控制 CH0/1/2 和 CH3，因此制动通道可单独规划保护；本草案尚未增加独立的制动 FAULT 引脚。功率板本地关断仍必须先于软件处理。

## PFC 专用口：J_PFC

| 信号 | 封装脚 | GPIO | 外设功能 | 复用 | 连接位置 |
| --- | --- | --- | --- | --- | --- |
| PFC_PWM_A1 | 78 | P3_15 | TIM0_CH0 | AF7 | J_PFC.1 |
| PFC_PWM_A2 | 35 | P1_11 | TIM0_CH1 | AF7 | J_PFC.2 |
| PFC_PWM_B1 | 40 | P2_0 | TIM1_CH0 | AF7 | J_PFC.4 |
| PFC_PWM_B2 | 66 | P3_6 | TIM1_CH1 | AF7 | J_PFC.5 |
| PFC_PWM_C1 | 52 | P2_10 | TIM4_CH0 | AF7 | J_PFC.7 |
| PFC_PWM_C2 | 54 | P2_12 | TIM4_CH1 | AF7 | J_PFC.8 |
| PFC_ENABLE | 6 | P5_3 | GPIO | AF0 | J_PFC.10 |
| PFC_FAULT_N | 41 | P2_1 | GPIO | AF0 | J_PFC.11 |
| PFC_V_BUS_LOWER | 99 | P5_0 | ADC0_CH7 | AF0 | J_PFC.12 |
| PFC_I_A | 91 | P4_12 | ADC0_CH12 | AF0 | J_PFC.14 |
| PFC_I_B | 65 | P3_5 | ADC1_CH11 | AF0 | J_PFC.15 |
| PFC_I_C | 67 | P3_7 | ADC2_CH11 | AF0 | J_PFC.16 |
| PFC_V_BUS_UPPER | 100 | P5_1 | ADC0_CH6 | AF0 | J_PFC.18 |
| PFC_V_A | 86 | P4_7 | ADC1_CH7 | AF0 | J_PFC.19 |
| PFC_V_B | 87 | P4_8 | ADC1_CH6 | AF0 | J_PFC.20 |
| PFC_V_C | 76 | P3_13 | ADC2_CH5 | AF0 | J_PFC.22 |
| PFC_TEMP_NTC | 77 | P3_14 | ADC2_CH4 | AF0 | J_PFC.23 |
| PFC_PRECHARGE | 36 | P1_12 | GPIO | AF0 | J_PFC.24 |

GND/AGND 位置与变频口相同，但不承诺插接电机功率板。单路 Boost 使用 A1、I_A、V_BUS_UPPER、V_A、TEMP_NTC 和 ENABLE/FAULT/PRECHARGE，其余按板型停用；Boost 的 V_BUS_UPPER 网络在该板型解释为完整 V_DC。Vienna 使用上下半母线反馈，两路反馈均须调理到控制地参考的 ADC 输入，母线中点不能直接接控制地。

这里按六路独立门极命令的上限分配，每相占同一 Timer 的 CH0/CH1。Vienna 每相是否两路同波形、三路总命令由板上分发，或确实需要独立六路，须随开关连接与栅极驱动确定；不把这六路自动配置为电机互补 PWM。

PFC_FAULT_N 接 P2_1，具有 EXTI14 输入能力，供状态上报；通用 Timer 没有在本表中落实 MCPWM 式的专用 BKIN 保护。PFC 功率板必须在本地把故障、ENABLE 和门极命令组合成不依赖 CPU 的关断路径。PRECHARGE 暂按高有效、上电下拉安排，最终随预充电路冻结。

## 编码器、SPI、通信、制动与指示灯

| 信号 | 封装脚 | GPIO | 外设功能 | 复用 | 连接位置 |
| --- | --- | --- | --- | --- | --- |
| ENC1_A | 38 | P1_14 | TIM2_CH0 | AF8 | J_ENC1.A |
| ENC1_B | 39 | P1_15 | TIM2_CH1 | AF8 | J_ENC1.B |
| ENC1_Z | 51 | P2_9 | TIM2_Z | AF8 | J_ENC1.Z |
| ENC2_A | 89 | P4_10 | TIM3_CH0 | AF8 | J_ENC2.A |
| ENC2_B | 88 | P4_9 | TIM3_CH1 | AF8 | J_ENC2.B |
| ENC2_Z | 90 | P4_11 | TIM3_Z | AF8 | J_ENC2.Z |
| SPI_A_CS_N | 2 | P0_1 | GPIO | AF0 | J_SPI_A.CS_N |
| SPI_A_MISO | 7 | P0_3 | SPI0_DI | AF5 | J_SPI_A.MISO |
| SPI_A_MOSI | 28 | P1_6 | SPI0_DO | AF5 | J_SPI_A.MOSI |
| SPI_A_SCK | 37 | P1_13 | SPI0_CLK | AF5 | J_SPI_A.SCK |
| SPI_B_CS_N | 30 | P1_7 | GPIO | AF0 | J_SPI_B.CS_N |
| SPI_B_MISO | 34 | P1_10 | SPI1_DI | AF5 | J_SPI_B.MISO |
| SPI_B_MOSI | 33 | P1_9 | SPI1_DO | AF5 | J_SPI_B.MOSI |
| SPI_B_SCK | 23 | P1_1 | SPI1_CLK | AF5 | J_SPI_B.SCK |
| UART_RX | 53 | P2_11 | UART0_RXD | AF4 | J_UART.2 |
| UART_TX | 4 | P0_2 | UART0_TXD | AF4 | J_UART.1 |
| CAN_RX | 20 | P0_14 | CAN_RX | AFA | U_CAN.RXD |
| CAN_TX | 82 | P4_3 | CAN_TX | AFA | U_CAN.TXD |
| BRAKE_1 | 32 | P1_8 | MCPWM0_CH3P | AF3 | J_BRAKE1.CTRL |
| BRAKE_2 | 22 | P1_0 | MCPWM1_CH3P | AF3 | J_BRAKE2.CTRL |
| LED_COMM | 79 | P4_0 | GPIO | AF0 | ONBOARD |
| LED_FAULT | 61 | P3_2 | GPIO | AF0 | ONBOARD |
| LED_RUN1 | 21 | P0_15 | GPIO | AF0 | ONBOARD |
| LED_RUN2 | 55 | P2_13 | GPIO | AF0 | ONBOARD |

编码器 1 使用 QEP2，编码器 2 使用 QEP3；TIM2/3_CH0/CH1/Z 是硬件编码器输入，不是软件逐沿计数。需使能对应 Timer 时钟、输入和滤波。A/B 方向在固件中校准，Z 索引处理随编码器定义。这里分配 MCU 侧信号，传感器供电、差分接收器和接插件总脚数仍待定。

BRAKE_1/2 仅为栅极驱动之前的控制信号；CH3N 不引出，也不允许固件把占用这些 GPIO 的 SPI 片选等误改成 CH3N。制动时基 1 可与电机时基 0 不同频率，但同一个 MCPWM 的模块时钟分频、部分配置资源仍共享，不能在电机运行时重置整个模块来开关制动。制动保护需随外接电路另行设计。

2026-11-01 用户确定制动由 controller 软件根据各自母线电压控制。现有 CH3P 资源作为输出候选；须核对 MCPWM FAIL/屏蔽配置能否关断三相桥而保留所需制动控制，当前静态引脚分配不代表这一动态行为已验证。制动判断不经 ThreadX 1 ms 线程调度，软件/驱动延迟及输出频率待落实，详见 [软件规划](software_resources.md)。

LED 暂定低有效。CAN 先预留 TX/RX；若收发器有 STB/EN，由外围固定到适当状态，或者重新分配 GPIO，不能默认为已有控制脚。UART 接口地为第 3 脚；SPI 与编码器连接器脚序尚未冻结，表中以信号名称标识。

## 最小系统与保留脚

| 信号 | 封装脚 | GPIO | 外设功能 | 复用 | 连接位置 |
| --- | --- | --- | --- | --- | --- |
| MCU_NRST | 10 | P0_6 | RST_n | SPECIAL | J_SWD.5 |
| OSC_OUT | 11 | P0_7 | OSC_OUT | SPECIAL | Y1.OUT |
| OSC_IN | 13 | P0_8 | OSC_IN | SPECIAL | Y1.IN |
| DEBUG_nTRST_RESERVED | 15 | P0_9 | DEBUG_RESERVED | SPECIAL | TEST_PAD_OPTION |
| SWDIO | 16 | P0_10 | SWDIO | SPECIAL | J_SWD.2 |
| DEBUG_TDI_RESERVED | 17 | P0_11 | DEBUG_RESERVED | SPECIAL | TEST_PAD_OPTION |
| SWCLK | 18 | P0_12 | SWCLK | SPECIAL | J_SWD.3 |
| DEBUG_TDO_RESERVED | 19 | P0_13 | DEBUG_RESERVED | SPECIAL | TEST_PAD_OPTION |
| REF_TEST_RESERVED | 74 | P3_11 | ANALOG_RESERVED | AF0 | TEST_PAD_OPTION |
| LDO12_TEST_RESERVED | 85 | P4_6 | ANALOG_RESERVED | AF0 | TEST_PAD_OPTION |

- 保持 SYS_IO_CFG.SWDMUX=0，保留正常在线 SWD；该位整组控制 P0.9～P0.13，不能假设只保留 SWDIO/SWCLK 就可随意使用另外三脚。P0.9/P0.11/P0.13 本草案均不接业务电路。
- 保持 RST_IO=0，10 脚维持 MCU 复位；SWD NRST 与已取消的功率板 RESET_N 不同。
- 保持 TRACEMUX=0，P0.14、P0.15、P1.0～P1.3 才按本表用于 CAN、LED、制动、SPI 和电机 PWM。本方案不使用 TRACE/SWV 输出。
- 11/13 脚留给外部晶振，具体频率、负载电容和 CAN 位时序在最小系统设计落实。
- 74 脚 REF 与 85 脚 LDO12 留作可选高阻测试点，不当作电源输入、不默认外接大电容。内部 REF/LDO 输出到 IO 的使能与 OPA 输出复用须按实际测量用途配置；本表不要求正常运行时打开输出。
- AVDD：14/42/71/92/93，全部接所设计的 3.3 V MCU 电源并逐脚去耦。VSS：12/31/62，VSS33：44/73/94/95，全部接地。NC：5/29/60/72，全部不连接。

## ADC 通道与时序候选

25 路直接外部模拟输入已落脚。ADC0 使用 9 路、ADC1 使用 7 路、ADC2 使用 9 路；未用 ADC1_CH8（P4.6）和 ADC2_CH7（P3.11），与两只模拟测试预留一致。三路 ADC 不能任意互换各自的外部通道。

| 候选采样槽 | ADC0 | ADC1 | ADC2 |
| --- | --- | --- | --- |
| 电流槽 0 | INV1_I_U / CH14 | INV1_I_V / CH13 | INV1_I_W / CH13 |
| 电流槽 1 | INV2_I_U / CH13 | INV2_I_V / CH12 | INV2_I_W / CH12 |
| 电流槽 2 | PFC_I_A / CH12 | PFC_I_B / CH11 | PFC_I_C / CH11 |
| 其余信号 | 6 路电压 | 4 路电压 | 3 路电压＋3 路 NTC |

这种布局允许同一控制级的三相电流分布于三个 ADC，便于在同一采样槽同步采集；上表只是通道/序列候选，尚未配置触发。电流之外的信号也未统一认定为低速，例如 Vienna 输入电压的采样速率仍须满足控制需要。

三个控制级共享三个 ADC，不能各自假设独占一组触发状态机。用户手册提供单段/两段序列，以及 MCPWM 和 UTimer 比较事件触发，但两段序列并不自动等于三套独立采样窗口。需选择协调 PWM 相位后的共同序列，或明确的分时采样安排，检查每次触发时 ADC 是否空闲、采样窗口和模拟信号建立时间。若采用三分流重构，还要检查不同占空比下的有效采样区间。

模拟脚采用 AF0，关闭对应数字输入、输出及上下拉；关闭冲突的 OPA/DAC/REF/LDO 对外输出。直接 ADC 输入以各 ADC 的内部地作为负端候选，增益/偏置/校准随前级调理确定。规格书中 5VT 标记不表示 ADC 能采集 5 V；必须按模拟输入范围设计。

## 静态核对结果与冻结前条件

已核对：100 个封装脚号完整且唯一；84 个 GPIO 均有用途或明确保留；79 个用途网络名唯一；25 个外部 ADC 通道唯一；每个选定外设功能和 AF 均出现在规格书表 3-2 对应 GPIO；符号引脚名称/编号与库内 CSV 一致。两只软件 CS 按 GPIO 使用，不与硬件 SPI 自动片选混算。

当前没有物理复用冲突，但以下条件通过前不冻结原理图：

1. PFC 的六路门极关系与驱动级确定。Timer0/1/4 的共同事件启动可研究 UTIMERx_CFG.ETON 与 UTIMERx_EVT；该模式每次事件仅运行一周期，必须验证周期衔接、首周期和事件丢失后的安全状态。不能把它当作已经实现的连续同步 PWM。
2. 通用 Timer 的 CMP/TH 动态更新不按 MCPWM 的影子寄存器机制假设；须验证占空比更新是否可能产生窄脉冲、漏脉冲，以及安全更新方式和采样触发位置。
3. 完成三套 PWM 与 ADC 的统一时序，确定开关频率/采样频率、模拟建立时间、DMA 分配及最坏中断耗时；本轮没有固件基准测试或台架验证。
4. 落实上电/复位时所有 ENABLE、预充、制动和门极输入的外部默认关断状态，以及 SPI CS 默认不选中状态；验证故障、欠压、程序失控时的本地硬件封锁。
5. 冻结指示灯、编码器电平、SPI 供电、CAN 收发器、制动保护需求与连接器。若新增 BOARD_ID 或其他反馈，先修订本表，不能占用标为保留的脚后继续沿用本预算。

若 PFC 时序验证不通过，应先在单 MCU 约束下调整 PFC 命令形式、外部门极分发或控制参数，再重排；本草案不擅自改成双 MCU 架构。

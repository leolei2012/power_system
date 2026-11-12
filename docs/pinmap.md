# power_system Rev E-1 引脚唯一真源

**状态：Rev E-1 草案，对应 Issue #1，雨田审后合并；原理图 #2 #3 以此为准；与本文冲突的旧文档以本文为准。**

## 1. 依据与适用范围

本文规定 Rev E-1 的 MCU 引脚、两板排针及 controller 本地接口。本文是该版本引脚唯一真源；下列旧资料用于核对物理脚号、追溯旧针位与机械约束，不覆盖本次定案。本文不表示原生原理图、PCB 或旧机器合同已经完成迁移。

- [ST DS12589 Rev6 表12/13](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf)：引脚定义、复位状态及 AF 依据；本文涉及的调试上拉与 UCPD 行为分别引用表12注5、注6。
- [README.md](../README.md)：项目背景；其中旧电流目标、接口分工及 52 个 GPIO 全引出的描述由本文覆盖。
- [Rev E 应用引脚说明](../inverter/docs/pin_assignment.md)：对照既有 MCU 外设与引脚分配。
- [STM32G431RBT6_pin_plan.csv](../controller/hardware/g431_core/STM32G431RBT6_pin_plan.csv)：LQFP64 全部物理脚号和端口依据；功能分配按本文定案更新。
- [controller_daughterboard.md 的“两组2×16接口”旧表](controller_daughterboard.md#两组2×16接口)：第4节“旧信号”列的唯一依据；同文件上半部的单功率口讨论稿不作为 Rev E 旧针位依据。
- [pcb_stack_contract_rev_e.json](pcb_stack_contract_rev_e.json)：旧叠板机械合同。该文件中的排针坐标尚未迁移到左右最外侧，新位置由布局 Issue #4 落实，不能继续按旧坐标冻结排针位置。

## 2. 定案摘要

- 两块 60×60 mm 板，2.54 mm 排针叠插；**叠板顺序：功率板 inverter 在上，controller 在下**（雨田 2026-11-12 定）。左右两边最外侧各一个 2×16（J101 左、J102 右，左右按 4.0 节的“装配俯视”定义；排针物理位置移动在布局 Issue #4 落实）。排针上空着的脚全部接 GND（PB0/PB2 备用 ADC 的底板悬空例外见 4.3 节）。controller 4 层，inverter 6 层，铜厚 2 oz。验收 5 Arms，母线 12–60 V，20 kHz，无风扇，**验收环境温度 ≤30 °C，MCU 保持 STM32G431RBT6**。
- 贴片阻容件最小封装 **0603**，不用 0402 及更小封装，以便手焊；两板现有 0402 全部换 0603，位号清单见 7.3 节。
- 叠板机械（雨田 2026-11-12 按 #4 核对建议拍板）：**板距 11.0 mm = 2.50 mm 公针塑高 + 8.5 mm 母座塑高**；四角采用 **M2×11 mm 母-母双通铜柱**。controller 底部支撑 **≥5 mm 且绝缘**，公针尾长 3.0 mm。J102 在两板上同步整体沿 **+X 平移 24.00 mm** 的坐标建议由 #4 落实，pad1 建议坐标 **(152.73, 110.95) mm**；同号焊盘保持同 XY。
- controller：STM32G431RBT6（LQFP64），只放 MCU 最小系统，3.3 V 由板上 LDO（沿用 TLV76733DRVR）。通讯口在 controller 上。
- CAN：沿用 SN65HVD232；PA11 FDCAN1_RX AF9，PA12 FDCAN1_TX AF9（经典 CAN）。
- 串口定为 RS-485（不是 TTL）：MAX3485ESA+T（立创 C18148），不隔离。USART3：PB10 USART3_TX AF7 → DI，PB11 USART3_RX AF7 ← RO。DE 与 /RE 并接，接 PB9（GPIO 推挽输出，软件控制方向），外部下拉电阻使复位/未初始化时 DE=0（只收不发）；阻值由原理图 #2 定。485 端子 4 针：1 A、2 B、3 GND、4 5V；5V 只做输出，经二极管或跳线，防止外部倒灌底板 5 V（具体器件 #2 定）。

  选 PB9 的理由：USART3 硬件 DE 脚 PB14（USART3_RTS_DE，AF7）已被 TIM1_CH2N 占用，只能软件控制方向；候选 PB3/PB4/PB9 中，PB4 复位后是 NJTRST，内部上拉（DS12589 表12注5），会让 DE 在复位期间为高、驱动总线；且 PB4 是 UCPD1_CC2，PA10（W 相上桥 PWM）为高时会被激活 5.1 kΩ 下拉（表12注6），需固件置 UCPD1_DBDIS；PB3 复位后为 JTDO/TRACESWO，保留给 SWO；PB9 复位后无调试功能、无内部上下拉，最适合。
- 编码器：ABZ 一路 PA0 TIM2_CH1 AF1、PA1 TIM2_CH2 AF1、PA2 GPIO EXTI2（Z，只承诺中断，不承诺硬件清零）。SPI 编码器一路：SPI1，PA5 SCK AF5、PA6 MISO AF5、PA7 MOSI AF5，CS=PA15 GPIO 软件片选（外部上拉）。理由：SPI2 引脚与 TIM1 下桥 PB13/14/15 冲突；SPI3 的 PC10/PC11 是 ROM 串口下载口（USART3 PC10_TX/PC11_RX），保留不占；SPI1 是唯一完整无冲突的硬件 SPI；PA15 复位后为 JTDI 带内部上拉（表12注5），复位期间 CS 保持无效高；使用前固件需释放 JTDI（保留 PA13/PA14 SWD）。编码器为 3.3 V 逻辑，端子供电电压待传感器选型。
- 两颗可编程 LED 在 controller 上边缘，改用**侧发光（side-view）LED**：PC5 RUN 绿色，PC8 FAULT 红色（PC8 不选 TIM8_CH3），引脚不变。
- SWD 在 controller 上边缘：PA13 SWDIO、PA14 SWCLK、NRST、+3V3（VTREF）、GND，采用板边侧插（卧式）座。
- 下边缘：CAN、485、ABZ、SPI 编码器端子。controller 所有接口一律**板边侧插（卧式），插头在板外**。controller 底面允许 0603 及以上、高度 ≤1 mm 的无源件和 SWD/测试焊盘；不放有源器件、连接器和高于 1 mm 的器件；安装孔周围 φ8 mm 内不放器件。
- 其他本地：PF0/PF1 HSE（DNP 可选）；PG10 NRST 接板边侧按 RESET 开关；**BOOT 按钮取消**，PB8 BOOT0 保留 10k 下拉并加测试焊盘。日常烧录走 SWD；需要 ROM 下载时通过 nBOOT0/nSWBOOT0 选项字节配置，或按第6节使用 BOOT0 测试焊盘。PC7 RUN_ARM 保留本地 10k 下拉，经 U105 与 CORE_RESET_OK 相与生成 CTRL_READY。
- inverter 顶面预留散热片，B 面（朝 controller 一面）整面 GND；功率级左移 **8–10 mm**，三相输出 **J4（MR60PW-M）移到 inverter 上边缘**，由 #3/#4 落实。
- 备用 ADC：PB0 ADC1_IN15、PB2 ADC2_IN12 引到排针，底板对应脚悬空（不接任何东西，但不是 GND）。三相电压不测，不加额外 AD 端子。
- NTC 接 PB1 ADC1_IN12（型号在 #3 选）。母线电压 V_DC 保留在 PC3 ADC2_IN9。电流 I_U PC0 ADC1_IN6、I_V PC1 ADC2_IN7、I_W PC2 ADC1_IN8，单端（不改差分）。MCU 侧（controller）ADC 输入加 RC（值在 #2 定，固件按 RC 留采样时间）。
- 新增 inverter 高端母线分流与双向高共模电流检测放大器，I_BUS 经 J101/23 和 controller 本地 RC 接 PA3 ADC1_IN4 + COMP2_INP；COMP2 内部接 TIM1_BKIN2，不引出 COMP2_OUT。板上比较器建议加入并接本地故障锁存，沿现有硬件 PWM 封锁及 FAULT_N 路径保护，详见 5A 节。相过流约 ±12 A、保险与输入电流上限约 8 A、相分流电阻不动，按 A13，具体值由焊台在 #3/#7 核算。
- PWM：PA8 TIM1_CH1 AF6（U 上）、PB13 TIM1_CH1N AF6（U 下）、PA9 TIM1_CH2 AF6（V 上）、PB14 TIM1_CH2N AF6（V 下）、PA10 TIM1_CH3 AF6（W 上）、PB15 TIM1_CH3N AF4（W 下，注意 AF4）。PB12 TIM1_BKIN AF6 FAULT_N 低有效；PC4 ENABLE GPIO 输出；PC6 TIM8_CH1 AF4 BRAKE；PC13 BASE_READY 输入；CTRL_READY 为 controller 上 U105 输出（不是 MCU 引脚）。初始化需置 UCPD1_DBDIS（PA9/PA10 dead-battery）。
- 不再使用的 13 个 GPIO（controller 上 NC、可按需加测试焊盘；固件配置为模拟输入）：PA4、PB3、PB4、PB5、PB6、PB7、PC9、PC10、PC11、PC12、PC14、PC15、PD2。

## 3. MCU 引脚总表（STM32G431RBT6，LQFP64）

脚号及端口逐行对应上述 CSV，共 64 脚。网络名采用本文的 Rev E-1 功能网络名；原理图 #2/#3 应据此对齐。ADC 接口网络经 controller 本地 RC 到对应 MCU 引脚，RC 两侧局部节点命名及元件值待原理图 #2 定；表中同一路功能名不表示短接 RC。

“NC”表示 controller 不接功能电路，可按需加测试焊盘，应用固件配置为模拟输入；不表示把 MCU 引脚接 GND。PB0/PB2 是已引出的备用 ADC，不属于 NC GPIO。

| 脚号 | 端口 | 网络名 | 功能/AF | 去向 | 备注 |
| --- | --- | --- | --- | --- | --- |
| 1 | VBAT | +3V3_MCU | 电源 | controller 本地 3.3 V 电源 | VBAT 接 VDD，沿用本地去耦 |
| 2 | PC13 | BASE_READY | GPIO 输入 | 排针 J102/25 | 底板就绪输入 |
| 3 | PC14 | NC | 模拟输入 | NC，可选测试焊盘 | 不引到排针 |
| 4 | PC15 | NC | 模拟输入 | NC，可选测试焊盘 | 不引到排针 |
| 5 | PF0 | HSE_IN | OSC_IN | controller 本地 HSE | DNP 可选；频率及负载参数待原理图 #2 定 |
| 6 | PF1 | HSE_OUT | OSC_OUT | controller 本地 HSE | DNP 可选；不引到排针 |
| 7 | PG10-NRST | NRST | NRST | controller 本地复位、监控、U103、SWD、板边侧按 RESET 开关 | PG10 保留 NRST 功能；外部复位只开漏拉低 |
| 8 | PC0 | I_U | ADC1_IN6，模拟 | 排针 J101/7，经本地 RC | U 相电流，单端 |
| 9 | PC1 | I_V | ADC2_IN7，模拟 | 排针 J101/10，经本地 RC | V 相电流，单端 |
| 10 | PC2 | I_W | ADC1_IN8，模拟 | 排针 J101/11，经本地 RC | W 相电流，单端 |
| 11 | PC3 | V_DC | ADC2_IN9，模拟 | 排针 J101/14，经本地 RC | 母线电压，保留原引脚 |
| 12 | PA0 | ENC_A | TIM2_CH1，AF1 | controller 本地 ABZ 端子 | 编码器 A，3.3 V 逻辑 |
| 13 | PA1 | ENC_B | TIM2_CH2，AF1 | controller 本地 ABZ 端子 | 编码器 B，3.3 V 逻辑 |
| 14 | PA2 | ENC_Z | GPIO EXTI2 | controller 本地 ABZ 端子 | Z 只承诺中断，不承诺硬件清零 |
| 15 | VSS | GND | 电源地 | GND | 数字地 |
| 16 | VDD | +3V3_MCU | 电源 | controller 本地 LDO 输出 | 本地去耦 |
| 17 | PA3 | I_BUS | ADC1_IN4 + COMP2_INP（模拟） | 排针 J101/23，经本地 RC | 母线电流；COMP2 输出内部接 TIM1_BKIN2；原编码器 B 的 Z 已删除 |
| 18 | PA4 | NC | 模拟输入 | NC，可选测试焊盘 | 删除原 V_U 采样用途 |
| 19 | PA5 | SPI_SCK | SPI1_SCK，AF5 | controller 本地 SPI 编码器端子 | 3.3 V 逻辑 |
| 20 | PA6 | SPI_MISO | SPI1_MISO，AF5 | controller 本地 SPI 编码器端子 | 3.3 V 逻辑 |
| 21 | PA7 | SPI_MOSI | SPI1_MOSI，AF5 | controller 本地 SPI 编码器端子 | 3.3 V 逻辑 |
| 22 | PC4 | ENABLE | GPIO 输出 | 排针 J102/21 | 桥使能；沿用底板默认下拉 |
| 23 | PC5 | LED_RUN | GPIO 输出 | controller 上边缘侧发光 RUN 绿色 LED | LED 型号待 #5 查；驱动极性及电阻待原理图 #2 定 |
| 24 | PB0 | ADC_SP1 | ADC1_IN15，模拟 | 排针 J101/18，经本地 RC | 底板对应脚悬空，不接任何东西，不是 GND |
| 25 | PB1 | NTC | ADC1_IN12，模拟 | 排针 J101/15，经本地 RC | NTC 型号待原理图 #3 选；不再测 V_W |
| 26 | PB2 | ADC_SP2 | ADC2_IN12，模拟 | 排针 J101/19，经本地 RC | 底板对应脚悬空；原 NTC 改到 PB1 |
| 27 | VSSA | GND | 模拟电源地 | GND | 与系统地共参考，控制模拟回流 |
| 28 | VREF+ | VREF_MCU | ADC 参考输入 | controller 本地模拟参考及去耦 | 来自滤波模拟电源；沿用现有最小系统参考设计 |
| 29 | VDDA | +3V3_A_MCU | 模拟电源 | controller 本地滤波模拟电源 | 保留本地去耦，不省略 VDDA |
| 30 | PB10 | RS485_TX | USART3_TX，AF7 | controller 本地 MAX3485ESA+T 的 DI | 应用串口 TX，不是 ROM 串口下载脚 |
| 31 | VSS | GND | 电源地 | GND | 数字地 |
| 32 | VDD | +3V3_MCU | 电源 | controller 本地 LDO 输出 | 本地去耦 |
| 33 | PB11 | RS485_RX | USART3_RX，AF7 | controller 本地 MAX3485ESA+T 的 RO | 应用串口 RX，不是 ROM 串口下载脚 |
| 34 | PB12 | FAULT_N | TIM1_BKIN，AF6 | 排针 J102/20 | 低有效；保留硬件故障封锁 |
| 35 | PB13 | PWM_UL | TIM1_CH1N，AF6 | 排针 J102/6 | U 相下桥 |
| 36 | PB14 | PWM_VL | TIM1_CH2N，AF6 | 排针 J102/10 | V 相下桥；不能再作 USART3_RTS_DE AF7 |
| 37 | PB15 | PWM_WL | TIM1_CH3N，AF4 | 排针 J102/14 | W 相下桥，必须用 AF4 |
| 38 | PC6 | BRAKE | TIM8_CH1，AF4 | 排针 J102/17 | 独立制动，沿用默认下拉 |
| 39 | PC7 | RUN_ARM | GPIO 输出 | controller 本地 10k 下拉、U105 输入 | 与 CORE_RESET_OK 相与；PC7 本身不引到排针 |
| 40 | PC8 | LED_FAULT | GPIO 输出 | controller 上边缘侧发光 FAULT 红色 LED | 不选 TIM8_CH3；LED 型号待 #5 查，驱动细节待原理图 #2 定 |
| 41 | PC9 | NC | 模拟输入 | NC，可选测试焊盘 | 删除 SPI B 软件片选；不作为 SPI1 CS |
| 42 | PA8 | PWM_UH | TIM1_CH1，AF6 | 排针 J102/3 | U 相上桥 |
| 43 | PA9 | PWM_VH | TIM1_CH2，AF6 | 排针 J102/7 | V 相上桥；初始化置 UCPD1_DBDIS |
| 44 | PA10 | PWM_WH | TIM1_CH3，AF6 | 排针 J102/11 | W 相上桥；初始化置 UCPD1_DBDIS |
| 45 | PA11 | CAN_RX | FDCAN1_RX，AF9 | controller 本地 SN65HVD232 的 R | 经典 CAN |
| 46 | PA12 | CAN_TX | FDCAN1_TX，AF9 | controller 本地 SN65HVD232 的 D | 经典 CAN |
| 47 | VSS | GND | 电源地 | GND | 数字地 |
| 48 | VDD | +3V3_MCU | 电源 | controller 本地 LDO 输出 | 本地去耦 |
| 49 | PA13 | SWDIO | SWDIO，AF0 | controller 上边缘侧插 SWD 座 | 保留 SWD 调试 |
| 50 | PA14 | SWCLK | SWCLK，AF0 | controller 上边缘侧插 SWD 座 | 保留 SWD 调试 |
| 51 | PA15 | SPI_CS | GPIO 软件片选 | controller 本地 SPI 编码器端子、外部上拉 | 复位为 JTDI、内部上拉；使用前释放 JTDI，保留 SWD |
| 52 | PC10 | NC | 应用固件模拟输入；ROM USART3_TX 保留 | NC，可选测试焊盘 | ROM 下载口 PC10_TX，保留不占，不接 SPI3 |
| 53 | PC11 | NC | 应用固件模拟输入；ROM USART3_RX 保留 | NC，可选测试焊盘 | ROM 下载口 PC11_RX，保留不占，不接 SPI3 |
| 54 | PC12 | NC | 模拟输入 | NC，可选测试焊盘 | 删除 SPI B MOSI |
| 55 | PD2 | NC | 模拟输入 | NC，可选测试焊盘 | 删除 COMM LED |
| 56 | PB3 | NC | 应用固件模拟输入；SWO 保留 | NC，可选测试焊盘 | 复位为 JTDO/TRACESWO；本版不接 DE，使用 SWO 时另配 |
| 57 | PB4 | NC | 模拟输入 | NC，可选测试焊盘 | 复位 NJTRST 内部上拉；UCPD1_CC2 行为见表12注5、注6 |
| 58 | PB5 | NC | 模拟输入 | NC，可选测试焊盘 | 删除 AUX LED |
| 59 | PB6 | NC | 模拟输入 | NC，可选测试焊盘 | 删除编码器 B 的 A |
| 60 | PB7 | NC | 模拟输入 | NC，可选测试焊盘 | 删除编码器 B 的 B |
| 61 | PB8-BOOT0 | BOOT0 | BOOT0 | controller 本地 10k 下拉、测试焊盘（BOOT 按钮取消） | PB8 保留启动用途，不引到排针 |
| 62 | PB9 | RS485_DE | GPIO 推挽输出，软件方向控制 | controller 本地 MAX3485ESA+T 的 DE 与 /RE、外部下拉 | DE=0 只收不发；下拉阻值待原理图 #2 定 |
| 63 | VSS | GND | 电源地 | GND | 数字地 |
| 64 | VDD | +3V3_MCU | 电源 | controller 本地 LDO 输出 | 本地去耦 |

电源/参考/地共 12 脚：1 VBAT、15 VSS、16 VDD、27 VSSA、28 VREF+、29 VDDA、31 VSS、32 VDD、47 VSS、48 VDD、63 VSS、64 VDD。其余 52 个信号/复用 pad 不再全部引出。

CTRL_READY 没有 MCU 物理脚号：controller 上 U103 将 NRST 缓冲成 CORE_RESET_OK，U105 输出 `CTRL_READY = RUN_ARM(PC7) ∧ CORE_RESET_OK`，接 J102/24。NRST 释放或进入 ROM 下载都不自动取得 ARM 许可。

## 4. 两组 2×16 排针定稿与 Rev E 旧针位对照

奇数针在一列、偶数针在另一列，同一行为 2k-1/2k。采用棋盘格 G-S-G：每个非电源信号针的上下相邻（n−2、n+2）和同排对面针（奇数 n+1，偶数 n−1）都是 GND。J101=电源+模拟（左边），J102=PWM+控制（右边），PWM 与模拟分区。

以下每个针号单列一行，不合并 GND。模拟、PWM 和控制信号按上述 G-S-G 分布；J101/1、3 按定稿保留为同一路 +5V 的相邻供电触点。两板按同名连接器、同一针号插合，镜像规则见 4.0 节；左右最外侧的位置移动由 Issue #4 落实。

“子板网络 / 底板网络”是 Rev E-1 的接口网络对应关系；ADC 的 MCU 侧另经第3节所述本地 RC。“与 Rev E 旧针位对比（旧信号）”严格取自旧表的同一连接器、同一针号，只用于迁移对照。

### 4.0 叠板顺序与针号镜像规则

- 叠板顺序（已定）：**inverter 在上，controller 在下**。controller 的公排针 PZ254V-12-32P 焊在其顶面（F.Cu）朝上；inverter 的母座 PM254V-12-32-H85 焊在其底面（B.Cu）朝下。雨田 2026-11-12 按 #4 核对建议定案：板距 **11.0 mm（2.50 mm 公针塑高 + 8.5 mm 母座塑高）**，四角用 M2×11 mm 母-母双通铜柱；controller 底部支撑 ≥5 mm 且绝缘（公针尾 3.0 mm）。插合深度和对向器件净空由 #4 按此落实校核。
- **“左/右”与针号以“装配俯视”为准**：两板叠好后从 inverter 上方往下看（与 controller 顶面俯视同一坐标）。此视角下 J101 在左边缘、J102 在右边缘；两板同一连接器、同一针号的焊盘 XY 必须完全重合。
- 看 controller 顶面：就是装配俯视，所见针位与第4节一致。叠好后 controller 顶面被 inverter 完全盖住，所有接口与指示从板边侧面操作/观察。
- 看 inverter 顶面（从上往下）：也是装配俯视，母座虽在底面，透视位置与 controller 一致，J101 仍在左。
- 把 inverter 翻过来看底面（从下往上看母座）：左右镜像，J101 出现在右手边，每个连接器的奇数列/偶数列也左右互换。照底面实物核对时要按镜像对照，不能按这个视角重新编号。
- KiCad 中 inverter 的母座封装必须“翻转到 B.Cu”（几何随之镜像），不能只改层属性；两块 PCB 都在同一装配坐标系中比对 J101/J102 每个焊盘坐标。controller 与 inverter 原理图里的 J101/J102 针号一一相同，不做任何针号映射或镜像排线。
- 本节取代 `pcb_stack_contract_rev_e.json` 中“两组排针都在左侧”的旧坐标；该 JSON 的 mating_rule（同号焊盘同 XY、母座翻到 B.Cu）继续有效，坐标在 #4 更新。
- J102 坐标建议：两板上的 J102 同步整体沿 +X 平移 24.00 mm，pad1 为 (152.73, 110.95) mm，由 #4 落实；保持针号及同号焊盘 XY 一致。

### 4.1 J101：电源+模拟（左边）

| 针号 | 定稿信号 | 子板网络 | 底板网络 | 与 Rev E 旧针位对比（旧信号） |
| --- | --- | --- | --- | --- |
| 1 | +5V（底板 +5V_INV / 子板 +5V_CORE_IN） | +5V_CORE_IN | +5V_INV | 5V_IN |
| 2 | GND | GND | GND | GND |
| 3 | +5V | +5V_CORE_IN | +5V_INV | 5V_IN |
| 4 | GND | GND | GND | GND |
| 5 | GND | GND | GND | PA0 |
| 6 | GND | GND | GND | PA1 |
| 7 | I_U(PC0) | I_U | I_U | PA2 |
| 8 | GND | GND | GND | PA3 |
| 9 | GND | GND | GND | PA4 |
| 10 | I_V(PC1) | I_V | I_V | PA5 |
| 11 | I_W(PC2) | I_W | I_W | PA6 |
| 12 | GND | GND | GND | PA7 |
| 13 | GND | GND | GND | PA8 |
| 14 | V_DC(PC3) | V_DC | V_DC | PA9 |
| 15 | NTC(PB1) | NTC | NTC | PA10 |
| 16 | GND | GND | GND | PA11 |
| 17 | GND | GND | GND | PA12 |
| 18 | ADC_SP1(PB0，底板悬空) | ADC_SP1 | 悬空（NC，不接任何东西，不是 GND） | PA13 |
| 19 | ADC_SP2(PB2，底板悬空) | ADC_SP2 | 悬空（NC，不接任何东西，不是 GND） | PA14 |
| 20 | GND | GND | GND | PA15 |
| 21 | GND | GND | GND | GND |
| 22 | +3V3_CORE_REF（子板 +3V3_MCU） | +3V3_MCU | +3V3_CORE_REF | 3V3_CORE_REF |
| 23 | I_BUS(PA3) | I_BUS | I_BUS | PB0 |
| 24 | GND | GND | GND | PB1 |
| 25 | GND | GND | GND | PB2 |
| 26 | GND | GND | GND | PB3 |
| 27 | GND | GND | GND | PB4 |
| 28 | GND | GND | GND | PB5 |
| 29 | GND | GND | GND | PB6 |
| 30 | GND | GND | GND | PB7 |
| 31 | GND | GND | GND | GND |
| 32 | +3V3_CORE_REF | +3V3_MCU | +3V3_CORE_REF | 3V3_CORE_REF |

### 4.2 J102：PWM+控制（右边）

| 针号 | 定稿信号 | 子板网络 | 底板网络 | 与 Rev E 旧针位对比（旧信号） |
| --- | --- | --- | --- | --- |
| 1 | GND | GND | GND | PB8_BOOT0 |
| 2 | GND | GND | GND | PB9 |
| 3 | PWM_UH(PA8) | PWM_UH | PWM_UH | PB10 |
| 4 | GND | GND | GND | PB11 |
| 5 | GND | GND | GND | PB12 |
| 6 | PWM_UL(PB13) | PWM_UL | PWM_UL | PB13 |
| 7 | PWM_VH(PA9) | PWM_VH | PWM_VH | PB14 |
| 8 | GND | GND | GND | PB15 |
| 9 | GND | GND | GND | GND |
| 10 | PWM_VL(PB14) | PWM_VL | PWM_VL | CTRL_READY |
| 11 | PWM_WH(PA10) | PWM_WH | PWM_WH | PC0 |
| 12 | GND | GND | GND | PC1 |
| 13 | GND | GND | GND | PC2 |
| 14 | PWM_WL(PB15) | PWM_WL | PWM_WL | PC3 |
| 15 | GND | GND | GND | PC4 |
| 16 | GND | GND | GND | PC5 |
| 17 | BRAKE(PC6) | BRAKE | BRAKE | PC6 |
| 18 | GND | GND | GND | PC7 |
| 19 | GND | GND | GND | PC8 |
| 20 | FAULT_N(PB12) | FAULT_N | FAULT_N | PC9 |
| 21 | ENABLE(PC4) | ENABLE | ENABLE | PC10 |
| 22 | GND | GND | GND | PC11 |
| 23 | GND | GND | GND | PC12 |
| 24 | CTRL_READY | CTRL_READY（U105 输出） | CTRL_READY | PC13 |
| 25 | BASE_READY(PC13) | BASE_READY | BASE_READY | PC14 |
| 26 | GND | GND | GND | PC15 |
| 27 | GND | GND | GND | GND |
| 28 | GND | GND | GND | PD2 |
| 29 | GND | GND | GND | HSE_IN |
| 30 | GND | GND | GND | HSE_OUT |
| 31 | GND | GND | GND | GND |
| 32 | GND | GND | GND | NRST |

### 4.3 计数、悬空例外及电源规则

计数：J101 信号 12（+5V×2、+3V3_CORE_REF×2、模拟 8）+ GND 20；J102 信号 11 + GND 21；共 23 个非 GND 触点 + 41 GND = 64。

这里“信号”按非 GND 触点计数，包含重复电源与参考，不是 23 个独立 MCU GPIO。PB0/PB2 对应的 J101/18、19 是两个备用模拟信号触点，底板焊盘必须悬空，不接地、不接其他网络或器件；不适用“空脚全部接 GND”。其余表内 41 个 GND 触点在两板均接 GND。新增 J101/23 I_BUS 的上下相邻 21、25 和同排对面 24 均为 GND。

5V 规则：子板 5 V 只由底板经 J101/1、3 供；禁止两路 5 V 并联。+3V3_CORE_REF 只给底板钳位/故障上拉参考，不与底板 +3V3_INV 并联。

485 端子第4针的 5V 是输出，必须经二极管或跳线防止外部倒灌底板 5 V；具体方案与器件待原理图 #2 定。该端子不成为子板第二路 5 V 输入。SWD 的 +3V3 是本地 +3V3_MCU 的 VTREF。

## 5. controller 本地接口表

CAN、485 和编码器端子位于下边缘；SWD 与两颗可编程 LED 位于上边缘。所有接口一律板边侧插（卧式），插头在板外；RESET 为板边侧按开关，RUN/FAULT 为上边缘侧发光（side-view）LED。controller 底面只允许 0603 及以上、高度 ≤1 mm 的无源件及 SWD/测试焊盘，不放有源器件、连接器及高于 1 mm 的器件，安装孔周围 φ8 mm 内不放器件。接口器件型号仅采用定案已给出的型号；侧插座、侧按开关和侧发光 LED 的型号待 #5 查，未定针序交原理图 #2 确定。

| 接口 | 针号/针序 | 信号与 MCU/器件连接 | 供电、型号及备注 |
| --- | --- | --- | --- |
| RS-485 | 1 | A，接 MAX3485ESA+T 总线 A | MAX3485ESA+T（立创 C18148），不隔离 |
| RS-485 | 2 | B，接 MAX3485ESA+T 总线 B | 板边侧插座，型号待 #5 查 |
| RS-485 | 3 | GND | 共地 |
| RS-485 | 4 | 5V 输出 | 经二极管或跳线防倒灌；具体器件待原理图 #2 定 |
| CAN | 1（建议） | CANH，接 SN65HVD232 | 沿用 SN65HVD232，经典 CAN；针序为建议，最终待 #2 定 |
| CAN | 2 | CANL，接 SN65HVD232 | PA11 FDCAN1_RX AF9、PA12 FDCAN1_TX AF9 |
| CAN | 3 | GND | 板边侧插座，型号待 #5 查；是否需要另加 5V：待定（#2） |
| ABZ 编码器 | 针序待 #2 定 | A=PA0 TIM2_CH1 AF1；B=PA1 TIM2_CH2 AF1；Z=PA2 EXTI2；另含供电、GND | 3.3 V 逻辑；板边侧插座型号待 #5 查；端子供电电压待传感器选型，保护待原理图 #2 定 |
| SPI 编码器 | 针序待 #2 定 | SCK=PA5 AF5；MISO=PA6 AF5；MOSI=PA7 AF5；CS=PA15 GPIO；另含供电、GND | SPI1，3.3 V 逻辑；CS 外部上拉；板边侧插座型号待 #5 查；端子供电电压待传感器选型，保护待原理图 #2 定 |
| SWD | 针序待 #2 定 | PA13 SWDIO、PA14 SWCLK、NRST、+3V3（VTREF）、GND | VTREF 接 +3V3_MCU；板边侧插座型号待 #5 查 |
| RUN LED | 不适用 | PC5 GPIO 输出，绿色 | controller 上边缘侧发光 LED；型号待 #5 查，驱动极性及电阻待原理图 #2 定 |
| FAULT LED | 不适用 | PC8 GPIO 输出，红色 | controller 上边缘侧发光 LED；不选 TIM8_CH3；型号待 #5 查，驱动极性及电阻待原理图 #2 定 |
| RESET | 不适用 | PG10 NRST，本地复位网络 | 板边侧按开关；型号待 #5 查，引脚不变 |
| BOOT0 测试焊盘 | 不适用 | PB8 BOOT0，保留 10k 下拉 | BOOT 按钮取消；日常烧录走 SWD，ROM 下载操作见第6节 |

485 逻辑侧固定为 PB10 USART3_TX AF7 → DI、PB11 USART3_RX AF7 ← RO；DE 与 /RE 并接 PB9，外部下拉使复位/未初始化时只收不发。PF0/PF1 HSE（DNP 可选）、PG10 NRST 及板边侧按 RESET 开关、PB8 BOOT0 测试焊盘及 10k 下拉、PC7 RUN_ARM 及 10k 下拉均保留在 controller 本地，不经两板排针引出；BOOT 按钮取消。不加额外 AD 端子。

## 5A. 母线电流检测与过流保护

### 5A.1 位置选择与故障覆盖

采用 inverter 上的**高端母线分流**：分流电阻串在直流母线电容（C19/C20 一侧）与三相桥上管漏极之间，使三相桥从母线取得的全部电流（含母线电容放电）都经过它。雨田不接受相线对地短路的保护盲区，位置选择理由如下：

1. 相线对地短路且上管导通时，短路电流从 VBUS 经上管流出、经外部地返回，不经过现有三相下桥分流 RS1–RS3，形成保护盲区。高端母线分流在上管之前，任何从母线流向三相桥的电流都能测到。
2. 本系统共地、不隔离，GND=DC−=controller 地。若将分流串在低端回流路径，会在功率地与控制地之间插入分流压降；经外部地（示波器、PC、485 地）返回的故障电流还可能绕过低端分流。
3. 相线对 VBUS 短路且下管导通时，电流经过下桥分流 RS1–RS3，由现有相电流过流链覆盖。

高端方案的代价是需要高共模电流检测放大器；INA241A2 已由 #3 定，交 #5 在立创查料号、#3 落实电路。

### 5A.2 放大器要求与定案参数

放大器共模输入范围须覆盖 0–60 V 母线并留裕量（建议 ≥80 V），具备 PWM 共模瞬变抑制，支持双向检测（再生/制动时母线电流可反向）。带宽和建立时间须满足快速过流检测，动态性能由 #3 核算；输出摆幅适配 3.3 V ADC。采用 INA241A2，供电 VS=3.3 V，REF1 接 VBIAS_1V65、REF2 接 GND；按 TI INA241 规格书 SBOSA30D 式 1，`VOUT = G×VIN + (VREF1+VREF2)/2`，零点 = (1.65+0)/2 = 0.825 V。

以下 5 Arms 保护参数中，**母线分流阻值、放大器增益、零点/量程及过流门限已由 [#3](https://github.com/leolei2012/power_system/issues/3#issuecomment-6803863671) 定**；分流封装/功率及保护响应仍由 #3/#7 按器件、误差核算：

| 项目 | 定案值与核算依据 | 状态 |
| --- | --- | --- |
| 母线分流电阻 | 5 mΩ；2512 级、额定功率 ≥1 W 为建议；按 8 A 输入上限，I²R≈0.32 W | 阻值已由 #3 定；封装/功率待 #3/#7 核算 |
| 放大器增益与灵敏度 | INA241A2，20 V/V → 100 mV/A | 已由 #3 定 |
| 双向电流量程 | 零点 0.825 V；线性输出区 0.05~3.10 V（VS=3.3 V，保证上摆 VS−0.2 V）→ +22.75 / −7.75 A；反向超过 −7.75 A 饱和 | 已由 #3 定 |
| 母线过流门限 | 约 15 A（峰值），对应 2.325 V；COMP2 DAC 门限约 2.325 V | 已由 #3 定 |

**按定案 A13（PR #9，`docs/design_decisions.md`），相电流硬件过流约 ±12 A，保险与输入电流上限约 8 A，相分流电阻不动；具体值由焊台在 #3/#7 核算。** 这些属于 A13 已定约束，不再列为待雨田定。

### 5A.3 两层过流保护

- **(a) inverter 板上硬件比较器：建议加入，#3 落实。** 放大器输出与门限比较，比较器采用开漏输出、带迟滞，型号与传播延迟待选型。开漏输出并入现有本地故障锁存；锁存后经硬件 PWM 封锁关断全桥，并拉低 FAULT_N（J102/20 → PB12 TIM1_BKIN）。该链与现有相电流比较器/锁存走同一路径，不依赖 MCU 初始化或固件，复位期间也有效。
- **(b) MCU 内部 COMP2：** 放大器输出作为 I_BUS，经排针 J101/23 和 controller 本地 RC 进入 PA3。PA3 同时是 ADC1_IN4（母线电流采样）和 COMP2_INP；COMP2_CSR.INPSEL 选择 PA3，另一个可选正输入 PA7 已被 SPI1_MOSI 占用。COMP2 反相输入选内部 DAC 通道，门限约 2.325 V（≈15 A），具体 INMSEL 编码以 RM0440 的 COMP 章节为准；不得选择引脚型 INM 的 PA2/PA5，因为 PA2=ENC_Z、PA5=SPI1_SCK。COMP2 输出通过 TIM1_AF2.BK2CMP2E 在内部连接 TIM1_BKIN2，不引到任何 GPIO。COMP2_OUT 的 AF 引脚 PA2/PA12 已分别用于 ENC_Z、CAN_TX，均不得配置为 COMP2_OUT。TIM1_BKIN 仍由 PB12 FAULT_N 输入，两路 break 都能封锁 PWM；MCU 这一层在完成初始化后生效。

### 5A.4 PA3 选择依据、ADC 通道与本地 RC

按 [DS12589 表12/表13](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf)，同时具备 ADC 与 COMP 正输入的引脚为 PA0、PA1、PA3、PA7、PB0、PB1、PC1：COMP1_INP=PA1/PB1，COMP2_INP=PA7/PA3，COMP3_INP=PA0/PC1，COMP4_INP=PB0。其中 PA0/PA1 已用于 ABZ，PA7 用于 SPI1_MOSI，PB1 用于 NTC，PC1 用于 I_V；PB0 是雨田定的备用 ADC（ADC1_IN15），也可作 COMP4_INP，列为备选但本次不占用。PA3 原为已删除的编码器 B 的 Z，原先空闲，本次用于 I_BUS。

ADC1 通道核对：IN4(PA3，I_BUS)、IN6(PC0，I_U)、IN8(PC2，I_W)、IN12(PB1，NTC)、IN15(PB0，ADC_SP1) 互不冲突；ADC2：IN7(PC1，I_V)、IN9(PC3，V_DC)、IN12(PB2，ADC_SP2) 互不冲突。

内部连接与寄存器依据为 [RM0440 Rev 9](https://www.st.com/resource/en/reference_manual/rm0440-stm32g4-series-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)：第24章 COMP，24.6.1 COMP_CxCSR 的 INPSEL/INMSEL；11.3.9 “From comparators (COMPx) to timers”；29.6.28 TIMx_AF2 的 BK2CMPxE（本方案使用 BK2CMP2E）。

MCU 侧 I_BUS 进入 PA3 前同样加本地 RC。该 RC 同时增加 COMP 路径延迟，时间常数须兼顾 ADC 采样与过流响应；R/C 值待 #2 定，不能只按 ADC 滤波选择。

## 6. 对固件的影响

### 6.1 MCU 外设与引脚不变

以下“不变”以已保存的 Rev E 应用引脚分配为基准，指 MCU 外设、端口和 AF；外围器件所在板及排针针号按本文迁移。

| 功能 | 保持的外设与引脚 |
| --- | --- |
| 六路 PWM | PA8 TIM1_CH1 AF6、PB13 TIM1_CH1N AF6、PA9 TIM1_CH2 AF6、PB14 TIM1_CH2N AF6、PA10 TIM1_CH3 AF6、PB15 TIM1_CH3N AF4 |
| BKIN | PB12 TIM1_BKIN AF6，FAULT_N 低有效 |
| ENABLE | PC4 GPIO 输出 |
| BRAKE | PC6 TIM8_CH1 AF4 |
| BASE_READY | PC13 GPIO 输入 |
| 三相电流 | PC0 ADC1_IN6、PC1 ADC2_IN7、PC2 ADC1_IN8，保持单端 |
| V_DC | PC3 ADC2_IN9 |
| CAN | PA11 FDCAN1_RX AF9、PA12 FDCAN1_TX AF9；沿用经典 CAN |
| USART3 | PB10 USART3_TX AF7、PB11 USART3_RX AF7；外部接口改为 RS-485 |
| ABZ 一路 | PA0 TIM2_CH1 AF1、PA1 TIM2_CH2 AF1、PA2 GPIO EXTI2；Z 只承诺中断 |
| SPI1 | PA5 SCK AF5、PA6 MISO AF5、PA7 MOSI AF5 |
| RUN / FAULT LED | PC5 / PC8 GPIO；PC8 不选 TIM8_CH3 |
| RUN_ARM | PC7 GPIO，经本地 U105 与 CORE_RESET_OK 相与产生 CTRL_READY |

### 6.2 新增与变化

- 新增 PB9 作为 RS485_DE 推挽输出；DE 与 /RE 并接，初始化保持 DE=0，外部下拉覆盖复位和未初始化阶段。不能使用已分配给 TIM1_CH2N 的 PB14 硬件 DE。
- 增加 485 半双工方向控制：发送前 DE=1，发送完成 TC 后 DE=0。切回接收以 USART 的 TC 为准，不能仅以发送数据寄存器空或 DMA 搬运结束判断总线发送完成。通信速率和方向切换的具体时序参数待定。
- NTC 从 PB2 ADC2_IN12 改到 PB1 ADC1_IN12；PB2 改为 ADC_SP2，PB0 改为 ADC_SP1。更新 ADC 通道、序列及温度换算配置，NTC 参数待原理图 #3 选型后确定。
- 新增 PA3 ADC1_IN4 采母线电流，按 #3 定案换算 `I_BUS = (V − 0.825 V) / 0.1 V/A`；12 位 ADC、3.3 V 满量程时分辨率约 8.1 mA/LSB。反向超过 −7.75 A 饱和，建议用 ADC1 模拟看门狗下限约 −7 A 做回馈过大告警。COMP2 配置 INPSEL=PA3、INM=内部 DAC 通道（门限约 2.325 V，≈15 A），并配置迟滞，必要时用 TIM1 输出做消隐；INMSEL 编码以 RM0440 COMP 章节为准，不得选择 PA2/PA5 引脚型 INM。
- 置 TIM1_AF2.BK2CMP2E=1，使 COMP2 输出内部接 TIM1_BKIN2；BKIN2 使能和极性（BK2E/BK2P）按 RM0440 配置。BKIN（PB12 FAULT_N）保持，两路 break 均参与 PWM 封锁。不能把 PA2/PA12 配置为 COMP2_OUT，避免与 ENC_Z/CAN_TX 冲突。
- SPI 软件 CS 固定为 PA15，带外部上拉。相对旧单功率口讨论稿是从 PC9 改到 PA15；**Rev E 中 SPI A CS 就是 PA15，Rev E-1 保持 PA15 不变**，不能误写成相对 Rev E 改脚。使用前释放 JTDI，并保留 PA13/PA14 SWD。
- 初始化需置 UCPD1_DBDIS，关闭影响 PA9/PA10 PWM 的 dead-battery 行为；PB4 的 UCPD1_CC2 相关下拉行为见第2节定案。
- ADC 有 MCU 侧 RC，采样时间按 RC 设；元件值待原理图 #2 定，不沿用旧底板 RC 数值作为新定案。I_BUS 的 RC 还须计入 COMP2 过流路径延迟，时间常数兼顾采样与保护响应。两个 ADC 的三相电流转换顺序及有效采样窗口仍需结合 RC 验证，不能假定三相同时转换。
- BOOT 按钮取消，日常烧录走 SWD；保持 nSWBOOT0=1（由 BOOT0 引脚决定，下拉→主 Flash）。需要 ROM 下载时，用 SWD 修改 nBOOT0/nSWBOOT0 选项字节，或在按 BOOT0 引脚启动的配置下将 BOOT0 测试焊盘短接到 3.3 V 后复位。RESET 改侧按、RUN/FAULT LED 改侧发光，仅改器件形式，引脚不变；ROM 启动期间仍不得 ARM。
- 相过流约 ±12 A、输入上限/保险约 8 A、相分流电阻不动，按 A13，具体值由焊台在 #3/#7 核算；母线过流门限约 15 A 已由 #3 定。固件中的母线保护阈值与电流换算系数按 5A.2 节定案值配置。
- 排针针序全部重排，但固件不关心排针针号；端口、AF、ADC 通道与本地硬件变化仍按本文处理。

### 6.3 删除与未用脚处理

- 删除编码器 B：PB6/PB7/PA3；PA3 改用于 I_BUS（ADC1_IN4 + COMP2_INP），PB6/PB7 未用；保留的一路 ABZ 使用 PA0/PA1/PA2。
- 删除 SPI B：SPI3 PC9–12，其中 PC9 为原软件 CS，PC10/PC11/PC12 为原 SCK/MISO/MOSI。PC10/PC11 保留 ROM USART3 下载用途，本版不接功能器件，可按需加测试焊盘。
- 删除 LED COMM/AUX：PD2/PB5，仅保留 PC5 RUN 与 PC8 FAULT。
- 删除 V_U/V_V/V_W 采样：原用途分别为 PA4/PB0/PB1；PA4 变 NC，PB0 变备用 ADC，PB1 改接 NTC。三相电压不测，不新增 AD 端子。
- PA4、PB3、PB4、PB5、PB6、PB7、PC9、PC10、PC11、PC12、PC14、PC15、PD2 共 13 个 GPIO 在 controller 上 NC，应用固件配置为模拟输入。PB3 保留将来 SWO 的用途，当前不接 DE；需要 SWO 时再配置调试功能。

上电初始化时保持 PC7 RUN_ARM 为低，先完成安全 PWM、ENABLE、BRAKE、PB12 低有效 BKIN 及故障恢复配置，并完成 COMP2/DAC 与 BKIN2 配置，再主动拉高 PC7 RUN_ARM。CTRL_READY 由 U105 产生，不当作独立 MCU GPIO；ROM 启动及复位释放不自动 ARM。

## 7. 原理图待改点清单

### 7.1 原理图 #2：controller

- [ ] J101/J102 按第4节新表逐针重连，只引出 23 个非 GND 触点（含重复电源与参考），其余 41 脚接 GND；J101 左、J102 右，物理移动在布局 Issue #4 落实。
- [ ] 沿用 STM32G431RBT6 最小系统与 TLV76733DRVR 本地 3.3 V，5 V 仅从 J101/1、3 进入；+3V3_MCU 经 J101/22、32 作为底板参考输出。
- [ ] 增加 MAX3485ESA+T（立创 C18148）、PB9 的 DE 与 /RE 并接及外部下拉、4 针 485 端子；按固定针序接 A/B/GND/5V，增加 5V 输出防倒灌路径。下拉阻值、防倒灌方案及器件待原理图 #2 定。
- [ ] CAN 收发器从底板搬到 controller，沿用 SN65HVD232 与 PA11/PA12；端子建议 1 CANH、2 CANL、3 GND（针序及是否另加 5V 待 #2 定）。
- [ ] 增加一路 ABZ 和一路 SPI1 编码器端子及保护；CS=PA15，外部上拉；侧插座型号待 #5 查，针序及供电电压待原理图 #2 结合传感器选型定，逻辑保持 3.3 V。
- [ ] 上边缘 RUN/FAULT 换侧发光 LED：PC5 RUN 绿色、PC8 FAULT 红色，引脚不变；删除 COMM/AUX 连接；LED 型号待 #5 查。
- [ ] 上边缘增加本地 SWD 座，连接 PA13、PA14、NRST、+3V3_MCU（VTREF）、GND；针序待原理图 #2 定，侧插座型号待 #5 查。
- [ ] SWD、485、CAN、ABZ、SPI 全部采用板边侧插（卧式）座，插头在板外；型号待 #5 查。
- [ ] ADC 末端 RC 放在 controller、靠 MCU 输入侧，覆盖 I_U/I_V/I_W/V_DC/NTC/I_BUS 及备用 ADC；值待原理图 #2 定，并交固件据此设采样时间。
- [ ] PA3 经本地 RC 接 J101/23（I_BUS），用于 ADC1_IN4 + COMP2_INP；RC 时间常数兼顾 ADC 采样与 COMP2 过流响应，值待 #2 定。
- [ ] RESET 换板边侧按开关；删除 BOOT 按钮，PB8 保留 10k 下拉 + 测试焊盘；侧按开关型号待 #5 查。
- [ ] 保留 PF0/PF1 可选 HSE、PG10 NRST、PB8 BOOT0 及上述下拉/测试焊盘、PC7 RUN_ARM 及本地 10k 下拉、U103/U105；CTRL_READY 从 U105 接 J102/24。
- [ ] 第2节列出的 13 个未用 GPIO 设 NC，可按需加测试焊盘；PB3 保留 SWO，PC10/PC11 保留 ROM 串口用途，不与排针 GND 连接。
- [ ] 底面只允许 0603 及以上、高度 ≤1 mm 的无源件与 SWD/测试焊盘；不放有源器件、连接器及高于 1 mm 的器件；安装孔周围 φ8 mm 内不放器件。
- [ ] 所有电阻电容最小 0603：现有 0402 全部换 0603，controller 13 个位号见 7.3 节。
- [ ] 与布局 #4 落实板距 11.0 mm（2.50 + 8.5 mm）、四角 M2×11 mm 母-母双通铜柱、controller 底部 ≥5 mm 绝缘支撑（公针尾 3.0 mm）；两板 J102 同步整体沿 +X 平移 24.00 mm，pad1 建议 (152.73, 110.95) mm，逐针保持同 XY。

### 7.2 原理图 #3：inverter

- [ ] 删除底板上的 SWD/TTL/ABZ/SPI/CAN/LED 及 BOOT/NRST 相关接线；对应接口和两颗可编程 LED 在 controller。
- [ ] 排针按第4节新表逐针重连，表内 GND 脚全部接地；J101/18（PB0）与 J101/19（PB2）对应底板脚悬空，不接任何东西，不是 GND。
- [ ] NTC 从 PB2 改接 PB1，经 J101/15；NTC 型号在原理图 #3 选。I_U/I_V/I_W、V_DC 仍分别到 PC0/PC1/PC2、PC3，保持单端采样。
- [ ] 新增高端母线分流 + 高共模电流检测放大器（双向，零点 0.825 V），位于 C19/C20 一侧与三相桥上管漏极之间，确保桥从母线取电及母线电容放电均经分流；输出 I_BUS 接 J101/23，采用 5 mΩ + INA241A2（VS=3.3 V），REF 接法按 5A.2 节 #3 定案落实（#3 设计、#5 查料号）。
- [ ] 新增板上硬件比较器（开漏、带迟滞，建议加入，#3 落实），并入现有故障锁存 → 硬件 PWM 封锁全桥、FAULT_N（J102/20）；型号与传播延迟待选型，不依赖 MCU 初始化或固件。
- [ ] 相过流约 ±12 A、保险与输入上限约 8 A、相分流电阻不动，按 A13，具体值由焊台在 #3/#7 核算；母线分流/增益/过流门限 5 mΩ/20 V/V/约 15 A（峰值）已由 #3 定，详见 5A 节。
- [ ] 删除 V_U/V_V/V_W 采样前端到排针的连接，三相电压不测，不加额外 AD 端子。
- [ ] ADC 末端 RC 移到 MCU 侧后，底板保留钳位/串阻；具体电路及参数由原理图 #3 定，钳位参考使用 +3V3_CORE_REF，不与 +3V3_INV 并联。
- [ ] 保留底板的 FAULT_N、ENABLE、BASE_READY、CTRL_READY 及 PWM/制动保护逻辑，按新针位接线；CTRL_READY 是 controller 上 U105 输出，不是 PC7 直接引出。
- [ ] 设置测试点：I_U、I_V、I_W、I_BUS（新增）、FAULT_N、ENABLE、GND、VBUS、+5V、+3V3。其中底板电源网分别为 +5V_INV、+3V3_INV。
- [ ] B 面（朝 controller）整面 GND，散热放顶面 + 内层，顶面预留散热片位置；散热片与导热垫型号待 #5 查。
- [ ] 与布局 #4 落实功率级左移 8–10 mm，三相输出 J4（MR60PW-M）移至 inverter 上边缘；J102 与 controller 同步按 4.0 节坐标建议移动，保持同号焊盘同 XY。
- [ ] 所有电阻电容最小 0603：现有 0402 全部换 0603，inverter 117 个位号见 7.3 节。

### 7.3 0402→0603 位号清单

以下清单来自两块 PCB 封装的脚本统计，按本次提供的位号逐项列出；全部换为 0603，其他已为 0603 及以上的阻容封装保持最小 0603 规则。

| 板卡 | 数量 | 现有 0402 位号（全部换 0603） |
| --- | --- | --- |
| controller | 13 | C63、C64、C65、C66、C67、C77、C79、C81、C83、C84、R92、R93、R122 |
| inverter | 117 | C17、C40、C41、C42、C43、C44、C45、C46、C47、C48、C49、C50、C54、C55、C56、C57、C58、C59、C60、C61、C62、C69、C70、C71、C72、C73、C74、C75、C76、C82、R13、R40、R41、R42、R43、R44、R45、R46、R47、R52、R57、R62、R67、R68、R69、R70、R71、R72、R73、R74、R75、R76、R77、R78、R79、R80、R81、R82、R83、R84、R85、R86、R87、R88、R89、R90、R91、R94、R95、R96、R97、R98、R99、R100、R101、R102、R103、R104、R105、R106、R107、R108、R109、R110、R111、R112、R113、R114、R115、R116、R117、R118、R119、R120、R121、R123、R124、R125、R126、R127、R128、R129、R130、R131、R132、R133、R134、R135、R136、R137、R138、R139、R140、R141、R142、R143、R160 |

## 8. 器件库现状与器件需求

依据本地 `kicad_library/parts.csv` 与 `symbols/MyParts.kicad_sym` 核对；本任务不修改器件库。

| 器件 | 现状 | Rev E-1 用途 |
| --- | --- | --- |
| SN65HVD232 | kicad_library 已有，MyParts | CAN 收发器沿用现有库项，搬到 controller |
| PZ254V-12-32P | kicad_library 已有 | controller 两组 2×16 排针 |
| PM254V-12-32-H85 | kicad_library 已有 | inverter 两组 2×16 排母 |
| TLV76733 | kicad_library 已有 TLV76733DRVR | controller 本地 3.3 V LDO |
| MAX3485ESA+T（立创 C18148） | kicad_library 没有，需要建库（#5） | 原理图 #2 增加 RS-485；建库时核对符号、封装和引脚映射 |

以下新增器件除母线放大器 INA241A2 已由 #3 定外，其余仍待选型，不在本文填写未经确认的型号/料号；交料号在立创查（Issue #5），并按原理图 #2/#3 与布局 #4 落实需求。MAX3485ESA+T 沿用上述已定型号，另交 #5 建库。

| 待选器件 | 需求约束 | 状态/归属 |
| --- | --- | --- |
| 母线分流电阻 | 高端分流；5 mΩ 已由 #3 定，2512 级、≥1 W 为建议 | 型号/料号待定，#5 查，封装/功率由 #3/#7 核算 |
| 高共模电流检测放大器 | 双向，覆盖 0–60 V 并留裕量（建议 ≥80 V），PWM 共模瞬变抑制，零点 0.825 V；其余要求见 5A 节 | INA241A2、VS=3.3 V 已由 #3 定，#5 查料号 |
| 板上比较器 | 开漏输出、带迟滞，传播延迟待选型；建议加入并接本地故障锁存 | 型号/料号待定，#5 查，#3 落实 |
| M2×11 mm 母-母双通铜柱 | 四角支撑 11.0 mm 板距 | 型号/料号待定，#5 查，#4 落实 |
| 板边侧按开关 | controller RESET，板边侧面操作 | 型号/料号待定，#5 查，#2/#4 落实 |
| 侧发光 LED（绿/红） | 上边缘 RUN/FAULT，side-view，PC5/PC8 不变 | 型号/料号待定，#5 查，#2 落实 |
| 板边侧插座 | GH 1.25 卧式或同类；SWD、485、CAN、ABZ、SPI 均侧插，插头在板外 | 型号/料号待定，#5 查，#2/#4 落实 |
| 顶面散热片与导热垫 | inverter 顶面散热，B 面朝 controller 整面 GND | 型号/料号及未给出的参数待定，#5 查，#3/#4 落实 |

## 9. 未决事项

以下列出实施细节及定案状态，不新增雨田拍板项；定案的 MCU 引脚、两组排针针序及 485 端子针序不因此改变。未有依据的器件参数均写待定。

| 事项 | 当前约束 | 状态/归属 |
| --- | --- | --- |
| PB9 DE 外部下拉阻值 | 复位/未初始化时 DE=0，只收不发 | 待原理图 #2 定 |
| 485 端子 5V 防倒灌方案 | 5V 只输出；二极管还是跳线及具体器件待定 | 待原理图 #2 定 |
| 端子型号与未定针序 | 485 的 1 A/2 B/3 GND/4 5V 已定；CAN 建议 1 CANH/2 CANL/3 GND；ABZ、SPI 编码器、SWD 针序待 #2 定 | 侧插座型号待 #5 查，未定针序待原理图 #2 定；CAN 是否另需 5V 待定 |
| 各接口侧插座、RESET 侧按开关、侧发光 LED 型号 | 所有接口板边侧插、插头在板外；RESET 侧按，RUN/FAULT 上边缘侧发光 | 型号/料号待定，待料号在立创查（#5） |
| ABZ/SPI 端子供电电压 | 逻辑固定为 3.3 V；端子供电电压待传感器选型 | 待原理图 #2 结合传感器选型定 |
| ADC 输入 RC | 位于 MCU 侧，固件按 RC 留采样时间；R/C 值待定 | 待原理图 #2 定 |
| I_BUS RC 取值 | PA3 前本地 RC 同时影响 ADC 采样与 COMP2 过流延迟，时间常数兼顾两者 | 待 #2 定 |
| ABZ/SPI 保护、LED 驱动及 HSE 参数 | 保护器件、LED 极性/电阻、可选 HSE 频率与负载参数待定；侧发光 LED 型号待 #5 查 | 待原理图 #2 定，LED 型号交 #5 |
| NTC 型号与采样前端 | MCU 输入固定 PB1 ADC1_IN12，型号及参数待定 | 待原理图 #3 定 |
| 底板 ADC 钳位/串阻 | 末端 RC 移到 controller 后仍保留底板钳位/串阻，具体参数待定 | 待原理图 #3 定 |
| 相过流/保险/输入上限 | 按 A13：相电流硬件过流约 ±12 A、保险与输入电流上限约 8 A，相分流电阻不动 | 按 A13，具体值由焊台在 #3/#7 核算 |
| 母线分流阻值、放大器增益、母线过流门限 | 5 mΩ/20 V/V/约 15 A（峰值，对应 2.325 V），零点 0.825 V，线性量程 +22.75 / −7.75 A，详见 5A 节 | 已由 [#3](https://github.com/leolei2012/power_system/issues/3#issuecomment-6803863671) 定；固件阈值/换算系数按 5A.2 节定案值配置 |
| 母线放大器型号、供电及动态性能 | INA241A2，VS=3.3 V，双向高共模检测，带宽与建立时间满足快速过流检测，3.3 V ADC 输出范围 | 型号、供电已由 #3 定；#5 查料号，动态性能由 #3 核算 |
| 板上比较器型号 | 开漏、带迟滞，传播延迟待选型；建议加入，#3 落实 | 型号待选（#5），#3 接入现有故障锁存 |

注：旧 `inverter/docs/pin_assignment.md` 把 V_W 接 PB1、NTC 接 PB2。按开工定案“三相电压不测”，V_U/V_V/V_W 全部取消，不再为 V_W 另配 ADC 通道；PB1 归 NTC。当前模拟通道 PA3 ADC1_IN4、PC0 ADC1_IN6、PC1 ADC2_IN7、PC2 ADC1_IN8、PC3 ADC2_IN9、PB1 ADC1_IN12、PB0 ADC1_IN15、PB2 ADC2_IN12 各占不同的 ADCx_INy，无通道冲突（PB1 与 PB2 虽同为 IN12，但分属 ADC1 与 ADC2）。

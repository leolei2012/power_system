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

- 两块 60×60 mm 板，2.54 mm 排针叠插；**叠板顺序：功率板 inverter 在上，controller 在下**（雨田 2026-11-12 定）。左右两边最外侧各一个 2×16（J101 左、J102 右，左右按 4.0 节的“装配俯视”定义；排针物理位置移动在布局 Issue #4 落实）。排针上空着的脚全部接 GND。controller 4 层，inverter 6 层，铜厚 2 oz。验收 5 Arms，母线 12–60 V，20 kHz，无风扇。
- controller：STM32G431RBT6（LQFP64），只放 MCU 最小系统，3.3 V 由板上 LDO（沿用 TLV76733DRVR）。通讯口在 controller 上。
- CAN：沿用 SN65HVD232；PA11 FDCAN1_RX AF9，PA12 FDCAN1_TX AF9（经典 CAN）。
- 串口定为 RS-485（不是 TTL）：MAX3485ESA+T（立创 C18148），不隔离。USART3：PB10 USART3_TX AF7 → DI，PB11 USART3_RX AF7 ← RO。DE 与 /RE 并接，接 PB9（GPIO 推挽输出，软件控制方向），外部下拉电阻使复位/未初始化时 DE=0（只收不发）；阻值由原理图 #2 定。485 端子 4 针：1 A、2 B、3 GND、4 5V；5V 只做输出，经二极管或跳线，防止外部倒灌底板 5 V（具体器件 #2 定）。

  选 PB9 的理由：USART3 硬件 DE 脚 PB14（USART3_RTS_DE，AF7）已被 TIM1_CH2N 占用，只能软件控制方向；候选 PB3/PB4/PB9 中，PB4 复位后是 NJTRST，内部上拉（DS12589 表12注5），会让 DE 在复位期间为高、驱动总线；且 PB4 是 UCPD1_CC2，PA10（W 相上桥 PWM）为高时会被激活 5.1 kΩ 下拉（表12注6），需固件置 UCPD1_DBDIS；PB3 复位后为 JTDO/TRACESWO，保留给 SWO；PB9 复位后无调试功能、无内部上下拉，最适合。
- 编码器：ABZ 一路 PA0 TIM2_CH1 AF1、PA1 TIM2_CH2 AF1、PA2 GPIO EXTI2（Z，只承诺中断，不承诺硬件清零）。SPI 编码器一路：SPI1，PA5 SCK AF5、PA6 MISO AF5、PA7 MOSI AF5，CS=PA15 GPIO 软件片选（外部上拉）。理由：SPI2 引脚与 TIM1 下桥 PB13/14/15 冲突；SPI3 的 PC10/PC11 是 ROM 串口下载口（USART3 PC10_TX/PC11_RX），保留不占；SPI1 是唯一完整无冲突的硬件 SPI；PA15 复位后为 JTDI 带内部上拉（表12注5），复位期间 CS 保持无效高；使用前固件需释放 JTDI（保留 PA13/PA14 SWD）。编码器为 3.3 V 逻辑，端子供电电压待传感器选型。
- 两颗可编程 LED 在 controller 上边缘：PC5 RUN 绿色，PC8 FAULT 红色（PC8 不选 TIM8_CH3）。
- SWD 在 controller 上边缘：PA13 SWDIO、PA14 SWCLK、NRST、+3V3（VTREF）、GND。
- 下边缘：CAN、485、编码器端子。底面不放器件。
- 其他本地：PF0/PF1 HSE（DNP 可选）；PG10 NRST；PB8 BOOT0（10k 下拉，按钮）；PC7 RUN_ARM（本地 10k 下拉，经 U105 与 CORE_RESET_OK 相与生成 CTRL_READY）。
- 备用 ADC：PB0 ADC1_IN15、PB2 ADC2_IN12 引到排针，底板对应脚悬空（不接任何东西，但不是 GND）。三相电压不测，不加额外 AD 端子。
- NTC 接 PB1 ADC1_IN12（型号在 #3 选）。母线电压 V_DC 保留在 PC3 ADC2_IN9。电流 I_U PC0 ADC1_IN6、I_V PC1 ADC2_IN7、I_W PC2 ADC1_IN8，单端（不改差分）。MCU 侧（controller）ADC 输入加 RC（值在 #2 定，固件按 RC 留采样时间）。
- PWM：PA8 TIM1_CH1 AF6（U 上）、PB13 TIM1_CH1N AF6（U 下）、PA9 TIM1_CH2 AF6（V 上）、PB14 TIM1_CH2N AF6（V 下）、PA10 TIM1_CH3 AF6（W 上）、PB15 TIM1_CH3N AF4（W 下，注意 AF4）。PB12 TIM1_BKIN AF6 FAULT_N 低有效；PC4 ENABLE GPIO 输出；PC6 TIM8_CH1 AF4 BRAKE；PC13 BASE_READY 输入；CTRL_READY 为 controller 上 U105 输出（不是 MCU 引脚）。初始化需置 UCPD1_DBDIS（PA9/PA10 dead-battery）。
- 不再使用（controller 上 NC、可按需加测试焊盘；固件配置为模拟输入）：PA3、PA4、PB3、PB4、PB5、PB6、PB7、PC9、PC10、PC11、PC12、PC14、PC15、PD2。

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
| 7 | PG10-NRST | NRST | NRST | controller 本地复位、监控、U103、SWD | PG10 保留 NRST 功能；外部复位只开漏拉低 |
| 8 | PC0 | I_U | ADC1_IN6，模拟 | 排针 J101/7，经本地 RC | U 相电流，单端 |
| 9 | PC1 | I_V | ADC2_IN7，模拟 | 排针 J101/10，经本地 RC | V 相电流，单端 |
| 10 | PC2 | I_W | ADC1_IN8，模拟 | 排针 J101/11，经本地 RC | W 相电流，单端 |
| 11 | PC3 | V_DC | ADC2_IN9，模拟 | 排针 J101/14，经本地 RC | 母线电压，保留原引脚 |
| 12 | PA0 | ENC_A | TIM2_CH1，AF1 | controller 本地 ABZ 端子 | 编码器 A，3.3 V 逻辑 |
| 13 | PA1 | ENC_B | TIM2_CH2，AF1 | controller 本地 ABZ 端子 | 编码器 B，3.3 V 逻辑 |
| 14 | PA2 | ENC_Z | GPIO EXTI2 | controller 本地 ABZ 端子 | Z 只承诺中断，不承诺硬件清零 |
| 15 | VSS | GND | 电源地 | GND | 数字地 |
| 16 | VDD | +3V3_MCU | 电源 | controller 本地 LDO 输出 | 本地去耦 |
| 17 | PA3 | NC | 模拟输入 | NC，可选测试焊盘 | 删除原编码器 B 的 Z |
| 18 | PA4 | NC | 模拟输入 | NC，可选测试焊盘 | 删除原 V_U 采样用途 |
| 19 | PA5 | SPI_SCK | SPI1_SCK，AF5 | controller 本地 SPI 编码器端子 | 3.3 V 逻辑 |
| 20 | PA6 | SPI_MISO | SPI1_MISO，AF5 | controller 本地 SPI 编码器端子 | 3.3 V 逻辑 |
| 21 | PA7 | SPI_MOSI | SPI1_MOSI，AF5 | controller 本地 SPI 编码器端子 | 3.3 V 逻辑 |
| 22 | PC4 | ENABLE | GPIO 输出 | 排针 J102/21 | 桥使能；沿用底板默认下拉 |
| 23 | PC5 | LED_RUN | GPIO 输出 | controller 上边缘 RUN 绿色 LED | LED 型号、驱动极性及电阻待原理图 #2 定 |
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
| 40 | PC8 | LED_FAULT | GPIO 输出 | controller 上边缘 FAULT 红色 LED | 不选 TIM8_CH3；驱动细节待原理图 #2 定 |
| 41 | PC9 | NC | 模拟输入 | NC，可选测试焊盘 | 删除 SPI B 软件片选；不作为 SPI1 CS |
| 42 | PA8 | PWM_UH | TIM1_CH1，AF6 | 排针 J102/3 | U 相上桥 |
| 43 | PA9 | PWM_VH | TIM1_CH2，AF6 | 排针 J102/7 | V 相上桥；初始化置 UCPD1_DBDIS |
| 44 | PA10 | PWM_WH | TIM1_CH3，AF6 | 排针 J102/11 | W 相上桥；初始化置 UCPD1_DBDIS |
| 45 | PA11 | CAN_RX | FDCAN1_RX，AF9 | controller 本地 SN65HVD232 的 R | 经典 CAN |
| 46 | PA12 | CAN_TX | FDCAN1_TX，AF9 | controller 本地 SN65HVD232 的 D | 经典 CAN |
| 47 | VSS | GND | 电源地 | GND | 数字地 |
| 48 | VDD | +3V3_MCU | 电源 | controller 本地 LDO 输出 | 本地去耦 |
| 49 | PA13 | SWDIO | SWDIO，AF0 | controller 上边缘 SWD 座 | 保留 SWD 调试 |
| 50 | PA14 | SWCLK | SWCLK，AF0 | controller 上边缘 SWD 座 | 保留 SWD 调试 |
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
| 61 | PB8-BOOT0 | BOOT0 | BOOT0 | controller 本地 10k 下拉、BOOT 按钮 | PB8 保留启动用途，不引到排针 |
| 62 | PB9 | RS485_DE | GPIO 推挽输出，软件方向控制 | controller 本地 MAX3485ESA+T 的 DE 与 /RE、外部下拉 | DE=0 只收不发；下拉阻值待原理图 #2 定 |
| 63 | VSS | GND | 电源地 | GND | 数字地 |
| 64 | VDD | +3V3_MCU | 电源 | controller 本地 LDO 输出 | 本地去耦 |

电源/参考/地共 12 脚：1 VBAT、15 VSS、16 VDD、27 VSSA、28 VREF+、29 VDDA、31 VSS、32 VDD、47 VSS、48 VDD、63 VSS、64 VDD。其余 52 个信号/复用 pad 不再全部引出。

CTRL_READY 没有 MCU 物理脚号：controller 上 U103 将 NRST 缓冲成 CORE_RESET_OK，U105 输出 `CTRL_READY = RUN_ARM(PC7) ∧ CORE_RESET_OK`，接 J102/24。NRST 释放或进入 ROM 下载都不自动取得 ARM 许可。

## 4. 两组 2×16 排针定稿与 Rev E 旧针位对照

奇数针在一列、偶数针在另一列，同一行为 2k-1/2k。采用棋盘格 G-S-G：每个信号的上下相邻和同排对面都是 GND。J101=电源+模拟（左边），J102=PWM+控制（右边），PWM 与模拟分区。

以下每个针号单列一行，不合并 GND。模拟、PWM 和控制信号按上述 G-S-G 分布；J101/1、3 按定稿保留为同一路 +5V 的相邻供电触点。两板按同名连接器、同一针号插合，镜像规则见 4.0 节；左右最外侧的位置移动由 Issue #4 落实。

“子板网络 / 底板网络”是 Rev E-1 的接口网络对应关系；ADC 的 MCU 侧另经第3节所述本地 RC。“与 Rev E 旧针位对比（旧信号）”严格取自旧表的同一连接器、同一针号，只用于迁移对照。

### 4.0 叠板顺序与针号镜像规则

- 叠板顺序（已定）：**inverter 在上，controller 在下**。controller 的公排针 PZ254V-12-32P 焊在其顶面（F.Cu）朝上；inverter 的母座 PM254V-12-32-H85 焊在其底面（B.Cu）朝下。8.5 mm 是母座塑高，不等于板距；板距、插合深度和对向器件净空在 #4 校核。
- **“左/右”与针号以“装配俯视”为准**：两板叠好后从 inverter 上方往下看（与 controller 顶面俯视同一坐标）。此视角下 J101 在左边缘、J102 在右边缘；两板同一连接器、同一针号的焊盘 XY 必须完全重合。
- 看 controller 顶面：就是装配俯视，所见针位与第4节一致。
- 看 inverter 顶面（从上往下）：也是装配俯视，母座虽在底面，透视位置与 controller 一致，J101 仍在左。
- 把 inverter 翻过来看底面（从下往上看母座）：左右镜像，J101 出现在右手边，每个连接器的奇数列/偶数列也左右互换。照底面实物核对时要按镜像对照，不能按这个视角重新编号。
- KiCad 中 inverter 的母座封装必须“翻转到 B.Cu”（几何随之镜像），不能只改层属性；两块 PCB 都在同一装配坐标系中比对 J101/J102 每个焊盘坐标。controller 与 inverter 原理图里的 J101/J102 针号一一相同，不做任何针号映射或镜像排线。
- 本节取代 `pcb_stack_contract_rev_e.json` 中“两组排针都在左侧”的旧坐标；该 JSON 的 mating_rule（同号焊盘同 XY、母座翻到 B.Cu）继续有效，坐标在 #4 更新。

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
| 23 | GND | GND | GND | PB0 |
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

计数：J101 信号 11（+5V×2、+3V3_CORE_REF×2、模拟 7）+ GND 21；J102 信号 11 + GND 21；共 22 + 42 GND = 64。

这里“信号”按非 GND 触点计数，包含重复电源与参考，不是 22 个独立 MCU GPIO。PB0/PB2 对应的 J101/18、19 是两个备用模拟信号触点，底板焊盘必须悬空，不接地、不接其他网络或器件；不适用“空脚全部接 GND”。其余表内 42 个 GND 触点在两板均接 GND。

5V 规则：子板 5 V 只由底板经 J101/1、3 供；禁止两路 5 V 并联。+3V3_CORE_REF 只给底板钳位/故障上拉参考，不与底板 +3V3_INV 并联。

485 端子第4针的 5V 是输出，必须经二极管或跳线防止外部倒灌底板 5 V；具体方案与器件待原理图 #2 定。该端子不成为子板第二路 5 V 输入。SWD 的 +3V3 是本地 +3V3_MCU 的 VTREF。

## 5. controller 本地接口表

CAN、485 和编码器端子位于下边缘；SWD 与两颗可编程 LED 位于上边缘。底面不放器件。接口器件型号仅采用定案已给出的型号；其余型号和未定针序交原理图 #2 确定。

| 接口 | 针号/针序 | 信号与 MCU/器件连接 | 供电、型号及备注 |
| --- | --- | --- | --- |
| RS-485 | 1 | A，接 MAX3485ESA+T 总线 A | MAX3485ESA+T（立创 C18148），不隔离 |
| RS-485 | 2 | B，接 MAX3485ESA+T 总线 B | 端子型号待原理图 #2 定 |
| RS-485 | 3 | GND | 共地 |
| RS-485 | 4 | 5V 输出 | 经二极管或跳线防倒灌；具体器件待原理图 #2 定 |
| CAN | 1（建议） | CANH，接 SN65HVD232 | 沿用 SN65HVD232，经典 CAN；针序为建议，最终待 #2 定 |
| CAN | 2 | CANL，接 SN65HVD232 | PA11 FDCAN1_RX AF9、PA12 FDCAN1_TX AF9 |
| CAN | 3 | GND | 端子型号待原理图 #2 定；是否需要另加 5V：待定（#2） |
| ABZ 编码器 | 针序待 #2 定 | A=PA0 TIM2_CH1 AF1；B=PA1 TIM2_CH2 AF1；Z=PA2 EXTI2；另含供电、GND | 3.3 V 逻辑；端子供电电压待传感器选型；端子型号及保护待原理图 #2 定 |
| SPI 编码器 | 针序待 #2 定 | SCK=PA5 AF5；MISO=PA6 AF5；MOSI=PA7 AF5；CS=PA15 GPIO；另含供电、GND | SPI1，3.3 V 逻辑；CS 外部上拉；端子供电电压待传感器选型；端子型号及保护待原理图 #2 定 |
| SWD | 针序待 #2 定 | PA13 SWDIO、PA14 SWCLK、NRST、+3V3（VTREF）、GND | VTREF 接 +3V3_MCU；座子型号待原理图 #2 定 |
| RUN LED | 不适用 | PC5 GPIO 输出，绿色 | controller 上边缘；LED 型号、驱动极性及电阻待原理图 #2 定 |
| FAULT LED | 不适用 | PC8 GPIO 输出，红色 | controller 上边缘；不选 TIM8_CH3；LED 型号、驱动极性及电阻待原理图 #2 定 |

485 逻辑侧固定为 PB10 USART3_TX AF7 → DI、PB11 USART3_RX AF7 ← RO；DE 与 /RE 并接 PB9，外部下拉使复位/未初始化时只收不发。PF0/PF1 HSE（DNP 可选）、PG10 NRST、PB8 BOOT0 按钮及 10k 下拉、PC7 RUN_ARM 及 10k 下拉均保留在 controller 本地，不经两板排针引出。不加额外 AD 端子。

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
- SPI 软件 CS 固定为 PA15，带外部上拉。相对旧单功率口讨论稿是从 PC9 改到 PA15；**Rev E 中 SPI A CS 就是 PA15，Rev E-1 保持 PA15 不变**，不能误写成相对 Rev E 改脚。使用前释放 JTDI，并保留 PA13/PA14 SWD。
- 初始化需置 UCPD1_DBDIS，关闭影响 PA9/PA10 PWM 的 dead-battery 行为；PB4 的 UCPD1_CC2 相关下拉行为见第2节定案。
- ADC 有 MCU 侧 RC，采样时间按 RC 设；元件值待原理图 #2 定，不沿用旧底板 RC 数值作为新定案。两个 ADC 的三相电流转换顺序及有效采样窗口仍需结合 RC 验证，不能假定三相同时转换。
- 排针针序全部重排，但固件不关心排针针号；端口、AF、ADC 通道与本地硬件变化仍按本文处理。

### 6.3 删除与未用脚处理

- 删除编码器 B：PB6/PB7/PA3；保留的一路 ABZ 使用 PA0/PA1/PA2。
- 删除 SPI B：SPI3 PC9–12，其中 PC9 为原软件 CS，PC10/PC11/PC12 为原 SCK/MISO/MOSI。PC10/PC11 保留 ROM USART3 下载用途，本版不接功能器件，可按需加测试焊盘。
- 删除 LED COMM/AUX：PD2/PB5，仅保留 PC5 RUN 与 PC8 FAULT。
- 删除 V_U/V_V/V_W 采样：原用途分别为 PA4/PB0/PB1；PA4 变 NC，PB0 变备用 ADC，PB1 改接 NTC。三相电压不测，不新增 AD 端子。
- PA3、PA4、PB3、PB4、PB5、PB6、PB7、PC9、PC10、PC11、PC12、PC14、PC15、PD2 在 controller 上 NC，应用固件配置为模拟输入。PB3 保留将来 SWO 的用途，当前不接 DE；需要 SWO 时再配置调试功能。

启动时继续先完成安全 PWM、ENABLE、BRAKE、低有效 BKIN 及故障恢复配置，再主动拉高 PC7 RUN_ARM。CTRL_READY 由 U105 产生，不当作独立 MCU GPIO；ROM 启动及复位释放不自动 ARM。

## 7. 原理图待改点清单

### 7.1 原理图 #2：controller

- [ ] J101/J102 按第4节新表逐针重连，只引出 22 个信号触点（含重复电源与参考），其余 42 脚接 GND；J101 左、J102 右，物理移动在布局 Issue #4 落实。
- [ ] 沿用 STM32G431RBT6 最小系统与 TLV76733DRVR 本地 3.3 V，5 V 仅从 J101/1、3 进入；+3V3_MCU 经 J101/22、32 作为底板参考输出。
- [ ] 增加 MAX3485ESA+T（立创 C18148）、PB9 的 DE 与 /RE 并接及外部下拉、4 针 485 端子；按固定针序接 A/B/GND/5V，增加 5V 输出防倒灌路径。下拉阻值、防倒灌方案及器件待原理图 #2 定。
- [ ] CAN 收发器从底板搬到 controller，沿用 SN65HVD232 与 PA11/PA12；端子建议 1 CANH、2 CANL、3 GND（针序及是否另加 5V 待 #2 定）。
- [ ] 增加一路 ABZ 和一路 SPI1 编码器端子及保护；CS=PA15，外部上拉；端子型号、针序及供电电压待原理图 #2 结合传感器选型定，逻辑保持 3.3 V。
- [ ] 上边缘布置两颗可编程 LED：PC5 RUN 绿色、PC8 FAULT 红色；删除 COMM/AUX 连接。
- [ ] 上边缘增加本地 SWD 座，连接 PA13、PA14、NRST、+3V3_MCU（VTREF）、GND；针序、型号待原理图 #2 定。
- [ ] ADC 末端 RC 放在 controller、靠 MCU 输入侧，覆盖 I_U/I_V/I_W/V_DC/NTC 及备用 ADC；值待原理图 #2 定，并交固件据此设采样时间。
- [ ] 保留 PF0/PF1 可选 HSE、PG10 NRST、PB8 BOOT0 及 10k 下拉/按钮、PC7 RUN_ARM 及本地 10k 下拉、U103/U105；CTRL_READY 从 U105 接 J102/24。
- [ ] 第2节列出的 14 个未用 GPIO 设 NC，可按需加测试焊盘；PB3 保留 SWO，PC10/PC11 保留 ROM 串口用途，不与排针 GND 连接。

### 7.2 原理图 #3：inverter

- [ ] 删除底板上的 SWD/TTL/ABZ/SPI/CAN/LED 及 BOOT/NRST 相关接线；对应接口和两颗可编程 LED 在 controller。
- [ ] 排针按第4节新表逐针重连，表内 GND 脚全部接地；J101/18（PB0）与 J101/19（PB2）对应底板脚悬空，不接任何东西，不是 GND。
- [ ] NTC 从 PB2 改接 PB1，经 J101/15；NTC 型号在原理图 #3 选。I_U/I_V/I_W、V_DC 仍分别到 PC0/PC1/PC2、PC3，保持单端采样。
- [ ] 删除 V_U/V_V/V_W 采样前端到排针的连接，三相电压不测，不加额外 AD 端子。
- [ ] ADC 末端 RC 移到 MCU 侧后，底板保留钳位/串阻；具体电路及参数由原理图 #3 定，钳位参考使用 +3V3_CORE_REF，不与 +3V3_INV 并联。
- [ ] 保留底板的 FAULT_N、ENABLE、BASE_READY、CTRL_READY 及 PWM/制动保护逻辑，按新针位接线；CTRL_READY 是 controller 上 U105 输出，不是 PC7 直接引出。
- [ ] 设置测试点：I_U、I_V、I_W、FAULT_N、ENABLE、GND、VBUS、+5V、+3V3。其中底板电源网分别为 +5V_INV、+3V3_INV。

## 8. 器件库现状

依据本地 `kicad_library/parts.csv` 与 `symbols/MyParts.kicad_sym` 核对；本任务不修改器件库。

| 器件 | 现状 | Rev E-1 用途 |
| --- | --- | --- |
| SN65HVD232 | kicad_library 已有，MyParts | CAN 收发器沿用现有库项，搬到 controller |
| PZ254V-12-32P | kicad_library 已有 | controller 两组 2×16 排针 |
| PM254V-12-32-H85 | kicad_library 已有 | inverter 两组 2×16 排母 |
| TLV76733 | kicad_library 已有 TLV76733DRVR | controller 本地 3.3 V LDO |
| MAX3485ESA+T（立创 C18148） | kicad_library 没有，需要建库 | 原理图 #2 增加 RS-485；建库时核对符号、封装和引脚映射 |

## 9. 未决事项

以下实施细节均为待原理图定，不新增雨田拍板项；定案的 MCU 引脚、两组排针针序及 485 端子针序不因此改变。未有依据的器件参数均写待定。

| 事项 | 当前约束 | 状态/归属 |
| --- | --- | --- |
| PB9 DE 外部下拉阻值 | 复位/未初始化时 DE=0，只收不发 | 待原理图 #2 定 |
| 485 端子 5V 防倒灌方案 | 5V 只输出；二极管还是跳线及具体器件待定 | 待原理图 #2 定 |
| 端子型号与未定针序 | 485 的 1 A/2 B/3 GND/4 5V 已定；CAN 建议 1 CANH/2 CANL/3 GND；ABZ、SPI 编码器、SWD 针序待 #2 定 | 待原理图 #2 定；CAN 是否另需 5V 待定 |
| ABZ/SPI 端子供电电压 | 逻辑固定为 3.3 V；端子供电电压待传感器选型 | 待原理图 #2 结合传感器选型定 |
| ADC 输入 RC | 位于 MCU 侧，固件按 RC 留采样时间；R/C 值待定 | 待原理图 #2 定 |
| ABZ/SPI 保护、LED 驱动及 HSE 参数 | 保护器件、LED 型号/极性/电阻、可选 HSE 频率与负载参数待定 | 待原理图 #2 定 |
| NTC 型号与采样前端 | MCU 输入固定 PB1 ADC1_IN12，型号及参数待定 | 待原理图 #3 定 |
| 底板 ADC 钳位/串阻 | 末端 RC 移到 controller 后仍保留底板钳位/串阻，具体参数待定 | 待原理图 #3 定 |
| 5 Arms 下的保护参数 | 相电流硬件过流门限、保险丝规格、分流电阻与放大增益是否随 5 Arms 调整 | **待定（待雨田定）**。本文只定 I_U/I_V/I_W 进 PC0/PC1/PC2 的引脚，不涉及电流满量程与门限；改分流或增益不改引脚，但会改固件里的电流换算系数和保护阈值 |

注：旧 `inverter/docs/pin_assignment.md` 把 V_W 接 PB1、NTC 接 PB2。按开工定案“三相电压不测”，V_U/V_V/V_W 全部取消，不再为 V_W 另配 ADC 通道；PB1 归 NTC。剩余模拟通道 PC0 ADC1_IN6、PC1 ADC2_IN7、PC2 ADC1_IN8、PC3 ADC2_IN9、PB1 ADC1_IN12、PB0 ADC1_IN15、PB2 ADC2_IN12 各占不同的 ADCx_INy，无通道冲突（PB1 与 PB2 虽同为 IN12，但分属 ADC1 与 ADC2）。

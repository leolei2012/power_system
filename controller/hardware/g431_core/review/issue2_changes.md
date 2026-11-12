# Issue #2：controller 原理图改动与核算

- 日期：2026-11-12；分支：`hw/controller-sch-issue2`；KiCad CLI **10.0.7**。
- 引脚唯一依据：[已合并的 pinmap](../../../../docs/pinmap.md)，重点逐项核对第 2、3、4.1、4.2、4.3、5、5A、6、7.1 节。
- 根工程为 `controller.kicad_sch`，当前共 **10 页、97 个位号**；新增 52 个位号，删除 SW3、R401，SW2 更换器件形式。Y1/C83/C84、D202/D203 共 5 个位号为 DNP。
- 仅修改允许的原理图、项目库表、项目本地符号库及本目录审查产物。PCB、固件、pinmap、design_decisions、`bom/bom.csv`、`bom/selection_pending.csv`、inverter 和共享库子模块均未修改；未 commit、push 或下单。
- 旧 `debug_comms.kicad_sch`、`sensors.kicad_sch` 保持未实例化，只参考其总线及编码器串阻/上拉拓扑；不能作为本版网络或针序依据。旧 README、旧检查报告和旧 BOM 不代表本次原理图状态。

## 1. J101 / J102 逐针重连

两组排针仍使用已有 `MyParts:PZ254V-12-32P`，不将叠板公排针替换成 GH 插座。以装配俯视定义 J101 左、J102 右；两板同号针直接插合，原理图不交换针号、不做镜像针序。

| 排针 | 非 GND 针位（未列出的全部接 GND） | GND 数量 |
| --- | --- | --- |
| J101 | 1、3=+5V_CORE_IN；22、32=+3V3_MCU；7=I_U；10=I_V；11=I_W；14=V_DC；15=NTC；18=ADC_SP1；19=ADC_SP2；23=I_BUS | 20 |
| J102 | 3=PWM_UH；6=PWM_UL；7=PWM_VH；10=PWM_VL；11=PWM_WH；14=PWM_WL；17=BRAKE；20=FAULT_N；21=ENABLE；24=CTRL_READY；25=BASE_READY | 21 |

合计 23 个非 GND 触点、41 个 GND 触点。接口侧模拟网使用上述名称，RC 后 MCU 局部网为 `I_U_MCU`、`I_V_MCU`、`I_W_MCU`、`I_BUS_MCU`、`V_DC_MCU`、`NTC_MCU`、`ADC_SP1_MCU`、`ADC_SP2_MCU`，没有跨接 RC。

PB0 / PB2 分别经 ADC_SP1 / ADC_SP2 的本地 RC 引出；底板对应脚悬空由 #3 落实，controller 不把它们接地。+5V_CORE_IN 仍仅从 J101/1、3 进入；J101/22、32 的 3.3 V 仅作为底板电平参考，不与底板稳压器并联。

## 2. MCU 引脚与 NC

U30 保持 STM32G431RBT6。全部 64 个物理脚已按 pinmap 第 3 节和实际 XML 网表核对：

| 端口 | 本版用途 |
| --- | --- |
| PC0 / PC1 / PC2 / PC3 | I_U / I_V / I_W / V_DC，经各自本地 RC |
| PA3 | I_BUS_MCU；同一引脚同时用于 ADC1_IN4 与 COMP2_INP |
| PB0 / PB1 / PB2 | ADC_SP1 / NTC / ADC_SP2，经各自本地 RC |
| PB9 / PB10 / PB11 | RS485_DE / RS485_TX / RS485_RX |
| PA11 / PA12 | CAN_RX / CAN_TX |
| PA0 / PA1 / PA2 | ENC_A / ENC_B / ENC_Z，经各自 100 Ω |
| PA5 / PA6 / PA7 / PA15 | SPI_SCK / SPI_MISO / SPI_MOSI / SPI_CS，经各自 100 Ω |
| PA13 / PA14 | SWDIO / SWCLK |
| PC5 / PC8 | LED_RUN / LED_FAULT，高电平亮 |
| PB8 / PC7 | BOOT0 / RUN_ARM，保留各自 10 kΩ 下拉 |
| PC13 / PC4 / PC6 / PB12 | BASE_READY / ENABLE / BRAKE / FAULT_N |
| PA8 / PB13 / PA9 / PB14 / PA10 / PB15 | PWM_UH / PWM_UL / PWM_VH / PWM_VL / PWM_WH / PWM_WL |
| PF0 / PF1 / PG10 | 本地可选 HSE / NRST |

PA4、PB3、PB4、PB5、PB6、PB7、PC9、PC10、PC11、PC12、PC14、PC15、PD2 共 **13 个 GPIO** 删除引出线并在 MCU 脚端放 no-connect，不接排针、不接 GND。未新增这些 GPIO 的测试点。VBAT、VDD、VDDA、VREF+、VSS/VSSA、原去耦与模拟参考方案保持。

## 3. 八路 ADC RC：数值、建立时间与 COMP2 延迟

新增电阻、电容均采用 0603；电容靠 MCU 输入，回流就近参考 VSSA 所在 GND。下列电容值是设计选择；未选定器件的 MPN/LCSC/原厂资料保留「待#5」，不声称已有料号或实际耐压。新滤波电容提出 ≥10 V 的选型要求，作为 3.3 V 工作电压的设计裕量，由 #5 查实。

| 信号 | 电阻 | 电容 | 设计理由 |
| --- | --- | --- | --- |
| I_U | R201=100 Ω | C201=1 nF，C0G 要求 | 快速电流采样；小时间常数减小中心采样建立时间 |
| I_V | R202=100 Ω | C202=1 nF，C0G 要求 | 同上 |
| I_W | R203=100 Ω | C203=1 nF，C0G 要求 | 同上 |
| I_BUS | R204=100 Ω | C204=1 nF，C0G 要求 | 兼顾 ADC1_IN4 与 COMP2_INP，避免慢 RC 延迟过流检测 |
| V_DC | R205=1 kΩ | C205=10 nF | 较慢母线电压，降低高频干扰 |
| NTC | R206=1 kΩ | C206=10 nF | 温度慢变量，无需沿用快速电流带宽 |
| ADC_SP1 | R207=1 kΩ | C207=10 nF | 备用慢速模拟通道；使用时重新核对源阻抗 |
| ADC_SP2 | R208=1 kΩ | C208=10 nF | 同上 |

快速四路：`τ=100 Ω×1 nF=100 ns`，`fc=1/(2πRC)≈1.59 MHz`；20 kHz 正弦分量的幅值比约 0.99992。慢速四路：`τ=1 kΩ×10 nF=10 µs`，`fc≈15.9 kHz`，20 kHz 分量幅值比约 0.623。C0G 是对快速通道温度/电压稳定性的选型要求，实际容差与料号待 #5。

**ADC 采样电容依据。** [ST DS12589 Rev6](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf) 表 60、PDF 第 119 页给出 `CADC=5 pF`，为典型值；本地原厂 Rev1 副本表 62 亦为 5 pF。1 nF / 5 pF=200，10 nF / 5 pF=2000，均远大于采样保持电容。该比例降低瞬间电荷扰动，但不能单凭比例保证 12 位建立精度。

以满量程阶跃建立到 12 位半 LSB 估算，`t≥ln(8192)×τ≈9.01τ`：忽略前级阻抗时，快速路约 **0.901 µs**，慢速路约 **90.1 µs**。实际使用 `τ=(R源+R本地)×C本地`；底板放大器、串阻、ADC 内部开关与采样序列都要计入。若 #3 最终仍采用旧文档的 360 Ω 串阻，仅作为条件示例，则快速路 τ=0.46 µs、9.01τ≈4.15 µs；这个 360 Ω 不是本次对底板的定案。

进一步以 CADC 在切换通道前后发生 3.3 V 满跨度变化估算，电荷共享瞬间误差约为 `3.3×CADC/(C本地+CADC)`：1 nF 时约 16.4 mV，10 nF 时约 1.65 mV。只按外部 RC 恢复到半 LSB（约 0.403 mV）计算，分别还需约 0.371 µs、14.1 µs；这只是简化模型，不包含内部开关建立时间。慢速路宜连续/低速读取，切换后先进行一次舍弃转换，再验证有效采样，不能假设最短采样周期足够。

20 kHz PWM 周期 50 µs、半周期 25 µs。快速路可把 **距最近开关扰动 ≥5 µs** 作为初始验证条件；例如 ADC 时钟 60 MHz、247.5 周期的采样段为 4.125 µs，可作为调试起点，必须结合实际前端、调制比、有效窗口和通道顺序实测。两 ADC 并不意味着三相同时转换；该建议不是最终固件时序验收结论。慢速通道的满阶跃稳定可能跨越多个 PWM 周期，应单独安排。

**COMP2 附加延迟。** 沿 pinmap 5A 的建议（均待 #3/#7 定案）：母线分流 5 mΩ、增益 20 V/V、中点 1.65 V，得到 `V(I)=1.65+0.1I`，15 A 门限约 3.15 V。对从 V0 到 V∞ 的阶跃，RC 到门限 Vth 的时间：

`td=τ×ln[(V∞−V0)/(V∞−Vth)]`。

以 0 A→16 A 为例：V0=1.65 V、V∞=3.25 V、Vth=3.15 V，`td=100 ns×ln(1.60/0.10)≈277 ns`。以理想 0 A→16.5 A、末值 3.30 V 为例，约 `100 ns×ln(11)=240 ns`。恰好到 15 A 门限的理想阶跃只渐近门限，不能声称固定有限触发时间。若条件性增加 360 Ω 源串阻，上述 16 A 示例变为约 1.28 µs。总保护时间还包括放大器建立、COMP2/DAC/迟滞、定时器 break、驱动关断与功率级响应，本次未宣称已经完成系统过流验收。

## 4. RS-485、默认方向与 5V_OUT

新增并实例化 `comms.kicad_sch`：

- U201=`MyParts:MAX3485ESA+T`，LCSC **C18148**，供电 +3V3_MCU；DI(4)←PB10，RO(1)→PB11，DE(3)与 /RE(2)实线并接至 PB9。
- R209=10 kΩ 下拉 DE；DE=0 时驱动关闭、接收开启。原厂资料给单个逻辑输入电流最大 ±2 µA；仅两个使能输入同向漏电造成的偏移约 `2×2 µA×10 kΩ=40 mV`，低于其 VIL 上限 0.8 V。还须计入 MCU/板面漏电。输出为高时电阻耗流约 `3.3/10k=0.33 mA`、耗散 1.09 mW。
- R210=10 kΩ 上拉 RO 到 +3V3_MCU。它仅防止关闭/失电等状态下逻辑输入悬空；正常 /RE=0 时 RO 由接收器主动驱动，不能把上拉解释为接收判决。RO 为低时附加约 0.33 mA 负载。
- C209=100 nF，沿用库内 CC0603KRX7R9BB104 / **C14663** 的已有字段，官方 0603 封装；按收发器近端高频去耦配置，不代替电源页原有大容量电容。C210 同理。
- J201 固定 **1 A / 2 B / 3 GND / 4 5V_OUT**；所有新外部插座均写「GH1.25 卧式 nP 待#5」，LCSC 待#5。
- R211=120 Ω（0805）串 JP201=`SolderJumper_2_Open`，默认断开，只在总线端点焊合。终端功耗核算见第 5 节。
- D202 为双线 TVS 功能占位，Value「TVS 待#5」，默认 DNP，Footprint 留空；没有编造型号或电气额定值。

D201=`MyParts:PMEG2010ER_115`，LCSC **C82288**，使用官方 `Diode_SMD:Nexperia_CFP3_SOD-123W`；**阳极 pin2=+5V_CORE_IN，阴极 pin1=5V_OUT**。其同一阴极网供 J201/4 以及编码器 5 V 选项，没有其他绕过二极管的 5 V 连接。

[Nexperia PMEG2010ER 数据手册](https://assets.nexperia.com/documents/data-sheet/PMEG2010ER.pdf) Rev3（2023-07-01）给出平均正向电流 **1 A**（受手册散热条件限制）、反向电压 **20 V**；25 °C、100 mA 下 Vf 最大 250 mV，1 A 下最大 340 mV。故 5V_OUT 是扣除二极管压降的输出，不是额外稳压 5.00 V。外部 5 V 使 D201 反偏，从主电流方向防止回灌；肖特基仍存在手册规定的反向漏电，不是电气隔离。

**遗留：端子 5 V 对地短路时没有专门限流。** D201 从输入网直接取电，电源页 R301 不在该支路中，二极管也不是限流器。建议 #5 评估自恢复保险丝（保持/动作电流、环境温度降额、压降均待选），由雨田/料号决定；不能把 1 A 额定理解为短路保护。

## 5. CAN、终端功率与 TVS

U202=`MyParts:SN65HVD232DR`，LCSC **C30530**，+3V3_MCU 供电，C210=100 nF。D(1)←CAN_TX(PA12)，R(4)→CAN_RX(PA11)，GND(2)、VCC(3)、CANL(6)、CANH(7)按原厂和共享库连接。J202 固定 **1 CANH / 2 CANL / 3 GND，不另加 5 V**。

**任务文字中的 RS 条款与器件实际功能不同。** [TI SLOS346O](https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf) 第 6、7 节明确：SN65HVD232 没有 RS，**5、8 脚均 NC**；RS 接 GND 进入高速模式适用于 SN65HVD230/231。按指定 232 和原厂资料将 5、8 脚标 NC，不将 NC 接地，不擅自换器件。这不改变 pinmap 的 PA11/PA12 或 CAN 型号。

R212=120 Ω（0805）串 JP202=`SolderJumper_2_Open`，默认断开。CAN/485 各用独立焊桥，不能把两个总线的终端共用。

每只 120 Ω 以正常工作下 3.6 V 差分幅值作保守设计检查：`P=V²/R=3.6²/120=0.108 W`；3.3 V 时为 0.0908 W。CAN 数据手册的差分输出最大 3 V 对应 0.075 W。两只电阻均提出 **≥0.25 W** 的采购要求，正常 0.108 W 时约有 2.31 倍功率余量；0805 只是封装，不代表任意 0805 已具备 0.25 W 额定。实际料号、降额和侧插环境由 #5 核对，不满足则在允许的 0805 以上封装中重新选。总线异常过压、共模/浪涌不在该正常功耗估算中。

D203 与 D202 同为双线 TVS 功能占位、默认 DNP、空封装。新增项目本地符号 `CoreProtection:DualLineTVS_Placeholder` 标注「**临时本地符号，待 #5 入 kicad_library**」。1/2/3 只表示 LINE1/LINE2/GND 功能，**不代表任何待选实物的物理脚号**。#5 按实际原厂 datasheet 替换/核对针序、工作电压、允许共模范围、钳位电压、结电容及浪涌能力；当前没有已完成外部 ESD/浪涌保护的结论。

## 6. 编码器、串阻、上拉与引脚耐压

新增并实例化 `encoders.kicad_sch`：

| 接口 | 固定针序 |
| --- | --- |
| J203 ABZ 5P | 1 VCC_ENC / 2 ENC_A / 3 ENC_B / 4 ENC_Z / 5 GND |
| J204 SPI 6P | 1 VCC_ENC / 2 SPI_CS / 3 SPI_SCK / 4 SPI_MISO / 5 SPI_MOSI / 6 GND |

JP203=`SolderJumper_3_Bridged12`：1=+3V3_MCU、2=VCC_ENC、3=5V_OUT；官方封装默认铜桥 **1–2 连接，默认 3.3 V**。切换供电须先切断 1–2，再焊 2–3，禁止把两种电源短接。两个接口共用 VCC_ENC；5 V 选项同样经过 D201。

| 电阻 | 网络与理由 |
| --- | --- |
| R213 / R214 / R215，均 100 Ω 0603 | ENC_A / ENC_B / ENC_Z 信号在 MCU 侧串联 |
| R216 / R217 / R218 / R219，均 100 Ω 0603 | SPI_CS / SPI_SCK / SPI_MISO / SPI_MOSI 在 MCU 侧串联 |
| R220 / R221 / R222，均 10 kΩ 0603 | ENC_A / ENC_B / ENC_Z 的 MCU 侧拉到 +3V3_MCU，兼容开集电极输出 |
| R223=10 kΩ 0603 | SPI_MISO 拉到 +3V3_MCU，防未驱动时悬空 |
| R224=10 kΩ 0603 | SPI_CS 拉到 +3V3_MCU，满足 PA15 外部上拉，复位时 CS 无效高 |

100 Ω 限制瞬态电流、缓和边沿振铃；不是电平转换或完整 ESD 防护。以信号等效电容 100 pF 的**设计示例**估算，串阻边沿 τ≈10 ns、10%–90% 上升时间约 22 ns；实际线缆与器件电容未选定，不能据此填写已验证最高 SPI 频率。10 kΩ 拉高在低电平时约 0.33 mA；若外部开集电极低电平理想为 0 V，100 Ω 与 10 kΩ 分压使 MCU 低电平约 `3.3×100/(10000+100)=32.7 mV`。开集电极输出释放时，按同样 100 pF 示例、10.1 kΩ 上拉路径，τ≈1.01 µs、10%–90% 约 2.22 µs，线缆加长会变慢；编码器最高边沿频率待 #5/#7 验证。

按 [DS12589 Rev6 表 11/12](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf) 逐脚核对（PDF 第 50、52、53、57 页）：

| MCU 引脚 | 功能 | I/O 结构 | 5 V 推挽接入结论 |
| --- | --- | --- | --- |
| PA0 | ENC_A | **TT_a** | 非 FT，不允许直接接 5 V 推挽 |
| PA1 | ENC_B | **TT_a** | 同上 |
| PA2 | ENC_Z | **TT_a** | 同上 |
| PA5 | SPI_SCK | **TT_a** | MCU 输出仍为 3.3 V；外部不能回驱 5 V |
| PA6 | SPI_MISO | **TT_a** | 非 FT，不允许直接接 5 V 推挽 |
| PA7 | SPI_MOSI | **TT_a** | MCU 输出仍为 3.3 V；外部不能回驱 5 V |
| PA15 | SPI_CS | **FT_f** | FT 类，仍须满足数据手册的供电/配置条件；本接口输出逻辑保持 3.3 V |

表 11 定义 TT 为 3.6 V 耐受、FT 为 5 V 耐受，`_a` 为模拟开关结构、`_f` 为 Fm+ 能力。**不能把 G431 所有端口都当作 FT。** 本次不改变 pinmap 引脚，也没有新增电平转换器。VCC_ENC=5 V 只适用于已经核实输出仍为 3.3 V 或开集电极且上拉到 3.3 V 的传感器；若 #5 选到 5 V 推挽 ABZ/MISO 器件，必须另行增加电平转换方案，不能直接安装使用。3.3 V SPI 输出能否满足某个 5 V 供电传感器的 VIH，也由该传感器原厂资料核对。

## 7. SWD、LED、RESET、BOOT 与所有侧插座

新增并实例化 `ui_debug.kicad_sch`：J205 **1 +3V3_MCU(VTREF) / 2 SWDIO / 3 SWCLK / 4 NRST / 5 GND**。NRST 保留原开漏复位与 U102/U103 监控，不允许调试器推挽驱动复位域。

PC5→R225=1 kΩ 0603→D204（侧发光绿 LED）→GND；PC8→R226=1 kΩ 0603→D205（侧发光红 LED）→GND，高电平亮。LED 均为 `Device:LED`，Value 分别为「侧发光 绿 待#5」「侧发光 红 待#5」，空封装。电阻旁注明「按 #5 选定 LED 的 Vf/If 复核」。

`I_LED=(3.3−Vf)/1kΩ`，具体 Vf/亮度/If 由 #5 选定原厂 LED 后核算，不假造典型 Vf。即使保守取 Vf=0，每颗也不超过 3.3 mA，电阻功率不超过 `3.3²/1k=10.9 mW`；这只是电路上界，不是所选 LED 的额定值。两颗一起为 3.3 V 负载预留不超过 6.6 mA。COMM/AUX 没有实例化或连接；PD2/PB5 已 NC。

SW2 从 TS-1101 顶按形式换为 `Switch:SW_Push`，Value「侧按开关 待#5」，Footprint 空，保持 NRST→GND 的同一电气功能。C81=100 nF、U102/U103、原 NRST 监控保持。

删除 SW3 和原来随 BOOT 按钮串联的 R401=1 kΩ。实际既有下拉是 **R122=10 kΩ**，已保留并换 0603（不是把原 R401 擅自改成 10 kΩ）；TP15「BOOT0」保留，并新增相邻 TP16「3V3」，均采用官方 `TestPoint_Pad_D1.5mm`。外部把 BOOT0 拉到 3.3 V 时，下拉耗流约 0.33 mA；常态默认低。日常 SWD，必要时临时短接两测试焊盘并复位，启动选项位按 pinmap 第 6 节处理。

J201/J202/J203/J204/J205 共五个新侧插座分别为 4/3/5/6/5P。全部已检查官方 GH 横插封装存在，采用：

`Connector_JST:JST_GH_SM0nB-GHS-TB_1x0n-1MP_P1.25mm_Horizontal`。

字段 Datasheet 为 [JST GH 官方页](https://www.jst-mfg.com/product/detail_e.php?series=105)，实际 MPN、LCSC、配套胶壳/端子/线束待 #5；不能仅凭“GH1.25”名称假定不同厂家的插座尺寸、针号方向完全一致。插头在板外，布置上边缘 SWD/LED、下边缘 CAN/485/编码器，由 #4 落实。

## 8. 保留方案、0603 迁移与新电源预算

TLV76733DRVR、U103、U105、PC7/RUN_ARM 的 R402=10 kΩ 下拉、`CTRL_READY=CORE_RESET_OK ∧ RUN_ARM`、本地参考吸收与监控电路均保持。实际网表已比较旧/新引脚连接分区：原供电、监控、ARM、HSE、去耦相互连接保持一致。供电页只更新过时的文字预算/接口说明。

| 既有位号 | 保持的原值/约束 | 本次变化/理由 |
| --- | --- | --- |
| C63/C64/C65/C66/C67 | 100 nF，原 16 V minimum 字段 | 逐个 VDD/VBAT 近端去耦；仅 0402→0603 |
| C77/C79 | 100 nF，原 16 V minimum 字段 | VDDA/VREF 高频去耦；仅换 0603 |
| C81 | 100 nF，原 16 V minimum 字段 | 原 NRST 滤波方案；仅换 0603 |
| C83/C84 | 18 pF / provisional，原 16 V minimum，DNP | HSE 负载值未定；仅换 0603，保持 DNP |
| R92/R93 | 0 Ω | 保持模拟供电/参考可配置连接，不引入未经验证的 LC；仅换 0603 |
| R122 | 10 kΩ | 原 BOOT0 下拉；仅换 0603 |
| Y1 | 8 MHz / CL TBD，DNP | 不改变晶体的原临时值，不声称 CL/ESR 已确定 |
| R402 | 10 kΩ，原 0603 | 保持 RUN_ARM 默认低；高电平时约 0.33 mA |

13 个指定 0402 的 Value、Voltage_Rating、DNP 已逐一比较保持，Footprint 全换 0603，MPN/LCSC/Supplier_PN 都写「待#5（0603）」，没有保留指向 0402 的采购字段。活动层级所有阻容均为 0603 及以上。C83/C84 的实际值应按 `CL≈C83×C84/(C83+C84)+C寄生` 结合晶体规格确定；18 pF 仅为继承的 DNP 临时值，不是本轮虚构的晶体负载参数。

### +3V3_MCU 负载估算

这是**工程预留估算，不是器件保证的整板最大电流或实测结果**。两种通讯可同时使用，不能仅用两颗收发器的空载电流相加。编码器型号未知，合计 50 mA 是本次用于评估的设计情景，实际数值待 #5。

| 项目 | 原厂依据和估算 | 设计预留 |
| --- | --- | --- |
| STM32G431 | DS12589 Rev6 表21：170 MHz Boost、ART缓存开/预取关、外设时钟关闭，25 °C典型25.5 mA、最大28 mA，85 °C最大33 mA；实际 ADC/COMP/外设和固件活动另核。预留50 mA，不把它写成MCU手册额定 | 50 mA |
| SN65HVD232，显性驱动 | SLOS346O 8.5：空载典型10 mA、最大17 mA；显性差分典型2 V、最大3 V，按双120Ω端接等效60Ω计算负载。典型示例约10+2/60=43.3 mA，预留17+3/60=67 mA | 67 mA |
| MAX3485，54 Ω负载 | Maxim 19-0333 Rev0，DE开启空载ICC典型1.1 mA、最大2.2 mA；54Ω下VOD最小1.5 V。手册没有把1.1/2.2 mA定义为带负载整颗电流。用供电上限3.6 V/54Ω+2.2 mA≈68.9 mA作正常电阻负载预留，不伪造厂家“带载最大ICC” | 69 mA |
| RUN/FAULT LED | Vf未定；两路1k，按Vf=0的3.3 V电路上界 | 6.6 mA |
| 上下拉、原监控/逻辑/参考与裕量 | 10k各有效支路约0.33 mA；给既有辅助电路留出合并预算，具体芯片工作状态待复核；不包含故障钳位持续吸流 | 5 mA |
| 两接口编码器合计，3.3 V选项 | 未选器件，无原厂电流数据；暂用合计50 mA情景，需原厂datasheet和线缆压降复核 | 50 mA（假设） |
| 合计 | 50+67+69+6.6+5+50 | **247.6 mA，约250 mA** |

因此旧 README 的 **100 mA 预算已被本版设计预留突破**；即不计编码器，上述同时驱动的预留也约 197.6 mA。不能继续沿用“最小核100mA”作为当前接口版功耗结论。底板参考输出负载及故障钳位回灌由 #3/#7 另核；50 mA 瞬态注入预算不代表允许持续注入，未混作正常负载。

[TI TLV767 RevD](https://www.ti.com/lit/ds/symlink/tlv767.pdf) 确认额定输出 **1 A**，库内 TLV76733DRVR 字段同为1A；250mA情景在额定电流以内，但额定电流不代表当前 PCB 在叠板环境已通过热验证。本地 TLV767 PDF 未能正常文本解析，本项已另核原厂在线 RevD。若以输入上限5.25 V、输出3.3 V、250 mA，忽略前级二极管/电阻压降作 LDO 发热上界，`P≈(5.25−3.3)×0.25=0.488 W`；5.0 V时约0.425 W。R301的0.47Ω在250mA情景耗散约0.029 W。实际LDO输入还受D102与R301压降影响，其余器件发热、DRV散热焊盘、铜面、环境与上层功率板热耦合由 #4/#7 校核。5V_OUT直接输出的外部负载不经过LDO，应另计输入电流与D201发热。

## 9. 首页底面/叠板规则

首页已加入要求原文：

> controller 底面只允许 0603 及以上、高度 ≤1 mm 无源件与 SWD/测试焊盘；所有接口板边侧插；叠板 inverter 在上；布局见 #4

另加入底面不放有源器件/连接器、安装孔周围φ8mm禁放，以及 #4 的机械交接：11.0mm板距=2.50mm公针塑高+8.5mm母座塑高；四角M2×11mm母-母双通铜柱；controller底部≥5mm绝缘支撑；公针尾3.0mm。J102两板同步+X移动24.00mm，pad1建议(152.73,110.95)mm，同号针同XY。**本次没有移动PCB或宣称上述布局已完成。**

## 10. 库表、新器件字段与 #5 清单

首先修正项目库表的 MyParts / MyFootprints URI：

- `${KIPRJMOD}/../../../lib/kicad_library/symbols/MyParts.kicad_sym`
- `${KIPRJMOD}/../../../lib/kicad_library/footprints/MyFootprints.pretty`

共享库只读。新元件均有 Reference、Value、Footprint、Datasheet、MPN、LCSC；未知采购字段/原厂资料明确「待#5」，允许留空的封装见下表。已知料号来自共享库已有字段，没有自行编造料号。符号使用既有 MyParts 或 KiCad 官方符号，新增本地符号仅为双线 TVS 功能占位。

| 位号/名称 | 数量与用途 | 规格要求/现状 | 原厂资料 |
| --- | --- | --- | --- |
| U201 MAX3485ESA+T | 1，半双工485 | 既有共享符号，3.3V，C18148；官方SOIC-8封装 | [ADI/Maxim](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX3483-MAX3491.pdf)；本地 `Maxim_MAX3485ESA+T_19-0333_Rev0.pdf` |
| U202 SN65HVD232DR | 1，CAN | 既有共享符号，3.3V，C30530；5/8脚NC；官方SOIC-8 | [TI](https://www.ti.com/lit/ds/symlink/sn65hvd230.pdf) |
| D201 PMEG2010ER,115 | 1，5V输出防倒灌 | 库已有20V/1A，C82288；官方CFP3/SOD123W | [Nexperia](https://assets.nexperia.com/documents/data-sheet/PMEG2010ER.pdf) |
| C209/C210 CC0603KRX7R9BB104 | 2，收发器去耦 | 100nF，0603，沿用库字段与C14663 | [YAGEO](https://www.yageogroup.com/download/specsheet/CC0603KRX7R9BB104) |
| R201–R204 | 4，快速ADC RC | 100Ω，0603；MPN/LCSC待#5 | 待#5 |
| C201–C204 | 4，快速ADC RC | 1nF、C0G要求、0603；耐压/容差按设计要求选型；待#5 | 待#5 |
| R205–R208 | 4，慢速ADC RC | 1kΩ，0603；待#5 | 待#5 |
| C205–C208 | 4，慢速ADC RC | 10nF有效电容要求、0603；考虑实际介质/DC偏压；待#5 | 待#5 |
| R209/R210 | 2，DE下拉/RO上拉 | 10kΩ，0603；待#5 | 待#5 |
| R211/R212 | 2，总线终端 | 120Ω、0805及以上，额定功率要求≥0.25W；当前候选0805，待#5核实 | 待#5 |
| JP201/JP202 | 2，端接焊桥 | 官方二焊盘 `SolderJumper_2_Open`，默认断开；PCB铜图形，无外购型号定案 | 不适用；字段待#5 |
| D202/D203 双线TVS占位 | 2，485/CAN外部保护 | **默认DNP、空封装、MPN/LCSC待#5**；按两总线分别选共模/工作电压/钳位/结电容/浪涌；本地临时符号待入共享库 | 待#5，不编型号/资料链接 |
| J201/J202/J203/J204/J205 | 5，485 4P / CAN 3P / ABZ 5P / SPI 6P / SWD 5P | GH1.25卧式、板边侧插；官方横插候选封装均存在；MPN/LCSC、线束及配套端子待#5 | [JST GH](https://www.jst-mfg.com/product/detail_e.php?series=105) |
| JP203 | 1，编码器供电选择 | 官方三焊盘 `SolderJumper_3_Bridged12`，默认1–2=3.3V；PCB铜图形 | 不适用；字段待#5 |
| R213–R219 | 7，编码器/SPI串阻 | 100Ω，0603；待#5 | 待#5 |
| R220–R224 | 5，ABZ/MISO/CS上拉 | 10kΩ，0603；待#5 | 待#5 |
| R225/R226 | 2，LED限流 | 1kΩ，0603；按最终LED Vf/If复核；待#5 | 待#5 |
| D204/D205 侧发光绿/红LED | 2，上边缘RUN/FAULT | **空封装**；侧发光方向、Vf/If、亮度/焊接方向待#5 | 待#5 |
| TP16「3V3」 | 1，BOOT临时短接参考 | 官方1.5mm测试焊盘；TP15 BOOT0保留 | PCB焊盘，无外购器件资料；字段待#5 |
| SW2（替换，非新增位号） | 1，板边侧按RESET | `Switch:SW_Push`，**空封装**；板边侧向动作，针序/机械/料号待#5 | 待#5 |
| 可选自恢复保险丝（未放置） | 新增需求，保护5V_OUT | 由雨田/料号决定；保持电流、动作电流、温度降额与压降待定 | 待#5 |

新增位号合计52：C201–C210（10）、R201–R226（26）、D201–D205（5）、J201–J205（5）、JP201–JP203（3）、TP16（1）、U201/U202（2）。空封装恰好五处：SW2、D202、D203、D204、D205；除这些待选项，全部活动器件封装可在项目/共享/官方库解析，并已核对封装焊盘包含符号全部针号。

## pinmap 7.1 落实检查

| 清单项 | 落实结果 |
| --- | --- |
| J101/J102按新表，余脚接GND | 已按64个触点逐针核对，23非GND/41GND；物理位置交#4 |
| MCU/TLV767最小系统、5V入口与3.3V参考 | 电气保持；只从J101/1、3进入，22、32参考输出 |
| MAX3485、PB9方向、下拉、4P与防倒灌 | U201/R209/R210/J201/D201，已落实 |
| CAN搬至controller | U202/C210/J202，已落实；针序固定，不另加5V |
| ABZ/SPI端子、串阻/上拉保护与PA15 CS | J203/J204、R213–R224、JP203，默认3.3V；5V推挽限制已明示 |
| RUN/FAULT侧发光、删除COMM/AUX | D204/D205与R225/R226；PD2/PB5 NC |
| 本地SWD | J205，固定五针针序 |
| 五类接口全部卧式板边侧插 | 五个GH官方横插候选封装；实际物料待#5，布局交#4 |
| 8路ADC末端RC | R201–R208/C201–C208；MCU侧独立命名，电容就近VSSA参考GND |
| PA3 ADC+COMP2及延迟 | I_BUS_MCU到PA3；100ns本地τ，门限阶跃延迟已估算 |
| 侧按RESET、BOOT取消、BOOT0下拉/TP | SW2待选、删除SW3/R401，保留R122与TP15，新增TP16 |
| HSE/NRST/BOOT0/RUN_ARM/U103/U105/CTRL_READY | 保持；PF0/PF1与晶体本地DNP；U105输出到J102/24 |
| 13个不用GPIO NC | MCU脚端13个NC，保留SWO/ROM功能的未来配置可能性 |
| 底面≤1mm规则与孔周φ8mm禁放 | 首页已注释；具体器件高度/布置由#4查实 |
| 13个0402→0603 | 值/耐压/DNP保持，采购字段待#5（0603） |
| 11mm板距/铜柱/底撑/J102位移 | 首页及接口页交接注释已写；PCB未改，布局实施归#4 |

## 对固件的影响

本次无超出 pinmap 第6节的新增引脚变化；未修改任何固件文件。

- PB9 GPIO 软件DE，初始化为低；发送前拉高，等USART **TC** 后拉低，不能以DMA搬完/寄存器空代替发送完成。PB10/PB11仍USART3 AF7，不能把PB14占给硬件DE。
- NTC=PB1 ADC1_IN12；PB0=ADC_SP1、PB2=ADC_SP2；新增PA3 ADC1_IN4。电流/温度/母线电压换算系数随#3/#5/#7前端定案。
- COMP2正输入PA3，负输入用内部DAC/VREFINT路径；按RM0440配置INPSEL/INMSEL和迟滞；TIM1_AF2.BK2CMP2E接内部BKIN2，保留PB12低有效BKIN。PA2/PA5不能用于COMP2引脚型负输入，PA2/PA12不能改成COMP2_OUT。
- SPI1 PA5/PA6/PA7 AF5，PA15软件CS为低有效（低电平选中），外部上拉使复位时无效高；释放JTDI但保留PA13/PA14 SWD。相对Rev E的SPI A，PA15本来就是CS，并非额外改脚。
- PA0/PA1 TIM2 ABZ，PA2 EXTI2只作Z中断；删除编码器B、SPI B与COMM/AUX；13个NC GPIO设为模拟输入。
- PWM保持pinmap规定端口/AF，特别PB15 TIM1_CH3N为AF4；初始化置UCPD1_DBDIS，避免PA9/PA10 dead-battery行为。
- PC5/PC8高电平点亮RUN/FAULT；PC8不配置为TIM8_CH3。
- ADC依据本次RC安排采样时间、慢速通道切换/舍弃转换和有效窗口，不能假定三相同时转换；COMP2计算须包含新增RC延迟。
- BOOT改为SWD/选项字节或BOOT0测试焊盘方式，保持pinmap的nSWBOOT0/nBOOT0等启动配置要求；不再提供BOOT按钮。
- PC7/RUN_ARM上电保持低，完成PWM/ENABLE/BRAKE、BKIN、COMP2/DAC/BKIN2与故障恢复安全初始化后才拉高；CTRL_READY来自U105，不新增一个MCU控制脚；ROM启动/复位释放不自动ARM。

## 遗留项

1. #5选定五类侧插座及配套线束、两颗侧发光LED、侧按RESET、TVS、普通阻容，补齐原厂资料/实际参数/封装与采购字段；旧13个0402对应料号由PR #12/#5同步处理，本次不写冻结BOM。
2. 5V_OUT无短路限流；是否增加自恢复保险丝由雨田/料号决定。D201仅防主电流倒灌，不能代替保险/限流，也存在原厂规定的反向漏电。
3. 编码器型号、供电电流、线缆/带宽与逻辑输出未选定；5V推挽ABZ/MISO不兼容当前直连TT_a引脚，必要时另定电平转换。默认3.3V供电，但仍须核对所选传感器的电平与电流。
4. 两路TVS默认DNP；没有选定器件即没有完整外部ESD/浪涌保护。终端电阻功率要求≥0.25W，需#5实选，0805字样不等于额定功率。
5. #3/#7确定底板源阻抗、放大器动态、阈值及钳位后，复核ADC建立/通道顺序、COMP2总延迟和保护有效性；约15A仍是建议门限。
6. 约250mA预算包含编码器合计50mA假设，未实测；#4/#7核对TLV767热、D102/R301压降发热、输入供电及叠板环境，额定1A不代表热验收完成。
7. 可选HSE保持DNP，实际晶体CL/ESR/驱动能力及C83/C84取值待#5；本轮没有冻结HSE实际参数。
8. #4落实板距/支撑、J102位移同XY、板边操作/插拔/侧发光方向、孔周禁放与底面高度。原PCB与新网表不一致是预期交接状态，不能用当前旧PCB生产。
9. 485总线整体空闲偏置与拓扑、最高通信速率待系统设计核对；R210是RO逻辑侧上拉，不是A/B差分总线偏置。本次没有凭空增加偏置器件。

## 与 pinmap 不一致/待决

**无引脚分配或排针针序不一致；没有修改 pinmap。**

- pinmap第8节“MAX3485尚未建库”是已过时的库状态描述：当前子模块1dd8f79已含该符号，按用户指定直接复用；不影响引脚。
- 任务文字中的“SN65HVD232 RS接地”无法按该型号原厂资料执行：232无RS，5/8为NC；本次依原厂和共享库标NC，未改型号与MCU引脚，详情见第5节。
- 5V编码器的逻辑兼容性与具体传感器仍待#5选定；pinmap本来要求3.3V逻辑，因此没有以改引脚或假设FT方式绕过限制。默认供电3.3V。
- 机械移动和物料最终选择分别交#4/#5；本次没有把尚未完成的布局/采购项写成已验证事实。

## 验证与导出

- 原有ERC配置未修改，未添加豁免、ERC排除或通过改引脚电气类型隐藏问题。与基线一致的全局忽略类别为“全局标签仅出现一次、四点交汇、SPICE模型、封装过滤器不匹配”；报告保留原样。
- 每批原理图/库表修改后执行 `kicad-cli sch erc --severity-all controller/hardware/g431_core/controller.kicad_sch -o /tmp/erc_ctrl.rpt`。第一批尚未实例化新页时有16项单引脚标签警告；新页接入后全部消除，最终 **0错误、0警告、0豁免项**。
- [ERC](erc_issue2.rpt)：`kicad-cli sch erc --severity-all --format report controller/hardware/g431_core/controller.kicad_sch -o controller/hardware/g431_core/review/erc_issue2.rpt`。
- [PDF](controller.pdf)：原生命令导出，10页；检查首页、MCU、RC、RESET/HSE、供电/ARM、排针及三个新页的图面和字段可读性。
- [XML网表](controller.net.xml)：KiCad原生`kicadxml`导出；直接与pinmap表比较全部64个MCU脚、64个排针触点，并检查新电路连接、NC、DNP、二极管方向和既有供电分区保持。
- [BOM](bom_issue2.csv)：KiCad原生导出；字段为Reference、Value、Footprint、MPN、LCSC、DNP、Qty，97个位号，保留DNP，无覆盖冻结BOM。
- [自动核对导出](validation_issue2.json)：734项检查通过，含封装焊盘/针号、所有新增器件字段、0603迁移、层级、BOM和冻结文件哈希校验。

资料溯源：电流、引脚结构、CADC、额定值均取原厂datasheet或库已有字段；数值计算和设计预留已明确区别于器件保证参数。共享库本地资料路径均在只读 `lib/kicad_library/datasheets/`，未改共享库。

## #12 BOM 0603 同步（2026-11-12）

以 PR #12 已合并的 [`bom/bom.csv`](../bom/bom.csv) 为准，仅同步其中 Footprint 为 `MyFootprints:C_0603_1608Metric` / `MyFootprints:R_0603_1608Metric` 且 MPN 非 `TBD` 的行。共 19 个位号，均在当前 `controller.kicad_sch` 的 10 页活动层级中找到。本节更新前文旧 13 个阻容采购字段仍为「待#5（0603）」的阶段状态。

- 实际改动 15 个位号：C63、C64、C65、C66、C67、C77、C79、C81、C83、C84、R92、R93、R122、R302、R303。
- 前 13 个位号的封装改用 BOM 的 `MyFootprints` 名称，并同步 Manufacturer、MPN、Supplier_PN、已有的 LCSC、Purchase_URL、Voltage_Rating、Tolerance；Supplier 均为 `LCSC`。电容耐压按 BOM 为 50V，100n 电容公差 10%，18p 电容公差 5%；R92/R93/R122 的 Manufacturer 为 UNI-ROYAL。
- R302/R303 的封装与采购字段原已一致，本次仅显式补齐与 BOM 相同的空 `Voltage_Rating`。其余电阻的该字段也保持 BOM 的空值。
- C304、C306、C307、C308 的上述字段原已全部一致，仅核对，原理图不改。
- 所有 Value、DNP 和已有 Design_Note 保持原样；C83/C84 仍为 `18p / provisional`、DNP，不将 BOM 的长 Design_Note 复制进原理图。未给原本没有 LCSC 的符号增设该字段，LCSC 采购编码由 Supplier_PN 保留。
- 项目 [`fp-lib-table`](../fp-lib-table) 现有 `${KIPRJMOD}/../../../lib/kicad_library/footprints/MyFootprints.pretty` 路径解析正确，已确认 `C_0603_1608Metric.kicad_mod`、`R_0603_1608Metric.kicad_mod` 均存在；库表和共享库不改。

| 位号 | 旧封装 | 新封装 | MPN | LCSC（Supplier_PN） | 处理 |
| --- | --- | --- | --- | --- | --- |
| C63 | `Capacitor_SMD:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 封装及字段同步 |
| C64 | `Capacitor_SMD:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 封装及字段同步 |
| C65 | `Capacitor_SMD:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 封装及字段同步 |
| C66 | `Capacitor_SMD:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 封装及字段同步 |
| C67 | `Capacitor_SMD:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 封装及字段同步 |
| C77 | `Capacitor_SMD:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 封装及字段同步 |
| C79 | `Capacitor_SMD:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 封装及字段同步 |
| R92 | `Resistor_SMD:R_0603_1608Metric` | `MyFootprints:R_0603_1608Metric` | `0603WAF0000T5E` | C21189 | 封装及字段同步 |
| R93 | `Resistor_SMD:R_0603_1608Metric` | `MyFootprints:R_0603_1608Metric` | `0603WAF0000T5E` | C21189 | 封装及字段同步 |
| C81 | `Capacitor_SMD:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 封装及字段同步 |
| C83 | `Capacitor_SMD:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603JRNPO9BN180` | C107040 | 封装及字段同步 |
| C84 | `Capacitor_SMD:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603JRNPO9BN180` | C107040 | 封装及字段同步 |
| R122 | `Resistor_SMD:R_0603_1608Metric` | `MyFootprints:R_0603_1608Metric` | `0603WAF1002T5E` | C25804 | 封装及字段同步 |
| C304 | `MyFootprints:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 原已一致，仅核对 |
| C306 | `MyFootprints:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 原已一致，仅核对 |
| C307 | `MyFootprints:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 原已一致，仅核对 |
| R302 | `MyFootprints:R_0603_1608Metric` | `MyFootprints:R_0603_1608Metric` | `RT0603BRD073K83L` | C861384 | 仅补空 Voltage_Rating |
| R303 | `MyFootprints:R_0603_1608Metric` | `MyFootprints:R_0603_1608Metric` | `RT0603BRD0710KL` | C95204 | 仅补空 Voltage_Rating |
| C308 | `MyFootprints:C_0603_1608Metric` | `MyFootprints:C_0603_1608Metric` | `CC0603KRX7R9BB104` | C14663 | 原已一致，仅核对 |

**跳过的 BOM 位号。** 本次符合条件的 19 行没有缺失位号。扫描整个 BOM 时，R401、SW3、U_RS485_待定、U31 不在当前活动原理图中，均跳过，不恢复旧符号；其中 R401/SW3 已在本分支删除。这四行本身也不属于本次已定料的 MyFootprints 0603 行。

**保留的新增件及待 #5 清单。** BOM 外新增件均未修改。精确筛选“官方 Resistor_SMD/Capacitor_SMD 0603 且 MPN=`待#5（0603）`”结果为 **0 个**；实际新增件的 MPN 原文是 `待#5`，符合官方 0603 封装且仍待 #5 选料的共 **32 个**：

| 页 | 待 #5 位号 | 数量 | 原封装 / 原 MPN |
| --- | --- | --- | --- |
| mcu_analog.kicad_sch | C201、C202、C203、C204、C205、C206、C207、C208 | 8 | `Capacitor_SMD:C_0603_1608Metric` / `待#5` |
| mcu_analog.kicad_sch | R201、R202、R203、R204、R205、R206、R207、R208 | 8 | `Resistor_SMD:R_0603_1608Metric` / `待#5` |
| comms.kicad_sch | R209、R210 | 2 | `Resistor_SMD:R_0603_1608Metric` / `待#5` |
| encoders.kicad_sch | R213、R214、R215、R216、R217、R218、R219、R220、R221、R222、R223、R224 | 12 | `Resistor_SMD:R_0603_1608Metric` / `待#5` |
| ui_debug.kicad_sch | R225、R226 | 2 | `Resistor_SMD:R_0603_1608Metric` / `待#5` |

R211/R212 为 0805，不计入该 0603 清单；C209/C210 已有 `CC0603KRX7R9BB104` / C14663，虽仍用官方 0603 封装，但不属于 MPN 待定件，保持全部字段原样。BOM 中 MPN 为 TBD 的其他既有件也不改。

**0402 检查。** 对当前活动层级的 10 个 `.kicad_sch` 文件执行 `rg -n '0402'`，无任何匹配；导出 BOM 的 Footprint 同样无 0402。额外扫描项目目录直属原理图，发现以下未实例化旧页仍有 **42 处** 0402 Footprint，已报告并保持原样；它们不属于当前 10 页活动原理图或本次导出：

| 未实例化旧页 | 0402 位号 | 匹配数 |
| --- | --- | --- |
| debug_comms.kicad_sch | C81、C82、R120–R129、R131–R134 | 16 |
| sensors.kicad_sch | R94–R119 | 26 |

**重新生成和核对。** KiCad CLI 10.0.7，覆盖以下审查产物：

- [ERC](erc_issue2.rpt)：按要求运行 `kicad-cli sch erc --severity-all --format report controller/hardware/g431_core/controller.kicad_sch -o controller/hardware/g431_core/review/erc_issue2.rpt`；**0 错误、0 警告、0 豁免项**。项目原有 ERC 配置和忽略类别未改。
- [PDF](controller.pdf)：原生 PDF 导出，`pdfinfo` 确认 10 页。
- [网表](controller.net.xml)：原生 `--format kicadxml` 导出；与修改前重新导出的基线比较，97 个器件、92 个网络、360 个引脚节点的连接和网络名完全一致，全部 Value 和 5 个 DNP 状态保持。
- [审查 BOM](bom_issue2.csv)：原生 KiCad BOM 导出，97 行器件，13 列为 Reference、Value、Footprint、Manufacturer、MPN、Supplier、Supplier_PN、LCSC、Purchase_URL、Voltage_Rating、Tolerance、DNP、Qty；保留 DNP，每个目标位号的字段已与原理图和源 BOM 逐项核对。

对原理图结构的比较仅允许上述位号的指定字段变化，其余符号、缓存库定义、引脚、导线、标签、层级、Value、Design_Note 和 DNP 均保持；所有 BOM 外新增件和未实例化旧页保持原样。`controller.kicad_pro`、库表、本地符号库、共享库子模块、fw/、docs/design_decisions.md、所有 PCB、`bom/bom.csv` 和 `review/bom.csv` 均未修改；未 commit/push。此前的 `validation_issue2.json` 保留为上一阶段核对快照，本次同步核对结果以本节及重新导出的上述四项产物为准。

## PR #13 第三轮（雨田 2、3 项 + 探针 N1–N6）

本节为当前状态，覆盖前文阶段记录中的“5V_OUT 尚无限流”“编码器可选 5 V”“五个空封装”“LED/TVS/RESET 待选”和“未加总线偏置”等结论。按雨田 2026-11-12 定案及 [PR #13 原评论](https://github.com/leolei2012/power_system/pull/13#issuecomment-6811001632) 实施；实际工具运行日期以 ERC 报告为准。工程仍为 10 页，**102 个器件位号**；本轮新增 U203、R227、C211、C212、R228、R229，删除 JP203。无 MCU 引脚分配变化。

### A. 5V_OUT 限流与 D201 防倒灌

- 路径改为 `J101/1,3 → +5V_CORE_IN → U203 TPS2553QDBVRQ1 → 5V_OUT_LIM → D201 阳极(2) → 阴极(1) → 5V_OUT → J201/4`。最终网表逐节点检查 5V_OUT 的对外端子，只有 J201/4，没有旁路。U203 的物理脚为 **1 IN、2 GND、3 EN、4 /FAULT、5 ILIM、6 OUT**；复用只读共享库 `MyParts:TPS2553QDBVRQ1` / `MyFootprints:SOT-23-6`。
- EN(3) 与 IN(1) 直接同接 +5V_CORE_IN，常开，不接 MCU 或 ENABLE。/FAULT(4) 开漏加 NC，不加上拉、不占 MCU 引脚，也不新增测试点。+5V_CORE_IN 由被动板间排针供电，因此新增电源标志 `#FLG203` 表示外部已供电；未改变 IC 引脚电气类型、ERC 配置或排除项。
- R227=**49.9 kΩ、1%、0603，0603WAF4992T5E / C23184**，ILIM→R227→GND。[TI SLVSBD0B](https://www.ti.com/lit/ds/symlink/tps2553-q1.pdf) PDF p3 引脚表、p5 电气特性表给 RILIM=49.9 kΩ 时 IOS **520 mA 典型、475–565 mA（−40~125 °C）**。该表以标称电阻为条件；R227 的 ±1% 对限流另有影响，不能把 475–565 mA 写成包含电阻公差的整机保证区间（p15–16 §9.1.2）。原理图保留用户指定的约 0.5 A 注释。
- C211=100 nF/0603，**CC0603KRX7R9BB104 / C14663**，与 C63 同料，IN→GND；布局 #4 须紧贴 U203。C212=**4.7 µF/0805、25 V 的设计规格**，与 C301 同规格，接 OUT→GND，确切 MPN/C 编号/DC bias 与 C301 一同待 #5；这些字段明确写待定，未虚构采购料号。
- TI p16 §9.1.3 要求输入近端 ≥0.1 µF；输出容量按负载瞬态优化，大瞬态负载可需要电解 bulk。4.7 µF 是本端口局部去耦设计值，不是厂家给出的通用最小输出容量。本端口是 485 辅助电源，没有按 USB hub 120 µF 示例照搬，也没有宣称已验证全部线缆/外接设备瞬态。
- **D201 保留**。TI p5 反向比较器门限 VOUT−VIN=95–190 mV，关断延迟 3–7 ms；p12 §8.3.2 说明延迟期间反向电流受功率 MOSFET 的导通电阻限制。因此外部电压略高于本板时，不能单靠 TPS2553 防倒灌。p6 的 VIN=0、VOUT=6.5 V、TA=25 °C 条件下 IREV 最大 1 µA；不把这个测试条件推广为全温保证。

### B. 编码器固定 3.3 V；仅加 PCB 丝印

先修改 `docs/pinmap.md` 的编码器供电描述及 485 第 4 针电源描述，再修改原理图。第 3 节、4.1/4.2 的引脚表以及 5A 全段保持逐字不变。

删除 JP203 及三条独立供电选择支路。**不再保留 VCC_ENC 别名**，J203/1、J204/1 直接使用原来 JP203/1 的 **+3V3_MCU** 网络；没有 5V_OUT 或 +5V_CORE_IN 连接。编码器端子旁加“仅支持 3.3 V 编码器（5 V 编码器不支持：PA0–PA2、PA5–PA7 为 TT_a 脚不耐 5 V）”。依据 [ST DS12589 Rev6 表11/12，p50、52–53、57](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf)，这些脚是 TT_a，PA15 是 FT_f；本轮不增电平转换、不更改引脚。

PCB 是旧布局，仅有 J101/J102，**没有 J203、J204，也没有 JP203**。使用 `/usr/local/bin/kicad-python` 的 pcbnew 新建 F.SilkS 文字，并只将其生成的一个 `gr_text` 加入原文件，避免全板重存造成额外变化。新增 **`3.3V ENCODER ONLY`，中心 (130.00, 158.00) mm，字号 0.8 mm，线宽 0.12 mm**，在 100–160 mm 板框内下边缘空白处。使用 ASCII 英文，以便常规 KiCad 笔画丝印与制造输出稳定显示。读回确认文字/层/位置；原板删除这唯一新增文字后，全部 S 表达式与原板一致，元件、焊盘、走线、过孔、区域及板框均未改变。PCB 与新原理图同步仍由 #4 完成。

### C / N1. 实物脚号和封装

- **SW2=SKRTLAE010 / C110293**，采用官方 `Button_Switch_SMD:SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010`。本地原厂 `SKRTLAE010.pdf` p2–3 的焊盘：两外侧接点 0.75×1.80 mm、中心接点 0.60×1.80 mm；两安装焊盘 1.30×0.90 mm，孔径 0.90 mm、孔距 4.25 mm。逐尺寸核对官方封装一致。p3 电路图说明实物外侧 **1、3 内部短接**，官方封装把两者同编为 pad1；中间实物2为 pad2。NRST→pad1 的两个接点、pad2→GND；MP 安装焊盘不接外部网络，符号 MP 加 NC。新本地 `CoreProtection:SKRTLAE010` 明确该映射，不能把实物3误作独立开关触点。
- **D202=SM712.TCT / C12067，RS-485**；**D203=PESD2CAN,215 / C75176，CAN**。修改前后网表均核对总线归属。分别新建 `CoreProtection:SM712`、`CoreProtection:PESD2CAN`，不再实例化功能编号占位符；**两者均物理1/2接两条线、物理3接GND**，DNP 保持。SM712 原厂 PDF p1 电路图、p2 电气表：−7/+12 V 非对称；PESD2CAN 原厂印刷p1–2（本地PDF第2–3页）、表2：1/2线、3公共端，印刷p8（本地PDF第9页）图11为SOT23外形。两颗用官方 `Package_TO_SOT_SMD:SOT-23`，三个实际 pad 编号与原厂一致，选择官方标准封装以保持可解析性。
- **D204=E6C1204YGAC1UDA / C375534（黄绿）**，**D205=E6C1204URAC1UDA / C375479（红）**。本地 `yg.pdf`、`red.pdf` **p5 封装/焊盘图完全一致**，可共用 `ControllerLocal:LED_Ekinglux_1204_SideView_3.2x1.0mm`。未找到官方库中焊盘与此三焊盘图完全相同的封装，因此按原图建本地封装。
- 两端矩形铜焊盘 **1.30×0.90 mm，内沿间隙1.90 mm，中心 x=−1.60/+1.60 mm、y=0**；中间矩形铜焊盘 **1.00×0.80 mm，x=0、y=+0.55 mm**。图中 0.50 mm 标的是两种焊盘下边缘之差：`y中=0.90/2+0.50−0.80/2=0.55 mm`，不是中心偏移0.50 mm。
- LED 原厂 p5 明确 **1=阳极+，2=阴极−**，与旧 `Device:LED` 的物理编号相反。为两型号各建临时本地符号，保留图形/功能连线，改为 **R225/R226→LED1(A)，LED2(K)→GND**。中央焊盘原图未编号且未说明电气属性，分配本地 pad3、符号3并加 NC，**不向外接网，不据此宣称它与电极绝缘或导通**；不用有钻孔含义的 NPTH 表示实物 SMT 焊盘。后续建共享库料号时需供应商补充其电气定义。
- 本地库表新增 `${KIPRJMOD}/ControllerLocal.pretty`，descr 为“临时本地封装，待料号入 kicad_library”。本地符号均注明“临时本地符号，待料号入 kicad_library”。所有实际器件符号均已分配非空封装。

### D / N2. D201 统一回流焊封装

D201 与 D103 同为 **PMEG2010ER,115 / C82288**，统一 `MyFootprints:Nexperia_CFP3_SOD123W_Reflow`。共享库已有 reviewed 封装，按 Nexperia 原厂 PMEG2010ER 回流焊推荐焊盘定义，D103 原已采用；物理1=K、2=A，不改变二极管方向。共享库文件只读。

### E / N3. 历史原理图隔离

先检查仓库所有 `.kicad_sch` 的 Sheetfile 和 `.kicad_pro` 引用，按引用文件所在目录解析路径，确认没有引用本次要移动的两份文件。`controller/hardware/controller.kicad_sch` 和 `review/migration_only/controller.kicad_sch` 虽引用同名页，但各自解析到自己的目录，不是本次移动目标。

执行两次 `git mv`，目标为 `history/debug_comms.kicad_sch`、`history/sensors.kicad_sch`。环境中 `.git` 只读，普通 `git mv` 报 index.lock 无法创建；随后复制当前索引到 `/tmp/controller_issue2_git_index`，用 `GIT_INDEX_FILE` 指向临时索引成功执行 `git mv`。**原仓库索引未写入**，工作区中表现为删除原路径与新增 history 文件，用户提交时 `git add -A` 可识别重命名。两文件内容逐字节保持；移动前后网络名/全部引脚连接分区完全相同，ERC 都是 **0 错误、0 警告**。

### F / N4. LED 电流

`yg.pdf`、`red.pdf` p2 电气特性与 p4 分档表均为 **VF=1.80–2.40 V @20 mA**；这不是 1–2 mA 下的电压范围。p3 IF–VF 曲线为典型图，读 1–2 mA 附近约 **1.8–1.9 V**（图的分辨率只支持近似读数）。因此：

`I=(VOH−VF)/R ≈ (3.3−1.8…1.9)/1000 = 1.5…1.4 mA`。

两路 **R225/R226 均保留 1 kΩ/0603**，补齐 **UNI-ROYAL 0603WAF1001T5E / C21190** 的字段。p3 相对亮度图支持用作低电流状态指示，但无在该电流下的绝对亮度保证；未虚构低电流光强值。ST DS12589 Rev6 表54（p113）的 GPIO 输出等级包含 8 mA 测试条件，1.4–1.5 mA 远低于此。实际 VOH 会略小于电源电压；使用 3.3 V 是设计估算，不是假定 GPIO 无压降。以 VF≥0、3.3 V+1%、R−1% 给两路电路电流上界 **2×3.333/990=6.733 mA**，纳入后述供电预算。

### H / N6. RS-485 总线偏置

新增 **R228：+3V3_MCU（与 U201 VCC 相同）→680 Ω→RS485_A**，**R229：RS485_B→680 Ω→GND**；均 **0603WAF6800T5E / C23228、1%、0603、默认 DNP**。偏置应只在总线一处、通常主站安装；本板作为主站或整条总线没有其它偏置时装上，各节点都装会加重负载。原理图已写此条件；R210 仍只是 RO 逻辑侧上拉。

[Maxim MAX3483–MAX3491，19-0333 Rev0](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX3483-MAX3491.pdf) **PDF p2 Electrical Characteristics，VTH 行**：接收差分判决门限 −200…+200 mV。

- **单个120 Ω终端**：`Vdiff=3.3×120/(680+680+120)=0.26757 V≈0.268 V≥0.200 V`；静态电流 `3.3/1480=2.230 mA≈2.2 mA`，是空闲且驱动器关闭的值。
- **两端各120 Ω（并联60 Ω）**：`Vdiff=3.3×60/(680+680+60)=0.13944 V≈0.139 V<0.200 V`；**不足**，不能按该偏置方案保证接收状态。任务给出的“0.134 V”与指定 680/680/60 Ω 公式不一致；按原值实际为 **0.139 V**，判断同样是不足，未为凑数改变阻值。原理图将使用算术核对后的0.139 V。
- 仅供最坏静态驱动预算：若驱动为 A低/B高，偏置方向与驱动相反，两支路可分别消耗约 VCC/680；3.333 V、R−1% 时合计 `<10 mA`。这与上面的2.2 mA空闲值是不同状态，后述预算使用10 mA，避免只算空闲电流。

### 3.3 V 静态电流上限

**工程供电设计上限：≤275 mA，不含外接编码器；外接编码器总预算≤50 mA；合计≤325 mA。** 275 mA 内已包含 J101/22、32底板参考、J102控制/PWM静态负载和J205/1 VTREF外部合计≤5 mA的约束预算。编码器的50 mA是分配的外部预算，不是未知编码器的厂家参数。

这里的“静态”指正常连续运行负载和固定总线/逻辑状态，包含170 MHz运行、两路通讯可同时带正常阻性负载，排除上电充电尖峰、线缆开关尖峰、总线故障/短路及模拟过压吸收电流。3.3 V 用3.333 V（TLV767 ±1%）作阻性负载计算；未定10 kΩ物料须满足≥9.9 kΩ的预算约束。**这是带裕量的设计/验收限值，不是所有固件、所有温度和所有未定物料条件下由厂家保证的整板最大值。** 特别是 ST 数字外设表为表征数据，没有保证的最大列，不能把典型值相加后冒称全工况最大值；板级验证仍由 #4/#7完成。

| +3V3_MCU及其滤波派生网络的负载 | 手册取值、类型与适用条件 | 本次计入 mA |
| --- | --- | ---: |
| U30 STM32G431RBT6：VDD×4、VBAT、经R92的VDDA和经R93的VREF+ | **DS12589 Rev6 表21 p76**：170MHz Boost、Flash/ART开、外设时钟关闭，25°C典型25.5、85°C最大33；**表34 p93–96**数字全外设Boost为250 µA/MHz表征值，170MHz为42.5；两ADC单端4Msps按**表60 p119**每只VDDA最大730 µA+VREF最大140 µA，共1.74；COMP2按**表73 p143**静态最大0.720；内部DAC半量程按**表70 p138**最大0.9552；VREFINTBUF按**表20 p74**最大0.020。规格/表征合计78.9352，另留21.0648用于工作码型、模拟配置、时钟与表征偏差等；100是预算，非ST额定最大值 | **100.000** |
| U102 TPS3808G33DBVR | 本地 TI TPS3808 原厂PDF **p6 §6.5**：VDD=3.3V、RESET未断言时典型2.4 µA、最大5 µA；RESET下拉支路另外算 | 0.005 |
| U201 MAX3485ESA+T | 本地 Maxim 19-0333 Rev0 **p3 Electrical Characteristics**：DE开、空载ICC典型1.1、最大2.2；另以正常总线等效负载≥54Ω及3.333/54=61.723作电阻负载上界，共63.923向上取64；不是把空载ICC当带载总电流 | **64.000** |
| U202 SN65HVD232DR | 本地 TI SLOS346O **p7 §8.5**：空载显性/隐性ICC典型10、最大17；双120Ω常见典型约10+2/60=43.3。预算用更保守的正常等效负载≥54Ω，17+3.333/54=78.723，向上取79（没有宣称这是厂家带载ICC规格） | **79.000** |
| U103 SN74LVC1G17DBVR | 本地原厂PDF **p6 §5.5/Table5-1**：ICC最大10 µA，另按一输入ΔICC最大500 µA预留中间电平附加电流；NRST拉电阻另外算 | 0.510 |
| U105 SN74LVC1G08DBVR | 本地原厂PDF **p6 §5.5**：ICC最大10 µA；ΔICC最大500 µA/输入，按两个输入共1 mA预留 | 1.010 |
| R122 BOOT0下拉 | 10k，输出/测试焊盘为高时，3.333/9.9k；平时低为0；依据欧姆定律及原理图网表 | 0.3367 |
| R402 RUN_ARM下拉 | 10k，RUN_ARM高时；同上 | 0.3367 |
| R209 RS485_DE下拉 | 10k，DE高时；同上 | 0.3367 |
| R210 RS485_RX上拉 | 10k，RO低时；同上 | 0.3367 |
| R220 ENC_A上拉 | 10k，A低时；以3.333/9.9k作保守预算，未扣串联100Ω | 0.3367 |
| R221 ENC_B上拉 | 10k，B低时；同上 | 0.3367 |
| R222 ENC_Z上拉 | 10k，Z低时；同上 | 0.3367 |
| R223 SPI_MISO上拉 | 10k，MISO低时；同上 | 0.3367 |
| R224 SPI_CS上拉 | 10k，CS低时；同上 | 0.3367 |
| R306 NRST上拉 | 10k，SW2/监控/调试器拉低时；与LED/运行等状态未必同时，仍相加保守预算 | 0.3367 |
| R302/R303参考分压 | 3.83k/10k、0.1%，3.333/(13.83k×0.999)=0.2413，向上取0.242；依据原理图/已有精密电阻物料参数及欧姆定律 | 0.242 |
| U104 TL431BIDBZR | 本地 TI SLVS543 原厂PDF **p11–14电气表**：参考输入最大4 µA，Ioff最大0.5 µA的测试条件为Vref=0、VKA=36V，不冒充本电路精确关断保证；3.3V正常低于约3.46V钳位点，另留0.100正常漏电/参考偏置预算；异常吸收不在本静态模型内 | 0.100 |
| R225+D204 RUN、R226+D205 FAULT | 两颗典型各1.4–1.5；预算按VF≥0与1k±1%电路上界6.733，向上取6.740；原厂LED p3/4及欧姆定律 | 6.740 |
| R228/R229，若装 | 默认DNP=0；单120Ω空闲2.230，驱动反向时两支路在3.333V/673.2Ω下合计9.902，向上取10；已选1%阻值/网表及欧姆定律 | 10.000 |
| C305 T491B476K010AT | 本地 KEMET原厂PDF **p1**给漏电4.7 µA（5min、25°C）；按0.050作温度/实际应用预算，明确非手册给出的全温最大值 | 0.050 |
| 其余3.3V/VDDA/VREF去耦、U101 SNS输入及未定器件漏电合并裕量 | MLCC无理想直流负载；实际绝缘/漏电按选定料号原厂PDF核定，合并预留1.000，不编造各未定料的漏电额定 | 1.000 |
| J101/22、32外部底板参考、J102控制/PWM静态负载、J205/1 VTREF | 外部约束预算，不假定向调试器供电；实际底板钳位/上拉、GPIO静态负载与VTREF合计不得超过5.000，超出须重新核算 | 5.000 |
| **逐项合计（十个0.3367按表中舍入相加）** | **手册规格、表征值和明确设计裕量合计** | **271.024** |
| **275 mA上限内剩余裕量** | 275−271.024 | **3.976** |
| **J203/1、J204/1外接编码器另列** | 两接口共用+3V3_MCU，合计预算≤50；外部逻辑通过板上上拉的耗流已在R220–224计入，不重复计入外部器件供电规格 | **≤50.000** |

网表逐负载补充：R92、R93为0Ω供电连接，不另加负载；C63–C68、C77–C80、C209/C210、C303/C304/C306/C307/C308属于上述MLCC/漏电预留，U30的VDDA/VREF已计入。ADC RC的C201–C208不直接接3.3V，R201–208接外部模拟信号，不是3.3V静态直流支路；编码器R213–219仅为串阻，信号静态负载由上拉/外部预算覆盖。D202/D203是总线保护件、默认DNP；若装，其漏电进入总线负载裕量。D103用于LDO反向应力旁路，正常本地3.3V下不增加正向耗流。Y1/C83/C84默认DNP，PF0/PF1时钟活动归入U30预算。SW2/TP15/TP16本身无静态电流，按下/外接拉高时分别算R306/R122。

R301、D101/D102、C301/C302、R304/R305在5V路径，U203/C211/C212/R227在独立5V_OUT路径，**不从TLV767的3.3V输出取电**；U101的IQ从其输入取电，不能当3.3V输出负载再相加。5V_OUT的约0.5A限流和3.3V的325mA预算是两个支路，输入供电还需同时承担两者。

[TI TLV767 RevD](https://www.ti.com/lit/ds/symlink/tlv767.pdf) **p1、p5 §6.3**输出能力1A；325mA为其32.5%，电流能力有余量。p1/§8.2要求的输出电容条件由原C303/C304保留，料号有效容量仍随#5核对。以最保守未扣输入二极管/电阻压降估算LDO功耗 `(5.25−3.3)×0.325≈0.634W`；散热、最小输入压差和叠板温升由#4验证，本轮没有通过1A字样宣称已完成热验收。共享库中的本地TLV767 PDF无法被pdftotext完整读取，本次只读查阅上述TI官方RevD补核，未替换或改写子模块文件。

### BOM 新增/变化料清单（仅更新 review/bom_issue2.csv）

| 位号 | 型号/值 | 厂家 | C编号 | 商品页 | 封装 | DNP | 需料号入 kicad_library |
| --- | --- | --- | --- | --- | --- | --- | --- |
| U203（新增） | TPS2553QDBVRQ1 | TI | C130055 | [141342](https://item.szlcsc.com/141342.html) | MyFootprints:SOT-23-6 | 否 | 否，库已有reviewed料 |
| R227（新增） | 0603WAF4992T5E，49.9k/1% | UNI-ROYAL | C23184 | [23911](https://item.szlcsc.com/23911.html) | MyFootprints:R_0603_1608Metric | 否 | 是，料号字段入库；符号/通用封装已有 |
| C211（新增） | CC0603KRX7R9BB104，100n | YAGEO | C14663 | [15331](https://item.szlcsc.com/15331.html) | MyFootprints:C_0603_1608Metric | 否 | 否，与C63同料，库已有 |
| C212（新增） | 4.7u/0805/25V，与C301同规格，确切MPN待#5 | YAGEO（同C301） | 待#5 | 待#5，与C301同料核定 | Capacitor_SMD:C_0805_2012Metric | 否 | 是，选料/DC-bias核查后建料 |
| SW2（更换） | SKRTLAE010 | ALPS ALPINE | C110293 | [111515](https://item.szlcsc.com/111515.html) | Button_Switch_SMD:SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010 | 否 | 是，临时本地符号；官方封装已有 |
| D202（落实选料） | SM712.TCT | Semtech | C12067 | [12644](https://item.szlcsc.com/12644.html) | Package_TO_SOT_SMD:SOT-23 | **是** | 是，临时本地符号 |
| D203（落实选料） | PESD2CAN,215 | Nexperia | C75176 | [76300](https://item.szlcsc.com/76300.html) | Package_TO_SOT_SMD:SOT-23 | **是** | 是，临时本地符号 |
| D204（落实选料） | E6C1204YGAC1UDA | ekinglux 亿晶源 | C375534 | [347834](https://item.szlcsc.com/347834.html) | ControllerLocal:LED_Ekinglux_1204_SideView_3.2x1.0mm | 否 | 是，临时本地符号+封装 |
| D205（落实选料） | E6C1204URAC1UDA | ekinglux 亿晶源 | C375479 | [347829](https://item.szlcsc.com/347829.html) | 同D204 | 否 | 是，临时本地符号+封装 |
| R225/R226（补采购字段，值保留） | 0603WAF1001T5E，1k/1% | UNI-ROYAL | C21190 | [立创商品页](https://www.lcsc.com/product-detail/C21190.html) | Resistor_SMD:R_0603_1608Metric | 否 | 是，料号字段入库；通用封装已有 |
| R228/R229（新增） | 0603WAF6800T5E，680/1% | UNI-ROYAL | C23228 | [23955](https://item.szlcsc.com/23955.html) | MyFootprints:R_0603_1608Metric | **是** | 是，料号字段入库；通用封装已有 |
| D201（封装统一） | PMEG2010ER,115 | Nexperia | C82288 | 沿用原符号商品页 | MyFootprints:Nexperia_CFP3_SOD123W_Reflow | 否 | 否，库已有 |
| JP203（删除） | 原3档编码器供电焊桥 | — | — | — | 从活动原理图及导出BOM移除 | — | — |

每个新增/选定实物的实例字段均填写Value、Footprint、Datasheet、Manufacturer、MPN、LCSC、Purchase_URL，同时补Supplier/Supplier_PN以兼容原BOM字段。电阻使用立创原厂PDF查看链接，TVS使用原厂PDF链接；LED资料与用户给定本地PDF内容核对。C212是用户明确允许的同C301待定选料例外，采购字段明确TBD而非空值。没有改 `bom/bom.csv` 或 `review/bom.csv`。

### 需料号建料/补库

1. `CoreProtection:SKRTLAE010`：物理1/3共接点与pad1×2的映射、pad2、MP NC；复用官方封装，待共享库建料。
2. `CoreProtection:SM712` / `CoreProtection:PESD2CAN`：物理针号已核对的两个独立临时本地符号；SOT-23通用封装无需重画。
3. `CoreProtection:E6C1204YGAC1UDA` / `CoreProtection:E6C1204URAC1UDA` 及 `ControllerLocal.pretty/LED_Ekinglux_1204_SideView_3.2x1.0mm.kicad_mod`：物理1=A、2=K、中央独立pad3；供应商需补中央焊盘电气定义后入共享库。
4. R227、R225/R226、R228/R229 的已定 UNI-ROYAL 料号入库；C212与C301统一选料、有效容量/电容规格核对后建料。本轮没有修改共享库。

### 第三轮检查与产物

每项完成后运行同一活动根工程的 `kicad-cli sch erc --severity-all --format report`；初次接U203时暴露外部5V没有电源输出标志，已补与真实外部供电对应的#FLG203，随后A–I各项ERC均0错误、0警告。项目ERC配置与原有忽略类别保持不变；不新增豁免。

最终重新导出 [ERC](erc_issue2.rpt)、[XML网表](controller.net.xml)、[13列审查BOM](bom_issue2.csv)、[10页PDF](controller.pdf)。[validation_issue2.json](validation_issue2.json) 保持原有“项目/通过/详情”检查结构，重新根据实际数据核对全部128个MCU/排针脚、既有RC/通讯/NC/供电分区及第三轮新增连接；删除旧JP203/占位封装结论，替换为固定3.3V、实物针号与零空封装检查。新增复现脚本及最终逐项摘要见同目录 `validate_pr13.py`、`pr13_third_round_result.md`。验证脚本固定以本轮修改前提交 `bb80a6c921c76b0064af353aefdfa5cc3e5e7714` 为比较基线，因此用户提交后仍可重跑。

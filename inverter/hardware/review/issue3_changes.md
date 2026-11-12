# Issue #3：inverter 原理图改动与审阅记录

日期：2026-11-12。工作分支：`hw/inverter-sch-issue3`。KiCad：10.0.7。依据：[GitHub Issue #3](https://github.com/leolei2012/power_system/issues/3)、只读 `docs/pinmap.md` 第2、4.0～4.3、5A、7.2、7.3节，以及只读 `/tmp/design_decisions.md` 的 A12～A27。

**状态：原理图审阅草稿。第10项已按任务规定暂停：3.3 V 供电的 INA241 不能保证到达 +15 A 所需的 3.15 V。板上母线比较器及其锁存接入尚未实现，不得把 ERC 的 0/0 理解为 A26 已完成。未擅改 15 A 或放大器供电。**

另一处任务文字矛盾：J101 列出的10个已连接触点 + 2个 NC + 20个 GND = 32。任务写“其余18针 GND”与逐针表不符；已严格保持 pinmap 4.1 的 **20个 GND**，该处不改针脚，提请确认“18”为笔误。

没有修改 pinmap、设计决定文件、固件、controller、PCB、仿真参数、正式 BOM/待选清单或共享库子模块；没有 commit、push、下单或读取认证文件。开工前已有暂存 `.gitmodules` 和子模块记录，保持原状。

## 1. 删除 controller 本地功能

- 从顶层删除实例，并实际删除 `debug_comms.kicad_sch`、`sensors.kicad_sch`。
- 删除 SWD J13、TTL J14、CAN J15/U31、GPIO LED D4～D7 及这些电路所属阻容；删除编码器/SPI J9～J12 及所属电阻。
- 实例化页面已无 BOOT/NRST 电气网络，也无旧的 PA/PB/PC 裸端口网络。未实例化的 `mcu*.kicad_sch` 按任务要求不处理。
- **保留 base_leds 的 D3 PWR 及 R130=2.2 kΩ；D3 不是 GPIO LED，供雨田确认保留。** R130 仅转换为0603。

## 2. J101/J102 排针

保留 `MyParts:PM254V-12-32-H85` 及原封装。下表每个未列为信号或 NC 的针都按 pinmap 接 GND。

| 连接器 | 针号 | 底板网络 |
| --- | --- | --- |
| J101 | 1、3 | +5V_INV |
| J101 | 7 / 10 / 11 | I_U / I_V / I_W |
| J101 | 14 / 15 / 23 | V_DC / NTC / I_BUS |
| J101 | 22、32 | +3V3_CORE_REF |
| J101 | 18、19 | **仅 NC 标记，未接地、网络、器件或测试点** |
| J101 | 2、4、5、6、8、9、12、13、16、17、20、21、24、25、26、27、28、29、30、31 | GND，共20针 |
| J102 | 3 / 6 / 7 / 10 / 11 / 14 | PWM_UH / PWM_UL / PWM_VH / PWM_VL / PWM_WH / PWM_WL |
| J102 | 17 / 20 / 21 / 24 / 25 | BRAKE / FAULT_N / ENABLE / CTRL_READY / BASE_READY |
| J102 | 1、2、4、5、8、9、12、13、15、16、18、19、22、23、26、27、28、29、30、31、32 | GND，共21针 |

**母座在 B 面（翻到 B.Cu），针号与 controller 一一相同、不镜像（pinmap 4.0），由 #4 落实。** 同号焊盘须保持同 XY；J101 左、J102 右以装配俯视为准。板距11.0 mm、M2×11双通铜柱、controller 底部≥5 mm绝缘支撑及 J102 同步 +X 24.00 mm/pad1建议坐标 (152.73,110.95) mm 均交 #4，未修改 PCB。

+5V_INV 只经 J101/1、3给 controller；+3V3_CORE_REF 仅供钳位/故障上拉，不与 +3V3_INV 并联。CTRL_READY 保持 controller U105 的输出定义，未改成 PC7 直连。

## 3. 删除三相电压，保留 V_DC

按实际网络识别，保留的是 **U14**，删除的是 **U15/U16/U17**；任务括号中的位号范围仅作为提示。

- 删除 V_U/V_V/V_W：R53～R67、C44～C49、U15～U17，以及通向保护页的三路网络。
- 保留 R48=240k、R49=240k、R50=10k、R51=10k、C42=100p、U14、R52=47Ω、C43。除0402转0603和原始输出改名外，值/耐压不变。
- 上臂总阻值 `240k+240k+10k=490k`，下臂10k：
  `V_ADC=V_BUS×10k/(490k+10k)=V_BUS/50`。
  65 V→1.30 V，0～65 V内不超过3.3 V；3.3 V理想满量程 **165 V**。因此不改分压。
- 保留 R68=20k/R69=13k 的1.30 V过压参考及原65 V名义过压链。
- 删除外接 NTC 座 J8 及原前端 C50=10n；R70 移至 bridge_v，见第5项。PA4/PB0/PB2 不再承接本板的三相电压/旧 NTC 信号。

## 4. 模拟接口串阻、钳位与 DNP

保护上轨全部使用 **+3V3_CORE_REF**，下轨为 GND；BAT54S 仍为1接地、2接上轨、3接钳位节点。

| 通道 | 360Ω限流 | BAT54S | 保留100Ω隔离 | 末端电容，均 DNP | 排针 |
| --- | --- | --- | --- | --- | --- |
| I_U | R201 | D201 | R84 | C69=1n | J101/7 |
| I_V | R202 | D202 | R85 | C70=1n | J101/10 |
| I_W | R203 | D203 | R86 | C71=1n | J101/11 |
| V_DC | R204 | D204 | R87 | C72=1n | J101/14 |
| NTC | R208 | D208 | R91 | C76=1n | J101/15 |
| I_BUS，新增 | R213 | D211 | R214 | C211=1n | J101/23 |

删除 R205～R207、D205～D207、R88～R90、C73～C75。新增通道照搬保留通道，360Ω用于异常输入/钳位电流限制，100Ω保留作串联隔离；**实际末端 RC 在 controller，本板不再装这些滤波电容**。1n值仅保留作调试位置，不作为已装滤波。电流/V_DC 通道前级另有原47Ω输出隔离，总串阻507Ω；NTC总串阻460Ω。新 I_BUS 的 R212=47Ω 同样隔离 INA 输出与接口负载。

状态返回保留 R210/R211=1k、D209/D210 及 R209=10k：`BASE_READY_RAW→保护→BASE_READY`、`FAULT_N_RAW→保护→FAULT_N`。R143=10k上拉仅接 +3V3_CORE_REF；板内 raw 命名用于明确串阻两侧，外部网络按 pinmap 命名。

## 5. 板载 NTC

TH1：Murata NCP18XH103F03RB，0603，10kΩ±1%，B25/50=3380 K±1%，−40～125 °C，额定100mW，允许工作电流0.31mA@25 °C，C13564。符号 `Device:Thermistor_NTC`，封装 `Resistor_SMD:R_0603_1608Metric`。

来源：[Murata产品页](https://www.murata.com/en-global/products/productdetail?partno=NCP18XH103F03RB)；本次网页403，采用任务给定规格，并核对[原厂产品数据表的Farnell镜像](https://www.farnell.com/datasheets/2048079.pdf)中的 R、B、功率、电流及典型耗散常数1mW/°C。采购：[立创C13564](https://www.lcsc.com/product-detail/C13564.html)。型号有 NRND/Not For New Designs 提示，替代型号待#5；[Murata型号清单](https://www.murata.com/-/media/webrenewal/tool/library/common-pdf/static-model/component-list-ntc-2508.ashx?cvid=20250930011345000000&la=ja-jp)也列NRND，不据此擅换型号。

接法：`+3V3_INV→R70 10k/0.1%/0603→NTC_RAW→TH1→GND`；再经第4项保护成为 NTC→J101/15→PB1。**布局时贴近 V 相下管（bridge_v Q4），交 #4。** R70值按指定10k，0.1%用于降低上拉对温度换算的误差。

按任务指定B值作常B近似：

`R(T)=10,000×exp[3380×(1/(T+273.15)−1/298.15)] Ω`

`I=3.3/(10,000+R)`，`V_NTC=3.3R/(10,000+R)`，`P_NTC=I²R`。

| 温度°C | NTC近似Ω | 节点V | 偏置mA | 自热功率mW | ΔT近似°C，δ=1mW/°C | 相对0.031mA建议 |
| --- | --- | --- | --- | --- | --- | --- |
| 25 | 10000.00 | 1.650000 | 0.165000 | 0.272250 | 0.272 | 5.32× |
| 60 | 3039.19 | 0.769167 | 0.253083 | 0.194663 | 0.195 | 8.16× |
| 80 | 1710.89 | 0.482110 | 0.281789 | 0.135853 | 0.136 | 9.09× |
| 100 | 1024.32 | 0.306618 | 0.299338 | 0.091783 | 0.092 | 9.66× |

25 °C偏置0.165mA，低于0.31mA允许电流，但高于其1/10即0.031mA的低自热建议 **5.32倍**；25 °C典型自热温升约0.272 °C。功率最大值出现在 R_NTC=R70=10k，`Pmax=3.3²/(4×10k)=0.27225mW`。其余温度的δ未给保证值，表内ΔT仅沿用25 °C典型δ作估算；0.31mA也仅是25 °C参数，不能当作全温额定电流。

B25/50不能保证60～100 °C外推精度，固件最终应采用原厂R-T表/相应拟合；板上实际散热耦合也须校准。未为了降低自热自行改变指定10k或增加GPIO；连续偏置的自热接受程度交雨田，替代NTC交#5。

## 6. D1 改理想二极管

删除 D1 MBRD20150CT-13，加入 U32 LTC4359IS8#PBF 与 Q9 `MyParts:BSC110N15NS5ATMA1`（C412739，150 V，沿用桥臂型号）。选型依据：[ADI LTC4359 Rev F](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4359.pdf)，并对照提供的本地Rev D原文。

- 工作4～80 V、反向输入保护到−40 V，正向覆盖12～60 V。[TI LM74700-Q1](https://www.ti.com/product/LM74700-Q1)上限65 V，对60 V及65 V过压附近的裕量较少；此对比仅指该65 V型号，不泛指所有LM74700变体。
- **S8实际脚号：GATE=1、SOURCE=2、NC=3、IN=4、SHDN=5、VSS=6、NC=7、OUT=8。** 任务暂列的 OUT1/GATE8 与原厂相反，按任务“以原文为准”纠正。两个NC均放标记。
- F1后 `DC_FUSED` 接 Q9源极1/2/3、U32 SOURCE/IN/SHDN；Q9漏极5/6/7/8接VBUS与U32 OUT；U32 GATE接Q9/4。Q9体二极管从输入源极指向母线漏极。SHDN接IN常使能。
- **VSS按原厂图4经R215=1k回到GND**，不是另一个系统地。加入D213 SMAT70A-13-F（70 V standoff）和D214 SMAJ24A-TR（24 V standoff），两者共阳极，阴极分别接DC_FUSED、IDEAL_VSS，按图4限制正/负输入瞬态。
- 24 V及以上按原厂要求加栅源齐纳 D212 DDZ9699T，12 V，阴极接GATE、阳极接SOURCE。[DDZ9699T原厂手册](https://www.diodes.com/datasheet/download/DDZ96xxT-DDZ97xxT.pdf)、[SMAT70A原厂手册](https://www.diodes.com/datasheet/download/SMAT70A.pdf)、[SMAJ24A原厂手册](https://www.st.com/resource/en/datasheet/smaj24a.pdf)。
- C213沿用已有库内2.2µF/100V/X7R器件，跨OUT/VSS，采用原厂图4的COUT≥1.5µF方案；标称2.2µF留一定余量，60V偏压下有效电容是否仍≥1.5µF待#5核对。没有把原厂的COUT误放在IN脚，也没有凭空添加未推荐的IN RC。
- R215阻值1k来自图4；按−40 V反接和24 V名义钳位估算，`I≈(40−24)/1k=16mA`，`P≈0.256W`。选2512封装、设计要求≥0.5W，实际料号/工作电压/热降额待#5，不把该要求冒充现成器件额定值。

Q9导通损耗采用[Infineon BSC110N15NS5 Rev2.6](https://www.infineon.com/assets/row/public/documents/24/49/infineon-bsc110n15ns5-datasheet-en.pdf)的 `RDS(on),max=11mΩ @VGS=10V、Tj=25 °C`：8A时 `P=8²×0.011=0.704W`，压降约88mV。对比任务给出的原肖特基6～7.5W评审估计值，热损耗明显降低；该6～7.5W不是本次重新取得的肖特基保证参数。热态RDS(on)会升高，0.704W不能当全温上限。

**理想二极管阻断回馈电流，制动/再生能量只能由现有制动斩波 J5、Q7 吸收。** 制动电阻能量、占空比与母线过压协调仍需#7及实测。D2原候选SMCJ60CA保持DNP，不把它当已落实的瞬态保证。

I档 `LTC4359IS8#PBF` 为−40～85 °C；需要125 °C档时为 `LTC4359HS8#PBF`，供雨田按板温选择。控制器−40 V的反接边界不等于能承受60 V电源反接到−60 V；如要求−60 V反接，需另作保护评估，不在此稿擅改型号。

## 7. 保险 F1

F1改为 Littelfuse **0476008.MRSN**，8 A、125 VDC、2410、断流300 A@125 VDC、标称冷电阻0.0112Ω。原0476015同系列封装不变，使用临时本地符号，LCSC待#5。依据：[476原厂手册](https://www.littelfuse.com/assetdocs/littelfuse-fuse-476-datasheet?assetguid=9862ea73-9130-481f-996c-12625fcc7ed2)、[原厂8A产品页](https://www.littelfuse.com/products/fuses-overcurrent-protection/fuses/surface-mount-fuses/nano-2-fuses/476/476008)。

125 VDC大于65 V母线硬件过压点；8 A冷态估算 `P=8²×0.0112≈0.7168W`、压降约89.6mV，只用于提示温升，不代表热态工作点。**5 Arms是相电流，不能直接当直流保险连续电流；8 A是输入上限方向，不承诺在所有温度下长期运行8 A。** 环境/板温、纹波、440µF充电浪涌、时间电流曲线、故障源预期短路电流及保险降额需#5与雨田确认；不编造降额系数，不将保险当15 A快速短路关断器。

## 8. 功率端子

| 位号 | 器件 / LCSC | 按库符号的接线 |
| --- | --- | --- |
| J3 | MyParts:XT60PW-M.G.Y / C98732 | 1=−/GND；2=+，经F1输入 |
| J2 | MyParts:XT30PW-M30.G.Y / C431092 | 1=−/GND；2=+，接原辅助输入F2 |
| J4 | MyParts:MR60PW-M.G.B / C19268044 | **1=U_PHASE、2=V_PHASE、3=W_PHASE** |
| 线端，不上板 | MR60-F / C3040681 | 配J4，装配线序与1/2/3对应；不计入板上BOM |
| J5 | 原制动电阻焊线孔 | 保持VBUS/BR_SW；P5仍待雨田确认 |

共享库MR60只给1/2/3电气编号，不定义U/V/W；上表为本项目相序分配。符号/封装及其原厂图纸链接均从库中复制，不自行重编号。

## 9. 高端母线电流

新增 `bus_current.kicad_sch`。功能名 **RS_BUS** 使用合法可注释位号 **RS4**（字段 `Design_Name=RS_BUS`），避免无数字位号造成KiCad网表导出“annotation errors”。

RS4完全沿用RS1～RS3的型号 `HoJLR2512-3W-5mR-1%`、5mΩ/3W/1%、库封装 `MyFootprints:Milliohm_HoJLR2512_Pad2.1x4.0mm_Gap4.1mm`、C2903482及库内手册链接，未改相分流。

`输入→F1→理想二极管→VBUS（C19/C20、J5/Q7制动）→RS4→VBUS_BR（三相上管漏极）`

- RS4两端各走独立取样线，按四端开尔文连接，**这是两端子器件的四线走线法，不冒充四焊盘器件**；交#4。
- C21/C22各2.2µF/100V/X7R移到VBUS_BR。保证桥开关回路短，代价是短路初期桥侧4.4µF放电不经RS4；随后C19/C20母线电解放电全部经RS4。60 V时该桥侧能量 `E=½×4.4µF×60²=7.92mJ`，不能声称初始短路能量也被检测。
- RS4在8 A时 `I²R=0.32W`，15 A时1.125W；3W是库已有额定字段，实际热降额/脉冲耐量需按库手册及布局核验。
- U33=INA241A2IDDFR：临时本地符号复制INA241A1IDDFR，改增益/型号/供应字段；使用官方 `Package_TO_SOT_SMD:SOT-23-8`，与现有相电流DDF同封装类别。
- DDF脚号按[TI INA241A Rev D](https://www.ti.com/lit/ds/symlink/ina241a.pdf)：1 IN−、2 GND、3 REF2、4保留脚接GND、5 OUT、6 VS、7 REF1、8 IN+。IN+接VBUS、IN−接VBUS_BR，母线流向桥为正。
- **同相电流拓扑：+3V3_INV供电、C210=100n去耦、REF1/REF2同接U13缓冲的VBIAS_1V65、R212=47Ω输出隔离。现有相电流输入没有额外RC，母线也不添加输入RC。** 将原局部VBIAS_1V65标签升级全局连接，没有复制第二套参考。
- 路径：I_BUS_RAW→R212→I_BUS_PORT→R213/D211/R214→I_BUS→J101/23；TP18测I_BUS。三相原始输出命名I_U_RAW/I_V_RAW/I_W_RAW，保持相比较器取钳位前信号；保护后网名才是I_U/I_V/I_W。

换算：`20 V/V×5mΩ=0.100 V/A`，`I=(VOUT−1.65)/0.100 A`；理想0～3.3 V对应±16.5 A。手册全温RL=10kΩ到地的摆幅高端最坏为VS−0.2 V，3.3 V供电下仅保证到3.1 V，故按该项得到正向约 **+14.5 A**；低端20mV对应约−16.3 A。该值仅为摆幅边界，不能代替所有输出电压/负载下的精度保证；手册增益误差测试输出区间也不覆盖接近顶轨的所有情况。

## 10. 母线比较器与故障锁存——按要求暂停

**未放置板上母线比较器、未把不可靠的15 A检测接进锁存，也未降低门限。** `InverterLocal` 中已建好TLV7021DBVR备用符号：SOT-23-5，1 OUT、2 VEE、3 IN+、4 IN−、5 VCC；开漏、内置迟滞，260ns为典型传播延迟，不能当系统最大关断时间。原厂：[TLV7021 Rev F](https://www.ti.com/lit/ds/symlink/tlv7021.pdf)。

### 暂停原因及两种改法

指定15 A需要 `1.65+15×0.1=3.15V`。现有3.3 V供电按手册只能保证3.1 V，少50mV；典型摆幅VS−0.07 V不能代替最坏保证。没有取得改变供电的授权，因此保留第9项的原供电并暂停此处。

1. **改门限**：保持3.3 V，降低到小于3.1 V并留供电、参考、分流、放大器和比较器误差裕量；摆幅折算14.5 A只是边界，不能直接当推荐新门限。该方法改变雨田定的15 A，须批准后才能实施。
2. **改供电**：母线INA改用现有+5V_INV，REF1/REF2仍接原1.65 V，阈值参考仍取+3V3_INV；保持15 A。比较器可一并5 V供电并以3.3 V上拉输出，使高故障电流时INA原始输出仍在比较器共模范围内。还须核接口钳位注入电流、失电/上电顺序和有效输出负载；不增加MCU引脚。该方法偏离“供电完全照搬相电流”，本稿未实施。

### 可审阅的门限候选，尚未落图

E96 0.1%：上臂1.00k、下臂21.0k，从+3V3_INV分压：
`VTH=3.3×21/(1+21)=3.150000V`，名义 **15.000A**。
两阻0.1%极限组合为3.149713～3.150286 V；仅分压电阻折算14.997134～15.002861 A（固定零点/灵敏度/供电）。1k/21k两值均为E96，器件MPN/LCSC待#5。

TLV7021输入失调最大±8mV，单独折算±0.08 A；迟滞典型4.2mV，范围1.2～14mV，对应完整回差典型0.042 A、范围0.012～0.140 A。若按5 V供电方案，叠加分压0.1%、R40/R41各0.1%、U13失调±1.6mV、INA241A2失调±10µV/增益±0.01%、分流±1%和比较器±8mV作25 °C静态预算，约 **14.734～15.272 A**，尚未计迟滞、供电误差、温漂及瞬态。此为候选设计预算，不是本版已实现/全温保证。

### 极性及拟接入链路，供电决定后再实施

指定IN+=I_BUS_RAW、IN−=VTH时：I_BUS_RAW低于阈值，开漏输出导通为低；超过阈值则释放、由10k上拉到+3V3_INV成为高。**不能把这个原始输出直接当低有效OC_BUS_N送进健康与门链，否则保护极性相反。** 选钳位前I_BUS_RAW是为了不让接口串阻、调试电容、controller RC或外部钳位负载增加本地保护延迟。

拟保留指定输入极性，用一片现有库型号74LVC00APW,118（另加100n去耦）完成反相与健康汇合，不动MCU/排针：

```text
INA241A2 I_BUS_RAW
  → TLV7021 IN+；IN−=3.15V
  → OC_BUS_RELEASED（开漏，10k上拉；超过门限时高）
  → 新NAND A两输入并接作反相 → OC_BUS_N（健康高，故障低）

原相过流/电源健康链 → HEALTH_PREBUS
HEALTH_PREBUS 与 OC_BUS_N
  → 新NAND B → 新NAND C两输入并接作反相 → HEALTH_ALL
  → 同时驱动原锁存/许可/故障输出逻辑
新NAND D固定输入，输出NC，不留输入悬空。
```

**上图是待实施方案，不是当前网表中的电路。** 当前没有OC_BUS_N或这片新逻辑器件。

### 当前实际链路及拟修改后各级行为

1. U18/U19/U20每相两个TLV3202比较器分别输出OC_*_HIGH_OK/LOW_OK，六路均健康为高；U21保留BUS_OV_OK/DRV_UV_OK。
2. U22A～D、U23A～D、U24A/B把六路相过流、电压、电源健康、BASE_LOGIC_OK、DRV_PG_LOGIC、AUX_FLT_N逐级相与，当前输出HEALTH_ALL。接母线后此处先成为HEALTH_PREBUS，再按上图并入母线健康，仍输出HEALTH_ALL。
3. HEALTH_ALL接U28A（74LVC74）/S，/R固定高、D=0；任一健康信号低使/S异步置位Q=1，/Q=NO_LATCH变低，故障恢复也不自行清除。
4. U24D得到HEALTH_UNLATCHED=HEALTH_ALL∧NO_LATCH；U26D先以ENABLE_IN∧CTRL_READY产生ENABLE_QUALIFIED；U25A再得到DRIVE_PERMIT=HEALTH_UNLATCHED∧ENABLE_QUALIFIED。
5. U25B/C/D、U26A/B/C分别与六路PWM相与；DRIVE_PERMIT低则六路HIN/LIN全部低。
6. U27B输出FAULT_ACTIVE=NOT(HEALTH_ALL∧NO_LATCH)，经R74驱动Q8，拉低FAULT_N_RAW；经过R211/D210后为FAULT_N→J102/20→PB12/BKIN。失去底板电源时不能靠Q8证明健康，继续使用BASE_READY/CTRL_READY互锁。
7. 复位不变：U27A反相ENABLE_QUALIFIED，U24C与HEALTH_ALL生成RESET_REQUEST，R73=10k/C55=10n延迟后给U28时钟。需故障解除且ENABLE低至少1ms再明确重使能；ENABLE高时恢复健康不会自动清除锁存。未加入NRST/BOOT路径。

## 11. 相过流约±12 A

保持INA241A1增益10、相分流5mΩ，灵敏度50mV/A。保持原串联分压拓扑，全部选E96、0.1%：

| 门限 | 从+3V3_INV到GND的串联电阻 | 取样点 | 名义电压 | 固定1.65V零点折算 |
| --- | --- | --- | --- | --- |
| 低门限 | R42=20k → R43=1.43k → R44=10k | R43/R44节点 | 1.049952 V | −12.000955 A |
| 高门限 | R45=10k → R46=1.43k → R47=20k | R45/R46节点 | 2.250048 V | +12.000955 A |

`VLO=3.3×10/31.43`；`VHI=3.3×21.43/31.43`；`I=(VTH−1.65)/0.05`。
仅三个分压电阻各0.1%极限组合：VLO=1.048521～1.051385 V、VHI=2.248615～2.251479 V，名义正/负门限绝对值约11.9723～12.0296 A（零点、增益、分流、供电固定）。参考分压电流约105µA，阻值在原量级，既不改拓扑，也不增额外RC延迟。

按标称3.3 V，将上述分压误差、R40/R41各0.1%、U13失调±1.6mV（原厂25 °C测试条件）、TLV3202失调±5mV、INA241A1失调±10µV/增益±0.01%、分流±1%组合预算，静态约 **±11.687～±12.321 A**。不是全温保证；电源误差、温漂、动态误差、实际负载及布局噪声需#7/实测。

[TLV3202原厂手册](https://www.ti.com/lit/ds/symlink/tlv3202.pdf)内置迟滞典型1.2mV，对应完整回差约 **0.024 A**；若按中心对称近似，单侧约0.012 A，不是保证的上下门限偏移。不新增外部正反馈。原图“no intentional hysteresis”说明已改为明确内置迟滞；首事件仍进入锁存。U13失调依据[TLV9001原厂手册](https://www.ti.com/lit/ds/symlink/tlv9001.pdf)，非凭空估值。

## 12. 顶面测试点

| 网络 | 位号 | 说明 |
| --- | --- | --- |
| I_U / I_V / I_W | TP11 / TP12 / TP13 | 保留位号，改测排针侧保护后网络；raw信号仍供相比较器 |
| I_BUS | TP18，新增 | 保护后、到J101/23 |
| FAULT_N | TP16 | 保护后、到J102/20 |
| ENABLE | TP17 | Value改ENABLE，排针侧；板内ENABLE_IN仍保留 |
| GND / VBUS / +5V_INV / +3V3_INV | TP19 / TP20 / TP21 / TP22，新增 | 均为Connector:TestPoint、1.5mm裸测试焊盘 |

**均放顶面（#4落实）**。测试焊盘没有独立采购器件，MPN/LCSC/Datasheet字段明确标“待#5（PCB测试焊盘，无独立物料）”，不编造厂家型号。

## 13. 首页布局说明

首页已加入以下内容（换行仅用于可读性）：

> 叠板 inverter 在上；母座 J101/J102 在 B 面；B 面整面 GND（大量缝合过孔接 In1/In4），散热铜在顶面和内层；顶面预留散热片和机械固定，不挡电解电容和焊线；无风扇、无铜条；2 oz 铜；J4 MR60 放上边缘、挪 C20、功率级左移 8–10 mm 再下移 2–3 mm；母线分流开尔文走线；验收 5 Arms/12–60 V/20 kHz，环境 ≤30 °C；布局见 #4。

本项是布局交接说明，没有翻转封装、移动PCB器件、增加过孔/铜面或改安装孔。

## 14. 器件字段、本地库与0603迁移

MyParts URI：`${KIPRJMOD}/../../lib/kicad_library/symbols/MyParts.kicad_sym`；MyFootprints URI：`${KIPRJMOD}/../../lib/kicad_library/footprints/MyFootprints.pretty`。共享库只读。

新增/替换但共享库暂无的LTC4359、INA241A2、TLV7021、0476008、DDZ9699T、SMAT70A、SMAJ24A均在 `InverterLocal.kicad_sym`，Description含“临时本地符号，待 #5 入 kicad_library”。新本地器件采用KiCad官方封装；F1按明确要求沿用原共享库保险封装。NTC按明确要求采用Device:Thermistor_NTC。沿用已存在的MOS、分流、去耦/高压电容及BAT54S继续使用其库定义/封装，未写入共享库。

每个实际新增器件均有Reference、Value、Footprint、Datasheet、MPN、LCSC；未知器件字段写待#5，设计需求与厂家保证参数分开。候选TLV7021尚未实例化，不混入当前板上BOM。

原117个0402中，保留且改0603 **61个**，删除 **56个**。保留位号：

C17、C40、C41、C42、C43、C54、C55、C56、C57、C58、C59、C60、C61、C62、C69、C70、C71、C72、C76、R13、R40、R41、R42、R43、R44、R45、R46、R47、R52、R68、R69、R70、R71、R72、R73、R74、R75、R76、R77、R78、R79、R80、R81、R82、R83、R84、R85、R86、R87、R91、R130、R135、R136、R137、R138、R139、R140、R141、R142、R143、R160。

删除的原0402位号：

C44、C45、C46、C47、C48、C49、C50、C73、C74、C75、C82、R57、R62、R67、R88、R89、R90、R94、R95、R96、R97、R98、R99、R100、R101、R102、R103、R104、R105、R106、R107、R108、R109、R110、R111、R112、R113、R114、R115、R116、R117、R118、R119、R120、R121、R123、R124、R125、R126、R127、R128、R129、R131、R132、R133、R134。

转换保持原值/耐压，原MPN/LCSC/Supplier_PN等采购指向改为“待#5（0603）”；R42～R47、R70的电路取值/精度变化另在第5/11项说明。未实例化mcu页面不计入本次迁移。

## 对固件的影响

- 外部引脚/AF/ADC仅按已合并pinmap：NTC→PB1 ADC1_IN12，I_BUS→PA3 ADC1_IN4/COMP2，保留相电流PC0/PC1/PC2与V_DC PC3；三相电压删除，PB0/PB2备用脚在底板NC。
- I_BUS换算名义0.1V/A、零点来自1.65V；相电流保持0.05V/A；V_DC保持50:1；NTC采用指定10k/3380K近似，最终用R-T表校准。保护参数随本说明及#7校核，未修改仿真/固件文件。
- controller侧ADC RC值和采样时间由#2/固件处理。I_BUS的RC也计入COMP2/BKIN2路径延迟。COMP2/BKIN2初始化、PA3 INP、内部DAC/VREFINT INM、PB12低有效BKIN和UCPD1_DBDIS仍按pinmap；本板不额外占GPIO。
- **本稿额外需要明确的软件/测试限制：15 A板上母线比较器尚未实现，且3.3 V INA输出不能保证到3.15 V；不得宣称已有独立于固件的A26母线15 A保护。** MCU COMP2也使用同一放大器输出，不能用MCU阈值配置掩盖该模拟摆幅问题。
- 内部网络raw/port/保护后命名区分、RS4的合法位号与测试点位置不改变MCU引脚或通信协议。CAN/485/编码器/LED迁移仍由controller原理图负责。

## 新增/替换及占位器件交 #5

表中“待#5”为尚未核实的采购信息；PCB测试焊盘无独立物料。下表参数来自任务、原厂手册或当前库字段；电阻精度/功率是明确的设计要求。

| 位号 | 名称/用途/规格或设计要求 | Datasheet | LCSC |
| --- | --- | --- | --- |
| U32 | LTC4359IS8#PBF；理想二极管控制器，SO-8；H档供雨田选 | [原厂/库内来源](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4359.pdf) | 待#5 |
| Q9 | BSC110N15NS5ATMA1；150V，沿用桥臂MOS | [原厂/库内来源](https://www.infineon.com/assets/row/public/documents/24/49/infineon-bsc110n15ns5-datasheet-en.pdf) | C412739 |
| D212 | DDZ9699T；12V栅源齐纳，SOD-523 | [原厂/库内来源](https://www.diodes.com/datasheet/download/DDZ96xxT-DDZ97xxT.pdf) | 待#5 |
| D213 | SMAT70A-13-F；70V输入TVS，SMA | [原厂/库内来源](https://www.diodes.com/datasheet/download/SMAT70A.pdf) | 待#5 |
| D214 | SMAJ24A-TR；24V反向TVS，SMA | [原厂/库内来源](https://www.st.com/resource/en/datasheet/smaj24a.pdf) | 待#5 |
| R215 | VSS限流；1k，2512；设计要求≥0.5W；实际额定值待#5 | 待#5（VSS 1k 阻值依据 LTC4359 图4） | 待#5 |
| C213 | 理想二极管OUT/VSS旁路；沿用2.2µF/100V/X7R，偏压有效值需≥1.5µF | [原厂/库内来源](https://www.yageogroup.com/download/specsheet/CS1210KKX7R0BB225) | C5578983 |
| F1 | 0476008.MRSN；8A/125VDC/2410，替换15A，同封装 | [原厂/库内来源](https://www.littelfuse.com/assetdocs/littelfuse-fuse-476-datasheet?assetguid=9862ea73-9130-481f-996c-12625fcc7ed2) | 待#5 |
| J3 | XT60PW-M.G.Y；母线输入，1−/2+ | [原厂/库内来源](https://atta.szlcsc.com/upload/public/pdf/source/20260730/06F30CB14C3A2EA0CED87E53A8C09E79.pdf) | C98732 |
| J2 | XT30PW-M30.G.Y；辅助输入，1−/2+ | [原厂/库内来源](https://atta.szlcsc.com/upload/public/pdf/source/20260730/844EFA5C28E5E2C849E53DEDB0B6B4E4.pdf) | C431092 |
| J4 | MR60PW-M.G.B；三相1U/2V/3W | [原厂/库内来源](https://atta.szlcsc.com/upload/public/pdf/source/20231221/53B4DC893AF29571B873350396E957CB.pdf) | C19268044 |
| TH1 | NCP18XH103F03RB；10k±1%/3380K±1%/0603；NRND替代待#5 | [原厂/库内来源](https://www.murata.com/en-global/products/productdetail?partno=NCP18XH103F03RB) | C13564 |
| R70 | 板载NTC上拉；10k/0.1%/0603，既有位号转移 | 待#5 | 待#5（0603） |
| RS4 | 功能名RS_BUS；HoJLR2512-3W-5mR-1%，同RS1～3 | [原厂/库内来源](https://www.lcsc.com/datasheet/C2903482.pdf) | C2903482 |
| U33 | INA241A2IDDFR；20V/V、−5～110V共模、1.1MHz、DDF/SOT-23-8 | [原厂/库内来源](https://www.ti.com/lit/ds/symlink/ina241a.pdf) | 待#5 |
| C210 | INA供电去耦100n，照搬相电流 | [原厂/库内来源](https://www.yageogroup.com/download/specsheet/CC0603KRX7R9BB104) | C14663 |
| R212 | INA输出隔离47Ω/0603，照搬相电流 | 待#5 | 待#5 |
| R213 | I_BUS钳位限流360Ω/0603 | 待#5 | 待#5 |
| R214 | I_BUS串联隔离100Ω/0603 | 待#5 | 待#5 |
| D211 | BAT54S,215；I_BUS钳位，参考CORE_REF | [原厂/库内来源](https://assets.nexperia.com/documents/data-sheet/BAT54S.pdf) | C47546 |
| C211 | I_BUS调试电容1n/0603，DNP | 待#5 | 待#5 |
| TP18～TP22 | I_BUS/GND/VBUS/+5V_INV/+3V3_INV测试焊盘；官方1.5mm焊盘 | PCB铜焊盘，无独立器件 | 待#5（无独立物料） |
| 待实施，未入板上BOM | TLV7021DBVR；开漏、内置迟滞、SOT-23-5，母线15A比较器 | [TI](https://www.ti.com/lit/ds/symlink/tlv7021.pdf) | 待#5 |
| 待实施，未入板上BOM | 74LVC00APW,118及100n去耦；第10项极性/健康汇合方案，沿用现有库型号 | [Nexperia](https://assets.nexperia.com/documents/data-sheet/74LVC00A.pdf) | 库内已有型号，实施时核对 |
| 待实施，未入板上BOM | 1.00k/21.0k E96 0.1%门限分压、10k输出上拉，均≥0603 | 实际器件手册待#5；阻值计算见第10项 | 待#5 |
| 不上板 | MR60-F线端 | 与板端配对的采购项，规格待#5核 | C3040681 |
| 既有位号批量变更 | 61个0402改0603及R42～R47新值；保留原耐压，0.1%等要求按图 | 实际0603料号/手册待#5 | 待#5（0603） |

R212/R213/R214、R215、R70、R42～R47的具体厂商料号未编造；#5需按图的值、精度、耐压和功率要求补全。临时本地符号的正式入库、C编号及封装土地核验也交#5。

## 遗留项与需雨田拍板的问题

1. **第10项供电/门限取舍**：允许母线放大器改+5V_INV并保留15A，还是调整门限？未得到选择前，A26比较器及新故障汇合级保持未实施，不能宣称全部验收通过。
2. **J101计数**：任务“18个GND”为笔误，而pinmap逐针表为20个GND；请确认文字，保持现有针脚不改。
3. **理想二极管温度档**：I档−40～85 °C还是H档−40～125 °C；验收环境≤30 °C仍需测局部板温。VSS采用原厂图4的1k回地，供审阅确认。
4. **反接边界**：LTC4359给出−40 V保护；是否要求60 V电源完整反接到−60 V？若要求，当前器件边界不覆盖，需后续方案评估。
5. **NTC**：接受指定10k连续偏置的25 °C约0.272 °C典型自热估计，还是另定偏置方案；NRND替代交#5核。没有擅改10k。
6. **F1连续工况/热降额与浪涌**：8 A是输入方向，不当作无条件连续额定；由雨田/#5结合实际工况、时间电流曲线确认。
7. **D3 PWR保留**，供雨田确认；J5焊线孔是否换型仍为P5，本次保持。
8. #4：排母B面、同号XY、J102位置、顶面测试点、功率级移动、C20/J4避让、开尔文/短回路、散热片/绝缘及缝合过孔落板。#7：保护动态响应、短路能量、制动/再生、采样窗口与阈值参数。
9. #5：C213在60V偏压下有效容量、R215实际≥0.5W额定与热降额、TVS/栅源钳位布局及浪涌能量、全部0603料号、未核实C编号。未用不明参数冒充保证值。

## 与 pinmap 不一致 / 待决

- **针脚接线按pinmap逐针表落实**。任务的J101“其余18针GND”与pinmap4.1/4.3的20针不一致；此处停在文字计数确认，不另改针脚。两板总计41个GND，底板实际21个已连接非GND触点+2个NC+41个GND=64；pinmap把两个备用ADC触点也计入23个非GND触点。
- **pinmap5A.3 / 7.2的板上母线比较器接锁存要求尚未完成**，原因及两种改法见第10项。该遗留不改变排针，但阻止A26保护功能的完整验收。
- pinmap5A.1“母线取得的全部电流都经过分流”须结合本任务指定的桥侧C21/C22例外理解：4.4µF最初放电不经分流，电解C19/C20之后放电经过。已按任务要求接桥侧，未回改pinmap。
- RS4是功能名RS_BUS的合法位号；未增加或改变任何MCU引脚。

## 验证和导出

- 每一轮原理图/字段修改后运行：`kicad-cli sch erc --severity-all inverter/hardware/inverter.kicad_sch -o /tmp/erc_inv.rpt`。最终复制同一次报告至`review/erc_issue3.rpt`，结果 **0错误、0警告**，无新ERC排除项。
- 项目原有忽略检查保持不变：单次全局标签、四线连接点、SPICE模型、封装过滤器匹配；未改`.kicad_pro`，未用降级检查掩盖新增错误。新电源边界在外部供电/无源保险或分流之后放显式PWR_FLAG，未改变器件引脚电气类型来躲ERC。
- 原生PDF：`review/inverter.pdf`（19页）；KiCad XML网表：`review/inverter.net.xml`；原生BOM：`review/bom_issue3.csv`，列为Reference、Value、Footprint、MPN、LCSC、DNP、Qty，保留DNP行，共247个器件行。
- `review/connectivity_issue3.json`记录347项全部通过的断言，覆盖逐针、NC孤立、电源分离、分流两侧、钳位极性、新器件字段、DNP、端子极性、故障链连接等断言，并对现有逻辑由导出网表枚举16,384组状态。该静态验证不替代传播延迟、模拟瞬态、短路/温升试验。
- 已目视检查关键PDF页面的排针编号/NC、保护通道、理想二极管和母线电流标注；第10项在原理图页与本说明均显著标为待决。
- 只把审阅导出写入review，未改正式BOM。所有临时脚本/中间导出在`/tmp`，不作为仓库代码提交。

## 改动文件

- `inverter/hardware/InverterLocal.kicad_sym`
- `inverter/hardware/aux_input.kicad_sch`
- `inverter/hardware/base_interlock.kicad_sch`
- `inverter/hardware/base_leds.kicad_sch`
- `inverter/hardware/bridge_u.kicad_sch`
- `inverter/hardware/bridge_v.kicad_sch`
- `inverter/hardware/bridge_w.kicad_sch`
- `inverter/hardware/bus_brake.kicad_sch`
- `inverter/hardware/bus_current.kicad_sch`
- `inverter/hardware/comparators.kicad_sch`
- `inverter/hardware/control_interface.kicad_sch`
- `inverter/hardware/core_signal_protection.kicad_sch`
- `inverter/hardware/current_sense.kicad_sch`
- `inverter/hardware/debug_comms.kicad_sch`（删除）
- `inverter/hardware/fault_logic.kicad_sch`
- `inverter/hardware/fp-lib-table`
- `inverter/hardware/inverter.kicad_sch`
- `inverter/hardware/mcu_coupling.kicad_sch`
- `inverter/hardware/power_interface.kicad_sch`
- `inverter/hardware/review/bom_issue3.csv`
- `inverter/hardware/review/connectivity_issue3.json`
- `inverter/hardware/review/erc_issue3.rpt`
- `inverter/hardware/review/inverter.net.xml`
- `inverter/hardware/review/inverter.pdf`
- `inverter/hardware/review/issue3_changes.md`
- `inverter/hardware/sensors.kicad_sch`（删除）
- `inverter/hardware/supply_logic.kicad_sch`
- `inverter/hardware/sym-lib-table`
- `inverter/hardware/voltage_sense.kicad_sch`


## 增量（2026-11-12 方案②／TLV1821／R71／#12 同步）

**当前状态以本节为准。** 本节覆盖前文第9/10节、固件影响、遗留项、待选表中“母线15 A保护暂停”“零点1.65 V”“TLV7021待实施”的旧状态；旧文保留作上一轮记录。方案②已经落图：U33=U_BUSAMP、U34=U_BUSCMP、RS4=RS_BUS；使用合法数字位号，功能名写入 `Design_Name`。15 A 为设计目标，E96 取值后的名义触发电流见下表。相电流 U10～U12 的增益、分流和零点保持。

工作基线：分支 `hw/inverter-sch-issue3`，本轮起点 `6764379`，已 rebase 到 `origin/main b14dfcd`，共享库子模块 `1dd8f79`，KiCad 10.0.7。仅增量修改原理图、本地符号及本节所列审阅导出。未修改 fw/、docs/design_decisions.md、任何 PCB、正式 bom/bom.csv、review/bom.csv、项目 ERC 配置或共享库；未 commit/push，未读取认证文件。

### A. 原厂依据和待核边界

| 器件 / 参数 | 原厂依据 / 核对结果 |
| --- | --- |
| INA241A2/A1 | [TI INA241A，SBOSA30D](https://www.ti.com/lit/ds/symlink/ina241a.pdf)，逐项核对本地 `/workspace/work/ds/ina241a.txt`。第6.5节：A1/A2增益、增益误差的输出区间、输出摆幅；第7.4.1节式(1)：两REF电压取平均；第7.4.3.3节/图7-7：一脚接外部参考、一脚接GND；第4节：DDF脚号。 |
| TLV1821DBVR | [TI TLV1821，SNOSDC8E Rev E](https://www.ti.com/lit/ds/symlink/tlv1821.pdf)，官方PDF在线读取；终端curl因DNS解析失败未能下载。第4节表4-1：DBV标准脚号；第5.3节：2.4～40 V供电；第7.4.2.2节：开漏；第7.4.4节：无内置迟滞；第8.1.2.1/8.1.2.3节：反相正反馈、开漏上拉须计入计算。 |
| U35 单与门 | [TI SN74LVC1G08，SCES217AA](https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf)，第4节DBV引脚、第5.3节供电/输入要求、第7.4节AND功能。沿用已有MyParts符号、MPN及C7666，不新增逻辑型号。 |
| C214/C215去耦 | [YAGEO CC0603KRX7R9BB104原厂规格](https://www.yageogroup.com/download/specsheet/CC0603KRX7R9BB104)：100 nF、±10%、50 VDC、X7R、0603；C14663来自任务/现有库采购字段。 |
| RS4采购变更 | 按本任务指定 Milliohm **LR2512D-3W-5mR-1% / C500739**，名义5 mΩ/3 W/1%。[资料入口](https://www.lcsc.com/datasheet/C500739.pdf)可定位到[原厂PDF镜像](https://datasheet.lcsc.com/datasheet/pdf/af008bf05bd6536b39b0bb7d67e56045.pdf)，但本次未取到PDF正文：**完整原厂料规、温度降额、脉冲及新MPN与既定焊盘的尺寸复核待核**。不沿用旧C2903482的料规作为新器件保证。 |
| R71 / R219及新阻值电阻 | R71的76.8k/0.1%、RT0603BRD0776K8L/C705795，R219的4.7k、0603WAF4701T5E/C23162均按本任务指定。R71/R219本次未取得原厂完整PDF，额定功率、工作电压、温漂等**待核**，不编造。R216～R218的1%是本次设计要求，具体MPN及其原厂料规待#5。 |

原厂文档的测试条件与名义电路计算分别列明。以下门限均按+3V3_INV=3.300 V、VBIAS_1V65=1.650 V、名义增益/5 mΩ分流计算；不代表整机全温/动态误差保证。LCSC编号按任务或#12 BOM同步，不把分销商库存/参数摘要替代原厂保证。

### B. 母线放大器及分流（方案②）

- U33：TI INA241A2IDDFR，C5240853，`MyFootprints:SOT-23-8`；供电保持+3V3_INV。
- **REF1=7脚接VBIAS_1V65；REF2=3脚接GND**；1=IN−接VBUS_BR、8=IN+接VBUS、2/4接GND、5=OUT、6=VS。相电流U10～U12两REF仍接1.65 V。
- RS4：新MPN/C号见A节；保持 `MyFootprints:Milliohm_HoJLR2512_Pad2.1x4.0mm_Gap4.1mm`。该封装及U33/U34所需SOT-23-8/SOT-23-5均在共享库中存在，**无待建封装**。两个端子的四线Kelvin取样与VBUS/VBUS_BR划分保持，RS1～RS3不变。
- C210=100n去耦、R212=47Ω输出隔离及接口链保持：`U33/5 I_BUS_RAW → R212 → I_BUS_PORT → R213 360Ω / D211 → R214 100Ω → I_BUS → J101/23 → PA3`。已有C211=1n保持DNP，实际MCU端RC仍由controller处理。

按SBOSA30D第7.4.1节式(1)及第7.4.3.3节：

```text
VOUT = G × VSENSE + (VREF1 + VREF2)/2
     = 20 × (I × 0.005) + (1.650 + 0)/2
     = 0.100 I + 0.825 V
I(A) = (VOUT − 0.825)/0.100
I=0 A     → 0.825 V
I=+15 A   → 2.325 V
上界3.1 V → (3.100−0.825)/0.100 = +22.75 A
下界0.05 V→ (0.050−0.825)/0.100 = −7.75 A
```

第6.5节的增益误差测试区间是 `GND+50mV < VOUT < VS−200mV`；同节高端摆幅条目在RL=10kΩ到GND、全温条件给出VS−0.2 V，3.3 V时为3.1 V。**本节用50 mV作为线性区下界；没有把另一条“Swing to Ground”20 mV摆幅值冒充50 mV。** −7.75/+22.75 A为名义线性区边界，端点不构成额外精度保证。15 A对应2.325 V，距3.1 V高端边界775 mV，旧双REF=1.65 V造成的3.15 V目标问题已解除。

固件换算应使用母线零点0.825 V和100 mV/A；相电流仍为1.65 V/50 mV/A。本轮不改固件。

### C. TLV1821母线门限、迟滞和锁存接入

U34=TI **TLV1821DBVR / C7068849**，`MyFootprints:SOT-23-5`；采用标准TLV1821，非电源脚互换的TLV1821L。实际脚号：1 OUT、2 V−=GND、3 IN+、4 IN−、5 V+=+3V3_INV。开漏输出，无内置迟滞。C214=CC0603KRX7R9BB104/C14663，100n去耦。

IN+接OC_BUS_REF，IN−接**钳位和接口RC之前的I_BUS_RAW**。电流低于上门限时输出释放、OC_BUS_N高；超过上门限时输出吸电流、OC_BUS_N低。正反馈由输出回到IN+。没有并联推挽输出。

| 位号 | 连接 | 阻值 / 0603要求 | 采购 |
| --- | --- | --- | --- |
| R216 | +3V3_INV → OC_BUS_REF | 10.2k，E96，1% | MPN=TBD（待#5） |
| R217 | OC_BUS_REF → GND | 23.2k，E96，1% | MPN=TBD（待#5） |
| R218 | OC_BUS_REF → OC_BUS_N | 226k，E96，1%，正反馈 | MPN=TBD（待#5） |
| R219 | +3V3_INV → OC_BUS_N | 4.7k，1%，开漏上拉 | UNI-ROYAL 0603WAF4701T5E，C23162 |

门限取+3V3_INV分压。本板既有VBIAS_1V65也是该电源分压缓冲，未找到独立高于2.325 V且更稳定的精密参考；直接3.3 V分压避免增加未授权的基准电路。电源/偏置误差仍应计入系统预算。**PR #14按旧3.15 V算的8.06k/165k/243k不用于本图。**

令 `RT=10.2k，RB=23.2k，RF=226k，RP=4.7k，VS=3.3 V`。按TI第8.1.2.3节，输出高态时反馈支路是RF+RP，不把OC_BUS_N理想化为严格3.3 V：

```text
G_H = 1/RT + 1/RB + 1/(RF+RP)
V_UP = VS × [1/RT + 1/(RF+RP)] / G_H
     = 2.322243459 V
I_UP = (V_UP−0.825)/0.100 = 14.972434595 A
VOH  = VS − RP × (VS−V_UP)/(RF+RP) = 3.280080383 V

G_L = 1/RT + 1/RB + 1/RF
V_DOWN = (VS/RT + VOL/RF)/G_L
VOL=0的名义近似：V_DOWN = 2.222539640 V
I_DOWN = (V_DOWN−0.825)/0.100 = 13.975396401 A
ΔV = 99.703819 mV；ΔI = 0.997038193 A
```

2.325 V/15 A是目标；E96实际上门限比目标低2.756541 mV，即低0.027565405 A（约0.184%），设计目标仍为15 A级。仅四个电阻各1%极限组合、固定其他量时，上门限2.308426～2.335949 V（14.834260～15.109488 A）；下门限在VOL=0近似下为2.207976～2.237003 V。实际VOL、比较器失调、分流/放大器/参考及供电误差尚需#7预算与实测；不将VOL=0近似当作保证值。RP远小于RF/10，符合TI反馈支路的建议。

U35=已有库SN74LVC1G08DBVR/C7666，C215同规格100n去耦。逻辑与信号路径：

```text
原相电流/OV/UV/电源健康链 U22/U23/U24B
  → 原U24/6输出改名 HEALTH_PREBUS
U35/1 = HEALTH_PREBUS
U35/2 = OC_BUS_N（U34/1，健康高、过流低）
U35/4 = HEALTH_ALL = HEALTH_PREBUS AND OC_BUS_N
  → U28/4 /S 异步置位故障锁存
  → U28/6 NO_LATCH变低
  → U24D HEALTH_UNLATCHED → U25A DRIVE_PERMIT
  → U25B/C/D、U26A/B/C封锁六路HIN/LIN
  → U27B FAULT_ACTIVE → R74 → Q8
  → FAULT_N_RAW → R211/D210 → FAULT_N → J102/20 → PB12 BKIN
```

U35其余脚：3 GND、5 +3V3_INV。原锁存复位条件与RESET_REQUEST、R73/C55、ENABLE_QUALIFIED互锁保持；比较器电流恢复到下门限仅恢复OC_BUS_N，不自动清除锁存。TLV1821第7.4.3节说明POR期间开漏输出为高阻；仍依靠原电源健康/BASE_READY/CTRL_READY链，不能把比较器上拉高单独当作上电健康保证。未把手册典型传播延迟当整条保护链最大关断时间。

### D. 相电流窗口与R71

实际工作分支上一轮已将R42～R47改成下面的正确E96组合，因此本轮保持这些阻值/连线，避免从#12旧BOM回退到2.65/0.65 V。U10～U12 INA241A1、5 mΩ及1.65 V零点保持：`10×0.005=0.050 V/A`，±12 A目标为2.25/1.05 V。

| 门限 | 从+3V3_INV到GND的串联电阻 | 取样点 | 实际名义电压 | 实际名义电流 |
| --- | --- | --- | --- | --- |
| 负向 | R42=20k → R43=1.43k → R44=10k | R43/R44 | 3.3×10/31.43 = 1.049952275 V | −12.000954502 A |
| 正向 | R45=10k → R46=1.43k → R47=20k | R45/R46 | 3.3×21.43/31.43 = 2.250047725 V | +12.000954502 A |

六个电阻均为MyFootprints 0603/E96，保留0.1%精度要求。**R42/R43/R46/R47的新阻值MPN=TBD（待#5）**，不写入#12中39k/1.8k的旧MPN。R44/R45仍是10k，和#12一致，已同步YAGEO RT0603BRD0710KL/C95204及0.1%字段；它们不是新阻值。表内为分压中心门限，不另改TLV3202已有迟滞。

R71改 **76.8k ±0.1%，YAGEO RT0603BRD0776K8L，C705795，MyFootprints:R_0603_1608Metric**。R72=10k及原1.3 V参考不变：

```text
V_DRV_UV(old) = 1.3×(76.1k+10k)/10k = 11.193 V
V_DRV_UV(new) = 1.3×(76.8k+10k)/10k = 11.284 V
变化 = +91 mV，+0.81%
```

以上为名义欠压跳变点，未加入比较器失调/电源精度/迟滞/温漂的新保证。

### E. #12 BOM同步与跳过清单

来源是 `git show origin/main:inverter/hardware/bom/bom.csv`（b14dfcd），与当前只读正式BOM字节一致。仅对其中Footprint为MyFootprints:R_0603_1608Metric或MyFootprints:C_0603_1608Metric的行操作，按当前根图的实际实例查位号，不把未实例化旧MCU页的同名符号算作仍在板上。

| 项目 | 位号数 | 处理 |
| --- | ---: | --- |
| 目标0603 BOM行 | 134 | 保留78，已删除56 |
| 保留位号的Footprint匹配 | 78 | 61个本轮改为BOM封装，17个原本一致 |
| 同步已知采购字段 | 73 | Manufacturer/MPN/Supplier_PN/LCSC/Purchase_URL/Voltage_Rating/Tolerance逐项同步，Supplier=LCSC |
| 新相窗口阻值例外 | 4 | R42/R43/R46/R47：封装同步，MPN=TBD，供应编号/URL待#5 |
| BOM自身MPN=TBD | 1 | R71不复制未知采购字段；按本任务专门料号补全 |
| 所有本分支新增、不在main BOM | 29 | 通用同步不处理；本轮明确要求的U33/RS4/U34等按专项更新 |

Value除任务明确要求的R71外未改，未复制BOM长Design_Note。同步#12后**R70的采购精度为1%（UNI-ROYAL 0603WAF1002T5E/C25804）**，按本轮明确的字段同步要求覆盖上一轮0.1%占位要求；阻值仍10k、连线不变。旧文R70待选/0.1%描述不作为当前料号规格。

保留的78个目标位号：

C4～C5、C9、C12、C17、C24、C26、C28、C30、C32、C34、C36～C43、C51～C62、C69～C72、C76、R13、R40～R47、R52、R68～R87、R91、R130、R135～R143、R160

73个同步已知采购字段的位号：

C4～C5、C9、C12、C17、C24、C26、C28、C30、C32、C34、C36～C43、C51～C62、C69～C72、C76、R13、R40～R41、R44～R45、R52、R68～R70、R72～R87、R91、R130、R135～R143、R160

已删除而跳过的56个目标0603位号：

C44～C50、C73～C75、C82、R57、R62、R67、R88～R90、R94～R121、R123～R129、R131～R134

BOM里存在、当前根图已删除的**全部91个电气位号**按原页列出（含非目标0603，均未重建）：

| 原BOM页 | 数量 | 跳过位号 |
| --- | ---: | --- |
| /Bus and brake/ | 1 | D1 |
| /Voltage and NTC/ | 26 | C44～C50、J8、R53～R67、U15～U17 |
| /ADC and status returns/ | 12 | C73～C75、D205～D207、R88～R90、R205～R207 |
| /Encoders and SPI/ | 30 | J9～J12、R94～R119 |
| /SWD UART CAN and status/ | 22 | C82、D4～D7、J13～J15、R120～R121、R123～R129、R131～R134、U31 |

另有3个非板载/机械占位行，当前根图无对应符号，跳过：`HARNESS_MR60_F_待定`、`STANDOFF_M2X11_待定`、`HSINK_TOP_待定`。合计缺失行94=91电气+3非板载，不混为94个已删除电气器件。

为满足“全图不得有0402封装”，另对未实例化、保留在目录中的旧页做**仅Footprint修改**；不改值、字段、连线，不把这些旧符号恢复到顶层/BOM：

| 未实例化文件 | 数量 | 封装改为官方0603的位号 |
| --- | ---: | --- |
| `mcu.kicad_sch` | 5 | C63～C67 |
| `mcu_analog.kicad_sch` | 20 | C69～C77、C79、R84～R93 |
| `mcu_control.kicad_sch` | 11 | C83～C84、R135～R143 |

共36个旧页符号。当前目录全部 `.kicad_sch` 的实例与嵌入库Footprint字段均无0402；`rg -n '"Footprint" "[^"\n]*0402' inverter/hardware --glob '*.kicad_sch'` 无命中。本文旧历史叙述中的0402文字不代表仍有0402封装。

### F. BRAKE检查（只报告，电路不改）

**结论：底板故障锁存不直接关断制动管Q7，不禁止BRAKE。** 网表路径如下：

```text
controller PC6/TIM8_CH1 → J102/17 BRAKE
  → R142（命令串阻） → BRAKE_IN
  → U29 UCC27517DBVR /3 IN+
U29/4 IN−固定GND；U29/1供电+12V_DRV、/2接GND
U29/5 OUT → BR_DRV → R17 15Ω → BR_GATE → Q7/4 G
R16 10k：BRAKE_IN默认下拉；R18 10k：BR_GATE下拉
Q7/1/2/3 S接GND；Q7/5/6/7/8 D接BR_SW
J5/1=VBUS，J5/2=BR_SW（外接制动电阻的功率端）
```

HEALTH_ALL、NO_LATCH、DRIVE_PERMIT均未进入上述驱动输入；PB12的FAULT_N/BKIN路径封锁的是TIM1桥PWM，底板没有把该信号串入PC6/BRAKE。J5是制动功率接口，BRAKE命令来自J102/17。因此不触发题设“锁存会禁止BRAKE→需雨田决定”的条件，本轮未改制动方案。该结论限底板硬件连线；MCU软件收到FAULT_N后是否主动撤销PC6需由固件核查。若故障本身使+12V_DRV丢失，不能据此声称U29仍可驱动。

### G. 新增与待#5器件

本轮实际新增8个：**U34、U35、R216～R219、C214、C215**。本分支新增、未出现在main BOM的29个当前器件如下；TP18～TP22为PCB铜焊盘，无独立采购物料。

| 位号 | Value / 用途 | MPN | LCSC / 状态 |
| --- | --- | --- | --- |
| C210 | 100n | CC0603KRX7R9BB104 | C14663 |
| C211 | 1n | 待#5 | 待#5 |
| C213 | 2.2u / 100V X7R | CS1210KKX7R0BB225 | C5578983 |
| C214 | 100n | CC0603KRX7R9BB104 | C14663 |
| C215 | 100n | CC0603KRX7R9BB104 | C14663 |
| D211 | BAT54S,215 | BAT54S,215 | C47546 |
| D212 | DDZ9699T | DDZ9699T | 待#5 |
| D213 | SMAT70A-13-F | SMAT70A-13-F | 待#5 |
| D214 | SMAJ24A | SMAJ24A-TR | 待#5 |
| Q9 | BSC110N15NS5ATMA1 | BSC110N15NS5ATMA1 | C412739 |
| R212 | 47 | 待#5 | 待#5 |
| R213 | 360 | 待#5 | 待#5 |
| R214 | 100 | 待#5 | 待#5 |
| R215 | 1k | 待#5 | 待#5 |
| R216 | 10.2k | TBD | 待#5 |
| R217 | 23.2k | TBD | 待#5 |
| R218 | 226k | TBD | 待#5 |
| R219 | 4.7k | 0603WAF4701T5E | C23162 |
| RS4 | 5m / 3W / 1% | LR2512D-3W-5mR-1% | C500739 |
| TH1 | NCP18XH103F03RB | NCP18XH103F03RB | C13564 |
| TP18 | I_BUS | 待#5（PCB测试焊盘，无独立物料） | PCB铜焊盘，无独立物料 |
| TP19 | GND | 待#5（PCB测试焊盘，无独立物料） | PCB铜焊盘，无独立物料 |
| TP20 | VBUS | 待#5（PCB测试焊盘，无独立物料） | PCB铜焊盘，无独立物料 |
| TP21 | +5V_INV | 待#5（PCB测试焊盘，无独立物料） | PCB铜焊盘，无独立物料 |
| TP22 | +3V3_INV | 待#5（PCB测试焊盘，无独立物料） | PCB铜焊盘，无独立物料 |
| U32 | LTC4359IS8#PBF | LTC4359IS8#PBF | 待#5 |
| U33 | INA241A2IDDFR | INA241A2IDDFR | C5240853 |
| U34 | TLV1821DBVR | TLV1821DBVR | C7068849 |
| U35 | SN74LVC1G08DBVR | SN74LVC1G08DBVR | C7666 |

任务要求单列的“本分支新增、仍使用Resistor_SMD/Capacitor_SMD且MPN待定”恰为5个：

| 位号 | 值 / 当前Footprint | 待#5事项 |
| --- | --- | --- |
| R212 | 47Ω / Resistor_SMD:R_0603_1608Metric | 保持本分支新增值/封装；具体MPN/采购编号待定 |
| R213 | 360Ω / Resistor_SMD:R_0603_1608Metric | 同上 |
| R214 | 100Ω / Resistor_SMD:R_0603_1608Metric | 同上 |
| R215 | 1k / Resistor_SMD:R_2512_6332Metric | ≥0.5W为既有设计要求；实际MPN、额定电压/功率及降额待#5 |
| C211 | 1n，DNP / Capacitor_SMD:C_0603_1608Metric | 具体MPN/耐压待#5，保持DNP |

其余本轮门限待选为R216=10.2k、R217=23.2k、R218=226k（0603/1%），以及R42/R47=20k、R43/R46=1.43k（0603/0.1%），均MPN=TBD。连同上表5个，共12个本次相关待选MPN位号（不含无独立物料的测试焊盘）。

上一轮延续：F1 0476008.MRSN、U32 LTC4359IS8#PBF、D212 DDZ9699T、D213 SMAT70A-13-F、D214 SMAJ24A-TR的LCSC仍待#5；C213的60 V偏压有效电容、TH1的替代与NRND状态、R215的额定/降额仍按前文交#5。本轮新建/更新的INA241A2、TLV1821、LR2512D本地符号正式入库待#5；**封装已存在，无“待建库”封装项**。RS4、R71、R219未取到完整原厂料规的项目明确标待核，未推定额定值。

### H. 验证、覆盖导出与改动文件

- 按指定原命令执行 `kicad-cli sch erc --severity-all --format report inverter/hardware/inverter.kicad_sch -o inverter/hardware/review/erc_issue3.rpt`：**0错误、0警告、0违规**，无须逐条解释的未消项。既有4项忽略检查保持，未新增排除/降级或修改.kicad_pro。
- 从最终原生XML网表验证：**1,443项检查全部通过**；枚举12路健康输入和ENABLE/CTRL_READY/先前锁存状态共**32,768组**，并检查六路PWM输入组合及锁存状态**128组**。覆盖新比较器、门限、极性、原锁存/复位/PWM/FAULT_N、全部64针、Kelvin/电容归属、DNP、BOM字段和禁改文件。连接/字段结果覆盖到 `connectivity_issue3.json`。
- 对照本轮起点，所有既有器件保留，只有R71的Value改变；所有既有引脚只有U33/3从VBIAS_1V65改GND、U24/6输出改为HEALTH_PREBUS两处网名变化，其余忽略层级前缀后保持。没有改相分流、桥侧电容、ADC接口或BRAKE驱动网络。
- PDF `inverter.pdf` 共**19页**，已目视检查母线检测/比较器/单与门及锁存页，新增字段和电源标注无重叠。XML格式为**kicadxml**。
- `bom_issue3.csv` 共**255行器件/Qty=255**，保留9行DNP，表头严格为 **Reference、Value、Footprint、Manufacturer、MPN、Supplier_PN、DNP、Qty**。审阅BOM覆盖导出，未写正式BOM。
- 静态连线和名义电阻计算不代替全温精度、短路/瞬态和保护关断时间试验，相关实测仍交#7。

本轮改动文件（相对仓库根目录；20张原理图+1个本地符号库+6个审阅文件，共27个）：

- `inverter/hardware/InverterLocal.kicad_sym`
- `inverter/hardware/base_interlock.kicad_sch`
- `inverter/hardware/base_leds.kicad_sch`
- `inverter/hardware/bridge_u.kicad_sch`
- `inverter/hardware/bridge_v.kicad_sch`
- `inverter/hardware/bridge_w.kicad_sch`
- `inverter/hardware/bus_brake.kicad_sch`
- `inverter/hardware/bus_current.kicad_sch`
- `inverter/hardware/comparators.kicad_sch`
- `inverter/hardware/control_interface.kicad_sch`
- `inverter/hardware/core_signal_protection.kicad_sch`
- `inverter/hardware/current_sense.kicad_sch`
- `inverter/hardware/fault_logic.kicad_sch`
- `inverter/hardware/inverter.kicad_sch`
- `inverter/hardware/mcu.kicad_sch`
- `inverter/hardware/mcu_analog.kicad_sch`
- `inverter/hardware/mcu_control.kicad_sch`
- `inverter/hardware/mcu_coupling.kicad_sch`
- `inverter/hardware/review/bom_issue3.csv`
- `inverter/hardware/review/connectivity_issue3.json`
- `inverter/hardware/review/erc_issue3.rpt`
- `inverter/hardware/review/inverter.net.xml`
- `inverter/hardware/review/inverter.pdf`
- `inverter/hardware/review/issue3_changes.md`
- `inverter/hardware/supply_12v.kicad_sch`
- `inverter/hardware/supply_logic.kicad_sch`
- `inverter/hardware/voltage_sense.kicad_sch`

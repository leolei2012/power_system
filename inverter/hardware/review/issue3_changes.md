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

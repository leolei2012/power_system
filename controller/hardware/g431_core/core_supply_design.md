# G431最小系统板供电、复位与运行许可（Rev E，project_draft）

本说明对应当前最小系统板的 `core_supply.kicad_sch` 和 `core_arm.kicad_sch`。核心只保留STM32G431及本地电源/去耦、VDDA/VREF去耦、复位与BOOT、可选时钟、运行许可和两组2×16排针。SWD、TTL、CAN、五个指示灯、编码器/SPI等功能接口以及采样前端和输入钳位均在功率底板。2026-11-11已将现有确切C号器件及四颗100nF/0603去耦同步为共享库reviewed符号和封装；本轮公共库只读，电路仍为应用审查稿。

## 已画电路

`+5V_CORE_IN → R301 0.47Ω → TVS/输入电容 → D102 → U101 TLV76733 → +3V3_MCU`。

核心插到底板时，底板经J101/1、3送入5 V；核心单独作为最小系统板使用时，仍经同一排针接稳压4.75–5.25 V和GND即可，不增加独立供电接头或电源选择跳帽。插到底板时使用单一5 V来源，不能把两个独立5 V电源并联。

| 核心排针 | 实际连接/用途 |
|---|---|
| J101/1、3 | `+5V_CORE_IN`输入 |
| J101/22、32 | `+3V3_MCU`回传，底板对应`+3V3_CORE_REF`，用于底板钳位上轨/故障上拉 |
| J101/2、4、21、31；J102/9、27、31 | 共7个GND触点 |
| J102/10 | `CTRL_READY`运行许可输出 |
| J102/18 | PC7；插到本功率底板时为`RUN_ARM` |
| J102/32 | `NRST`；供底板SWD/调试复位，保持复位功能 |
| J102/1 | `PB8_BOOT0`，与核心BOOT按钮共网 |

`+3V3_MCU` 与底板 `+3V3_INV` 不并联，两板共地。底板`+3V3_CORE_REF`来自上述两个回传针，不得再接底板本地3.3 V稳压器，也不是MCU精密`VREF+`引脚的外部输入。D102采用低漏电的硅整流管，阻止核心电容或信号钳位电流回到5 V入口；D103从LDO OUT接向IN，旁路LDO掉电反压。D101仅处理能量受限的短时正向扰动，R301是阻尼电阻，不是保险丝或浪涌能量额定器件。本页不承担持续24/60 V误接保护，也不代表已通过IEC浪涌或热插拔认证。两板按断电插拔使用，普通排针没有触点先后连接保证。

U101采用项目库已有的16 V输入TLV76733；MCC SMF6.0A的指定钳位值为10.3 V，给LDO留出额定输入余量。TVS数值仍有指定波形、电流和布局条件，不能外推到任意来源的故障。[TI TLV767，§6/§9.1.4](https://www.ti.com/lit/ds/symlink/tlv767.pdf)、[MCC原厂表格镜像，p2](https://www.alldatasheet.co.kr/html-pdf/433293/MCC/SMF6.0A/114/2/SMF6.0A.html)。

## 电压、电流及散热预算

入口合同为排针处稳态4.75–5.25 V，不是给功率母线直接使用的宽压输入。本版 `+3V3_MCU` **总预算100 mA持续**，包含MCU及启用的内部外设、本地电路和任何外供3.3 V负载。底板CAN、四个状态灯、编码器/SPI等外围的供电来自底板本地3.3 V/传感器电源，其供电电流不再计入核心LDO预算；MCU的I/O驱动/灌电流仍须满足芯片引脚及总电流限制。TLV767的1 A芯片额定值不等于本版排针或核心板额定值。

| 项目 | 本版约束/计算 |
|---|---|
| MCU及启用外设 | 先留60 mA工程预算；并非ST保证的所有外设全开最大值 |
| 本地复位/ARM逻辑、分压及余量 | 先留5 mA；ARM高时R402约0.33 mA，U103/U105静态各≤10 µA |
| 外供3.3 V及其余余量 | 合计落在剩余约35 mA内；回传参考轨若增加外围负载，需重新核算 |
| 5 V入口持续供电预留 | 至少120 mA；包括MR分压、LDO地电流和TVS漏电余量 |
| 启动电流 | C305及输入电容充电不受100 mA稳态预算限制；需在底板5 V实物验证启动/插接波形 |

ST数据表中高主频的电流表有温度、执行存储器和外设关闭等条件，不能把某个典型值作为整个核心板最大耗电。[STM32G431RB数据表，电流特性](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf)。

以100 mA负载计算，另计MR分压后R301约掉0.05 V。D102即保守借用其25°C、1 A条件下的1.1 V最大Vf，U101入口仍约为 `4.75−0.05−1.10=3.60 V`。TI给出的DRV封装最大压差1.4 V@1 A，并在§8.3.2说明以导通电阻估算较小电流，100 mA对应约0.14 V；与3.333 V输出上限比较尚有约0.12 V估算余量。该推算不是100 mA/全温度单独生产保证；最低入口、冷态、动态负载和插座压降仍需样机确认。[Diodes S1A原厂数据表](https://www.diodes.com/datasheet/download/S1M.pdf)、[TI TLV767](https://www.ti.com/lit/ds/symlink/tlv767.pdf)。

U101最保守忽略D102压降，损耗上界近似 `(5.25−3.3)×0.1=0.195 W`；TI DRV的JEDEC参考θJA=77.7°C/W，估算升温约15°C。实际需连接EP至地铜并结合底板热源核温，不能把JEDEC参数直接当最终PCB保证。

## 底板钳位回传与核心3.3 V吸收

8路ADC的360 Ω/BAT54S/100 Ω+1 nF，以及BASE_READY/FAULT_N的两路1 kΩ钳位，现位于底板`core_signal_protection`。其钳位上轨`+3V3_CORE_REF`经J101/22、32回到核心`+3V3_MCU`，由核心U104吸收正向注入。两根参考轨触点及共地触点都是这条保护回路的一部分，应低阻、短回路连接，不能作为可省略的测量参考线。MCU的VDDA/VREF+本地去耦仍保留在核心。

U104为TL431BIDBZR。R302=3.83 kΩ、R303=10 kΩ均0.1%，名义开启点约为 `2.495×(1+3.83/10)+IREF×3.83k≈3.46 V`。LDO本身不会吸收信号钳位注入电流，U104提供有限的吸收通道。TL431B的参考初始误差、温漂、REF偏流、动态阻抗均会影响实际钳位值；这不是精确的3.450 V故障界限，更不是硬性保证瞬态峰值不超过MCU绝对最大值。需实测脉冲注入时的轨电压、振铃和器件温升。[TI TL431，§6.12/稳定性章节](https://www.ti.com/lit/ds/symlink/tl431.pdf)。

**总正向短时注入工程预算≤50 mA**，不是达到50 mA便自动切断的限流器。底板8路模拟钳位在360 Ω之后、100 Ω之前，因此流进BAT54S及参考电源轨的限流电阻只有360 Ω。100 Ω仅在ADC支路：底板RC的理想时间常数为 `(360+100)Ω×1 nF=0.46 µs`，外部源阻抗以及排针/跨板走线寄生另计；故障注入不能将这两个电阻串算。BASE_READY/FAULT_N两路数字钳位各经1 kΩ，同属这个50 mA总预算。

按全部10路输入均为5.25 V、本地轨取3.25 V、忽略二极管正向压降，且360 Ω及1 kΩ电阻都取1%负容差，合计为：

`8×(5.25−3.25)/(360×0.99) + 2×(5.25−3.25)/(1000×0.99) = 48.93 mA < 50 mA`。

该计算以本地轨不低于3.25 V为前提，不能直接代替断电轨从0 V建立时或轨电压振铃的动态分析；实际正常端口来自3.3 V域。既有50 mA分流器条件和器件型号保持不变；本页不保证60 V持续故障免疫。

C305必须装47 µF±10%/10 V钽电容。它是TL431稳定性设计的一部分，不应仅按标称容量换成会明显直流偏压降容的MLCC。TI稳定性资料要求考虑阴极电压、电流、输出电容及ESR；本设计选在大电容一侧，47 µF的初始最小42.3 µF加本地陶瓷电容，比资料所举>22 µF的保守示例更大，并应结合3.46 V、0.7–50 mA范围复核。资料曲线本身是典型特性，最终稳定性仍须样机验证。TLV767输出电容额定范围1–220 µF，本页的4.7 µF陶瓷加47 µF及MCU分布去耦处在总容量范围内；保留U101旁的陶瓷电容，不能只剩高ESR钽电容。[TI SLVA482A](https://www.ti.com/lit/an/slva482a/slva482a.pdf)、[KEMET T491原厂数据表](https://content.kemet.com/datasheets/KEM_T2005_T491.pdf)。

## 复位及许可

U102复用TPS3808G33DBVR，SENSE/VDD接本地3.3 V，RESET为开漏，R306上拉到本地3.3 V。CT留空，释放延迟典型20 ms。当前原生网络名为`NRST`，连接MCU/7、核心RESET按钮SW2、核心C81、U102 RESET及U103输入，并通过J102/32引出到底板SWD。底板故障通过BKIN/本地关断链处理，不直接把FAULT连接到NRST。核心本身只有RESET/BOOT按钮，SWD接头在底板。[TI TPS3808](https://www.ti.com/lit/ds/symlink/tps3808.pdf)。

MR额外检查D102**之前**的5 V节点，R304/R305=1 kΩ/1.1 kΩ。低端4.75 V输入时MR约2.46 V，高于0.7×3.333 V=2.333 V；高端10.3 V TVS指定钳位时MR约5.40 V，低于MR推荐上限6.5 V。

5 V插座断开、核心被信号钳位反向托起时，MR仍通过R305拉低。D102选硅整流管而非普通SS14，是为了避免后者mA级高温漏电抬高这个检测点。即使取S1A在125°C/额定反压下的最大100 µA漏电，以及TPS3808最小70 kΩ内部上拉，MR仍约低于0.2 V，低于0.3×本地VDD低电平门限。该比较覆盖本页漏电来源，未假定所有其它外接电缆都不会额外给5 V入口供电。

U103 SN74LVC1G17DBVR保留施密特整形：`NRST → CORE_RESET_OK`。R306/C81使NRST释放沿较慢，不能直接用普通CMOS AND替代这个施密特级。新增`core_arm.kicad_sch`中的U105 SN74LVC1G08DBVR，将`CORE_RESET_OK`与PC7组合为`CTRL_READY = CORE_RESET_OK AND PC7`；U105/1=A、2=B、3=GND、4=CTRL_READY、5=+3V3_MCU。R402=10 kΩ在核心本地将PC7下拉，C308=100 nF为U105本地去耦。[TI SN74LVC1G17](https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf)、[TI SN74LVC1G08，§5.3/5.5/7.3](https://www.ti.com/lit/ds/symlink/sn74lvc1g08.pdf)。

复位或进入ROM启动流程时，应用没有主动置位PC7，R402将ARM保持低，避免ROM初始化与应用PWM/ENABLE复用的引脚后误产生许可。应用先配置安全的PWM/BKIN及状态，再显式置位PC7/RUN_ARM和ENABLE；从已运行应用直接跳ROM前先清ARM。PG10保持NRST功能，PB8/BOOT0按钮是否进入ROM还取决于Option Bytes；接功率底板时PC7必须保留给ARM，排针引出不表示允许底板上拉或外设驱动它。[ST AN2606，STM32G431xx/441xx启动接口](https://www.st.com/resource/en/application_note/an2606-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf)。

两颗逻辑均有Ioff部分断电特性。U105在VCC=0时输出漏电最大±10 µA，结合底板CTRL_READY的10 kΩ下拉，端口电压上界约0.1 V；其输入最大±5 µA漏电与R402组合约50 mV，保持ARM低。正常ARM高时增加约0.33 mA下拉电流。MR检测及NRST开漏/上拉时序保持原设计。`CTRL_READY`是复位健康和应用ARM的组合许可，最终桥臂仍受底板本地健康/故障/ENABLE门控；它不是心跳、看门狗或CPU调试暂停检测器。

## 已同步的精确器件

下表器件现均采用公共库reviewed符号和封装，应用及样机验证尚未完成。C304/C306/C307/C308已采用YAGEO CC0603KRX7R9BB104/C14663（100nF、50V、±10%、X7R、0603），满足这四处原记录的100nF/16V/0603要求。其余普通阻容继续保持原值、封装、YAGEO品牌及待选约束，未借同值批量替换。

| 位号 | 完整型号 | LCSC | 封装/用途 |
|---|---|---|---|
| U101 | TLV76733DRVR，TI | [C2848334](https://item.szlcsc.com/3046559.html) | WSON-6+EP，独立3.3 V |
| U102 | TPS3808G33DBVR，TI | [C43698](https://item.szlcsc.com/44691.html) | SOT23-6，本地监控 |
| U103 | SN74LVC1G17DBVR，TI | [C7836](https://item.szlcsc.com/8313.html) | SOT23-5，NRST施密特整形至CORE_RESET_OK |
| U104 | TL431BIDBZR，TI | [C41283](https://item.szlcsc.com/42267.html) | SOT23-3，钳位注入吸收 |
| U105 | SN74LVC1G08DBVR，TI | [C7666](https://item.szlcsc.com/8143.html) | SOT23-5，RESET_OK与PC7/RUN_ARM的AND |
| D101 | SMF6.0A-TP，MCC | [C914434](https://item.szlcsc.com/985114.html) | SOD123FL，短时输入TVS |
| D102 | S1A-13-F，Diodes | [C150735](https://item.szlcsc.com/162075.html) | SMA，低漏电反向阻断 |
| D103 | PMEG2010ER,115，Nexperia | [C82288](https://item.szlcsc.com/83445.html) | CFP3/SOD123W，低Vf反压旁路 |
| C305 | T491B476K010AT，KEMET | [C116617](https://item.szlcsc.com/117871.html) | B/3528-21，47 µF±10%/10 V；稳定性关键件 |
| R302 | RT0603BRD073K83L，YAGEO | [C861384](https://item.szlcsc.com/921722.html) | 3.83 kΩ、0.1%、0603 |
| R303 | RT0603BRD0710KL，YAGEO | [C95204](https://item.szlcsc.com/96405.html) | 10 kΩ、0.1%、0603 |

R301=0.47 Ω/0805，已有说明中的YAGEO采购候选为RL0805FR-070R47L/C705493（国内商品页待核），但本页原生通用电阻字段仍标TBD；不能把它写成已完成公共库物料。C301/C302需25 V、0805、4.7 µF，实际在5.25 V下有效容量至少2.2 µF；C303在3.3 V下同样需保留有效容量。R304/R305/R306/R402及其余待选阻容保持原理图给定值与YAGEO品牌，精确MPN待普通被动件统一采购时补齐。

## 电气及图面检查

供电页仍为20个物理器件，ARM页增加U105、R402、C308三个器件。Rev E最小系统板的最新完整XML共47个器件。保留旧供电检查的51条pin-net断言，只将`MCU_RESET_N`更新为`NRST`、U103/4输出更新为`CORE_RESET_OK`，另核对ARM页9个引脚连接；U102/4(CT)、U103/1(NC)仍按原厂规定留空。检查使用`review/controller.net.xml`，而非旧Rev D的`core_supply_full_probe.net.xml`。此快照对应的完整top ERC为0 error / 0 warning；连接及库引用检查不替代上面的电源动态/热/故障实测。

D103现采用`MyParts:PMEG2010ER_115`及`MyFootprints:Nexperia_CFP3_SOD123W_Reflow`共享定义，pin1为阴极、pin2为阳极。厂家回流焊尺寸与实际共享封装文件为几何依据；本轮已核对符号引脚和真实焊盘覆盖，未完成PCB装配验证。[PMEG2010ER原厂数据表，p2/p9](https://assets.nexperia.com/documents/data-sheet/PMEG2010ER.pdf)。

本轮迁移前后的233个物理pin-node、64针接口及52个MCU信号pad检查见`review/shared_parts_2026-11-11/pin_equivalence.json`，共享封装焊盘覆盖见同目录`footprint_pin_check.json`，当前完整图面为`review/controller.pdf`。既有60条供电/ARM期望连接已由根工程对最新XML统一复核并通过；`review/core_supply_expected.json`及旧`review/core_supply_validation.json`用于追溯，不将旧源hash当成本轮验证。双板最新PASS报告已刷新到根工程`outputs/schematic_review_2026-11-11/system_check.json`和本目录`review/system_check.json`。旧的供电独立PDF和`tools/build_core_supply.py`属于Rev D作者资料，不应直接重跑覆盖Rev E原生页。

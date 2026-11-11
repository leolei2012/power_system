# 当前双板待补物料清单

> 历史快照，已由 [2026-11-11 原理图交接](schematic_update_2026-11-11.md)及 [当前待选CSV](parts_to_complete_2026-11-11/selection_pending.csv)更新。下列21款已选型号现已全部入共享库并接入原理图，C14663也已reviewed并用于21个位号；无需重复建库。当前剩余65组、233个位号待定完整采购料号。以下正文、CSV及Excel保留2026-11-10时点记录。

截至 2026-11-10，范围为当前 Rev E 的 controller 最小系统板和 inverter 功率底板。共享库已有 30 款。先补 **21 款已选型号的共享库条目**，再补 **67 组待定采购料号**。

- [可填写 Excel](../outputs/parts_to_complete_2026-11-10/parts_to_complete.xlsx)：两张可筛选表，黄色列供填写进度或采购型号。
- [已选型号待入库 CSV](parts_to_complete_2026-11-10/library_missing.csv)：21 款，42 个位号，默认装配 40 个、DNP 2 个。
- [采购料号待确定 CSV](parts_to_complete_2026-11-10/selection_pending.csv)：67 个初筛组，254 个位号，默认装配 241 个、DNP 13 个。

## 已选型号待入共享库

每款补齐对应符号、封装、完整订货型号、C 编号和资料记录。表中的装配 / DNP 数量均按一套双板计。全部采购链接统一为国内立创商城（2026-11-10）：20 款对应商品详情页，电感 C408447 使用国内按型号搜索入口，详情页待核。两项既有候选的采购链接也已同步为国内站。部分详情页通过官方同一商品 ID、完整型号和 C 编号映射，国内正文读取受限，已在表中标明。未据此确认实时库存和价格。

“已选型号”表示已有具体采购候选。原 BOM 的选型状态已随表保留，保险丝保护协调、电感工作及热验证、MOS 热与脉冲验证等待办仍按各条备注执行。

### controller 最小系统板

共 9 款。

| 编号 | 位号 | 完整订货型号 | 立创链接 | 装配 / DNP |
| --- | --- | --- | --- | --- |
| L01 | C305 | T491B476K010AT | [C116617](https://item.szlcsc.com/117871.html) 国内 | 1 / 0 |
| L02 | D101 | SMF6.0A-TP | [C914434](https://item.szlcsc.com/985114.html) 国内 | 1 / 0 |
| L03 | D102 | S1A-13-F | [C150735](https://item.szlcsc.com/162075.html) 国内 | 1 / 0 |
| L04 | D103 | PMEG2010ER,115 | [C82288](https://item.szlcsc.com/83445.html) 国内 | 1 / 0 |
| L05 | R302 | RT0603BRD073K83L | [C861384](https://item.szlcsc.com/921722.html) 国内 | 1 / 0 |
| L06 | R303 | RT0603BRD0710KL | [C95204](https://item.szlcsc.com/96405.html) 国内 | 1 / 0 |
| L07 | U103 | SN74LVC1G17DBVR | [C7836](https://item.szlcsc.com/8313.html) 国内 | 1 / 0 |
| L08 | U104 | TL431BIDBZR | [C41283](https://item.szlcsc.com/42267.html) 国内 | 1 / 0 |
| L09 | U105 | SN74LVC1G08DBVR | [C7666](https://item.szlcsc.com/8143.html) 国内 | 1 / 0 |

### inverter 功率底板

共 12 款。

| 编号 | 位号 | 完整订货型号 | 立创链接 | 装配 / DNP |
| --- | --- | --- | --- | --- |
| L10 | D1 | MBRD20150CT-13 | [C151357](https://item.szlcsc.com/162697.html) 国内 | 1 / 0 |
| L11 | D201 D202 D203 D204 D205 D206 D207 D208 D209 D210 | BAT54S,215 | [C47546](https://item.szlcsc.com/48551.html) 国内 | 10 / 0 |
| L12 | F1 | 0476015.MRSN | [C3165851](https://item.szlcsc.com/3727788.html) 国内 | 1 / 0 |
| L13 | F2 | 0451002.MRL | [C99547](https://item.szlcsc.com/100761.html) 国内 | 1 / 0 |
| L14 | J2 | B2B-PH-K-S(LF)(SN) | [C131337](https://item.szlcsc.com/142630.html) 国内 | 1 / 0 |
| L15 | J7 J8 | PZ127-1-02-Z | [C5372825](https://item.szlcsc.com/6225189.html) 国内 | 1 / 1 |
| L16 | J9 J10 J13 | PZ127-1-05-Z | [C5372828](https://item.szlcsc.com/6225192.html) 国内 | 3 / 0 |
| L17 | J11 J12 | PZ127-1-06-Z | [C5372829](https://item.szlcsc.com/6225193.html) 国内 | 2 / 0 |
| L18 | J14 J15 | PZ127-1-03-Z | [C5372826](https://item.szlcsc.com/6225190.html) 国内 | 1 / 1 |
| L19 | L1 L2 | MWSA0603S-4R7MT | [C408447](https://so.szlcsc.com/global.html?k=MWSA0603S-4R7MT) 国内搜索，详情待核 | 2 / 0 |
| L20 | Q1 Q2 Q3 Q4 Q5 Q6 Q7 | BSC110N15NS5ATMA1 | [C412739](https://item.szlcsc.com/404529.html) 国内 | 7 / 0 |
| L21 | SW1 | TS-1088-AR02016 | [C720477](https://item.szlcsc.com/763484.html) 国内 | 1 / 0 |

BSC110N15NS5 的完整订货型号按 **BSC110N15NS5ATMA1 / C412739** 整理，主桥 Q1～Q6 和制动 Q7 共七颗。现有八个物理脚的项目封装可作为核对起点，入共享库时须按原厂图复核。

控制板 SW2、SW3 已选的新按键 **TS-1101-C-W / C318938 已建库**，不再补旧型号。上表 TS-1088-AR02016 只用于功率底板 SW1。

## 采购料号待确定

| 板卡 | 初筛组数 | 位号数 | 默认装配 | DNP |
| --- | --- | --- | --- | --- |
| controller | 14 | 30 | 27 | 3 |
| inverter | 53 | 224 | 214 | 10 |

CSV 和 Excel 按板卡、厂家要求、数值、封装、耐压记录及公差记录分组，并保留全部位号、DNP 位号和逐位号用途。分组只是选料起点，同一组采用一个料号前仍须满足该组所有用途及额定要求。

共享库新增的 **CC0603KRX7R9BB104 / C14663**（100nF、0603、50V、±10%、X7R）目前为 **draft**。已在两板 100nF / 0603 组的候选栏注明；可复核后复用，不用重复建条目，原理图待定状态仍保留。

- 普通固定贴片电阻和通用小陶瓷电容按 **YAGEO 国巨**。87 颗待选电容的公差字段均为空，介质与偏压有效容量也需补齐，不能直接当成已确定的 X7R 或 ±10%。
- inverter 的 **R209（10k、0603）公差仍空**，不并入已写 1% 的 10k 组。
- controller **C301、C302**：4.7µF、0805、25V，须在 **5.25V 偏压下有效容量至少 2.2µF**。
- controller **C303**：4.7µF、0805、16V，须在 **3.3V 偏压下有效容量至少 2.2µF**。C68 为 0603、4.7µF、至少 16V，三者规格分别保留。
- controller **Y1、C83、C84 默认 DNP**。Y1 暂定 8MHz，CL、ESR、驱动等级及启动条件待定；C83、C84 的 18pF 只是占位，随晶体和 PCB 杂散重算。
- controller **R301** 的 [RL0805FR-070R47L / C705493](https://item.szlcsc.com/742063.html) 仅为已有说明中的候选，原理图仍为 TBD，在待选表保留这一状态。
- controller **C305 / T491B476K010AT** 是稳定性关键的钽电容，已列入上面的已选型号清单，不能按普通同值 MLCC 合并。

## 已建库条目及工程同步

以下器件不用重复建库，后续原理图需同步到对应共享条目。

| 型号 | 立创编号 | 位置 | 尚待同步内容 |
| --- | --- | --- | --- |
| STM32G431RBT6 | C431633 | controller U30 | 当前仍使用项目符号及通用封装 |
| TS-1101-C-W | C318938 | controller SW2、SW3 | 当前仍为旧按键型号及旧封装 |
| PZ254V-12-32P | C22465940 | controller J101、J102 | 当前仍为通用排针定义 |
| PM254V-12-32-H85 | C46595991 | inverter J101、J102 | 当前仍为通用排母定义 |

PCB 焊线孔 J3、J4、J5 和测试点已有项目或官方定义，无须采购对应连接器。外接制动电阻及外置 NTC 不计入本次板载物料数量。

## 对照依据

- [共享库台账](../../kicad_library/parts.csv)。
- [controller BOM](../controller/hardware/g431_core/bom/bom.csv)及[逐位号待选表](../controller/hardware/g431_core/bom/selection_pending.csv)。
- [inverter BOM](../inverter/hardware/bom/bom.csv)及[逐位号待选表](../inverter/hardware/bom/selection_pending.csv)。
- [最小系统板供电约束](../controller/hardware/g431_core/core_supply_design.md)。

清单按当前共享库台账去重。两板原有 library_intake.csv 仍包含已建库排针或排母，以及控制板待替换的旧按键，不按其原行数作为本次待补数量。

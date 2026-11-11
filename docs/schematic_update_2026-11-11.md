# Rev E 双板原理图交接（2026-11-11）

本轮已更新 STM32G431RBT6 最小系统子板与变频功率底板的原生 KiCad 原理图，将已选器件接入当前 reviewed 共享库，刷新 PDF、BOM 和验证记录。原有供电、保护、接口及板间针序保持一致；当前交付为原理图审查稿。

| 板卡 | 原生 KiCad 工程 | 图纸 | 位号 / DNP | 共享库位号 | 待定采购料号位号 |
| --- | --- | --- | --- | --- | --- |
| controller 最小核 | [controller.kicad_pro](../controller/hardware/g431_core/controller.kicad_pro) | [7页 PDF](../controller/hardware/g431_core/review/controller.pdf) | 47 / 3 | 20 | 26 |
| inverter 功率底板 | [inverter.kicad_pro](../inverter/hardware/inverter.kicad_pro) | [20页 PDF](../inverter/hardware/review/inverter.pdf) | 317 / 14 | 91 | 207 |

## 已落实到图纸

共享库 `kicad_library/parts.csv` 当前有51款，均为 reviewed。上一轮清单中的21款已选型号已全部入库并接入原理图，相关 `library_intake.csv` 均为零行，不需重复建立这些型号。

- 控制板 U30 使用共享 STM32G431RBT6；J101/J102 使用公头 PZ254V-12-32P / C22465940；SW2/SW3 使用 TS-1101-C-W / C318938。
- 功率底板 J101/J102 使用排母 PM254V-12-32-H85 / C46595991；Q1～Q7 使用 BSC110N15NS5ATMA1 / C412739。MOS 的1～3脚为源极，4脚为栅极，5～8脚及重复5号散热焊盘为漏极。
- 底板 D1 改接共享 MBRD20150CT-13 的实际三脚符号，并局部重画连接线；其余模块内部连线沿用原图，模块间仍可用网络标签。
- 两板21颗100nF / 0603采用已reviewed的国巨 CC0603KRX7R9BB104 / C14663（50V、±10%、X7R）。它们已从待选清单移除。
- 已选物料的采购字段统一使用国内立创商品页或明确注明的国内搜索入口。电感 C408447、分流器 C2903482 的国内详情页仍待核；已保留完整型号及C编号，不以搜索入口表示实时库存。

两板仍规划60×60mm，下层为控制板，上层为功率底板。控制板MCU、公头及RESET/BOOT按键均在顶面；按键靠边，从侧面伸入后向下操作。实际板距、孔位及插合净空随两板PCB共同校核。完整架构与64针表见 [双板说明](controller_daughterboard.md)。

## 本轮检查结果

KiCad 10.0.7重新导出两板XML、ERC和PDF。两板ERC均为 **0错误、0警告**。已逐页查看27页图面，并复核变更后的按键、电源、排针、D1及桥臂图。最终统一导出的PDF也与已审查图面核对一致，见 [PDF验证记录](../outputs/schematic_review_2026-11-11/final_pdf_validation.json)。

[跨板验证报告](../outputs/schematic_review_2026-11-11/system_check.json)为PASS，检查入口为 [verify_shared_library_schematics.py](../tools/verify_shared_library_schematics.py)。检查包括：

- 与本轮改动前基线比较，两板共1202个物理引脚的网络分区完全一致，位号及DNP不变。
- 64个板间触点、52个MCU信号pad及全部64个MCU引脚连接正确。
- RESET/BOOT路径、60项核心供电与ARM引脚断言、ADC与状态回传钳位、两侧独立3.3V电源域通过。
- 32768组硬件许可逻辑组合通过；复位、ARM、ENABLE、本地健康信号及故障锁存共同决定桥PWM许可。
- 已接入共享库器件的完整型号、供应商、符号、封装及引脚焊盘对应关系通过；MOS铜焊盘编号包含1～8，5号重复为散热焊盘。

当前BOM与来源哈希分别见 [控制板BOM](../controller/hardware/g431_core/bom/bom.csv)、[控制板清单](../controller/hardware/g431_core/review/design_manifest.json)、[底板BOM](../inverter/hardware/bom/bom.csv)及 [底板清单](../inverter/hardware/review/design_manifest.json)。本轮改动前原生图分别保存在两板 `history/rev_e_before_shared_parts_2026-11-11*.zip`；导出XML基线保存在 `outputs/schematic_review_2026-11-11/baseline/`。

以上检查覆盖原理图连接、库定义与静态逻辑，不作为PCB验证结论。后续已建立本版 [PCB 0.1布局审查稿](pcb_review_2026-11-11.md)，其实际布线与DRC独立记录；回流、寄生参数、保护动态、热和插合仍需后续验证。

## 需要继续补的物料

剩余 **65组、233个位号** 尚未确定完整采购型号：默认装配220个，DNP13个。分组可填写表见 [selection_pending.csv](parts_to_complete_2026-11-11/selection_pending.csv)，保留每个位号的用途、额定与候选记录。分组是选料起点，同组共用一个料号前仍须满足所有用途。

| 板卡 | 分组 | 位号数 | 默认装配 | DNP | 内容 |
| --- | --- | --- | --- | --- | --- |
| controller | 13 | 26 | 23 | 3 | 16电容、9电阻、1晶振 |
| inverter | 52 | 207 | 197 | 10 | 152电阻、50电容、5LED |

普通贴片电阻和通用小陶瓷电容继续统一YAGEO。关键约束：

- 控制板 C301/C302：4.7µF、0805、25V，在5.25V偏压下有效容量至少2.2µF；C303：4.7µF、0805、16V，在3.3V偏压下有效容量至少2.2µF。C68为另一组0603器件，不能直接合并。
- C305已采用 T491B476K010AT 稳定性关键钽电容，不并入普通同值MLCC。
- 底板七颗15Ω / 0805栅极电阻 R17/R19/R20/R25/R26/R31/R32 需核脉冲适用性；R209的10k / 0603公差仍未定，与已指定1%的10k组分开。
- 可选HSE的 Y1、C83/C84 默认DNP；18pF仅为占位值，待实际晶体CL、ESR、驱动等级及PCB杂散确定后重算。

[2026-11-10旧清单与Excel](parts_to_complete_2026-11-10.md)保留为历史记录，当前补料以本页及新的65组CSV为准。PCB焊线孔、测试点不需建立采购连接器；外接制动电阻和外置NTC不计入板载待补数量。

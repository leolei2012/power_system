# Rev E应用功率底板BOM

[bom.csv](bom.csv)来自当前二十页原理图，317个位号、14项默认DNP；配套 [最小核BOM](../../../controller/hardware/g431_core/bom/bom.csv)为47位号/3DNP。两板合计DNP仍为17项，分配已经改变，不能按Rev D的140/219清单装配。

底板包含功率与应用电路：SWD/TTL/ABZ/SPI/CAN、五个LED、ADC RC和回传钳位也在本表。默认DNP包括可选CAN整支路、四个传感器5 V连接及原有J7/R8/D2。两组排母PM254V-12-32-H85/C46595991已采用共享reviewed符号及专用封装，规划装在上层功率板底面朝下，配套下板顶面朝上的PZ254V-12-32P/C22465940；实物插合和整板机械仍待验证。8.5 mm是母座塑高，不是冻结板距。

2026-11-11已按最终原生图XML刷新BOM，91个位号采用reviewed共享物料；[selection_pending.csv](selection_pending.csv)剩207个位号、52组完整采购型号待选，[library_intake.csv](library_intake.csv)为零行，已选型号无需重复建库。两板合并的65组选型表与关键约束见 [本轮交接](../../../docs/schematic_update_2026-11-11.md)。普通小阻容按国巨补齐；器件库reviewed不等于应用验证。J3/J4/J5是工程焊线孔，不采购对应端子；外接制动电阻及NTC不计板载装配。

两块PCB已建立60×60mm布局审查稿，上功率下最小核、轮廓边线对齐，四个2.2mm M2孔心距52×52mm。实际布线/DRC见 [PCB交接](../../../docs/pcb_review_2026-11-11.md)；插合高度、额定、热及动态保护尚未闭环。当前约束见 [审查](../design_review.md)，旧40针双板见 [Rev D归档](../../history/daughterboard_rev_d_before_minimum_core_2026-11-07.zip)。

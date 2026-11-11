# Rev E功率底板PCB 0.1审查

已从当前317件原理图建立 [inverter.kicad_pcb](inverter.kicad_pcb)，另有4个安装孔。969个唯一符号引脚对应976个编号铜焊盘（7颗MOS的5号散热焊盘各重复一次），14项DNP保持。当前为完整元件布局与主功率/Kelvin布线初稿，驱动、辅助电源、保护逻辑及接口信号仍未全部布通。

两板均60×60mm，本板为上层；6层、1.6mm及1oz铜厚为候选。四个2.2mm NPTH孔心距52×52mm，距板边4mm。两组母座装B面朝下，64针与下层公头逐号同心。共同坐标见 [机械合同](../../docs/pcb_stack_contract_rev_e.json)和 [双板交接及预览](../../docs/pcb_review_2026-11-11.md)。最小孔周铜避让半径2.8mm，铺铜另有3.0mm余量。

## 本版布线与检查

保存板有1852段线、295个过孔、12块导电铜区（含规则区的总zone数为46），已实际填铜。原生DRC没有电气/几何错误；仍有10条悬空铜警告（8过孔、2走线）。内部计数与原生报告均为236项未连接。当前统计见 [pcb_review.json](review/pcb_rev_e_2026-11-11/pcb_review.json)、[最终跨板检查](../../outputs/pcb_review_2026-11-11/system_check.json)及 [原生DRC](../../outputs/pcb_review_2026-11-11/inverter_drc.json)，不能表述为布线完成或DRC全部通过，当前不能据此制板。

原锁定的277段主功率线、98个过孔保持；本轮增加普通信号布线、GND连接过孔及In3上X≤142.5mm低压区域的`+3V3_INV`铜区。BB_L1和VREG测试点TP2已闭合，剩余驱动、辅助电源、保护逻辑和接口连接仍待完成。

In3的VBUS铜区优先级为2，`+3V3_INV`铜区为1，保证相交区域由母线保留。为恢复母线连续，还撤回4网共19段未锁定In3线：`+3V3_INV` 3段、`OC_HIGH_REF` 6段、`Net-(D206-K1{slash}A2)` 2段、`+5V_INV` 8段。锁定功率铜及原zone轮廓保持；撤线留下的5个额外普通过孔悬端包含在上述警告中。

全部位号、Value、DNP、封装、物理焊盘网络、板框、安装孔、courtyard及3D路径纳入最终核对。原生parity有120项，全部为KiCad 10的`ki_fp_filters`保留字段提醒；测试点BOM属性、资料字段及BAT54S自动网名的`{slash}`编码已对齐。编码差异按同一网络规范化核验，没有改变原理图或合并网络。

32个纯阻焊辅助pad已注记为与同位铜pad同网，解决自身阻焊桥误判；没有改变铜几何或电路网络，见 [阻焊注记独立核对](../../outputs/pcb_review_2026-11-11/mask_only_net_association_review.json)。

恢复母线连续后的 [主功率几何检查](review/pcb_rev_e_2026-11-11/power_plane_restored/critical_geometry.json)通过输入→F1、F1→整流器、VBUS、主GND、制动输出及三相PHASE/SOURCE/负端Kelvin共14组连接。检测依据为保存后的实际焊盘、走线、过孔和逐层填铜岛。三相输出增加短的In2宽铜，连接漏极转层区与实际输出孔。

低管SOURCE先接分流热端，驱动COM返回本相SOURCE，INA从分流两端独立Kelvin引出。三路负端Kelvin过孔在In1/In4均有地平面避让。细采样支路不充当驱动回流路径，本轮路由将Kelvin段列为保护对象；新增布线后的实际接触和隔离见 [最终Kelvin核对](../../outputs/pcb_review_2026-11-11/final_kelvin_review.json)。[power_copper.json](review/pcb_rev_e_2026-11-11/power/power_copper.json)仅追踪锁定的关键功率铜，完整布线统计与未连接项目以当前PCB、`pcb_review.json`及最终跨板报告为准。

每相分流冷端有4个0.8/0.4mm并联过孔。其它原计划4孔的转层组以实际数量为准：U相source-transfer为2个、U相VBUS为3个、V相VBUS为2个；本版未证明这些位置的载流、均流及温升能力。分流焊盘内过孔及部分贴片焊盘附近过孔还需填孔/盖孔或焊料流失评估。

## 装配与剩余工作

功率MOS和电解优先在顶面，驱动与大量低压逻辑双面布置，母座在背面。驱动/门阻/自举按半桥局部分组，U2/L1和U3/L2的自举电容靠近对应脚；这些电路仍有未连接项，不能把元件靠近等同于连线完成。未连接清单见当前原生DRC报告。

底板两侧3.3V不并联；U1的8/17脚是EFUSE_RTN。J5外接制动电阻线从顶面引出，避免向下进入控制板两键操作区。母座8.5mm塑高不直接确定板距，4套M2支柱/螺钉的完整型号与长度待定。B面薄型器件的二维投影仍进入按键区域，操作净空须插合后实测。

Q1～Q7没有3D实体模型，预览显示真实焊盘；两只220µF/100V电解的25mm高度已纳入外观预览。仍有207个底板位号待确定完整采购型号，见 [待选BOM](bom/selection_pending.csv)。本版未完成整板损耗/温升、EMI、保护动态、插接或装配验证，未生成生产包。

本轮原理图和共享库保持只读。Rev C集成PCB及Rev D针序不适用于此版；历史与原理图入口见 [README](README.md)。

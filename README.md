# power_system

最新方案已收敛为**单功率PWM口**：PWM8P、CTRL、SPI、I²C、ABZ各一路，CAN/TTL/SWD各一路；保留10个独立ADC2P端子和5V输入。按重复功能各减一路的规划，共19个连接器；电机与PFC二选一。推荐沿用已有STM32G431RBT6（LQFP64）物料，44个功能脚已分配、剩8个。见 [当前引脚表](docs/controller_single_power_pin_plan.csv)、[连接器总表](docs/controller_connector_inventory.csv)和 [规划说明](docs/controller_daughterboard.md)。旧双功率口/100脚规划已归档，原生工程仍是Rev E排针版，尚未迁移到端子版。

低压电力电子实验平台。当前 **Rev E为STM32G431RBT6最小系统子板＋应用功率底板**：子板只通过排针插接底板，全部52个可GPIO复用信号pad集中引出；编码器、SPI、TTL、CAN、LED及应用采样/保护均在底板。每套仍控制一路三相桥和一路制动，采用共地、非隔离连接。PFC电源板本阶段暂不绘制。

| 当前工程 | 原理图交付 | PCB 0.1 布局审查 |
| --- | --- | --- |
| [G431最小核](controller/hardware/g431_core/README.md) | 7页、47个位号、3项DNP；[KiCad](controller/hardware/g431_core/controller.kicad_pro)、[PDF](controller/hardware/g431_core/review/controller.pdf) | [60×60mm四层PCB](controller/hardware/g431_core/controller.kicad_pcb) |
| [应用功率底板](inverter/hardware/README.md) | 20页、317个位号、14项DNP；[KiCad](inverter/hardware/inverter.kicad_pro)、[PDF](inverter/hardware/review/inverter.pdf) | [60×60mm六层PCB](inverter/hardware/inverter.kicad_pcb) |

原理图已更新为共享库器件审查稿，双ERC为0错误/0警告；64针、52个信号pad及32768组静态保护/ARM逻辑检查通过。原理图变更、验证与待补物料见 [2026-11-11 原理图交接](docs/schematic_update_2026-11-11.md)。两块PCB已建立60×60mm布局审查稿，上层功率板、下层G431最小核，轮廓边线对齐；四个M2安装孔中心相距52×52mm。实际布线、未连接与DRC状态见 [PCB交接及预览](docs/pcb_review_2026-11-11.md)，板距、插合及散热仍待验证。当前连接和使用方法见 [最小核与功率底板](docs/controller_daughterboard.md)，实际位号见 [子板BOM](controller/hardware/g431_core/bom/bom.csv)和 [底板BOM](inverter/hardware/bom/bom.csv)。

两组2×16、2.54 mm排针共64针：52个MCU信号pad、2针5 V输入、2针核心3.3 V参考、CTRL_READY及7地。子板全部引出，底板9个未用插座脚显式NC。子板独立使用时仍从J101/1、3送入4.75～5.25 V，不增加独立电源/调试连接器；禁止并联两路5 V来源。

子板保留MCU及去耦/VDDA/VREF、可选HSE、RESET/BOOT按钮、本地5 V转3.3 V及监控。PC7在插底板时保留RUN_ARM职责：NRST经U103施密特缓冲后，与默认下拉的PC7通过U105相与生成CTRL_READY。ROM启动和复位阶段不因NRST释放就自动许可功率桥。SWD、BOOT和ROM串口使用条件见 [引脚说明](inverter/docs/pin_assignment.md)。

功率目标沿用12～60 V直流母线、直流输入最大10 A、每相连续10 Arms及20 kHz桥PWM。底板另接12～24 V辅助电源，产生驱动12 V、5 V及本地3.3 V。子板3.3 V总负载预算100 mA，底板回传钳位的短时总正向注入预算50 mA；两侧3.3 V不并联。共地结构不保证炸管后MCU存活，额定、动态保护、插接和热仍待实物验证。

电源板的Boost/Vienna版本及PFC＋LLC仍属后续规划，相关输入、变比和单MCU资源不由本次原理图确认。实验链路与长期讨论见 [架构](vfd/docs/architecture.md)和 [路线图](docs/roadmap.md)；当前先用实验直流源。

## 历史与器件约定

上一版40针、应用接口在子板的Rev D已整体 [归档](inverter/history/daughterboard_rev_d_before_minimum_core_2026-11-07.zip)，不能与Rev E混插。原 [LKS controller](controller/hardware/controller.kicad_sch)仍保留历史；更早的 [Rev C集成板](inverter/history/integrated_rev_c_60x60/)、[Rev A](inverter/history/split_rev_a_2026-11-06.zip)及 [PCB0.1](inverter/history/pcb_0_1_200x140_before_60mm_2026-11-06.zip)不覆盖当前双板。

器件统一在国内立创商城选型，采购链接使用国内商品页；普通小贴片阻容统一YAGEO，分流、电解及稳定性关键电容另行选型。相邻公共库为kicad_library；项目draft符号/封装不等于公共库reviewed或实物验证。两板bom目录分别保留完整型号待定和公共库待建清单，原生图与实际XML为连接依据。参考资料见 [reference](reference/README.md)及 [ATK-PD6010B](reference/ATK-PD6010B/README.md)。

上一轮21款待建型号已全部入库并接入原理图，另复用已reviewed的100nF / 0603电容。目前已选型号无需重复建库，剩余 **65组、233个位号** 待确定完整采购料号，见 [当前待选CSV](docs/parts_to_complete_2026-11-11/selection_pending.csv)与 [交接说明](docs/schematic_update_2026-11-11.md)。[2026-11-10 清单和Excel](docs/parts_to_complete_2026-11-10.md)保留为历史快照。

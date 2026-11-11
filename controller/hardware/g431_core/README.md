# Rev E STM32G431最小系统板

本工程为 **只通过两组2×16排针连接底板的G431最小核**。七页原理图已完成，47个位号、3项HSE默认DNP；全部52个可GPIO复用信号pad引出。2026-11-11已将20个位号同步为共享库reviewed符号及封装，本轮核心ERC0错误/0警告，233个物理引脚节点与迁移前等价，64针/52pad核对通过；双板系统检查已统一刷新并为PASS。已建立 [controller.kicad_pcb](controller.kicad_pcb)四层PCB 0.1布局审查稿，实际布线/DRC见 [双板PCB交接](../../../docs/pcb_review_2026-11-11.md)。两板均60×60mm，本板位于下层，轮廓边线对齐；四角M2孔心距52×52mm，装配仍待验证。

- [KiCad](controller.kicad_pro)、[原理图](controller.kicad_sch)、[PDF](review/controller.pdf)、[实际XML](review/controller.net.xml)
- [MCU脚表](STM32G431RBT6_pin_plan.csv)、[BOM](bom/bom.csv)、[待选](bom/selection_pending.csv)、[候选入库](bom/library_intake.csv)
- [64针、供电和启动操作](../../../docs/controller_daughterboard.md)、[应用脚表](../../../inverter/docs/pin_assignment.md)、[本地供电分析](core_supply_design.md)
- [本轮迁移记录](review/shared_parts_2026-11-11/migration.json)、[逐pin等价](review/shared_parts_2026-11-11/pin_equivalence.json)、[共享封装引脚检查](review/shared_parts_2026-11-11/footprint_pin_check.json)、[SVG](review/shared_parts_2026-11-11/svg/)

## 最小核范围

仅保留MCU/去耦、VDDA/VREF、RESET/BOOT按钮、可选DNP晶振及负载电容、本地5 V转3.3 V/监控、ARM许可和GPIO排针。SWD/TTL/ABZ/SPI/CAN专用接口、四个GPIO LED及ADC应用滤波/钳位全部在底板，不在最小核重复放置。

64针包含52个MCU信号pad、2针5 V输入、2针核心3.3 V参考、CTRL_READY和7地，子板无GPIO NC。52是可复用物理pad数量，并非52个可同时自由使用GPIO：PG10保留NRST，PF0/PF1与HSE复用，PB8与BOOT0复用，PA13/PA14默认SWD。底板九个未用socket脚NC属于底板用途，不改变最小核引出情况。

U103将NRST缓冲成CORE_RESET_OK，U105再与PC7相与输出CTRL_READY。R402 10k使PC7默认低；插底板时PC7必须保留RUN_ARM职责，应用完成安全初始化后才能主动拉高。独立使用可按GPIO使用PC7。NRST释放不等于功率桥允许运行。

## 供电、调试与BOOT

独立使用从J101/1、3输入 **4.75～5.25 V**，接相应GND；插底板时由底板供电，不增加独立连接器，禁止并联两个5 V源。TLV76733DRVR产生本地+3V3_MCU，总负载预算100 mA。J101/22、32输出核心参考，仅供底板回传钳位/故障上拉及调试电平参考，不能并入底板本地3.3 V或作为其通用电源。

独立板从GPIO排针接PA13/SWDIO、PA14/SWCLK、NRST、3.3 V VTREF和GND；插底板时可用底板SWD口。NRST有本地监控/按键，外部仅作开漏拉低，不用推挽驱动。

物理BOOT法要求选项位 **nSWBOOT0=1、nBOOT1=1、BOOT_LOCK=0**。按住BOOT，按下并释放RESET，再松开BOOT。ROM USART3使用 **PC10_TX/PC11_RX**，不是应用TTL的PB10/PB11；使用时断开复用这两脚的SPI B外设。ROM阶段PC7保持默认低，功率桥不得取得ARM许可。

## 机械与限制

排针为XFCN PZ254V-12-32P / C22465940，配套底板排母PM254V-12-32-H85 / C46595991，两组2×16/P2.54。公头已采用共享库reviewed符号及厂家尺寸封装；子板顶面male朝上、功率板底面female朝下，实际插合、两板布局及装配仍须验证。母座8.5 mm只是塑高，不冻结板距，需按相向元件、插合及通风/装配余量决定。Rev E不兼容上一版40针接口。

MCU放在下层控制板顶面、朝两板之间，避开上板功率热源及高dv/dt铜区投影。RESET（SW2）和BOOT（SW3）均在控制板顶面、与MCU同面，操作面朝上，靠板边从侧面伸入后向下按，并与排针、M2支柱及线束错开。插合后侧向通道须允许按住BOOT的同时操作RESET。两键已同步为XKB Connection [TS-1101-C-W / C318938](https://item.szlcsc.com/300030.html)的共享reviewed符号及封装，电气功能不变；实际操作净空须随板距、支撑及线束共同校核，尚未经机械验证。

底板限流/钳位经核心参考轨回传的短时总正向注入预算50 mA，不是硬限流或持续耐受保证。共地、非隔离结构不保证炸管后MCU存活，PCB、采样时序、供电/保护动态及热仍待验证。旧97件迁移子集脚本及Rev D报告仅属历史，不用于覆盖当前最小核。

## 当前复核与待补物料

本轮采用共享件的20个位号包括MCU、两公头、两键、本地电源/保护的已选器件，以及C304/C306/C307/C308的100nF、50V、X7R、0603国巨C14663。其余26个位号仍缺完整采购型号，其中Y1/C83/C84保持DNP；普通待选阻容的数值、封装及已有约束均保留。BOM由根工程按最新XML统一导出。

在本目录可运行 `python tools/migrate_reviewed_parts_2026_11_11.py --verify` 复核本轮前后逐pin等价。该脚本的`--apply`是一次性增量迁移，不用于重新生成工程。备份见 [迁移前快照](history/rev_e_before_shared_parts_2026-11-11.zip)。双板新系统报告入口为 [根工程检查](../../../outputs/schematic_review_2026-11-11/system_check.json)及 [本地系统报告](review/system_check.json)，已按最终XML复核并为PASS；旧报告不能替代本轮复核。

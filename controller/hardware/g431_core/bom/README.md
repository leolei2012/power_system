# Rev E G431最小核BOM

[bom.csv](bom.csv)来自当前七页原理图，47个位号、3项默认DNP，仅为HSE晶体和两个负载电容。最小核只包含MCU/去耦/VDDA/VREF、RESET/BOOT/HSE、本地稳压/监控、PC7 ARM联锁及两组2×16排针。应用接口、LED和ADC RC/钳位已在 [底板BOM](../../../../inverter/hardware/bom/bom.csv)。

2026-11-11原生图已将20个位号同步为公共库reviewed符号及封装，包括C304/C306/C307/C308采用国巨CC0603KRX7R9BB104/C14663；其余26个位号、13组仍待确定完整采购型号，另有1个PCB测试点。已按最终XML统一刷新 [bom.csv](bom.csv)、[selection_pending.csv](selection_pending.csv)及 [library_intake.csv](library_intake.csv)；library_intake为零行，已选型号无需重复建库。两板合并的65组选型表见 [本轮交接](../../../../docs/schematic_update_2026-11-11.md)。普通阻容按国巨；C305的KEMET钽电容是稳定性关键件，不能随意以同标称MLCC代换。器件reviewed不等于应用或实物验证。

排针PZ254V-12-32P/C22465940已采用共享reviewed符号及厂家尺寸封装，规划装在下层最小核顶面朝上，配套上板底面朝下的PM254V-12-32-H85/C46595991；实际插合和两板装配仍待验证。母座8.5 mm塑高不直接决定两板间距。两板同60×60 mm轮廓，四角M2支撑待共同校核；RESET（SW2）/BOOT（SW3）均在下层控制板顶面、与MCU同面，操作面朝上，靠板边从侧面伸入后向下按，与排针、支柱和线束错开。两键已同步为XKB Connection [TS-1101-C-W / C318938](https://item.szlcsc.com/300030.html)共享reviewed符号及封装，电气功能不变，插合后操作净空随板距、支撑及线束共同校核。独立供电沿用J101/1、3，不新增连接器，不得并联独立5 V与底板5 V。

以 [原理图](../controller.kicad_sch)、[供电说明](../core_supply_design.md)及 [64针合同](../../../../docs/controller_daughterboard.md)为准。已建立配套 [PCB 0.1布局审查稿](../controller.kicad_pcb)，实际布线/DRC见 [PCB交接](../../../../docs/pcb_review_2026-11-11.md)；机械、启动/供电动态、热和装配仍未完成生产验证。上一版140件应用子板属于Rev D历史。

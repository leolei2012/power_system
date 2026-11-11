# STM32G431最小系统子板

当前 **Rev E为仅通过两组2×16排针连接底板的G431最小系统板**。新工程位于 [g431_core](hardware/g431_core/README.md)，七页原理图已完成，47个位号、3项HSE默认DNP；本工程ERC0错误/0警告，64针/52pad及系统ARM联锁检查通过，PCB未画。最小核现规划60×60 mm，位于功率板下层，与上板轮廓边线对齐；四角M2孔待两板PCB共同校核。

- [KiCad](hardware/g431_core/controller.kicad_pro)、[原理图](hardware/g431_core/controller.kicad_sch)、[PDF](hardware/g431_core/review/controller.pdf)
- [MCU脚表](hardware/g431_core/STM32G431RBT6_pin_plan.csv)、[BOM](hardware/g431_core/bom/bom.csv)
- [64针合同和供电/BOOT操作](../docs/controller_daughterboard.md)

子板只保留STM32G431RBT6、去耦/VDDA/VREF、RESET/BOOT与HSE候选、本地稳压监控及PC7 RUN_ARM联锁。全部52个可GPIO复用pad引出，包括按NRST使用的PG10、PF0/PF1和PB8/BOOT0；专用SWD、TTL、ABZ、SPI、CAN、四个GPIO灯及ADC应用滤波/保护均在inverter底板。

独立使用同样从J101/1、3输入4.75～5.25 V，并从GPIO排针接SWD。插底板时由底板5 V供电，不能并联两个5 V源。3.3 V参考仅供底板回传钳位/故障上拉及调试参考，不与底板本地3.3 V并接。PC7独立使用可作GPIO，插功率底板时必须保留ARM职责。

MCU放在下层控制板顶面、朝两板之间，避开上板热源及高dv/dt铜区投影。RESET（SW2）/BOOT（SW3）也在控制板顶面、与MCU同面，操作面朝上，靠板边从侧面伸入后向下按，并与排针、支柱及线束错开；两键统一采用TS-1101-C-W/C318938，电气功能不变。插合后的操作净空须随板距、支撑及线束共同校核。子板顶面排针朝上，连接上层功率板底面朝下的排母，实际板距不由母座8.5 mm塑高单独决定。

## 历史资料

[hardware/controller.kicad_sch](hardware/controller.kicad_sch)及 [九页说明](hardware/README.md)是LKS32MC451VCT8集中控制双逆变/PFC的历史稿，未覆盖。原100脚/25ADC及集中ThreadX预算不能用于本次最小核。上一版Rev D的应用子板已 [归档](../inverter/history/daughterboard_rev_d_before_minimum_core_2026-11-07.zip)，其40针、140位号及旧复位合同不适用于Rev E。

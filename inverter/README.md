# 变频应用功率底板

当前 **Rev E二十页功率底板原理图已完成**，配套 [G431最小系统子板](../controller/hardware/g431_core/README.md)。底板不放MCU，但集中放置全部应用接口与保护；每套仍由一颗STM32G431RBT6控制一路三相桥和一路制动。底板317个位号、14项DNP，本工程ERC0错误/0警告，64针/52pad及系统ARM联锁检查通过。

- [KiCad与硬件说明](hardware/README.md)、[当前PDF](hardware/review/inverter.pdf)、[BOM](hardware/bom/bom.csv)
- [应用引脚分配](docs/pin_assignment.md)、[64针合同](../docs/controller_daughterboard.md)、[PCB状态](hardware/PCB_REVIEW.md)

底板保留MOS/驱动/自举、分流/INA、电压及NTC前端、比较器、故障锁存、PWM门控和制动；并接回SWD、TTL、两路ABZ、两路SPI、可选DNP CAN、五个LED、ADC末端RC及输入限流/钳位。最小核52个信号pad全部引出，本底板对其中9个不用的插座脚显式NC；PC7的ARM功能在子板内部完成，不需接入底板PC7插座脚。

| 功率指标 | 当前目标 |
| --- | --- |
| 直流母线/输入电流 | 12～60 V DC，输入最大10 A |
| 连续相电流 | 每相10 Arms设计目标，额定与热验证未完成 |
| 桥PWM/输出 | 20 kHz，U/V/W为原始PWM |
| 制动 | 一路独立软件命令，电阻外接，不用可开路 |
| 辅助输入 | 独立12～24 V，产生驱动12 V、5 V及本地3.3 V |

J101/1、3将底板+5V_INV送至子板+5V_CORE_IN；J101/22、32接收核心3.3 V参考，只用于回传保护/上拉及调试参考，禁止与底板本地3.3 V并接。NRST现由64针接口接到底板SWD。CTRL_READY须同时满足子板复位正常和PC7主动ARM，不能仅靠NRST释放就开桥。

机械规划为 **两板均60×60 mm，上功率板、下G431最小核，轮廓边线对齐**；四角M2孔为共同支撑规划，PCB均未画。功率板底面排母朝下，子板顶面排针朝上；板距按插合、相向器件高度及通风/装配余量确定，不把8.5 mm母座塑高当板距。

功率器件/电解在上板顶面外露便于布置，但BSC110N15NS5主要经底部焊盘向PCB导热，仍需安排上板背面和风道；上下位置交换不能保证10 Arms。下板MCU置于顶面、朝两板之间，避开上板热源及高dv/dt铜区投影。RESET（SW2）/BOOT（SW3）均在下层控制板顶面、与MCU同面，操作面朝上，靠板边从侧面伸入后向下按，并与排针、支柱和线束错开；两键统一采用TS-1101-C-W/C318938，电气功能不变，插合后操作净空须随板距、支撑及线束共同校核。共地、非隔离结构仍不保证炸管后子板完好，热、采样和保护动态未验证。

[Rev D40针双板](history/daughterboard_rev_d_before_minimum_core_2026-11-07.zip)、[Rev C集成板](history/integrated_rev_c_60x60/)及更早PCB均保留历史，不作为当前连线或生产依据。PFC电源板暂不绘图，本板不增加PFC/LLC专用接口。

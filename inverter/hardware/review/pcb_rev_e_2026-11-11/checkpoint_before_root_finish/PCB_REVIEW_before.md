# Rev E功率底板PCB状态

当前二十页Rev E应用功率底板原理图已完成，317个位号、14项DNP，配套七页47位号最小核。双ERC为0错误、0警告；64针、52个信号pad及静态ARM/保护逻辑检查通过。**新PCB尚未设计**，这些检查不是DRC或10 A连续工作验证。

机械规划为 **上层功率板、下层G431最小核，两板均60×60 mm、轮廓边线对齐**。规划四角M2孔作共同支撑，孔位/边距/干涉需两板PCB共同校核。PCB均未布局，板厚、叠层及板距仍待设计；旧Rev C六层1 oz、孔位及布线不能直接沿用，不发布Gerber、钻孔或装配包。

当前资料：[原理图](inverter.kicad_sch)、[PDF](review/inverter.pdf)、[BOM](bom/bom.csv)、[64针合同](../../docs/controller_daughterboard.md)、[审查](design_review.md)。

## 新布局边界

- 两组2×16/P2.54：下层子板顶面PZ254V-12-32P male朝上，上层功率板底面PM254V-12-32-H85 female朝下。8.5 mm只是母座塑高，板距须按相向器件高度、完整插合、公差及通风/装配余量核定；均属待核机械draft，不能混接旧40针板。
- 下板MCU放在顶面、朝两板之间，避开上板热源及高dv/dt铜区投影。RESET（SW2）/BOOT（SW3）均在下层控制板顶面、与MCU同面，操作面朝上，靠板边从侧面伸入后向下按；与排针、M2支柱及线束错开，两键统一采用TS-1101-C-W/C318938，电气功能不变。插合后实际操作净空须随板距、支撑及线束共同校核，当前尚未经机械验证。
- 全部应用接口、五个LED、八路ADC RC/钳位及状态回传保护在底板；应用RC靠近GPIO插座布置，跨板到MCU的实际走线与回流须纳入采样和EMI评估。
- J101/1、3提供5 V；22、32只接收核心3.3 V参考，禁止与底板本地3.3 V并接。NRST经J102/32到SWD；PC7在子板内参与ARM，底板PC7 socket为NC，CTRL_READY单独经J102/10。
- 每相SOURCE先经分流再到GND；驱动COM/栅源回流保持本相SOURCE，禁止铜区旁路分流。INA两输入分别Kelvin取样，负端不能从任意地平面代取。
- HO/LO、栅阻、自举和浮动参考组成短局部环路。U2/L1、U3/L2及相应电容保持局部开关环路。
- U1 TPS26600的EP17/引脚8为EFUSE_RTN，不是GND；R8仍DNP，SW1接EFUSE_RTN。底板比较器、锁存、PWM门控及失联下拉必须本地闭环。

## 器件及额定

功率目标仍为12～60 V母线、输入最大10 A、每相连续10 Arms与20 kHz桥PWM。Q1～Q7采用BSC110N15NS5，物理1/2/3=S、4=G、5/6/7/8=D；D1 MBRD20150CT-13按DS37086 Rev4-2 / September2026核1/3=A、2/tab=公共K。两阳极并联不自动证明均流或10 A散热能力。上板顶面MOS/电解外露只是方便布置，BSC110N15NS5主要经底部焊盘向PCB导热，必须安排上板背面导热/风道；交换上下位置不能保证10 Arms，需实测损耗、热耦合及温升。

F1/F2分断、I²t和热降额需与直流源协调；L1/L2只用于辅助转换器。2×220 µF/100 V电解需核纹波/温升及D12.5×H25 mm结构空间。J3/J5为6 mm间距2P焊线孔、J4为15 mm三相孔，当前2.0 mm孔/4.5 mm盘仍需线束及温升确认。

[工程封装说明](Inverter_Compact_README.md)和 [来源记录](Inverter_Compact_sources.csv)保留候选依据；有封装不等于公共库reviewed或实物验证。后续须检查新PCB全错误DRC、未连接、原理图一致性、重复焊盘号、DNP、64针及9个底板NC、SOURCE/Kelvin、主电流截面、回流和装配，然后完成波形、热及故障动态测试。共地接口不保证炸管后MCU存活。

## 历史

[40针Rev D双板](../history/daughterboard_rev_d_before_minimum_core_2026-11-07.zip)、[60 mm六层Rev C集成PCB](../history/integrated_rev_c_60x60/inverter.kicad_pcb)及 [200×140 mm四层PCB0.1](../history/pcb_0_1_200x140_before_60mm_2026-11-06.zip)只用于追溯。旧PCB或旧DRC通过结果不得作为Rev E制板依据。

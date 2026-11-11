# Rev E最小核与应用底板审查

2026-11-11：已将底板确定采购型号同步到reviewed共享库，并保持一颗STM32G431RBT6控制一路三相桥及一路制动。子板仍为全部GPIO引出的最小系统；调试、传感器、CAN、LED、ADC滤波/钳位等应用功能均在底板。PFC/LLC电源板本阶段仍不绘图。

| 当前交付 | 最小核 | 功率底板 |
| --- | --- | --- |
| 原理图 | [7页](../../controller/hardware/g431_core/controller.kicad_sch) | [20页](inverter.kicad_sch) |
| PDF | [controller.pdf](../../controller/hardware/g431_core/review/controller.pdf) | [inverter.pdf](review/inverter.pdf) |
| BOM | [47位号、3DNP](../../controller/hardware/g431_core/bom/bom.csv) | [317位号、14DNP](bom/bom.csv) |
| ERC | 0错误、0警告 | 0错误、0警告 |

64个排针、52个信号pad、1061个旧物理pin连通等价及32768组静态保护/ARM逻辑检查已有基线通过记录。外设3.3 V迁到底板和新增ARM分裂是明确的设计变化。本轮底板共享库迁移另经实际CLI网表确认317个位号、969个物理pin节点和238条网络分区等效，64针/标称值/14DNP保持，ERC0/0；BAT54S的八条自动网络名因厂家pin3名改为K1/A2而变化，连通分区完全一致，见 [本轮报告](review/shared_parts_2026-11-11/pin_equivalence.json)。最新跨板检查见 [system_check.json](review/system_check.json)。检查不代表瞬态、传播延迟、热、机械或实物故障验证。两块新PCB已建立同60×60mm的PCB 0.1布局审查稿，实际布线及DRC见 [PCB交接](../../docs/pcb_review_2026-11-11.md)；上层功率板、下层G431最小核，四角M2孔心距52×52mm，支撑高度及实际装配待共同校核。

## 64针、供电与ARM

两组2×16/P2.54：52个MCU信号pad、2个5 V输入、2个核心3.3 V参考、CTRL_READY和7地。子板全部引出，包括NRST/HSE/BOOT复用脚；底板9个未用socket脚NC与子板是否引出是两回事。[完整针表](../../docs/controller_daughterboard.md)是当前合同，旧40针Rev D不可混插。

J101/1、3输入4.75～5.25 V；独立板和插底板均使用同一入口，禁止并联两个5 V源。子板TLV76733DRVR提供独立+3V3_MCU，持续总预算100 mA。J101/22、32输出核心参考到+3V3_CORE_REF，仅供底板回传钳位/故障上拉及SWD VTREF，不能与底板+3V3_INV并联或供通用负载。TPS3808保留本地电源监控及二极管前5 V检查，详见 [供电说明](../../controller/hardware/g431_core/core_supply_design.md)。

U103施密特缓冲NRST成为CORE_RESET_OK，U105与PC7相与后输出CTRL_READY。R402 10k使PC7复位默认低；插底板时PC7为RUN_ARM，应用完成安全初始化后才能主动拉高。底板仍以CTRL_READY和ENABLE形成许可。复位释放、BOOT按钮或ROM串口活动不能直接取得功率桥许可。

比较器、健康链和故障锁存独立在底板封锁六路PWM；FAULT_N由Q8开集电极返回，经1 kΩ/钳位进入PB12，10k上拉参考核心轨。BASE_READY经保护进入PC13。原始NRST现经J102/32到达底板SWD，外部只能开漏拉低。制动仍为独立软件控制，不与桥ENABLE/FAULT许可相与。

## 应用与采样

ABZ、SPI、TTL、CAN、五个LED、应用ADC RC和输入保护全在底板。八路采样经360 Ω/BAT54S钳位，再接100 Ω/1 nF；七路缓冲源另有47 Ω，合计507 Ω。NTC另计10k源阻和10 nF滤波，不能套用统一0.46 µs。比较器继续读取源端；ADC保护及末端RC靠近底板插座布置，跨板走线、参考地及ADC采样时间仍需实际核算。

两ADC不能让三相电流全部同时转换，低端分流窗口与重构需后续验证。八路模拟和两路状态钳位短时总正向注入预算50 mA，由核心轨有限吸收，不是硬限流或持续故障耐受。共地结构不保证炸管后MCU存活，断开两路电源后装拆。

物理BOOT法需要nSWBOOT0=1、nBOOT1=1、BOOT_LOCK=0；按住BOOT，按放RESET，再松BOOT。ROM USART3为PC10_TX/PC11_RX，不是底板应用TTL的PB10/PB11；PC10/PC11与SPI B复用，使用ROM串口须断开相关外设。PC7在插底板时保留ARM，详见 [应用引脚](../docs/pin_assignment.md)。

## 保留的功率目标与未完成项

12～60 V母线、直流输入最大10 A、每相连续10 Arms为目标，桥PWM20 kHz；同时可用工作区及热额定未验证。名义硬件过流±20 A、过压65 V；电流量程1.65 V±50 mV/A，四路电压50:1。65 V是故障门限。2×220 µF/100 V、外接制动电阻及原始三相PWM输出保留，不设独立预充/母线放电。

三颗2ED2182S06FXUMA1/C1850289驱动、七颗BSC110N15NS5ATMA1/C412739、SOURCE经分流回地及Kelvin结构保留，已全部引用共享符号及专用封装；MOS 1～3=S、4=G、5～8=D及重复D5大焊盘逐号核对。D1双肖特基符号的1/3阳极仍并联，2/散热片为阴极，局部改线保持原网络。15 Ω栅阻、自举2.2 µF+100 nF为波形验证起点。17颗原25 V要求的100 nF/0603采用国巨50 V、±10%、X7R的CC0603KRX7R9BB104/C14663。其余152颗电阻、50颗电容和5颗LED仍为TBD；电容DC偏压、脉冲、稳定性及热仍属应用验证。

排针PZ254V-12-32P/C22465940在下板顶面male朝上，排母PM254V-12-32-H85/C46595991在上板底面female朝下；器件共享库定义已reviewed，底板已引用排母专用符号及封装，整板装配仍为工程草稿。8.5 mm仅是母座塑高；板距须按实际插合、相向元件、公差与通风/装配余量核定，不能从库定义审核推定实物插合、pin1旋转或两板机械已验证。

上板顶面MOS/电解外露方便布置，但BSC110N15NS5主要经底部焊盘向PCB导热，须安排上板背面与风道，不能以交换上下保证10 Arms。下板MCU置于顶面、朝两板之间，避开上板热源及高dv/dt铜区投影。RESET（SW2）/BOOT（SW3）均在下层控制板顶面、与MCU同面，操作面朝上，靠板边从侧面伸入后向下按；与排针、支柱及线束错开，两键统一采用TS-1101-C-W/C318938，电气功能不变。底板辅助复位SW1仍为TS-1088-AR02016/C720477。插合后操作净空须随板距、支撑及线束共同校核，尚未经机械验证。底板34种确定型号、91个位号的共享库引用已补齐，其余普通被动件MPN及新增选型后的公共库建档仍待完成；还需完成新PCB的主电流、回流、栅极、热、保护响应和供电/插接动态验证。BOM及候选表不是采购/生产发布。

[Rev D应用子板](../history/daughterboard_rev_d_before_minimum_core_2026-11-07.zip)和 [Rev C合板](../history/integrated_rev_c_60x60/)仅作追溯，旧检查与PCB不能覆盖本版。

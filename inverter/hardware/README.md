# Rev E应用功率底板硬件

2026-11-11已完成当前二十页原理图的共享物料同步，**317个位号、14项DNP**，配套 [七页G431最小核](../../controller/hardware/g431_core/README.md)。底板集中放置功率级与应用电路；本工程ERC0错误/0警告。底板迁移前后的969个物理引脚节点、238条网络分区、64针连接、位号、标称值及DNP均保持等效，见 [本轮核对](review/shared_parts_2026-11-11/pin_equivalence.json)；跨板系统检查见 [system_check.json](review/system_check.json)。

- [KiCad工程](inverter.kicad_pro)、[原理图](inverter.kicad_sch)、[当前PDF](review/inverter.pdf)、[实际XML](review/inverter.net.xml)
- [BOM](bom/bom.csv)、[完整型号待定](bom/selection_pending.csv)、[公共库候选](bom/library_intake.csv)
- [应用脚表](../docs/pin_assignment.md)、[64针定义](../../docs/controller_daughterboard.md)、[设计审查](design_review.md)、[PCB状态](PCB_REVIEW.md)

## 当前电路

功率目标为12～60 V母线、DC输入最大10 A、每相连续10 Arms及20 kHz桥PWM。保留2×220 µF/100 V电解、两只2.2 µF/100 V旁路、三路低端分流/INA241、四路电压及外接NTC前端。Q1～Q7为BSC110N15NS5ATMA1/C412739，D1为MBRD20150CT-13/C151357，现均引用共享MyParts符号与MyFootprints专用封装；连续额定、热和实际装配仍待验证。

比较器、健康链、故障锁存和六路PWM硬件门控均在底板本地。ENABLE与CTRL_READY相与形成运行许可；CTRL_READY来自子板的NRST正常与PC7 RUN_ARM相与。拔板、复位、ROM启动或尚未ARM时保持禁止。FAULT_N由Q8开集电极回传，经1 kΩ/钳位后进入PB12；BASE_READY同样经保护进入PC13。制动仍独立软件控制。

SWD、TTL、两路ABZ、两路SPI、可选经典CAN及五个LED全部在底板。八路ADC的360 Ω/BAT54S钳位和100 Ω/1 nF末端RC也全部在底板，子板只有通用GPIO排针。CAN整支路、传感器5 V连接等按BOM保持DNP；外部信号仍为3.3 V单端。现有TTL口PB10/PB11不是ROM串口入口，ROM使用PC10_TX/PC11_RX，与SPI B复用，见脚表。

辅助入口J2为12～24 V，板上产生12 V驱动、5 V及底板3.3 V。U1 TPS26600的EP17/引脚8是EFUSE_RTN，不是GND；R8仍DNP，SW1接EFUSE_RTN。J101/1、3给子板5 V；J101/22、32接收+3V3_CORE_REF，只供回传保护/故障上拉及SWD VTREF检测，不接底板本地+3V3_INV。

J3/J5为6 mm间距2P焊线孔，J4为15 mm间距U/V/W三孔，现用工程定义为2.0 mm成品孔、4.5 mm铜盘。J5接外置制动电阻，不用可开路；母线不设独立预充或专用放电，输出LC另定。J7传感器供电口默认DNP，J8为外部10k NTC。

## 排针和交付边界

子板使用XFCN PZ254V-12-32P / C22465940，底板使用PM254V-12-32-H85 / C46595991；两组2×16、P2.54。公母器件的共享库定义均已reviewed，底板J101/J102已切换到共享排母符号和1.02 mm钻孔专用封装。规划为下层子板顶面male朝上、上层功率板底面female朝下。母座8.5 mm仅为塑高，实际板距须合并插合几何、两板相向器件高度及通风/装配余量核定；装配面的pin1方向、两板焊盘对位和实物插合仍待PCB/样件验证，不可与旧40针板混插。底板九个未用插座脚NC不影响子板52信号pad全部引出。

两板均 **60×60mm**，上功率板、下G431最小核，同轮廓边线对齐；已建立 [六层inverter.kicad_pcb](inverter.kicad_pcb)及配套四层最小核PCB 0.1布局审查稿，四个2.2mm M2孔心距52×52mm。实际布线/DRC及预览见 [PCB交接](../../docs/pcb_review_2026-11-11.md)，板距、器件干涉和装配仍待验证。新PCB独立于 [Rev C归档](../history/integrated_rev_c_60x60/)；上一版应用子板/底板为 [Rev D历史](../history/daughterboard_rev_d_before_minimum_core_2026-11-07.zip)，旧revd_power.pdf也仅属历史。

上板顶面MOS/电解外露只便于布置。BSC110N15NS5主要由底部焊盘向PCB铜导热，须安排上板背面散热及风道，不能靠交换上下保证10 Arms。下板MCU置于顶面、朝两板之间，避开上板热源及高dv/dt铜区投影。RESET（SW2）/BOOT（SW3）均在下层控制板顶面、与MCU同面，操作面朝上，靠板边从侧面伸入后向下按，并与排针、支柱和线束错开；两键统一采用TS-1101-C-W/C318938，电气功能不变，插合后操作净空须随板距、支撑及线束共同校核。

底板34种确切采购型号、91个位号现均引用已reviewed的共享符号及封装，包括三颗半桥驱动、七颗MOS、D1、钳位二极管、保险、电感、各小排针、SW1及两组排母。17颗100 nF/0603落实为国巨CC0603KRX7R9BB104/C14663，50 V、±10%、X7R，覆盖原25 V局部去耦/自举要求。其余207个位号仍待采购选型（152电阻、50电容、5 LED），未猜填型号；J3/J4/J5焊线孔及测试点不计采购件。SW1仍是辅助电源复位按键TS-1088-AR02016，与子板RESET/BOOT两键独立。

共享器件的reviewed仅说明库定义检查通过，不能作为应用或实物验证。模块内部保留直接连线，独立模块间允许标签。D1改为完整双肖特基符号并重接局部直连线，MOS保留1～3为S、4为G、5～8为D的8物理脚对应。当前共地设计不保证炸管后MCU存活；最终PCB和实物的回流、采样、保护动态、插接及热尚未验证。本轮 [备份清单](review/shared_parts_2026-11-11/backup_manifest.json)、[迁移记录](review/shared_parts_2026-11-11/migration.json)、[PDF](review/shared_parts_2026-11-11/inverter.pdf)、[SVG](review/shared_parts_2026-11-11/svg/)用于追溯。

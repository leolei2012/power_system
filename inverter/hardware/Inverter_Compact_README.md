# PCB0.2 紧凑封装与物料来源

2026-11-06，Rev C / 60×60 mm 六层1 oz双面工程稿。物理定义已用于本轮图纸，均不是实物验证结论；当前仍在布线。来源逐项见 [Inverter_Compact_sources.csv](Inverter_Compact_sources.csv)，记录实际文件和SHA-256；完整迁移字段见 [compact_design.json](tools/compact_design.json)。早期候选 [compact_mechanical_parts.json](tools/compact_mechanical_parts.json) / [compact_power_parts.json](tools/compact_power_parts.json)保留选型依据，实际图纸优先。

## 项目库 Inverter_Compact.pretty

| 定义 | 实际位号 | 来源与变更 |
| --- | --- | --- |
| BSC110N15NS5_TDSON8_8PhysicalPins | Q1～Q7 | 从KiCad Infineon PG-TDSON-8几何派生；右侧四引脚按1.27 mm排列、独立编号5/6/7/8，大drain pad重复5；物理1/2/3=S、4=G，全部八个物理脚进入符号/网表。原厂Rev2.6提供外形，不等于完整厂家推荐land已验证 |
| PinHeader_HCTL_PZ127_1x02/03/05/06_P1.27mm_D0.70mm | J7～J15 | 从相应KiCad 1.27 mm单排针派生，按HCTL PZ127-1-N-Z图把成品孔改0.70 mm，原针序不变；0.4方针，额定1 A/触点，传感器0.5 A目标仍需预算 |
| WireSolder_2P_P6.00mm_D2.00mm | J3、J5 | 本工程焊线孔定义：两针间距6 mm、成品孔2 mm、铜盘4.5 mm，第一针矩形；不是需购买的端子 |
| WireSolder_3P_P15.00mm_D2.00mm | J4 | 本工程U/V/W三孔定义，**实际间距15 mm**；其余孔盘尺寸同上，不能套用早期6 mm三孔候选 |

焊线以AWG14约2.08 mm²铜线为候选，实际浸锡束径、孔铜/焊锡、绝缘、应力释放、温升及两面焊接空间需确认。模型不替代这些机械/电气验证。

## 直接复用的标准几何

| 器件 | 本地KiCad封装 | 已核对与未闭环 |
| --- | --- | --- |
| D1 MBRD20150CT-13 / C151357 | TO-252-3_TabPin2 | 原厂DS37086 **Rev4-2 / September2026**图确认1/3为A、2/tab为K；同订货码有不同机械变体，实际到货外形、land及热待确认 |
| F1 0476015.MRSN / C3165851；F2 0451002.MRL / C99547 | Fuse_Littelfuse-NANO2-451_453 | 实际land与476建议几何匹配，不能由封装名推断F1电气额定。F1为15 A/125 VDC/300 A分断；MRSN与高分断MRS后缀有区别，I²t与热降额另审 |
| L1/L2 MWSA0603S-4R7MT / C408447 | L_Sunlord_MWSA0603S | 4.7 µH，DCRmax33 mΩ；land2.35×3.5 mm、间隙3.7 mm匹配；额定列的定义、30 V最大差分电压及辅助电源峰值/温升待应用核查 |
| SW1/SW2 TS-1088-AR02016 / C720477 | SW_SPST_TS-1088-xR020 | 当前单页原厂图的两pad1.05×2.0、中心±2.225 mm与本地一致；旧两页资料land不同。R8已DNP，SHDN使用内部偏置，不承载12～24 V功率 |
| J2 B2B-PH-K-S(LF)(SN) / C131337 | JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical | 2 mm/2 A（AWG24条件）；0.75 mm成品孔在原厂0.70+0.1/-0范围。母座、压接端子和线束另列装配物料 |

本轮3D链接已有相对路径维护，但当前仍缺9个元件实例的模型：Q1～Q7引用的官方TDSON STEP与F1/F2引用的Nano2 STEP未安装。三维预览不完整，不能据此认为这些实体或装配空间已验证；焊线/线束也须另做机械检查。

## 公共库与待办

[公共物料待建清单](../../docs/inverter_library_todo.csv)按当前XML和相邻公共库台账重新生成：11种完整型号、24个位号记录。所有条目已有工程或官方几何封装，没有因此留下PCB空封装。采购页包括LCSC国际站，最终国内页/库存与完整后缀仍需复核，特别是C408447直接页面自动抓取未成功。

[待选型号清单](../../docs/inverter_selection_todo.csv)只列未确定完整MPN的实际采购件；测试点和工程焊线孔不当作缺型号物料。普通小阻容统一国巨。既有公共reviewed物料不表示当前项目使用的草稿符号或不同标准land已经同步，见 [项目符号说明](InverterLocal_README.md)。本轮没有修改公共库。

## 许可与追溯

KiCad官方符号/封装源于 [KiCad libraries](https://gitlab.com/kicad/libraries)，采用 [CC BY-SA 4.0及KiCad设计使用例外](https://www.kicad.org/libraries/license/)；项目派生保留来源，不能把几何修改称为厂家认证。原厂PDF保留各自版权，不因本工程引用或保存而重新授权。工程自绘焊孔独立标明为项目机械定义；文件哈希用于锁定本次检查版本，不是实物验证标记。

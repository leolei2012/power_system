# 工程符号与公共库状态

2026-11-06，当前Rev C / PCB0.2为60×60 mm六层1 oz双面集成变频板，正在布线。`InverterLocal.kicad_sym`保留工程派生符号；项目字段`project_draft`与公共物料的`reviewed`分别记录，不能互相替代。本轮不修改相邻`kicad_library`。

| 当前使用的工程符号 | 引脚/来源 | 当前公共物料与待办 |
| --- | --- | --- |
| STM32G431RBT6 | KiCad STM32G431RBTx继承图形，ST DS12589 Rev6，LQFP64；C431633 | 公共MyParts已有reviewed，当前项目仍为InverterLocal和官方标准LQFP land；是否改挂公共符号/专用land需另审，不自动同步 |
| BSC110N15NS5 | Infineon Rev2.6；物理1/2/3=S、4=G、5/6/7/8=D；大drain焊盘重复5；C412739，完整订货码BSC110N15NS5ATMA1 | 新增项目八脚定义及紧凑派生封装，公共完整物料待建；与旧IRFS三脚型号/焊盘不兼容 |
| MBRD20150CT_13 | Diodes DS37086 Rev4-2（September2026）第1页原厂图确认1/3=A、2/tab=K；C151357 | 公共待建；DPAK实际到货变体/land及热待确认；不能沿用旧STPS40150候选采购信息 |
| MMBT3904LT1G | onsemi MMBT3904L，1B/2E/3C；C81464 | 公共已有reviewed，项目仍使用InverterLocal及官方SOT-23；公共专用推荐land尚未自动替换 |

IRFS4227TRLPBF和STPS40150CG等旧符号若仍保存在库文件中，只用于历史追溯，当前XML不再装配这些功率器件。IRFS公共物料现已reviewed也不能套给本轮BSC器件。

另外，RS1～RS3的HoJLR2512-3W-5mR-1%和D2 SMCJ60CA已存在公共reviewed物料，但项目仍用通用Device符号与官方R2512/D_SMC几何。分流焊盘尤其影响Kelvin/温升，不能把“公共物料已建”当成“当前工程已采用该专用land”。D2保持DNP，TVS应用配合另审。普通芯片的库定义reviewed同样不代表板级电气或热通过。

紧凑封装、标准几何复用、原厂文档/许可及哈希见 [Inverter_Compact_README.md](Inverter_Compact_README.md)与[来源CSV](Inverter_Compact_sources.csv)。[当前待建完整型号](../../docs/inverter_library_todo.csv)与[待选型号](../../docs/inverter_selection_todo.csv)分开维护；任何符号/封装同步须在原生工程中审查后执行，不由文档修改带入。

# PR #13 第三轮执行结果

分支 `hw/controller-sch-issue2`，KiCad 10.0.7；未切分支、未 commit/push，原索引未写入。

| 项 | 结果 |
| --- | --- |
| A | U203 TPS2553，R227=49.9k；IN/EN同接+5V_CORE_IN，OUT→D201；/FAULT NC；C211/C212输入/输出去耦；5V_OUT对外仅J201/4，均在限流后。 |
| B | pinmap先改；删JP203；J203/1、J204/1直接+3V3_MCU；PCB只加英文F.SilkS，(130,158)mm，未移动器件/走线；旧PCB无J203/J204/JP203。 |
| C / N1 | SW2、D202/D203、D204/D205已选料并补封装；核对物理针号；LED 1=A、2=K、中央3外部NC；本地符号/LED封装待入共享库。 |
| D / N2 | D201/D103统一共享库reviewed CFP3回流焊封装。 |
| E / N3 | 用临时索引执行git mv到history；内容不变，移动前后网表及ERC一致。原.git只读，提交时请git add -A纳入移动。 |
| F / N4 | R225/R226保留1k并补C21190；典型LED电流1.4–1.5mA。 |
| G / N5 | 3.3V逐负载规格/预算表完成：271.024mA合计，工程静态预算≤275mA，不含外接编码器≤50mA；合计≤325mA，小于TLV767的1A能力。条件和待验项见下。 |
| H / N6 | R228/R229=680Ω/0603，默认DNP。单120Ω约0.268V/2.23mA；双终端实算0.139V，低于200mV；原任务0.134V算术有误，已说明。 |
| I | 变更说明、BOM变化/补库表已追加；只更新review/bom_issue2.csv；原生导出ERC、XML、BOM、PDF、验证JSON均完成。 |

新增位号：**U203、R227、C211、C212、R228、R229**；另有非BOM电源标志#FLG203。删除JP203；D202/D203以及新增偏置DNP保留。

ERC原文摘要：`ERC messages: 0  Errors 0  Warnings 0`。未改ERC配置，保留基线已有全局忽略类别。

脚位核对：pinmap §3 MCU **64/64**；§4.1/4.2 J101/J102 **64/64**，连同物理端口、13个独立NC及全部既有引脚连接重新核对。验证总计 **2092 项，失败 0 项**；实际结论：**通过**。

活动10页实例封装扫描：**0402/01005/0201=0；空Footprint=0**。PCB移除唯一新增gr_text后与原板全部结构一致；PCB差异11行新增、0行删除，全部属于这一条文字。

修改文件（含新增/移入文件，取自git status）：

```text
 M controller/hardware/g431_core/CoreProtection.kicad_sym
 M controller/hardware/g431_core/comms.kicad_sch
 M controller/hardware/g431_core/controller.kicad_pcb
 M controller/hardware/g431_core/controller.kicad_sch
 M controller/hardware/g431_core/core_supply.kicad_sch
 D controller/hardware/g431_core/debug_comms.kicad_sch
 M controller/hardware/g431_core/encoders.kicad_sch
 M controller/hardware/g431_core/fp-lib-table
 M controller/hardware/g431_core/mcu_control.kicad_sch
 M controller/hardware/g431_core/review/bom_issue2.csv
 M controller/hardware/g431_core/review/controller.net.xml
 M controller/hardware/g431_core/review/controller.pdf
 M controller/hardware/g431_core/review/erc_issue2.rpt
 M controller/hardware/g431_core/review/issue2_changes.md
 M controller/hardware/g431_core/review/validation_issue2.json
 D controller/hardware/g431_core/sensors.kicad_sch
 M controller/hardware/g431_core/ui_debug.kicad_sch
 M docs/pinmap.md
?? controller/hardware/g431_core/ControllerLocal.pretty/LED_Ekinglux_1204_SideView_3.2x1.0mm.kicad_mod
?? controller/hardware/g431_core/history/debug_comms.kicad_sch
?? controller/hardware/g431_core/history/sensors.kicad_sch
?? controller/hardware/g431_core/review/pr13_third_round_result.md
?? controller/hardware/g431_core/review/validate_pr13.py
```

未完成/需交接：C212按用户要求与C301一同待#5选确切料号/DC bias；中央LED焊盘的内部电气属性未在原厂图明确，已独立编号并外部NC；本地符号/封装及选定电阻料号待#5入共享库。275mA是列明条件和裕量的工程设计/验收上限，ST数字外设表无保证最大列，不能宣称全工况整板保证最大值；#4/#7仍需核对真实外部负载、LDO输入压差、热与瞬态。双120Ω终端需要系统重新核定偏置方案；本轮按指定680Ω默认DNP保留。

详细依据及计算见 [issue2_changes.md](issue2_changes.md) 第三轮；逐项检查见 [validation_issue2.json](validation_issue2.json)。

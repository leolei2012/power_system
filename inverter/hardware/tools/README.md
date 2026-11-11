# 原理图、紧凑PCB检查与导出

2026-11-06，当前Rev C / PCB0.2为60×60 mm、六层1 oz双面集成变频板，18页原理图；正在布线。**原生KiCad文件为准**，创建/迁移/自动摆放脚本是本次操作记录，不能覆盖后续人工修改。当前板文件已切换紧凑版本；最终报告和预览仍须在布线结束后同步。

## 原理图

- `export_review_metadata.py`：从实际XML导出两份一致的BOM与元数据，不替代选型。
- `verify_inverter.py`：独立读实际XML，检查G431/接口/电源/采样和保护逻辑。
- `verify_readability_equivalence.py`：比较物理引脚和连通分组，并核对参数、DNP、封装；本轮允许的MOS物理脚展开、R8 DNP等必须显式记录，不能掩盖其它变化。
- `cleanup_instance_fp_filters.py`：只处理与嵌入库默认值一致的冗余实例字段，属于历史同步兼容记录；不删除lib_symbols筛选定义。

在`inverter/hardware`中执行并核对输出版本：

```powershell
& 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe' sch export netlist inverter.kicad_sch --format kicadxml -o review/inverter.net.xml
python -X utf8 tools/export_review_metadata.py
python -X utf8 tools/verify_inverter.py
python -X utf8 tools/verify_compact_equivalence.py
& 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe' sch erc inverter.kicad_sch -o review/erc.rpt --exit-code-violations
& 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe' sch export pdf inverter.kicad_sch -o review/inverter.pdf
```

当前图面继续按功能模块：模块内部直接连线，模块之间可用标签；连续功率/栅极/自举/反馈/采样回路沿线可读。`redraw_common.py`与`redraw_*.py`对应之前的固定快照，不应直接重跑覆盖本轮。

## PCB0.2创建与布线记录

| 文件 | 范围 |
| --- | --- |
| `compact_design.json` | 本轮确切型号、封装、MOS脚序展开及R8 DNP字段迁移；不是发布批准 |
| `compact_power_parts.json` / `compact_mechanical_parts.json` | 原厂/立创选型证据与应用限制；候选和实际有差异时以实际XML及迁移记录为准，例如J4实际15 mm间距 |
| `compact_revision.py` | 工程符号/封装和字段迁移记录；会改native，不能直接覆盖后续编辑 |
| `compact_control_placement.json` / `compact_power_placement.json` / `compact_aux_placement.json` | 分区摆放输入；创建后有移动时以实际PCB读回为准 |
| `compact_board.py` | 从实际XML创建六层工作板，工作目录`review/compact_work`；不是只对旧200 mm走线缩放 |
| `compact_power_copper.py` | 本轮固定主路径、参考地、局部功率铜及Kelvin出点的创建记录 |
| `compact_route.py` / `compact_stitch_signals.py` | 本地DSN/SES交换与本轮补线记录；导入后必须重新填铜、查连通及电气间距 |
| `compact_sync_metadata.py` / `compact_model_paths.py` | 项目字段同步和PCB模型路径维护；不能补出未安装的STEP或代替装配检查 |
| `compact_footprint_candidates.json` | 当前实际XML的19项机械封装映射，供本轮独立检查；旧`pcb_footprint_candidates.json`只作PCB0.1历史输入 |
| `verify_pcb.py` | 独立读实际PCB和XML，检查313位号、含重复编号的实体焊盘、DNP、几何、铜层、主参考层及外部DRC；不导入创建器 |

In1.Cu和In4.Cu保留GND参考，普通信号使用F.Cu/In2.Cu/In3.Cu/B.Cu；主功率/浮动SOURCE/Kelvin按本轮实际设计约束。输入库、两面坐标、DNP和3D模型来源见 [紧凑封装说明](../Inverter_Compact_README.md)。

## 最终板检查命令

以下用于最终原生文件整合之后。`--save-board`会保存填铜结果，应针对要审核的板或明确的私有副本执行。当前布线尚未完成，命令记录不代表已经取得通过结果。

```powershell
& 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe' pcb drc inverter.kicad_pcb --format json --schematic-parity --all-track-errors --refill-zones --save-board -o review/pcb_drc.json
& 'C:/Program Files/KiCad/10.0/bin/python.exe' tools/verify_pcb.py --board inverter.kicad_pcb --netlist review/inverter.net.xml --candidates tools/compact_footprint_candidates.json --expected-copper-layers 6 --expected-width-mm 60 --expected-height-mm 60 --strict-layout
& 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe' pcb render inverter.kicad_pcb --side top --width 1600 --height 1600 --background opaque -o review/pcb_top.png
```

`verify_pcb.py`默认值已指向当前紧凑版；这里显式参数用于标明范围。`pcbnew`内部未连计数与CLI列出的airwire数量可能采用不同表示/截断，不混为同一统计；布线完成必须结合真实铜连通、完整DRC和一致性检查。报告须匹配板文件SHA和时间，不能只看旧PASS文字。最终验证待填栏见 [PCB_REVIEW.md](../PCB_REVIEW.md)。

## 历史PCB0.1和分板脚本

旧200×140 mm四层PCB0.1已存 [改板前归档](../../history/pcb_0_1_200x140_before_60mm_2026-11-06.zip)。旧`build_pcb.py`、`finish_pcb.py`、`route_pcb.py`、`repair_pcb_routing.py`、`apply_route_patches.py`与旧坐标/补丁哈希只对应当时版本，不能向PCB0.2重放。审核旧归档须显式使用旧候选映射、四层、200×140 mm参数，不得覆盖当前报告。

更早`build_inverter.py`、`migrate_integrated_rev_b.py`及`redraw_*.py`属于Rev A/Rev B创建过程；旧分板资料见归档。局部文件/模型哈希记录来源，不代表电气额定、热、动态保护或实物装配通过。

本地布线工具在根目录`.tools/`，未纳入版本控制；只进行本地文件交换，未上传外部布线服务。最终Gerber/钻孔/装配发布仍待后续决定。

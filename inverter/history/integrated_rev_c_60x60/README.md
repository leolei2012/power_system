# 历史合板 Rev C

此目录保存改为可插拔单片机子板之前的 60×60 mm 集成方案。它有 18 页原理图，PCB 仍有 215 处未连接，不能作为当前分板版的生产文件。

`inverter.kicad_pcb` 已从原目录移至此处，文件内容未变，SHA256 为 `4d4f0c2ae1d5177ebf351e92cd70ae8483fde624233a5b98dc958461cede13fb`。配套旧原理图、工程和局部库从不可变 [Rev C 完整归档](../integrated_60x60_rev_c_before_mcu_split_2026-11-06.zip) 提取。这里的库表仅调整了共享库相对路径；PCB 内嵌的共享 3D 模型路径仍保留原值，需要在原目录恢复归档才能完整预览。

当前分板方案见 [功率底板](../../hardware/inverter.kicad_sch) 和 [G431 子板](../../../controller/hardware/g431_core/controller.kicad_sch)。两个新 PCB 尚未设计。

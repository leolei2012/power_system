# 集中控制固件历史占位

2026-11-05：取消一颗 LKS 同时控制两路逆变及 PFC。变频板和电源板分别有 MCU、分别构建固件；电源板的 PFC＋LLC 控制正在评估。下文目录和预算仅作旧方案参考，当前没有可编译固件。最新依据见 [合板方案](../../docs/integrated_board.md)。


本目录是单颗 LKS32MC451VCT8 的固件工程位置，计划使用 ThreadX。目前只有设计文档，尚无启动代码、厂家 SDK、ThreadX 源码依赖或可编译工程。

软件职责与预算见[软件资源规划](../docs/software_resources.md)，物理映射见[引脚规划](../docs/pin_assignment.md)。固件最终覆盖两路 inverter 和一路预留 PFC，LLC 暂不实现。

拟按 bsp（时钟与外设）、control（逆变/PFC 快环算法）、app（状态机与线程）、protocol（UART/CAN）、services（参数/故障/遥测）、config（板型与 ThreadX 配置）划分。此处为后续目录设计，不表示相应模块已经存在。

inverter 下已有的 firmware 目录仍是历史空占位；同一颗 MCU 只构建本目录中的一个应用，后续实现时再归并算法代码，避免两个独立固件工程重复拥有同一 PWM/ADC。

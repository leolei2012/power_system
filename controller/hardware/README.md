# Controller KiCad 原理图

2026-11-05 架构变更：用户确定控制、驱动与逆变功率级合板，MCU 改为 **STM32G431**。当前依据见 [合板方案](../../docs/integrated_board.md)。本文下方 LKS、独立 controller、24 脚板间接口及旧引脚/软件预算属于上一版记录；旧 KiCad/BOM/检查结果不代表新合板版本已完成。已确定每板一颗 MCU，分变频板与电源板，取消单 MCU 同时控制两路逆变和 PFC。LLC 在电源板恢复讨论，具体配置、接口和 MCU 完整后缀待评估。


2026-11-01，Rev A 可审查草稿。用户要求使用 KiCad 绘制 controller，已建立原生 KiCad 10 工程；尚未进入 PCB，也不作为生产发布版本。

打开 [controller.kicad_pro](controller.kicad_pro)，再打开根原理图 [controller.kicad_sch](controller.kicad_sch)。总览页中的功能框可进入子页。

| 页码 | 文件 | 内容 |
| --- | --- | --- |
| 1 | controller.kicad_sch | 总览、页面导航及使用边界 |
| 2 | power.kicad_sch | 独立 5 V 输入、TLV76733DRVR、TPS3808G33DBVR、MCU 电源单元和逐脚去耦 |
| 3 | mcu.kicad_sch | LKS32MC451VCT8 三组 GPIO 单元、12 MHz 晶体、五个保留测试点 |
| 4 | inverter_1.kicad_sch | J2 变频信号接口、八路 ADC、PWM/ENABLE/FAULT、J3 制动控制 |
| 5 | inverter_2.kicad_sch | J4 第二路变频接口、J5 制动控制 |
| 6 | pfc.kicad_sch | J6 专用 PFC 24 脚口，六路命令、九路 ADC、预充控制预留 |
| 7 | sensors.kicad_sch | J7/J8 两路 A/B/Z，暂按 3.3 V 单端输入绘制 |
| 8 | spi.kicad_sch | J9/J10 两路独立 SPI，CS 上拉及默认不装的可选供电跳接 |
| 9 | debug_comms.kicad_sch | J11 SWD、J12 TTL、J13 CAN 可选模块、五个 LED |

## 审查文件

- [九页 PDF](review/controller.pdf)及 [PNG 缩略总览](review/preview/contact-sheet.png)。
- [实际位号 BOM](review/bom.csv)：196 个物理器件/测试点记录，15 项 DNP；普通小阻容均标为 YAGEO，未确认完整型号的项目保留 TBD。
- [ERC 报告](review/erc.rpt)：KiCad 10.0.7 默认规则下 0 错误、0 警告；未为本工程新增屏蔽或排除项。报告末尾列出的四类忽略检查为 KiCad 默认设置。
- [网表连接核对](review/connectivity_check.txt) / [JSON](review/connectivity_check.json)：对照独立 100 脚规划与接口契约检查，另核对 573 项实际器件引脚网络断言。
- [设计依据、计算与待定事项](design_review.md)。

## 库依赖

工程专用 `sym-lib-table` / `fp-lib-table` 引用 `../../../kicad_library`，即当前的 `D:/workspace/kicad_library`，未改公共库。U1/U2/U3/U4 分别使用库内 LKS32MC451VCT8、TLV76733DRVR、TPS3808G33DBVR、SN65HVD232DR 的真实符号及封装引用；其余采用安装的 KiCad 10 官方通用符号。源文件 SHA256 记录在 [library_sources.json](review/library_sources.json)。

符号已缓存进原理图，查看图纸不依赖重新下载；继续更新库或转 PCB 时应保留外部库路径。连接器和 SW1 的封装仍为空，不能直接发布 PCB；共享库封装中的 3D 模型项目相对路径也需在 PCB 阶段适配，不影响本次原理图连线。

## 使用边界

只接一路稳压 5 V 到 J1；不能接 12~24 V，也不能将两个 inverter 的 5 V 输出直接并联。三路 24 脚口不供电。当前为同参考地、非隔离实验草稿，未来串联整流/PFC 的不同功率参考域不能直接用这些地脚短接。

ABZ 暂按 3.3 V 推挽单端绘制，不表示已经支持 5 V TTL、开集电极或差分编码器。四路传感器可选 3.3 V 供电跳接及其旁路默认 DNP；CAN 的收发器、接口、两只 0 Ω 链接、TX 上拉、去耦和 120 Ω 端接默认 DNP，启用时按模块成套装配，端接只在物理总线端点选装。

`tools/build_controller.py` 是本轮初稿的创建辅助脚本，**后续人工在 KiCad 修改的文件为准，不要直接重跑覆盖**。`tools/verify_controller.py` 只读取导出的网表与引脚规划进行核对，适合后续修改后复查。软件实现、PFC 同步和三套 ADC 采样调度均未由本次绘图验证。

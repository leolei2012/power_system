# ATK-PD6010B 设计参考

更新：2026-10-31。参考对象为正点原子 **ATK-PD6010B 三相直流无刷驱动板**。用户已纠正最初提到的 PD6010D，有刷 D 型不作为当前参考对象。

2026-11-01 用户明确以该板作为本项目 inverter 的主要硬件设计参考，按其功能块与回路展开；母线电解首版采用相同的 2×220 µF/100 V 配置。与本项目器件、供电、保护和接口的适配关系见 [绘图任务书](../../docs/schematic_agent_task.md#指定参考板)。

## 官方来源

- [正点原子电机驱动板资料下载中心](https://www.openedv.com/docs/boards/stm32dj/ATK-PD6010B.html)。
- [官方硬件资料与讨论帖](https://www.openedv.com/thread-336839-1-1.html)。
- [驱动板与电机硬件资料包](https://pan.baidu.com/s/1AZWRsQMWcjxMkKIYbsbq2w)，公开提取码 **eyx4**。
- [官方 DMF407 配套资料索引](https://github.com/alientek-openedv/Products/blob/d917adac269f72ea1fb008baaed4d25319fcdf0c/zdyz_docs/boards/stm32dj/ATK-DMF407.rst)：A 盘链接 `https://pan.baidu.com/s/1xPjILZ-hBV-0dyiDoW4Tyg`，提取码 **k9kb**，作为配套资料入口。
- [官方公开教程第 21 章](https://blog.51cto.com/u_15046463/5632029)：三相驱动及接口介绍；当前未取得本地完整文章。

本地 RST 索引固定于官方 Products 仓库提交 `d917adac269f72ea1fb008baaed4d25319fcdf0c`。下载中心显示的文档版本不能当作板卡硬件版本。以下 GitHub 原理图标题栏已核对为 **V1.0，2021/12/24**。

## GitHub 第三方副本

- 主来源：[leolei2012/project_template 的原理图目录](https://github.com/leolei2012/project_template/tree/aab1d6a927f95bbe223f560d3102474edc5b447f/docs/%E5%8E%9F%E7%90%86%E5%9B%BE)，固定提交 `aab1d6a927f95bbe223f560d3102474edc5b447f`。
- 交叉核对：[3142430257/chendian 中的 PD6010B 原理图](https://github.com/3142430257/chendian/blob/14cbbb447ed90c19004038ed2634234e867023ce/hardware/controller_board/ATK-PD6010B_V1.0.pdf)，固定提交 `14cbbb447ed90c19004038ed2634234e867023ce`。

两处 PD6010B PDF 下载后逐字节一致，SHA-256 为 `4e4e98ee517178fa5592709966976477ed5a147b27798fc8b96939161e0cbea4`；同时核对主文件的 Git blob SHA-1。该检查确认仓库副本一致，不代表已与官方发布包校验。

## 已下载文件

| 文件 | 内容 |
| --- | --- |
| [ATK-PD6010B_V1.0.pdf](original/github/ATK-PD6010B_V1.0.pdf) | **主要参考：驱动板原理图，2 页，V1.0，2021/12/24；两页均已渲染查看** |
| [ATK-PD6010B_V1.0_second_mirror.pdf](original/github/ATK-PD6010B_V1.0_second_mirror.pdf) | 第二仓库的相同副本，用于交叉核对 |
| [DMG474_V1.0.pdf](original/github/DMG474_V1.0.pdf) | 配套 DMG474 控制板原理图，6 页；不是 PD6010B 驱动板图纸 |
| [DMG474_hardware_manual_V1.0.pdf](original/github/DMG474_hardware_manual_V1.0.pdf) | 配套 DMG474 控制板硬件参考手册 V1.0，38 页；不是 PD6010B 独立用户手册 |
| [project_template_docs_README.md](original/github/project_template_docs_README.md) | 上游资料目录说明 |
| [official_download_page.html](original/official_download_page.html) | 官方下载入口网页快照 |
| [official_download_index.rst](original/official_download_index.rst) | 官方驱动板资料索引原文，含网盘入口及提取码 |
| [official_DMF407_index.rst](original/official_DMF407_index.rst) | 配套 DMF407 电机开发板资料索引原文 |
| [official_board_front.png](original/official_board_front.png) | 官方 PD6010B 正面实物图 |
| [official_hardware_forum.html](original/official_hardware_forum.html) | 官方硬件资料讨论帖网页快照 |

[downloads.json](downloads.json)记录官方入口资料；[github_downloads.json](github_downloads.json)记录 GitHub 副本、固定提交、校验值及失败尝试。原文件不作修改。阅读结论见 [原理图对照笔记](design_notes.md)，两页预览见 [第 1 页](preview/schematic-1.png)和 [第 2 页](preview/schematic-2.png)。

## 尚未下载的核心资料

- ATK-PD6010B 用户手册 PDF。
- 官方发布包及其版本记录：已有 GitHub 转存的 V1.0 原理图 PDF，但尚未与官方发布包比对。
- PCB / 源工程：需先查看官方包内目录，确认是否提供。
- 与具体硬件版本对应的 BOM、器件资料和配套示例：按包内实际内容补齐。

官方网盘包未取得。GitHub 已取得上述 PDF；独立 PD6010B 用户手册、可编辑 SchDoc/PCB 源工程及 BOM 尚未找到可下载且核实的副本。检索中发现的原理图 ZIP 下载失败，不列为已取得资料。

## 阅读和对照重点

| 重点 | 应核对的内容 |
| --- | --- |
| 三相功率桥和驱动 | 驱动电源、自举、PWM 极性、上下管互锁、MOS 型号与耐压、栅极回路 |
| 电流与电压采样 | 分流位置、信号增益/偏置、采样窗口、输入保护及参考地 |
| 故障与制动 | 过流检测和关断路径、复位方式、制动接口及能量处理；不能直接照搬门限 |
| 辅助供电 | 是否从功率母线取电、各电源轨、掉电默认态；与本项目独立辅助 12～24 V 的结构逐项比较 |
| 板间接口 | 六路 PWM、故障/使能、模拟反馈与连接器脚序；同为 24 脚不代表电气兼容 |
| 隔离边界 | 光耦两侧的供电、地和其他信号是否跨接；有光耦不自动等于完整系统隔离 |

公开教程可用于定位阅读内容，正式结论以取得的对应版本手册、原理图和原厂芯片资料为依据。参考板的 10 A 定义需在手册中核实，不能用它证明本工程每相连续 10 A_rms、瞬时 ±20 A 保护或最高 600 W 输入的全部工况成立。

本项目既定指标、器件与接口仍见 [规格](../../inverter/docs/spec.md)、[选型](../../inverter/docs/component_selection.md)和 [原理图任务书](../../docs/schematic_agent_task.md)。

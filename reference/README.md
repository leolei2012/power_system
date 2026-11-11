# 设计参考资料

工程参考资料的统一入口。按产品或项目建立子目录，原始下载文件放在各自的 `original/` 中，来源、版本和下载状态写入目录 README 与清单；对照分析放在原始文件外，保留原文件内容及厂家信息。

| 参考 | 用途 | 当前资料 |
| --- | --- | --- |
| [ATK-PD6010B](ATK-PD6010B/README.md) | 正点原子三相无刷电机驱动板，重点对照驱动、采样、保护和板间接口 | 已取得 GitHub 转存的 V1.0 两页原理图及 DMG474 配套控制板资料，已写对照笔记；PD6010B 独立手册和源工程待补 |
| [已有开源对照笔记](../inverter/reference/README.md) | OWNVERTER、Nexperia、ODrive、VESC 等项目索引 | 原有对照笔记与上游链接 |
| [STM32G431双电机资料](ST_G431_dual_motor/sources.json) | 核验一颗G431运行双电机的先例与证据边界 | 已保存ST多轴伺服演示PDF和UM2896；另记录SimpleFOC作者运行自述和Gooser5/5.8项目 |
| [STM32G431规格书与历史100脚评估](ST_G431_dual_pwm/sources.json) | G431引脚、ADC及定时器复用核验 | 保存ST DS12589 Rev6原件；曾用于双PWM/100脚方案，现已收敛为单功率口/RBT6；不验证原理图/PCB实现 |

## G431双电机证据（2026-11-11）

- [ST多轴伺服演示原件](ST_G431_dual_motor/original/ST_Multiaxis_servo_drives.pdf)：第7页直接给出G431双路16kHz FOC、CPU负载23%的厂商数据。该页没有提供完整算法、采样与RTOS测试配置，不能将23%作为本项目的性能测量。[官网来源](https://www.st.com/content/dam/is22/plenary/plenary-mc-cc-seven-zeng-en.pdf)
- [UM2896 Rev1原件](ST_G431_dual_motor/original/UM2896_EVSPIN32G4_DUAL_Rev1.pdf)：STSPIN32G4内置一颗G431，配STDRIVE101组成双三相功率级；其单分流电流检测与本项目三低端分流方案不同。[官方板卡](https://www.st.com/en/evaluation-tools/evspin32g4-dual.html)
- [SimpleFOC用户Pat的原帖](https://community.simplefoc.com/t/how-to-use-stm32-flash-settings-storage-with-2-motors/5676)：2024-10-18明确自述使用同款G431控制两台电机、运行正常，2024-10-19反馈双电机参数存储方案有效。帖子没有给出双电流环频率、完整电流闭环配置或视频，属于作者运行自述。
- [Gooser5.8硬件项目](https://oshwlab.com/dekutree64/gooser5)与 [作者实测记录](https://community.simplefoc.com/t/gooser-a-4-in-1-lepton-derivative/5325/96)：项目定义两电机共享一颗G431，分别用TIM1与TIM8；作者已发布Gooser5功能验证及实物、电流测试记录，后续 [5.8更新](https://community.simplefoc.com/t/gooser-a-4-in-1-lepton-derivative/5325/103)包含双编码器实用经历。不得将其单电机循环频率或更早四电机版本描述当成双路20kHz电流FOC的实测证明。

已保存的inverter工程仍是一路电机。controller曾评估双功率口和100脚VBT6，用户现已要求收敛为单功率口，当前推荐沿用64脚RBT6；上述双电机资料保留供历史对照，不是当前双电机需求，也不代表ThreadX、三分流采样或新端子引脚已经实现。下载哈希、版本及网上证据分级见上述清单。PDF保持上游原件，页面预览位于`outputs/g431_dual_motor_reference_2026-11-11/`。

本工程第一版指标以 [inverter 规格](../inverter/docs/spec.md)为准：母线 12～60 V、直流输入最大 10 A、每相连续 10 A_rms、三相桥 PWM 20 kHz、相电流硬件过流名义门限瞬时 ±20 A。参考板的同名电流/功率指标不能自动替代本工程定义。

新增资料记录来源 URL、取得日期、版本（能确认时）、文件名、字节数与 SHA-256。文件存在和内容有效后再标已下载；网页索引不等同于完整手册或原理图。上游许可与署名随原文件保留，直接复用图纸前核对对应许可。

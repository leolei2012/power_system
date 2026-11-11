# 控制板 MCU 选型记录

2026-11-05：本文为旧分板/集中控制方案的参考记录。当前按 [变频板与电源板各一颗 MCU](../../docs/integrated_board.md)推进，MCU 改为 STM32G431 方向，电源板 PFC＋LLC 恢复评估；本文旧引脚、资源数量和检查不能覆盖新版。


## 已选择 LKS32MC451VCT8（2026-10-30）

凌鸥 LKS32MC45x 系列官方定位包含双电机加 PFC。按用户决定，主控切换为 100 脚 LKS32MC451VCT8。最新范围为两路变频加一路 PFC 专用口同时运行，LLC 已暂停。2026-10-31 已完成 [引脚草案 A](pin_assignment.md)的封装/复用静态核对；时序及实时性能待验证，详见 [单芯片评估](single_mcu_evaluation.md)。下列 LLC 相关检查为先前扩大范围时的记录，当前不要求实现。

官方 v1.71 数据手册给出的系列资源包括 192 MHz Cortex-M4F、256 KB Flash、40 KB SRAM、两组 MCPWM（共 16 路输出）、四组编码器接口、三路 14 位 ADC，以及 UART、CAN 和最多 84 个 GPIO。具体封装可引出资源仍需逐脚确认，不能直接把系列最大值视作无冲突组合。

重点核对：

- 两路 24 脚通用功率接口、两路 A/B/Z 编码器、两路独立 SPI、两路制动、独立 LLC、串口、CAN、SWD 的复用和 ADC 通道覆盖。
- 双路逆变已需 12 路 PWM，LLC 主桥与同步整流可能再需 2~6 路或更多；总输出数之外，还必须确认独立变频时基、死区、同步和硬件故障封锁能力。
- 目前查到的 MCPWM 时钟为 192 MHz，尚未确认有与 G474 HRTIM 相当的高分辨率功能，不能宣称 LLC 控制能力等同。
- 程序与采样缓存的 RAM 预算、工具链和调试器支持、芯片勘误，均需在定型前核对。
- 采购与报价统一以立创商城国内站为准。立创编号 C17557026，封装 LQFP100；国内价格阶梯和库存待确认，不采用其他商城或国际站价格替代。

来源（2026-10-30 查询）：

- [凌鸥 LKS45 官方系列页](https://www.lksmcu.com/index.php/LKS45Series/)
- [官方数据手册 v1.71](https://sjk.lksmcu.com/static/upload/file/20230113/LKS32MC45x_Datasheet_v1.71.pdf)
- [官方资料与勘误下载入口](https://www.lksmcu.com/index.php/Datasheet_3/)
- [立创国内商品页](https://item.szlcsc.com/18686247.html)






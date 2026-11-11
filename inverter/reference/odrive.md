# ODrive 与 ODriveX

两套都是双轴无刷电机驱动，固件完整，母线电压低于本板。

## ODrive v3

- 硬件：https://github.com/odriverobotics/ODriveHardware
- 固件：https://github.com/odriverobotics/ODriveFirmware
- 工具：Altium
- 许可：以仓库 LICENSE 为准

一块板控两个电机。MCU 是 STM32F405，每轴一颗 DRV8301，功率管是 60 V 的 NTMFS5C628NLT。板子按电容耐压分成 24 V 和 48 V 两种。电流采样是低端分流加 AD8418。有 USB 和 CAN。

原理图按电机单元拆页（`MotorCell`），功率级和「去掉功率管、共用电源」的第二轴是分开的。看双轴怎么共用母线时有用。

60 V 管子、48 V 母线，线电压有效值到不了 60 V。DRV8301 也不支持我们的 80~120 V 母线。

## ODriveX

- 仓库：https://github.com/zhbi98/MotorKit
- 许可：MIT
- 工具：KiCad，4 层板。仓库说明已经打样过，并带中文注释。

作者给出的指标是最高 60 V、单轴电流可达 100 A，驱动 1.2 kW 以内的 BLDC 或永磁同步电机。功率管是英飞凌 60 V DirectFET，驱动仍是 DRV8301，MCU 是 STM32F405。固件含电流、速度、位置三环，通信走 CAN，编码器用 AS5047P，和驱动板分开。

电压上限同样是 60 V，不能当作本板的功率级。中文注释和「驱动板 / 编码器板」分开，读 FOC 固件比原版 ODrive 省事。

## 和本板的对照

电机模式的软件结构可以看这两套：采样、校准、电流环、编码器。硬件接口不要照搬 DRV8301。交流源模式它们没有电压闭环和 LC 滤波。

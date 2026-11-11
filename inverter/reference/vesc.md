# VESC 与 FOC_KING

VESC 是 Benjamin Vedder 的开源电调固件和工具，硬件变体很多，常见于滑板和轻型电动车，母线多在 60 V 上下，电流远大于我们的 10 A。

## 固件

- https://github.com/vedderb/bldc
- 许可：GNU GPL
- 上位机是 VESC Tool

电机模式若走 VESC 兼容，硬件约束会反过来卡死 PWM、采样电阻和运放增益。第一版不打算兼容 VESC，只把它当作 FOC 和无感观测的读物。GPL 固件不能整段抄进以后可能闭源的控制器程序。

## FOC_KING

- https://github.com/nordstream3/FOC
- 许可：CERN-OHL
- 工具：KiCad。按 JLCPCB / LCSC 的库存选型。

作者把它做成 VESC6 风格的无驱动芯片方案：六路独立栅极驱动，而不是一颗三相预驱。板子拆成三块，用排针叠起来：

| 模块 | 内容 |
|------|------|
| POWER BRIDGE | 三相桥，可装 6 或 12 只 MOSFET |
| MCU | STM32F405，USB-C，CAN，BMI270 |
| SUPPLY | 12 V 给驱动，5 V 和 3.3 V 给逻辑 |

仓库里的指标写过两套：标题一带是 75 V / 300 A 的设计目标，正文里又写连续约 84 V / 200 A、20 串电池。以原理图上的管子和电容耐压为准。

84 V 母线用线性 SVPWM 时，线电压有效值大约到 84 / √2 ≈ 59 V，刚好擦到 60 V，开关过冲没有余量。布局是大电流电调，不是 10 A 的实验功率板。

## paltatech 控制板

- https://github.com/paltatech/VESC-controller
- 许可：CERN OHL 1.2
- 作者标明硬件未测试

这是一块 VESC 固件的控制板，不是功率板。它定义了母线电压、相电流、相电压、驱动故障、霍尔 / 编码器 / 旋变，驱动侧示例接到 Power Integrations 2SP0115T。这种接口是高压 IGBT 模块用的，和 100 V MOSFET 自举驱动不是一条路。

「控制板只出 PWM 和收采样、功率级另做」这件事，和我们的连接器思路一致，引脚定义不要照抄。

## 和本板的对照

可参考独立栅极驱动（每只管子一路）和功率 / 控制 / 电源分板。电流和电压等级都不适合第一版。

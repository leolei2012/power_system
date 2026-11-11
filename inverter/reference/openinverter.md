# openinverter

- 硬件：https://github.com/jsphuebner/inverter-hardware
- 项目：https://openinverter.org/wiki/Main_Page
- 驱动板说明：https://openinverter.org/wiki/Gate_Driver
- 许可：CC BY-SA 4.0。丝印上的 “J. Huebner / openinverter.org” 按仓库要求不能改位置和内容。
- 工具：Eagle。分成主板、采样板、栅极驱动板。

Johannes Huebner 的开源交流电机逆变器，面向电动汽车改装，固件做 V/f 和 FOC。功率器件用现成的 IGBT 模块，开源的是控制、采样和驱动，不是一块低压 MOSFET 功率板。

## 硬件分法

| 板 | 作用 |
|----|------|
| Main board | STM32 控制、编码器 / 旋变、CAN、保护逻辑 |
| Sense board | 母线电压、散热器温度、两相电流 |
| Gate driver | 隔离驱动。Si8261，隔离电源约 +15 V / −9 V，峰值驱动约 4 A |

驱动板供电能力大约 1 W，开关频率上不去，文档示例是 8~10 kHz 量级的 IGBT，不是 20 kHz 的 MOSFET。

项目 FAQ 里写过：380 V 交流整流后母线约 540 V，600 V 的 IGBT 余量不够，这种场合要用 1200 V 功率级。这是高压工业变频器的约束，和我们第一版 100 V 无关。

## 和本板的对照

第一版不要用这套功率级和隔离驱动。自举驱动在 100 V 更简单，损耗也更低。

以后母线做到 400 V 时，这套「控制板 / 采样板 / 每相隔离驱动」是直接的结构参考。电流采样用两相、第三相用基尔霍夫算出，FOC 里很常见，和我们第一版「三相都采样」不同，做电机模式时可以再取舍。

可参考的部分：板级划分、隔离驱动的电源和故障回传、电机固件的参数组织。不要把 Eagle 图改进本仓库而不保留 CC BY-SA。

# SimpleFOC 与低压评估板

- 固件：https://github.com/simplefoc/Arduino-FOC
- 许可：MIT
- 社区：https://community.simplefoc.com/
- 常用硬件：ST B-G431B-ESC1，用户手册 UM2516

SimpleFOC 把无刷驱动收成电压、速度、位置几层接口，支持 STM32 的六路 PWM 和低端电流采样。适合先把电机模式的软件跑通，再往自己的功率板上搬。

B-G431B-ESC1 是无人机电调形态，ST 说明它面向最高 6 串锂电池，标称 22.2 V，充满约 25.2 V。板上 MOSFET 耐压 60 V，这个 60 V 不是允许的母线电压。社区里讨论过改到 48~56 V，需要换辅助电源、母线电容和分压，而且 60 V 管子贴着用没有过压余量。

立创上的课设板也可以当入门看，但不是 1 kW 参考：

- https://oshwhub.com/lovewangdake/BLDC_Drive
- STM32F103，控制板和驱动板分开，六步换相，作者只验证了霍尔有感
- 许可 GPL 3.0，功率是百毫安到约 1 A 量级

## 和本板的对照

固件分层可以看：PWM 驱动、电流采样、电机对象分开。评估板和课设板的功率级、栅极驱动、母线电容都不要拿来放大到 100 V / 1 kW。

交流源模式不在 SimpleFOC 的范围内。电压给定、LC 滤波和输出电压闭环仍要自己做。

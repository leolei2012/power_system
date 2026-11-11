# Nexperia NEVB-MTR1-I56-1

- 仓库：https://github.com/Nexperia/NEVB-MTR1-I56-1
- 套件说明：https://www.nexperia.com/applications/evaluation-boards/NEVB-MCTRL-100---1-kW--12-48-V-BLDC-motor-driver-kit
- 原理图 PDF：https://assets.nexperia.com/documents/design-support/NEVB-MTR1-I56-1-schematic.pdf
- 许可：MIT/X
- 工具：KiCad。仓库里有 Gerber、BOM，以及分页原理图。

这是 Nexperia 电机评估套件里的三相逆变功率板。控制在另一块板（NEVB-MTR1-C-1）上，可用 Leonardo R3 或 Nucleo。套件面向 12~48 V、1 kW 的 BLDC、永磁同步和有刷电机。

## 功率级

- MOSFET：PSMN3R9-100YSF，100 V，LFPAK56，半桥每臂可并联
- 栅极驱动：NGD4300
- 相电流：分流电阻 + INA241
- 另有母线电流采样和母线电容页

原理图按页拆开：电源输入、输入电流采样、电容组、逆变桥、相电流采样。信号用排针接到控制板，板上留了测试点。

## 和本板的对照

「功率板单独成板、控制用评估板」和我们的拆法一致，分页方式可以直接当目录来用：输入与预充、母线电容、三相桥、驱动、电流采样、电压采样。

不能拿去投 100 V 母线。套件工作电压只到 48 V，管子耐压 100 V。我们母线会到 120 V，过压保护按 130 V，管子至少要 200 V。1 kW 在 48 V 下电流也比我们 100 V、10 A 大得多，分流和铜皮不能照搬。

可参考的部分：原理图分页、控制接口排针、分流 + INA241 的电流采样、母线电容和开关管就近放薄膜电容。

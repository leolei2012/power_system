# PR #15 探针 M1 执行结果

分支 `hw/controller-fixes-issue2`，KiCad 10.0.7；未切分支、未 commit/push。

D102：S1A-13-F/C150735 → **PMEG2010ER,115/C82288（Nexperia）**，与D103、D201同料同封装。符号`MyParts:PMEG2010ER_115`；封装`MyFootprints:Nexperia_CFP3_SOD123W_Reflow`；字段已补齐。

网表极性：**D102/2=A→CORE_5V_TVS，D102/1=K→CORE_LDO_IN**。与M1前固定提交比较的376个物理pin-node网络保持；供电页仅D102及两条漏电图注改变，其余活动页原文保持。

R301：`0.47×(I+0.0024)`；需求：`3.333+1.4I`；旧VF=1.100 V，新VF=0.320+0.100=0.420 V。冷态加量、小电流折算是工程模型，未包含连接器、容差和动态下陷，不是独立全温保证。

| 入口 V | 负载 mA | 旧S1A LDO入口 | 新PMEG LDO入口 | LDO需求 | 旧余量 | 新余量 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4.75 | 100 | 3.602 | 4.282 | 3.473 | +0.129 | +0.809 |
| 4.75 | 275 | 3.520 | 4.200 | 3.718 | -0.198 | +0.482 |
| 4.75 | 325 | 3.496 | 4.176 | 3.788 | -0.292 | +0.388 |
| 5.00 | 100 | 3.852 | 4.532 | 3.473 | +0.379 | +1.059 |
| 5.00 | 275 | 3.770 | 4.450 | 3.718 | +0.052 | +0.732 |
| 5.00 | 325 | 3.746 | 4.426 | 3.788 | -0.042 | +0.638 |
| 5.25 | 100 | 4.102 | 4.782 | 3.473 | +0.629 | +1.309 |
| 5.25 | 275 | 4.020 | 4.700 | 3.718 | +0.302 | +0.982 |
| 5.25 | 325 | 3.996 | 4.676 | 3.788 | +0.208 | +0.888 |

最紧点4.75 V/325 mA：LDO入口4.176122 V，需求3.788 V，余量 **+0.388122 V**。按0.2 V最小VF工程假设，高端LDO损耗 **0.518740 W**、θJA=77.7°C/W估算温升 **40.31°C**；保留原忽略压降 **0.633750 W / 49.24°C** 保守上界。典型工况估算约65–110 mA不含编码器，**275/325 mA设计上限不变**。

漏电代价：60 µA与1 mA示例在VDD=3.46 V、70 kΩ MR上拉下，CORE_5V_TVS/MR分别约0.1785/0.1185 V与2.1365/1.1365 V。85°C、数伏反压Fig.5约20–30 mA为典型量级，实际反压会随前端抬高而下降；MR可能进入未定义区，不能排除误判5 V存在。场景限于≤50 mA总短时异常注入，须实测。

| 检查 | 实际结果 |
| --- | --- |
| ERC（--severity-all） | `ERC messages: 0  Errors 0  Warnings 0` |
| MCU pinmap逐脚/物理端口/NC | 64/64 |
| J101 / J102 | 32/32 + 32/32 |
| 全部验证（含第三轮原检查） | 2144项，失败0项；**通过** |
| 活动层级 | 10页，102个位号；PDF 10页 |
| 0402/01005/0201 / 空Footprint | 0 / 0 |
| 冻结范围 | lib子模块、inverter、两份归料号BOM、design_decisions、test_spec及PCB保持；四个明确受保护文件SHA256见JSON |

修改文件（含新增/移入文件，取自git status）：

```text
 M controller/hardware/g431_core/core_supply.kicad_sch
 M controller/hardware/g431_core/core_supply_design.md
 M controller/hardware/g431_core/review/bom_issue2.csv
 M controller/hardware/g431_core/review/controller.net.xml
 M controller/hardware/g431_core/review/controller.pdf
 M controller/hardware/g431_core/review/erc_issue2.rpt
 M controller/hardware/g431_core/review/issue2_changes.md
 M controller/hardware/g431_core/review/validate_pr13.py
 M controller/hardware/g431_core/review/validation_issue2.json
 M docs/controller_daughterboard.md
?? controller/hardware/g431_core/review/pr15_m1_result.md
```

未决项：

- D102 S1A-13-F/C150735→PMEG2010ER,115/C82288：bom/bom.csv待料号同步，本PR不改；review/bom.csv同样保持
- 最低入口/低温/动态压差及0.634W保守上界下的叠板温升待样机验证
- 高温高阻掉电、≤50mA短时回供可能使MR处于未定义区，不能排除误判5V存在；需测MR/NRST/CTRL_READY
- PMEG表7与Fig.5室温漏电典型数据不一致，需原厂澄清；85C图示仅作量级，非保证最大值
- C212与C301确切MPN/LCSC/DC bias、LED中央焊盘属性及既有本地临时器件入库交接保持原待办
- 65–110mA仅为不含编码器的条件化典型工况估算；不改275/325mA设计上限，降预算须雨田决定

依据页/表、漏电分析及典型工况分项见 [issue2_changes.md](issue2_changes.md#pr-15-探针-m1ldo-入口压差)；逐项检查/精确核算见 [validation_issue2.json](validation_issue2.json)。

复现：从g431_core目录运行 `python3 review/validate_pr13.py -o review/pr15_m1_result.md`。原PR #13基线及M1前基线均固定，允许本次精确变更，未放宽受保护文件检查。

# STM32G431应用引脚与资源（Rev E）

一颗STM32G431RBT6/LQFP64控制一路三相桥及一路制动。最小核全部52个可GPIO复用pad通过两组2×16排针引出，**GPIO无NC**；逐脚定义见 [当前CSV](../../controller/hardware/g431_core/STM32G431RBT6_pin_plan.csv)，接口见 [64针表](../../docs/controller_daughterboard.md)。52包含NRST、HSE和BOOT复用脚，不是52个可同时自由使用GPIO。

所有应用接口、LED、ADC滤波及输入保护均在底板，最小核网络使用GPIO端口名。下面是本底板的应用分配，不能把旧Rev D的FAULT_N_MCU等应用名当作最小核通用网名。

| 功能 | GPIO | 外设/约束 |
| --- | --- | --- |
| U/V/W上桥PWM | PA8/PA9/PA10 | TIM1_CH1/2/3，AF6 |
| U/V/W下桥PWM | PB13/PB14/PB15 | CH1N/2N为AF6，PB15 CH3N为AF4 |
| 桥故障 | PB12 | TIM1_BKIN AF6，低有效；底板1k/钳位后接入，上拉参考核心3.3 V |
| 桥使能 | PC4 | GPIO；底板串阻/物理下拉 |
| 独立制动 | PC6 | TIM8_CH1 AF4；底板物理下拉 |
| RUN_ARM | PC7/p39 | 子板R402 10k下拉，送U105与复位正常相与产生CTRL_READY；底板该socket脚NC |
| 底板就绪 | PC13/p2 | BASE_READY经底板1k/钳位到达PC13，下拉默认低 |
| I_U/I_V/I_W | PC0/PC1/PC2 | ADC1_IN6 / ADC2_IN7 / ADC1_IN8 |
| V_DC/V_U/V_V/V_W | PC3/PA4/PB0/PB1 | ADC2_IN9 / ADC2_IN17 / ADC1_IN15 / ADC1_IN12 |
| NTC | PB2 | ADC2_IN12 |
| 编码器A | PA0/PA1/PA2 | TIM2_CH1/2 AF1；Z为EXTI2 |
| 编码器B | PB6/PB7/PA3 | TIM4_CH1/2 AF2；Z为EXTI3 |
| SPI A | PA5/PA6/PA7/PA15 | SPI1 SCK/MISO/MOSI AF5；CS为GPIO |
| SPI B | PC10/PC11/PC12/PC9 | SPI3 SCK/MISO/MOSI AF6；CS为GPIO；PC10/11同时是ROM串口复用脚 |
| 应用TTL | PB10/PB11 | USART3 TX/RX AF7，**不是ROM USART3入口** |
| 可选CAN | PA11/PA12 | FDCAN1 RX/TX AF9；底板PHY仅按经典CAN，整支路DNP |
| SWD | PA13/PA14 | SWDIO/SWCLK AF0，经64针到底板J13；独立核从排针接调试器 |
| 四个GPIO LED | PC5/PC8/PD2/PB5 | RUN/FAULT/COMM/AUX，实体全部在底板 |
| HSE候选 | PF0/PF1 | 子板晶体及负载电容DNP；装HSE时不得当GPIO外驱 |
| NRST/BOOT | PG10/PB8 | NRST经J102/32供底板SWD，PB8_BOOT0经J102/1引出，仍有本地按钮/下拉 |
| 应用未分配 | PC14/PC15/PB3/PB4/PB9 | 最小核全部引出，底板对应socket脚NC |

底板共9个socket脚NC：上述5个未分配脚，加PB8_BOOT0、PC7、HSE_IN、HSE_OUT。它们在子板仍连接，PC7/BOOT/HSE也各有本地用途，不应称为9个未用MCU脚。

引脚/AF依据保留 [ST DS12589 Rev6图10/表12/13](https://www.st.com/resource/en/datasheet/stm32g431rb.pdf)。SPI B使用SPI3避开下桥PWM；Z为中断输入，不承诺硬件索引清零。ABZ/SPI/TTL为3.3 V逻辑，传感器5 V供电不代表可直接接5 V或RS-422信号。

机械规划为两块60×60 mm PCB轮廓对齐，上功率板下最小核，四角M2孔待共同校核。下板顶面male朝上、上板底面female朝下，64针电气合同不变；8.5 mm母座塑高不冻结板距。RESET（SW2）/BOOT（SW3）均在下层控制板顶面、与MCU同面，操作面朝上，靠板边从侧面伸入后向下按；与排针、支柱及线束错开，两键统一采用TS-1101-C-W/C318938，电气功能不变，插合后操作净空须随板距、支撑及线束共同校核。

## 启动与调试

U103把NRST缓冲成CORE_RESET_OK，U105与PC7相与产生CTRL_READY。插底板时PC7必须保留RUN_ARM，复位默认低；应用先配置安全PWM/ENABLE/BRAKE、低有效BKIN及故障恢复流程，再主动ARM，不使用自动重启。独立最小板可按通用GPIO使用PC7。

物理BOOT需要 **nSWBOOT0=1、nBOOT1=1、BOOT_LOCK=0**。按住BOOT，按下并释放RESET，再松BOOT。ROM USART3使用 **PC10_TX/PC11_RX**，不是应用TTL的PB10/PB11；使用时断开SPI B相关外设。ROM阶段不取得PC7 ARM许可。

底板SWD使用PA13、PA14、NRST、核心3.3 V VTREF和GND；独立最小板从同一GPIO排针接。保持NRST功能，外部仅开漏拉低；PA15作CS前释放JTDI，检查BOOT选项与未使用的UCPD默认功能。

## ADC时序

底板八路360 Ω/钳位后接100 Ω/1 nF，七路缓冲输出还带47 Ω，名义串阻合计507 Ω；NTC另计10k源阻及底板10 nF，跨板走线也需计入采样评估。两ADC不能让三相电流全部同时转换，U/V同步与W顺序、低端分流有效窗口及重构仍待验证。TIM1内部触发不额外占GPIO。

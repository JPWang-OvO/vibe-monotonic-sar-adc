# MONOTONIC_SAR

TSMC 180 nm、1.8 V、10 bit、50 MS/s 全差分单调切换 SAR ADC。
采用顶板采样、向下单调切换、PMOS 动态比较器及异步完成握手。
CDAC 单位电容 4.8 fF，每侧 512 个单位、总计 2.4576 pF。

当前设计包含 15 个功能 cell，直接引用 11 个标准单元。
电路源位于各 cell 的 `netlist/`，原生 schematic、symbol 及绘图独立保存。
规格、条件和基线归所属 flow；参数与拓扑探索归 study。项目入口见 [project.json](project.json)。

已有 20 项验收结果保存在 [系统 flow 的 baseline](regression/systems/monotonic_sar/flows/acceptance/baselines/accepted.json)：
TT/25°C 及 SS/FF、−40/125°C，各覆盖两个频点和关闭/开启 seed=1 的瞬态噪声。
TT 无噪声低/中频 SNDR 为 61.196/60.542 dB，含噪声为 60.227/59.586 dB；
全矩阵最低 SNDR 为 59.223 dB，最小转换余量为 0.763 ns。
TT 核心功耗为 2.0410–2.0765 mW，包含参考供电并扣除输出缓冲，满足 3 mW 上限。

当前已按论文 Fig. 7(a) 补齐 SAR_BOOST 的串联复位管，并将 SAR_BIT strength 改为从 1 开始的末级倍乘。
原生 OA 与当前源的 1,266 组底层器件比较通过；strength 调整保持原有器件的 finger/multi。
复位拓扑修改后尚未重新仿真，上面的 20 项性能数值属于修改前的已批准基线。

| 任务 | 入口 |
|---|---|
| 设计尺寸、接口与时序 | [设计约定](docs/architecture/adc.md) |
| 20 项实测结果 | [电气验收](docs/verification/lowpower-acceptance.md) |
| 编译、仿真、扫参与报告 | [Regression](regression/README.md) |
| 比较器噪声表征 | [Noise study](regression/blocks/sar_cmp/studies/noise/README.md) |
| DAC 建立与捕获竞争 | [SNDR 诊断](docs/verification/sndr-diagnosis.md) |
| 原生网表和图面核对 | [OA 交付](docs/verification/lowpower-oa-delivery.md) |
| 优化前的冻结设计 | [Checkpoint](docs/history/2026-10-24-ai-autonomous-human-polish-r1.md) |

本机产物根目录为 `<artifact-root>`，连接配置见
`config/environments/tsmc18.local.json`。历史候选及旧 flow 由 Git 和既有 artifacts 保存。
Bridge、PDK 和标准单元源库为外部依赖；本项目当前验证范围为原理图及仿真。

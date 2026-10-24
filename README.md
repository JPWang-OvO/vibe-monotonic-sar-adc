# MONOTONIC_SAR

TSMC 180 nm、1.8 V、10 bit、50 MS/s 的全差分单调切换 SAR ADC。
采用论文的顶板采样、向下单调切换、PMOS 动态比较器及异步完成握手。
CDAC 单位电容 4.8 fF，每侧 512 个单位、总计 2.4576 pF。

同一低功耗版本已通过全部 20 项原规格验收：TT/25°C 及 SS/FF、−40/125°C，
每个条件覆盖两个指定频点及关闭/开启固定 seed=1 的瞬态噪声。
TT 无噪声低/中频 SNDR 为 61.196/60.542 dB，含噪声为 60.227/59.586 dB。
全矩阵最低 SNDR 为 59.223 dB，最小转换余量为 0.763 ns。
TT 核心功耗为 2.0410–2.0765 mW，满足 3 mW 上限；
该口径包含参考供电并扣除输出缓冲，含缓冲功耗与主时钟输入功率单列于验收报告。

SNDR 收敛主要修正了 DAC 建立与比较评估的重叠。
比较器采用 4 µm 输入对和 2 µm 再生对，其噪声由独立模块 flow 测量。
DAC 单变量对照使 FF/125°C 低频无噪声 SNDR 从 57.678 提升到 60.990 dB；
后续加强再生支路，修正近零差分时 Valid 提前触发复位造成的最低位捕获竞争。
比较器噪声、逐位波形及单变量对照见 [SNDR 诊断](docs/verification/sndr-diagnosis.md)。

当前层次包含 27 个自研 cell，原生 schematic 和 symbol 保存于各 cell 的 view 目录。
原生导出的层次端口、连接和有效器件参数与已验收 DUT 一致，修改视图已完成原生窗口审阅。
输出接口为 `D<9:0>`；统一在采样结束后 18 ns 读码，十次比较和 EOC 在下一采样前完成。

| 入口 | 内容 |
|---|---|
| [设计约定](docs/architecture/adc.md) | 论文机制、当前尺寸、接口与时序 |
| [低功耗验收](docs/verification/lowpower-acceptance.md) | 20 项 SNDR、功耗、时序及 checkpoint 对照 |
| [SNDR 诊断](docs/verification/sndr-diagnosis.md) | 失真原因、独立比较器噪声及 DAC 建立对照 |
| [比较器噪声 flow](regression/blocks/sar_cmp/flows/noise_regen2/README.md) | 激励、统计方法、测量范围和复现 |
| [尺寸收敛](docs/verification/lowpower-sizing.md) | 功耗分解与候选选择 |
| [固定验收方法](docs/verification/acceptance-method.md) | 取码、FFT、噪声和供电边界 |
| [仿真入口](regression/README.md) | prepare、execute、collect 与报告 |
| [低功耗 OA 交付](docs/verification/lowpower-oa-delivery.md) | 保留图面、原生核对和截图 |
| [冻结 checkpoint](docs/history/2026-10-24-ai-autonomous-human-polish-r1.md) | 优化前的已验收设计与人工图面 |

批次保存实际 view、激励、PDK 参数补全、原始码、频谱、逐位记录与完整日志；波形保留在服务器。
本机产物根目录为 `<artifact-root>`，机器配置见
`config/environments/tsmc18.local.json`。当前完整绑定由 `config/lowpower_design.json` 固定。
优化前的 `config/final_design.json`、`config/acceptance_results.json` 及 checkpoint tag 保留。
模板、Bridge、PDK 和标准单元库保持只读；设计与验证范围为原理图及仿真。

# MONOTONIC_SAR

TSMC 180 nm、1.8 V、10 bit、50 MS/s 的全差分单调切换 SAR ADC。
基于论文的顶板采样、向下单调切换、PMOS 动态比较器及异步完成握手，
按 Python 电荷模型、模块化 Verilog-A、晶体管电路逐层实现。

同一晶体管版本已通过全部 20 项正式验收：TT/25 °C 和 SS/FF、−40/125 °C，
每个条件覆盖两个指定频点及无噪声、固定 seed=1 瞬态噪声。
TT 无噪声低/中频 SNDR 为 61.645/61.006 dB，含噪声为 60.655/60.343 dB；
全矩阵最低 SNDR 为 58.488 dB，最小转换余量为 2.555 ns。
TT 无噪声总供电功耗约 193.7 mW，包含输出缓冲，主时钟输入功率单列。
正式绑定、逐项指标和功耗见 [电气验收](docs/verification/electrical-acceptance.md)，
分层实现及修正依据见 [开发结果](docs/verification/development-status.md)。
28 个自研 cell 的 OA schematic/symbol 已生成并完成原生网表等价核对，
功能图和重复实例阵列已重绘，原生窗口图面审阅完成；输出接口为 `D<9:0>`。

| 入口 | 内容 |
|---|---|
| [设计约定](docs/architecture/adc.md) | 论文机制、迁移参数、接口与误差预算 |
| [开发结果](docs/verification/development-status.md) | 分层证据、候选批次、当前未完成项 |
| [固定验收方法](docs/verification/acceptance-method.md) | 取码、FFT、噪声、时序及功耗边界 |
| [执行窗口](docs/plans/execution.md) | 用户延长后的完成条件与资源上限 |
| [Python 模型](regression/systems/monotonic_sar/model.py) | 显式采样、逐次比较和电荷重分配 |
| [电路源](library/systems/monotonic_sar/MONOTONIC_SAR/cell.json) | 顶层接口与 view；实际模块绑定由各 flow 固定 |
| [仿真入口](regression/README.md) | prepare、execute、collect 与结果组织 |
| [OA 源表示](docs/architecture/source-contract.md) | circuit/native/drawing 文件与原生导出核对 |
| [OA 交付](docs/verification/oa-delivery.md) | 原生库、阵列、检查结果与复现命令 |

每个批次的 `batch.json`、`preview.md`、`settings.json`、`pdk.scs` 和 `changes.json`
保存实际绑定、激励、enrichment、资源与判据；`summary.json` 及各 case 的 `results.json`
保存指标、连续输出码、逐位轨迹、频谱和功耗。原始波形保留在服务器。
本机产物根目录为 `<artifact-root>`，机器配置见
`config/environments/tsmc18.local.json`。

工程从 IC_DESIGN_TEMPLATE 复制，模板原件、Bridge、PDK 与标准单元库保持只读。
模板说明保留于 [README-TEMPLATE.md](README-TEMPLATE.md)。本任务范围为原理图和仿真。

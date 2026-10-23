# MONOTONIC_SAR

TSMC 180 nm、1.8 V、10 bit、50 MS/s 的全差分单调切换 SAR ADC。
基于论文的顶板采样、向下单调切换、PMOS 动态比较器及异步完成握手，
按 Python 电荷模型、模块化 Verilog-A、晶体管电路逐层实现。

当前已完成全有源晶体管替换。开发批次 `physical_sine_07` 在 TT、无噪声条件下，
两个指定频点的实际 256 点输出码 SNDR 为 61.197/60.768 dB；该版本的采样周期误差未通过。
后续候选已通过 TT/SS125 的功能、逐位建立、周期及输出保持检查，正在解决等待门过冲。
正式 20 项验收尚未完成，OA schematic/symbol 尚未进入收尾阶段。

| 入口 | 内容 |
|---|---|
| [设计约定](docs/architecture/adc.md) | 论文机制、迁移参数、接口与误差预算 |
| [开发结果](docs/verification/development-status.md) | 分层证据、候选批次、当前未完成项 |
| [固定验收方法](docs/verification/acceptance-method.md) | 取码、FFT、噪声、时序及功耗边界 |
| [执行窗口](docs/plans/execution.md) | 12 小时绝对截止时间与资源上限 |
| [Python 模型](regression/systems/monotonic_sar/model.py) | 显式采样、逐次比较和电荷重分配 |
| [电路源](library/systems/monotonic_sar/MONOTONIC_SAR/cell.json) | 顶层接口与 view；实际模块绑定由各 flow 固定 |
| [仿真入口](regression/README.md) | prepare、execute、collect 与结果组织 |
| [OA 源表示](docs/architecture/source-contract.md) | circuit/native/drawing 文件与原生导出核对 |

每个批次的 `batch.json`、`preview.md`、`settings.json`、`pdk.scs` 和 `changes.json`
保存实际绑定、激励、enrichment、资源与判据；`summary.json` 及各 case 的 `results.json`
保存指标、连续输出码、逐位轨迹、频谱和功耗。原始波形保留在服务器。
本机产物根目录为 `<artifact-root>`，机器配置见
`config/environments/tsmc18.local.json`。

工程从 IC_DESIGN_TEMPLATE 复制，模板原件、Bridge、PDK 与标准单元库保持只读。
模板说明保留于 [README-TEMPLATE.md](README-TEMPLATE.md)。本任务范围为原理图和仿真。

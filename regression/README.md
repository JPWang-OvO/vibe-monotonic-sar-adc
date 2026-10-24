# ADC 验证复现

从项目根目录运行。`$edaPython` 使用已有 Bridge Python，设置见[配置说明](../config/README.md)。
本机环境文件为 `config/environments/tsmc18.local.json`；实际产物根目录由该环境和项目配置解析。

```powershell
& $edaPython -m regression.common.runner prepare --environment config/environments/tsmc18.local.json --batch-id <新批次名称> --workers 2
& $edaPython -m regression.systems.monotonic_sar.acceptance.check_netlist <本地批次目录> --formal --acceptance config/acceptance_lowpower.json
& $edaPython -m regression.common.runner execute --batch <本地批次目录>
& $edaPython -m regression.common.runner collect --batch <本地批次目录>
```

默认 `project.json` 指向两个 TT 无噪声频点。`prepare` 打包实际 view 绑定、模型和 TB，
通过 PDK CDF 回调及原生导出补全器件参数，生成 `preview.md`、`batch.json`、`settings.json`、
`pdk.scs` 和 `changes.json`。审阅这些文件及网表边界后，按已确认的批次范围执行。

`collect` 在作业结束后下载指标、汇总和完整日志；原始波形保留在服务器。
`cancel --batch <本地批次目录>` 停止指定批次。全部仿真使用 Spectre X AX、每 worker 8 线程，
所有批次及准备阶段合计不超过 14 worker，不添加精度、积分步长或收敛控制。

## 当前低功耗设计

`config/lowpower_design.json` 固定当前 DUT 的全部绑定和 14 个复现 flow，覆盖原来的 20 个条件。
TT/25°C 以及 SS/FF 的 −40/125°C 各运行低、中两个频点及关闭/开启瞬态噪声。
使用重复的 `--flow` 参数选择其中的 flow；不同噪声条件可在已批准的资源限额内并行。
当前 TT 功耗上限为 3 mW，SNDR 下限沿用 57/56.5 dB，并单列向 59–60 dB 优化的结果。

已验收矩阵由 `lowpower_final_remaining_05` 的 17 项，以及 `lowpower_regen2_adc_01` 的三项复测组成。
复用条件为 TT 低频无噪声、SS/125°C 低频含噪声及 SS/−40°C 中频含噪声；两批次属于同一 DUT：

```text
python -m regression.systems.monotonic_sar.acceptance.lowpower_report <剩余17项批次> <三项复测批次>
```

从上述 14 个 flow 全新复现时，可把全部同一 DUT 批次作为位置参数传给 `lowpower_report`。
脚本核对全部实际源、固定窗口、频点和噪声，更新 `config/acceptance_lowpower_results.json`
及 [低功耗验收](../docs/verification/lowpower-acceptance.md)。独立比较器测试见
[比较器噪声 flow](blocks/sar_cmp/flows/noise_regen2/README.md)，系统失真定位见 [SNDR 诊断](../docs/verification/sndr-diagnosis.md)。

## 冻结 checkpoint 的阶段

`config/final_design.json` 保留优化前 checkpoint 的全部绑定和 12 个 flow。使用重复的 `--flow` 参数合并同一阶段的频点。

| 阶段 | flow 文件夹 | 启动条件 |
|---|---|---|
| 1 | `final_stage1_tt_k3`、`final_stage1_tt_k51` | 完整晶体管集成及边界检查通过 |
| 2 | `final_stage2_tt_k3`、`final_stage2_tt_k51` | 阶段 1 两项全部通过 |
| 3 | `final_stage3_{ss_m40,ss_125,ff_m40,ff_125}_{k3,k51}` | 阶段 2 两项全部通过 |

以上文件夹均位于 `regression/systems/monotonic_sar/flows/`，每个使用其中的 `flow.json`。
阶段 3 每个 flow 同时包含关闭/开启瞬态噪声两个 case，总计 16 项。
执行窗口记录于 `config/run_budget.json`；`deadline_utc` 为 null，表示未设置绝对截止时间。
每个批次受其 flow 的执行时限约束。配置了绝对截止时间的批次会在收集预留窗口前停止启动新作业。

## 绘图与 checkpoint 报告

```powershell
& $edaPython -m regression.systems.monotonic_sar.analysis.plot_candidate <本地批次目录>
& $edaPython -m regression.systems.monotonic_sar.analysis.plot_timing <本地批次目录>
& $edaPython -m regression.systems.monotonic_sar.acceptance.report <阶段1批次> <阶段2批次> <四个阶段3批次>
```

每个批次的 `figures/` 包含原始连续输出码 CSV、FFT 图和代表性转换时序。
上述 `report` 用于冻结 checkpoint，检查固定窗口、频点、门槛、实际噪声频带、模块绑定及各批次 DUT 源文件一致性，
更新 `config/acceptance_results.json` 和 `docs/verification/electrical-acceptance.md`。
仅同一版本的 20 项全部通过后进入 OA 收尾。

Python 与 Verilog-A 对齐记录、模块测试和失败候选见[开发结果](../docs/verification/development-status.md)。
这些 flow 保留实际测试条件，不能与最终候选混合计为正式通过。

## 工具归属

公共运行、依赖解析、日志与 PSF 读取放在 `common/`。
ADC 的参考模型、测量、绘图和诊断见 [analysis](systems/monotonic_sar/analysis/README.md)，
正式验收见 [acceptance](systems/monotonic_sar/acceptance/README.md)。
模块实验按 target 保存于 `studies/`，包括 [采样孔径](blocks/sar_sampler/studies/aperture/README.md)
和 [等待门](systems/monotonic_sar/studies/wait_gate/README.md)。
[TSMC18 参数补全资格测试](blocks/tsmc18_devices/flows/qualification/README.md) 检查原型与原生参数。
电路源由 `library/` 管理；flow 直接引用 cell 的已有 view。

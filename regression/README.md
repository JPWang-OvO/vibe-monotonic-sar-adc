# ADC 验证复现

从项目根目录运行。`$edaPython` 使用已有 Bridge Python，设置见[配置说明](../config/README.md)。
本机环境文件为 `config/environments/tsmc18.local.json`；实际产物根目录由该环境和项目配置解析。

```powershell
& $edaPython -m regression.common.runner prepare --environment config/environments/tsmc18.local.json --batch-id <新批次名称> --workers 2
& $edaPython -m regression.check_final_netlist <本地批次目录> --formal
& $edaPython -m regression.common.runner execute --batch <本地批次目录>
& $edaPython -m regression.common.runner collect --batch <本地批次目录>
```

默认 `project.json` 指向阶段 1 的两个 TT 无噪声频点。`prepare` 打包实际 view 绑定、模型和 TB，
通过 PDK CDF 回调及原生导出补全器件参数，生成 `preview.md`、`batch.json`、`settings.json`、
`pdk.scs` 和 `changes.json`。审阅这些文件及网表边界后执行；本任务已获得用户的自主执行授权。

`collect` 在作业结束后下载指标、汇总和完整日志；原始波形保留在服务器。
`cancel --batch <本地批次目录>` 停止指定批次。全部仿真使用 Spectre X AX、每 worker 8 线程，
所有批次及准备阶段合计不超过 14 worker，不添加精度、积分步长或收敛控制。

## 正式阶段

`config/final_design.json` 列出同一候选的全部绑定和 12 个 flow。使用重复的 `--flow` 参数合并同一阶段的频点。

| 阶段 | flow 文件夹 | 启动条件 |
|---|---|---|
| 1 | `final_stage1_tt_k3`、`final_stage1_tt_k51` | 完整晶体管集成及边界检查通过 |
| 2 | `final_stage2_tt_k3`、`final_stage2_tt_k51` | 阶段 1 两项全部通过 |
| 3 | `final_stage3_{ss_m40,ss_125,ff_m40,ff_125}_{k3,k51}` | 阶段 2 两项全部通过 |

以上文件夹均位于 `regression/systems/monotonic_sar/flows/`，每个使用其中的 `flow.json`。
阶段 3 每个 flow 同时包含关闭/开启瞬态噪声两个 case，总计 16 项。
执行窗口记录于 `config/run_budget.json`。用户已将本任务延长至目标完成，`deadline_utc` 为 null；
每个批次仍受其 flow 的执行时限约束。配置了绝对截止时间的批次会在收集预留窗口前停止启动新作业。

## 输出与报告

```powershell
& $edaPython -m regression.plot_candidate <本地批次目录>
& $edaPython -m regression.plot_timing <本地批次目录>
& $edaPython -m regression.report_acceptance <阶段1批次> <阶段2批次> <四个阶段3批次>
```

每个批次的 `figures/` 包含原始连续输出码 CSV、FFT 图和代表性转换时序。
报告脚本检查固定窗口、频点、门槛、实际噪声频带、模块绑定及各批次 DUT 源文件一致性，
更新 `config/acceptance_results.json` 和 `docs/verification/electrical-acceptance.md`。
仅同一版本的 20 项全部通过后进入 OA 收尾。

Python 与 Verilog-A 对齐记录、模块测试和失败候选见[开发结果](../docs/verification/development-status.md)。
这些 flow 保留实际测试条件，不能与最终候选混合计为正式通过。

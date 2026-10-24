# ADC 正式验收

`check_netlist` 检查已准备批次中的 DUT 边界、理想源位置、仿真参数和固定测量窗口。
`lowpower_report` 汇总当前设计的正式矩阵，检查视图绑定、条件、源文件一致性和实际噪声频带，
保存 `config/acceptance_lowpower_results.json` 及低功耗电气验收报告。

```text
python -m regression.systems.monotonic_sar.acceptance.check_netlist <批次目录> --formal --acceptance config/acceptance_lowpower.json
python -m regression.systems.monotonic_sar.acceptance.lowpower_report <同一DUT批次> ...
```

报告使用 `config/lowpower_design.json` 的视图绑定。输入批次合计覆盖 TT/25 °C、
SS 与 FF 的 −40/125 °C，两个规定频点及关闭/开启瞬态噪声，共 20 项。
每个 case 只能出现一次；同一角落分批完成时，分别传入对应批次。
混合候选批次必须使用 `--case <批次目录> <case ID>` 选出当前 DUT；不同候选不能合并。
当前功耗门槛为 3 mW，SNDR 原门槛不变；低于 59 dB 优化目标的 case 另列。
优化前的 `report`、`config/final_design.json` 和 `config/acceptance_results.json` 保留用于 checkpoint 复现。
方法与条件见 [验收说明](../../../../docs/verification/acceptance-method.md)。

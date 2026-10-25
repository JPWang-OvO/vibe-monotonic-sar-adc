# ADC 正式验收

`check_netlist` 检查已准备批次的源边界、理想源位置、精度、PDK 补全及固定测量窗口。
`report` 按指定 flow 汇总一个或多个批次，核对实际条件、DUT 源、测量、判据和执行日志。
报告输出到 artifacts；已批准的结果由所属 flow 的 `baselines/` 保存。

```text
python -m regression.systems.monotonic_sar.acceptance.check_netlist <批次目录> --formal
python -m regression.systems.monotonic_sar.acceptance.report --flow regression/systems/monotonic_sar/flows/acceptance/flow.json --output <产物目录>/acceptance.json <批次目录> ...
```

同一条件分批运行时，每次使用 runner 的 `--condition` 选择范围。
报告要求同一 flow 内每个条件只出现一次，并明确列出尚缺条件。
方法见[验收说明](../../../../docs/verification/acceptance-method.md)。

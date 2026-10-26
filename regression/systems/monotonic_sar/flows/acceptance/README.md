# ADC 系统验收

`flow.json` 绑定固定 ADC TB，规定 20 项 PVT、频点和瞬态噪声条件及逐条件判据。
`measure.py` 调用系统波形计算并检查解析后的 criteria；`baselines/accepted.json` 保存当前电路完整 20/20 项通过的正式基线。

从工程根目录运行：

```text
python -m regression.systems.monotonic_sar.flows.acceptance.run compile --condition tt_25_k3_quiet --output <新产物目录>
python -m regression.systems.monotonic_sar.flows.acceptance.run prepare --environment config/environments/tsmc18.local.json --batch-id <新批次> --workers 2
python -m regression.systems.monotonic_sar.acceptance.check_netlist <批次目录> --formal
python -m regression.systems.monotonic_sar.flows.acceptance.run execute --batch <批次目录>
python -m regression.systems.monotonic_sar.flows.acceptance.run collect --batch <批次目录>
```

`compile` 离线展开；`prepare` 调用 PDK/Spectre 生成可执行输入。审阅实际批次后执行。
`--condition` 可同时用于 compile 和 prepare；省略时准备全部 20 项。
2026-10-26 的完整复验覆盖串联复位管补齐后的电路，执行、日志审阅、测量及全部电气判据通过。完整命令、资源约定及报告方法见 [regression 说明](../../../../README.md)。

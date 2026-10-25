# 规格验证与优化实验

从项目根目录运行，`$edaPython` 使用[已有 Bridge Python](../config/README.md)。
`project.json` 登记三个规格 flow：系统验收、比较器功能、分频器功能；
系统 flow 持有 20 项已有实测 baseline。两个模块 flow 的当前实现尚未在本次清理中仿真，未建立新 baseline。

## 编译和仿真

```powershell
$plan = "regression/systems/monotonic_sar/flows/acceptance/flow.json"
& $edaPython -m regression.common.runner compile --plan $plan --output <新的产物目录>
& $edaPython -m regression.common.runner prepare --plan $plan --environment config/environments/tsmc18.local.json --batch-id <新批次名称> --workers 2
& $edaPython -m regression.systems.monotonic_sar.acceptance.check_netlist <本地批次目录> --formal
& $edaPython -m regression.common.runner execute --batch <本地批次目录>
& $edaPython -m regression.common.runner collect --batch <本地批次目录>
```

`compile` 只展开本地配置、变体和相对 include，生成 `plan.json` 及输入文件。
`prepare` 还配置模型、调用 Spectre 参数报告及 PDK CDF 补全，生成可执行的 `batch.json` 和 `preview.md`。
执行前审阅实际输入、条件、测量、阈值与资源。全部仿真使用 Spectre X AX、每 worker 8 线程。
`cancel --batch <目录>` 停止指定批次；原始波形保留在服务器。

`--plan` 接受 `flow.json` 或 `study.json`。重复 `--condition` 可选择该计划中的明确条件，
例如系统验收的 `tt_25_k3_quiet`；省略时展开所选计划全部条件。
正式系统 flow 在同一 TB 下表达 PVT、频点和噪声矩阵，SNDR 门槛按 k 选择，功耗门槛仅用于 TT。

## Study

| Study | 变量与目标 |
|---|---|
| [比较器](systems/monotonic_sar/studies/comparator/study.json) | 输入对、再生对宽度；按系统规格检查功耗与 SNDR |
| [采样](systems/monotonic_sar/studies/sampling/study.json) | 单位电容、采样开关宽度 |
| [控制](systems/monotonic_sar/studies/control/study.json) | 反馈反相器数量、保护电容、DAC 驱动倍率 |
| [独立噪声](blocks/sar_cmp/studies/noise/README.md) | 比较器尺寸与 PVT 下的概率曲线、噪声、偏移和功耗 |

Study 引用 flow 的测量与判据，声明变量、器件参数修改或拓扑生成规则。
候选网表在批次 `inputs/` 中生成；正式 cell 只维护当前电路。
尺寸变体在 `prepare` 时按实际几何重新执行 PDK 参数补全。
独立噪声 study 使用自己的固定 TB 和统计测量，结果解释其表征范围。

```powershell
& $edaPython -m regression.common.runner compile --plan regression/systems/monotonic_sar/studies/comparator/study.json --output <新的产物目录>
& $edaPython -m regression.common.study <study批次目录> --output <产物目录>/study-results.json
```

Study 汇总按参数点列出本批次选定条件的完整性、flow 判据和最坏功耗，再对合格点排序。
59–60 dB 是优化目标；验收 SNDR 下限仍由 flow 规定。
候选晋升时，将选定电路更新到正式源、同步 OA 并完成相应验证。

## 报告与基线

```powershell
& $edaPython -m regression.systems.monotonic_sar.acceptance.report --flow $plan --output <产物目录>/acceptance.json <批次目录> ...
```

报告核对同一 flow 的实际条件、测量、判据、精度及 DUT 源，逐项检查执行、日志与指标。
报告只写 artifacts。基线晋升经审阅后写入所属 flow 的 `baselines/`。
本次归位的是已批准的 20 项历史测量，原批次 ID 和结果路径仍记录在 baseline 中。

波形诊断与绘图见 [analysis](systems/monotonic_sar/analysis/README.md)，固定测量边界见
[验收方法](../docs/verification/acceptance-method.md)。

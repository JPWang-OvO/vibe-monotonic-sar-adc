# 准备和运行验证

一个 flow 保存 `flow.json`、`run.py`、`measure.py` 和其他必要的帮助脚本。配置中的 `testbench` 相对仓库根目录，
TB 的相对 include 决定电路依赖。每个 condition 指定输入变量、corner、`cell_views` 和是否执行 `enrichment`。
因此，一个 flow 可以用同一 TB 比较 schematic 与 PEX。

## 准备与执行

在仓库根目录运行以下命令。`$edaPython` 使用已有 Bridge Python，设置方法见[配置说明](../config/README.md)。
命令中的尖括号表示需要填写的路径。

```powershell
& $edaPython -m regression.common.check
& $edaPython -m regression.common.runner prepare --environment <本机配置文件> --batch-id <批次名称> --workers 1
& $edaPython -m regression.common.runner execute --batch <本地批次目录>
& $edaPython -m regression.common.runner collect --batch <本地批次目录>
```

`prepare` 从 `project.json` 的 `flows` 读取任务，也可重复使用 `--flow <flow.json路径>` 指定任务。
它将依赖打包为文件名唯一的扁平目录，改写 include，填入条件与模型配置。
`enrichment: true` 的条件使用 process 中的映射及 CDF 合约补全 PDK 参数；此步骤需要连接 Virtuoso 和 Spectre。
生成的 `preview.md`、`batch.json`、`settings.json` 与输入 deck 供运行前审阅。

用户确认批次范围、判据、精度和资源后执行 `execute`。服务器独立完成仿真和测量。
`collect` 查询状态，结束后下载指标、汇总及逐作业日志，波形保留在服务器。
`cancel --batch <本地批次目录>` 停止正在运行的批次。运行和基线规则见[验证政策](../docs/verification/policy.md)。

## 测量与扩展

`simulator.precision` 用于 preview 描述，实际精度语句来自 TB；调整精度时同步两处。
`simulator.threads` 和 `timeout_s` 分别规定每作业线程与时限，`--workers` 规定并发上限。

服务器的 `common/measure.py` 按 `measurement.kind` 分发测量。
新增测量算法时接入该分发入口；使用额外模块时，在 `common/runner.py` 的批次打包列表中加入模块及其依赖。
探索性实验放在所属 target 的 `studies/`，记录参数范围、停止条件和运行资源。

用户批准的基线保存到 flow 的 `baselines/`，测量与日志证据路径直接记录在 JSON 中。

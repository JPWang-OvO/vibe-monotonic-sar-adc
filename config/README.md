# 配置环境

本地工具使用 Python 3.10+。Virtuoso 与 Calibre 操作分别使用各自已有的 Bridge Python 环境，
远端 controller 使用 environment 中指定的 Python。

| 配置 | 内容 |
|---|---|
| 根目录 `.env` | `VIRTUOSO_BRIDGE_ROOT`、`CALIBRE_BRIDGE_ROOT` 指向本机工具目录 |
| `project.json` | 项目 ID、设计库名、工艺配置和 flow 索引 |
| `processes/` | technology、器件 master、模型 section、参数补全合约和 Calibre baseline 名 |
| `environments/*.local.json` | Bridge profile、工具与模型路径、运行根目录、OA 库路径 |
| 各 flow 的 `flow.json` | 条件、view 绑定、精度、线程、时限、测量和阈值 |
| `lowpower_design.json`、`acceptance_lowpower.json` | 当前低功耗设计的 view 绑定、正式 flow 和验收条件 |
| `acceptance_lowpower_results.json` | 当前设计已完成批次的实际 view 标识、逐项测量与判定 |
| `final_design.json`、`acceptance.json`、`acceptance_results.json` | 优化前 checkpoint 的绑定、验收条件与结果 |
| 物理任务 JSON | layout/source 身份、电源地、提取设置和 CalibreView 目标 |

从 environment 样例创建本机 `.local.json` 并替换占位值。本机配置忽略入 Git；认证沿用 Bridge 用户配置。
`cadence_setup` 指向远端 csh 环境脚本；SSH 环境已经能运行工具时设为 null。
`remote_runs` 与 `oa_library_path` 分别指向项目独立的运行根目录和 OA 库。

复制根目录的 [.env.example](../.env.example) 为 `.env`，填写两个工具根目录。
物理任务准备时读取此文件，进程中已设置的同名环境变量优先。
本机 environment 的 `calibre.python` 是相对 `CALIBRE_BRIDGE_ROOT` 的解释器路径，
`calibre.config`、`calibre.profile` 选择已有 Calibre Bridge 配置和连接。
Calibre 工艺包管理 runset、layermap、cellmap、规则与 CDL 依赖；项目 process 通过 baseline 名引用它们。
每个物理运行使用项目独立的远端 jobs 目录，原工具配置保持只读。

在仓库根目录使用已有 Python。以下示例适用于 shell 已设置 `VIRTUOSO_BRIDGE_ROOT`，且安装采用按主机命名的环境：

```powershell
$edaPython = Join-Path $env:VIRTUOSO_BRIDGE_ROOT ".venv-$env:COMPUTERNAME/Scripts/python.exe"
& $edaPython -m regression.common.check
& $edaPython -m virtuoso.environment --profile <profile> --remote-run <项目远端目录>/probe
```

解释器路径以实际安装为准。环境盘点检查 CIW、technology、执行主机、CPU/内存和模型可读性；
license 与调度配额按实际获得的信息记录。

更换工艺时更新 project 引用及 process 配置，核对模型 section、器件 master、CDF 版本与回调顺序。
Enrichment 使用 Spectre 原生参数报告、SpiceIn、CDF 和原生 netlister，所选 Bridge profile 的 SSH 环境需能运行 Spectre。
具体配置示例见 [README-TEMPLATE](../README-TEMPLATE.md)。

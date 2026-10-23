# 从已有版图提取 PEX

用户完成并保存 layout 后，项目通过 Virtuoso Bridge 导出 GDS/CDL，调用 Calibre Bridge 执行 DRC、LVS 和 PEX。
主要路径是生成 CalibreView、导入 OA，再由原生 netlister 导出 `pex/netlist.scs` 纳入 Git。
Flow 通过 cell/view 选择这个网表，沿用已有 TB 和测量。

## 配置任务

先按[配置说明](../config/README.md)设置两个 Bridge 根目录和本机 environment。
物理任务 JSON 放在所属 flow 或 study 中，记录以下内容：

| 字段 | 内容 |
|---|---|
| `cell_directory` | 仓库中的 cell 目录，接收发布后的 PEX view |
| `inputs` | `kind: oa` 时指定 library、cell、layout_view、source_view；`kind: files` 时指定远端 layout_file、layout_top_cell、source_file、source_top_cell |
| `operations` | 本次需要的 `drc`、`lvs`、`pex` |
| `power_names`、`ground_names` | LVS 的电源、地网络识别 |
| `cores` | 每个 Calibre 作业使用的核数 |
| `pex` | 引擎、R/RC/RCC、参考地、输出格式、约简与精度 |
| `calibreview` | 导入的 library、cell、view，以及 schematic_library、schematic_view |

工艺 baseline 和映射文件由 Calibre Bridge 工艺包提供，process 配置引用其 baseline 名。
输入 GDS/CDL、规则和映射路径需要在相应执行主机上可读。直接提供文件时，这些路径使用远端绝对路径。
具体配置示例集中在 [README-TEMPLATE](../README-TEMPLATE.md)。

## 准备、运行和收集

从仓库根目录调用项目入口，使用已有 Virtuoso Bridge Python。入口通过 `CALIBRE_BRIDGE_ROOT` 定位 Calibre Bridge 的独立 Python 环境。

```powershell
& $edaPython -m physical.run prepare --environment <本机配置文件> --target <物理任务JSON> --run-id <运行名称>
& $edaPython -m physical.run submit --run <本地运行目录> --operation lvs
& $edaPython -m physical.run collect --run <本地运行目录> --operation lvs
& $edaPython -m physical.run submit --run <本地运行目录> --operation pex
& $edaPython -m physical.run collect --run <本地运行目录> --operation pex
```

`prepare` 保存实际输入、工艺资源、各操作请求和 `preview.md`，OA 输入会在此阶段导出 GDS/CDL。
确认当前设计的提取设置后提交。已确认的同一设置沿用，各操作分别返回 `run_id`。
作业由服务器托管；`status` 查询状态，`collect` 收取报告、完整诊断和提取输出，`cancel` 停止指定作业。
DRC 使用相同入口的 `--operation drc`，任务的 `operations` 中需包含该项。

分别检查工具结束状态、DRC/LVS 结论和报告解析状态。普通 PEX 使用 LVS 匹配的结果。
寄生参考地由当前电路端口及 TB 接法决定，`pex.ground_net` 与 LVS 的 `ground_names` 分别配置。

## CalibreView 到 Git 中的 PEX view

```powershell
& $edaPython -m physical.run import-view --run <本地运行目录>
& $edaPython -m physical.run publish --run <本地运行目录>
```

`import-view` 依据任务中的目标和工艺 cellmap 创建 OA CalibreView，保存导入日志、端口和实例数量。
目标 view 已存在时，先审阅更新范围，再用 `--overwrite` 明确替换已关闭的 view。

`publish` 从该 OA view 调用原生 Spectre netlister，保存原始导出，并将顶层电路包装为 cell 的 subckt。
发布过程核对端口、实例语句与参数，保存 `library/.../<CELL>/pex/netlist.scs`，同时更新 `cell.json`。
该文件纳入 Git，保留完整器件参数和寄生网络。原始 Calibre 输出、OA 导出目录和操作报告留在 artifacts。

审阅网表差异及参考地连接后，在同一 flow 中选择 `pex` view，设置 `enrichment: false`，准备后仿真批次。
仿真和基线规则见[验证政策](../docs/verification/policy.md)。

## 直接 Spectre 输出

任务也可选择 `pex.output_format: SPECTRE`。收集后直接执行 `publish`，导入器展开原始网表中的 include，
保留提取参数和连接，以一个网表保存为 PEX view。已有本地 Spectre 提取入口可直接使用：

```powershell
& $edaPython -m physical.pex --cell <cell目录> --netlist <提取入口文件>
```

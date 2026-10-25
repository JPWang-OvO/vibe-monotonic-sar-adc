---
title: 电路源与原生视图约定
type: architecture
status: current
last_reviewed: 2026-10-24
authoritative_sources:
  - ../../virtuoso/oa/cells.py
  - ../../virtuoso/oa/native.py
  - ../../virtuoso/oa/replay.py
---

# 电路源与原生视图

`cell.json` 索引一个 cell 的各个 view，`ports` 给出网表接口顺序。
`ports` 可包含 `D<9:0>` 形式的总线；核对 Spectre 接口时按声明方向展开为有序标量端口。
Spectre 文件将尖括号转义为 `D\<9\>`；顶层测试台仍按位置连接各位信号。
实例阵列在 `array_members` 中保存成员顺序，公共标量连接广播到每个成员。
`netlist` 等源路径相对 cell 目录。
当前电路使用 `netlist`，原生 OA 使用 `schematic` 和 `symbol`，寄生表示使用 `pex`。
扫参及短期拓扑由 study 生成到批次目录，表示约定见[电路库](../../library/README.md)。
Spectre 文件使用 `.scs` 扩展名，仿真器由 flow 指定。View 按实际内容登记。

| 文件 | 保存内容 |
|---|---|
| `<view>/netlist.scs` | 连接、模型名及设计参数，通过相对 include 使用子模块 |
| `schematic/circuit.json` | 端口、实例 master、连接、设计参数及位置 |
| `<view>/native.json` | 来源库与原生 OA 电气数据，保留 typed properties |
| `<view>/drawing.json` | 原生位置、方向、导线、pin、文字与形状 |
| `cdf.il` | cell 的 base CDF，存在时保存 |
| `veriloga/<CELL>.va` | 行为定义 |
| `pex/netlist.scs` | 从 OA CalibreView 导出的电路及完整寄生参数，纳入 Git |

`ic-circuit-v1` 和 `native-oa-v1` 是设计语义与原生快照的 JSON 格式名称，`v1` 表示第一版格式。
前者标记 `circuit.json` 的设计字段，后者标记 `native.json` 的来源库和原生读取结果。
这些名称用于让读写工具识别数据结构；字段以对应工具的读写接口为准。

## 设计参数与仿真参数

设计网表中的 PDK 器件保留 W/L、finger 数、倍乘等设计参数。
仿真准备阶段的 enrichment 根据已安装 PDK 的 CDF 和原生 netlister 计算完整参数，
在批次中生成 `pdk.scs` 的 Spectre `alter` 语句及 `changes.json`。
修改尺寸、连接或模型后重新准备批次，使参数补全对应当前设计。

OA 快照保留原生数据，供回放和比较使用。PEX 网表保存版图提取得到的器件参数和寄生网络，
由 `cell.json` 的 `pex.netlist` 登记；后仿真直接使用该网表。原始提取文件和导入日志保存在 artifacts。

## 与 OA 同步

`capture` 将当前 OA view 保存为 native/drawing；`replay` 从这些文件重建独立库的 symbol 和 schematic。
`verify` 比较回读的电气数据、图形以及导出网表中的设计参数与连接。
比较时处理明确的库重绑定和工具生成属性，详细范围由比较代码定义。

手工改图后先 capture 并审阅差异。电气变化同步到 `circuit.json`，随后用 `publish-netlist` 从原生导出更新叶级设计网表；
该命令保留设计描述中的参数。纯几何修改更新 native/drawing。
命令参数和回放要求见 [OA 说明](../../virtuoso/oa/README.md)。

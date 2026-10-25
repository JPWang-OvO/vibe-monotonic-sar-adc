# 电路库

`blocks/` 保存功能模块，`systems/` 保存层次集成，`support/standard_cells/` 保存实际引用的标准单元导出，
`testbenches/` 保存固定激励、负载和分析。

每个 cell 由 `cell.json` 定义端口顺序与 view 路径。当前电路统一维护在 `netlist/netlist.scs`，
通过相对 include 引用子模块。标准单元在 OA 中直接使用其原库 master。

| View | 内容 |
|---|---|
| `netlist` | 当前设计的连接、模型和设计参数，或 TB |
| `schematic` | 原生电气对象、图面及原生导出网表 |
| `symbol` | 端口与功能图形 |
| `pex` | 建立版图后，从 OA CalibreView 导出的寄生网表 |

尺寸和短期拓扑候选由 study 在批次中生成。选定设计晋升后更新当前源及相应 OA 表示。
实际不同表示可通过 flow 的 `cell_views` 选择，例如以后建立的 PEX；端口顺序必须一致。

PDK 器件保留设计尺寸，完整参数在仿真准备时补全。同步规则见[源表示约定](../docs/architecture/source-contract.md)。

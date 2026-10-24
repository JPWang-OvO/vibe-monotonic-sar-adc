# 电路库

每个 cell 保存自己的索引与各 view 源：

```text
blocks/<category>/<CELL>/<view>/
systems/<category>/<CELL>/<view>/
support/<category>/<CELL>/<view>/
testbenches/<blocks|systems>/<target>/<TB_CELL>/<view>/
```

View 使用 `表示形式[_变体]` 命名。表示形式为 `schematic`、`symbol`、`veriloga`、`netlist` 或 `pex`；
变体后缀使用小写字母、数字和下划线，在所属 cell 内解释。

| View | 内容 |
|---|---|
| `schematic` | 原生原理图的电气对象、图形与导出网表 |
| `symbol` | 端口及功能图形 |
| `veriloga`、`veriloga_timed` | 行为模型与参数化包装 |
| `netlist`、`netlist_<variant>` | 文本网表实现，包括晶体管电路、层次组合和 TB |
| `pex` | 从 OA CalibreView 导出的寄生网表 |

例如 `SAR_BIAS/netlist_fast36` 的 `Mn_sink` 为 W/L=3.6/2 µm，
`netlist_fast` 和 `netlist_fast45` 的下拉宽度分别为 2.7 µm 和 4.5 µm。
每个变体的模型、尺寸与连接由其源文件定义，系统实际采用的变体由 flow 的 `cell_views` 指定。

`cell.json` 固定端口顺序，并通过相对路径登记已有源文件。
网表定义自己的 cell，通过相对 include 引用子模块。Flow 的每个 condition 用 `cell_views` 选择替代 view。
OA CalibreView 导出的网表保存为 `pex/netlist.scs` 并纳入 Git，cell 索引用 `netlist` 登记。
该 view 保留完整提取参数和寄生网络，供后仿真直接使用。

PDK 设计网表维护连接和设计参数，完整参数在仿真准备阶段补全。
OA 原生数据、绘图和设计网表的同步方式见[源表示约定](../docs/architecture/source-contract.md)。

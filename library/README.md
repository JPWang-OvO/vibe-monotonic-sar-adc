# 电路库

每个 cell 保存自己的索引与各 view 源：

```text
blocks/<category>/<CELL>/<view>/
systems/<category>/<CELL>/<view>/
support/<category>/<CELL>/<view>/
testbenches/<blocks|systems>/<target>/<TB_CELL>/<view>/
```

`cell.json` 固定端口顺序，并通过相对路径登记已有源文件。
网表定义自己的 cell，通过相对 include 引用子模块。Flow 的每个 condition 用 `cell_views` 选择替代 view。
OA CalibreView 导出的网表保存为 `pex/netlist.scs` 并纳入 Git，cell 索引用 `netlist` 登记。
该 view 保留完整提取参数和寄生网络，供后仿真直接使用。

PDK 设计网表维护连接和设计参数，完整参数在仿真准备阶段补全。
OA 原生数据、绘图和设计网表的同步方式见[源表示约定](../docs/architecture/source-contract.md)。

# OA 保存与回放

工具使用 cell 目录中的设计描述、native 数据和 drawing 数据。
从项目根目录运行，`--cell`、目标库及其远端路径填写为当前项目的实际值：

```powershell
& $edaPython -m virtuoso.oa.cells capture --cell <cell目录> --environment <本机配置文件> --library <设计库> --library-path <远端库路径> --run-id <操作名称>
& $edaPython -m virtuoso.oa.cells publish-netlist --cell <cell目录> --environment <本机配置文件> --library <设计库> --library-path <远端库路径> --run-id <操作名称>
& $edaPython -m virtuoso.oa.cells replay --cell <cell目录> --environment <本机配置文件> --library <独立回放库> --library-path <远端回放库路径> --run-id <操作名称>
```

`capture` 保存当前 schematic 和 symbol。手工改图后先审阅捕获差异，将电气变化同步到 `circuit.json`，
再用 `publish-netlist` 更新叶级网表。该命令核对 master、连接、端口及设计参数，采用原生导出的连接与模型，
保留设计描述中的参数。详细 PDK 参数由仿真准备阶段补全。

`replay` 在尚不存在的目标 views 中先创建 symbol、再创建 schematic，完成 Check/Save 后比较回读结果。
已有回放库使用 `verify`。比较结果保存到 `<artifact-root>/<run-id>/<CELL>__verification.json`，
包含逐 view 电气与图形比较，以及网表连接和设计参数比较。图面可读性通过查看原理图和 symbol 审阅。

数据格式见[源表示约定](../../docs/architecture/source-contract.md)。

## 标准单元导出

`python -m virtuoso.oa.export_stdcells --environment <本机配置文件>`
读取 TSMC18 标准单元的原生连接、CDF 端序和 Spectre 网表，保存到 `library/support/standard_cells/`。
回读与导出工作文件位于 artifact 根目录的 `stdcell_native/`。

# IC design template

面向模拟与混合信号 IC 设计的工程模板，用于从零组织电路源、Virtuoso 视图、仿真验证与运行证据。
电路按 cell/view 保存，验证按 flow 保存，EDA 工具通过外部 Bridge 接入。

## 建立项目

1. 复制模板，填写 `project.json` 的项目 ID、设计库名、工艺配置与 flow 入口。
2. 按[配置说明](config/README.md)连接已有 EDA 环境，设置项目独立的 OA 库与产物目录。
3. 按[设计与验证流程](docs/architecture/workflow.md)加入自己的电路、testbench 和验收条件。
4. 准备仿真输入，审阅并确认实际批次，运行后检查每个作业的日志和测量结果。

具体示例的文件、命令与适用条件集中在 [README-TEMPLATE.md](README-TEMPLATE.md)。

| 入口 | 内容 |
|---|---|
| [docs](docs/README.md) | 工程架构、源表示和验证政策 |
| [library](library/README.md) | 电路与 testbench 的 cell/view 组织 |
| [regression](regression/README.md) | flow、批次准备、执行、测量和基线 |
| [virtuoso](virtuoso/README.md) | OA 保存、回放、核对与 ADE 接入 |
| [physical](physical/README.md) | 已有版图的 DRC/LVS/PEX、CalibreView 与后仿真 |
| [config](config/README.md) | 项目、工艺和机器环境配置 |

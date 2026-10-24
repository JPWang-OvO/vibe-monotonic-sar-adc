---
title: 工程目录与职责
type: architecture
status: current
last_reviewed: 2026-10-21
authoritative_sources:
  - ../../project.json
  - ../../regression/common/project.py
  - ../../regression/common/runner.py
---

# 工程目录与职责

电路实现由 cell/view 标识，验证任务由 flow 标识。Testbench 提供激励、供电、负载和分析，
flow 规定运行条件、视图绑定、测量及验收标准。同一 flow 可以在相同 TB 下比较多个 view。

```text
library/blocks|systems|support/<category>/<CELL>/<view>/
library/testbenches/<blocks|systems>/<target>/<TB_CELL>/<view>/
regression/blocks|systems/<target>/flows/<flow>/
regression/blocks|systems/<target>/analysis/
regression/systems/<target>/acceptance/
regression/blocks|systems/<target>/studies/<study>/
regression/common/
virtuoso/oa/ 和 virtuoso/ade/
physical/
config/environments/ 和 config/processes/
docs/{architecture,verification,notes,plans,history}/
```

`blocks` 保存可复用模块，`systems` 表达层次组合，`support` 保存激励与辅助电路。
每个 flow 保持自己的 TB 身份；其各个 condition 用 `cell_views` 选择端口顺序一致的实现。
接口或功能身份变化时建立独立 cell。探索性实验放在所属 target 的 `studies/`，选定设计经审阅后纳入正式源。

各 target 的 `analysis/` 保存参考模型、测量、绘图与日常诊断；`acceptance/` 保存系统正式验收检查与报告。
`studies/<study>/` 保存有明确问题、输入和方法的实验工具。`regression/` 顶层保存索引与包入口。

`regression/common` 从 TB 的相对 include 收集依赖、绑定 view、补全 PDK 参数并调度 Spectre。
`virtuoso/oa` 保存和回放原生电路与图形。`physical` 从已有版图导出 GDS/CDL，调用 Calibre 验证、提取，
将 CalibreView 导入 OA，再导出纳入 Git 的 PEX view 网表。这些操作通过外部 Virtuoso Bridge 和 Calibre Bridge 使用已有 EDA 安装。

Environment 提供机器连接和安装路径，process 提供工艺器件、模型 section 和参数补全配置。
每个仿真批次保存实际展开的输入与设置，项目 ID 决定外部 artifact 子目录。

---
title: 工程模板文档
type: index
status: current
last_reviewed: 2026-10-21
authoritative_sources:
  - ../project.json
  - ../library/README.md
  - ../regression/README.md
---

# 阅读顺序

第一次使用从根 [README](../README.md) 和[配置说明](../config/README.md)开始。

| 任务 | 入口 |
|---|---|
| 了解目录与职责 | [工程架构](architecture/workspace.md) |
| 理解 cell/view 文件格式 | [源表示约定](architecture/source-contract.md) |
| 增加模块、TB 或 flow | [设计与验证流程](architecture/workflow.md) |
| 管理仿真、产物、基线与 checkpoint | [验证政策](verification/policy.md) |
| 保存、回放和核对原生 OA | [Virtuoso](../virtuoso/README.md) |
| 导入寄生视图 | [Physical](../physical/README.md) |
| 保存调查、计划和完成记录 | [Notes](notes/README.md)、[Plans](plans/README.md)、[History](history/README.md) |

源和实际配置定义运行行为；用户批准的基线记录已测结果及适用条件。
架构文档解释当前设计，历史记录保留完成决策的依据。

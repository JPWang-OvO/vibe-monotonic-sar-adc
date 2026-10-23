---
title: 增加设计与验证
type: architecture
status: current
last_reviewed: 2026-10-21
authoritative_sources:
  - ../../library/README.md
  - ../../regression/README.md
  - ../../project.json
---

# 增加设计与验证

1. 在 `library/blocks/<category>/<CELL>/` 保存 `cell.json`、电路源和已有绘图。设计网表保留连接与设计参数。
2. 在 `library/testbenches/blocks/<target>/<TB_CELL>/spectre/` 建立 TB，通过相对 include 使用电路。
3. 在 `regression/blocks/<target>/flows/<flow>/` 添加 `flow.json`、`run.py` 和测量入口，登记到 `project.json`。
4. 运行工程检查及 runner 的 `prepare` 子命令。它展开条件和 view，生成实际输入 deck；启用 enrichment 的条件会调用 PDK 完成参数补全。
5. 审阅 `preview.md`、测量窗口、单位和判据，确认批次后执行。逐个检查作业状态、完整日志和指标。
6. 将候选结果交给用户审核；用户批准后才加入 flow 的 `baselines/`。证据路径和日志审阅结论写入基线 JSON。

系统集成采用独立 system cell 和 system TB。相同激励下比较 schematic 与 PEX 时，在一个 flow 的不同 condition 中选择 view。
具体命令见 [Regression](../../regression/README.md)，源文件格式见[源表示约定](source-contract.md)。

短期实验记录问题、变量、停止条件和结果。完成的设计决策保存在 history，当前架构说明保留最终行为与仍有效的理由。

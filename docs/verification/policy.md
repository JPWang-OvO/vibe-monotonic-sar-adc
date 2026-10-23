---
title: 验证与运行产物政策
type: verification-policy
status: current
last_reviewed: 2026-10-21
authoritative_sources:
  - ../../regression/common/runner.py
  - ../../regression/common/server.py
  - ../../regression/common/measure.py
---

# 验证与运行产物

Flow 配置规定条件和验收阈值；分析与精度语句来自 TB，flow 中的精度描述与 TB 同步。
每项结论注明实际运行的设计、view、条件和测量范围。

## 仿真批次

`prepare` 是 runner 的批次准备子命令。它创建唯一批次目录，展开条件、依赖和视图绑定，
生成输入 deck、命令和 `preview.md`。启用 enrichment 时，它还调用 Spectre 参数报告和原生 PDK CDF 完成参数补全。
正式分析由后续 `execute` 子命令启动。

执行前由项目负责人确认实际批次的 DUT/TB、模型、激励、精度、测量窗口、阈值、作业数、线程与时限。
已确认的批次继续执行；源、条件、精度或测量发生实质变化时，重新准备并确认变化。

`prepare --workers N` 设置并发上限，默认 1。每作业线程数由 flow 指定，实际并发还受 case 数量限制。
远端 supervisor 托管 controller，完成仿真、波形解析和结果保存；SSH 负责提交与查询。
提交成功后用 `collect` 查询同一批次。电气判据失败时继续独立 case；执行、日志或测量错误停止新增作业，收集正在运行的作业。
超时终止对应进程组。重跑与扩大矩阵需重新确定范围。

逐个检查作业的退出状态与完整日志，要求 Spectre 正常结束并通过日志检查，警告原文保留供审阅。
结果分别记录 execution、log audit、measurement、functional 和 performance；未定义的 performance 为 null。
长任务按实际环境安排通知或 watcher，并验证断线后继续运行与会话恢复。CLI 通过 `collect` 收集结果。

## Artifact boundary

设置非空 `VIRTUOSO_BRIDGE_ARTIFACTS_DIR` 时，产物根目录为 `<该目录>/<project_id>`；
否则使用 `<workspace>/artifacts`。配置路径使用本机绝对路径，不可用时报告错误。

```text
<artifact-root>/<batch-id>/
  batch.json, preview.md          实际批次与命令
  cases/<case>/settings.json      展开配置
  cases/<case>/inputs/            扁平化的实际输入文件
  cases/<case>/enrichment/        参数补全记录与原生导出证据
  cases/<case>/logs/              工具与仿真日志
  cases/<case>/results.json       指标和逐项判据
  summary.json, status.json       汇总与远端状态
```

远端项目目录保存 raw 波形、supervisor/controller 状态与日志；参数准备工作位于其 `preparation/<batch-id>/` 下。
波形在服务器解析，本地 collect 收取标量结果与日志。清理产物前确认必要证据已经保留、使用方已经结束。

Git 保存电路源、PEX view 网表、方法、配置、绘图及审核通过的小型基线。
原始 OA 数据库、GDS、波形、Calibre 原始提取输出和导出工作目录保存在 artifacts。
从 OA CalibreView 发布的 `pex/netlist.scs` 保留完整器件与寄生参数，并通过 cell 索引的 `netlist` 登记。

物理任务保存实际 GDS/CDL 路径、工艺资源、请求、run_id、报告与导入日志。
PEX 接入前核对工具结束状态、LVS 匹配、报告解析和端口；CalibreView 还需检查目标 view 与参考地连接。
提取参考地、引擎、耦合、约简与精度按当前设计确认；已确认的同一设置沿用。

## 基线与 checkpoint

新增或更新基线须经项目负责人审核批准。候选结果先留在 artifacts；批准后将必要的小型 JSON 放入所属 flow 的 `baselines/`。
JSON 记录设计版本、view 绑定、条件、精度、指标、判定、基线审核结论，以及测量结果和日志审阅的证据路径。
功能、性能、DRC/LVS 和 PEX 接入分别记录各自结论。

Checkpoint/tag 需项目负责人明确批准，冻结记录与 tag 一一对应；不移动旧 tag 或改写其结论。
无需 checksum、hash 或完整性清单。

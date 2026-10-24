---
title: AI 自主电路与第一轮人工原理图美化 checkpoint
type: checkpoint
status: frozen
last_reviewed: 2026-10-25
authoritative_sources:
  - ../../config/final_design.json
  - ../../config/acceptance_results.json
  - ../verification/electrical-acceptance.md
  - ../verification/oa-delivery.md
---

# 冻结版本

Tag：`checkpoint/ai-autonomous-human-polish-r1-20261025`。

该 checkpoint 是 **AI 纯自主设计的电路 + 人工迭代一轮原理图美化后的结果**。
电路拓扑、器件尺寸和此前的电气迭代由 AI 自主完成；人工审阅和修改了 schematic、symbol 的图面。
本次按用户明确要求同步并建立 tag，作为后续降低功耗、消除过设计的起点。

# 本次同步

从 `MONOTONIC_SAR` OA 库捕获 28 个 cell 的 56 个视图，保留已有人工修改。
与同步前仓库比较，本次新增图面变化为：

- schematic：MONOTONIC_SAR、SAR_BOOST、SAR_BOOST_HI、SAR_CAPTURE_LATCH、SAR_CMP、
  SAR_DFFR、SAR_DFFS、SAR_FAST_SEQ、SAR_OUT、SAR_OUTPUT_FF、SAR_PHASE。
- symbol：SAR_SAMPLE。

SAR_SAMPLE 的 SampleB pin 横坐标由 −0.375 移至 −0.625，纵坐标保持 −0.875。
父级 SAR_FRONTEND 的旧线端未随之移动；Check/Save 后出现四条悬空警告。
在父级补接两坐标之间的短导线后，原 SampleB 连接恢复，四条警告消失。
该同步修正保持人工 symbol 图形和原电气功能。

原生图形、typed properties 和实例位置分别保存于各 view 的 `drawing.json`、`native.json`
与 schematic 的 `placement.json`。生成式 `functional.svg` 不代表本次人工修改后的实际图形。

# 核对结果与适用范围

- 对 11 个修改过的 schematic 及 SAR_SAMPLE 的直接父级执行 Check/Save：零错误；
  SAR_PHASE 保留两条并联驱动器 shorted-output 警告，其余零警告。
- 从当前 OA 重新导出的原生网表与 `final_stage1_06` 比较通过：
  29 个层次接口、1111 个展开 primitive 组的连接、模型和有效参数一致。
- 本次没有运行新性能仿真；此前同一电气设计的 20 项验收结果由上述等价核对关联。
- TT 总供电功耗约 193.7 mW，现有尺寸和功耗问题保留在此 checkpoint 中。
  20 项验收通过覆盖当时的功能、SNDR、时序和电压告警判据，未设功耗上限。
- CDAC 使用理想电容；没有完成版图、PEX 或失配 Monte Carlo 验证。

捕获与核对产物保存在项目 artifact 根目录的 `oa_delivery/checkpoint_20261025/`；
该目录包含原始捕获、Check/Save 结果、SampleB 补接记录和当前原生网表。
整体电气比较结果位于 `oa_delivery/electrical_comparison.json`。

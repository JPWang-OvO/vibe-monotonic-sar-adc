---
title: 工程目录与职责
type: architecture
status: current
last_reviewed: 2026-10-25
authoritative_sources:
  - ../../project.json
  - ../../regression/common/plans.py
  - ../../regression/common/runner.py
  - ../../regression/common/variants.py
---

# 工程目录与职责

Cell 表达实际功能，view 表达电路的不同表示。Flow 管理固定目标的规格、测试条件、测量和已批准 baseline。
Study 管理参数及拓扑探索，复用 flow 的验收约束。Batch 是计划展开后的一次实际运行。

```text
library/{blocks,systems,support}/<category>/<CELL>/<view>/
library/testbenches/{blocks,systems}/<target>/<TB_CELL>/<view>/
regression/{blocks,systems}/<target>/flows/<flow>/flow.json
regression/{blocks,systems}/<target>/flows/<flow>/{run.py,measure.py,README.md}
regression/{blocks,systems}/<target>/flows/<flow>/baselines/
regression/{blocks,systems}/<target>/studies/<study>/study.json
regression/{blocks,systems}/<target>/studies/<study>/run.py
regression/{blocks,systems}/<target>/analysis/
regression/common/
virtuoso/{oa,ade}/
physical/
config/{environments,processes}/
docs/{architecture,verification,notes,plans,history}/
```

同一目标的 PVT、频点、噪声与表示选择放在一个 flow 的 conditions 中。
`condition_defaults` 保存共同准备设置，`criteria_rules` 将条件相关门槛解析为每 case 的实际 criteria。
Flow 直接引用固定 TB；TB 的相对 include 决定当前电路依赖。

Study 用 `variables` 展开参数点，`edits` 指定实际 cell、实例与参数，`topology` 引用明确的拓扑生成规则。
变体只写入 batch 的输入目录。系统优化 study 引用正式 flow；独立表征 study 自带固定实验。
各 flow/study 的 `run.py` 绑定本目录计划，公共 runner 负责批次准备、提交和收集。
Flow 的 `measure.py` 定义测量及规格判定；独立表征 study 维护自己的测量。

`analysis/` 保存参考模型、系统波形计算及诊断；`acceptance/` 检查规格矩阵并输出候选报告。
原始波形、准备 deck 和工具输出保存在项目独立 artifacts。已批准的小型 baseline 与 flow 一起纳入 Git。

`virtuoso/oa` 捕获、回放和比较原生电路及图面。`physical` 负责已有版图的 DRC/LVS/PEX 与寄生 view 接入。
Environment 提供机器连接和安装路径；process 提供器件、模型 section 及 PDK 参数补全设置。

---
title: 2026-10-24 文件组织整理
type: migration
status: historical
last_reviewed: 2026-10-24
authoritative_sources:
  - ../../library/README.md
  - ../../regression/README.md
  - ../architecture/workspace.md
---

# 脚本归属

开发时保留了大量一次性候选生成脚本，`regression/` 顶层共有 89 个 Python 文件。
用户批准清理生成器、按目标归位保留工具，并要求当前文档直接描述可用结构。

删除 75 个一次性脚本：顶层 65 个 `build_*`、系统行为源生成器、初始化和配置补丁、
固定条件探查脚本，以及由公共重新测量入口覆盖的诊断脚本。
已纳入 Git 的电路源、118 个 flow 和既有仿真产物保留。

19 个模块按以下职责归位：

| 目标目录 | 保留内容 |
|---|---|
| `regression/systems/monotonic_sar/analysis/` | 参考模型、FFT、系统与模块测量、Python 验证、绘图、状态汇总及常用诊断，共 13 个模块 |
| `regression/systems/monotonic_sar/acceptance/` | DUT 边界检查与正式报告 |
| `regression/systems/monotonic_sar/studies/wait_gate/` | 等待门内部节点诊断 |
| `regression/blocks/sar_sampler/studies/aperture/` | 孔径与关断误差研究 |
| `regression/blocks/tsmc18_devices/flows/qualification/` | PDK 参数补全资格测试 |
| `virtuoso/oa/` | 标准单元原生导出 |

命令入口显式调用 `main()`。服务器打包包含新的 analysis 包；远端诊断携带所用的局部测量函数。
PDK 资格测试的标准反相器来自受维护的 library 源。

检查通过：19 个迁移模块导入、15 个命令入口帮助、远端诊断语法、独立服务器测量包导入、
工程检查和 Python 参考模型验证。参考模型覆盖 30 个固定输入、两个频点及 FFT 已知信号；
四个数值模块的函数与类定义保持一致。

# View 命名

80 个 cell 中的 176 个 view 使用表示形式作为前缀，已有 schematic、symbol、veriloga 和 pex 保持名称。
迁移规则如下，目录、cell 索引、相对 include、flow 绑定和当前设计配置同步更新：

| 原名称 | 当前名称 |
|---|---|
| `transistor`、`spectre` | `netlist` |
| `fast`、`fast36` 等文本变体 | `netlist_fast`、`netlist_fast36` 等 |
| SAR_CMP、SAR_ASYNC 的 `timed` | `veriloga_timed` |

原生 OA schematic/symbol、既有批次 deck、日志与测量结果保持原样。
`acceptance_results.json` 中的 view 标识属于实际完成的批次记录；
`final_design.json` 与各 flow 使用当前目录名。

本地比较覆盖 216 份网表，连接、模型、参数和执行语句保持一致；相对 include 均能解析。
118 个 flow 的 247 个 condition 依赖展开成功。正式 20 个 case 的输入网表、激励、
模型入口、仿真设置、测量窗口和验收判据在路径对应后保持一致。
本次验证使用本地依赖展开与语义比较，没有重新调用 PDK、启动 Spectre 或修改 OA。

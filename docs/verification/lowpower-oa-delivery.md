---
title: 当前 ADC 原生 OA 及层次清理
type: verification-method
status: current
last_reviewed: 2026-10-25
authoritative_sources:
  - ../../config/design.json
  - ../../virtuoso/oa/adc_compare.py
  - ../../regression/systems/monotonic_sar/flows/acceptance/baselines/accepted.json
---

# 当前 OA 层次

顶层为 `MONOTONIC_SAR/schematic`，库路径由本机环境配置固定。
当前包含 15 个功能 cell，直接引用 11 个 `standard_cells` 标准单元。
标准单元转接层、序列寄存器转接层、独立延时链及组合等待门已并入实际使用它们的模块。
采样保护统一为 `SAR_SAMPLE_GUARD`。OA 中已删除 14 个废弃 cell，包括旧高压自举候选。

写入前捕获已有视图并核对电气与图面差异。15 个功能 schematic 按实际 master 端口收紧布局：
串联级对齐，比较器保持差分对称，复位反相器转向寄存器复位端，顶层逐位控制排为三列。
连线合并共线段、去除无用途支段，每个连续总线段保留一处有序网名；输入、输出和电源接口分组放置。
顶层未使用的 `Bp<0>`、`Bn<0>` 保留原生 noConn 标记。

`SAR_BIT` symbol 显示锁存输出后的互补反相器；`SAR_ASYNC` 标明四级反馈延时、两级完成延时及
NOR/AOI211 控制逻辑；`SAR_PHASE` 标明锁存门控。三个 symbol 的端口位置与端序保持一致，
其父级已重新 Check/Save。原生快照、绘图、设计语义、SVG 及导出网表已同步到各 cell。

# 验证范围

15 个功能 schematic 的 Check/Save 均为 0 error、0 warning，实例端口连接读回一致。
清理前后源网表通过以顶层端口为锚点的图同构比较，检查器件模型、端序、有效参数和倍乘。
原生 OA 网表与当前源的 26 个层次接口、1,264 组底层器件连接及有效参数逐项一致。
源网表和原生网表比较均无缺失或新增器件。

本次没有重新仿真。系统性能依据仍为 flow baseline 中的 20 项已有实测；
器件层次和内部命名变化后，重新运行的瞬态噪声数值可能不同。
本次等价验证确认电气结构，未产生新的噪声样本。

核对产物位于项目 artifact 根目录的 `restructure_20261025/`：
源等价结果为 `source_equivalence.json`，最终 OA 比较为 `electrical_comparison.json`；
紧凑图面的检查、原生网表及截图位于 `compact_native/`，symbol 修改与回读位于 `compact_symbols/`。
性能结果见[电气验收](lowpower-acceptance.md)。

# 后续核对

```text
python -m virtuoso.oa.adc_compare --qualification <已有PDK资格批次> --native <原生导出目录>/netlist --run-id <核对产物名称>
```

资格批次仅提供与实际几何匹配的 PDK 回调结果。尺寸改变时须重新取得对应参数。
手工 OA 改动先捕获和审阅，再同步电路源；回放与视图维护见 [OA 工具](../../virtuoso/oa/README.md)。

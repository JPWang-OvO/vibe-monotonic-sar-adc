---
title: 当前 ADC 原生 OA 与源核对
type: verification-method
status: current
last_reviewed: 2026-10-26
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
其父级已重新 Check/Save。

2026-10-26 图面快照包含 SAR_CMP、SAR_ASYNC、SAR_STARTUP、SAR_BOOST、顶层 schematic，
以及 SAR_BIT、SAR_SAMPLE symbol，共七个 view；调整范围均为图形对象。
当前展示以各 view 的 `native.json` 和 `drawing.json` 为准；`functional.svg` 保留生成时的图形源。

在该图面基础上，SAR_BOOST 的 Gate 复位支路补齐栅接 VDD 的串联 NMOS，下管由 SampleB 控制。
SAR_BIT 的 strength 改为末级实际倍乘，最小为 1。参数调整保持 BIT 和顶层的图形对象，
BOOST 仅调整复位支路及邻近 Gate 引脚。

# 验证范围

修改后的 BOOST、BIT 和顶层已执行 Check/Save，实例连接及参数读回一致。
单独重定义 strength 前后的 1,264 组底层器件连接及有效参数完全相同，现有 finger/multi 保持原值。
补齐两个采样支路的复位串管后，原生 OA 网表与当前源的 26 个层次接口、1,266 组底层器件
连接及有效参数逐项一致；BOOST 与父级图面已审阅。

补齐串联复位管后的电路已通过全部 20 项系统验收，结果保存于正式 flow baseline。
比较器与分频器的独立功能验收各有 5/5 项 PVT 条件通过。

核对产物位于项目 artifact 根目录的 `reset_strength_20261026/`：
`manual/` 保存电气修改前的手工视图，`strength_check.json` 保存参数重定义比较，
`electrical_comparison.json` 保存当前源与 OA 的比较；原生导出位于 `native_export/`，截图位于同级目录。
性能结果见[电气验收](lowpower-acceptance.md)。

# 后续核对

```text
python -m virtuoso.oa.adc_compare --qualification <已有PDK资格批次> --native <原生导出目录>/netlist --run-id <核对产物名称>
```

资格批次仅提供与实际几何匹配的 PDK 回调结果。尺寸改变时须重新取得对应参数。
手工 OA 改动先捕获和审阅，再同步电路源；回放与视图维护见 [OA 工具](../../virtuoso/oa/README.md)。

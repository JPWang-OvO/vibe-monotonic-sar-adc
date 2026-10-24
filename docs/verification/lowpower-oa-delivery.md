---
title: 低功耗 ADC 原生 OA 交付
type: verification-method
status: active
last_reviewed: 2026-10-25
authoritative_sources:
  - ../../config/lowpower_design.json
  - ../../config/acceptance_lowpower_results.json
  - ../../virtuoso/oa/adc_update_lowpower.py
  - ../../virtuoso/oa/adc_compare.py
---

# 当前层次与图面

库名和路径沿用本机环境配置，顶层为 `MONOTONIC_SAR/schematic`。
当前验收层次包含 27 个自研 cell；低功耗改版更新 22 个 schematic 和 6 个 symbol，
5 个 schematic 的电气定义和图面保持原值。
写入前逐个比较全部维护视图的原生对象和图面，并保存 `lowpower_oa_delivery/before_update.json`。

仅改变尺寸的单元保留原实例坐标、导线和标签。拓扑或 master 改变的单元按实际 native symbol 端口重新布线。
更新的功能图为 SAR_SAMPLE, SAR_FRONTEND, SAR_PHASE, SAR_INV, SAR_FAST_SEQ, SAR_HANDSHAKE，全部保持原 pin 坐标；层次与端口接口沿用现有总线约定。
修改视图及受影响顶层共 29 张原生截图已审阅，位于 `lowpower_oa_delivery/native_previews/`。
同目录另存顶层及比较器的四张局部图。
原设计与人工图面保存在 `checkpoint/ai-autonomous-human-polish-r1-20261024`；此前交付记录见 [原 OA 记录](oa-delivery.md)。

# 核对结果

27 个 schematic Check/Save 均为零错误、零警告。
原生网表与已验收低功耗电路的 38 个层次接口一致，
展开后的 1264 组 primitive 连接、模型和有效参数一致；缺失、增加及参数改变项均为零。
逐项文件保存在 `lowpower_oa_delivery/checks.json`、`electrical_comparison.json` 和各 cell 的 readback JSON。
20 项系统结果见 [低功耗验收](lowpower-acceptance.md)。

# 复现

使用配置好的 Virtuoso Bridge Python，在工程根目录运行。`BATCH` 为已验收的低功耗批次，
`ARTIFACTS` 为本机解析的产物根目录。

```text
python -m virtuoso.oa.adc_update_lowpower --batch BATCH --prepare-only
python -m virtuoso.oa.adc_update_lowpower --batch BATCH
python -m virtuoso.oa.adc_compare --batch BATCH --native ARTIFACTS/lowpower_oa_delivery/native_netlist/netlist --run-id lowpower_oa_delivery --design-config config/lowpower_design.json
```

写入要求同一 DUT 的全部 20 项通过，并检查当前 OA 与保存状态一致。
源码的 circuit/native/drawing、CDF 与原生导出同步保存在各 cell 的相应 view；大型截图和波形留在产物目录。

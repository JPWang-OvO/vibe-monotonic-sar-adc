---
title: Virtuoso Bridge 接口问题
type: note
status: active
last_reviewed: 2026-10-21
authoritative_sources:
  - ../../physical/run.py
---

# Virtuoso Bridge 接口问题

## 2026-10-21：CalibreView 导入受活动窗口库影响

- 状态：Bridge 中未修复；项目导入入口已显式绑定库上下文。
- 观察环境：Virtuoso Bridge 0.8.0、IC23.1、Calibre 2025.2，profile 为 `prime-voyager_ciw01`。
- 接口：`layout.import_calibreview(library=..., schematic_library=...)`。
- 预期：输出库和 schematic 参考库使用调用参数。
- 实际：当 `mgc_eview_globals` 的 `outputLibrary`、`schematicLibrary` 为空，且活动编辑窗口属于其他库时，导入使用活动窗口的库。原生日志报告完成，Bridge 随后的目标 view 检查失败。
- 复现依据：请求和 setup 文件均指定 `IC_TEMPLATE`，活动窗口属于 `RECONFIGURABLE_ADC`；本次 `INV/calibre` 被创建到后者。其 78 个实例、四个端口、创建时间与本次导入一致，误建 cell 已删除。
- 机制：Bridge 将库名写入 setup 文件，但启动 vendor 导入前只设置 `schViewNames`。当前 Calibre 集成仍从空的库全局变量和活动窗口决定库上下文。
- 项目处理：调用前将两个库全局变量绑定到请求值，结束后恢复原值。原生 API 超时时保留尚在使用的上下文，供调查正在执行的导入。共享 Bridge 源码保持只读。
- 验证：活动窗口仍在其他库时，正确导入 `IC_TEMPLATE/INV/calibre`，78 个实例、45 个网络、四个端口；原生日志 0 errors、0 warnings。随后从该 view 原生导出并发布 PEX 网表。
- 证据：项目 artifact 根目录 `calibre_restore_20261021/` 中的 `run.json`、`ciw-import-diagnostic.log`、原始导入工作目录、`calibreview.json`、`calibreview.log` 和 `oa-netlist/`。

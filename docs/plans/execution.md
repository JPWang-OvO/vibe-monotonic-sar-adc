---
title: ADC 执行状态与时间预算
type: plan
status: active
last_reviewed: 2026-10-23
authoritative_sources:
  - ../../config/run_budget.json
  - ../../config/architecture.json
  - ../../regression/systems/monotonic_sar/analysis/validate_python.py
---

# 执行窗口

开始：2026-10-23 06:40:35 UTC（日本时间 15:40:35）。
用户于 2026-10-23 18:32:32 UTC 将时间限制延长至目标完成；`deadline_utc` 设为 null。
每个仿真仍使用 8 线程，总计最多 14 worker；每个作业保留其 flow 规定的执行时限。
用户已授权自主审阅 preview、启动测试、修改设计和重跑受影响条件。

# 阶段

1. Python 电荷模型与 FFT：已通过 30 个代表性及边界输入和两个指定频点。
2. 模块化 Verilog-A：理想电荷及加入延迟的两个频点均已通过逐码、逐位和时序对齐。
3. TSMC18 primitive enrichment：2 V/5 V MOS 映射、CDF 回调、原生导出、尺寸变化及反相器角落资格测试已通过。
4. 晶体管模块及混合替换：已完成全部有源功能替换，功能、逐位建立、输出保存/保持及额定条件通过。
5. 完整系统 20 个正式 case：`final_*_06` 同一电路全部通过。两项 FF/125 °C 无噪声测试因磁盘配额中断，迁移旧波形后以相同输入和判据重跑通过。
6. OA schematic/symbol：完成 28 个自研 cell；原生连接、阵列展开网表、总线位序及图面审阅通过，见 [OA 交付](../verification/oa-delivery.md)。

现有 `artifacts/pdk_smoke_20261023` 属于任务开始前的环境预检，只作为环境证据。
新仿真批次存放于运行时解析的 artifact 根目录。原始波形保留在服务器。

---
title: ADC 执行状态与时间预算
type: plan
status: active
last_reviewed: 2026-10-23
authoritative_sources:
  - ../../config/run_budget.json
  - ../../config/architecture.json
  - ../../regression/systems/monotonic_sar/validate_python.py
---

# 执行窗口

开始：2026-10-23 06:40:35 UTC（日本时间 15:40:35）。
截止：2026-10-23 18:40:35 UTC（日本时间次日 03:40:35）。恢复任务沿用该截止时间。
预留末尾 15 分钟收集结果；每个仿真使用 8 线程，总计最多 14 worker。
用户已授权自主审阅 preview、启动测试、修改设计和重跑受影响条件。

# 阶段

1. Python 电荷模型与 FFT：已通过 30 个代表性及边界输入和两个指定频点。
2. 模块化 Verilog-A：理想电荷及加入延迟的两个频点均已通过逐码、逐位和时序对齐。
3. TSMC18 primitive enrichment：2 V/5 V MOS 映射、CDF 回调、原生导出、尺寸变化及反相器角落资格测试已通过。
4. 晶体管模块及混合替换：五个 PVT 条件的功能、逐位建立、输出保存/保持及额定电压已通过开发检查；SS125 的采样周期偏差仍在修正。
5. 完整系统 20 个正式 case：首轮 TT 无噪声通过 1/2；时钟修改后的第二轮 TT 无噪声正在执行。其后依次执行 TT 有噪声、SS/FF 极端温度。
6. OA schematic/symbol：全部电气验收通过后进入；当前未进入。

现有 `artifacts/pdk_smoke_20261023` 属于任务开始前的环境预检，只作为环境证据。
新仿真批次存放于运行时解析的 artifact 根目录。原始波形保留在服务器。

---
title: 单调 SAR ADC 开发验证记录
type: note
status: active
last_reviewed: 2026-10-23
authoritative_sources:
  - ../../config/run_budget.json
  - ../../regression/systems/monotonic_sar/flows/timed/flow.json
  - ../../regression/systems/monotonic_sar/flows/mixed_cmp/flow.json
  - ../../config/processes/tsmc18_callbacks.json
---

# 已完成的层次

本次执行从 2026-10-23 06:40:35 UTC 开始，截止时间为同日 18:40:35 UTC。
当前结果均为开发候选。尚未进入完整晶体管系统的正式 20-case 验收，也未生成设计 OA。

| 批次 | 结果与范围 |
|---|---|
| python_reference | 30 个代表性及边界输入的电荷、位序、码制检查通过；两个 256 点正弦与独立量化参考一致；FFT 已用已知谐波和 Nyquist 信号校验 |
| pdk_qualification_02、pdk_qualification_resize | 6 个 NMOS/PMOS 单指、多指、倍乘实例补全；72 项参数回填；尺寸变化后重新计算，原生标准单元参数保持 |
| inv_enriched_01 | 1.8 V 反相器 TT/25、SS/125、FF/−40 的逻辑高低电平通过；这是初版简单反相器的验证 |
| va_charge_01 | 两频点各 256 个连续码逐码一致，十次比较和逐位顶板电压符合模型 |
| va_timed_01 | 加入 600 ps 比较及 600 ps 建立预算后通过；SNDR 61.1248/61.2598 dB，最小转换余量 3.7295 ns |
| cmp_tt_03 | 晶体管比较器及自偏置通过 5 档共模、±0.25/±1 LSB 的 20 次比较；最慢 1.1884 ns，Bias 约 0.9266 V |
| mixed_cmp_01 | 替换比较器和偏置后两频点通过，SNDR 61.1248/61.2598 dB，最小转换余量 3.0090/3.0324 ns |
| front_modules_02 | 分频器功能通过，采样窗约 3.9785 ns；内部标准单元仍有约 1.99 V 的瞬态 SOA 提示。5 V 采样器无 SOA 提示，但建立和关断误差未通过 |
| pdk_5v_qualification | 新增 nmos5v/nch_5、pmos5v/pch_5 映射；6 个原型、72 项回填，原生导出、尺寸和连接检查通过 |

比较器混合批次使用的行为时钟边沿为 1 ps，引起复位节点负向耦合及 SOA 提示。
接下来的晶体管控制替换将检查真实驱动边沿。功能通过不代表额定电压检查已完成。
早期理想采样电导模型出现数值误差，已改用显式保存顶板电荷的模块化前端行为模型；失败批次保留。

# PDK 参数约定

原生 CDF 回调及读回显示：**Spectre `w` = CDF `wf` = 总沟道宽度**，
CDF `w` = `wf/fingers`；Spectre `nf` 对应 `fingers`，`m` 对应 `simM`。
例如 `w=8u nf=32` 的单指宽度是 0.25 µm。
早期源注释误将 Spectre W 称为单指宽度，现已纠正；已通过的比较器实际网表尺寸保持不变。
补全器保护 Spectre W/L/nf/m 和模型，额外检查 CDF 总宽与单指宽关系。

缺少 `lxCDFCallbackParams`、`pdkVersion` 的适配仅存在于本项目。
处理流程为：Spectre primitive 清点 → 独立临时 OA 原型 → 已核对的 PDK CDF 回调 → 原生导出
→ `pdk.scs` 实例级 alter → 重新读回参数和连接。临时库在导出后删除。
重复参数报告和批次结果压缩后传回本地，原始波形留在服务器。

# 当前问题

5 V 采样器首版自举启动约消耗采样窗的一半，关断差分耦合达到数 mV。
正在验证加大自举驱动后的建立过程，并依据实测耦合选择补偿。
异步控制、DAC 驱动和输出寄存器正在进入混合系统验证。
全部有源功能替换、正式噪声及 PVT 验收、功耗分项和 OA 收尾尚待完成。

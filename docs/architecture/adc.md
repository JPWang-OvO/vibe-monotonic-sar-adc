---
title: 单调切换 SAR ADC 接口与设计预算
type: architecture
status: active
last_reviewed: 2026-10-26
authoritative_sources:
  - ../../config/architecture.json
  - ../../config/design.json
  - ../../regression/systems/monotonic_sar/flows/acceptance/specification.json
  - ../../library/systems/monotonic_sar/MONOTONIC_SAR/cell.json
  - ../../regression/systems/monotonic_sar/analysis/model.py
---

# 架构和共同约定

本设计复现 Liu 等人 2010 年 JSSC 论文的顶板采样、向下单调切换和异步比较完成握手。
目标工艺为 TSMC180，电源及参考为 1.8 V，输入共模为 0.9 V。
论文的 PMOS 输入动态比较器采用串联偏置 PMOS 稳定输入对电流；偏置在本项目内由晶体管电路产生。
采样实现采用单级自举 NMOS 开关。Gate 复位支路按论文 Fig. 7(a) 使用两只串联 NMOS：
上管栅接 VDD，下管栅接 SampleB，中间节点为 ResetMid；两管均为 2/0.18 µm、nf=1、m=1。

每侧 CDAC 的权重为 256、128、64、32、16、8、4、2、1，加一个保持接 VREFP 的单位电容。
单位电容为论文规模的 4.8 fF，每侧总电容 2.4576 pF。
自举使用 2 V MOS 和 500 fF 电容；采样 NMOS 的 W/L=16/0.18 µm、nf=4。
采样时所有底板接 VREFP，顶板跟踪输入；Sample 下降沿为采样时刻。
第一次比较直接判定采样差分。随后将较高电位侧当前权重的底板由 VREFP 切至 VREFN。
第十次比较只决定 LSB。两个顶板的总电荷分别保持不变。

比较 `Vp >= Vn` 对应判决 1。理想模型在严格相等时输出 1；Python 用有理数运算保持边界一致。
输出为 offset binary，接口为 `D<9:0>`，`D<9>` 为 MSB，差分零对应 512，差分正满量程饱和为 1023。
晶体管比较器在零差分附近的决策属于模拟误差预算，必须同时检查完成时间。

| 模块 | 信号与含义 |
|---|---|
| SAR_PHASE | Clks 250 MHz 输入；Sample 高电平为采样，周期 20 ns，高电平标称 4 ns |
| SAR_SAMPLE | Vin 至 Top 的自举采样开关；Sample/SampleB 为互补控制 |
| SAR_CDAC | Vp/Vn 为顶板；Bp<9:1>、Bn<9:1> 为实际底板电压 |
| SAR_CMP | ClkC 高电平复位，低电平比较；复位 Outp/Outn 同为高，完成后互补；Valid 高表示完成 |
| SAR_ASYNC | Sample 结束后启动比较；每次 Valid 上升推进 Ck<9:0> 中一位，复位比较器并等待 DAC 建立；十位后产生 Done |
| SAR_BIT | Capture 低时锁存器透明且两侧底板预充；Capture 上升后保持 Outp 判决，Bp/Bn 仅一侧下降；Sample 为保留的未用接口 |
| SAR_OUT | Done 上升锁存十位结果；输出保持至下次 Done |
| SAR_BIAS | 由 VDD/VSS 产生比较器 PMOS 电流源的 Bias |

全部数字节点电源域为 VDD/VSS。最终输入及偏置节点的工作范围按晶体管实测记录。
算法参考模型保存在 analysis；当前正式电路为晶体管与标准单元实现。

## 当前低功耗参数

当前顶层与验收入口由 `config/design.json` 固定，各 cell 的 `netlist/` 保存当前实现，完整验收结果见
[低功耗验收](../verification/lowpower-acceptance.md)。尺寸选择与对照结果见
[尺寸收敛记录](../verification/lowpower-sizing.md)。此前实现保存在
`checkpoint/ai-autonomous-human-polish-r1-20261024`。

| 功能 | 实现与尺寸 |
|---|---|
| 五分频与启动 | 五级环形寄存器使用原生 DFCNQD1/DFSNQD1；VDD 充电产生上电复位，Clks 低电平锁存复位释放后门控时钟；门控及时钟路径使用 INVD2 |
| 采样相位驱动 | INVD2、INVD8 两级；互补控制使用单级 INVD4 |
| 比较器 | PMOS 输入对 W/L=4/0.18 µm；偏置 PMOS 6/0.36 µm、nf=3；时钟 PMOS 6/0.18 µm、nf=3；NMOS 再生管 2/0.18 µm、复位管 1/0.18 µm；输出感测使用 INVD1/INVD2 |
| 偏置 | 二极管连接 PMOS 0.25/0.36 µm；栅接 VDD 的 NMOS 0.3/8 µm；Bias 对地 100 fF |
| 异步等待 | Valid 直接推进序列寄存器；前五位保留四级 INVD1 反馈建立延时；AOI211D1 合并等待条件，INVD2 驱动比较器时钟 |
| 逐位保存及 DAC | LNQD1 锁存判决，ND2 选择底板；MSB 前级 N/P=8/16 µm、末级 N/P=32/96 µm，其余位按电容权重缩放，最小前级为 0.5/1 µm、末级为 1/3 µm |
| 采样保护 | 两级反相器与保持逻辑，延迟节点对地 15 fF；关断建立由实际码、比较顺序及 SNDR 检查 |
| 结果保存 | 原生 DFQD1 由 EOC 触发；每位后接倍率 1/2 两级输出缓冲及 10 fF 负载 |

五分频器、上电复位、输出寄存器和内部驱动是本项目为固定 TB 边界补全的实现。
相位和异步驱动按实际扇出选型，DAC 驱动按各位电容负载及下一次比较前的建立时间选择。
`SAR_BIT.strength` 表示末级 MOS 的实际倍乘，最小档为 1；bit9 至 bit0 依次为
32、16、8、4、2、1、1、1、1、1。前级倍乘为 `max(1,strength/2)`，各管 finger 保持原值。
2026-10-26 的 strength 重定义保持全部原有有效尺寸；新增复位串管后的性能待重新验证。
允许短时瞬态 SOA 电压超限及 2 V 自举器件的 G-B 超压，警告保留在结果中。
这些电压提示用于观测；候选选择依据系统功能、SNDR、转换时间和功耗。

# 系统约束与尺寸选择

LSB 为 3.515625 mV。量化噪声约为 0.289 LSB RMS，−1 dBFS 输入差分 RMS 为 1.1344 V。
采样周期为 20 ns，采样窗标称 4 ns；十次比较和唯一 EOC 必须在下一次采样开始前完成。
输出寄存器在下一采样窗口继续保持此前结果，统一在采样结束后 18 ns 读取，保持至下一次 EOC。
原两频点的 SNDR 门槛分别为 57.0/56.5 dB；TT 核心功耗目标为 ≤3 mW，包含参考供电并扣除输出缓冲。

局部 RC、逐位顶板残差、比较器动态误差和完成余量用于定位限制支路。
尺寸调整通过真实输出码、原系统 SNDR 及 PVT 条件判断，不另设固定边沿、顶板残差或额外周期裕量门槛。
Python 算法参考模型保留电荷守恒与原始输出码约定。

# 正式验收激励

VDD 从 0 V 在 10 ns 内线性升至 1.8 V；外部时钟在 20 ns 开始，周期 4 ns，
上升/下降时间各 20 ps，平台高电平宽 1.98 ns，按 50% 电平交点测得占空比 50%。
晶体管分频器通过自身上电复位启动；正式矩阵覆盖 TT/25°C 和 SS/FF、−40/125°C，各有/无噪声两频点共 20 项。
输出每位负载为 10 fF。丢弃前 16 个转换，在其后连续 256 个周期的采样结束后 18 ns 读取输出。
数字低电平判据为 ≤0.18 V，高电平为 ≥1.62 V，中间电平计为无效位。
正式测量设置已固定于 `regression/systems/monotonic_sar/flows/acceptance/specification.json`：瞬态噪声 1 Hz–50 GHz、seed=1，
输出使用两级 SAR_DRIVE（scale=1/2）。频带依据和功耗边界见 `docs/verification/acceptance-method.md`。

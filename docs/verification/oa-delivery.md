---
title: ADC 原生 OA 交付与复现
type: verification-method
status: active
last_reviewed: 2026-10-24
authoritative_sources:
  - ../../config/final_design.json
  - ../../config/acceptance_results.json
  - ../../virtuoso/oa/adc_source.py
  - ../../virtuoso/oa/adc_build.py
  - ../../virtuoso/oa/adc_compare.py
---

# 原生库与源文件

交付库名为 `MONOTONIC_SAR`，包含 28 个自研 cell 的 schematic 和 symbol。
目标路径由本机 `config/environments/tsmc18.local.json` 的 `oa_library_path` 指定：

```text
<oa-library-path>
```

原生库绑定 `tsmc18`，PDK 器件和标准单元引用其既有库。
本次 CIW 使用的 `cds.lib` 映射及原映射记录位于产物目录 `oa_delivery/library_mapping.json`；
其余库的映射保持原值。切换 CIW 时，按该记录加载映射后打开顶层 `MONOTONIC_SAR/schematic`。

每个 cell 在 `library/` 中保存以下文件，`cell.json` 声明对应 view：

| 文件 | 用途 |
|---|---|
| `schematic/circuit.json` | 模型、参数、端序、连接及阵列成员映射 |
| `schematic/placement.json` | 实例坐标与朝向 |
| `schematic/native.json`、`drawing.json` | 从 OA 回读的电气对象及绘图对象 |
| `schematic/netlist.scs` | 原生 Spectre 导出中的本 cell 定义 |
| `symbol/native.json`、`drawing.json` | 原生 symbol 的端口、图形和标签 |
| `symbol/functional.svg` | 与原生功能图共用绘图定义的预览 |
| `cdf.il`（含参数的 cell） | 六个参数化 cell 的 CDF 保存结果 |

# 图面与阵列

Symbol 按实际电路功能重新绘制：顶层展开采样、CDAC、比较器、逐位锁存、
输出寄存器和异步控制；比较器标明前级完成检测与输出缓冲；锁存器画出传输门反馈。
门形参考实际标准单元几何，主要路径采用直线和短正交连接，必要交叉使用跨线弧。

Schematic 将同 master、同有效参数的重复结构改为以下实例阵列。
不同驱动尺寸的逐位控制保持独立实例，以保留已经验收的建立时间配置。

| Cell | 阵列 | 连接方式 |
|---|---|---|
| SAR_PHASE | `I_pre<7:0>`、`I_final<63:0>` | 并联驱动，共享输入和输出 |
| SAR_PHASE | `I_ring<3:0>` | 逐级数据连接，广播时钟与复位 |
| SAR_ASYNC | `I_seq<9:0>` | 逐位序列连接，广播控制 |
| MONOTONIC_SAR | `I_out<9:0>` | 十位数据及输出逐位连接，广播完成信号 |
| MONOTONIC_SAR | `I_bit<1:0>` | 两个相同尺寸的低位控制单元 |

阵列网名保留原来的标量命名，并在导出后逐成员展开比较。
悬空标记按展开后的标量连接计数；仅出现在总线中的未使用低位底板输出单独引出命名短线。

# 核对结果

28 个 schematic 的 Check/Save 均为零错误。27 个 cell 为零警告；
SAR_PHASE 的两条 shorted-output 警告来自上述两组并联驱动器。
这些输出共同驱动同一个负载，与验收网表中的显式并联实例一致。

原生网表与 `final_stage1_06` 的已验收电路完成以下比较：

- 29 个层次定义的端口顺序一致，包括引用的标准反相器。
- 阵列展开后的 1111 组 primitive 连接、模型和有效参数一致。
- 缺失、增加及参数改变的 primitive 组均为零。

原生图面截图审阅待 Bridge 连接恢复后完成。SVG 功能图已检查。
20 项电气验收结果见[电气验收](electrical-acceptance.md)；图面重排保持已验收电路的电气定义。

# 复现命令与产物

在工程根目录使用已配置的 Virtuoso Bridge Python 环境。`BATCH` 指向
产物根目录下的 `final_stage1_06`，`ARTIFACTS` 为运行时解析的产物根目录。
首次构建使用新的目标库；已有库重绘会先比较原生回读与保存版本，发现手工编辑时停止。

```text
python -m virtuoso.oa.adc_build --batch BATCH --prepare-only
python -m virtuoso.oa.adc_redraw --batch BATCH
python -m virtuoso.oa.adc_compare --batch BATCH --native ARTIFACTS/oa_delivery/native_netlist/netlist
python -m virtuoso.oa.adc_render --batch BATCH --inkscape INKSCAPE_EXECUTABLE
python -m regression.common.check
```

单独重绘指定 schematic 可使用 `adc_redraw --schematics-only --cells CELL ...`。
`oa_delivery/electrical_comparison.json` 保存等价比较结果，`redraw_checks.json` 保存逐 cell 检查结果。
SVG 渲染及原生窗口截图分别放在 `symbol_previews/` 和 `native_previews/`，大型产物留在 Git 外。

# 适用范围

本次完成原理图级实现与固定条件的电气验收。TT 总供电功耗约 193.7 mW，包含输出缓冲。
CDAC 使用理想电容；固定 seed=1 的瞬态噪声通过结果不代表统计良率。
本次未完成版图、寄生提取或 Monte Carlo 失配验证。

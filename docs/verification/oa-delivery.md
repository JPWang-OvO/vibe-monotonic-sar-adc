---
title: ADC 原生 OA 交付与复现
type: verification-method
status: active
last_reviewed: 2026-10-24
authoritative_sources:
  - ../../config/final_design.json
  - ../../config/acceptance_results.json
  - ../../virtuoso/oa/adc_source.py
  - ../../virtuoso/oa/adc_buses.py
  - ../../virtuoso/oa/adc_build.py
  - ../../virtuoso/oa/adc_schematic.py
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
| `symbol/functional.svg` | 生成式功能图的预览；手工图形保存在 native/drawing 中 |
| `cdf.il`（含参数的 cell） | 六个参数化 cell 的 CDF 保存结果 |

# 图面与阵列

Symbol 按实际电路功能重新绘制：顶层展开采样、CDAC、比较器、逐位锁存、
输出寄存器和异步控制；比较器标明前级完成检测与输出缓冲；锁存器画出传输门反馈。
门形参考实际标准单元几何，主要路径采用直线和短正交连接，必要交叉使用跨线弧。
SAR_SAMPLE 展示两级升压器、Lift 中间节点、Gate 驱动和 Vin 到 Top 的 NMOS 采样通路。

锁存器和触发器沿数据流排列输入级、主级、从级与输出级，反馈放在对应级上方，
时钟与复位置于所属功能组。比较器采用左右对称的输入、再生和复位支路，
两条交叉耦合线在交叉处不连接；升压器按启动、预充电、电容、传输和复位分区。
VDD/VSS 使用短线标签，动态体端电位就地标注。局部数据和反馈用连续导线表达，
合并共线段并去除无用途支段；内部时钟分发采用命名网络。

Schematic 将同 master、同有效参数的重复结构改为以下实例阵列。
不同驱动尺寸的逐位控制保持独立实例，以保留已经验收的建立时间配置。

| Cell | 阵列 | 连接方式 |
|---|---|---|
| SAR_PHASE | `I_pre<7:0>`、`I_final<63:0>` | 并联驱动，共享输入和输出 |
| SAR_PHASE | `I_ring<3:0>` | 逐级数据连接，广播时钟与复位 |
| SAR_ASYNC | `I_seq<9:0>` | 逐位序列连接，广播控制 |
| MONOTONIC_SAR | `I_out<9:0>` | 十位数据及输出逐位连接，广播完成信号 |
| MONOTONIC_SAR | `I_bit<1:0>` | 两个相同尺寸的低位控制单元 |
| SAR_BIT | `I_select<1:0>`、`I_buf0<1:0>`、`I_buf1<1:0>` | 正负底板控制及两级驱动 |
| SAR_FRONTEND | `I_sample<1:0>`、`C_cross<1:0>` | 差分采样器及交叉补偿电容 |
| SAR_CMP | `I_out<1:0>`、`I_out1<1:0>`、`I_out2<1:0>` | 差分输出的三级缓冲 |
| SAR_CDAC | `C_weight9<1:0>` 至 `C_weight1<1:0>`、`C_dummy<1:0>` | 每个权重的正负电容配对 |
| SAR_PHASE、SAR_STARTUP | `I_por<1:0>` | 两级 POR 缓冲 |
| SAR_ASYNC | `I_cp<1:0>` | 公共时钟的两级缓冲 |
| SAR_SAMPLE_GUARD2 | `I_d<1:0>` | 两级延时缓冲 |

顶层输出接口为 `D<9:0>`，`D<9>` 为 MSB。CDAC 和前端的底板接口为
`Bp<9:1>`、`Bn<9:1>`；异步控制器输出为 `Ck<9:0>`。
顶层内部的锁存结果、底板和逐位控制网络分别使用 `Q<9:0>`、`Bp<9:0>`、
`Bn<9:0>`、`Ck<9:0>`；相位发生器的环形状态使用 `R<4:0>`。
连续位段按实际顺序压缩为总线，差分支路使用有序网名列表，公共控制使用广播连接。
每个阵列保存原实例到成员的映射，原生网表逐成员展开核对。
悬空标记按展开后的连接计数；未使用的 `Bp<0>`、`Bn<0>` 由一个双实例 noConn 阵列终结。

# 核对结果

28 个 schematic 的 Check/Save 均为零错误。27 个 cell 为零警告；
SAR_PHASE 的两条 shorted-output 警告来自上述两组并联驱动器。
这些输出共同驱动同一个负载，与验收网表中的显式并联实例一致。

原生网表与 `final_stage1_06` 的已验收电路完成以下比较：

- 29 个层次定义的端口顺序一致，包括引用的标准反相器；总线按声明顺序展开，并按 cell 中声明的信号族映射到验收版本的标量名称。
- 阵列展开后的 1111 组 primitive 连接、模型和有效参数一致。
- 缺失、增加及参数改变的 primitive 组均为零。

原生窗口截图覆盖 28 个 cell。功能重绘涉及的 15 个 schematic、SAR_SAMPLE symbol
及其在 SAR_FRONTEND 中的显示已审阅；比较器、存储单元另有局部放大图。
阵列端口的有序网名在连线前逐端标注，检查后逐位核对。
20 项电气验收结果见[电气验收](electrical-acceptance.md)；图面重排保持已验收电路的电气定义。

# 复现命令与产物

在工程根目录使用已配置的 Virtuoso Bridge Python 环境。`BATCH` 指向
产物根目录下的 `final_stage1_06`，`ARTIFACTS` 为运行时解析的产物根目录。
首次构建使用新的目标库；已有库重绘会先比较原生回读与保存版本，发现手工编辑时停止。
手工修改先捕获到对应 view 的 native/drawing，核对电气差异后继续。
功能重绘读取捕获的器件属性和子模块实际 pin 坐标，保留所选修改范围以外的视图。

```text
python -m virtuoso.oa.adc_build --batch BATCH --prepare-only
python -m virtuoso.oa.adc_redraw --batch BATCH --functional --cells CELL ... --schematics-only
python -m virtuoso.oa.adc_compare --batch BATCH --native ARTIFACTS/oa_delivery/native_netlist/netlist
python -m virtuoso.oa.adc_render --batch BATCH --inkscape INKSCAPE_EXECUTABLE
python -m regression.common.check
```

单独重绘指定 schematic 可使用 `adc_redraw --schematics-only --cells CELL ...`。
`--functional` 支持 `adc_schematic.py` 中列出的 15 个 cell，使用其功能布局和局部连线；
`--prepare-only` 仅检查绘图方案。
若同时修改 SAR_SAMPLE symbol，在包含该 cell 的选择中以 `--symbols SAR_SAMPLE` 替换 `--schematics-only`。
重绘 symbol 后，工具对其直接父级执行 Check/Save 并核对实际连接，再导出原生网表。
`oa_delivery/electrical_comparison.json` 保存等价比较结果，`redraw_checks.json` 保存逐 cell 检查结果。
SVG 渲染及原生窗口截图分别放在 `symbol_previews/` 和 `native_previews/`，大型产物留在 Git 外。

# 适用范围

本次完成原理图级实现与固定条件的电气验收。TT 总供电功耗约 193.7 mW，包含输出缓冲。
CDAC 使用理想电容；固定 seed=1 的瞬态噪声通过结果不代表统计良率。
本次未完成版图、寄生提取或 Monte Carlo 失配验证。

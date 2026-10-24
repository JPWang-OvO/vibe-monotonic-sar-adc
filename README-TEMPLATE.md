# 模板示例

这些例子用于查看 cell/view、层次组合、视图选择和验证配置如何落到文件中。
建立自己的项目时，可替换电路与 flow，并同步 `project.json` 的入口。

| 示例 | 电路入口 | Flow |
|---|---|---|
| RC 低通 | [RC_LOWPASS](library/blocks/passive/RC_LOWPASS/cell.json) | [response](regression/blocks/rc/flows/response/flow.json) |
| 晶体管反相器 | [INV](library/blocks/logic/INV/cell.json) | [functional](regression/blocks/inverter/flows/functional/flow.json) |
| 2-bit counter 系统 | [COUNTER_DEMO](library/systems/counter_demo/COUNTER_DEMO/cell.json) | [state_sequence](regression/systems/counter_demo/flows/state_sequence/flow.json) |

## 环境与输入

复制 [tsmc28.example.json](config/environments/tsmc28.example.json) 为本机的 `tsmc28.local.json`，填写已有 Bridge profile、Spectre、模型和运行路径。
工艺配置采用 `tsmcN28`，TT sections 为 `top_tt` 与 `pre_simu`，标称电源 0.9 V、温度 25 °C。
Enrichment 的器件映射和 CDF 合约位于 [config/processes](config/processes/tsmc28.json)。更换 PDK 安装后需重新核对。
RC 与 counter 使用理想器件和 Verilog-A，运行需要 Spectre。
物理提取还需在根目录 `.env` 配置 `CALIBRE_BRIDGE_ROOT`，在本机 environment 中填写 Calibre Python 相对路径、配置文件和 profile。

在仓库根目录设置 `$edaPython`，方法见[配置说明](config/README.md)。选定一个 flow 准备输入，例如：

```powershell
& $edaPython -m regression.blocks.rc.flows.response.run prepare --environment config/environments/tsmc28.local.json --batch-id rc_response
& $edaPython -m regression.systems.counter_demo.flows.state_sequence.run prepare --environment config/environments/tsmc28.local.json --batch-id counter_sequence
```

准备结果位于项目 artifact 根目录下的同名批次目录。审阅输入、判据和资源并由用户确认后，使用公共 runner 的 `execute` 和 `collect`，见[运行说明](regression/README.md)。

## RC：解析值与仿真比较

[设计网表](library/blocks/passive/RC_LOWPASS/schematic/netlist.scs)为 1 kΩ/1 pF 低通。
[TB](library/testbenches/blocks/rc/tb_RC_response/netlist/netlist.scs)提供 1 V 激励、AC 和阶跃分析。
测量将 AC 复数响应与 `1/(1+jωRC)` 比较，将瞬态与 `1-exp(-t/RC)` 比较，两项最大误差阈值均为 1 mV。
该 cell 同时保存 schematic/symbol 的 native 与 drawing 文件，可用于查看 OA 保存格式及独立库回放。

## INV：一个 flow 选择 schematic 与 PEX

[设计网表](library/blocks/logic/INV/schematic/netlist.scs)使用 PMOS 600n/30n、NMOS 300n/30n，保留 W/L、倍乘与 finger 数。
`functional` flow 的两个 condition 共用 [tb_INV](library/testbenches/blocks/inverter/tb_INV/netlist/netlist.scs)：

| Condition | cell_views | enrichment |
|---|---|---|
| `schematic_tt` | `INV: schematic` | true，由 PDK 补全参数 |
| `pex_tt` | `INV: pex` | false，使用提取得到的参数 |

两个条件采用 TT、0.9 V、25 °C、5 fF，执行 DC 扫描与 6 ns 瞬态。
低电平上限为 0.09 V，高电平下限为 0.81 V，具体采样点在 flow 配置中。

INV 的 [physical.json](regression/blocks/inverter/flows/functional/physical.json) 从已有 `IC_TEMPLATE/INV/layout` 开始，
使用 xRC/RCC、VSS 参考地、关闭 analog reduction 和 TICER、每作业 1 核，输出为 CalibreView。
主要操作如下，各次 collect 应在对应作业完成后检查报告：

```powershell
& $edaPython -m physical.run prepare --environment config/environments/tsmc28.local.json --target regression/blocks/inverter/flows/functional/physical.json --run-id inverter_extraction
# 审阅实际输入和提取配置，确认后执行：
& $edaPython -m physical.run submit --run <运行目录> --operation lvs
& $edaPython -m physical.run collect --run <运行目录> --operation lvs
& $edaPython -m physical.run submit --run <运行目录> --operation pex
& $edaPython -m physical.run collect --run <运行目录> --operation pex
& $edaPython -m physical.run import-view --run <运行目录>
& $edaPython -m physical.run publish --run <运行目录>
& $edaPython -m regression.blocks.inverter.flows.functional.run prepare --environment config/environments/tsmc28.local.json --batch-id inverter_views
```

CalibreView 导入到 `IC_TEMPLATE/INV/calibre`，随后从该 OA view 导出并发布
`library/blocks/logic/INV/pex/netlist.scs`。该网表随项目纳入 Git，保留提取网络和完整器件参数。
已有 PEX view 可直接用于准备仿真；版图更新后重新提取并审阅网表差异。

## Counter：层次、总线与状态测量

[COUNTER2](library/blocks/digital/COUNTER2/veriloga/COUNTER2.va)提供 2-bit 行为模型，
[COUNTER_STIM](library/support/stimulus/COUNTER_STIM/netlist/netlist.scs)产生时钟、复位与使能，
系统 cell 将两者连接到总线端口。
[TB](library/testbenches/systems/counter_demo/tb_COUNTER_sequence/netlist/netlist.scs)执行 20 ns 瞬态，
测量检查 12 个采样点的复位、计数、保持和恢复状态，要求错码数与无效位数均为零。
Spectre 层的总线节点使用转义形式，位序以 cell 索引和测量配置为准。

## 已有运行证据

重组前的实际运行已覆盖 RC、INV schematic、counter 和 INV RCC 后仿真。
历史条件、日志与结果保留在 artifact 根目录的 `legacy-validation/`、原始批次目录和 `baseline_candidates/`。
候选结果等待用户审核后再成为正式 baseline。

`refactor_prepare_20261021` 完成了重组后四个 case 的实际输入准备和原生 PDK 参数补全。
电气结果仍引用重组前的运行；当前结构的正式分析需按生成的 preview 确认后执行。
`calibre_restore_20261021` 已从现有 layout 完成 GDS/CDL 导出、LVS、CalibreView 提取与 OA 导入，
并由 OA view 发布当前 Git 中的 PEX 网表。该提取包含 2 个 MOS、42 个电阻和 34 个电容，
参考地连接到 VSS；工艺规则沿用既有 VDD 寄生排除设置。新的 PEX 网表尚未进行 DC/瞬态复测。
ADE 目前提供接入约定，原生设置生成与运行尚未验收。

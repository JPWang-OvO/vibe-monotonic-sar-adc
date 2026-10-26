# ADE 重建与运行

`rebuild` 将已登记 flow 的固定 TB 重建为原生 schematic，并在环境配置指定的服务器 OA 库中保存 Maestro view。
Flow 继续负责条件、精度和判据；Maestro 使用 corner 和 design variable 展开运行点。

| Flow | Maestro cell | Tests | 展开条件 |
|---|---|---|---|
| `sar_cmp_functional` | `ade_sar_cmp_functional` | `functional` | 5 个 PVT |
| `sar_phase_functional` | `ade_sar_phase_functional` | `functional` | 5 个 PVT |
| `sar_acceptance` | `ade_sar_acceptance` | `quiet`、`noise` | 每个 test：5 个 PVT × 2 个 `fin` |

共 3 个 Maestro、4 个 tests、30 个运行点。编译时检查展开结果与 flow conditions 一一对应。
目前支持这三个 transient flow 所用的固定 TB 语法；study 尚未接入。

在 [环境配置](../../config/README.md) 中填写 Bridge profile、模型、工具和服务器目录。
目标库需在 CIW 启动目录的 `cds.lib` 中可见，供 Maestro 的本地仿真子进程读取。
使用安装 Virtuoso Bridge 的 Python 环境，在工程根目录依次执行：

```powershell
python -m virtuoso.ade.rebuild prepare --flow regression/blocks/sar_cmp/flows/functional/flow.json --run-id ade_cmp_run --environment config/environments/tsmc18.local.json --library MY_ADE_LIBRARY --library-path /path/to/oa/library
python -m virtuoso.ade.rebuild rebuild --run-id ade_cmp_run
python -m virtuoso.ade.run verify --run-id ade_cmp_run
python -m virtuoso.ade.run start --run-id ade_cmp_run
python -m virtuoso.ade.run collect --run-id ade_cmp_run
```

`prepare` 解析所选电路 view、生成 PDK 几何修正，并写出实际 `preview.md`；按项目验证规则审阅后继续。
多 flow 共用目标库时，先完成全部 `prepare` 和 `rebuild`，再启动 Maestro 仿真。
已有目标 TB 不会被覆盖。各批次使用独立 run ID；同一批次只允许 `start` 一次。

TB 的激励和负载使用 analogLib，DUT 符号绑定该批次所选 view 的 Spectre 定义。
重建结果包含原生连接读回、PVT 模型 section、温度、变量 sweep、分析和顶层波形输出。
`verify` 从已保存的 Maestro 导出各 test/corner 网表，核对 TB 与 flow，并检查 Spectre X、AX 和每 job 8 线程设置。
`prepare --workers N` 设置并行 jobs，默认 4，上限由 `config/run_budget.json` 指定。
ADE 的运行超时覆盖整个 ICRP 作业；一个作业可连续运行多个条件，因此使用各条件超时的总和作为作业上限。
运行时保持其 GUI session 打开，提前关闭会取消仿真。

`start` 记录明确的 `Interactive.N` history；`collect` 在服务器解析该 history 的 ASCII 波形，
核对实际 PVT/变量展开、命令和日志，然后复用 flow 的测量器与判据。
未结束时返回 `running`，结束后只收取小型 `summary.json`。以其中的 `pass_` 和逐 case 结果判断验收。
Maestro 的波形输出用于查看信号；功能与性能判据由 flow 测量器执行。

`setup.json`、preview、原生设置快照、网表、运行回执和结果保存在运行时解析的 artifact root。
它们会包含实际模型、OA 和服务器路径。Git 保存可重建的代码和 flow 配置；原生 OA 数据库及运行产物留在配置的服务器和 artifact 目录。

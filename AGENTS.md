# IC design workspace

## 入口

先读 `docs/README.md`、`docs/architecture/workspace.md` 和相关目录的说明。
仿真读 `docs/verification/policy.md` 与所选 flow；OA 操作读 `virtuoso/README.md`；物理验证读 `physical/README.md`。

## 源与工具

- 电路在 `library/{blocks,systems,support,testbenches}`；每个 cell 独立维护 `cell.json`，每个 view 独立保存源与已有绘图。
- Flow 引用固定 TB；TB 的相对 include 决定依赖，各 condition 通过 cell_views 选择实现。
- `circuit.json` 的设计语义与 `native.json` 的原生 OA 保存格式分别声明 schema。电气修改须同步相关表示，并检查原生网表。
- 手工 OA 修改先捕获、审阅，再继续重建。已有目标 view 不自动覆盖；只有集成工作目录写共享 OA 库。
- Virtuoso Bridge 和 Calibre Bridge 是外部只读依赖，分别由 `VIRTUOSO_BRIDGE_ROOT`、`CALIBRE_BRIDGE_ROOT` 定位，使用各自已有的 Python 环境。
- 物理流程从已有 layout 或 GDS/CDL 开始。CalibreView 导入 OA 后，由原生 netlister 导出 `pex/netlist.scs` 并纳入 Git，供 flow 选择。
- 执行 EDA 操作时读取对应 Virtuoso、Spectre、Calibre 和绘图技能，核对实际 API 签名。
- 复杂远端命令用 LF-only 脚本上传执行。避免 PowerShell 对远端变量和重定向的二次解释。

## 验证与产物

- 新仿真批次先准备实际 preview，并确认 case、判据、精度和资源；确认过的同一批次直接继续。
- PEX 明确参考地、引擎、R/RC/RCC、约简和精度设置；使用已确认的当前设计配置。
- 波形在服务器解析，本地收取指标、日志和必要图片。工具成功、日志检查、功能和性能结论分别记录。
- 产物根目录按 `regression/common/project.py` 在运行时解析；新项目 ID 必须独立。模型、机器路径和连接参数不写进电路源。
- 新增或更新基线须经用户审核批准，候选结果先留在 artifacts，批准后写入所属 flow 的 baselines JSON。
- Git 保存电路、PEX view 网表、工具、文档和小型审阅基线；原始提取输出、波形、工具数据库、截图及仿真批次 deck 留在 artifacts。
- 不需要创建 hash、checksum、签名或完整性清单，除非用户明确要求字节身份验证。
- 用最小权威验证；仅在代码改变或新证据影响结论时重跑。完成请求范围后停止。

## 文档与提交

- 文档正文用中文，字段、代码和文件名用英文。编辑文档前使用已安装的 humanizer 和 doc-prune 技能。
- `docs/` 使用 title、type、status、last_reviewed、authoritative_sources frontmatter。当前设计、验证、调查、计划和历史分开。
- 状态允许 current、active、frozen、historical、superseded。类型沿用 index、architecture、verification-policy、verification-method、checkpoint、note、plan、decision、remediation、migration。
- 完成计划后先报告结果，获得批准再归档计划或修改其对应的当前结论。Checkpoint/tag 需明确批准。
- 完成功能或修复后作聚焦提交。修复提交正文依次包含 Discovery、Bug mechanism、Solution mechanism and effect 三个非空段落。
- 不添加推测性重试、回退或无关整理。未完成验证的能力明确写出范围和原因。

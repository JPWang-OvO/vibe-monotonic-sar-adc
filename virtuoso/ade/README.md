# ADE 接入

本目录说明 ADE 接入约定，当前提供的可执行仿真入口是 [Spectre runner](../../regression/README.md)。
ADE 设置生成与运行尚未实机验收。

接入时，ADE 应引用本工程的固定 TB 与已登记 view，变量、分析、corner、精度和指标与对应 flow 保持一致。
以 flow 为运行配置来源，避免在 GUI 和 Python 配置中维护两份独立判据。

推荐操作顺序为创建/选择 TB，保存设置，生成原生网表并核对绑定，再按实际配置准备仿真 preview。
运行后绑定明确的 history ID 读取结果，检查每个 job 的日志。

使用安装 Bridge 的 Maestro API 和对应示例，明确本项目保存的设置文件及回放范围。

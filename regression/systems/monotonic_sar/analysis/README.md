# ADC 建模与分析

从工程根目录以 `python -m` 调用。`model.py` 实现电荷守恒的理想逐次逼近模型，
`fft.py` 提供参考模型的频谱分析，`measure.py` 读取系统波形。
各 flow 的 `measure.py` 应用验收判据；比较器、分频器功能测量和独立噪声表征位于各自 flow/study 目录。
解析后的 flow 条件和 criteria 决定测量窗口与判据。

```text
python -m regression.systems.monotonic_sar.analysis.validate_python --output <输出目录>
python -m regression.systems.monotonic_sar.analysis.plot_candidate <批次目录>
python -m regression.systems.monotonic_sar.analysis.plot_timing <批次目录>
python -m regression.systems.monotonic_sar.analysis.summarize_batch <批次目录>
python -m regression.systems.monotonic_sar.analysis.peek_batch <批次目录>
```

`validate_python` 检查固定输入、量化边界和两个频点，输出参考码与逐位轨迹。
绘图入口使用已收集的 `summary.json`，图像和原始采样 CSV 写入该批次的 `figures/`。
`peek_batch` 读取远端作业状态与已完成 case 的结果。

下列诊断接受 `<批次目录> <case-id>`，在服务器解析保留的波形，把诊断结果写到批次目录：

| 入口 | 输入及输出 |
|---|---|
| `diagnose_system` | Sample、Valid、ClkC、EOC、输出码及顶板电压；检查转换次数和握手时序 |
| `diagnose_capture` | 逐位 Ck、Outp、底板及比较器时钟；测量捕获、底板建立与再比较间隔 |
| `diagnose_output` | 已测转换记录和各输出位；测量 EOC 后的建立时间与读取余量 |
| `diagnose_period` | 主时钟与采样沿；定位最大采样周期误差 |

例如 `python -m regression.systems.monotonic_sar.analysis.diagnose_capture <批次目录> <case-id>`。
内部节点应由所选 TB 的 `save` 语句保存。诊断脚本携带所用的局部测量函数，
PSF 读取器使用批次内的 `regression.common.psf`；正式结果由公共 runner 调用测量实现。

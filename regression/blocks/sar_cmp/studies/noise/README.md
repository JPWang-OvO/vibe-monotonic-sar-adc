# 比较器噪声表征

`study.json` 扫描输入对 1/2/4 µm、再生对 1/2 µm，覆盖 TT/25°C、SS/FF 的 −40/125°C。
固定 TB 驱动比较器与实际偏置电路；每个条件包含 3,456 次比较。
激励顺序与 `measurement.json` 的采样点一一对应，输出负载为 Outp/Outn 各 20 fF、Valid 50 fF。

测量在时钟开始评估后 1.8 ns 读取互补输出，分别统计未决、Valid 迟到和复位错误。
概率曲线采用二项最大似然拟合偏移及输入等效噪声 σ，并报告拟合可识别性及局部统计不确定度。
噪声分析限定于比较器及偏置电路；系统采样、CDAC 噪声和失配由相应系统实验另行检查。

```text
python -m regression.common.runner compile --plan regression/blocks/sar_cmp/studies/noise/study.json --output <新产物目录>
python -m regression.common.runner prepare --plan regression/blocks/sar_cmp/studies/noise/study.json --environment config/environments/tsmc18.local.json --batch-id <新批次> --workers 2
```

Study 变体未在本次清理中重新仿真。既有实测与系统 SNDR 诊断见
[SNDR 诊断](../../../../../docs/verification/sndr-diagnosis.md)。

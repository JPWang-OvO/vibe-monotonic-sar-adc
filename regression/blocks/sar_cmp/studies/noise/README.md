# 比较器噪声表征

`study.json` 扫描输入对 1/2/4 µm、再生对 1/2 µm，覆盖 TT/25°C、SS/FF 的 −40/125°C。
固定 TB 驱动比较器与实际偏置电路；每个条件包含 3,456 次比较。
`measurement.json` 保存 3 个共模、9 个差分电平、每电平 128 次重复及打乱种子 31。
`stimulus.py` 按共模分组，逐轮打乱差分电平，重建与固定 TB 一致的 3,456 次比较顺序。
`measure.py` 使用该序列关联输入与输出。输出负载为 Outp/Outn 各 20 fF、Valid 50 fF。

测量在时钟开始评估后 1.8 ns 读取互补输出，分别统计未决、Valid 迟到和复位错误。
概率曲线采用二项最大似然拟合偏移及输入等效噪声 σ，并报告拟合可识别性及局部统计不确定度。
噪声分析限定于比较器及偏置电路；系统采样、CDAC 噪声和失配由相应系统实验另行检查。

```text
python -m regression.blocks.sar_cmp.studies.noise.run compile --output <新产物目录>
python -m regression.blocks.sar_cmp.studies.noise.run prepare --environment config/environments/tsmc18.local.json --batch-id <新批次> --workers 2
```

Study 变体未在本次清理中重新仿真。既有实测与系统 SNDR 诊断见
[SNDR 诊断](../../../../../docs/verification/sndr-diagnosis.md)。

序列参数与 TB 的 PWL 共同定义实验。调整序列后须同步 TB；
`regression.test_execution` 会核对两个输入的全部 3,456 次电平及时间，防止测量顺序与激励错位。

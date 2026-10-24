# 采样孔径与关断误差

研究目标是比较 Sample 下降沿附近的差分电压频谱和栅极复位时间，判断采样关断对线性的影响。
`diagnose.py` 读取已完成的 k=51、50 MS/s 正弦批次，丢弃前 16 次采样，分析后续 256 次。

```text
python -m regression.blocks.sar_sampler.studies.aperture.diagnose <批次目录> <case-id>
```

输入波形需要保存 Sample、SampleB、Vinp、Vinn、Vp、Vn、Gp、Gn；
对应测试见 [sine flow](../../flows/sine/flow.json)。
脚本比较 −0.3 至 1 ns 的观察偏移，输出各偏移的 SNDR、三次谐波功率、
前 12 次采样的节点电压和栅极复位延迟。结果写入批次的 `aperture_diagnostic.json`。
正式采样窗口和验收判据由 flow 决定。

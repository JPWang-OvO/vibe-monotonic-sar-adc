# 2 µm 再生对的独立噪声

本 flow 表征 4 µm 输入对、2 µm 交叉耦合再生 NMOS、1 µm 复位管及 6 µm 偏置/时钟管的比较器。
改变再生尺寸的依据是完整 ADC 矩阵中出现的近零差分完成与捕获竞争，见
[SNDR 诊断](../../../../../docs/verification/sndr-diagnosis.md)。

覆盖 TT/25°C、SS/−40°C、SS/125°C 和 FF/125°C。激励、负载、3456 次判决、
噪声频带及二项概率拟合沿用 [输入对尺寸比较 flow](../noise/README.md)。
该测试使用独立输入和时钟，系统中的 Valid 反馈、捕获与复位关系由完整 ADC 条件验证。

从项目根目录运行公共 runner，选择本目录的 `flow.json`。收集后生成概率和噪声图：

```text
python -m regression.blocks.sar_cmp.flows.noise.report <本地批次目录>
```

每个工艺与温度分别绘图。原 1 µm 再生对的噪声结果保留为尺寸对照。

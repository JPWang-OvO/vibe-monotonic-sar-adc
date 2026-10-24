# 等待门内部节点与建立时间

研究目标是观测等待门 P2 节点、输出 CompareEnable 及两者间电压，检查大权重切换后的控制时序。
输入为使用 [等待门测试台](../../../../../library/testbenches/systems/monotonic_sar/tb_SAR_wait_nodes/cell.json)
生成的批次，包含完整 PSF、`results.json` 和逐位轨迹。

```text
python -m regression.systems.monotonic_sar.studies.wait_gate.diagnose <批次目录> <case-id>
```

脚本在服务器提取 P2、CompareEnable、ValidDelay 和 Early，
记录全窗口极值及首个转换各比较时刻的节点电压，输出 `<case-id>_wait_diagnostic.json`。
器件额定值来自所用工艺模型，建立时间判据来自对应 flow。

# 分频器功能验证

`flow.json` 绑定分频器固定 TB，覆盖 TT/25°C 及 SS/FF 的 −40/125°C。
`measure.py` 检查 Sample 脉冲数，以及相邻 Sample 上升沿间恰有 5 个输入时钟上升沿。
周期误差、脉宽和 POR 最终电压作为观测量；采样窗与转换时间的有效性由系统验收检查。
当前实现尚未重新仿真，baseline 为空。

从工程根目录运行：

```text
python -m regression.blocks.sar_phase.flows.functional.run compile --condition tt_25 --output <新产物目录>
python -m regression.blocks.sar_phase.flows.functional.run prepare --condition tt_25 --environment config/environments/tsmc18.local.json --batch-id <新批次> --workers 1
python -m regression.blocks.sar_phase.flows.functional.run execute --batch <批次目录>
python -m regression.blocks.sar_phase.flows.functional.run collect --batch <批次目录>
```

省略 `--condition` 时选择全部 5 项条件；执行前审阅准备好的批次。公共运行约定见 [regression 说明](../../../../README.md)。

# 比较器功能验证

`flow.json` 绑定比较器与偏置电路的固定 TB，覆盖 TT/25°C 及 SS/FF 的 −40/125°C。
`measure.py` 检查决定极性、Valid 脉冲和复位，并报告延时及偏置电压。
当前实现已通过全部 5 项 PVT 功能验收，结果保存在 `baselines/accepted.json`。

从工程根目录运行：

```text
python -m regression.blocks.sar_cmp.flows.functional.run compile --condition tt_25 --output <新产物目录>
python -m regression.blocks.sar_cmp.flows.functional.run prepare --condition tt_25 --environment config/environments/tsmc18.local.json --batch-id <新批次> --workers 1
python -m regression.blocks.sar_cmp.flows.functional.run execute --batch <批次目录>
python -m regression.blocks.sar_cmp.flows.functional.run collect --batch <批次目录>
```

省略 `--condition` 时选择全部 5 项条件；执行前审阅准备好的批次。公共运行约定见 [regression 说明](../../../../README.md)。

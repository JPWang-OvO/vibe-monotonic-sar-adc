# TSMC18 参数补全资格测试

检查 NMOS/PMOS 的单指、多指和倍乘实例，并保留已导出的标准反相器参数。
原型使用明确的 W/L、finger 数及倍乘；结果包括原生回读、连接与尺寸检查。
参考反相器来自 `library/support/standard_cells/INVD1BWP7T`。

```text
python -m regression.blocks.tsmc18_devices.flows.qualification.run --batch <独立批次名>
python -m regression.blocks.tsmc18_devices.flows.qualification.run --batch <独立批次名> --scale 2
python -m regression.blocks.tsmc18_devices.flows.qualification.run --batch <独立批次名> --five-volt
```

该入口调用实际 PDK CDF 和原生 netlister，使用本机 TSMC18 environment。
每次使用新的批次名；输入、补全记录和 `summary.json` 保存于 artifact 根目录下的该批次。

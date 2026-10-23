# Virtuoso

通过外部 Virtuoso Bridge 连接已有 CIW，操作前核对工作目录、目标库和 technology。
[OA 工具](oa/README.md)负责保存、回放与比较原生视图，[ADE 说明](ade/README.md)规定设置与 flow 的对应关系。

`native.json` 保存原生电气数据和 typed properties，`drawing.json` 保存图形，存在 base CDF 时保存 `cdf.il`。
手工修改后重新捕获并审阅对应源。共享 OA 库由集成工作目录写入，回放使用独立目标库。

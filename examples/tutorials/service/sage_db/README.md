# SAGE-DB Examples

本目录包含两类与 `sage_flow` 风格一致的 SAGE-DB 示例：

1) 应用（Application）方式：`hello_sage_db_app.py`
   - 直接使用 `SageDB` Python API，插入少量向量后进行一次查询

2) 服务（Service）方式：`hello_sage_db_service.py`
   - 以微服务形式封装 SAGE-DB，注册到 `LocalEnvironment` 后由外部推入向量并执行查询

## 运行前置

SAGE-DB 依赖已编译的 Python 扩展模块 `_sage_db`。如未安装，可运行：

```bash
sage extensions install sage_db  # 若需重新编译可加 --force
```

该命令会在仓库根目录下构建并同步 `_sage_db` 扩展，示例中的相对导入即可找到。

## 运行示例

应用方式：

```bash
python examples/service/sage_db/hello_sage_db_app.py
```

服务方式：

```bash
python examples/service/sage_db/hello_sage_db_service.py
```

## 说明
- Canonical Python API 位于 `packages/sage-middleware/src/sage/middleware/components/sage_db/python/sage_db.py`
- 为保持仓库内运行便捷，示例脚本在未安装包时会自动将 `packages/*/src` 加入 `sys.path`
- 若你需要对外暴露更丰富的接口，可在 `python/micro_service/sage_db_service.py` 基础上扩展（如批量删除、索引保存/加载、带条件过滤的查询等）

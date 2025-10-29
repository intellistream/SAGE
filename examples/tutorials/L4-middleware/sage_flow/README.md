# Sage Flow Examples

本目录包含两类示例，风格与 `examples/service/neuromem_vdb` 保持一致：

1. 应用（Application）方式：`hello_sage_flow_app.py`

   - 使用 SAGE 的 pipeline API（from_batch/sink 等）构建一个最小向量处理应用

1. 服务（Service）方式：`hello_sage_flow_service.py`

   - 以微服务形式运行 Sage Flow，支持从外部推入向量并执行一次消费

## 运行示例

建议先编译 C++ 扩展（若尚未构建）：

```bash
# 可选：确保 _sage_flow 扩展已构建
# 构建目录通常在 packages/sage-middleware/src/sage/middleware/components/sage_flow/build/
```

运行应用方式：

```bash
python examples/service/sage_flow/hello_sage_flow_app.py
```

运行服务方式：

```bash
python examples/service/sage_flow/hello_sage_flow_service.py
```

## 说明

- Minimal 服务 `SageFlowService` 位于
  `packages/sage-middleware/src/sage/middleware/components/sage_flow/micro_service/sage_flow_service.py`
- 当前服务主要演示了数据注入与执行路径，后续可扩展 topk/itopk/index 等算子，将其对外暴露为 service API

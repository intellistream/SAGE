# Control Plane Examples

这个目录包含 sageLLM Control Plane 的示例代码，展示不同的使用场景和功能。

## 📁 示例文件

### 1. `example_http_client.py` - HTTP 客户端模式示例

完整的 HTTP 客户端模式使用示例，演示如何使用 Control Plane 调度多个 vLLM 实例。

**包含的示例：**

- `example_local_single_machine()` - 单机多卡部署（4 GPUs）
- `example_multi_machine()` - 跨机器部署（8 GPUs）
- `example_mixed_deployment()` - 本地+远程混合部署
- `example_custom_scheduling()` - 自定义调度策略
- `example_priorities_and_monitoring()` - 优先级调度与性能监控
- `example_policy_switching()` - 动态策略切换

**前置条件：** 需要启动 vLLM 实例。例如：

```bash
# 启动单个 vLLM 实例
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b --port 8000
```

**运行示例：**

```bash
# 修改 main() 函数选择要运行的示例
python -m control_plane.examples.example_http_client
```

### 2. `demo_control_plane.py` - 完整演示（无需 vLLM 实例）

使用 Mock 模拟 vLLM 响应，无需实际的 vLLM 实例即可运行，适合快速了解功能。

**包含的演示：**

- `demo_basic_usage()` - 基础使用流程
- `demo_priorities()` - 优先级调度演示
- `demo_slo_aware()` - SLO 感知调度
- `demo_pd_separation()` - PD 分离优化
- `demo_policy_comparison()` - 策略性能对比
- `demo_monitoring()` - 性能监控

**运行演示：**

```bash
python -m control_plane.examples.demo_control_plane
```

## 🎯 选择哪个示例？

| 场景                     | 推荐示例                             |
| ------------------------ | ------------------------------------ |
| 快速了解功能（无需 GPU） | `demo_control_plane.py`              |
| 实际部署参考             | `example_http_client.py`             |
| 单机多卡部署             | `example_http_client.py` → Example 1 |
| 跨机器部署               | `example_http_client.py` → Example 2 |
| 优先级调度               | `example_http_client.py` → Example 5 |
| 策略切换                 | `example_http_client.py` → Example 6 |

## 📚 更多文档

- [部署指南](../../docs/DEPLOYMENT.md) - 生产环境部署说明
- [集成指南](../../docs/INTEGRATION.md) - 架构和集成文档
- [README](../../README.md) - 项目总览

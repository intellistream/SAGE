# sageLLM - Self-Developed Inference Engine (Placeholder)

<p align="center">
  <strong>SAGE's Custom LLM Inference Engine Project</strong>
</p>

______________________________________________________________________

## ⚠️ Status: Placeholder / Future Development

**sageLLM** is designed to be SAGE's **self-developed LLM inference engine** (similar in scope to
vLLM, TensorRT-LLM, etc.). However, the actual inference engine implementation is **not yet
developed**.

### What Happened?

The original sageLLM repository mistakenly contained **Control Plane** code, which has now been
**moved to the correct location**:

```
❌ OLD (Incorrect):
packages/sage-llm-core/src/sage/llm/
└── sageLLM/
    ├── control_plane/          # ❌ Should not be here
    ├── strategies/
    └── executors/

✅ NEW (Correct):
packages/sage-llm-core/src/sage/llm/
├── control_plane/              # ✅ Engine-agnostic scheduling
│   ├── manager.py
│   ├── strategies/
│   └── executors/
├── service.py                  # vLLM wrapper
├── unified_client.py           # Unified API
└── sageLLM/                    # 📦 Future: Self-developed engine
    └── (To be implemented)
```

## Architecture Overview

### Multi-Engine Design

SAGE supports **multiple inference engines** through a unified Control Plane:

```
┌─────────────────────────────────────────────────────┐
│          sage.llm.control_plane                     │
│   (Engine-agnostic scheduling & routing)            │
└─────────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐  ┌─────────┐  ┌──────────┐
   │  vLLM   │  │ sageLLM │  │  Other   │
   │ (Ready) │  │(Future) │  │ (Future) │
   └─────────┘  └─────────┘  └──────────┘
```

- **vLLM**: Third-party engine (currently integrated)
- **sageLLM**: Self-developed engine (**this submodule**, not yet implemented)
- **Control Plane**: Unified scheduler for **all engines** (engine-agnostic)

### Why Separate Control Plane from Engines?

1. **Engine Independence**: Control Plane can schedule across different engines
1. **Fair Comparison**: Enables benchmarking vLLM vs sageLLM vs others
1. **Clear Responsibilities**:
   - Control Plane: Scheduling, routing, load balancing
   - Engines: Inference execution

## Current Status

### ✅ What Exists

- **Control Plane**: `packages/sage-llm-core/src/sage/llm/control_plane/`

  - Intelligent scheduling (FIFO, Priority, SLO-aware, Adaptive, etc.)
  - PD separation optimization
  - Multi-engine orchestration
  - Performance monitoring

- **vLLM Integration**: `packages/sage-llm-core/src/sage/llm/service.py`

  - VLLMService wrapper
  - API server integration

- **Unified Client**: `packages/sage-llm-core/src/sage/llm/unified_client.py`

  - Single entry point for all engines

### 🚧 What's Missing (This Submodule)

- **sageLLM Inference Engine**: Core inference implementation
- **Custom Kernels**: CUDA/Triton kernels for optimization
- **Model Loading**: Efficient model loading and caching
- **Attention Mechanisms**: PagedAttention or custom alternatives
- **Batching Logic**: Continuous batching implementation

## Migration Guide

If you have imports from the old structure:

```python
# ❌ OLD (Deprecated)
from sage.llm.sageLLM.control_plane import ControlPlaneManager
from sage.llm.sageLLM.control_plane.strategies import HybridSchedulingPolicy

# ✅ NEW (Correct)
from sage.llm.control_plane import ControlPlaneManager
from sage.llm.control_plane.strategies import HybridSchedulingPolicy
```

## How to Use (Current Functionality)

Even though sageLLM engine is not implemented, you can use the Control Plane with vLLM:

```python
from sage.llm import UnifiedInferenceClient

# Create client (uses Control Plane with vLLM backend)
client = UnifiedInferenceClient.create()

# LLM inference
response = client.chat([
    {"role": "user", "content": "Hello!"}
])

# Embedding
vectors = client.embed(["text1", "text2"])
```

## Future Development Roadmap

When sageLLM inference engine is implemented, it will include:

1. **Core Inference Engine**

   - Model loading and weight management
   - Efficient attention mechanisms (e.g., custom PagedAttention)
   - KV cache management

1. **Performance Optimizations**

   - Custom CUDA/Triton kernels
   - Continuous batching
   - Speculative decoding support

1. **Integration with Control Plane**

   - Register as an available engine
   - Expose metrics for scheduling decisions
   - Support PD separation hints

## Related Documentation

- **Control Plane**: `packages/sage-llm-core/src/sage/llm/control_plane/`
- **vLLM Integration**: `packages/sage-llm-core/src/sage/llm/service.py`
- **Unified Client**: `packages/sage-llm-core/src/sage/llm/unified_client.py`
- **Architecture Docs**: `docs-public/docs_src/dev-notes/l1-common/`

## Submodule Information

- **Repository**: https://github.com/intellistream/sageLLM.git
- **Branch**: main-dev
- **Purpose**: Self-developed inference engine (future implementation)
- **Parent Package**: sage-llm-core (L1)

## License

Apache License 2.0

______________________________________________________________________

**Note**: This is a placeholder submodule. The actual inference engine implementation is planned for
future development. For current LLM inference, use vLLM through the Control Plane.
max_parallel_requests=200, ), )

manager.register_instance(prefilling_instance) manager.register_instance(decoding_instance)

````

**性能对比：**

| 指标              | 单实例   | PD分离  | 提升    |
| ----------------- | -------- | ------- | ------- |
| 吞吐量 (tokens/s) | 100      | 150-180 | +50-80% |
| P99延迟 (ms)      | 120      | 50-60   | -50-60% |
| GPU利用率         | 75%      | 90%     | +15%    |
| 成本效率          | baseline | 1.8x    | +80%    |

### 3️⃣ **动态并行策略（5种方案）**

自动选择最优的模型并行方案，支持 TP、PP、DP、EP、Hybrid：

| 并行策略                   | 说明                   | 适用场景                |
| -------------------------- | ---------------------- | ----------------------- |
| **TP (Tensor Parallel)**   | 张量并行，模型权重切分 | 单模型太大无法放入单GPU |
| **PP (Pipeline Parallel)** | 流水线并行，模型层切分 | 超大模型（70B+）        |
| **DP (Data Parallel)**     | 数据并行，模型复制     | 高吞吐场景              |
| **EP (Expert Parallel)**   | 专家并行，MoE模型      | Mixtral等MoE模型        |
| **Hybrid**                 | 混合并行，组合多种策略 | 超大模型+高吞吐         |

```python
from control_plane import ParallelismConfig

# 自动优化并行配置
config = ParallelismConfig(
    auto_optimize=True,
    supported_strategies=["TP", "PP", "Hybrid"],
)

# 手动指定并行配置
instance = ExecutionInstance(
    instance_id="hybrid-instance",
    tensor_parallel_size=4,     # TP=4
    pipeline_parallel_size=2,   # PP=2
    data_parallel_size=2,       # DP=2
    gpu_count=16,
)
````

**并行方案推荐：**

| 模型大小 | GPU数量 | 推荐策略            |
| -------- | ------- | ------------------- |
| \<10B    | 1-2     | TP=1 或 TP=2        |
| 10B-30B  | 2-4     | TP=4                |
| 30B-70B  | 4-8     | TP=4 或 TP=8        |
| 70B-175B | 8-16    | Hybrid (TP=4, PP=2) |
| >175B    | 16+     | Hybrid (TP=8, PP=4) |

### 4️⃣ **请求路由策略**

支持多种路由算法，优化请求分发：

- **load_balanced**: 负载均衡，路由到负载最低的实例
- **round_robin**: 轮询
- **random**: 随机选择
- **affinity**: 用户亲和性，同一用户请求路由到同一实例（提高缓存命中率）
- **locality**: 基于哈希的局部性路由，提高缓存命中率

```python
manager = ControlPlaneManager(
    routing_strategy="affinity",  # 用户亲和性路由
)
```

### 5️⃣ **性能监控与指标**

实时收集和分析性能指标：

```python
# 获取性能指标
metrics = manager.get_metrics()

# 请求指标
print(f"Total requests: {metrics.total_requests}")
print(f"Completed: {metrics.completed_requests}")
print(f"Active: {metrics.active_requests}")

# 延迟指标
print(f"Avg latency: {metrics.avg_latency_ms}ms")
print(f"P95 latency: {metrics.p95_latency_ms}ms")
print(f"P99 latency: {metrics.p99_latency_ms}ms")

# 吞吐指标
print(f"Tokens/sec: {metrics.tokens_per_second}")
print(f"Requests/sec: {metrics.requests_per_second}")

# SLO指标
print(f"SLO violations: {metrics.slo_violations}")
print(f"SLO compliance: {metrics.slo_compliance_rate:.2%}")

# 资源指标
print(f"GPU utilization: {metrics.avg_gpu_utilization:.2%}")
```

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/intellistream/sageLLM.git
cd sageLLM

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### 基本使用

```python
import asyncio
from control_plane import (
    ControlPlaneManager,
    ExecutionInstance,
    RequestMetadata,
    RequestPriority,
)


async def main():
    # 1. 创建控制平面管理器
    manager = ControlPlaneManager(
        scheduling_policy="adaptive",  # 自适应调度
        routing_strategy="load_balanced",  # 负载均衡
        enable_monitoring=True,
    )

    # 2. 注册 vLLM 实例
    instance = ExecutionInstance(
        instance_id="vllm-1",
        host="localhost",
        port=8000,
        model_name="meta-llama/Llama-2-7b-chat-hf",
        tensor_parallel_size=2,
        gpu_count=2,
        max_concurrent_requests=100,
    )
    manager.register_instance(instance)

    # 3. 启动控制平面
    await manager.start()

    # 4. 提交推理请求
    request = RequestMetadata(
        request_id="req-001",
        user_id="user-123",
        priority=RequestPriority.HIGH,
        slo_deadline_ms=1000,  # 1秒SLO
        max_tokens=512,
        prompt="Explain quantum computing in simple terms.",
    )

    request_id = await manager.submit_request(request)
    print(f"Request submitted: {request_id}")

    # 5. 等待并获取结果
    await asyncio.sleep(2)
    status = await manager.get_request_status(request_id)
    print(f"Request status: {status}")

    # 6. 获取性能指标
    metrics = manager.get_metrics()
    print(f"Throughput: {metrics.requests_per_second:.2f} req/s")
    print(f"Avg Latency: {metrics.avg_latency_ms:.2f} ms")

    # 7. 停止控制平面
    await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

### 高级使用示例

更详细的使用示例，请查看：

- **[HTTP 客户端模式](./control_plane/examples/example_http_client.py)** - 实际部署场景示例（单机、多机、混合部署）
- **[完整演示](./control_plane/examples/demo_control_plane.py)** - 功能演示（无需 vLLM 实例）
- **[示例文档](./control_plane/examples/README.md)** - 示例说明和使用指南
- **[集成指南](./dev-notes/INTEGRATION.md)** - 与应用集成的详细步骤

### 运行测试

```bash
# 运行所有 Control Plane 测试
cd tests/control_plane
python -m pytest -v

# 运行特定测试模块
python -m pytest test_scheduling.py -v      # 调度策略测试
python -m pytest test_pd_separation.py -v   # PD 分离测试
python -m pytest test_executor.py -v        # 执行器测试
python -m pytest test_integration.py -v     # 集成测试

# 生成覆盖率报告
python -m pytest --cov=control_plane tests/control_plane/
```

**测试结果：** ✅ 全部 20 个测试通过

- ✅ 5 个调度测试 (`test_scheduling.py`)
- ✅ 5 个 PD 分离测试 (`test_pd_separation.py`)
- ✅ 5 个执行器测试 (`test_executor.py`)
- ✅ 5 个集成测试 (`test_integration.py`)

async def main(): # 创建控制平面管理器 manager = ControlPlaneManager( scheduling_policy="adaptive",
enable_pd_separation=True, )

```
# 注册 vLLM 实例
instance = ExecutionInstance(
    instance_id="llama-instance-1",
    model_name="meta-llama/Llama-2-7b-chat-hf",
    tensor_parallel_size=2,
    gpu_count=2,
)
manager.register_instance(instance)

# 处理请求
from vllm.sampling_params import SamplingParams

prompt = "Hello, how are you?"
sampling_params = SamplingParams(
    temperature=0.7,
    top_p=0.9,
    max_tokens=512,
)

output = await manager.process_request(
    prompt=prompt,
    sampling_params=sampling_params,
)

print(f"Output: {output}")

# 获取性能指标
metrics = manager.get_metrics()
print(f"吞吐: {metrics.throughput} req/s")
print(f"平均延迟: {metrics.avg_latency} ms")
```

if __name__ == "__main__": asyncio.run(main())

````

更详细的使用示例，请查看 [`control_plane/examples/`](./control_plane/examples/) 目录。

### 运行测试

```bash
# 运行所有 Control Plane 测试
cd tests/control_plane
python -m pytest -v

# 运行特定测试
python -m pytest test_scheduling.py -v
python -m pytest test_pd_separation.py -v

# 生成覆盖率报告
python -m pytest --cov=control_plane tests/control_plane/
````

**测试结果：** ✅ 全部 17 个测试通过

- ✅ 5 个调度测试 (test_scheduling.py)
- ✅ 5 个 PD 分离测试 (test_pd_separation.py)
- ✅ 5 个执行器测试 (test_executor.py)
- ✅ 2 个集成测试 (test_integration.py)

## 🏗️ 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       User Application                           │
│                  (SAGE Apps, Custom Services)                    │
└────────────────────────────┬────────────────────────────────────┘
                             │ submit_request()
┌────────────────────────────▼────────────────────────────────────┐
│                    Control Plane (sageLLM)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           Control Plane Manager (核心管理器)              │   │
│  │  • 请求队列管理 (pending_queue, running_requests)         │   │
│  │  • 调度循环 (scheduling_loop)                             │   │
│  │  • 健康检查 (health_check_loop)                           │   │
│  │  • 性能监控 (performance monitoring)                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│           │                  │                  │                │
│           ▼                  ▼                  ▼                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Scheduling   │  │ Parallelism  │  │ PD Router &  │          │
│  │ Policies     │  │ Optimizer    │  │ Routing      │          │
│  │              │  │              │  │              │          │
│  │ • FIFO       │  │ • Auto TP/PP │  │ • Adaptive   │          │
│  │ • Priority   │  │ • DP/EP      │  │ • Hash-based │          │
│  │ • SLO-Aware  │  │ • Hybrid     │  │ • LB/Affinity│          │
│  │ • Cost-Opt   │  │              │  │              │          │
│  │ • Adaptive   │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│           │                  │                  │                │
│           └──────────────────┴──────────────────┘                │
│                              │                                   │
│                              ▼                                   │
│                  ┌──────────────────────┐                        │
│                  │ Execution Coordinator │                        │
│                  │  • Instance Registry  │                        │
│                  │  • Health Monitoring  │                        │
│                  │  • Metrics Collection │                        │
│                  └──────────────────────┘                        │
└──────────────────────────────┼───────────────────────────────────┘
                               │ HTTP API calls
┌──────────────────────────────▼───────────────────────────────────┐
│                     Execution Layer (vLLM)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ vLLM     │  │ vLLM     │  │ vLLM     │  │ vLLM     │        │
│  │ Instance │  │ Instance │  │ Instance │  │ Instance │        │
│  │    1     │  │    2     │  │    3     │  │    N     │        │
│  │          │  │          │  │          │  │          │        │
│  │ TP=4     │  │ TP=2,PP=2│  │ DP=2     │  │ Hybrid   │        │
│  │ Prefill  │  │ Decode   │  │ Decode   │  │ General  │        │
│  │ 优化吞吐  │  │ 优化延迟  │  │ 高并发   │  │ 混合负载 │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                   │
│  • GPU Memory: PagedAttention, KV Cache Management              │
│  • Kernels: CUDA, FlashAttention, FlashInfer                    │
│  • Quantization: GPTQ, AWQ, FP8, INT8                           │
└─────────────────────────────────────────────────────────────────┘
```

### 请求处理流程

```
1. User App submits RequestMetadata
          ↓
2. Control Plane Manager receives request
          ↓
3. Scheduling Policy determines priority/order
          ↓
4. PD Router (if enabled) determines request phase
   • Prefilling phase (long input)
   • Decoding phase (short input)
          ↓
5. Request Router selects appropriate instance
   • Load balancing
   • Affinity/Locality
   • Health check
          ↓
6. Execution Coordinator executes via HTTP API
   • POST /v1/completions or /v1/chat/completions
   • Stream or batch response
          ↓
7. vLLM Instance processes request
   • AsyncLLMEngine execution
   • KV cache management
   • GPU scheduling
          ↓
8. Response returns to Control Plane
          ↓
9. Metrics collected and updated
          ↓
10. Result returns to User App
```

### 核心组件说明

#### 1. Control Plane Manager (`manager.py`)

- 核心协调层，管理整个请求生命周期
- 维护请求队列和运行状态
- 协调各个子组件工作

#### 2. Scheduling Strategies (`strategies/`)

- 5种调度策略：FIFO、Priority、SLO-Aware、Cost-Optimized、Adaptive
- 模块化设计，每个策略独立文件
- 支持自定义策略开发（参见 `docs/CUSTOM_SCHEDULING.md`）

#### 3. PD Router (`pd_routing.py`)

- Prefilling/Decoding 分离路由
- 根据请求特征（输入长度、输出长度）判断阶段
- 将请求路由到专门优化的实例

#### 4. Request Router (`router.py`)

- 请求路由和负载均衡
- 支持多种路由策略：load_balanced、round_robin、affinity、locality
- 考虑实例健康状态和当前负载

#### 5. Parallelism Optimizer (`parallelism.py`)

- 自动选择最优并行策略
- 支持 TP、PP、DP、EP、Hybrid
- 根据模型大小和 GPU 数量推荐配置

#### 6. Execution Coordinator (`executor.py`)

- 管理所有 vLLM 实例
- 执行 HTTP API 调用
- 健康检查和指标收集

#### 7. Types (`types.py`)

- 数据模型定义
- 枚举类型
- 配置类

## 📚 文档

- **[集成指南](./dev-notes/INTEGRATION.md)** - Control Plane 集成架构和使用指南
- **[部署指南](./dev-notes/DEPLOYMENT.md)** - vLLM 实例部署配置
- **[项目结构](./STRUCTURE.md)** - 详细的目录结构说明
- **[测试文档](./tests/control_plane/README.md)** - 测试套件说明

## ⚙️ 环境设置

### GPU 支持 (生产环境推荐)

```bash
# 安装 CUDA Toolkit (Ubuntu/Debian)
sudo apt update && sudo apt install -y nvidia-cuda-toolkit

# 验证 CUDA 安装
nvcc --version
nvidia-smi

# 安装 vLLM（会自动编译 CUDA 内核）
pip install vllm

# 重新安装 sageLLM (如需编译扩展)
pip install -e .
```

### CPU 测试环境

```bash
# 测试可以在没有 GPU 的环境下运行（仅用于单元测试）
cd tests/control_plane
python -m pytest -v

# 注意：实际推理需要 GPU
```

## 🔗 依赖关系

### 核心依赖

- **vLLM** (>= 0.3.0): LLM 推理引擎
- **PyTorch** (>= 2.0.0): 深度学习框架
- **Python** (>= 3.8): 编程语言

### 可选依赖

- **asyncio**: 异步编程（Python 内置）
- **pydantic**: 数据验证
- **pytest**: 单元测试
- **pytest-cov**: 测试覆盖率

详见 `requirements.txt` 和 `requirements-dev.txt`

## 🚢 部署

### 本地开发

```bash
# 启动单个 vLLM 实例
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1

# 启动 Control Plane
python -m control_plane.example
```

### 生产环境

参考 [部署指南](./dev-notes/DEPLOYMENT.md) 了解：

- 多实例部署
- PD 分离配置
- 负载均衡设置
- 监控和日志

## 🎓 使用场景

### 场景 1: 高吞吐批处理

```python
# 使用 DP (数据并行) 提高吞吐
manager = ControlPlaneManager(scheduling_policy="fifo")
instance = ExecutionInstance(
    instance_id="batch-instance",
    data_parallel_size=4,
    gpu_count=4,
)
```

### 场景 2: 低延迟在线服务

```python
# 使用 SLO-Aware 调度 + PD 分离
manager = ControlPlaneManager(
    scheduling_policy="slo_aware",
    enable_pd_separation=True,
)
# 注册 decoding 优化实例（低延迟）
```

### 场景 3: 混合优先级

```python
# 使用 Priority 调度
manager = ControlPlaneManager(scheduling_policy="priority")

# 高优先级请求
high_priority_request = RequestMetadata(
    priority=RequestPriority.CRITICAL,
    slo_deadline_ms=500,
)

# 低优先级请求
low_priority_request = RequestMetadata(
    priority=RequestPriority.LOW,
)
```

### 场景 4: 成本优化

```python
# 使用 Cost-Optimized 调度
manager = ControlPlaneManager(scheduling_policy="cost_optimized")

# 设置成本预算
request = RequestMetadata(
    cost_budget=0.01,  # 最多花费 $0.01
)
```

## 📄 许可

本项目采用 Apache 2.0 许可证，详见 [LICENSE](./LICENSE)

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](../../../../../../CONTRIBUTING.md) 了解如何参与开发。

### 快速开始贡献

```bash
# Fork 和 Clone
git clone https://github.com/yourusername/SAGE.git
cd packages/sage-common/src/sage/common/components/sage_llm/sageLLM

# 创建特性分支
git checkout -b feature/your-feature

# 修改代码并提交
git add .
git commit -m "feat: your feature description"

# Push 并创建 PR
git push origin feature/your-feature
```

## 📮 联系方式

- 📧 邮件：请通过 GitHub Issues 联系
- 💬 讨论：使用 GitHub Discussions
- 🐛 Bug 报告：GitHub Issues

## 🙏 致谢

- 感谢 [vLLM 项目](https://github.com/vllm-project/vllm) 提供优秀的 LLM 推理引擎
- 感谢 SAGE 项目团队的支持和指导

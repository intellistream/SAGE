# L1 Common 开发文档

`sage-common` 属于 L1（基础层），提供 SAGE 框架的核心基础设施和通用组件。本目录记录 sage-common 的开发文档和历史。

## 🚀 Quickstart

### 1. 启动服务

```bash
# 方式一：一键启动 LLM + Embedding 服务（推荐）
sage llm serve

# 方式二：仅启动 LLM 服务
sage llm serve --no-embedding

# 方式三：指定模型
sage llm serve -m Qwen/Qwen2.5-7B-Instruct -e BAAI/bge-m3

# 查看服务状态
sage llm status
```

### 2. 使用统一客户端

```python
from sage.common.components.sage_llm import UnifiedInferenceClient

# 创建客户端（自动连接本地服务）
client = UnifiedInferenceClient.create()

# Chat 对话
response = client.chat([
    {"role": "user", "content": "用一句话介绍人工智能"}
])
print(response)  # "人工智能是让计算机模拟人类智能的技术。"

# Embedding 向量化
vectors = client.embed(["Hello world", "你好世界"])
print(f"向量维度: {len(vectors[0])}")  # 向量维度: 512
```

### 3. 高级：启动 Control Plane Gateway

> ⚠️ **注意**：当前 SAGE 有两个 Gateway 服务，功能不同：
>
> | Gateway | 端口 | 启动方式 | 功能 |
> |---------|------|----------|------|
> | **sage-gateway** | 8000 | `sage studio start` | Chat 代理、会话管理、RAG |
> | **UnifiedAPIServer** | 8000 | 手动启动（见下方） | Control Plane、引擎管理 |
>
> `sage llm engine list/start/stop` 命令需要 **UnifiedAPIServer**，不是 sage-gateway。

```bash
# 先启动 LLM 和 Embedding 服务
sage llm serve

# 然后启动 UnifiedAPIServer（Control Plane Gateway）
python -c "
from sage.common.components.sage_llm.unified_api_server import (
    UnifiedAPIServer, UnifiedServerConfig, BackendInstanceConfig
)
server = UnifiedAPIServer(UnifiedServerConfig(
    port=8000,
    llm_backends=[BackendInstanceConfig(host='localhost', port=8901, model_name='Qwen/Qwen2.5-0.5B-Instruct', instance_type='llm')],
    embedding_backends=[BackendInstanceConfig(host='localhost', port=8090, model_name='BAAI/bge-small-zh-v1.5', instance_type='embedding')],
    enable_control_plane=True,
))
server.start()
"

# 现在可以使用引擎管理命令
sage llm gpu                    # 查看 GPU 状态
sage llm engine list            # 列出引擎
sage llm engine start <model>   # 启动新引擎
sage llm preset list            # 查看预设
sage llm preset apply -n qwen-lite --dry-run  # 预览预设
```

### 4. 停止服务

```bash
sage llm stop
```

---

## 🖥️ CLI 命令详解

### 服务管理

```bash
# 启动服务
sage llm serve                              # LLM + Embedding（默认）
sage llm serve --no-embedding               # 仅 LLM
sage llm serve -m <model> -e <embed_model>  # 指定模型
sage llm serve --foreground                 # 前台运行（调试用）
sage llm serve --port 8901 --embedding-port 8090  # 指定端口

# 服务状态
sage llm status                             # 查看运行状态和健康检查

# 停止/重启
sage llm stop                               # 停止服务
sage llm restart                            # 重启服务

# 日志
sage llm logs                               # 查看日志
sage llm logs --follow                      # 实时跟踪日志
```

### GPU 监控

```bash
sage llm gpu                                # 显示 GPU 资源状态
```

输出示例：
```
                         GPU 资源  
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
┃ GPU                      ┃ 内存 (已用/总量)  ┃  空闲   ┃ 利用率 ┃ 关联引擎 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
│ 0: NVIDIA A100 80GB PCIe │ 68.7 GB / 80.0 GB │ 11.3 GB │  28%   │ engine-1 │
│ 1: NVIDIA A100 80GB PCIe │ 9.7 GB / 80.0 GB  │ 70.3 GB │  30%   │ -        │
└──────────────────────────┴───────────────────┴─────────┴────────┴──────────┘
```

### 引擎管理

> ⚠️ **重要**：引擎管理命令需要 **UnifiedAPIServer** 运行在端口 8000，不是 sage-gateway。
>
> - `sage studio start` 启动的是 **sage-gateway**（不支持引擎管理）
> - 需要手动启动 **UnifiedAPIServer**（参见 Quickstart 第 3 步）

```bash
# 列出引擎
sage llm engine list

# 启动引擎
sage llm engine start <model_id> [options]

# 示例
sage llm engine start Qwen/Qwen2.5-7B-Instruct           # 启动 LLM 引擎
sage llm engine start Qwen/Qwen2.5-7B-Instruct -tp 2     # 2 GPU 并行
sage llm engine start Qwen/Qwen2.5-7B-Instruct --engine-port 8902  # 指定端口
sage llm engine start BAAI/bge-m3 --engine-kind embedding          # Embedding 引擎
sage llm engine start BAAI/bge-m3 --engine-kind embedding --use-gpu  # Embedding + GPU

# 停止引擎
sage llm engine stop <engine_id>
```

**engine start 参数**:
| 参数 | 说明 |
|------|------|
| `--engine-port` | 引擎监听端口 |
| `-tp, --tensor-parallel` | Tensor 并行 GPU 数 |
| `-pp, --pipeline-parallel` | Pipeline 并行 GPU 数 |
| `--engine-kind` | 引擎类型：`llm` (默认) 或 `embedding` |
| `--use-gpu / --no-gpu` | 是否使用 GPU（默认 LLM 用，Embedding 不用）|
| `--label` | 自定义标签 |
| `--max-concurrent` | 最大并发数（默认 256）|

### 预设系统

```bash
# 列出内置预设
sage llm preset list

# 查看预设详情
sage llm preset show --name qwen-lite
sage llm preset show --file my-preset.yaml  # 自定义预设文件

# 应用预设
sage llm preset apply --name qwen-lite              # 执行预设
sage llm preset apply --name qwen-lite --dry-run    # 仅预览
sage llm preset apply --file my-preset.yaml -y      # 无需确认
```

**内置预设**:
| 预设名 | 描述 |
|--------|------|
| `qwen-lite` | 单个 Qwen 0.5B 引擎（无 Embedding）|
| `qwen-mini-with-embeddings` | Qwen 1.5B + BGE-small Embedding |

**自定义预设文件示例** (`my-preset.yaml`):
```yaml
version: 1
name: my-custom-preset
description: 自定义多引擎配置
engines:
  - name: chat
    kind: llm
    model: Qwen/Qwen2.5-7B-Instruct
    tensor_parallel: 2
    port: 8901
    label: main-chat
  - name: embed
    kind: embedding
    model: BAAI/bge-m3
    port: 8090
    use_gpu: true  # Embedding 使用 GPU
```

### 模型管理

```bash
sage llm model download <model_id>          # 下载模型
sage llm model list                         # 列出已下载模型
```

---

## 📦 主要模块

### 🤖 sageLLM 组件 (`components/sage_llm/`)

统一的 LLM 和 Embedding 推理客户端和调度系统：

| 模块 | 描述 |
|------|------|
| `unified_client.py` | `UnifiedInferenceClient` - 统一推理客户端（**唯一入口**） |
| `unified_api_server.py` | `UnifiedAPIServer` - OpenAI 兼容 API Gateway |
| `control_plane_service.py` | Control Plane SAGE 封装层 |
| `compat.py` | `LLMClientAdapter`, `EmbeddingClientAdapter` - vLLM 引擎适配器 |
| `sageLLM/control_plane/` | 核心调度框架（GPU 管理、引擎生命周期、预设系统） |

**统一入口 API**:
```python
from sage.common.components.sage_llm import UnifiedInferenceClient

# 方式一：自动检测（推荐）
# 自动发现本地 LLM (8901) 和 Embedding (8090) 服务
client = UnifiedInferenceClient.create()

# 方式二：连接指定的 Control Plane Gateway
client = UnifiedInferenceClient.create(
    control_plane_url="http://localhost:8000/v1"
)

# 方式三：内嵌模式（在进程内启动 Control Plane）
client = UnifiedInferenceClient.create(embedded=True)

# 使用
response = client.chat([{"role": "user", "content": "Hello"}])
vectors = client.embed(["text1", "text2"])
```

**CLI 引擎管理**:
```bash
# 启动 Embedding 引擎（默认 CPU）
sage llm engine start BAAI/bge-m3 --engine-kind embedding

# 启动 Embedding 引擎使用 GPU
sage llm engine start BAAI/bge-m3 --engine-kind embedding --use-gpu

# 查看引擎列表
sage llm engine list
```

### 🎯 sage_embedding 组件 (`components/sage_embedding/`)

Embedding 服务和工厂：

| 模块 | 描述 |
|------|------|
| `embedding_server.py` | OpenAI 兼容 Embedding 服务器 |
| `factory.py` | `EmbeddingFactory` - 本地模型加载 |
| `service.py` | `EmbeddingService` - Embedding 服务管理 |

> **注意**: 独立的 `IntelligentEmbeddingClient` 已被移除，请使用 `UnifiedInferenceClient.create().embed()` 替代。

### ⚙️ 配置模块 (`config/`)

| 模块 | 描述 |
|------|------|
| `ports.py` | `SagePorts` - 统一端口配置 |
| `env.py` | 环境变量管理 |

## 📁 文档结构

### 核心文档

- **[control-plane-enhancement.md](./control-plane-enhancement.md)** - Control Plane 动态引擎管理增强（GPU/Lifecycle/预设/`use_gpu` 支持）
- **[control-plane-roadmap-tasks.md](./control-plane-roadmap-tasks.md)** - Control Plane 任务路线图（已完成）

### 工具文档

- **[CLEANUP_AUTOMATION.md](./CLEANUP_AUTOMATION.md)** - 自动清理功能说明
- **[VLLM_TORCH_VERSION_CONFLICT.md](./VLLM_TORCH_VERSION_CONFLICT.md)** - vLLM 和 Torch 版本冲突解决

## 🏗️ Gateway 架构说明

> ⚠️ **当前状态**：SAGE 有两个 Gateway 服务，功能不同，尚未合并。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Gateway 对比                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐    │
│  │      sage-gateway          │    │    UnifiedAPIServer         │    │
│  │      (sage-gateway 包)      │    │    (sage-common 包)         │    │
│  ├─────────────────────────────┤    ├─────────────────────────────┤    │
│  │ 启动: sage studio start    │    │ 启动: 手动 Python 代码      │    │
│  │ 端口: 8000                 │    │ 端口: 8000（需手动指定）    │    │
│  ├─────────────────────────────┤    ├─────────────────────────────┤    │
│  │ ✅ /v1/chat/completions    │    │ ✅ /v1/chat/completions     │    │
│  │ ✅ /sessions (会话管理)    │    │ ✅ /v1/completions          │    │
│  │ ✅ /admin/index/* (RAG)    │    │ ✅ /v1/embeddings           │    │
│  │ ❌ 引擎管理 API            │    │ ✅ /v1/management/* (引擎)  │    │
│  │ ❌ Control Plane           │    │ ✅ Control Plane 集成       │    │
│  └─────────────────────────────┘    └─────────────────────────────┘    │
│                                                                         │
│  适用场景:                          适用场景:                          │
│  • Studio Chat 功能                 • 动态引擎管理                     │
│  • 多轮对话会话                     • sage llm engine list/start/stop │
│  • RAG 文档索引                     • GPU 资源监控                     │
│                                     • 预设系统                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**使用建议**：

| 场景 | 推荐方案 |
|------|----------|
| Studio Chat + RAG | `sage studio start`（使用 sage-gateway）|
| 动态引擎管理 | 手动启动 `UnifiedAPIServer` |
| 纯 LLM/Embedding 推理 | `sage llm serve` + `UnifiedInferenceClient.create()` |

**未来计划**：考虑将两个 Gateway 合并为统一服务。

## 🎯 快速导航

| 想要了解... | 查看 |
|-------------|------|
| 统一推理客户端使用 | [hybrid-scheduler/README.md](./hybrid-scheduler/README.md) |
| 动态引擎管理 | [control-plane-enhancement.md](./control-plane-enhancement.md) |
| Embedding GPU 支持 | [control-plane-enhancement.md](./control-plane-enhancement.md) |
| Control Plane 架构 | `packages/sage-common/src/sage/common/components/sage_llm/sageLLM/` |
| 端口配置 | `packages/sage-common/src/sage/common/config/ports.py` |
| Embedding 服务 | `packages/sage-common/src/sage/common/components/sage_embedding/` |
| 单元测试 | `packages/sage-common/tests/unit/components/sage_llm/` |

## 🔗 相关资源

- **代码位置**: `packages/sage-common/src/sage/common/`
- **测试**: `packages/sage-common/tests/`
- **Copilot 指南**: `.github/copilot-instructions.md`

---

**最后更新**: 2025-12-02

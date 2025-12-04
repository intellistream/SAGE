# L1 Common 开发文档

`sage-common` 属于 L1（基础层），提供 SAGE 框架的核心基础设施和通用组件。本目录记录 sage-common 的开发文档和历史。

## 🚀 Quickstart

### 1. 启动服务

```bash
# 方式一：启动 Gateway 服务（推荐，包含 Control Plane）
sage gateway start

# 方式二：仅启动 LLM + Embedding 服务（不含 Control Plane）
sage llm serve

# 方式三：指定端口
sage gateway start -p 9000

# 查看服务状态
sage gateway status
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

### 3. 使用引擎管理命令

> ℹ️ **说明**：`sage gateway` 是统一的 API Gateway，包含 Control Plane 引擎管理功能。

```bash
# 启动 Gateway（包含 Control Plane）
sage gateway start

# 引擎管理命令
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

> ℹ️ **说明**：引擎管理命令需要 Gateway 运行（`sage gateway start`）。
>
> `sage studio start` 也会自动启动 Gateway（包含 Control Plane）。

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
| `control_plane_service.py` | Control Plane SAGE 封装层 |
| `compat.py` | `LLMClientAdapter`, `EmbeddingClientAdapter` - vLLM 引擎适配器 |
| `sageLLM/control_plane/` | 核心调度框架（GPU 管理、引擎生命周期、预设系统） |

> **注意**：`UnifiedAPIServer` 已移除，Control Plane 功能现由 `sage-gateway` 提供。

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

`sage-gateway` 是 SAGE 的**统一 API Gateway**，提供：

- **OpenAI 兼容 API**：`/v1/chat/completions`、`/v1/completions`、`/v1/embeddings`
- **Control Plane 引擎管理**：`/v1/management/engines/*`、`/v1/management/gpu`
- **会话管理**：`/sessions/*`（多轮对话持久化）
- **RAG 索引**：`/admin/index/*`（文档索引和检索）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         sage-gateway (统一 Gateway)                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                     API 端点                                     │   │
│   ├─────────────────────────────────────────────────────────────────┤   │
│   │  ✅ /v1/chat/completions       ← OpenAI 兼容                    │   │
│   │  ✅ /v1/completions            ← OpenAI 兼容                    │   │
│   │  ✅ /v1/embeddings             ← OpenAI 兼容                    │   │
│   │  ✅ /v1/management/engines     ← Control Plane 引擎管理         │   │
│   │  ✅ /v1/management/gpu         ← GPU 资源监控                   │   │
│   │  ✅ /v1/management/backends    ← 后端发现                       │   │
│   │  ✅ /sessions                  ← 会话管理                       │   │
│   │  ✅ /admin/index               ← RAG 索引管理                   │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│   启动方式:                                                              │
│     • sage gateway start           # 直接启动 Gateway                  │
│     • sage studio start            # 启动 Studio（自动启动 Gateway）    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**CLI 命令参考**：

```bash
# Gateway 管理
sage gateway start                  # 启动 Gateway（后台）
sage gateway start --foreground     # 前台运行（调试用）
sage gateway stop                   # 停止 Gateway
sage gateway status                 # 查看状态和已注册引擎
sage gateway logs --follow          # 查看日志

# 引擎管理（需要 Gateway 运行）
sage llm engine list               # 列出引擎
sage llm engine start <model>      # 启动引擎
sage llm engine stop <id>          # 停止引擎
sage llm gpu                       # GPU 资源状态
sage llm preset list               # 查看预设
```

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

---

## 🎓 CLI 使用教程

本教程演示如何使用 SAGE Gateway 和 LLM CLI 命令完成完整的推理流程。

### 教程 1: 基础服务启动与对话

**目标**: 启动 Gateway 服务，完成一次 LLM 对话

```bash
# 第一步: 启动 Gateway（包含 Control Plane）
sage gateway start

# 输出示例:
# ✅ Gateway 已启动 (PID: 12345)
#    地址: http://localhost:8000
#    Control Plane: 已启用
#    健康检查: http://localhost:8000/health

# 第二步: 确认 Gateway 状态
sage gateway status

# 输出示例:
# Gateway: ✅ 运行中 (PID 12345)
#   地址: http://localhost:8000
#   Control Plane: ✅ 可用
#   已注册引擎: 0

# 第三步: 启动 LLM 引擎
sage llm engine start Qwen/Qwen2.5-0.5B-Instruct

# 输出示例:
# ✅ 引擎启动成功
#    ID: engine-abc123
#    模型: Qwen/Qwen2.5-0.5B-Instruct
#    端口: 8901
#    状态: READY

# 第四步: 验证引擎已注册
sage llm engine list

# 输出示例:
#           引擎列表
# ┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
# ┃ ID             ┃ 模型                    ┃ 端口    ┃ 状态   ┃
# ┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
# │ engine-abc123  │ Qwen/Qwen2.5-0.5B-Inst..│ 8901    │ ✅ READY│
# └────────────────┴─────────────────────────┴─────────┴────────┘

# 第五步: 测试对话
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-0.5B-Instruct",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 教程 2: 完整服务栈（LLM + Embedding）

**目标**: 启动 LLM 和 Embedding 引擎，使用 Python 客户端

```bash
# 第一步: 启动 Gateway
sage gateway start

# 第二步: 启动 LLM 引擎
sage llm engine start Qwen/Qwen2.5-0.5B-Instruct

# 第三步: 启动 Embedding 引擎（CPU 模式）
sage llm engine start BAAI/bge-m3 --engine-kind embedding

# 或使用 GPU 加速 Embedding
sage llm engine start BAAI/bge-m3 --engine-kind embedding --use-gpu

# 第四步: 确认所有引擎就绪
sage llm engine list

# 输出示例:
#           引擎列表
# ┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
# ┃ ID             ┃ 模型                    ┃ 端口    ┃ 状态   ┃
# ┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
# │ engine-abc123  │ Qwen/Qwen2.5-0.5B-Inst..│ 8901    │ ✅ READY│
# │ engine-xyz789  │ BAAI/bge-m3             │ 8090    │ ✅ READY│
# └────────────────┴─────────────────────────┴─────────┴────────┘
```

**使用 Python 客户端** (详见 `examples/tutorials/L1-common/unified_inference_client_example.py`):

```python
from sage.common.components.sage_llm import UnifiedInferenceClient

# 创建客户端，连接到 Gateway
client = UnifiedInferenceClient.create(
    control_plane_url="http://localhost:8000/v1"
)

# 对话
response = client.chat([
    {"role": "user", "content": "什么是人工智能？"}
])
print(response)

# Embedding
vectors = client.embed(["Hello world", "你好世界"])
print(f"向量维度: {len(vectors[0])}")
```

### 教程 3: GPU 资源监控与引擎管理

**目标**: 监控 GPU 使用情况，管理多个引擎

```bash
# 查看 GPU 资源状态
sage llm gpu

# 输出示例:
#                          GPU 资源  
# ┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┓
# ┃ GPU                      ┃ 内存 (已用/总量)  ┃  空闲   ┃ 利用率 ┃ 关联引擎 ┃
# ┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━┩
# │ 0: NVIDIA A100 80GB PCIe │ 12.5 GB / 80.0 GB │ 67.5 GB │  12%   │ engine-1 │
# │ 1: NVIDIA A100 80GB PCIe │ 0.0 GB / 80.0 GB  │ 80.0 GB │  0%    │ -        │
# └──────────────────────────┴───────────────────┴─────────┴────────┴──────────┘

# 使用多 GPU 并行启动大模型
sage llm engine start Qwen/Qwen2.5-72B-Instruct -tp 4

# 停止特定引擎（优雅关闭）
sage llm engine stop engine-abc123

# 强制停止引擎
sage llm engine stop engine-abc123 --force
```

### 教程 4: 使用预设系统

**目标**: 使用预设快速部署多引擎配置

```bash
# 列出可用预设
sage llm preset list

# 输出示例:
#           可用预设
# ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
# ┃ 名称                       ┃ 描述                                          ┃
# ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
# │ qwen-lite                  │ 单个 Qwen 0.5B 引擎（无 Embedding）            │
# │ qwen-mini-with-embeddings  │ Qwen 1.5B + BGE-small Embedding               │
# └────────────────────────────┴───────────────────────────────────────────────┘

# 预览预设（不实际执行）
sage llm preset apply --name qwen-lite --dry-run

# 应用预设
sage llm preset apply --name qwen-mini-with-embeddings
```

**自定义预设文件** (`my-preset.yaml`):

```yaml
version: 1
name: production-stack
description: 生产环境多引擎配置
engines:
  - name: chat-main
    kind: llm
    model: Qwen/Qwen2.5-7B-Instruct
    tensor_parallel: 2
    port: 8901
    max_concurrent: 256
    label: main-chat
  - name: chat-backup
    kind: llm
    model: Qwen/Qwen2.5-7B-Instruct
    tensor_parallel: 2
    port: 8902
    label: backup-chat
  - name: embed
    kind: embedding
    model: BAAI/bge-m3
    port: 8090
    use_gpu: true
    label: main-embed
```

```bash
# 应用自定义预设
sage llm preset apply --file my-preset.yaml -y
```

### 教程 5: 服务诊断与日志

**目标**: 排查服务问题

```bash
# 查看 Gateway 日志
sage gateway logs --follow

# 查看 Gateway 详细状态
sage gateway status

# 常见问题诊断
# 问题 1: Gateway 启动失败
sage gateway start --foreground  # 前台运行查看错误

# 问题 2: 引擎启动失败
sage llm engine list  # 检查引擎状态是否为 ERROR

# 问题 3: 端口冲突
lsof -i :8000  # 检查 Gateway 端口
lsof -i :8901  # 检查 LLM 端口
lsof -i :8090  # 检查 Embedding 端口

# 问题 4: 重启所有服务
sage gateway stop
sage llm stop
sage gateway start
```

### 常用命令速查表

| 命令 | 描述 |
|------|------|
| `sage gateway start` | 启动 Gateway（后台） |
| `sage gateway start --foreground` | 启动 Gateway（前台调试） |
| `sage gateway stop` | 停止 Gateway |
| `sage gateway status` | 查看 Gateway 状态 |
| `sage gateway logs --follow` | 实时查看日志 |
| `sage llm engine list` | 列出所有引擎 |
| `sage llm engine start <model>` | 启动 LLM 引擎 |
| `sage llm engine start <model> --engine-kind embedding` | 启动 Embedding 引擎 |
| `sage llm engine start <model> --engine-kind embedding --use-gpu` | GPU Embedding |
| `sage llm engine stop <id>` | 停止引擎 |
| `sage llm gpu` | 查看 GPU 状态 |
| `sage llm preset list` | 列出预设 |
| `sage llm preset apply --name <preset>` | 应用预设 |
| `sage llm status` | 查看 LLM 服务状态 |

---

**最后更新**: 2025-12-03

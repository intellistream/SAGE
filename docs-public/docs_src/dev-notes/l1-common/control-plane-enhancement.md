# sageLLM Control Plane 增强说明 (Issue #1284)

## 概述

本次增强为 sageLLM Control Plane 添加了动态引擎生命周期管理和 GPU 资源调度能力，使控制平面可以：

1. **自动监控 GPU 显存** — 通过 `GPUResourceManager` (NVML / Mock) 追踪系统级 GPU 状态和内部逻辑预留。
1. **按需启动/停止推理引擎** — `EngineLifecycleManager` 支持 vLLM 或 Embedding 服务器进程管理。
1. **统一管理 API** — `/v1/management/engines` (POST/DELETE) 与 `/v1/management/status` (GET) 提供 RESTful
   控制接口。
1. **预设编排** — 内置 `sage llm preset` 命令组，支持一键部署多模型引擎组合。

______________________________________________________________________

## 新增组件

### 1. GPUResourceManager

| 文件      | `packages/sage-common/.../control_plane/gpu_manager.py`                                         |
| --------- | ----------------------------------------------------------------------------------------------- |
| 职责      | NVML GPU 状态采集、逻辑内存预留、模型显存估算                                                   |
| 关键 API  | `get_system_status()`, `allocate_resources()`, `release_resources()`, `estimate_model_memory()` |
| Mock 模式 | 当 `nvidia-ml-py` 不可用或显式禁用时自动启用                                                    |

### 2. EngineLifecycleManager

| 文件                 | `packages/sage-common/.../control_plane/engine_lifecycle.py`               |
| -------------------- | -------------------------------------------------------------------------- |
| 职责                 | 启动 (subprocess)、停止 (SIGTERM/SIGKILL)、列举引擎进程                    |
| 关键 API             | `spawn_engine()`, `stop_engine()`, `get_engine_status()`, `list_engines()` |
| `EngineRuntime` 枚举 | `llm` / `embedding`，决定启动 vLLM 还是 Embedding Server                   |

### 3. ControlPlaneManager 集成

| 文件     | `packages/sage-common/.../control_plane/manager.py`                                            |
| -------- | ---------------------------------------------------------------------------------------------- |
| 新方法   | `request_engine_startup(engine_kind=...)`, `request_engine_shutdown()`, `get_cluster_status()` |
| 关键改进 | Embedding 引擎无需 GPU 预留；`engine_kind` 元数据贯穿实例注册、集群状态快照                    |

### 4. UnifiedAPIServer REST 路由

| 端点                                 | 方法   | 描述                                                |
| ------------------------------------ | ------ | --------------------------------------------------- |
| `/v1/management/engines`             | POST   | 启动新引擎（`EngineStartRequest` 含 `engine_kind`） |
| `/v1/management/engines/{engine_id}` | DELETE | 停止并释放引擎                                      |
| `/v1/management/status`              | GET    | 获取 GPU、引擎、实例聚合状态                        |

### 5. CLI 命令

| 命令                               | 描述                                                                                                               |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `sage llm engine list`             | 展示当前由控制平面管理的引擎（含 runtime 列）                                                                      |
| `sage llm engine start <model_id>` | 启动引擎，支持 `--engine-kind llm\|embedding`、`--use-gpu/--no-gpu`、`--tensor-parallel`、`--pipeline-parallel` 等 |
| `sage llm engine stop <engine_id>` | 停止引擎                                                                                                           |
| `sage llm gpu`                     | 展示 GPU 状态                                                                                                      |
| `sage llm preset list`             | 列出内置预设                                                                                                       |
| `sage llm preset show -n <name>`   | 查看预设详情                                                                                                       |
| `sage llm preset apply -n <name>`  | 按预设启动多个引擎（含 dry-run 和 rollback）                                                                       |

______________________________________________________________________

## 预设系统

预设文件（YAML）描述一组引擎：

```yaml
version: 1
name: qwen-mini-with-embeddings
description: Start a Qwen 1.5B chat engine and BGE-small embedding server.
engines:
  - name: chat
    kind: llm
    model: Qwen/Qwen2.5-1.5B-Instruct
    tensor_parallel: 1
    label: chat-qwen15b
  - name: embed
    kind: embedding
    model: BAAI/bge-small-zh-v1.5
    label: embedding-bge
  - name: embed-gpu
    kind: embedding
    model: BAAI/bge-m3
    use_gpu: true  # 显式使用 GPU（默认 Embedding 不用 GPU）
    label: embedding-bge-m3-gpu
```

**`use_gpu` 参数行为**:

- `use_gpu: null` 或省略 (默认): LLM 用 GPU，Embedding 不用
- `use_gpu: true`: 强制使用 GPU
- `use_gpu: false`: 强制不用 GPU（即使是 LLM）

内置预设位于 `packages/sage-common/.../sage_llm/presets/registry.py`；用户可通过 `--file` 加载自定义 YAML。

______________________________________________________________________

## 快速验证

```bash
# 启动 Unified API Server（含管理 API）
sage llm serve

# 列出现有引擎
sage llm engine list

# 启动额外 Embedding 引擎（默认 CPU）
sage llm engine start BAAI/bge-m3 --engine-kind embedding --port 8095

# 启动 Embedding 引擎使用 GPU
sage llm engine start BAAI/bge-m3 --engine-kind embedding --use-gpu --port 8095

# 一键预设部署
sage llm preset apply -n qwen-mini-with-embeddings

# 查看 GPU 状态
sage llm gpu
```

______________________________________________________________________

## 相关文件

| 文件                                                                    | 用途             |
| ----------------------------------------------------------------------- | ---------------- |
| `packages/sage-llm-core/src/sage/llm/control_plane/gpu_manager.py`      | GPU 监控与预留   |
| `packages/sage-llm-core/src/sage/llm/control_plane/engine_lifecycle.py` | 引擎进程管理     |
| `packages/sage-llm-core/src/sage/llm/control_plane/manager.py`          | 控制平面核心     |
| `packages/sage-llm-core/src/sage/llm/unified_api_server.py`             | REST API 网关    |
| `packages/sage-llm-core/src/sage/llm/presets/`                          | 预设模型与注册表 |
| `packages/sage-cli/src/sage/cli/commands/apps/llm.py`                   | CLI 命令实现     |
| `docs/dev-notes/l6-cli/llm-preset-launcher.md`                          | 预设系统设计文档 |

______________________________________________________________________

## 后续计划

1. ~~单元/集成测试覆盖 GPU Manager、Lifecycle Manager、Preset 解析与 CLI 命令。~~ ✅ 已完成
1. 可视化面板 (sage-studio) 与 preset apply 状态反馈整合。
1. 引擎健康检查与自动重启策略。

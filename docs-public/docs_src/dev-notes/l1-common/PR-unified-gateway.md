# PR: Unified Gateway with Control Plane Integration

## 📋 概述

本 PR 合并了 Issue #1287 (Gateway 合并) 和 Issue #1295 (动态引擎发现)，实现了 SAGE 的统一 Gateway 服务。

**分支**: `feature/unified-gateway`\
**目标分支**: `main-dev`

## 🎯 主要变更

### 1. Control Plane 动态引擎管理

- **引擎注册与生命周期管理** (`sageLLM/control_plane/types.py`, `manager.py`)

  - 新增 `EngineState` 枚举：`STARTING → READY → DRAINING → STOPPED → ERROR`
  - 新增 `EngineInfo` 数据类：包含引擎 ID、模型、端口、状态、创建时间等
  - 实现 `register_engine()`, `unregister_engine()`, `get_engine_state()`
  - 心跳机制：连续 3 次健康检查失败自动进入 ERROR 状态
  - 优雅关闭：DRAINING 状态等待请求完成后再 STOPPED

- **动态后端发现** (`unified_client.py`)

  - `GET /v1/management/backends` 端点返回所有已注册后端
  - `UnifiedInferenceClient` 支持 `control_plane_url` 参数
  - 自动故障转移：后端不可用时路由到其他可用后端

### 2. Gateway 统一

- **sage-llm-gateway 集成 Control Plane** (`sage-llm-gateway/src/sage/gateway/`)

  - 新增 `routes/control_plane.py`：所有 Control Plane 端点
  - 更新 `server.py`：添加 `/v1/embeddings` 端点
  - 新增 `__main__.py`：支持 `python -m sage.llm.gateway` 启动

- **移除 UnifiedAPIServer**

  - 删除 `packages/sage-common/.../sage_llm/unified_api_server.py`
  - 所有 Control Plane 功能迁移至 sage-llm-gateway

- **CLI 命令统一** (`sage-cli/src/sage/cli/commands/apps/gateway.py`)

  - 新增 `sage gateway` 命令组：`start`, `stop`, `status`, `logs`, `restart`
  - 更新 `sage llm engine` 命令使用 Gateway 端点

### 3. API 端点

| 端点                               | 方法 | 描述                  |
| ---------------------------------- | ---- | --------------------- |
| `/v1/chat/completions`             | POST | OpenAI 兼容对话       |
| `/v1/completions`                  | POST | OpenAI 兼容生成       |
| `/v1/embeddings`                   | POST | OpenAI 兼容 Embedding |
| `/v1/management/engines`           | GET  | 列出所有引擎          |
| `/v1/management/engines/start`     | POST | 启动新引擎            |
| `/v1/management/engines/{id}/stop` | POST | 停止引擎              |
| `/v1/management/backends`          | GET  | 获取可用后端列表      |
| `/v1/management/gpu`               | GET  | GPU 资源状态          |
| `/v1/management/status`            | GET  | Control Plane 状态    |
| `/sessions/*`                      | -    | 会话管理              |

## 📁 文件变更

### 新增文件

| 文件                                                               | 描述                             |
| ------------------------------------------------------------------ | -------------------------------- |
| `sage-llm-gateway/src/sage/gateway/__main__.py`                    | Gateway CLI 入口点               |
| `sage-llm-gateway/src/sage/gateway/routes/control_plane.py`        | Control Plane 路由               |
| `sageLLM/control_plane/types.py`                                   | EngineState, EngineInfo 类型定义 |
| `sage-cli/src/sage/cli/commands/apps/gateway.py`                   | Gateway CLI 命令                 |
| `tests/integration/test_control_plane.py`                          | Control Plane 集成测试           |
| `tests/integration/test_dynamic_discovery.py`                      | 动态发现集成测试                 |
| `examples/tutorials/L1-common/unified_inference_client_example.py` | 客户端使用示例                   |
| `docs/dev-notes/l1-common/unified-gateway-tasks.md`                | 任务规划文档                     |

### 修改文件

| 文件                                          | 变更                           |
| --------------------------------------------- | ------------------------------ |
| `sage-llm-gateway/src/sage/gateway/server.py` | 添加 `/v1/embeddings` 端点     |
| `sageLLM/control_plane/manager.py`            | 添加引擎注册和生命周期管理逻辑 |
| `unified_client.py`                           | 支持 `control_plane_url` 参数  |
| `sage-cli/src/sage/cli/main.py`               | 注册 gateway 命令              |
| `docs/dev-notes/l1-common/README.md`          | 添加 CLI 使用教程              |
| `examples/tutorials/L1-common/README.md`      | 添加新示例说明                 |

### 删除文件

| 文件                                             | 原因                          |
| ------------------------------------------------ | ----------------------------- |
| `packages/sage-common/.../unified_api_server.py` | 功能已迁移至 sage-llm-gateway |

## 🐛 Bug 修复

1. **EngineRuntime.VLLM 未定义**

   - 问题：`/v1/management/status` 返回 500 错误
   - 修复：`manager.py` 第 1872 行 `EngineRuntime.VLLM` → `EngineRuntime.LLM`

1. **Gateway 无法通过 CLI 启动**

   - 问题：`sage gateway start` 报错 "No module named sage.llm.gateway.__main__"
   - 修复：创建 `__main__.py` 入口文件

1. **缺少 `/v1/embeddings` 端点**

   - 问题：Gateway 不支持 Embedding 请求
   - 修复：在 `server.py` 添加 Embedding 代理端点

## ✅ 测试

### 集成测试

```bash
# Control Plane 测试
pytest tests/integration/test_control_plane.py -v

# 动态发现测试
pytest tests/integration/test_dynamic_discovery.py -v
```

### 手动验证

```bash
# 1. 启动 Gateway
sage gateway start

# 2. 启动引擎
sage llm engine start Qwen/Qwen2.5-0.5B-Instruct
sage llm engine start BAAI/bge-m3 --engine-kind embedding

# 3. 验证引擎列表
sage llm engine list

# 4. 测试 Chat
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen2.5-0.5B-Instruct", "messages": [{"role": "user", "content": "Hello"}]}'

# 5. 测试 Embedding
curl http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "BAAI/bge-m3", "input": ["Hello", "World"]}'

# 6. 测试 Python 客户端
python examples/tutorials/L1-common/unified_inference_client_example.py
```

## 📖 使用方式

### CLI 命令

```bash
# Gateway 管理
sage gateway start                  # 启动 Gateway
sage gateway stop                   # 停止 Gateway
sage gateway status                 # 查看状态
sage gateway logs --follow          # 查看日志

# 引擎管理
sage llm engine list               # 列出引擎
sage llm engine start <model>      # 启动 LLM 引擎
sage llm engine start <model> --engine-kind embedding  # 启动 Embedding 引擎
sage llm engine stop <id>          # 停止引擎
sage llm gpu                       # GPU 状态
```

### Python API

```python
from sage.llm import UnifiedInferenceClient

# 连接到 Gateway Control Plane
client = UnifiedInferenceClient.create(
    control_plane_url="http://localhost:8000/v1"
)

# 对话
response = client.chat([{"role": "user", "content": "Hello"}])

# Embedding
vectors = client.embed(["text1", "text2"])
```

## 🔄 Breaking Changes

1. **UnifiedAPIServer 已移除**

   - 迁移方式：使用 `sage gateway start` 替代直接启动 UnifiedAPIServer

1. **端口变更**

   - Gateway 默认端口：8000（原 UnifiedAPIServer 为 8001）

## 📚 文档更新

- `docs/dev-notes/l1-common/README.md` - 添加详细 CLI 使用教程
- `examples/tutorials/L1-common/README.md` - 添加新示例说明
- `.github/copilot-instructions.md` - 需要后续更新

## ✅ Checklist

- [x] 代码符合项目规范 (`sage-dev quality`)
- [x] 所有测试通过 (`sage-dev project test`)
- [x] 文档已更新
- [x] 添加了示例代码
- [x] 无向上依赖（遵循 L1-L6 架构）

## 🔗 相关 Issue

- Closes #1287 (Gateway 合并)
- Closes #1295 (动态引擎发现)

______________________________________________________________________

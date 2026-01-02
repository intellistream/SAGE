# Studio Memory 集成概览

> 适用范围：`packages/sage-studio` + `packages/sage-llm-gateway`
> 主干代码（2025-11）。本说明合并了原「集成改进报告」与「快速上手」内容，覆盖后端 API、前端 UI 以及配置/排障指南。

## 1. 当前架构

### 关键代码路径

| 模块                 | 位置                                                                              | 作用                                                                    |
| -------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| MemoryServiceFactory | `packages/sage-middleware/.../memory_service_factory.py`                          | 统一创建短期/向量/KV/图记忆服务                                         |
| SessionManager       | `packages/sage-llm-gateway/src/sage/gateway/session/manager.py`                   | Gateway 会话 + 记忆生命周期管理；默认 `short_term`，可选 `vdb/kv/graph` |
| Memory APIs          | `packages/sage-llm-gateway/src/sage/gateway/server.py`                            | `/memory/config`, `/memory/stats`, `/sessions/**`                       |
| Memory UI            | `packages/sage-studio/src/sage/studio/frontend/src/components/MemorySettings.tsx` | 设置页中的“记忆管理”卡片                                                |
| API Client           | `packages/sage-studio/src/sage/studio/frontend/src/services/api.ts`               | `getMemoryConfig`, `getMemoryStats` 请求代理                            |

### 运行流程

1. Chat 请求命中 Gateway → `SessionManager` 通过 `MemoryServiceFactory` 为每个 session 初始化记忆后端。
1. `SessionManager.store_dialog_to_memory()` 将对话同步到当前后端（短期窗口或 neuromem collection）。
1. `GET /memory/config|stats` 暴露运行时配置和每个会话的使用情况；SSE/Chat 面板通过 `/api/chat/memory/*` 代理调用。
1. Studio 前端 `MemorySettings` 组件在设置页中展示后端类型、会话使用率、集合信息及说明。

## 2. 快速上手

### 启动服务

```bash
# 1. 启动 Studio（默认会自动启动 gateway）
sage studio start
# 或仅启动 gateway 调试
python -m sage.llm.gateway.server
```

浏览器访问 `http://localhost:5173` → 右上角齿轮 → “记忆管理”页签。

### 配置记忆后端

#### 方式 A：环境变量（推荐）

```bash
# 短期记忆（默认）
export SAGE_MEMORY_BACKEND=short_term
export SAGE_MEMORY_MAX_DIALOGS=10

# 向量数据库记忆（需 neuromem + 嵌入模型）
export SAGE_MEMORY_BACKEND=vdb
export SAGE_MEMORY_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
export SAGE_MEMORY_EMBEDDING_DIM=384

# 键值存储
export SAGE_MEMORY_BACKEND=kv
export SAGE_MEMORY_INDEX_TYPE=bm25s

# 图记忆
export SAGE_MEMORY_BACKEND=graph
```

> 在启动 gateway 之前设置；`ChatModeManager` 只读取一次配置。

#### 方式 B：直接构造 `SessionManager`

```python
from sage.llm.gateway.session.manager import SessionManager

manager = SessionManager(
    max_memory_dialogs=10,
    memory_backend="vdb",
    memory_config={"embedding_model": "sentence-transformers/all-MiniLM-L6-v2", "embedding_dim": 384},
)
```

## 3. 前端体验

`MemorySettings.tsx` 展示：

- **当前配置**：后端类型、窗口大小 / 嵌入模型 / 向量维度。
- **使用统计**：活跃会话数、默认后端。
- **会话表格**：
  - `short_term` → `dialog_count / max_dialogs` + 进度条。
  - 其他后端 → collection 名称、索引是否存在。
- **说明卡片**：简述四种后端用途与运行时切换限制。

> 数据来源：`getMemoryConfig()` + `getMemoryStats()`，失败时前端以 `message.error` 提示。

## 4. API 速查

| 路径                                   | 方法 | 描述                                                                     |
| -------------------------------------- | ---- | ------------------------------------------------------------------------ |
| `/memory/config`                       | GET  | 返回 `backend`, `max_dialogs`, `config`, `available_backends`            |
| `/memory/stats`                        | GET  | 每个 session 的记忆使用情况（短期窗口大小，或 neuromem collection 状态） |
| `/sessions`                            | GET  | 会话摘要（ID、标题、消息数）                                             |
| `/sessions/{id}/clear`                 | POST | 清空某个会话的历史与记忆                                                 |
| `/sessions/cleanup?max_age_minutes=30` | POST | 批量清理过期会话                                                         |

示例：

```bash
curl http://localhost:8000/memory/config | jq
curl http://localhost:8000/memory/stats | jq
curl -X POST "http://localhost:8000/sessions/cleanup?max_age_minutes=15"
```

若通过 Studio 后端代理：`curl http://localhost:5173/api/chat/memory/config`。

## 5. 测试与验证

### UI 验证

1. 启动 Studio → Chat 页面创建多个会话。
1. 打开“记忆管理”页，确认各会话的进度条随对话滚动。
1. 切换不同后端后重启 gateway，验证卡片信息变化。

### API 验证（Python）

```python
from sage.llm.gateway.session.manager import SessionManager

manager = SessionManager(max_memory_dialogs=3)
session = manager.create_session(title="demo")

dialogs = [
    ("你好", "你好！"),
    ("SAGE 是什么?", "SAGE 是一个数据处理框架"),
    ("如何安装?", "pip install isage"),
    ("能举个例子?", "当然...")
]

for user, bot in dialogs:
    manager.store_dialog_to_memory(session.id, user, bot)

print(manager.retrieve_memory_history(session.id))
```

## 6. 排障笔记

| 症状                          | 排查要点                                                                                   |
| ----------------------------- | ------------------------------------------------------------------------------------------ |
| 记忆管理页空白                | 无法访问 `http://localhost:8000/memory/config`；检查 gateway 是否运行、浏览器 console 报错 |
| 会话统计不更新                | 当前无活跃会话或未发送消息；`SessionManager.persist()` 是否被调用                          |
| VDB/KV/Graph 显示“未创建索引” | 对话尚未写入；或 neuromem 依赖缺失，检查 `pip install isage-middleware[neuromem]`          |
| API 500                       | 查看 `~/.sage/gateway.log`，确认 MemoryServiceFactory 是否能创建对应服务                   |

## 7. 后续迭代考量

- 图记忆增强：实体/关系提取、可视化（尚未落地，参考 TODO 列表）。
- 记忆后端运行时切换：目前需重启 gateway 才能生效。
- 记忆导出/压缩：暂无实现，仍处于规划阶段。

保持此文档与 `MemorySettings.tsx` / `session/manager.py` 的实现一致，若新增后端或 API，请更新“架构”“API 速查”两节。

# L6 Gateway Dev Notes

该文档追踪 `packages/sage-llm-gateway` (L6) 的最新架构与运行约定，优先记录**当前代码已经实现且在 Studio/CLI 中可用的能力**，避免与实现脱节。

## 范围与职责

- 对外暴露 OpenAI 兼容 API（`/v1/chat/completions`）以及会话/索引管理接口。
- 将请求编排为 SAGE DataStream/RAG 流水线，复用 L3-L4 能力（`sage-kernel`, `sage-middleware`）。
- 为 Studio Chat/Canvas 提供默认后端，并可独立启动 (`sage-llm-gateway --host ...`).

以下内容**暂未在主干中落地**，因此不在当前说明范围：Anthropic `/v1/messages`、WebSocket 接口、外部多租户认证。

## 关键模块 (按代码结构)

- `server.py`：FastAPI 入口，声明健康检查、会话管理、记忆配置、索引管理等所有 HTTP 路由。
- `adapters/openai.py`：OpenAI 协议适配器，负责会话接入、RAG Pipeline 调用、流式回包（SSE）。
- `rag_pipeline.py`：持久化 Pipeline-as-a-Service，使用 `LocalEnvironment` + `Map/Source/Sink` 组合执行 RAG
  检索与工作流生成。
- `session/manager.py`：会话与记忆管理，支持 `short_term`、`vdb`、`kv`、`graph` 后端并落盘
  (`~/.sage/gateway/sessions.json`)。

## 请求执行路径

1. **入口**：`POST /v1/chat/completions` → `ChatCompletionRequest` (pydantic)；若 `stream=true` 使用
   `StreamingResponse` 返回 SSE。
1. **会话层**：`SessionManager.get_or_create()` 维护对话记录，并将用户消息写入短期记忆或 Neuromem collection。
1. **RAG Pipeline**：`OpenAIAdapter._ensure_pipeline_started()` 懒加载 `RAGPipelineService`，通过
   `PipelineBridge` 将请求送入工作线程；流程内置：
   - 检测工作流意图 → 调用 `sage.libs.agentic.workflow.LLMWorkflowGenerator` 生成 VisualPipeline；
   - 否则执行 `RAGChatMap`：读取 `~/.sage/cache/chat/docs-public_manifest.json`，使用 `SageDB + embedding`
     检索，再由 UnifiedInferenceClient 生成回答；
   - 若索引缺失，自动触发 `_build_index_from_docs()`（`docs-public/docs_src`）。
1. **回写**：adapter 将助手回复写入会话、调用 `store_dialog_to_memory()`，最后生成非流式或流式响应体。

## 会话与记忆后端

- 默认 `short_term`：滑动窗口，`SAGE_GATEWAY_SESSION_BACKEND=short_term`。
- `vdb/kv/graph`：委托 `sage.middleware.components.sage_mem.neuromem`，每个会话创建独立 collection/index
  (`session_{id}_{backend}`)，用于语义检索或键值查找。
- 相关环境变量：
  ```bash
  SAGE_GATEWAY_SESSION_BACKEND=neuromem   # vdb/kv/graph 需要 neuromem 依赖
  SAGE_GATEWAY_SESSION_FILE_PATH=~/.sage/gateway/sessions.json
  SAGE_GATEWAY_SESSION_NEUROMEM_PATH=~/.sage/gateway/neuromem_sessions
  SAGE_GATEWAY_WORKERS=4
  ```

## RAG 索引管理

- Gateway 会在第一次请求或调用 `/admin/index/build` 时检查 `~/.sage/vector_db/manifest.json`。
- 自动源目录优先 `docs-public/docs_src`（通过 `find_sage_project_root()` 定位）；如果不存在仅降级运行、提示执行
  `sage chat ingest`。
- 路由：
  - `GET /admin/index/status`：返回索引 manifest 字段（文档数、chunk、时间戳）。
  - `POST /admin/index/build`：可指定 `source_dir`、`force_rebuild`，内部复用 `_build_index_from_docs()`。
  - `DELETE /admin/index`：删除 `~/.sage/vector_db`。

## 与 Studio / CLI 集成

- `sage studio start` 默认：
  - 检测本地 Gateway 是否运行，未运行则以 CLI 方式启动。
  - 前端 Chat 模式调用 `http://{gateway-host}:{port}/v1/chat/completions`，会话管理通过 `/sessions/**` REST API。
- 独立部署：`sage-llm-gateway --host 0.0.0.0 --port 8000` 或 `python -m sage.llm.gateway.server`。

## REST API 端点清单

| 端点                   | 方法   | 说明                                                 |
| ---------------------- | ------ | ---------------------------------------------------- |
| `/`                    | GET    | 根路径，返回服务信息和可用端点列表                   |
| `/health`              | GET    | 健康检查，返回会话统计                               |
| `/v1/chat/completions` | POST   | OpenAI 兼容聊天端点，支持流式/非流式                 |
| `/sessions`            | GET    | 列出所有会话                                         |
| `/sessions`            | POST   | 创建新会话                                           |
| `/sessions/{id}`       | GET    | 获取会话详情                                         |
| `/sessions/{id}`       | DELETE | 删除会话                                             |
| `/sessions/{id}/clear` | POST   | 清空会话历史                                         |
| `/sessions/{id}/title` | PATCH  | 更新会话标题                                         |
| `/sessions/cleanup`    | POST   | 清理过期会话（参数：`max_age_minutes`）              |
| `/memory/config`       | GET    | 获取记忆后端配置                                     |
| `/memory/stats`        | GET    | 获取各会话的记忆使用情况                             |
| `/admin/index/status`  | GET    | 获取 RAG 索引状态                                    |
| `/admin/index/build`   | POST   | 构建 RAG 索引（参数：`source_dir`, `force_rebuild`） |
| `/admin/index`         | DELETE | 删除 RAG 索引                                        |

## 运维与排查要点

- **健康检查**：`GET /health` 返回 session 统计；Studio 依赖该接口判定是否联通。
- **Session 清理**：`POST /sessions/cleanup?max_age_minutes=30`，或直接调用
  `/sessions/{id}/clear`、`DELETE /sessions/{id}`。
- **日志**：`logging.basicConfig(level=INFO)`，可通过 `SAGE_GATEWAY_LOG_LEVEL` 调整。
- **LLM 后端降级**：`OpenAIAdapter._fallback_direct_llm()` 在 RAG Pipeline 异常时直接调用
  UnifiedInferenceClient，根据 `SAGE_CHAT_*` 环境变量自动选择本地 Gateway/vLLM，必要时才回退到 OpenAI 兼容云端。

## 后续更新指引

- 当 Gateway 新增路由或支持 Anthropic/WebSocket，需要同步在“请求执行路径”和“运维”两节补充。
- 若 RAG/记忆架构有调整（例如迁移到新索引格式或 MemoryService），请标注**自哪个 commit 起生效**，方便排查历史行为。

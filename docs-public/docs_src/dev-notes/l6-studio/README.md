# L6 Studio Dev Notes

`packages/sage-studio` 提供 SAGE Studio 可视化工作台，包括 Flow Editor、Chat、Playground、Finetune 与 Memory
等视图，用于将前端 React/Vite 应用与 FastAPI 后端、Gateway、本地 vLLM 服务以及 `sage-kernel` / `sage-middleware`
能力串联起来。本笔记聚焦当前主干代码已经实现的能力与运维要点，便于快速定位模块与排查问题。

## 目录与职责速查

| 路径                                    | 说明                                                                                                                    |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `src/sage/studio/studio_manager.py`     | CLI/服务编排器，负责启动前端、后端、gateway，并提供 `sage studio *` 命令                                                |
| `src/sage/studio/chat_manager.py`       | 默认 Manager，内置本地 LLM 管理、微调模型热切换、gateway 进程生命周期                                                   |
| `src/sage/studio/config/backend/api.py` | FastAPI 后端，暴露 Flow/Playground/Finetune/Memory 等 REST API                                                          |
| `src/sage/studio/services/`             | `node_registry.py`, `pipeline_builder.py`, `docs_processor.py`, `workflow_generator.py`, `finetune_manager.py` 等服务层 |
| `src/sage/studio/frontend/src/`         | React 组件：`FlowEditor`, `ChatMode`, `Playground`, `FinetunePanel`, `MemorySettings` 等                                |
| `tests/`                                | CLI、Pipeline Builder、Node Registry 等集成测试                                                                         |

### 运行流程（`sage studio start`）

1. **LLM**：`ChatModeManager` 默认启用本地 vLLM 服务（`SAGE_STUDIO_LLM=true`），使用 `sage.llm.LLMAPIServer` 在
   `localhost:8001` 暴露 OpenAI 接口，可选 `--use-finetuned` 改为最新微调模型。
1. **Gateway**：若未运行，自动拉起 `sage.llm.gateway.server`（默认 8000），供前端和 Studio Backend 调用。
1. **Backend**：启动 FastAPI（默认 8080），提供 Flow/Playground/Finetune/Memory APIs。
1. **Frontend**：Vite dev server（默认 5173）或生产版（build 后 3000/4173）。
1. **Studio React UI**：通过 `/api/**`（后端代理）调用 gateway：
   - Chat 面板：`/api/chat/send` → gateway `/v1/chat/completions`
   - Finetune：`/api/finetune/*` → `finetune_manager`（写入 `~/.sage/studio_finetune/`）
   - Memory：`/api/chat/memory/*` → gateway `/memory/config|stats`

## 本地 LLM / vLLM 快速指引

| 服务            | 默认端口                    | 备注                             |
| --------------- | --------------------------- | -------------------------------- |
| Gateway         | 8000                        | Studio/Gateway/CLI 通用          |
| 本地 vLLM       | **8001**                    | `ChatModeManager` 优先检测此端口 |
| Studio Backend  | 8080                        | FastAPI                          |
| Studio Frontend | 5173 (dev) / 4173 (preview) | Vite                             |

1. **启动本地 vLLM**（任一方式）
   ```bash
   sage llm run Qwen/Qwen2.5-7B-Instruct --port 8001
   # 或使用 finetune 产物
   sage finetune serve <task_id> --port 8001
   # 直接调用 vLLM
   python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-1.5B-Instruct --port 8001
   ```
1. **启动 Studio**
   ```bash
   sage studio start          # 自动检测 8001，失败时降级云端 API
   sage studio start --no-llm # 如需仅用云端
   ```
1. **验证**
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8001/v1/models
   tail -f ~/.sage/studio/chat/gateway.log  # 查看 Gateway 实际使用的 LLM 源
   ```
1. **仅使用云端 API**：设置 `SAGE_FORCE_CLOUD_API=true` 或在 Chat 面板选择“云端”。

> ⚠️ 端口冲突时可改用 8002+，同时更新 `SAGE_STUDIO_LLM_PORT` 和 `UnifiedInferenceClient` 的自动检测列表。

## 深入主题

### 记忆后端与 UI 总览

Studio 的记忆能力由 Gateway + Middleware 提供，Studio 主要负责可视化与配置入口：

- Gateway 侧通过 `SessionManager` 与 `MemoryServiceFactory` 管理 `short_term`/`vdb`/`kv`/`graph` 等后端，并暴露
  `/memory/config`、`/memory/stats` 与 `/sessions/**` API。
- Studio Backend 通过 `/api/chat/memory/*` 代理调用 Gateway；前端 `MemorySettings`
  组件读取配置与统计信息，在“记忆管理”页中展示当前后端、窗口大小、会话使用情况等。
- 后端类型与参数主要由环境变量控制（如 `SAGE_MEMORY_BACKEND`、`SAGE_MEMORY_MAX_DIALOGS`、`SAGE_MEMORY_EMBEDDING_MODEL`
  等），需要在启动 Gateway 之前设置。

更详细的 API 行为、UI 字段与排障步骤见 `archive/MEMORY_OVERVIEW.md`。

### 微调 + Chat 集成总览

Studio 提供从“创建微调任务 → 监控训练 → 将产物切换为 Chat 后端”的一站式链路：

- 前端 `FinetunePanel.tsx` 负责任务创建、数据上传、进度展示与“切换为对话后端”等操作。
- Backend 在 `config/backend/api.py` 下注册 `/api/finetune/**` 路由，具体逻辑由 `services/finetune_manager.py`
  实现，包括任务队列、GPU 探测、LoRA/merged 模型写入 `~/.sage/studio_finetune/<task_id>/` 等。
- `chat_manager.py`（`ChatModeManager`）提供 `list_finetuned_models()`、`_start_llm_service()` 等能力，用于在端口
  8001 上以 `LLMAPIServer` 形式重启本地 vLLM，并让 Gateway 通过 `UnifiedInferenceClient` 自动切换到新模型。

用户可通过 Web UI Finetune 面板完成全流程，也可以使用 `sage finetune start` 与 `sage studio start --use-finetuned` 走
CLI 路径；更完整的数据流与 API 列表见 `archive/STUDIO_FINETUNE_INTEGRATION.md`。

### 部署与外部访问概览

Studio 前端基于 React + Vite，支持开发（`--dev`）与生产（`--prod`）两种模式：

- **依赖与环境**：推荐在 conda 环境中安装 Node.js 20（`conda install -y nodejs=20 -c conda-forge`），并通过
  `sage studio install` 安装前端依赖；后端通过 `./quickstart.sh --dev --yes` 准备。
- **开发模式**：`sage studio start --dev --host 0.0.0.0 --port 5173`，使用 Vite dev server，自带 HMR。
- **生产模式**：先 `sage studio build` 再
  `sage studio start --prod --host 0.0.0.0 --port 5173`，基于预构建静态资源，适合配合反向代理或 Cloudflare Tunnel 部署。
- **allowedHosts 配置**：在 `vite.config.ts` / `preview` 中配置 `allowedHosts: true`，以允许通过自定义域名访问（否则 Vite
  会阻止非 localhost Host 头）。

CI/CD 与 Cloudflare Tunnel 的具体脚本示例与常见部署故障排查见 `archive/DEPLOYMENT.md`。

### 用户认证与数据隔离规划

为支持多用户场景，Studio 侧已经设计了一套以 FastAPI + JWT + SQLite 为基础的认证与数据隔离方案，目前主要以任务拆解与 Prompt 形式记录在：

- `archive/auth_implementation_prompts.md`：后端/前端四大任务的详细实现提示（认证 API、数据隔离、前端登录 UI、状态集成）。
- `archive/user-auth-tasks.md`：同一方案的任务分解与时间评估（后端认证 API、用户私有数据目录、前端认证 UI 与状态集成、最终集成测试清单）。

核心思路包括：

- 后端新增 `auth_service.py` 与 `/api/auth/*` 端点，使用 JWT（基于 `python-jose`）和
  `~/.local/share/sage/studio.db` 中的用户表管理身份；为现有 API 增加 `get_current_user()` 依赖。
- 将原 `.sage/pipelines/` 等全局目录迁移到
  `~/.local/share/sage/users/{user_id}/pipelines|sessions|uploads/`，未登录用户统一映射为 `anonymous`，保留向后兼容。
- 前端基于 React + Zustand 实现 `authStore`、`LoginPage`、`UserMenu`，并在 `App.tsx` 加入路由守卫；所有 API 调用通过统一的
  `Authorization: Bearer <token>` header 注入登录态。

当前代码库中尚未完全落地全部任务时，可以将这两份文档视为“设计蓝图 + Prompt 库”；未来若完成实现，应同步更新本节描述并在对应服务/组件文件中补充链接。

## 开发与测试

```bash
# 前端
cd packages/sage-studio/src/sage/studio/frontend
sage studio npm install
sage studio npm run dev

# 后端
cd packages/sage-studio
python -m sage.studio.config.backend.api

# 单元测试
pytest packages/sage-studio/tests -q

# 端到端验证
sage studio start --use-finetuned
# -> 浏览器访问 http://localhost:5173 运行 Flow/Chat/Finetune/Memory 全链路
```

遇到 gateway/LLM 进程残留时使用 `sage studio stop --gateway`，若手动通过 `sage llm run` 启动过本地服务，请直接关闭其终端或执行
`pkill -f vllm.entrypoints.openai.api_server` 清理。`~/.sage/studio` 下存放前端缓存、Finetune 输出与日志，可在排查异常时检查。

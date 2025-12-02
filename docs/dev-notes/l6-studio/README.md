# L6 Studio Dev Notes

`packages/sage-studio` 提供    ```bash
   curl http://localhost:8001/health
   curl http://localhost:8001/v1/models
   tail -f ~/.sage/studio/chat/gateway.log  # 查看 Gateway 实际使用的 LLM 源
   ```
4. **仅使用云端 API**：设置 `SAGE_FORCE_CLOUD_API=true` 或在 Chat 面板选择"云端"。

> ⚠️ 端口冲突时可改用 8002+，同时更新 `SAGE_STUDIO_LLM_PORT` 和 `UnifiedInferenceClient` 的自动检测列表。

## 深入主题面（Flow Editor、Chat、Playground、Finetune、Memory 视图），负责把前端 React/Vite 应用与 FastAPI 后端、`sage-kernel`/`sage-middleware` 能力连接起来。本笔记记录当前主干代码已经实现的能力，便于快速定位模块与排查问题。

## 目录与职责速查

| 路径 | 说明 |
| --- | --- |
| `src/sage/studio/studio_manager.py` | CLI/服务编排器，负责启动前端、后端、gateway，并提供 `sage studio *` 命令 |
| `src/sage/studio/chat_manager.py` | 默认 Manager，内置本地 LLM 管理、微调模型热切换、gateway 进程生命周期 |
| `src/sage/studio/config/backend/api.py` | FastAPI 后端，暴露 Flow/Playground/Finetune/Memory 等 REST API |
| `src/sage/studio/services/` | `node_registry.py`, `pipeline_builder.py`, `docs_processor.py`, `workflow_generator.py`, `finetune_manager.py` 等服务层 |
| `src/sage/studio/frontend/src/` | React 组件：`FlowEditor`, `ChatMode`, `Playground`, `FinetunePanel`, `MemorySettings` 等 |
| `tests/` | CLI、Pipeline Builder、Node Registry 等集成测试 |

### 运行流程（`sage studio start`）

1. **LLM**：`ChatModeManager` 默认启用本地 vLLM 服务（`SAGE_STUDIO_LLM=true`），使用 `sage.common.components.sage_llm.LLMAPIServer` 在 `localhost:8001` 暴露 OpenAI 接口，可选 `--use-finetuned` 改为最新微调模型。
2. **Gateway**：若未运行，自动拉起 `sage.gateway.server`（默认 8000），供前端和 Studio Backend 调用。
3. **Backend**：启动 FastAPI（默认 8080），提供 Flow/Playground/Finetune/Memory APIs。
4. **Frontend**：Vite dev server（默认 5173）或生产版（build 后 3000/4173）。
5. **Studio React UI**：通过 `/api/**`（后端代理）调用 gateway：
   - Chat 面板：`/api/chat/send` → gateway `/v1/chat/completions`
   - Finetune：`/api/finetune/*` → `finetune_manager`（写入 `~/.sage/studio_finetune/`）
   - Memory：`/api/chat/memory/*` → gateway `/memory/config|stats`

## 本地 LLM / vLLM 快速指引

| 服务 | 默认端口 | 备注 |
| --- | --- | --- |
| Gateway | 8000 | Studio/Gateway/CLI 通用 |
| 本地 vLLM | **8001** | `ChatModeManager` 优先检测此端口 |
| Studio Backend | 8080 | FastAPI |
| Studio Frontend | 5173 (dev) / 4173 (preview) | Vite |

1. **启动本地 vLLM**（任一方式）
   ```bash
   sage llm run Qwen/Qwen2.5-7B-Instruct --port 8001
   # 或使用 finetune 产物
   sage finetune serve <task_id> --port 8001
   # 直接调用 vLLM
   python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-1.5B-Instruct --port 8001
   ```
2. **启动 Studio**
   ```bash
   sage studio start          # 自动检测 8001，失败时降级云端 API
   sage studio start --no-llm # 如需仅用云端
   ```
3. **验证**
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8001/v1/models
   tail -f ~/.sage/studio/chat/gateway.log  # 查看 Gateway 实际使用的 LLM 源
   ```
4. **仅使用云端 API**：设置 `SAGE_FORCE_CLOUD_API=true` 或在 Chat 面板选择“云端”。

> ⚠️ 端口冲突时可改用 8002+，同时更新 `SAGE_STUDIO_LLM_PORT` 和 `UnifiedInferenceClient` 的自动检测列表。

## 深入主题

- **记忆后端与 UI** → `MEMORY_OVERVIEW.md`
  - 记录 `MemoryServiceFactory` 接入、`/memory/config|stats` API 以及 React `MemorySettings` 组件的使用指南与排障步骤。
- **微调 + Chat 集成** → `STUDIO_FINETUNE_INTEGRATION.md`
  - 合并原始集成说明与 UI 快速参考，覆盖任务创建、实时监控、模型热切换（API `/api/finetune/switch-model` → `chat_manager._start_llm_service()`），以及 CLI 与 Web UI 联动流程。

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

遇到 gateway/LLM 进程残留时使用 `sage studio stop --gateway`，若手动通过 `sage llm run` 启动过本地服务，请直接关闭其终端或执行 `pkill -f vllm.entrypoints.openai.api_server` 清理。`~/.sage/studio` 下存放前端缓存、Finetune 输出与日志，可在排查异常时检查。

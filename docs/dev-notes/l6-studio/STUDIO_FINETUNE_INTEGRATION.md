# Studio 微调 +数据流：
1. 用户在 Finetune 面板创建任务 → 后端写入任务元数据并调用 `finetune_manager.create_task()`。
2. 训练完成后输出 `merged_model/` 或 `lora/`，并更新任务状态。
3. 前端轮询 `/api/finetune/tasks`、`/api/finetune/models` 展示列表。
4. 选择模型或点击"切换为对话后端" → `POST /api/finetune/switch-model`。
5. 后端调用 `chat_manager._stop_llm_service()` → `_start_llm_service(model_path)`，通过 `sage.common.components.sage_llm.LLMAPIServer` 在 `localhost:8001` 重启 vLLM。
6. Gateway 通过 `UnifiedInferenceClient` 自动检测新的本地服务，Chat 面板立即使用。

## 2. Web UI 操作流程（推荐）南

> 适用版本：`packages/sage-studio` (React/Vite + FastAPI) 与 `packages/sage-gateway` 主干，2025-11。本文合并原「集成文档」「UI 总结」「快速参考」，聚焦已经落地的功能及排障手册。

## 1. 架构总览

| 层 | 位置 | 说明 |
| --- | --- | --- |
| 前端 | `frontend/src/components/FinetunePanel.tsx` | 创建任务、上传数据、实时监控、模型列表、热切换 UI |
| 后端 | `config/backend/api.py` (`/api/finetune/**`) | 透传到 `services/finetune_manager.py`，负责任务调度、数据预处理、模型缓存 |
| 服务 | `services/finetune_manager.py` | 管理任务队列、GPU 资源探测、LoRA/merged 模型输出到 `~/.sage/studio_finetune/<task_id>/` |
| Chat Manager | `chat_manager.py` (`ChatModeManager`) | `list_finetuned_models()`、`_start_llm_service()` 支持选择最新微调模型并热切换 LLM |

数据流：
1. 用户在 Finetune 面板创建任务 → 后端写入任务元数据并调用 `finetune_manager.create_task()`。
2. 训练完成后输出 `merged_model/` 或 `lora/`，并更新任务状态。
3. 前端轮询 `/api/finetune/tasks`、`/api/finetune/models` 展示列表。
4. 选择模型或点击“切换为对话后端” → `POST /api/finetune/switch-model`。
5. 后端调用 `chat_manager._stop_llm_service()` → `_start_llm_service(model_path)`，通过 `sage.common.components.sage_llm.LLMAPIServer` 在 `localhost:8001` 重启 vLLM。
6. Gateway 通过 `UnifiedInferenceClient` 自动检测新的本地服务，Chat 面板立即使用。

## 2. Web UI 操作流程（推荐）

1. **启动 Studio**
   ```bash
   sage studio start
   # 或使用生产模式
   sage studio start --prod
   ```
2. **Finetune 面板入口**：顶部导航 → `Finetune`。
3. **创建任务**
   - 选择基础模型（默认推荐 `Qwen/Qwen2.5-0.5B/1.5B/Coder`）。
   - 上传 `.json/.jsonl` 数据集或点击“使用 SAGE 文档样例”。
   - 配置 `epochs/batch_size/lr`，GPU 不足时后台会返回 Warning Modal。
4. **监控训练**
   - 列表自动 3s 轮询，状态以 ✅/🔄/⏳ 等标记。
   - Progress 列显示百分比 + `Epoch/Loss`。
   - 可在详情抽屉中查看实时日志。
5. **热切换模型**（任意一种方式）
   - 当前模型卡片 → 下拉框选择带 `[微调]` 标签的项。
   - 或任务表格中点击「切换为对话后端」。
   - `FinetunePanel` 调用 `/api/finetune/switch-model?model_path=...`，成功后提示：
     - ✅ “模型已切换并生效（LLM 服务已自动重启）”。
     - ⚠️ “模型已切换（需重启）” → 通常是本地 LLM 未启用。
6. **在 Chat 中验证**
   - 切换到 `Chat` 标签，顶部状态栏会展示当前模型。
   - 与微调模型对话；日志位于 `~/.sage/studio/chat/gateway.log`。

## 3. CLI 与自动化

- 查看可用微调模型：
  ```bash
  sage studio start --list-finetuned
  ```
- 启动时直接使用最新微调模型：
  ```bash
  sage studio start --use-finetuned
  ```
- 指定模型路径：
  ```bash
  sage studio start --llm-model ~/.sage/studio_finetune/<task_id>/merged_model
  ```
- 训练脚本化：
  ```bash
  sage finetune start --model Qwen/Qwen2.5-Coder-1.5B --data data.jsonl
  ```

CLI 适合批量创建任务；UI 负责监控与热切换，两者共享同一 `finetune_manager`。

## 4. API 参考

| Endpoint | 方法 | 说明 |
| --- | --- | --- |
| `/api/finetune/upload-dataset` | POST multipart | 上传 JSON/JSONL，返回缓存路径 |
| `/api/finetune/create` | POST | 创建任务，参数同前端表单 |
| `/api/finetune/tasks` | GET | 任务列表（含进度、Loss、日志、输出目录） |
| `/api/finetune/tasks/{task_id}` | GET | 获取单个任务详情 |
| `/api/finetune/tasks/{task_id}` | DELETE | 删除任务 |
| `/api/finetune/tasks/{task_id}/cancel` | POST | 取消运行中的任务 |
| `/api/finetune/tasks/{task_id}/download` | GET | 下载任务产出的模型文件 |
| `/api/finetune/models` | GET | 基础 + 微调模型清单（type: base/finetuned） |
| `/api/finetune/models/base` | GET | 获取可用基础模型列表 |
| `/api/finetune/current-model` | GET | 当前对话使用的模型路径 |
| `/api/finetune/switch-model?model_path=...` | POST | 触发热切换；返回 `llm_service_restarted` 标记 |
| `/api/finetune/use-as-backend` | POST | 通过 task_id 切换（表格快捷按钮使用） |
| `/api/system/gpu-info` | GET | GPU 数量、显存、推荐配置，用于 UI 提示 |
| `/api/finetune/prepare-sage-docs` | POST | 下载 docs-public 并生成训练样本（SAGE RAG 数据集） |

## 5. 热切换实现细节

```python
# config/backend/api.py
@app.post("/api/finetune/switch-model")
async def switch_model(model_path: str):
    chat_manager = ChatModeManager()
    chat_manager._stop_llm_service()
    restarted = chat_manager._start_llm_service(model=model_path)
    return {"current_model": model_path, "llm_service_restarted": restarted}
```

- LLM 通过 `LLMAPIServer` 以后台线程启动，端口 `8001`（可通过 `SAGE_STUDIO_LLM_PORT` 修改）。
- 成功后更新 `SAGE_CHAT_BASE_URL` 与 `SAGE_CHAT_MODEL` 环境变量，Gateway 立刻改用新的 API。
- 若 `sage-llm` 未安装或 vLLM 缺失，`_start_llm_service` 返回 False，前端提示需要手动重启。

## 6. 快速参考表

| 场景 | 操作 | 预期反馈 |
| --- | --- | --- |
| 微调刚完成想立即使用 | 任务表格 ✅ 行 → 「切换为对话后端」 | toast: ✅ 模型已切换并生效 |
| 想在 Chat 中确认当前模型 | Chat 面板顶部 “当前模型” 标签 | 显示模型名/路径 |
| 仅用云端 API | `sage studio start --no-llm` 或设置 `SAGE_FORCE_CLOUD_API=true` | 下拉框提示“云端” |
| GPU 不足提示 | 创建任务时弹出 Warning Modal | 可继续任务但建议调小参数 |
| 需要日志 | Finetune 列表中点击任务 → 日志抽屉 / `~/.sage/studio_finetune/<task>/logs.txt` | 实时刷新 |

## 7. 故障排查

| 症状 | 处理步骤 |
| --- | --- |
| 下拉框没有微调模型 | 检查任务状态是否 `completed`；刷新页面；查看 `~/.sage/studio_finetune/` 是否包含 `finetune_meta.json` |
| 切换后 Chat 仍使用旧模型 | 查看 toast 是否为 ⚠️；若是，运行 `sage studio restart` 或确保 `--llm` 未关闭 |
| 训练一直排队 | 受限于单 GPU；`finetune_manager` 顺序执行，可取消排队任务或等待当前任务完成 |
| 创建任务失败 | 检查上传的数据集格式；查看后端日志 `~/.sage/studio/finetune_api.log` |
| 热切换时报 “LLMAPIServer 不可用” | 确认安装 `isage-common` + `vllm`，或在 CLI 中执行 `pip install vllm` |

## 8. 保养 & TODO

- ✅ 已实现：任务管理、GPU 建议、实时日志、模型热切换、SAGE 文档一键准备。
- 🧭 规划中：
  - 多 GPU 并发训练队列。
  - UI 内的模型分组/搜索。
  - LoRA → merged 自动合并工具链。
  - 更细粒度的权限控制（多用户场景）。

更新此文档时请同步检查以下文件：
- `frontend/src/components/FinetunePanel.tsx`
- `services/finetune_manager.py`
- `chat_manager.py`
若新增 API 或按钮，需要在“API 参考”与“快速参考表”中补充，避免再次出现重复文档。

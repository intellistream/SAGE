# Task 3.4: Chat API 路由集成

## 目标

将 AgentOrchestrator 集成到现有的 Chat API 路由。

## 依赖

- Task 3.2 (Orchestrator 核心)
- Task 3.3 (Stream Handler)

## 文件位置

`packages/sage-studio/src/sage/studio/routes/chat.py`（修改现有文件）

## 提示词

````
请将 AgentOrchestrator 集成到现有的 Chat API 路由。

## 背景
SAGE Studio 已有 chat 路由，需要修改以支持 Multi-Agent 模式。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/routes/chat.py

2. 新增/修改接口:
   - POST /api/chat/agent - 使用 Multi-Agent 处理
   - 保留原有 /api/chat/* 接口兼容

3. 请求格式:
   ```json
   {
     "message": "string",
     "session_id": "string",
     "history": [{"role": "user", "content": "..."}, ...]
   }
````

## 代码模板

```python
# 在现有 chat.py 中添加:

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sage.studio.services.agent_orchestrator import get_orchestrator
from sage.studio.services.stream_handler import get_stream_handler


class AgentChatRequest(BaseModel):
    """Agent 聊天请求"""
    message: str
    session_id: str
    history: list[dict[str, str]] | None = None


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/agent")
async def agent_chat(request: AgentChatRequest):
    """Multi-Agent 聊天接口"""
    orchestrator = get_orchestrator()
    stream_handler = get_stream_handler()

    source = orchestrator.process_message(
        message=request.message,
        session_id=request.session_id,
        history=request.history,
    )

    return stream_handler.create_response(source)


@router.post("/agent/sync")
async def agent_chat_sync(request: AgentChatRequest):
    """非流式 Agent 聊天接口（调试用）"""
    orchestrator = get_orchestrator()

    steps = []
    text_parts = []

    async for item in orchestrator.process_message(
        message=request.message,
        session_id=request.session_id,
        history=request.history,
    ):
        if hasattr(item, "step_id"):  # AgentStep
            steps.append(asdict(item))
        else:  # str
            text_parts.append(item)

    return {
        "steps": steps,
        "response": "".join(text_parts),
    }
```

## 注意

- 保持与现有路由兼容
- 流式接口返回 StreamingResponse
- 提供同步接口便于调试

```

## 验收标准
- [ ] /api/chat/agent 返回 SSE 流
- [ ] /api/chat/agent/sync 返回 JSON
- [ ] 现有接口不受影响
- [ ] 错误处理完善
```

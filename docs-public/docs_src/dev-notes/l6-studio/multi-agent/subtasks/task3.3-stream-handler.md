# Task 3.3: 流式响应处理

## 目标

实现流式响应的封装和处理，支持 Server-Sent Events (SSE)。

## 依赖

- Task 3.1 (AgentStep Schema)
- Task 3.2 (Orchestrator 核心)

## 文件位置

`packages/sage-studio/src/sage/studio/services/stream_handler.py`

## 提示词

```
请实现流式响应处理模块，支持 Server-Sent Events (SSE)。

## 背景
Multi-Agent 系统需要流式输出执行步骤和回复文本。
前端通过 SSE 接收实时更新。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/services/stream_handler.py

2. 支持两种流式事件:
   - step: AgentStep 对象（JSON 序列化）
   - text: 回复文本片段

3. SSE 格式:
```

event: step data: {"step_id": "abc", "type": "reasoning", ...}

event: text data: 你好

event: text data: ，我是

````

## 代码模板
```python
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any, AsyncGenerator

from starlette.responses import StreamingResponse

from sage.studio.services.agent_orchestrator import AgentStep

logger = logging.getLogger(__name__)


class SSEFormatter:
 """Server-Sent Events 格式化器"""

 @staticmethod
 def format_event(event: str, data: str) -> str:
     """格式化 SSE 事件"""
     return f"event: {event}\ndata: {data}\n\n"

 @staticmethod
 def format_step(step: AgentStep) -> str:
     """格式化 AgentStep 为 SSE"""
     data = json.dumps(asdict(step), ensure_ascii=False)
     return SSEFormatter.format_event("step", data)

 @staticmethod
 def format_text(text: str) -> str:
     """格式化文本片段为 SSE"""
     return SSEFormatter.format_event("text", text)

 @staticmethod
 def format_error(error: str) -> str:
     """格式化错误为 SSE"""
     data = json.dumps({"error": error}, ensure_ascii=False)
     return SSEFormatter.format_event("error", data)

 @staticmethod
 def format_done() -> str:
     """格式化完成事件"""
     return SSEFormatter.format_event("done", "")


class StreamHandler:
 """流式响应处理器"""

 def __init__(self):
     self.formatter = SSEFormatter()

 async def process_stream(
     self,
     source: AsyncGenerator[AgentStep | str, None],
 ) -> AsyncGenerator[str, None]:
     """将 AgentStep/str 流转换为 SSE 字符串流"""
     try:
         async for item in source:
             if isinstance(item, AgentStep):
                 yield self.formatter.format_step(item)
             elif isinstance(item, str):
                 yield self.formatter.format_text(item)
             else:
                 logger.warning(f"Unknown item type: {type(item)}")
     except Exception as e:
         logger.error(f"Stream error: {e}")
         yield self.formatter.format_error(str(e))
     finally:
         yield self.formatter.format_done()

 def create_response(
     self,
     source: AsyncGenerator[AgentStep | str, None],
 ) -> StreamingResponse:
     """创建 SSE StreamingResponse"""
     return StreamingResponse(
         self.process_stream(source),
         media_type="text/event-stream",
         headers={
             "Cache-Control": "no-cache",
             "Connection": "keep-alive",
             "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
         },
     )


# 单例
_stream_handler: StreamHandler | None = None


def get_stream_handler() -> StreamHandler:
 global _stream_handler
 if _stream_handler is None:
     _stream_handler = StreamHandler()
 return _stream_handler
````

## 注意

- 确保 JSON 中文不转义 (ensure_ascii=False)
- 异常处理发送 error 事件
- 流结束发送 done 事件

```

## 验收标准
- [ ] SSE 格式正确
- [ ] AgentStep 正确序列化
- [ ] 文本片段正确传输
- [ ] 错误和完成事件正常
```

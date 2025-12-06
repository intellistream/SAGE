"""
Stream Handler for Multi-Agent System

Layer: L6 (sage-studio)
Dependencies: AgentStep Schema

提供 Server-Sent Events (SSE) 格式的流式响应处理，
将 Agent 执行步骤和文本流转换为前端可消费的 SSE 流。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, is_dataclass
from typing import TYPE_CHECKING, Any, AsyncGenerator

from starlette.responses import StreamingResponse

if TYPE_CHECKING:
    from sage.studio.models.agent_step import AgentStep

logger = logging.getLogger(__name__)


class SSEFormatter:
    """Server-Sent Events 格式化器

    SSE 格式规范:
    - 每个事件由 "event:" 和 "data:" 字段组成
    - 事件以两个换行符结束
    - 支持的事件类型: step, text, error, done
    """

    @staticmethod
    def format_event(event: str, data: str) -> str:
        """格式化 SSE 事件

        Args:
            event: 事件类型 (step, text, error, done)
            data: 事件数据

        Returns:
            格式化后的 SSE 字符串

        Example:
            >>> SSEFormatter.format_event("text", "Hello")
            'event: text\\ndata: Hello\\n\\n'
        """
        return f"event: {event}\ndata: {data}\n\n"

    @staticmethod
    def format_step(step: AgentStep) -> str:
        """格式化 AgentStep 为 SSE 事件

        将 AgentStep 对象序列化为 JSON 并封装为 SSE 格式。

        Args:
            step: Agent 执行步骤对象

        Returns:
            格式化后的 SSE 字符串
        """
        # 支持 dataclass 和普通对象
        if is_dataclass(step) and not isinstance(step, type):
            step_dict = asdict(step)
        elif hasattr(step, "to_dict"):
            step_dict = step.to_dict()
        elif hasattr(step, "model_dump"):
            # Pydantic v2
            step_dict = step.model_dump()
        elif hasattr(step, "dict"):
            # Pydantic v1
            step_dict = step.dict()
        else:
            step_dict = _serialize_step(step)

        data = json.dumps(step_dict, ensure_ascii=False, default=str)
        return SSEFormatter.format_event("step", data)

    @staticmethod
    def format_text(text: str) -> str:
        """格式化文本片段为 SSE 事件

        Args:
            text: 回复文本片段

        Returns:
            格式化后的 SSE 字符串
        """
        # 处理多行文本：SSE data 字段不能包含换行符
        # 需要将换行符转义或分成多行 data
        escaped_text = text.replace("\n", "\\n")
        return SSEFormatter.format_event("text", escaped_text)

    @staticmethod
    def format_error(error: str) -> str:
        """格式化错误信息为 SSE 事件

        Args:
            error: 错误消息

        Returns:
            格式化后的 SSE 字符串
        """
        data = json.dumps({"error": error}, ensure_ascii=False)
        return SSEFormatter.format_event("error", data)

    @staticmethod
    def format_done() -> str:
        """格式化流结束事件

        Returns:
            格式化后的 SSE 字符串，标记流传输完成
        """
        return SSEFormatter.format_event("done", "[DONE]")


def _serialize_step(step: Any) -> dict[str, Any]:
    """通用步骤序列化

    处理各种可能的 AgentStep 实现。

    Args:
        step: 任意步骤对象

    Returns:
        可 JSON 序列化的字典
    """
    result = {}

    # 尝试获取常见属性
    for attr in [
        "step_id",
        "stepId",
        "type",
        "content",
        "status",
        "metadata",
        "step",
        "timestamp",
        "duration",
        "toolName",
        "toolInput",
        "toolOutput",
    ]:
        if hasattr(step, attr):
            value = getattr(step, attr)
            # 处理枚举值
            if hasattr(value, "value"):
                value = value.value
            result[attr] = value

    return result


class StreamHandler:
    """流式响应处理器

    负责将 Agent 编排器产生的步骤和文本流转换为
    SSE 格式的响应流，供前端实时消费。

    Usage:
        handler = StreamHandler()

        # 创建 SSE 响应
        async def my_generator():
            yield AgentStep(...)
            yield "Hello "
            yield "World"

        response = handler.create_response(my_generator())
    """

    def __init__(self):
        """初始化流式处理器"""
        self.formatter = SSEFormatter()

    async def process_stream(
        self,
        source: AsyncGenerator[Any, None],
    ) -> AsyncGenerator[str, None]:
        """将 AgentStep/str 流转换为 SSE 字符串流

        Args:
            source: 异步生成器，产生 AgentStep 对象或 str 文本片段

        Yields:
            格式化后的 SSE 事件字符串

        Example:
            async for sse_event in handler.process_stream(orchestrator_stream):
                await send_to_client(sse_event)
        """
        try:
            async for item in source:
                if item is None:
                    continue

                # 判断是否为 AgentStep（支持多种实现）
                if _is_agent_step(item):
                    yield self.formatter.format_step(item)
                elif isinstance(item, str):
                    yield self.formatter.format_text(item)
                elif isinstance(item, dict):
                    # 支持直接传入字典格式的步骤
                    data = json.dumps(item, ensure_ascii=False, default=str)
                    yield self.formatter.format_event("step", data)
                else:
                    logger.warning(f"Unknown item type in stream: {type(item)}")
                    # 尝试作为字符串处理
                    yield self.formatter.format_text(str(item))

        except GeneratorExit:
            # 客户端断开连接
            logger.info("Client disconnected from SSE stream")
        except Exception as e:
            logger.error(f"Stream processing error: {e}", exc_info=True)
            yield self.formatter.format_error(str(e))
        finally:
            yield self.formatter.format_done()

    def create_response(
        self,
        source: AsyncGenerator[Any, None],
        headers: dict[str, str] | None = None,
    ) -> StreamingResponse:
        """创建 SSE StreamingResponse

        Args:
            source: 异步生成器，产生 AgentStep 对象或 str 文本片段
            headers: 额外的响应头

        Returns:
            配置好的 StreamingResponse 对象
        """
        default_headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
            "Access-Control-Allow-Origin": "*",  # CORS 支持
        }

        if headers:
            default_headers.update(headers)

        return StreamingResponse(
            self.process_stream(source),
            media_type="text/event-stream",
            headers=default_headers,
        )


def _is_agent_step(obj: Any) -> bool:
    """判断对象是否为 AgentStep 类型

    支持多种 AgentStep 实现：
    - dataclass 版本
    - Pydantic 版本
    - 具有特定属性的对象

    Args:
        obj: 待检查的对象

    Returns:
        True 如果对象是 AgentStep 类型
    """
    if isinstance(obj, str):
        return False

    # 检查类名
    class_name = type(obj).__name__
    if class_name == "AgentStep":
        return True

    # 检查是否具有 AgentStep 的关键属性
    required_attrs = {"type", "content"}
    optional_attrs = {"step_id", "stepId", "step", "status"}

    has_required = all(hasattr(obj, attr) for attr in required_attrs)
    has_optional = any(hasattr(obj, attr) for attr in optional_attrs)

    return has_required and has_optional


# 单例模式
_stream_handler: StreamHandler | None = None


def get_stream_handler() -> StreamHandler:
    """获取 StreamHandler 单例

    Returns:
        StreamHandler 实例
    """
    global _stream_handler
    if _stream_handler is None:
        _stream_handler = StreamHandler()
    return _stream_handler


__all__ = [
    "SSEFormatter",
    "StreamHandler",
    "get_stream_handler",
]

"""
OpenAI Compatible API Adapter

将 OpenAI 格式的请求转换为 SAGE DataStream 执行
"""

import time
from typing import AsyncIterator

from pydantic import BaseModel, Field

from sage.gateway.session import get_session_manager


class ChatMessage(BaseModel):
    """OpenAI 格式的消息"""

    role: str  # system, user, assistant
    content: str
    name: str | None = None


class ChatCompletionRequest(BaseModel):
    """OpenAI /v1/chat/completions 请求格式"""

    model: str = "sage-default"
    messages: list[ChatMessage]
    temperature: float = Field(default=1.0, ge=0, le=2)
    max_tokens: int | None = None
    stream: bool = False
    session_id: str | None = None  # SAGE 扩展：会话 ID


class ChatCompletionChoice(BaseModel):
    """响应中的选择项"""

    index: int
    message: ChatMessage
    finish_reason: str  # stop, length, content_filter


class ChatCompletionUsage(BaseModel):
    """Token 使用统计"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI /v1/chat/completions 响应格式"""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage


class ChatCompletionStreamChoice(BaseModel):
    """流式响应的选择项"""

    index: int
    delta: dict  # {"role": "assistant"} 或 {"content": "text"}
    finish_reason: str | None = None


class ChatCompletionStreamResponse(BaseModel):
    """流式响应格式"""

    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChatCompletionStreamChoice]


class OpenAIAdapter:
    """OpenAI 协议适配器"""

    def __init__(self):
        self.session_manager = get_session_manager()

    async def chat_completions(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse | AsyncIterator[str]:
        """处理 chat completions 请求"""
        # 1. 获取或创建会话
        session = self.session_manager.get_or_create(request.session_id)

        # 2. 添加用户消息到会话
        user_message = request.messages[-1]  # 最后一条消息
        session.add_message(user_message.role, user_message.content)

        # 3. 调用 SAGE Kernel 执行
        # TODO: 实际调用 sage-kernel 的 DataStream API
        # 这里先返回模拟响应
        assistant_response = await self._execute_sage_pipeline(request, session)

        # 4. 添加助手响应到会话
        session.add_message("assistant", assistant_response)
        self.session_manager.persist()

        # 5. 返回响应
        if request.stream:
            return self._create_stream_response(request, session, assistant_response)
        else:
            return self._create_response(request, session, assistant_response)

    async def _execute_sage_pipeline(self, request: ChatCompletionRequest, session) -> str:
        """执行 SAGE DataStream Pipeline"""
        # TODO: 实际实现
        # from sage.kernel.api import LocalEnvironment
        # env = LocalEnvironment(f"chat_{session.id}")
        # ...

        # 临时模拟响应
        user_input = request.messages[-1].content
        return f"Echo: {user_input} (processed by SAGE)"

    def _create_response(
        self, request: ChatCompletionRequest, session, content: str
    ) -> ChatCompletionResponse:
        """创建非流式响应"""
        return ChatCompletionResponse(
            id=f"chatcmpl-{session.id}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="stop",
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=len(request.messages[-1].content.split()),
                completion_tokens=len(content.split()),
                total_tokens=len(request.messages[-1].content.split()) + len(content.split()),
            ),
        )

    async def _create_stream_response(
        self, request: ChatCompletionRequest, session, content: str
    ) -> AsyncIterator[str]:
        """创建流式响应（SSE 格式）"""
        import asyncio

        # 首先发送 role
        chunk = ChatCompletionStreamResponse(
            id=f"chatcmpl-{session.id}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionStreamChoice(index=0, delta={"role": "assistant"}, finish_reason=None)
            ],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"

        # 逐字发送内容（模拟流式效果）
        for char in content:
            chunk = ChatCompletionStreamResponse(
                id=f"chatcmpl-{session.id}",
                created=int(time.time()),
                model=request.model,
                choices=[
                    ChatCompletionStreamChoice(index=0, delta={"content": char}, finish_reason=None)
                ],
            )
            yield f"data: {chunk.model_dump_json()}\n\n"
            await asyncio.sleep(0.02)  # 模拟延迟

        # 发送结束标记
        chunk = ChatCompletionStreamResponse(
            id=f"chatcmpl-{session.id}",
            created=int(time.time()),
            model=request.model,
            choices=[ChatCompletionStreamChoice(index=0, delta={}, finish_reason="stop")],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"

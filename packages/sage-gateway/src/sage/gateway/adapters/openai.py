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

    def _load_api_key_from_config(self) -> str | None:
        """从 ~/.sage/.env.json 加载 DASHSCOPE_API_KEY"""
        import json
        from pathlib import Path

        config_path = Path.home() / ".sage" / ".env.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    return config.get("DASHSCOPE_API_KEY")
            except Exception:
                pass
        return None

    async def chat_completions(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse | AsyncIterator[str]:
        """处理 chat completions 请求"""
        # 1. 获取或创建会话
        session = self.session_manager.get_or_create(request.session_id)

        # 2. 添加用户消息到会话
        user_message = request.messages[-1]  # 最后一条消息
        session.add_message(user_message.role, user_message.content)

        # 3. 调用 SAGE Kernel 执行（已集成 DataStream API）
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
        """
        执行 SAGE RAG Pipeline

        流程:
        1. 文档爬取 (docs-src)
        2. 向量化存储 (ChromaDB)
        3. 检索相关文档
        4. 生成回答 (RAG)
        """
        user_input = request.messages[-1].content

        try:
            # 导入 SAGE Pipeline 组件
            from sage.kernel.api import LocalEnvironment
            from sage.libs.io.source import TextSource
            from sage.libs.io.sink import RetriveSink
            from sage.middleware.operators.rag.retriever import ChromaRetriever
            from sage.middleware.operators.rag.promptor import QAPromptor
            from sage.middleware.operators.rag.generator import OpenAIGenerator
            import os
            from pathlib import Path

            # 创建 Pipeline 环境
            sage_env = LocalEnvironment()

            # 1. Source: 用户输入
            source = TextSource([user_input])

            # 2. Retriever: 从向量数据库检索相关文档
            chroma_config = {
                "persist_directory": str(Path.home() / ".sage" / "vector_db"),
                "collection_name": "sage_docs",
                "top_k": 5,
                "embedding_model": "BAAI/bge-small-zh-v1.5",
            }
            retriever = ChromaRetriever(chroma_config)

            # 3. Promptor: 构建 RAG prompt
            promptor_config = {
                "template": "根据以下文档回答问题：\n\n{{external_corpus}}\n\n问题：{{query}}\n\n回答："
            }
            promptor = QAPromptor(promptor_config)

            # 4. Generator: LLM 生成回答
            # 从环境变量读取配置
            model_name = os.getenv("SAGE_CHAT_MODEL", "qwen-max")
            base_url = os.getenv(
                "SAGE_CHAT_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            api_key = (
                os.getenv("SAGE_CHAT_API_KEY")
                or os.getenv("ALIBABA_API_KEY")
                or os.getenv("DASHSCOPE_API_KEY")
                or self._load_api_key_from_config()
            )

            if not api_key:
                return "[配置错误] 请设置 DASHSCOPE_API_KEY 环境变量以启用 RAG 功能"

            generator_config = {
                "model_name": model_name,
                "base_url": base_url,
                "api_key": api_key,
                "seed": 42,
            }
            generator = OpenAIGenerator(generator_config)

            # 5. Sink: 收集结果
            sink = RetriveSink()

            # 构建 Pipeline
            (
                sage_env.from_source(source)
                .map(retriever)
                .map(promptor)
                .map(generator)
                .add_sink(sink)
            )

            # 执行 Pipeline
            job = sage_env.submit(autostop=True)

            # 等待执行完成
            import asyncio

            while job.is_running():
                await asyncio.sleep(0.1)

            # 获取结果
            results = sink.get_results()
            if results and len(results) > 0:
                # 提取生成的回答
                result = results[0]
                if isinstance(result, dict) and "generated" in result:
                    return result["generated"]
                elif isinstance(result, str):
                    return result
                else:
                    return str(result)
            else:
                return "抱歉，未能生成回答。"

        except Exception as e:
            # 错误处理：返回友好的错误信息
            import traceback

            error_details = traceback.format_exc()
            return f"抱歉，处理您的请求时遇到错误：{str(e)}\n\n详细信息：\n{error_details}"

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

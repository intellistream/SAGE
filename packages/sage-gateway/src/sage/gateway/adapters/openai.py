"""
OpenAI Compatible API Adapter

将 OpenAI 格式的请求转换为 SAGE DataStream 执行
"""

import logging
import time
from pathlib import Path
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
    """OpenAI 协议适配器

    使用持久化的 RAG Pipeline-as-Service 来处理请求：
    - 对话模式：RAG 检索 + 生成回答
    - 工作流模式：调用 Pipeline Builder 生成工作流配置
    """

    def __init__(self):
        self.session_manager = get_session_manager()

        # 启动持久化的 RAG Pipeline
        # 注意：必须在主线程启动，因为 JobManager 需要注册信号处理器
        from sage.gateway.rag_pipeline import RAGPipelineService

        self.rag_pipeline = RAGPipelineService()
        self._pipeline_started = False

        # 延迟启动 Pipeline（在第一次请求时启动）
        # 这样可以避免 Gateway 启动时阻塞，同时确保在主线程中启动

    def _ensure_pipeline_started(self):
        """确保 Pipeline 已启动（懒加载模式）"""
        if self._pipeline_started:
            return

        try:
            import logging

            logger = logging.getLogger(__name__)
            logger.info("Starting RAG Pipeline (first request)...")
            self.rag_pipeline.start()
            self._pipeline_started = True
            logger.info("RAG Pipeline started successfully")
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to start RAG Pipeline: {e}", exc_info=True)

    def _ensure_index_ready_background(self) -> None:
        """后台线程：确保 RAG 索引就绪

        修复: 将索引构建移到后台线程，避免阻塞 Gateway 启动
        这解决了"新建聊天时好时坏"的问题 - Gateway 可能因为索引构建而启动缓慢
        """
        try:
            self._ensure_index_ready()
            self._index_ready = True
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Background index building failed: {e}")
            # 不抛出异常，让 Gateway 继续运行

    def _ensure_index_ready(self) -> None:
        """Ensure RAG vector index is built and ready.

        Checks if index exists at ~/.sage/vector_db/manifest.json
        If not, builds it automatically from docs-public/docs_src
        """
        from pathlib import Path

        logger = logging.getLogger(__name__)

        # Check if index exists
        index_dir = Path.home() / ".sage" / "vector_db"
        manifest_path = index_dir / "manifest.json"

        if manifest_path.exists():
            logger.info(f"RAG index found at {index_dir}")
            return

        # Index doesn't exist, build it
        logger.warning("RAG index not found, building automatically...")

        try:
            # Find source documents
            from sage.common.config.output_paths import find_sage_project_root

            project_root = find_sage_project_root()
            if project_root:
                source_dir = project_root / "docs-public" / "docs_src"
            else:
                # Fallback: try common locations
                source_dir = Path.cwd() / "docs-public" / "docs_src"
                if not source_dir.exists():
                    source_dir = Path.home() / "SAGE" / "docs-public" / "docs_src"

            if not source_dir.exists():
                logger.warning(
                    f"Documentation source not found at {source_dir}. "
                    "RAG功能将不可用。请运行 'sage chat ingest' 手动构建索引。"
                )
                return

            # Build index using IndexBuilder
            self._build_index_from_docs(source_dir, index_dir)
            logger.info(f"✅ RAG index built successfully at {index_dir}")

        except Exception as e:
            logger.error(f"Failed to build RAG index: {e}", exc_info=True)
            logger.warning("RAG功能将不可用。请运行 'sage chat ingest' 手动构建索引。")

    def _build_index_from_docs(self, source_dir: Path, index_dir: Path) -> None:
        """Build RAG index from documentation source.

        Args:
            source_dir: Path to docs_src directory
            index_dir: Path to store the built index
        """
        import sys
        from pathlib import Path as P

        from sage.common.components.sage_embedding import get_embedding_model
        from sage.common.utils.document_processing import (
            iter_markdown_files,
            parse_markdown_sections,
            slugify,
        )
        from sage.middleware.operators.rag.index_builder import IndexBuilder

        logger = logging.getLogger(__name__)

        # Import ChromaVectorStoreAdapter from source (dev mode)
        # This is needed because package isn't reinstalled yet
        chroma_adapter_path = P(__file__).parents[4] / "sage-libs" / "src"
        if chroma_adapter_path.exists():
            sys.path.insert(0, str(chroma_adapter_path))

        try:
            from sage.libs.integrations.chroma_adapter import ChromaVectorStoreAdapter
        except ImportError:
            logger.error("Failed to import ChromaVectorStoreAdapter. Using mock for now.")
            # Fallback: skip index building for now
            logger.warning("Skipping index build - ChromaVectorStoreAdapter not available")
            return

        # Create embedder
        embedder = get_embedding_model("hash", dim=384)  # Use hash for fast startup

        # Backend factory for ChromaDB
        def backend_factory(persist_path: P, dim: int):
            return ChromaVectorStoreAdapter(persist_path, dim)

        # Document processor for Markdown
        def document_processor(src: P) -> list[dict]:
            chunks = []
            for file_path in iter_markdown_files(src):
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                sections = parse_markdown_sections(text)

                if not sections:
                    continue

                rel_path = file_path.relative_to(src)
                doc_title = sections[0]["heading"] if sections else file_path.stem

                for section in sections:
                    chunks.append(
                        {
                            "content": section["content"],
                            "metadata": {
                                "doc_path": str(rel_path),
                                "title": doc_title,
                                "heading": section["heading"],
                                "anchor": slugify(section["heading"]),
                            },
                        }
                    )

            logger.info(f"Processed {len(chunks)} sections from documentation")
            return chunks

        # Build index
        builder = IndexBuilder(backend_factory=backend_factory)
        manifest = builder.build_from_docs(
            source_dir=source_dir,
            persist_path=index_dir,
            embedding_model=embedder,
            index_name="sage_docs",
            chunk_size=800,
            chunk_overlap=160,
            document_processor=document_processor,
        )

        logger.info(f"Index built: {manifest.num_documents} docs, {manifest.num_chunks} chunks")

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
        # 确保 Pipeline 已启动
        self._ensure_pipeline_started()

        # 1. 获取或创建会话
        session = self.session_manager.get_or_create(request.session_id)

        # 2. 添加用户消息到会话
        user_message = request.messages[-1]  # 最后一条消息
        session.add_message(user_message.role, user_message.content)

        # 3. 调用 SAGE Kernel 执行（已集成 DataStream API + sage-memory）
        assistant_response = await self._execute_sage_pipeline(request, session)

        # 4. 添加助手响应到会话
        session.add_message("assistant", assistant_response)

        # 5. 将对话存储到短期记忆服务（sage-memory集成）
        self.session_manager.store_dialog_to_memory(
            session.id, user_message.content, assistant_response
        )

        self.session_manager.persist()

        # 6. 返回响应
        if request.stream:
            return self._create_stream_response(request, session, assistant_response)
        else:
            return self._create_response(request, session, assistant_response)

    async def _execute_sage_pipeline(self, request: ChatCompletionRequest, session) -> str:
        """
        执行 SAGE RAG Pipeline（通过持久化的 Pipeline-as-Service）

        流程:
        1. 从 sage-memory 检索对话历史
        2. 将请求提交到 RAG Pipeline（包含历史记忆上下文）
        3. Pipeline 自动决定：对话模式 vs 工作流生成模式
        4. 返回响应（文本回答 或 工作流配置）
        """
        try:
            # 1. 从短期记忆服务检索对话历史
            memory_history = self.session_manager.retrieve_memory_history(session.id)

            # 2. 准备请求数据
            request_data = {
                "messages": [
                    {"role": msg.role, "content": msg.content} for msg in request.messages
                ],
                "model": request.model,
                "temperature": request.temperature,
                "memory_context": memory_history,  # 传递记忆上下文到 Pipeline
            }

            # 3. 提交到 Pipeline 并等待响应
            response = self.rag_pipeline.process(request_data, timeout=120.0)

            # Handle different response types
            response_type = response.get("type", "chat")

            if response_type == "workflow":
                # Workflow generation response
                workflow_data = response.get("workflow_data", {})
                visual_pipeline = workflow_data.get("visual_pipeline", {})

                # Format response with workflow info
                import json

                workflow_json = json.dumps(visual_pipeline, indent=2, ensure_ascii=False)
                content = response.get("content", "工作流已生成")
                content += f"\n\n```json\n{workflow_json}\n```"

                return content

            elif response_type == "error":
                # Error response
                return response.get("content", "抱歉，处理请求时出错。")

            else:
                # Normal chat response
                content = response.get("content", "")
                sources = response.get("sources", [])

                # If sources are available, append them to the response
                if sources:
                    content += "\n\n---\n\n**参考文档：**\n\n"
                    for source in sources:
                        doc_path = source.get("doc_path", "unknown")
                        heading = source.get("heading", "")
                        source_id = source.get("id", 0)
                        text_preview = source.get("text", "")

                        # Format source citation
                        if heading:
                            content += f"[{source_id}] **{heading}** ({doc_path})\n"
                        else:
                            content += f"[{source_id}] {doc_path}\n"
                        content += f"> {text_preview}\n\n"

                return content

        except Exception as e:
            # Fallback: if Pipeline service fails, use direct LLM
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Pipeline service error: {e}", exc_info=True)

            user_input = request.messages[-1].content
            return await self._fallback_direct_llm(request, user_input)

    async def _fallback_direct_llm(self, request: ChatCompletionRequest, user_input: str) -> str:
        """降级方案：直接调用 LLM（无 RAG）"""
        import os

        from sage.common.components.sage_llm import UnifiedInferenceClient

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
            return "[配置错误] 请设置 DASHSCOPE_API_KEY 环境变量"

        client = UnifiedInferenceClient(
            llm_model=model_name,
            llm_base_url=base_url,
            llm_api_key=api_key,
        )

        messages = [{"role": "user", "content": user_input}]
        return client.chat(messages)

    async def _build_sage_chat_index(self, index_root: Path, index_name: str):
        """后台构建 sage chat 索引（与 sage chat ingest 相同）"""

        logger = logging.getLogger(__name__)
        logger.info("Building SAGE chat index in background...")

        try:
            from sage.common.components.sage_embedding import get_embedding_model
            from sage.common.config.output_paths import find_sage_project_root
            from sage.common.utils.document_processing import parse_markdown_sections
            from sage.middleware.components.sage_db.backend import SageDBBackend
            from sage.middleware.operators.rag.index_builder import IndexBuilder

            # 查找文档源
            project_root = find_sage_project_root()
            if not project_root:
                logger.warning("Project root not found, skipping index build")
                return

            source_dir = project_root / "docs-public" / "docs_src"
            if not source_dir.exists():
                logger.warning(f"Source dir not found: {source_dir}")
                return

            # 创建输出路径
            index_root.mkdir(parents=True, exist_ok=True)
            db_path = index_root / f"{index_name}.sagedb"

            # 创建 embedder
            embedder = get_embedding_model("hash", dim=384)

            # Backend factory
            def backend_factory(persist_path: Path, dim: int):
                return SageDBBackend(persist_path, dim)

            # Document processor
            def document_processor(source_dir: Path):
                for md_file in source_dir.rglob("*.md"):
                    try:
                        with open(md_file, encoding="utf-8") as f:
                            content = f.read()
                        sections = parse_markdown_sections(content)
                        for section in sections:
                            yield {
                                "content": f"{section['heading']}\n\n{section['content']}",
                                "metadata": {
                                    "doc_path": str(md_file.relative_to(source_dir)),
                                    "heading": section["heading"],
                                },
                            }
                    except Exception as e:
                        logger.warning(f"Error processing {md_file}: {e}")
                        continue

            # Build index
            builder = IndexBuilder(backend_factory=backend_factory)
            index_manifest = builder.build_from_docs(
                source_dir=source_dir,
                persist_path=db_path,
                embedding_model=embedder,
                index_name=index_name,
                chunk_size=800,
                chunk_overlap=160,
                document_processor=document_processor,
            )

            # Save manifest
            manifest_data = {
                "index_name": index_name,
                "db_path": str(db_path),
                "created_at": index_manifest.created_at,
                "source_dir": str(source_dir),
                "embedding": {
                    "method": "hash",
                    "dim": 384,
                },
                "chunk_size": 800,
                "chunk_overlap": 160,
                "num_documents": index_manifest.num_documents,
                "num_chunks": index_manifest.num_chunks,
            }

            manifest_file = index_root / f"{index_name}_manifest.json"
            import json

            with open(manifest_file, "w") as f:
                json.dump(manifest_data, f, indent=2)

            logger.info(
                f"✅ Index built: {index_manifest.num_chunks} chunks from {index_manifest.num_documents} docs"
            )

        except Exception as e:
            logger.error(f"Failed to build index: {e}", exc_info=True)

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

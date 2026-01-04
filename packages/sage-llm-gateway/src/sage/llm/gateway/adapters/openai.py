"""
OpenAI Compatible API Adapter

将 OpenAI 格式的请求转换为 SAGE DataStream 执行
"""

import logging
import time
from pathlib import Path
from typing import AsyncIterator

from pydantic import BaseModel, Field

from sage.libs.agentic.intent import IntentClassifier, IntentResult, UserIntent
from sage.llm.gateway.session import get_session_manager

# Try to import Agentic components (L3)
try:
    from sage.libs.agentic.agents.action.mcp_registry import MCPRegistry
    from sage.libs.agentic.agents.planning.simple_llm_planner import SimpleLLMPlanner as LLMPlanner
    from sage.libs.agentic.agents.profile.profile import BaseProfile
    from sage.libs.agentic.agents.runtime.agent import AgentRuntime
    from sage.middleware.operators.agentic.refined_searcher import RefinedSearcherOperator
    from sage.middleware.operators.rag.generator import OpenAIGenerator
    from sage.middleware.operators.tools.arxiv_searcher import ArxivSearcher
    from sage.middleware.operators.tools.duckduckgo_searcher import DuckDuckGoSearcher

    HAS_AGENTIC = True
except ImportError:
    HAS_AGENTIC = False

logger = logging.getLogger(__name__)


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

        try:
            self.intent_classifier: IntentClassifier | None = IntentClassifier(
                mode="keyword", fallback_modes=["llm"]
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Intent classifier unavailable: %s", exc)
            self.intent_classifier = None

        # 启动持久化的 RAG Pipeline
        # 注意：必须在主线程启动，因为 JobManager 需要注册信号处理器
        from sage.llm.gateway.rag_pipeline import RAGPipelineService

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
        """从 ~/.sage/.env.json 加载 SAGE_CHAT_API_KEY（兼容旧字段）。"""
        import json
        from pathlib import Path

        config_path = Path.home() / ".sage" / ".env.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                    return config.get("SAGE_CHAT_API_KEY")
            except Exception:
                pass
        return None

    async def _classify_intent(self, query: str) -> IntentResult | None:
        """Run L3 intent classifier; swallow failures to keep gateway resilient."""

        if self.intent_classifier is None:
            return None

        try:
            return await self.intent_classifier.classify(query)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Intent classification failed: %s", exc)
            return None

    @staticmethod
    def _is_agentic_intent(intent_result: IntentResult | None) -> bool:
        if intent_result is None:
            return False
        if intent_result.intent == UserIntent.KNOWLEDGE_QUERY:
            return intent_result.is_high_confidence(threshold=0.5)
        return False

    @staticmethod
    def _should_force_agentic(query: str) -> bool:
        """Heuristic to route obvious research requests to the agentic path.

        Covers common research phrases even if the intent classifier returns low confidence.
        """

        research_keywords = [
            r"论文",
            r"引用",
            r"arxiv",
            r"paper",
            r"papers",
            r"调研",
            r"最新.*(论文|paper)",
            r"research",
            r"文献",
        ]

        import re

        lowered = query.lower()
        for pattern in research_keywords:
            if re.search(pattern, lowered, re.IGNORECASE):
                return True
        return False

    def _create_agent_runtime(self, request: ChatCompletionRequest):
        """Helper to create AgentRuntime instance"""
        import os

        # 1. Setup Tools (Using L4 Operator)
        tools = []
        for tool_ctor in (DuckDuckGoSearcher, ArxivSearcher):
            try:
                tools.append(tool_ctor())
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to init tool %s: %s", tool_ctor.__name__, exc)

        # Use RefinedSearcherOperator which wraps SearcherBot + Refiner
        search_operator = RefinedSearcherOperator(
            tools=tools, refiner_config={"algorithm": "simple", "max_tokens": 2000}
        )

        registry = MCPRegistry()
        registry.register(search_operator)

        # 2. Setup Planner & Generator
        # Try to get base_url from env first, then fall back to local ports
        from sage.common.config.ports import SagePorts

        base_url_env = os.getenv("SAGE_CHAT_BASE_URL")
        if base_url_env:
            base_url_env = base_url_env.rstrip("/")
            if not base_url_env.endswith("/v1"):
                base_url_env = base_url_env + "/v1"

        def _is_llm_alive(url: str) -> bool:
            import httpx

            try:
                resp = httpx.get(url.rstrip("/") + "/models", timeout=0.6)
                return resp.status_code == 200
            except Exception:
                return False

        # Prefer reachable local endpoints first, then fallback
        candidates: list[str | None] = [
            base_url_env,
            f"http://localhost:{SagePorts.get_recommended_llm_port()}/v1",
            f"http://localhost:{SagePorts.BENCHMARK_LLM}/v1",
        ]

        base_url = None
        for candidate in candidates:
            if candidate and _is_llm_alive(candidate):
                base_url = candidate
                break

        if not base_url:
            # Last resort: use env even if unreachable to surface clearer error
            base_url = base_url_env or f"http://localhost:{SagePorts.BENCHMARK_LLM}/v1"

        gen_config = {
            "method": "openai",
            "model_name": self._resolve_model_name(request.model),
            "base_url": base_url,
            # Use dummy if no API key; local vLLM does not require one.
            "api_key": os.getenv("SAGE_CHAT_API_KEY", "dummy"),
        }

        logger.info(
            "Agent runtime generator base_url=%s model=%s",
            gen_config["base_url"],
            gen_config["model_name"],
        )

        try:
            generator = OpenAIGenerator(gen_config)
        except Exception as e:
            logger.error(f"Failed to init OpenAIGenerator: {e}")
            raise e

        planner = LLMPlanner(generator=generator)

        # 3. Setup Profile
        profile = BaseProfile(
            name="SageResearcher",
            role="Research Assistant",
            goals=["Provide accurate information based on search results.", "Verify sources."],
        )

        return AgentRuntime(profile=profile, planner=planner, tools=registry)

    async def _execute_agent_runtime(self, request: ChatCompletionRequest, session) -> str:
        """Execute request using L3 AgentRuntime"""
        if not HAS_AGENTIC:
            return "Agentic capabilities are not available (missing dependencies)."

        import asyncio

        user_query = request.messages[-1].content

        try:
            runtime = self._create_agent_runtime(request)
        except Exception:
            return "Failed to initialize Agent Runtime."

        # 4. Run Agent
        # Run in thread
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, runtime.execute, user_query)
        except Exception as exc:  # noqa: BLE001
            logger.error("Agent runtime failed: %s", exc)
            return (
                "Agent runtime failed to reach an LLM backend. "
                "请启动本地 vLLM 服务 (默认端口 8001/8901) 或配置 SAGE_CHAT_BASE_URL。"
            )

        return result.get("reply", "No reply generated.")

    async def _stream_agent_runtime(
        self, request: ChatCompletionRequest, session
    ) -> AsyncIterator[str]:
        """Stream execution of L3 AgentRuntime with reasoning steps"""
        import json

        if not HAS_AGENTIC:
            yield f"data: {json.dumps({'choices': [{'delta': {'content': 'Agentic capabilities missing.'}}]}, ensure_ascii=False)}\n\n"
            return

        import asyncio
        import time
        import uuid

        user_query = request.messages[-1].content

        try:
            runtime = self._create_agent_runtime(request)
        except Exception as e:
            yield f"data: {json.dumps({'choices': [{'delta': {'content': f'Failed to init agent: {e}'}}]}, ensure_ascii=False)}\n\n"
            return

        # Helper to run step() generator in a thread and yield events
        # Since we can't easily iterate a sync generator in a thread and yield async,
        # we will collect events in chunks or just run it synchronously for now (blocking loop)
        # OR better: use a queue and a worker thread.

        queue = asyncio.Queue()

        def worker():
            try:
                for event in runtime.step(user_query):
                    asyncio.run_coroutine_threadsafe(queue.put(event), loop)
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)  # Sentinel
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "error", "content": str(e)}), loop
                )
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop = asyncio.get_running_loop()
        # Start worker thread
        import threading

        t = threading.Thread(target=worker)
        t.start()

        # Consume queue
        while True:
            event = await queue.get()
            if event is None:
                break

            event_type = event.get("type")

            if event_type == "plan":
                # Convert plan to reasoning step
                steps = event.get("steps", [])
                plan_text = "\n".join(
                    [f"{i + 1}. {s.get('type')}: {s.get('name', '')}" for i, s in enumerate(steps)]
                )

                step_id = str(uuid.uuid4())[:8]
                reasoning_step = {
                    "type": "reasoning_step",
                    "step": {
                        "id": step_id,
                        "type": "plan",
                        "title": "生成计划",
                        "content": f"已生成执行计划:\n{plan_text}",
                        "status": "completed",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                }
                yield f"data: {json.dumps(reasoning_step, ensure_ascii=False)}\n\n"

            elif event_type == "action":
                # Tool call started
                tool_name = event.get("tool")
                tool_args = event.get("args")

                step_id = str(uuid.uuid4())[:8]
                reasoning_step = {
                    "type": "reasoning_step",
                    "step": {
                        "id": step_id,
                        "type": "tool",
                        "title": f"调用工具: {tool_name}",
                        "content": f"参数: {json.dumps(tool_args, ensure_ascii=False)}",
                        "status": "running",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                }
                yield f"data: {json.dumps(reasoning_step, ensure_ascii=False)}\n\n"

                # Store step_id to update it later (simplified: just emit a new completed step for observation)

            elif event_type == "observation":
                # Tool output
                content = str(event.get("content"))
                # Emit a completed step or update previous?
                # For simplicity, emit a new "Observation" step
                step_id = str(uuid.uuid4())[:8]
                reasoning_step = {
                    "type": "reasoning_step",
                    "step": {
                        "id": step_id,
                        "type": "observation",
                        "title": "工具输出",
                        "content": content[:500] + "..." if len(content) > 500 else content,
                        "status": "completed",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                }
                yield f"data: {json.dumps(reasoning_step, ensure_ascii=False)}\n\n"

            elif event_type == "reply":
                # Final answer - stream it
                content = event.get("content", "")
                # Simulate streaming the content
                chunk_size = 10
                for i in range(0, len(content), chunk_size):
                    chunk = content[i : i + chunk_size]
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.01)

            elif event_type == "error":
                error_content = event.get("content")
                friendly = (
                    f"Error: {error_content}. 请确认本地 vLLM 已启动 (默认 8001/8901) "
                    "或配置 SAGE_CHAT_BASE_URL 指向可用的 LLM 服务。"
                )
                yield f"data: {json.dumps({'choices': [{'delta': {'content': friendly}}]}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    def _resolve_model_name(self, model_name: str) -> str:
        """Resolve 'sage-default' to the actual model name running on the backend."""
        if model_name != "sage-default":
            return model_name

        # 1. Try to get default model from RAG pipeline's client
        try:
            if hasattr(self, "rag_pipeline") and hasattr(self.rag_pipeline, "chat_map"):
                client = self.rag_pipeline.chat_map._get_llm_client()
                # Force refresh/fetch of default model
                resolved = client._get_default_llm_model()
                if resolved and resolved != "default":
                    return resolved
        except Exception as e:
            logger.warning(f"Failed to resolve default model via RAG pipeline: {e}")

        # 2. Try to query vLLM directly
        try:
            import httpx

            from sage.common.config.ports import SagePorts

            # Try common ports
            ports = [SagePorts.LLM_DEFAULT, SagePorts.BENCHMARK_LLM]
            for port in ports:
                try:
                    with httpx.Client(timeout=1.0) as client:
                        resp = client.get(f"http://localhost:{port}/v1/models")
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("data") and len(data["data"]) > 0:
                                return data["data"][0]["id"]
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Failed to resolve default model via direct query: {e}")

        return "gpt-3.5-turbo"  # Fallback if resolution fails

    async def chat_completions(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse | AsyncIterator[str]:
        """处理 chat completions 请求"""
        # 确保 Pipeline 已启动
        self._ensure_pipeline_started()

        # Resolve model name
        request.model = self._resolve_model_name(request.model)

        # 1. 获取或创建会话
        session = self.session_manager.get_or_create(request.session_id)

        # 2. 添加用户消息到会话
        user_message = request.messages[-1]  # 最后一条消息
        session.add_message(user_message.role, user_message.content)

        # Check for Agentic Intent (Track 3)
        intent_result = await self._classify_intent(user_message.content)
        force_agentic = self._should_force_agentic(user_message.content)

        if HAS_AGENTIC and (self._is_agentic_intent(intent_result) or force_agentic):
            logger.info("Detected Agentic Intent. Switching to AgentRuntime.")

            if request.stream:
                return self._stream_agent_runtime(request, session)
            else:
                try:
                    assistant_response = await self._execute_agent_runtime(request, session)
                    session.add_message("assistant", assistant_response)
                    self.session_manager.store_dialog_to_memory(
                        session.id, user_message.content, assistant_response
                    )
                    self.session_manager.persist()
                    return self._create_response(request, session, assistant_response)
                except Exception as e:
                    logger.error(f"Agent execution failed: {e}. Fallback to RAG.")
                    # Fallback to normal flow

        # 3. 如果是流式请求，使用增强版流式响应（包含推理步骤）
        if request.stream:
            return self._create_stream_response_with_reasoning(request, session)

        # 4. 非流式请求：执行 Pipeline 并返回完整响应
        assistant_response = await self._execute_sage_pipeline(request, session)
        session.add_message("assistant", assistant_response)
        self.session_manager.store_dialog_to_memory(
            session.id, user_message.content, assistant_response
        )
        self.session_manager.persist()
        return self._create_response(request, session, assistant_response)

    async def _create_stream_response_with_reasoning(
        self, request: ChatCompletionRequest, session
    ) -> AsyncIterator[str]:
        """创建带推理步骤的流式响应 - 方案B实现

        直接在 Gateway 层编排各组件，实现真正的流式推理展示。

        发送顺序：
        1. thinking - 分析用户意图
        2. workflow/retrieval - 根据意图执行工作流生成或文档检索
        3. analysis - 分析处理结果
        4. conclusion - 生成最终回答
        5. 推理结束事件
        6. 最终回答内容（流式）
        7. 完成标记
        """
        import asyncio
        import json
        import time
        import uuid

        user_input = request.messages[-1].content
        start_time = time.time()

        logger.info(f"[Reasoning] Starting stream response for: {user_input[:50]}")

        # 收集推理步骤，用于保存到消息 metadata
        collected_reasoning_steps: list[dict] = []

        # ============ Step 1: 思考步骤 ============
        thinking_step_id = str(uuid.uuid4())[:8]
        thinking_step = {
            "type": "reasoning_step",
            "step": {
                "id": thinking_step_id,
                "type": "thinking",
                "title": "分析问题",
                "content": f"正在分析用户意图: {user_input[:100]}{'...' if len(user_input) > 100 else ''}",
                "status": "running",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }
        yield f"data: {json.dumps(thinking_step, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)

        # 检测请求类型
        is_workflow_request = self._detect_workflow_intent(user_input)
        is_casual_chat = self._detect_casual_chat(user_input)

        # 更新思考步骤
        intent_description = (
            "检测到工作流生成意图"
            if is_workflow_request
            else "检测到闲聊"
            if is_casual_chat
            else "检测到知识问答意图"
        )
        thinking_duration = int((time.time() - start_time) * 1000)
        thinking_update = {
            "type": "reasoning_step_update",
            "step_id": thinking_step_id,
            "updates": {
                "status": "completed",
                "content": intent_description,
                "duration": thinking_duration,
            },
        }
        yield f"data: {json.dumps(thinking_update, ensure_ascii=False)}\n\n"

        # 收集思考步骤
        collected_reasoning_steps.append(
            {
                "id": thinking_step_id,
                "type": "thinking",
                "title": "分析问题",
                "content": intent_description,
                "status": "completed",
                "duration": thinking_duration,
            }
        )

        response = {}
        sources = []

        if is_workflow_request:
            # ============ 工作流生成路径 ============
            workflow_step_id = str(uuid.uuid4())[:8]
            workflow_step = {
                "type": "reasoning_step",
                "step": {
                    "id": workflow_step_id,
                    "type": "workflow",
                    "title": "生成工作流",
                    "content": "正在调用 LLM 生成工作流配置...",
                    "status": "running",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            }
            yield f"data: {json.dumps(workflow_step, ensure_ascii=False)}\n\n"

            workflow_start = time.time()
            try:
                # 真实调用 LLMWorkflowGenerator
                workflow_result = await asyncio.to_thread(
                    self._generate_workflow_direct, user_input
                )

                workflow_duration = int((time.time() - workflow_start) * 1000)

                if workflow_result.get("success"):
                    visual_pipeline = workflow_result.get("visual_pipeline", {})
                    pipeline_name = visual_pipeline.get("name", "自定义工作流")
                    node_count = len(visual_pipeline.get("nodes", []))

                    workflow_update = {
                        "type": "reasoning_step_update",
                        "step_id": workflow_step_id,
                        "updates": {
                            "status": "completed",
                            "content": f"已生成工作流: {pipeline_name} ({node_count} 个节点)",
                            "duration": workflow_duration,
                        },
                    }
                    response = {
                        "type": "workflow",
                        "content": workflow_result.get("message", "工作流已生成"),
                        "workflow_data": {"visual_pipeline": visual_pipeline},
                    }
                else:
                    workflow_update = {
                        "type": "reasoning_step_update",
                        "step_id": workflow_step_id,
                        "updates": {
                            "status": "error",
                            "content": f"生成失败: {workflow_result.get('error', '未知错误')}",
                            "duration": workflow_duration,
                        },
                    }
                    response = {
                        "type": "error",
                        "content": f"抱歉，工作流生成失败: {workflow_result.get('error')}",
                    }

                yield f"data: {json.dumps(workflow_update, ensure_ascii=False)}\n\n"

                # 收集工作流步骤
                collected_reasoning_steps.append(
                    {
                        "id": workflow_step_id,
                        "type": "workflow",
                        "title": "生成工作流",
                        "content": workflow_update["updates"]["content"],
                        "status": workflow_update["updates"]["status"],
                        "duration": workflow_duration,
                    }
                )

            except Exception as e:
                logger.error(f"Workflow generation error: {e}", exc_info=True)
                workflow_duration = int((time.time() - workflow_start) * 1000)
                workflow_update = {
                    "type": "reasoning_step_update",
                    "step_id": workflow_step_id,
                    "updates": {
                        "status": "error",
                        "content": f"生成异常: {str(e)[:100]}",
                        "duration": workflow_duration,
                    },
                }
                yield f"data: {json.dumps(workflow_update, ensure_ascii=False)}\n\n"

                # 收集错误步骤
                collected_reasoning_steps.append(
                    {
                        "id": workflow_step_id,
                        "type": "workflow",
                        "title": "生成工作流",
                        "content": f"生成异常: {str(e)[:100]}",
                        "status": "error",
                        "duration": workflow_duration,
                    }
                )
                response = {"type": "error", "content": f"抱歉，工作流生成出错: {e}"}

        elif is_casual_chat:
            # ============ 闲聊路径（无需检索） ============
            chat_step_id = str(uuid.uuid4())[:8]
            chat_step = {
                "type": "reasoning_step",
                "step": {
                    "id": chat_step_id,
                    "type": "analysis",
                    "title": "生成回复",
                    "content": "直接生成对话回复...",
                    "status": "running",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            }
            yield f"data: {json.dumps(chat_step, ensure_ascii=False)}\n\n"

            chat_start = time.time()
            try:
                response = await asyncio.to_thread(self._generate_casual_response, user_input)
                chat_duration = int((time.time() - chat_start) * 1000)

                chat_update = {
                    "type": "reasoning_step_update",
                    "step_id": chat_step_id,
                    "updates": {
                        "status": "completed",
                        "content": "回复已生成",
                        "duration": chat_duration,
                    },
                }
                yield f"data: {json.dumps(chat_update, ensure_ascii=False)}\n\n"

                # 收集闲聊步骤
                collected_reasoning_steps.append(
                    {
                        "id": chat_step_id,
                        "type": "analysis",
                        "title": "生成回复",
                        "content": "回复已生成",
                        "status": "completed",
                        "duration": chat_duration,
                    }
                )

            except Exception as e:
                logger.error(f"Chat response error: {e}", exc_info=True)
                response = {"type": "chat", "content": "你好！有什么可以帮助你的吗？"}
                # 收集错误步骤
                collected_reasoning_steps.append(
                    {
                        "id": chat_step_id,
                        "type": "analysis",
                        "title": "生成回复",
                        "content": "生成回复时出错",
                        "status": "error",
                        "duration": 0,
                    }
                )

        else:
            # ============ RAG 检索路径 ============
            retrieval_step_id = str(uuid.uuid4())[:8]
            retrieval_step = {
                "type": "reasoning_step",
                "step": {
                    "id": retrieval_step_id,
                    "type": "retrieval",
                    "title": "检索文档",
                    "content": "正在从知识库检索相关文档...",
                    "status": "running",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            }
            yield f"data: {json.dumps(retrieval_step, ensure_ascii=False)}\n\n"

            retrieval_start = time.time()
            try:
                # 执行检索
                rag_result = await asyncio.to_thread(
                    self._perform_rag_retrieval, user_input, request.model
                )
                sources = rag_result.get("sources", [])
                retrieval_duration = int((time.time() - retrieval_start) * 1000)

                # 更新检索步骤
                source_summary = f"检索到 {len(sources)} 个相关文档"
                if sources:
                    top_sources = [s.get("doc_path", "").split("/")[-1] for s in sources[:3]]
                    source_summary += f": {', '.join(top_sources)}"

                retrieval_update = {
                    "type": "reasoning_step_update",
                    "step_id": retrieval_step_id,
                    "updates": {
                        "status": "completed",
                        "content": source_summary,
                        "duration": retrieval_duration,
                    },
                }
                yield f"data: {json.dumps(retrieval_update, ensure_ascii=False)}\n\n"

                # 分析步骤
                analysis_step_id = str(uuid.uuid4())[:8]
                analysis_step = {
                    "type": "reasoning_step",
                    "step": {
                        "id": analysis_step_id,
                        "type": "analysis",
                        "title": "分析文档",
                        "content": "正在分析检索到的文档并生成回答...",
                        "status": "running",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    },
                }
                yield f"data: {json.dumps(analysis_step, ensure_ascii=False)}\n\n"

                analysis_start = time.time()

                # 生成回答
                memory_history = self.session_manager.retrieve_memory_history(session.id)
                answer = await asyncio.to_thread(
                    self._generate_rag_answer, user_input, sources, memory_history, request.model
                )
                analysis_duration = int((time.time() - analysis_start) * 1000)

                analysis_update = {
                    "type": "reasoning_step_update",
                    "step_id": analysis_step_id,
                    "updates": {
                        "status": "completed",
                        "content": "回答已生成",
                        "duration": analysis_duration,
                    },
                }
                yield f"data: {json.dumps(analysis_update, ensure_ascii=False)}\n\n"

                # 收集检索和分析步骤
                collected_reasoning_steps.append(
                    {
                        "id": retrieval_step_id,
                        "type": "retrieval",
                        "title": "检索文档",
                        "content": source_summary,
                        "status": "completed",
                        "duration": retrieval_duration,
                    }
                )
                collected_reasoning_steps.append(
                    {
                        "id": analysis_step_id,
                        "type": "analysis",
                        "title": "分析文档",
                        "content": "回答已生成",
                        "status": "completed",
                        "duration": analysis_duration,
                    }
                )

                response = {"type": "chat", "content": answer, "sources": sources}

            except Exception as e:
                logger.error(f"RAG retrieval error: {e}", exc_info=True)
                retrieval_duration = int((time.time() - retrieval_start) * 1000)
                retrieval_update = {
                    "type": "reasoning_step_update",
                    "step_id": retrieval_step_id,
                    "updates": {
                        "status": "error",
                        "content": f"检索失败: {str(e)[:100]}",
                        "duration": retrieval_duration,
                    },
                }
                yield f"data: {json.dumps(retrieval_update, ensure_ascii=False)}\n\n"

                # 收集错误步骤
                collected_reasoning_steps.append(
                    {
                        "id": retrieval_step_id,
                        "type": "retrieval",
                        "title": "检索文档",
                        "content": f"检索失败: {str(e)[:100]}",
                        "status": "error",
                        "duration": retrieval_duration,
                    }
                )
                response = {"type": "error", "content": f"抱歉，检索文档时出错: {e}"}

        # ============ 结论步骤 ============
        conclusion_step = {
            "type": "reasoning_step",
            "step": {
                "id": str(uuid.uuid4())[:8],
                "type": "conclusion",
                "title": "整理回答",
                "content": "正在整理最终回答...",
                "status": "completed",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "duration": 50,
            },
        }
        yield f"data: {json.dumps(conclusion_step, ensure_ascii=False)}\n\n"
        collected_reasoning_steps.append(conclusion_step["step"])

        # ============ 推理结束事件 ============
        reasoning_end = {"type": "reasoning_end"}
        yield f"data: {json.dumps(reasoning_end, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)

        # ============ 构建最终内容 ============
        content = self._build_final_content(response, sources)

        # 保存响应到会话（包含推理步骤）
        session.add_message(
            "assistant",
            content,
            metadata={
                "reasoningSteps": collected_reasoning_steps,
            },
        )
        self.session_manager.store_dialog_to_memory(
            session.id, request.messages[-1].content, content
        )
        self.session_manager.persist()

        # ============ 流式发送最终内容 ============
        # 发送 role
        chunk = ChatCompletionStreamResponse(
            id=f"chatcmpl-{session.id}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionStreamChoice(index=0, delta={"role": "assistant"}, finish_reason=None)
            ],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"

        # 逐字发送内容
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
            await asyncio.sleep(0.01)

        # 发送结束标记
        chunk = ChatCompletionStreamResponse(
            id=f"chatcmpl-{session.id}",
            created=int(time.time()),
            model=request.model,
            choices=[ChatCompletionStreamChoice(index=0, delta={}, finish_reason="stop")],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"

    def _detect_workflow_intent(self, user_input: str) -> bool:
        """检测是否是工作流生成意图"""
        import re

        workflow_patterns = [
            # 中文 - 明确的工作流关键词
            r"创建.*(?:工作流|pipeline|流程|框架|系统|方案)",
            r"生成.*(?:工作流|pipeline|流程|框架|系统|方案)",
            r"构建.*(?:工作流|pipeline|流程|框架|系统|方案)",
            r"设计.*(?:工作流|pipeline|流程|框架|系统|方案)",
            r"搭建.*(?:工作流|pipeline|流程|框架|系统|方案)",
            r"开发.*(?:工作流|pipeline|流程|框架|系统)",
            r"帮我做.*(?:数据处理|ETL|工作流)",
            # 中文 - 任务规划类
            r"(?:制定|规划|安排).*(?:计划|方案|流程)",
            # 英文
            r"create.*(?:workflow|pipeline|framework|system)",
            r"generate.*(?:workflow|pipeline|framework|system)",
            r"build.*(?:workflow|pipeline|framework|system)",
            r"design.*(?:workflow|pipeline|framework|system)",
        ]
        for pattern in workflow_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                return True
        return False

    def _detect_casual_chat(self, user_input: str) -> bool:
        """检测是否是简单闲聊（只匹配纯粹的寒暄用语）"""
        user_lower = user_input.lower().strip()

        # 精确匹配的闲聊模式（必须完全匹配或非常接近）
        exact_casual_patterns = [
            "你好",
            "hi",
            "hello",
            "嗨",
            "hey",
            "谢谢",
            "thanks",
            "thank you",
            "再见",
            "bye",
            "拜拜",
            "test",
            "测试",
            "ok",
            "好的",
            "嗯",
            "好",
            "你好啊",
            "hello there",
            "hi there",
            "嘿",
            "哈喽",
        ]

        # 精确匹配
        if user_lower in exact_casual_patterns:
            return True

        # 带感叹号/问号的简单寒暄
        for pattern in exact_casual_patterns:
            if user_lower in [f"{pattern}!", f"{pattern}？", f"{pattern}?", f"{pattern}。"]:
                return True

        return False

    def _generate_workflow_direct(self, user_input: str) -> dict:
        """直接调用 LLMWorkflowGenerator 生成工作流"""
        try:
            import os

            from sage.libs.agentic.workflow import GenerationContext
            from sage.libs.agentic.workflow.generators import LLMWorkflowGenerator

            logger.info(f"Starting workflow generation for: {user_input[:100]}")

            context = GenerationContext(
                user_input=user_input,
                conversation_history=[],
            )

            # Try to get base_url from SagePorts or env
            import httpx

            from sage.common.config.ports import SagePorts

            base_url = os.getenv("SAGE_CHAT_BASE_URL")
            if not base_url:
                # Try 8901 first as seen in logs, then 8001
                base_url = f"http://localhost:{SagePorts.BENCHMARK_LLM}/v1"

            # Auto-detect model
            model_name = self._resolve_model_name("sage-default")
            try:
                # Use a short timeout to avoid blocking
                with httpx.Client(timeout=2.0) as client:
                    resp = client.get(f"{base_url}/models")
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("data") and len(data["data"]) > 0:
                            model_name = data["data"][0]["id"]
                            logger.info(f"Auto-detected LLM model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to auto-detect model from {base_url}: {e}")

            generator = LLMWorkflowGenerator(base_url=base_url, model=model_name, api_key="dummy")
            logger.info(
                f"LLMWorkflowGenerator config: model={generator.model}, "
                f"base_url={generator.base_url}, api_key={'set' if generator.api_key else 'NOT SET'}"
            )

            result = generator.generate(context)

            logger.info(
                f"Generation result: success={result.success}, "
                f"error={result.error}, strategy={result.strategy_used}"
            )

            if result.success:
                return {
                    "success": True,
                    "visual_pipeline": result.visual_pipeline,
                    "message": result.explanation or "工作流已生成",
                }
            else:
                return {
                    "success": False,
                    "error": result.error or "未知错误",
                }
        except Exception as e:
            logger.error(f"Workflow generation failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _generate_casual_response(self, user_input: str) -> dict:
        """生成闲聊回复"""
        # 简单的闲聊回复映射
        responses = {
            "你好": "你好！我是 SAGE 助手，有什么可以帮助你的吗？",
            "hi": "Hi! I'm SAGE assistant. How can I help you?",
            "hello": "Hello! I'm SAGE assistant. How can I help you?",
            "谢谢": "不客气！如果还有其他问题，随时告诉我。",
            "thanks": "You're welcome! Let me know if you have any other questions.",
            "test": "测试成功！我可以正常工作。",
            "测试": "测试成功！我可以正常工作。",
        }
        user_lower = user_input.lower().strip()
        for key, value in responses.items():
            if user_lower.startswith(key):
                return {"type": "chat", "content": value}
        return {"type": "chat", "content": "你好！有什么可以帮助你的吗？"}

    def _perform_rag_retrieval(self, user_input: str, model: str | None = None) -> dict:
        """执行 RAG 检索"""
        try:
            # 调用 RAG Pipeline 的检索功能
            if hasattr(self.rag_pipeline, "retrieve_documents"):
                sources = self.rag_pipeline.retrieve_documents(user_input)
            else:
                # 回退到完整处理
                request_data = {
                    "messages": [{"role": "user", "content": user_input}],
                    "model": model or self._resolve_model_name("sage-default"),
                }
                result = self.rag_pipeline.process(request_data, timeout=60.0)
                sources = result.get("sources", [])
            return {"sources": sources}
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}", exc_info=True)
            return {"sources": []}

    def _generate_rag_answer(
        self, user_input: str, sources: list, memory_history: str, model: str | None = None
    ) -> str:
        """基于检索结果生成回答"""
        try:
            request_data = {
                "messages": [{"role": "user", "content": user_input}],
                "model": model or self._resolve_model_name("sage-default"),
                "memory_context": memory_history,
            }
            result = self.rag_pipeline.process(request_data, timeout=120.0)
            return result.get("content", "抱歉，我无法生成回答。")
        except Exception as e:
            logger.error(f"RAG answer generation failed: {e}", exc_info=True)
            return f"抱歉，生成回答时出错: {e}"

    def _build_final_content(self, response: dict, sources: list) -> str:
        """构建最终回答内容"""
        import json

        response_type = response.get("type", "chat")

        if response_type == "workflow":
            workflow_data = response.get("workflow_data", {})
            visual_pipeline = workflow_data.get("visual_pipeline", {})
            workflow_json = json.dumps(visual_pipeline, indent=2, ensure_ascii=False)
            content = response.get("content", "工作流已生成")
            content += f"\n\n```json\n{workflow_json}\n```"
            return content

        elif response_type == "error":
            return response.get("content", "抱歉，处理请求时出错。")

        else:
            content = response.get("content", "")
            sources = response.get("sources", sources)

            # Filter sources based on relevance score
            # Only show sources with score >= 0.4 (if score exists)
            valid_sources = []
            for source in sources:
                score = source.get("score")
                if score is not None:
                    try:
                        if float(score) >= 0.4:
                            valid_sources.append(source)
                    except (ValueError, TypeError):
                        valid_sources.append(source)
                else:
                    # If no score provided, keep it (assume relevant)
                    valid_sources.append(source)

            if valid_sources:
                content += "\n\n---\n\n**参考文档：**\n\n"
                for i, source in enumerate(valid_sources[:3]):  # Limit to 3 sources
                    doc_path = source.get("doc_path", "unknown")
                    heading = source.get("heading", "")
                    text_preview = source.get("text", "")[:150]
                    if heading:
                        content += f"[{i + 1}] **{heading}** ({doc_path})\n"
                    else:
                        content += f"[{i + 1}] {doc_path}\n"
                    content += f"> {text_preview}...\n\n"
            return content

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

                # Filter sources based on relevance score
                valid_sources = []
                for source in sources:
                    score = source.get("score")
                    if score is not None:
                        try:
                            if float(score) >= 0.4:
                                valid_sources.append(source)
                        except (ValueError, TypeError):
                            valid_sources.append(source)
                    else:
                        valid_sources.append(source)

                # If sources are available, append them to the response
                if valid_sources:
                    content += "\n\n---\n\n**参考文档：**\n\n"
                    for i, source in enumerate(valid_sources[:3]):  # Limit to 3
                        doc_path = source.get("doc_path", "unknown")
                        heading = source.get("heading", "")
                        source_id = source.get("id", i + 1)
                        text_preview = source.get("text", "")[:150]

                        # Format source citation
                        if heading:
                            content += f"[{source_id}] **{heading}** ({doc_path})\n"
                        else:
                            content += f"[{source_id}] {doc_path}\n"
                        content += f"> {text_preview}...\n\n"

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

        from sage.common.config.ports import SagePorts
        from sage.llm import UnifiedInferenceClient

        model_name = os.getenv("SAGE_CHAT_MODEL", "qwen-max")
        base_url = os.getenv("SAGE_CHAT_BASE_URL")
        api_key = (
            os.getenv("SAGE_CHAT_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or self._load_api_key_from_config()
        )

        if not api_key:
            return "[配置错误] 请设置 SAGE_CHAT_API_KEY 或 OPENAI_API_KEY 环境变量"

        if not base_url:
            for port in [
                SagePorts.get_recommended_llm_port(),
                SagePorts.LLM_DEFAULT,
                SagePorts.BENCHMARK_LLM,
            ]:
                candidate = f"http://localhost:{port}/v1"
                if UnifiedInferenceClient._check_endpoint_health(candidate):
                    base_url = candidate
                    break

        if not base_url:
            return (
                "[配置错误] 未找到可用的本地 LLM 服务，请启动 `sage llm serve` 或设置 "
                "SAGE_CHAT_BASE_URL 指向可用端点"
            )

        # Create client via factory to respect the unified creation contract.
        # Set temporary env var so the factory picks up API key for this call.
        old_key = os.environ.get("SAGE_UNIFIED_API_KEY")
        try:
            os.environ["SAGE_UNIFIED_API_KEY"] = api_key
            client = UnifiedInferenceClient.create(
                control_plane_url=base_url,
                default_llm_model=model_name,
            )

            messages = [{"role": "user", "content": user_input}]
            return client.chat(messages)
        finally:
            # restore previous env var
            if old_key is None:
                os.environ.pop("SAGE_UNIFIED_API_KEY", None)
            else:
                os.environ["SAGE_UNIFIED_API_KEY"] = old_key

    async def _build_sage_chat_index(self, index_root: Path, index_name: str):
        """后台构建 sage chat 索引（与 sage chat ingest 相同）"""

        logger = logging.getLogger(__name__)
        logger.info("Building SAGE chat index in background...")

        try:
            from sage.common.components.sage_embedding import get_embedding_model
            from sage.common.config.output_paths import find_sage_project_root
            from sage.common.utils.document_processing import parse_markdown_sections
            from sage.middleware.components.sage_db.backend import SageVDBBackend
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
            db_path = index_root / f"{index_name}.sagevdb"

            # 创建 embedder
            embedder = get_embedding_model("hash", dim=384)

            # Backend factory
            def backend_factory(persist_path: Path, dim: int):
                return SageVDBBackend(persist_path, dim)

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

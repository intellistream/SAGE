"""
RAG-enabled Conversational Pipeline for SAGE Gateway

This module implements a persistent Pipeline-as-Service for the Gateway,
combining RAG capabilities with workflow generation.

Architecture:
- PipelineBridge: Queue-based request/response mechanism
- RAGChatSource: Pulls chat requests from bridge
- RAGChatMap: Performs retrieval + generation (or workflow generation)
- RAGChatSink: Returns responses to callers

Reference: examples/tutorials/L4-middleware/memory_service/rag_memory_pipeline.py
"""

import logging
import queue
import textwrap
import threading
from typing import Any

from sage.common.core.functions import MapFunction, SinkFunction, SourceFunction
from sage.kernel.api.local_environment import LocalEnvironment

logger = logging.getLogger(__name__)


class PipelineBridge:
    """Bridge for submitting requests to the Pipeline and receiving responses.

    Based on the PipelineBridge pattern from rag_memory_pipeline.py
    """

    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self._closed = False
        self._lock = threading.Lock()

    def submit(self, payload: dict[str, Any]) -> queue.Queue:
        """Submit a request to the pipeline and get a response queue.

        Args:
            payload: Request data (e.g., {"messages": [...], "model": "..."})

        Returns:
            Queue that will receive the response
        """
        if self._closed:
            raise RuntimeError("Bridge is closed")

        response_q: queue.Queue = queue.Queue()
        with self._lock:
            self._queue.put({"payload": payload, "response_queue": response_q})

        return response_q

    def next(self, timeout: float = 0.1) -> dict[str, Any] | None:
        """Get the next request from the queue (used by Source).

        Args:
            timeout: Timeout in seconds

        Returns:
            Request dict or None if timeout/closed
        """
        if self._closed:
            return None

        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self):
        """Close the bridge (stops accepting new requests)."""
        with self._lock:
            self._closed = True


class RAGChatSource(SourceFunction):
    """Source: Pulls chat requests from the bridge."""

    def __init__(self, bridge: PipelineBridge):
        super().__init__()
        self.bridge = bridge

    def execute(self, data=None):
        """Pull next request from bridge."""
        if self.bridge._closed:
            return None

        request = self.bridge.next(timeout=0.1)
        return request if request else None


class RAGChatMap(MapFunction):
    """Map: Performs RAG retrieval + generation (or workflow generation if needed)."""

    def __init__(self, config: dict[str, Any]):
        super().__init__()
        self.config = config
        self._db = None
        self._embedder = None
        self._manifest_data = None

    def _ensure_rag_initialized(self):
        """Lazy initialization of RAG components."""
        if self._db is not None:
            return

        try:
            import json
            from pathlib import Path as P

            from sage.common.components.sage_embedding import get_embedding_model
            from sage.middleware.components.sage_db.python.sage_db import SageDB

            # Load manifest
            index_root = P.home() / ".sage" / "cache" / "chat"
            index_name = "docs-public"
            manifest_file = index_root / f"{index_name}_manifest.json"

            if not manifest_file.exists():
                logger.warning("RAG index not found, RAG will be disabled")
                return

            with open(manifest_file, "r") as f:
                self._manifest_data = json.load(f)

            db_path = P(self._manifest_data["db_path"])

            # Initialize embedder
            embed_config = self._manifest_data.get("embedding", {})
            embedding_method = embed_config.get("method", "hash")
            embedding_model = embed_config.get("model_name")

            if embedding_method in ["hf", "openai", "jina"]:
                self._embedder = get_embedding_model(embedding_method, model_name=embedding_model)
            else:
                self._embedder = get_embedding_model(embedding_method, dim=384)

            # Load SageDB
            self._db = SageDB(self._embedder.get_dim())
            self._db.load(str(db_path))

            logger.info("RAG components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG: {e}", exc_info=True)
            self._db = None
            self._embedder = None

    def _detect_workflow_intent(self, user_input: str) -> bool:
        """Detect if user wants to create a workflow.

        Keywords that indicate workflow creation intent:
        - 创建/生成/构建 + 工作流/pipeline/流程
        - 帮我做一个/设计一个 + 数据处理/ETL
        """
        workflow_keywords = [
            r"创建.*(?:工作流|pipeline|流程)",
            r"生成.*(?:工作流|pipeline|流程)",
            r"构建.*(?:工作流|pipeline|流程)",
            r"帮我做.*(?:数据处理|ETL|工作流)",
            r"设计.*(?:工作流|pipeline|流程)",
            r"create.*(?:workflow|pipeline)",
            r"generate.*(?:workflow|pipeline)",
            r"build.*(?:workflow|pipeline)",
        ]

        import re

        for pattern in workflow_keywords:
            if re.search(pattern, user_input, re.IGNORECASE):
                return True

        return False

    def _generate_workflow(self, requirements: dict[str, Any]) -> dict[str, Any]:
        """Generate a workflow using Pipeline Builder.

        This integrates sage.cli.commands.apps.pipeline builder functionality
        to convert conversational requirements into executable pipelines.

        Returns:
            Workflow configuration in VisualPipeline format
        """
        try:
            import os
            from sage.cli.commands.apps import pipeline as pipeline_builder

            # Build config (similar to chat.py)
            config = pipeline_builder.BuilderConfig(
                backend="openai",
                model=os.getenv("SAGE_PIPELINE_BUILDER_MODEL", "qwen-max"),
                base_url=os.getenv(
                    "SAGE_PIPELINE_BUILDER_BASE_URL",
                    "https://dashscope.aliyuncs.com/compatible-mode/v1",
                ),
                api_key=(
                    os.getenv("SAGE_PIPELINE_BUILDER_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
                ),
                domain_contexts=(),
                knowledge_base=None,
                knowledge_top_k=0,
                show_knowledge=False,
            )

            # Generate plan
            generator = pipeline_builder.PipelinePlanGenerator(config)
            plan = generator.generate(requirements, previous_plan=None, feedback=None)

            # Convert to VisualPipeline format for Studio
            visual_pipeline = self._convert_to_visual_pipeline(plan)

            return {
                "type": "workflow",
                "plan": plan,
                "visual_pipeline": visual_pipeline,
                "message": "我已经为您生成了一个工作流配置，您可以在 Studio 中查看和编辑。",
            }

        except Exception as e:
            logger.error(f"Workflow generation failed: {e}", exc_info=True)
            return {"type": "error", "error": str(e), "message": f"抱歉，工作流生成失败：{e}"}

    def _convert_to_visual_pipeline(self, plan: dict[str, Any]) -> dict[str, Any]:
        """Convert pipeline plan to VisualPipeline format.

        This adapts the LLM-generated plan to Studio's visual format.
        """
        nodes = []
        connections = []

        # Extract pipeline metadata
        pipeline_info = plan.get("pipeline", {})

        # Create source node
        source_config = plan.get("source", {})
        nodes.append(
            {
                "id": "source-0",
                "type": source_config.get("class", "text_file_source").lower().replace(".", "_"),
                "label": "数据源",
                "config": source_config.get("params", {}),
                "position": {"x": 100, "y": 100},
            }
        )

        # Create stage nodes
        stages = plan.get("stages", [])
        for idx, stage in enumerate(stages):
            stage_id = f"stage-{idx}"
            nodes.append(
                {
                    "id": stage_id,
                    "type": stage.get("class", "map_function").lower().replace(".", "_"),
                    "label": stage.get("summary", f"处理阶段 {idx + 1}"),
                    "config": stage.get("params", {}),
                    "position": {"x": 100 + (idx + 1) * 200, "y": 100},
                }
            )

            # Connect to previous node
            prev_id = f"stage-{idx - 1}" if idx > 0 else "source-0"
            connections.append(
                {
                    "id": f"conn-{idx}",
                    "source_node_id": prev_id,
                    "target_node_id": stage_id,
                    "source_port": "output",
                    "target_port": "input",
                }
            )

        # Create sink node
        sink_config = plan.get("sink", {})
        sink_id = f"sink-{len(stages)}"
        nodes.append(
            {
                "id": sink_id,
                "type": sink_config.get("class", "terminal_sink").lower().replace(".", "_"),
                "label": "输出",
                "config": sink_config.get("params", {}),
                "position": {"x": 100 + (len(stages) + 1) * 200, "y": 100},
            }
        )

        # Connect last stage to sink
        if stages:
            connections.append(
                {
                    "id": f"conn-{len(stages)}",
                    "source_node_id": f"stage-{len(stages) - 1}",
                    "target_node_id": sink_id,
                    "source_port": "output",
                    "target_port": "input",
                }
            )
        else:
            connections.append(
                {
                    "id": "conn-0",
                    "source_node_id": "source-0",
                    "target_node_id": sink_id,
                    "source_port": "output",
                    "target_port": "input",
                }
            )

        return {
            "name": pipeline_info.get("name", "生成的工作流"),
            "description": pipeline_info.get("description", ""),
            "nodes": nodes,
            "connections": connections,
            "metadata": {
                "generated_by": "sage_gateway_rag_pipeline",
                "version": pipeline_info.get("version", "1.0.0"),
            },
        }

    def _perform_rag_chat(self, user_input: str) -> dict:
        """Perform RAG-based chat response.

        Returns:
            Dict with 'content' (answer) and 'sources' (retrieved documents)
        """
        self._ensure_rag_initialized()

        if self._db is None or self._embedder is None:
            # Fallback to direct LLM
            return {"content": self._fallback_direct_llm(user_input), "sources": [], "type": "chat"}

        try:
            # 1. Retrieve relevant documents
            query_vector = self._embedder.embed(user_input)
            top_k = 4
            results = self._db.search(query_vector, top_k, True)

            # Extract contexts and build sources list
            contexts = []
            sources = []
            for idx, item in enumerate(results, start=1):
                metadata = dict(item.metadata) if hasattr(item, "metadata") else {}
                text = metadata.get("text", "")

                if text:
                    contexts.append(text)
                    # Build source info for display
                    sources.append(
                        {
                            "id": idx,
                            "text": text[:500] + ("..." if len(text) > 500 else ""),  # Preview
                            "full_text": text,
                            "doc_path": metadata.get("doc_path", "unknown"),
                            "heading": metadata.get("heading", ""),
                            "chunk": metadata.get("chunk", "0"),
                        }
                    )

            # 2. Build RAG prompt
            context_block = "\n\n".join(
                f"[{idx}] {textwrap.dedent(ctx).strip()}"
                for idx, ctx in enumerate(contexts, start=1)
                if ctx
            )

            system_instructions = textwrap.dedent(
                """
                You are SAGE 内嵌编程助手。回答用户关于 SAGE 的问题，依据提供的上下文进行解释。
                - 如果上下文不足以回答，请坦诚说明并给出下一步建议。
                - 引用时使用 [编号] 表示，例如 [1], [2]。
                - 回答保持简洁，直接给出步骤或示例代码。
                - 在回答末尾简要说明引用来源的文档标题。
                """
            ).strip()

            if context_block:
                system_instructions += f"\n\n已检索上下文:\n{context_block}"

            messages = [
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_input.strip()},
            ]

            # 3. Generate response using vLLM service
            import os
            from sage.libs.integrations.openaiclient import OpenAIClient

            # Use local vLLM service by default
            model_name = os.getenv("SAGE_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
            base_url = os.getenv("SAGE_CHAT_BASE_URL", "http://localhost:8000/v1")
            api_key = os.getenv("SAGE_CHAT_API_KEY", "token-abc123")

            if not base_url:
                return {
                    "content": "[配置错误] 请设置 SAGE_CHAT_BASE_URL 环境变量或启动本地 vLLM 服务",
                    "sources": [],
                    "type": "error",
                }

            client = OpenAIClient(
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
                seed=42,
            )

            response = client.generate(messages, temperature=0.2, stream=False)

            # Return answer with sources
            return {"content": response, "sources": sources, "type": "chat"}

        except Exception as e:
            logger.error(f"RAG chat error: {e}", exc_info=True)
            return {"content": self._fallback_direct_llm(user_input), "sources": [], "type": "chat"}

    def _fallback_direct_llm(self, user_input: str) -> str:
        """Fallback: Direct LLM call without RAG using vLLM service."""
        try:
            import os
            from sage.libs.integrations.openaiclient import OpenAIClient

            # Use local vLLM service by default
            model_name = os.getenv("SAGE_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
            base_url = os.getenv("SAGE_CHAT_BASE_URL", "http://localhost:8000/v1")
            api_key = os.getenv("SAGE_CHAT_API_KEY", "token-abc123")

            if not base_url:
                return "[配置错误] 请设置 SAGE_CHAT_BASE_URL 环境变量或启动本地 vLLM 服务"

            client = OpenAIClient(
                model_name=model_name,
                base_url=base_url,
                api_key=api_key,
                seed=42,
            )

            messages = [{"role": "user", "content": user_input}]
            return client.generate(messages, temperature=0.7, stream=False)

        except Exception as e:
            logger.error(f"Fallback LLM error: {e}", exc_info=True)
            return f"抱歉，处理请求时出错：{e}"

    def execute(self, data):
        """Main execution: route to RAG chat or workflow generation."""
        if not data:
            return None

        payload = data["payload"]

        # Extract user input
        messages = payload.get("messages", [])
        if not messages:
            return {
                "payload": {"error": "No messages provided"},
                "response_queue": data["response_queue"],
            }

        user_input = messages[-1].get("content", "")

        # Detect intent: workflow creation vs. conversation
        if self._detect_workflow_intent(user_input):
            # Workflow generation mode
            requirements = {
                "name": "用户自定义工作流",
                "goal": user_input,
                "data_sources": ["文档知识库"],
                "latency_budget": "实时响应优先",
                "constraints": "",
                "initial_prompt": user_input,
            }

            result = self._generate_workflow(requirements)
            response_content = result.get("message", "工作流已生成")
            response_type = result.get("type", "workflow")

            return {
                "payload": {
                    "content": response_content,
                    "type": response_type,
                    "workflow_data": result if response_type == "workflow" else None,
                },
                "response_queue": data["response_queue"],
            }
        else:
            # RAG chat mode
            rag_result = self._perform_rag_chat(user_input)

            return {
                "payload": {
                    "content": rag_result.get("content", ""),
                    "type": rag_result.get("type", "chat"),
                    "sources": rag_result.get("sources", []),
                },
                "response_queue": data["response_queue"],
            }


class RAGChatSink(SinkFunction):
    """Sink: Returns responses to callers via response queue."""

    def execute(self, data):
        if not data:
            return

        response_queue = data["response_queue"]
        payload = data["payload"]

        # Put response in the queue
        response_queue.put(payload)


class RAGPipelineService:
    """Main service: manages the persistent RAG Pipeline."""

    def __init__(self):
        self.bridge = PipelineBridge()
        self.env = None
        self.job = None
        self._started = False

    def start(self):
        """Start the persistent Pipeline job."""
        if self._started:
            logger.warning("RAG Pipeline already started")
            return

        try:
            # Create environment
            self.env = LocalEnvironment()

            # Build Pipeline: Source -> Map -> Sink
            (
                self.env.from_source(RAGChatSource, self.bridge, name="RAGChatSource")
                .map(RAGChatMap, config={}, name="RAGChatMap")
                .sink(RAGChatSink, name="RAGChatSink")
            )

            # Submit job (keep running in background)
            self.job = self.env.submit(autostop=False)
            self._started = True

            logger.info("✅ RAG Pipeline started successfully")

        except Exception as e:
            logger.error(f"Failed to start RAG Pipeline: {e}", exc_info=True)
            raise

    def process(self, request_data: dict[str, Any], timeout: float = 120.0) -> dict[str, Any]:
        """Process a chat request through the Pipeline.

        Args:
            request_data: Chat request (messages, model, etc.)
            timeout: Response timeout in seconds

        Returns:
            Response dict with content/type/workflow_data
        """
        if not self._started:
            raise RuntimeError("RAG Pipeline not started")

        # Submit request and wait for response
        response_q = self.bridge.submit(request_data)

        try:
            response = response_q.get(timeout=timeout)
            return response
        except queue.Empty:
            logger.error(f"Pipeline response timeout after {timeout}s")
            return {"error": "Response timeout", "content": "抱歉，处理请求超时，请稍后重试。"}

    def stop(self):
        """Stop the Pipeline."""
        if self.job:
            self.bridge.close()
            # Job will stop naturally when bridge is closed
            self._started = False
            logger.info("RAG Pipeline stopped")

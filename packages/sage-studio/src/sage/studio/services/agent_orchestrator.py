"""
Agent Orchestrator for SAGE Studio

Layer: L6 (sage-studio)
Dependencies: IntentClassifier, KnowledgeManager, WorkflowGenerator
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import AsyncGenerator

import httpx

from sage.common.config.ports import SagePorts
from sage.libs.agentic.intent import IntentClassifier, IntentResult, UserIntent
from sage.libs.agentic.workflows.router import (
    WorkflowDecision,
    WorkflowRequest,
    WorkflowRoute,
    WorkflowRouter,
)
from sage.studio.models.agent_step import (
    AgentStep,
)
from sage.studio.services.agents.researcher import ResearcherAgent
from sage.studio.services.knowledge_manager import KnowledgeManager
from sage.studio.services.memory_integration import get_memory_service

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Agent 编排器

    协调意图分类、知识检索、工具调用等，处理用户请求。
    """

    def __init__(self):
        # 优先使用 LLM 模式以获得 Agentic 体验，内部会自动降级到 keyword
        self.intent_classifier = IntentClassifier(mode="llm")
        self.workflow_router = WorkflowRouter(self.intent_classifier)
        self.knowledge_manager = KnowledgeManager()

        # 尝试获取工具注册表
        try:
            from sage.studio.tools.base import get_tool_registry

            self.tools = get_tool_registry()
        except ImportError:
            logger.warning("ToolRegistry not found, tools will be unavailable.")

            class MockRegistry:
                def get(self, name):
                    return None

                def register(self, tool):
                    pass

                def list_tools(self):
                    return []

            self.tools = MockRegistry()

        # 注册内置工具
        self._register_builtin_tools()

        # Initialize Agents (Swarm Architecture)
        # Pass all available tools to the researcher agent
        self.researcher_agent = ResearcherAgent(self.tools.list_tools())

    def _register_builtin_tools(self):
        """注册内置工具"""
        try:
            from sage.studio.tools.arxiv_search import ArxivSearchTool
            from sage.studio.tools.knowledge_search import KnowledgeSearchTool
            from sage.studio.tools.middleware_adapter import NatureNewsTool

            self.tools.register(KnowledgeSearchTool(self.knowledge_manager))
            self.tools.register(ArxivSearchTool())

            # 注册新的 Middleware 适配工具
            self.tools.register(NatureNewsTool())
        except ImportError as e:
            logger.warning(f"Builtin tools not found or failed to load: {e}")

    def _make_step(
        self, type: str, content: str, status: str = "completed", **metadata
    ) -> AgentStep:
        """创建执行步骤"""
        return AgentStep.create(
            type=type,
            content=content,
            status=status,
            **metadata,
        )

    async def process_message(
        self,
        message: str,
        session_id: str,
        history: list[dict[str, str]] | None = None,
        *,
        should_index: bool = False,
        metadata: dict[str, str] | None = None,
        evidence: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[AgentStep | str, None]:
        """Route a message through the shared workflow router and stream steps/results."""

        history = history or []
        metadata = metadata or {}
        evidence = evidence or []

        memory_service = get_memory_service(session_id)

        yield self._make_step("routing", "正在检索上下文并分析意图...", status="running")
        context_items = await memory_service.retrieve_context(message)

        decision = await self.workflow_router.decide(
            WorkflowRequest(
                query=message,
                session_id=session_id,
                history=history,
                metadata=metadata,
                should_index=should_index,
                evidence=evidence,
                context=[item.content for item in context_items[:3]],
            )
        )

        yield self._make_step(
            "routing",
            (
                f"路由: {decision.route.value} | 意图: {decision.intent.value} "
                f"(置信度 {decision.confidence:.2f})"
            ),
            matched_keywords=decision.matched_keywords,
            status="completed",
        )

        route_started_at = time.perf_counter()

        if decision.route == WorkflowRoute.SIMPLE_RAG:
            async for chunk in self._run_simple_rag(message, session_id, context_items, decision):
                yield chunk
            route_duration = time.perf_counter() - route_started_at
            logger.info(
                "route completed",
                extra={
                    "route": decision.route.value,
                    "intent": decision.intent.value,
                    "duration_ms": int(route_duration * 1000),
                    "should_index": decision.should_index,
                },
            )
            return

        if decision.route in {WorkflowRoute.AGENTIC, WorkflowRoute.CODE}:
            async for chunk in self._run_agentic(message, session_id, history, decision):
                yield chunk
            route_duration = time.perf_counter() - route_started_at
            logger.info(
                "route completed",
                extra={
                    "route": decision.route.value,
                    "intent": decision.intent.value,
                    "duration_ms": int(route_duration * 1000),
                    "should_index": decision.should_index,
                },
            )
            return

        async for chunk in self._run_general_chat(message, session_id, context_items, decision):
            yield chunk
        route_duration = time.perf_counter() - route_started_at
        logger.info(
            "route completed",
            extra={
                "route": decision.route.value,
                "intent": decision.intent.value,
                "duration_ms": int(route_duration * 1000),
                "should_index": decision.should_index,
            },
        )

    async def _run_general_chat(
        self,
        message: str,
        session_id: str,
        context_items: list,
        decision: WorkflowDecision,
    ) -> AsyncGenerator[AgentStep | str, None]:
        memory_service = get_memory_service(session_id)
        response_text = await self._call_gateway_chat(
            message=message,
            session_id=session_id,
            context_items=context_items,
            evidence=[],
        )
        if response_text:
            await memory_service.add_interaction(message, response_text)
            yield response_text

    async def _run_simple_rag(
        self,
        message: str,
        session_id: str,
        context_items: list,
        decision: WorkflowDecision,
    ) -> AsyncGenerator[AgentStep | str, None]:
        memory_service = get_memory_service(session_id)
        yield self._make_step("retrieval", "正在检索知识库...", status="running")

        try:
            km_results = await self.knowledge_manager.search(message, limit=4, score_threshold=0.4)
        except Exception as exc:
            logger.warning(f"Knowledge search failed: {exc}")
            km_results = []

        evidence_payload = [
            {
                "content": res.content,
                "score": res.score,
                "source": res.source,
                "metadata": res.metadata,
            }
            for res in km_results
        ]

        if evidence_payload:
            yield self._make_step(
                "retrieval",
                f"检索到 {len(evidence_payload)} 条知识库证据",
                status="completed",
                evidence=evidence_payload,
            )
        else:
            yield self._make_step("retrieval", "未找到知识库证据，继续对话", status="completed")

        response_text = await self._call_gateway_chat(
            message=message,
            session_id=session_id,
            context_items=context_items,
            evidence=evidence_payload,
        )

        if evidence_payload:
            await memory_service.add_evidence_batch(
                evidence_payload, {"route": decision.route.value}
            )

            if decision.should_index:
                try:
                    await self.knowledge_manager.ingest_texts(
                        [ev.get("content", "") for ev in evidence_payload],
                        source_name="agentic_evidence",
                        metadata={"session_id": session_id, "route": decision.route.value},
                    )
                except Exception as exc:
                    logger.warning("Failed to ingest evidence into vector store: %s", exc)

        if response_text:
            await memory_service.add_interaction(message, response_text)
            yield response_text

    async def _run_agentic(
        self,
        message: str,
        session_id: str,
        history: list[dict],
        decision: WorkflowDecision,
    ) -> AsyncGenerator[AgentStep | str, None]:
        memory_service = get_memory_service(session_id)
        full_response = ""
        evidence_payload: list[dict[str, object]] = []
        async for item in self.researcher_agent.run(message, history):
            if hasattr(item, "metadata"):
                raw_results = (
                    item.metadata.get("raw_results") if hasattr(item, "metadata") else None
                )
                if raw_results:
                    for res in raw_results:
                        if not isinstance(res, dict):
                            continue
                        content = res.get("content")
                        if not content:
                            continue
                        try:
                            score_val = float(res.get("score", 1.0))
                        except Exception:
                            score_val = 1.0
                        evidence_payload.append(
                            {
                                "content": content,
                                "score": score_val,
                                "source": res.get("source") or "agentic_tool",
                                "metadata": res.get("metadata") or {},
                            }
                        )
            if isinstance(item, str):
                full_response += item
            yield item

        if evidence_payload:
            await memory_service.add_evidence_batch(
                evidence_payload,
                {"route": decision.route.value},
            )

            if decision.should_index:
                try:
                    await self.knowledge_manager.ingest_texts(
                        [ev.get("content", "") for ev in evidence_payload],
                        source_name="agentic_evidence",
                        metadata={"session_id": session_id, "route": decision.route.value},
                    )
                except Exception as exc:
                    logger.warning("Failed to ingest agentic evidence into vector store: %s", exc)

        if full_response:
            await memory_service.add_interaction(message, full_response)

    async def _call_gateway_chat(
        self,
        *,
        message: str,
        session_id: str,
        context_items: list,
        evidence: list[dict],
    ) -> str:
        """Call the LLM Gateway /v1/chat/completions with optional context/evidence."""

        context_text = self._format_context(context_items, evidence)
        messages = []
        if context_text:
            messages.append({"role": "system", "content": context_text})
        messages.append({"role": "user", "content": message})

        try:
            base_url = self._resolve_gateway_base_url()
            async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
                resp = await client.post(
                    f"{base_url}/v1/chat/completions",
                    json={
                        "model": "sage-default",
                        "messages": messages,
                        "stream": False,
                        "session_id": session_id,
                    },
                )
            if resp.status_code != 200:
                logger.warning("Gateway returned %s: %s", resp.status_code, resp.text)
                return ""

            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as exc:
            logger.warning("Gateway call failed: %s", exc)
            return ""

    def _resolve_gateway_base_url(self) -> str:
        """Resolve gateway base URL with local-first preference."""

        env_url = os.environ.get("SAGE_GATEWAY_BASE_URL") or os.environ.get("GATEWAY_BASE_URL")
        if env_url:
            return env_url.rstrip("/")

        host = os.environ.get("SAGE_GATEWAY_HOST")
        if host:
            return f"http://{host}:{SagePorts.GATEWAY_DEFAULT}"

        # Local-first: try gateway default port
        return f"http://127.0.0.1:{SagePorts.GATEWAY_DEFAULT}"

    def _format_context(self, context_items: list, evidence: list[dict]) -> str:
        """Build a compact context string for the system prompt."""

        context_snippets = []
        for item in context_items[:3]:
            try:
                snippet = item.content if len(item.content) <= 400 else f"{item.content[:400]}..."
                context_snippets.append(f"Memory: {snippet}")
            except Exception:
                continue

        for ev in evidence[:3]:
            content = ev.get("content")
            if content:
                snippet = content if len(content) <= 400 else f"{content[:400]}..."
                source = ev.get("source") or "knowledge"
                context_snippets.append(f"Evidence ({source}): {snippet}")

        if not context_snippets:
            return ""

        return "\n".join(context_snippets)

    def _get_handler(self, intent: UserIntent):
        """获取意图处理器"""
        handlers = {
            UserIntent.KNOWLEDGE_QUERY: self._handle_knowledge_query,
            UserIntent.SAGE_CODING: self._handle_sage_coding,
            UserIntent.SYSTEM_OPERATION: self._handle_system_operation,
            UserIntent.GENERAL_CHAT: self._handle_general_chat,
        }
        return handlers.get(intent, self._handle_general_chat)

    async def _handle_knowledge_query(
        self,
        message: str,
        intent: IntentResult,
        history: list[dict],
    ) -> AsyncGenerator[AgentStep | str, None]:
        """处理知识库查询（包括 SAGE 文档、研究指导等）"""
        # Delegate to Researcher Agent (Swarm Architecture)
        async for step in self.researcher_agent.run(message, history):
            yield step

    async def _handle_sage_coding(
        self,
        message: str,
        intent: IntentResult,
        history: list[dict],
    ) -> AsyncGenerator[AgentStep | str, None]:
        """处理 SAGE 编程请求（Pipeline 生成、代码调试）"""
        yield self._make_step("reasoning", "分析编程需求...", status="running")

        # 先检索相关文档和示例
        tool = self.tools.get("knowledge_search")
        if tool:
            yield self._make_step(
                "tool_call", "检索相关代码示例...", status="running", tool_name="knowledge_search"
            )
            try:
                result = await tool.run(query=message, sources=["sage_docs", "examples"])

                if result["status"] == "success":
                    docs = result["result"]
                    yield self._make_step(
                        "tool_result",
                        f"找到 {len(docs)} 个相关示例",
                        tool_name="knowledge_search",
                        documents=docs,
                    )
            except Exception:
                pass

        # TODO: 调用 WorkflowGenerator 或 LLM 生成代码
        yield self._make_step("reasoning", "正在生成代码方案...")

        response = f"这是一个 SAGE 编程请求。根据您的描述 '{message}'，建议使用以下 Pipeline 结构...\n\n(代码生成功能开发中)"

        for char in response:
            yield char
            await asyncio.sleep(0.005)

    async def _handle_system_operation(
        self,
        message: str,
        intent: IntentResult,
        history: list[dict],
    ) -> AsyncGenerator[AgentStep | str, None]:
        """处理系统操作"""
        yield self._make_step("reasoning", "解析系统操作指令...", status="running")

        # TODO: 实现系统操作工具
        yield self._make_step("reasoning", "系统操作功能尚未完全实现", status="completed")

        response = f"收到系统操作指令: {message}。\n目前仅支持查看状态，暂不支持修改操作。"
        for char in response:
            yield char
            await asyncio.sleep(0.005)

    async def _handle_general_chat(
        self,
        message: str,
        intent: IntentResult,
        history: list[dict],
    ) -> AsyncGenerator[AgentStep | str, None]:
        """处理普通对话"""
        # TODO: 调用 LLM 进行对话
        yield self._make_step("reasoning", "生成回复...", status="running")

        response = f"收到您的消息: {message}\n\n这是一个普通对话，我会尽力帮助您。"

        for char in response:
            yield char
            await asyncio.sleep(0.005)


# 单例
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator

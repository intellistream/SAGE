"""
Agent Orchestrator for SAGE Studio

Layer: L6 (sage-studio)
Dependencies: IntentClassifier, KnowledgeManager, WorkflowGenerator
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator

from sage.studio.models.agent_step import (
    AgentStep,
)
from sage.studio.services.intent_classifier import (
    IntentClassifier,
    IntentResult,
    UserIntent,
)
from sage.studio.services.knowledge_manager import KnowledgeManager
from sage.studio.services.memory_integration import get_memory_service

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Agent 编排器

    协调意图分类、知识检索、工具调用等，处理用户请求。
    """

    def __init__(self):
        # 使用 keyword 模式初始化，避免依赖 embedding 模型
        self.intent_classifier = IntentClassifier(mode="keyword")
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

            self.tools = MockRegistry()

        # 注册内置工具
        self._register_builtin_tools()

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
    ) -> AsyncGenerator[AgentStep | str, None]:
        """处理用户消息"""
        history = history or []

        # Memory Integration
        memory_service = get_memory_service(session_id)

        # 1. Retrieve Context
        yield self._make_step("reasoning", "正在检索记忆上下文...", status="running")
        context_items = await memory_service.retrieve_context(message)

        if context_items:
            yield self._make_step(
                "reasoning",
                f"检索到 {len(context_items)} 条相关记忆",
                status="completed",
                context_items=[
                    {"id": item.id, "content": item.content[:100]} for item in context_items
                ],
            )
        else:
            yield self._make_step("reasoning", "未找到相关记忆", status="completed")

        # 2. 意图识别
        yield self._make_step("reasoning", "正在分析用户意图...", status="running")

        try:
            intent_result = await self.intent_classifier.classify(message, history)
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            intent_result = IntentResult(
                intent=UserIntent.GENERAL_CHAT,
                confidence=0.5,
                matched_keywords=[],
            )

        yield self._make_step(
            "reasoning",
            f"识别意图: {intent_result.intent.value} (置信度: {intent_result.confidence:.2f})",
            matched_keywords=intent_result.matched_keywords,
        )

        # 3. 路由到对应处理器
        handler = self._get_handler(intent_result.intent)

        full_response = ""
        async for item in handler(message, intent_result, history):
            yield item
            if isinstance(item, str):
                full_response += item

        # 4. Save Interaction to Memory
        if full_response:
            await memory_service.add_interaction(message, full_response)

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
        # 调用知识检索工具
        yield self._make_step(
            "tool_call", "调用知识库检索...", status="running", tool_name="knowledge_search"
        )

        tool = self.tools.get("knowledge_search")
        if tool:
            # 使用 intent 中的 knowledge_domains
            sources = (
                intent.get_search_sources()
                if hasattr(intent, "get_search_sources")
                else ["sage_docs", "examples"]
            )

            try:
                result = await tool.run(query=message, sources=sources)

                if result["status"] == "success":
                    docs = result["result"]
                    yield self._make_step(
                        "tool_result",
                        f"找到 {len(docs)} 个相关文档",
                        tool_name="knowledge_search",
                        documents=docs,
                    )

                    # 生成回复
                    context = "\n\n".join([d["content"][:500] for d in docs[:3]])
                    yield self._make_step("reasoning", "正在生成回复...")

                    # TODO: 调用 LLM 生成回复
                    # 暂时使用简单的模板回复
                    response = (
                        f"根据检索到的资料：\n\n{context[:1000]}...\n\n(LLM 生成功能尚未连接)"
                    )

                    for char in response:
                        yield char
                        await asyncio.sleep(0.005)  # 打字机效果
                else:
                    yield self._make_step(
                        "tool_result",
                        f"检索失败: {result.get('error')}",
                        status="failed",
                        tool_name="knowledge_search",
                    )
                    yield "抱歉，知识库检索遇到问题。"
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                yield self._make_step(
                    "tool_result",
                    f"工具执行异常: {str(e)}",
                    status="failed",
                    tool_name="knowledge_search",
                )
                yield "抱歉，检索过程中发生错误。"
        else:
            # 降级策略：直接使用 KnowledgeManager
            yield self._make_step(
                "reasoning", "知识检索工具未注册，尝试直接检索...", status="running"
            )
            try:
                sources = intent.get_search_sources()
                results = await self.knowledge_manager.search(message, sources=sources)
                yield self._make_step(
                    "tool_result", f"找到 {len(results)} 条结果", tool_name="knowledge_manager"
                )

                context = "\n\n".join([r.content[:500] for r in results[:3]])
                response = f"根据检索结果：\n\n{context[:1000]}...\n\n(LLM 生成功能尚未连接)"
                for char in response:
                    yield char
                    await asyncio.sleep(0.005)
            except Exception as e:
                logger.error(f"Direct search failed: {e}")
                yield "抱歉，无法访问知识库。"

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

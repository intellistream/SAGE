# Task 3.2: Orchestrator 核心实现

## 目标
实现 AgentOrchestrator 的核心逻辑，作为 Multi-Agent 系统的入口。

## 依赖
- Task 1.3 (IntentClassifier)
- Task 2.4 (KnowledgeManager)
- Task 3.1 (AgentStep Schema)

## 文件位置
`packages/sage-studio/src/sage/studio/services/agent_orchestrator.py`

## 提示词

```
请实现 AgentOrchestrator 的核心逻辑。

## 背景
AgentOrchestrator 是 Multi-Agent 系统的"大脑"，负责:
1. 接收用户消息
2. 调用 IntentClassifier 识别意图
3. 根据意图路由到相应的处理器
4. 流式返回执行步骤和结果

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/services/agent_orchestrator.py

2. 实现核心类:
   ```python
   class AgentOrchestrator:
       def __init__(self):
           self.intent_classifier = IntentClassifier()
           self.knowledge_manager = KnowledgeManager()
           self.tools = ToolRegistry()

       async def process_message(
           self,
           message: str,
           session_id: str,
           history: list[dict[str, str]] | None = None,
       ) -> AsyncGenerator[AgentStep | str, None]:
           """处理用户消息，流式返回结果"""
           pass
   ```

3. 流式输出两种类型:
   - AgentStep: 执行步骤（用于前端展示推理过程）
   - str: 最终回复文本片段（用于打字机效果）

4. 处理流程:
   ```
   用户消息 → 意图识别 → 路由分发 → 执行处理器 → 流式输出
                ↓
           AgentStep(reasoning)
                ↓
           AgentStep(tool_call) (如果需要)
                ↓
           AgentStep(tool_result)
                ↓
           str, str, str... (最终回复)
   ```

## 代码模板
```python
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator

from sage.studio.services.intent_classifier import IntentClassifier, IntentResult, UserIntent
from sage.studio.services.knowledge_manager import KnowledgeManager
from sage.studio.tools.base import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    """Agent 执行步骤"""
    step_id: str
    type: str  # "reasoning", "tool_call", "tool_result", "response"
    content: str
    status: str = "pending"  # "pending", "running", "completed", "failed"
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentOrchestrator:
    """Agent 编排器

    协调意图分类、知识检索、工具调用等，处理用户请求。
    """

    def __init__(self):
        self.intent_classifier = IntentClassifier(mode="hybrid")
        self.knowledge_manager = KnowledgeManager()
        self.tools = get_tool_registry()

        # 注册内置工具
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """注册内置工具"""
        from sage.studio.tools.knowledge_search import KnowledgeSearchTool
        from sage.studio.tools.arxiv_search import ArxivSearchTool

        self.tools.register(KnowledgeSearchTool(self.knowledge_manager))
        self.tools.register(ArxivSearchTool())

    def _make_step(
        self,
        type: str,
        content: str,
        status: str = "completed",
        **metadata
    ) -> AgentStep:
        """创建执行步骤"""
        return AgentStep(
            step_id=str(uuid.uuid4())[:8],
            type=type,
            content=content,
            status=status,
            metadata=metadata,
        )

    async def process_message(
        self,
        message: str,
        session_id: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[AgentStep | str, None]:
        """处理用户消息"""
        history = history or []

        # 1. 意图识别
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

        # 2. 路由到对应处理器
        handler = self._get_handler(intent_result.intent)

        async for item in handler(message, intent_result, history):
            yield item

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
        yield self._make_step("tool_call", "调用知识库检索...", status="running")

        tool = self.tools.get("knowledge_search")
        if tool:
            # 使用 intent 中的 knowledge_domains
            sources = intent.get_search_sources() if hasattr(intent, 'get_search_sources') else ["sage_docs", "examples"]
            result = await tool.run(query=message, sources=sources)

            if result["status"] == "success":
                docs = result["result"]
                yield self._make_step(
                    "tool_result",
                    f"找到 {len(docs)} 个相关文档",
                    documents=docs,
                )

                # 生成回复
                context = "\n\n".join([d["content"][:500] for d in docs[:3]])
                yield self._make_step("reasoning", "正在生成回复...")

                # TODO: 调用 LLM 生成回复
                response = f"根据检索到的资料：\n\n{context[:1000]}..."

                for char in response:
                    yield char
                    await asyncio.sleep(0.01)  # 打字机效果
            else:
                yield f"抱歉，检索失败: {result['error']}"
        else:
            yield "知识检索工具未可用"

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
            result = await tool.run(query=message, sources=["sage_docs", "examples"])

            if result["status"] == "success":
                docs = result["result"]
                yield self._make_step(
                    "tool_result",
                    f"找到 {len(docs)} 个相关示例",
                    documents=docs,
                )

        # TODO: 调用 LLM 生成代码
        response = f"这是一个 SAGE 编程请求，我会帮您生成/调试代码..."

        for char in response:
            yield char
            await asyncio.sleep(0.01)

    async def _handle_general_chat(
        self,
        message: str,
        intent: IntentResult,
        history: list[dict],
    ) -> AsyncGenerator[AgentStep | str, None]:
        """处理普通对话"""
        # TODO: 调用 LLM 进行对话
        response = f"收到您的消息: {message}\n\n这是一个普通对话，我会尽力帮助您。"

        for char in response:
            yield char
            await asyncio.sleep(0.01)

    # ... 其他处理器实现类似


# 单例
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
```

## 注意
- 所有处理器都是 async generator
- 错误处理要完善
- 考虑超时机制
```

## 验收标准
- [ ] 意图识别正常工作
- [ ] 4 种意图都有对应处理器
- [ ] 流式输出 AgentStep 和 str
- [ ] 错误处理覆盖

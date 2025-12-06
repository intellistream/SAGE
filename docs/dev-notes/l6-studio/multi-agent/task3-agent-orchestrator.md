# Task 3: Agent Orchestrator (Agent 编排器)

## 任务概述

实现 Agent 编排器，作为 Multi-Agent 系统的核心大脑。它负责接收用户输入，调用意图分类器，根据意图路由到相应的 Agent 或 Tool，并协调执行过程。

**优先级**: P0 (高)  
**预计工时**: 3-4 天  
**可并行**: 否（依赖 Task 1, 2 接口，但可先 Mock）

## 目标

1. **统一入口**: 替代现有的简单 Chat 逻辑，成为所有对话请求的入口
2. **动态路由**: 根据意图动态选择执行路径
3. **执行流管理**: 管理"思考-工具调用-响应"的完整生命周期
4. **流式输出**: 支持将推理步骤和最终结果流式传输给前端

## 文件位置

```
packages/sage-studio/src/sage/studio/services/agent_orchestrator.py
packages/sage-studio/tests/unit/test_agent_orchestrator.py
```

## 接口设计

```python
"""
Agent Orchestrator for SAGE Studio

Layer: L6 (sage-studio)
Dependencies: IntentClassifier, KnowledgeManager, WorkflowGenerator
"""

from __future__ import annotations

from typing import AsyncGenerator, Any, Dict, List
from dataclasses import dataclass

from sage.studio.services.intent_classifier import IntentClassifier, UserIntent, IntentResult
from sage.studio.services.knowledge_manager import KnowledgeManager
from sage.studio.services.memory_integration import MemoryIntegrationService
# from sage.studio.services.workflow_generator import WorkflowGenerator


@dataclass
class AgentStep:
    """Agent 执行步骤（用于前端展示）"""
    step_id: str
    type: str  # "reasoning", "tool_call", "tool_result", "response"
    content: str
    status: str = "pending"  # "pending", "running", "completed", "failed"
    metadata: Dict[str, Any] = None


class AgentOrchestrator:
    """Agent 编排器

    协调 IntentClassifier, KnowledgeManager 和各种 Tools 来处理用户请求。
    """

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.knowledge_manager = KnowledgeManager()
        self.memory_service = MemoryIntegrationService()
        # self.workflow_generator = WorkflowGenerator()
        self.tools = {}  # 注册的工具集合

    async def process_message(
        self,
        message: str,
        session_id: str,
        history: List[Dict[str, str]]
    ) -> AsyncGenerator[AgentStep | str, None]:
        """处理用户消息（生成器模式）

        Yields:
            AgentStep: 执行步骤更新（用于 UI 展示推理过程）
            str: 最终回复的文本片段（用于打字机效果）
        """
        # 0. 记忆增强 (RAG)
        yield AgentStep(..., type="reasoning", content="正在检索记忆上下文...")
        context = await self.memory_service.get_context(session_id, message)

        # 1. 意图识别 (带上下文)
        yield AgentStep(..., type="reasoning", content="正在分析用户意图...")
        intent_result = await self.intent_classifier.classify(message, history, context)
        yield AgentStep(..., type="reasoning", content=f"识别意图: {intent_result.intent.value}")

        # 2. 路由分发
        if intent_result.intent == UserIntent.KNOWLEDGE_QUERY:
            async for chunk in self._handle_knowledge_query(message, intent_result, context):
                yield chunk

        elif intent_result.intent == UserIntent.PIPELINE_GENERATION:
            async for chunk in self._handle_pipeline_generation(message, intent_result, context):
                yield chunk

        elif intent_result.intent == UserIntent.SYSTEM_OPERATION:
            async for chunk in self._handle_system_operation(message, intent_result, context):
                yield chunk

        else:
            # 默认普通对话
            async for chunk in self._handle_general_chat(message, history, context):
                yield chunk

        # 3. 记忆更新
        await self.memory_service.add_context(session_id, {"role": "user", "content": message})
        # 注意：assistant 的回复需要在 handle 方法中收集并添加

    async def _handle_knowledge_query(
        self,
        query: str,
        intent: IntentResult
    ) -> AsyncGenerator[AgentStep | str, None]:
        """处理知识问答"""
        # 1. 检查并加载所需知识源
        yield AgentStep(..., type="tool_call", content=f"检索知识库: {intent.suggested_sources}")

        for source in intent.suggested_sources:
            await self.knowledge_manager.ensure_source_loaded(source)

        # 2. 执行检索
        results = await self.knowledge_manager.search(query, sources=intent.suggested_sources)
        yield AgentStep(..., type="tool_result", content=f"找到 {len(results)} 条相关记录")

        # 3. 生成回答 (RAG)
        context = "\n\n".join([r.content for r in results])
        prompt = f"基于以下参考资料回答问题:\n\n{context}\n\n问题: {query}"

        # 调用 LLM 生成回答
        # ...
```

## 核心逻辑流程

### 1. 意图路由表

| 意图类型 | 处理逻辑 | 涉及组件 |
|---------|---------|---------|
| `KNOWLEDGE_QUERY` | RAG 流程：加载源 -> 检索 -> 生成 | KnowledgeManager, LLM |
| `PIPELINE_GENERATION` | 工作流生成：分析需求 -> 生成配置 -> 可视化 | WorkflowGenerator |
| `CODE_ASSISTANCE` | 代码助手：检索 API -> 生成代码 | KnowledgeManager (API docs), LLM |
| `SYSTEM_OPERATION` | 工具调用：解析参数 -> 调用系统 API | SystemTools |
| `GENERAL_CHAT` | 直接对话：调用 LLM | LLM |

### 2. 上下文管理

Orchestrator 需要维护当前会话的上下文，特别是：
- **当前任务状态**: 是否正在生成 Pipeline？是否在等待用户确认？
- **工具执行结果**: 上一步工具的输出作为下一步的输入。

### 3. 错误处理与回退

- 如果意图识别置信度低 -> 回退到 `GENERAL_CHAT` 并尝试引导用户。
- 如果知识库检索无结果 -> 尝试使用 LLM 内部知识回答，并注明来源。
- 如果工具调用失败 -> 返回错误信息并建议重试。

## 集成点

需要修改 `packages/sage-studio/src/sage/studio/config/backend/api.py` 中的 Chat 接口：

```python
# 原有代码
@app.post("/api/chat/message")
async def send_chat_message(request: ChatRequest):
    # ... 直接调用 gateway ...

# 修改后
from sage.studio.services.agent_orchestrator import AgentOrchestrator
orchestrator = AgentOrchestrator()

@app.post("/api/chat/message")
async def send_chat_message(request: ChatRequest):
    # 使用 StreamingResponse 返回 SSE 流
    return StreamingResponse(
        orchestrator.process_message(request.message, request.session_id, ...),
        media_type="text/event-stream"
    )
```

## 测试计划

```python
# tests/unit/test_agent_orchestrator.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from sage.studio.services.agent_orchestrator import AgentOrchestrator

class TestAgentOrchestrator:

    @pytest.fixture
    def orchestrator(self):
        orch = AgentOrchestrator()
        orch.intent_classifier = AsyncMock()
        orch.knowledge_manager = AsyncMock()
        return orch

    @pytest.mark.asyncio
    async def test_knowledge_query_flow(self, orchestrator):
        # Mock intent
        orchestrator.intent_classifier.classify.return_value = IntentResult(
            intent=UserIntent.KNOWLEDGE_QUERY,
            confidence=0.9,
            suggested_sources=["sage_docs"]
        )

        # Mock search
        orchestrator.knowledge_manager.search.return_value = [
            SearchResult(content="SAGE is...", score=0.8, source="sage_docs")
        ]

        # Run process
        steps = []
        async for chunk in orchestrator.process_message("What is SAGE?", "sess_1", []):
            if isinstance(chunk, AgentStep):
                steps.append(chunk)

        # Verify flow
        assert any(s.type == "reasoning" for s in steps)
        assert any(s.type == "tool_call" for s in steps)
        orchestrator.knowledge_manager.ensure_source_loaded.assert_called_with("sage_docs")
```

## 提示词（复制使用）

```
请在 SAGE 项目中实现 AgentOrchestrator 编排器。

## 背景
SAGE Studio 需要一个中心化的编排器来协调 Multi-Agent 系统的运行，替代原有的简单对话逻辑。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/services/agent_orchestrator.py
2. 实现 AgentOrchestrator 类
3. 集成 IntentClassifier (Task 1) 和 KnowledgeManager (Task 2)
4. 实现 process_message 方法，使用 AsyncGenerator 返回执行步骤和回答
5. 实现针对不同意图的处理逻辑 (_handle_knowledge_query, _handle_pipeline_generation 等)
6. 定义 AgentStep 数据结构，用于前端展示推理过程

## 注意
- 这是一个异步服务
- 需要处理流式输出 (SSE 格式友好)
- 做好错误处理和降级策略
- 暂时 Mock 缺失的组件 (如 WorkflowGenerator)
```

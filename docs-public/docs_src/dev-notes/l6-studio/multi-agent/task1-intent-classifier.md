# Task 1: Intent Classifier (意图分类器)

## 任务概述

实现用户意图分类器，用于判断用户消息的意图类型，决定是否需要调用知识库检索、工作流生成等功能。

**优先级**: P0 (高)\
**预计工时**: 2-3 天\
**可并行**: 是（无外部依赖）

**✨ 关键改进**: 复用 `sage-libs` 中已有的工具选择（Tool Selection）算法作为意图分类的基础！

## 背景与架构决策

### 现有资源

SAGE 在 `sage-libs` 和 `sage-benchmark` 中已经实现了完善的 **Tool Selection** 算法和评测框架：

1. **多种工具选择策略** (`sage.libs.agentic.agents.action.tool_selection`):

   - `KeywordSelector`: 基于关键词匹配
   - `EmbeddingSelector`: 基于语义向量相似度
   - `HybridSelector`: 混合策略（关键词 + Embedding）
   - `GorillaSelector`: 使用 Gorilla API 调用模型
   - `DFSDTSelector`: ToolLLM 的检索增强方法

1. **统一接口** (`SelectorRegistry`):

   ```python
   from sage.libs.agentic.agents.action.tool_selection import (
       get_selector, create_selector_from_config, SelectorConfig
   )
   selector = get_selector("hybrid", resources)
   ```

1. **Benchmark 评测** (`sage-benchmark/benchmark_agent`):

   - 1000+ 工具的真实测试集
   - 标准化评测指标（Accuracy, Recall@5, MRR）

### 设计决策

**将"意图分类"建模为"特殊的工具选择问题"**：

| 传统工具选择                   | Studio 意图分类         |
| ------------------------------ | ----------------------- |
| 输入：用户查询                 | 输入：用户消息          |
| 候选集：1000+ 工具             | 候选集：5 种意图类型    |
| 输出：Top-K 工具               | 输出：最佳意图 + 置信度 |
| 方法：Keyword/Embedding/Hybrid | **直接复用这些方法**    |

**优势**：

- ✅ 复用成熟算法，避免重复造轮子
- ✅ 继承 benchmark 验证的性能表现
- ✅ 统一的配置和注册机制
- ✅ 未来可无缝切换更先进的方法（如 SIAS）

## 目标

1. **复用 sage-libs Tool Selector**：将意图作为"伪工具"定义
1. 支持规则匹配（KeywordSelector）和语义匹配（EmbeddingSelector）两种模式
1. 返回意图类型和置信度
1. 为后续升级到 LLM-based 分类留接口

## 文件位置

```
packages/sage-studio/src/sage/studio/services/intent_classifier.py
packages/sage-studio/tests/unit/test_intent_classifier.py
```

## 接口设计

### 1. 意图定义为"伪工具"

```python
"""
Intent Classifier for SAGE Studio Multi-Agent

基于 sage-libs Tool Selection 框架实现意图分类。

Layer: L6 (sage-studio)
Dependencies: sage-libs (tool selection)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sage.libs.agentic.agents.action.tool_selection import (
    SelectorResources,
    ToolPrediction,
    ToolSelectionQuery,
    get_selector,
)
from sage.libs.agentic.agents.action.tool_selection.schemas import Tool


class UserIntent(Enum):
    """用户意图类型"""

    KNOWLEDGE_QUERY = "knowledge_query"
    PIPELINE_GENERATION = "pipeline_gen"
    CODE_ASSISTANCE = "code_assist"
    GENERAL_CHAT = "general_chat"
    SYSTEM_OPERATION = "system_op"


# 将意图定义为"伪工具"，复用 Tool Selection 框架
INTENT_TOOLS = [
    Tool(
        tool_id="intent_knowledge_query",
        name="Knowledge Query Handler",
        description="处理关于 SAGE 框架的知识性问题，如'怎么使用 Operator'、'什么是 Pipeline'、'API 文档'",
        keywords=["怎么", "如何", "什么是", "why", "how to", "what is", "explain",
                  "SAGE", "operator", "pipeline", "文档", "documentation", "示例", "example"],
        category="intent",
    ),
    Tool(
        tool_id="intent_pipeline_generation",
        name="Pipeline Generation Handler",
        description="生成数据处理工作流，如'创建 RAG pipeline'、'搭建问答系统'、'设计数据处理流程'",
        keywords=["创建", "生成", "搭建", "构建", "设计", "create", "build", "generate",
                  "pipeline", "工作流", "流程", "RAG", "问答", "数据处理"],
        category="intent",
    ),
    Tool(
        tool_id="intent_code_assistance",
        name="Code Assistance Handler",
        description="代码相关问题，如'这段代码有问题'、'帮我写函数'、'调试错误'",
        keywords=["代码", "code", "bug", "错误", "error", "调试", "debug",
                  "函数", "function", "类", "class"],
        category="intent",
    ),
    Tool(
        tool_id="intent_system_operation",
        name="System Operation Handler",
        description="系统操作请求，如'启动服务'、'查看状态'、'配置参数'",
        keywords=["启动", "停止", "重启", "状态", "start", "stop", "restart",
                  "服务", "service", "配置", "config"],
        category="intent",
    ),
    Tool(
        tool_id="intent_general_chat",
        name="General Chat Handler",
        description="普通对话，如'你好'、'谢谢'、'再见'",
        keywords=["你好", "谢谢", "再见", "hello", "hi", "thanks", "bye"],
        category="intent",
    ),
]


@dataclass
class IntentResult:
    """意图分类结果"""

    intent: UserIntent
    confidence: float
    matched_keywords: list[str] = field(default_factory=list)
    suggested_sources: list[str] = field(default_factory=list)
    raw_prediction: ToolPrediction | None = None  # 保留原始预测


class IntentClassifier:
    """意图分类器（基于 Tool Selector）

    Example:
        >>> classifier = IntentClassifier(mode="hybrid")  # 或 "keyword", "embedding"
        >>> result = await classifier.classify("怎么使用 SAGE 的 Operator?")
        >>> print(result.intent)
        UserIntent.KNOWLEDGE_QUERY
        >>> print(result.confidence)
        0.85
    """

    def __init__(
        self,
        mode: str = "hybrid",  # "keyword", "embedding", "hybrid"
        embedding_model: str = "BAAI/bge-m3",
    ):
        """
        Args:
            mode: 选择器模式 (复用 sage-libs selector)
            embedding_model: Embedding 模型（仅 embedding/hybrid 模式需要）
        """
        self.mode = mode

        # 准备 SelectorResources
        self.resources = SelectorResources(
            tools_data=INTENT_TOOLS,
            embedding_model=embedding_model,
            # vector_db 可选，简单场景下直接内存检索即可
        )

        # 获取 Selector（复用 sage-libs）
        self.selector = get_selector(mode, self.resources)

    async def classify(
        self,
        message: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> IntentResult:
        """分类用户意图

        Args:
            message: 用户输入消息
            conversation_history: 对话历史（可选，用于上下文理解）

        Returns:
            IntentResult 包含意图类型、置信度等信息
        """
        # 构建查询（复用 ToolSelectionQuery）
        query = ToolSelectionQuery(
            sample_id="intent_classification",
            instruction=message,
            candidate_tools=[tool.tool_id for tool in INTENT_TOOLS],
            context={"history": conversation_history} if conversation_history else {},
        )

        # 调用 Selector
        predictions = await self.selector.select(query, top_k=1)

        if not predictions:
            # 默认回退到 GENERAL_CHAT
            return IntentResult(
                intent=UserIntent.GENERAL_CHAT,
                confidence=0.3,
            )

        # 解析结果
        top_prediction = predictions[0]
        intent_id = top_prediction.tool_id.replace("intent_", "")

        # 映射建议的知识源
        suggested_sources = self._get_suggested_sources(intent_id)

        return IntentResult(
            intent=UserIntent(intent_id),
            confidence=top_prediction.score,
            matched_keywords=getattr(top_prediction, "matched_keywords", []),
            suggested_sources=suggested_sources,
            raw_prediction=top_prediction,
        )

    def _get_suggested_sources(self, intent_id: str) -> list[str]:
        """根据意图推荐知识源"""
        mapping = {
            "knowledge_query": ["sage_docs", "examples", "api_reference"],
            "code_assist": ["api_reference", "examples"],
            "pipeline_generation": ["examples"],
        }
        return mapping.get(intent_id, [])
```

### 2. 配置与扩展

可通过配置文件切换策略：

```yaml
# config/intent_classifier.yaml
selector:
  mode: hybrid  # keyword, embedding, hybrid, gorilla
  embedding_model: BAAI/bge-m3
  top_k: 1

  # Hybrid 模式参数
  keyword_weight: 0.3
  embedding_weight: 0.7
```

## 实现步骤

### Step 1: 定义意图伪工具

在 `intent_classifier.py` 中定义 `INTENT_TOOLS`，将每种意图建模为一个"工具"。

### Step 2: 初始化 Selector

```python
from sage.libs.agentic.agents.action.tool_selection import (
    get_selector, SelectorResources
)

resources = SelectorResources(tools_data=INTENT_TOOLS, ...)
selector = get_selector("hybrid", resources)  # 或 "keyword", "embedding"
```

### Step 3: 实现 classify 方法

将用户消息转换为 `ToolSelectionQuery`，调用 `selector.select()`，解析结果。

### Step 4: （可选）增强规则

如果基础 Selector 不够精准，可以：

1. 丰富 `INTENT_TOOLS` 中的 keywords 和 description
1. 使用 `HybridSelector` 调整权重
1. 添加后处理逻辑（如排除明显错误的意图）

## 关键优势

### 1. 零开发成本的高级特性

直接继承 sage-libs Selector 的能力：

- ✅ **Embedding 缓存**: 避免重复计算
- ✅ **多种检索策略**: Keyword/Embedding/Hybrid/Gorilla/DFSDT
- ✅ **Benchmark 验证**: 在 1000+ 工具上测试过的算法
- ✅ **可配置化**: 通过 YAML 切换策略

### 2. 未来升级路径清晰

```
Phase 1: 使用 Keyword/Hybrid Selector (当前)
    ↓
Phase 2: 升级到 Gorilla (LLM-based，更精准)
    ↓
Phase 3: 接入 SIAS（训练式，持续优化）
```

只需修改配置，无需重构代码。

### 3. 与 Benchmark 对齐

Studio 的意图分类和 Benchmark 的工具选择使用**相同的算法和评测标准**，便于：

- 对比不同方法的性能（Recall@1, MRR）
- 复现论文实验
- 迁移最新研究成果

## 测试用例

````python
# tests/unit/test_intent_classifier.py

import pytest
from sage.studio.services.intent_classifier import (
    IntentClassifier,
    UserIntent,
)


class TestIntentClassifier:

    @pytest.fixture
    def classifier(self):
        return IntentClassifier(mode="rule_based")

    @pytest.mark.asyncio
    async def test_knowledge_query_chinese(self, classifier):
        result = await classifier.classify("怎么使用 SAGE 的 Operator?")
        assert result.intent == UserIntent.KNOWLEDGE_QUERY
        assert result.confidence >= 0.7
        assert "sage_docs" in result.suggested_sources

    @pytest.mark.asyncio
    async def test_knowledge_query_english(self, classifier):
        result = await classifier.classify("How to configure a Pipeline?")
        assert result.intent == UserIntent.KNOWLEDGE_QUERY

    @pytest.mark.asyncio
    async def test_pipeline_generation(self, classifier):
        result = await classifier.classify("帮我创建一个 RAG 问答 pipeline")
        assert result.intent == UserIntent.PIPELINE_GENERATION
        assert result.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_general_chat(self, classifier):
        result = await classifier.classify("你好")
        assert result.intent == UserIntent.GENERAL_CHAT

    @pytest.mark.asyncio
    async def test_code_assistance(self, classifier):
        result = await classifier.classify("这段代码有什么问题?\n```python\nprint('hello')\n```")
        assert result.intent == UserIntent.CODE_ASSISTANCE

    @pytest.mark.asyncio
    async def test_system_operation(self, classifier):
        result = await classifier.classify("启动 LLM 服务")
        assert result.intent == UserIntent.SYSTEM_OPERATION

    @pytest.mark.asyncio
    async def test_ambiguous_defaults_to_general(self, classifier):
        result = await classifier.classify("嗯")
        assert result.intent == UserIntent.GENERAL_CHAT
        assert result.confidence < 0.5


class TestIntentRules:
    """测试具体规则匹配"""

    @pytest.mark.asyncio
    async def test_negative_keywords(self, classifier):
        # "怎么创建 pipeline" 应该是 PIPELINE_GENERATION 而不是 KNOWLEDGE_QUERY
        result = await classifier.classify("怎么创建一个 pipeline?")
        assert result.intent == UserIntent.PIPELINE_GENERATION
````

## 验收标准

- [ ] 实现 `IntentClassifier` 类
- [ ] 实现规则匹配模式
- [ ] 置信度计算逻辑正确
- [ ] 单元测试覆盖率 > 80%
- [ ] 中英文意图识别准确率 > 85%
- [ ] 代码通过 `ruff` 检查
- [ ] 添加完整的 docstring

## 提示词（复制使用）

````
请在 SAGE 项目中实现 IntentClassifier 意图分类器。

## 背景
SAGE Studio 正在升级为 Multi-Agent 架构，需要一个意图分类器来判断用户消息的类型。
关键创新：**复用 sage-libs 中已有的 Tool Selection 算法**，将意图建模为"伪工具"。

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/services/intent_classifier.py
2. 导入 sage-libs Tool Selection 组件:
   ```python
   from sage.libs.agentic.agents.action.tool_selection import (
       get_selector, SelectorResources, ToolSelectionQuery
   )
   from sage.libs.agentic.agents.action.tool_selection.schemas import Tool
````

3. 定义 INTENT_TOOLS 列表，将 5 种意图建模为 Tool 对象
1. 实现 IntentClassifier 类：
   - 初始化时创建 Selector (mode="hybrid" 推荐)
   - classify() 方法将消息转为 ToolSelectionQuery，调用 selector.select()
   - 解析 ToolPrediction 为 IntentResult
1. 支持通过配置切换 Selector 模式 (keyword/embedding/hybrid)

## 关键点

- 每个意图定义详细的 description 和 keywords (这些会被 Selector 使用)
- 复用 SelectorResources 管理 Embedding 模型
- 保留 raw_prediction 字段便于调试

## 测试

编写单元测试: packages/sage-studio/tests/unit/test_intent_classifier.py

- 测试各种意图的识别准确性
- 测试 Selector 模式切换
- Mock SelectorResources 避免加载真实模型

## 依赖

- sage.libs.agentic.agents.action.tool_selection
- 无需新增外部依赖

## 注意

- Layer: L6 (sage-studio)
- 使用 async/await
- 遵循项目的代码风格（查看 tools/ruff.toml）
- 参考 sage-benchmark/benchmark_agent 中的 Selector 使用方式

```
```

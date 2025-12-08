# Task 1.4: IntentClassifier 单元测试

## 目标
为 IntentClassifier 编写完整的单元测试。

## 依赖
- Task 1.3 (IntentClassifier 实现)

## 文件位置
`packages/sage-studio/tests/unit/test_intent_classifier.py`

## 提示词

```
请为 IntentClassifier 编写单元测试。

## 要求
1. 文件位置: packages/sage-studio/tests/unit/test_intent_classifier.py

2. 测试用例覆盖:
   - test_classify_knowledge_query: 测试知识库查询意图识别
   - test_classify_pipeline_generation: 测试工作流生成意图识别
   - test_classify_code_assistance: 测试代码辅助意图识别
   - test_classify_system_operation: 测试系统操作意图识别
   - test_classify_general_chat: 测试普通闲聊意图识别
   - test_classify_paper_research: 测试论文研究意图识别
   - test_mode_switching: 测试 keyword/embedding/hybrid 模式切换
   - test_empty_message: 测试空消息处理
   - test_with_context: 测试带上下文的分类

3. 测试数据示例:
   ```python
   KNOWLEDGE_QUERY_SAMPLES = [
       "SAGE 怎么配置 LLM 服务？",
       "如何使用 KnowledgeManager？",
       "sage-libs 有哪些组件？",
   ]

   PIPELINE_GENERATION_SAMPLES = [
       "帮我创建一个 RAG 流水线",
       "生成一个数据处理工作流",
       "我想搭建一个 pipeline",
   ]

   # ... 其他意图的测试样本
   ```

4. Mock 策略:
   - Mock SelectorResources 避免加载真实 Embedding 模型
   - 对于 keyword 模式，可以不 mock 直接测试

## 代码模板
```python
import pytest
from unittest.mock import Mock, patch

from sage.studio.services.intent_classifier import (
    IntentClassifier,
    IntentResult,
    UserIntent,
)


class TestIntentClassifier:
    """IntentClassifier 单元测试"""

    @pytest.fixture
    def classifier(self):
        """创建测试用分类器（keyword 模式，不需要 embedding）"""
        return IntentClassifier(mode="keyword")

    @pytest.mark.asyncio
    async def test_classify_knowledge_query(self, classifier):
        """测试知识库查询意图"""
        result = await classifier.classify("SAGE 怎么配置 LLM？")
        assert result.intent == UserIntent.KNOWLEDGE_QUERY
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_classify_pipeline_generation(self, classifier):
        """测试工作流生成意图"""
        result = await classifier.classify("帮我创建一个 RAG 流水线")
        assert result.intent == UserIntent.PIPELINE_GENERATION

    # ... 更多测试用例


class TestIntentClassifierModes:
    """测试不同 Selector 模式"""

    def test_keyword_mode(self):
        classifier = IntentClassifier(mode="keyword")
        assert classifier.mode == "keyword"

    @patch("sage.studio.services.intent_classifier.get_selector")
    def test_hybrid_mode(self, mock_get_selector):
        mock_selector = Mock()
        mock_get_selector.return_value = mock_selector
        classifier = IntentClassifier(mode="hybrid")
        mock_get_selector.assert_called_once()
```

## 注意
- 使用 pytest 和 pytest-asyncio
- 测试应该快速执行（避免真实网络调用）
- 覆盖率目标: > 80%
```

## 验收标准
- [ ] 所有 6 种意图都有测试用例
- [ ] 测试覆盖率 > 80%
- [ ] 所有测试通过
- [ ] 测试执行时间 < 5 秒

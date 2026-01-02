# Task 1.3: IntentClassifier 核心实现

## 目标

实现 IntentClassifier 类，复用 sage-libs 的 Selector 进行意图分类。

## 依赖

- Task 1.1 (UserIntent, IntentResult)
- Task 1.2 (INTENT_TOOLS)

## 文件位置

`packages/sage-studio/src/sage/studio/services/intent_classifier.py` (追加)

## 提示词

````
请实现 IntentClassifier 类，使用 sage-libs 的 Tool Selection 框架进行意图分类。

## 背景
sage-libs 提供了多种工具选择器:
- KeywordSelector: 基于关键词匹配，速度快
- EmbeddingSelector: 基于语义相似度，更智能
- HybridSelector: 混合策略，平衡速度和准确度

## 要求
1. 导入 sage-libs 组件:
   ```python
   from sage.libs.agentic.agents.action.tool_selection import (
       get_selector,
       SelectorResources,
       ToolSelectionQuery,
   )
````

2. 实现 IntentClassifier 类:

   ```python
   class IntentClassifier:
       def __init__(
           self,
           mode: str = "hybrid",  # "keyword", "embedding", "hybrid"
           embedding_model: str | None = None,
       ):
           # 初始化 Selector
           # 加载 INTENT_TOOLS 作为候选集
           pass

       async def classify(
           self,
           message: str,
           history: list[dict[str, str]] | None = None,
           context: str | None = None,
       ) -> IntentResult:
           # 1. 构建 ToolSelectionQuery
           # 2. 调用 selector.select()
           # 3. 将 ToolPrediction 转换为 IntentResult
           pass
   ```

1. 转换逻辑:

   - ToolPrediction.tool_id → UserIntent 枚举
   - ToolPrediction.score → confidence
   - ToolPrediction.matched_keywords → matched_keywords

1. 配置支持:

   - 通过 mode 参数选择 Selector 类型
   - 支持从配置文件加载参数

## 代码模板

```python
class IntentClassifier:
    """意图分类器

    复用 sage-libs Tool Selection 框架，将意图分类建模为工具选择问题。
    """

    def __init__(
        self,
        mode: str = "hybrid",
        embedding_model: str | None = None,
    ):
        self.mode = mode

        # 准备资源
        resources = SelectorResources(
            tools_data=[t.model_dump() for t in INTENT_TOOLS],
            embedding_model=embedding_model,
        )

        # 获取 Selector
        self._selector = get_selector(mode, resources)

    async def classify(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        context: str | None = None,
    ) -> IntentResult:
        # 构建查询
        query = ToolSelectionQuery(
            instruction=message,
            context=context or "",
            candidate_tools=INTENT_TOOLS,
        )

        # 执行选择
        predictions = self._selector.select(query, top_k=1)

        if not predictions:
            return IntentResult(
                intent=UserIntent.GENERAL_CHAT,
                confidence=0.5,
                matched_keywords=[],
            )

        top = predictions[0]
        return IntentResult(
            intent=UserIntent(top.tool_id),
            confidence=top.score,
            matched_keywords=top.matched_keywords or [],
            raw_prediction=top,
        )
```

## 注意

- 处理 Selector 不可用的情况（graceful fallback）
- 添加日志记录分类过程
- 考虑异步兼容性（Selector 可能是同步的）

```

## 验收标准
- [ ] 支持 keyword/embedding/hybrid 三种模式
- [ ] classify() 方法返回正确的 IntentResult
- [ ] 处理了边界情况（空消息、Selector 失败等）
- [ ] 有适当的日志输出
```

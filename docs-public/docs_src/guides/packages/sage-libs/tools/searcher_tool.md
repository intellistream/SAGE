# SearcherTool - 搜索工具集

## 概述

SearcherTool 是 SAGE 框架中用于执行各类搜索任务的工具集合。它位于 L4 层（sage-middleware），基于 L3 层的 `BaseTool`
基类构建，提供了从学术论文到网页内容的多种搜索能力。

______________________________________________________________________

## 工具列表

| 工具名称            | 功能描述             | 数据源           |
| ------------------- | -------------------- | ---------------- |
| `ArxivSearcher`     | 搜索 arXiv 学术论文  | arxiv.org        |
| `BochaSearchTool`   | 通用网页搜索         | Bocha Search API |
| `NatureNewsFetcher` | 获取 Nature 期刊新闻 | nature.com       |

______________________________________________________________________

## 架构设计

### 继承关系

```
sage.libs.foundation.tools.BaseTool (L3)
    │
    ├── ArxivSearcher (L4)
    │
    ├── BochaSearchTool (L4, MapOperator)
    │
    └── NatureNewsFetcher (L4)
```

### 设计模式

所有搜索工具遵循**统一接口模式**：

```python
class BaseTool(ABC):
    """工具基类 - 定义标准接口"""

    def __init__(
        self,
        tool_name: str,
        tool_description: str,
        input_types: list[str] | dict[str, str],
        output_type: str,
        demo_commands: list[str] | list[dict],
        require_llm_engine: bool = False,
    ): ...

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """执行工具的核心功能"""
```

______________________________________________________________________

## ArxivSearcher

用于搜索 arXiv 学术论文数据库。

### 使用示例

```python
from sage.middleware.operators.tools import ArxivSearcher

# 创建搜索器
searcher = ArxivSearcher()

# 搜索论文
results = searcher.execute(
    query="large language models",
    max_results=10
)

# 处理结果
for paper in results:
    print(f"标题: {paper['title']}")
    print(f"作者: {', '.join(paper['authors'])}")
    print(f"摘要: {paper['abstract'][:200]}...")
    print(f"链接: {paper['url']}")
    print("---")
```

### API 参考

```python
class ArxivSearcher(BaseTool):
    def execute(
        self,
        query: str,
        max_results: int = 10
    ) -> list[dict]:
        """
        搜索 arXiv 论文

        Args:
            query: 搜索关键词
            max_results: 最大结果数量（上限 100）

        Returns:
            论文列表，每项包含:
            - title: 论文标题
            - authors: 作者列表
            - abstract: 摘要
            - published: 发表日期
            - url: arXiv 链接
            - categories: 分类标签
        """
```

______________________________________________________________________

## BochaSearchTool

通用网页搜索工具，集成 Bocha Search API，可作为 Pipeline 算子使用。

### 配置

```python
from sage.middleware.operators.tools import BochaSearchTool

config = {
    "url": "https://api.bochasearch.com/search",
    "api_key": "your-api-key",  # 或设置 BOCHA_API_KEY 环境变量
    "max_results_per_query": 5,
    "search_engine_name": "Bocha"
}

searcher = BochaSearchTool(config)
```

### 在 Pipeline 中使用

```python
from sage.kernel.api.local_environment import LocalEnvironment
from sage.middleware.operators.tools import BochaSearchTool

env = LocalEnvironment()

# 作为 Map 算子使用
(
    env.from_source(QuerySource, queries)
    .map(BochaSearchTool, config=search_config)
    .sink(ResultSink)
)

env.submit()
```

### 搜索结果结构

```python
@dataclass
class SearchResult:
    title: str           # 结果标题
    content: str         # 内容摘要
    source: str          # 来源 URL
    rank: int            # 排名位置
    relevance_score: float  # 相关性评分 (0-1)
```

______________________________________________________________________

## 与 Agent 集成

搜索工具可以被 Agent 动态调用：

```python
from sage.libs.agentic import Agent
from sage.middleware.operators.tools import ArxivSearcher

# 注册搜索工具
agent = Agent()
agent.register_tool(ArxivSearcher())

# Agent 可以根据用户意图调用搜索
response = agent.run("帮我查找关于 Transformer 的最新论文")
```

______________________________________________________________________

## 自定义搜索工具

基于 `BaseTool` 创建自定义搜索工具：

```python
from sage.libs.foundation.tools import BaseTool

class CustomSearcher(BaseTool):
    def __init__(self):
        super().__init__(
            tool_name="custom_searcher",
            tool_description="自定义搜索工具",
            input_types={"query": "str - 搜索关键词"},
            output_type="list - 搜索结果列表",
            demo_commands=[
                {"command": "tool.execute(query='example')", "description": "示例搜索"}
            ],
        )

    def execute(self, query: str, **kwargs) -> list[dict]:
        # 实现自定义搜索逻辑
        results = self._call_search_api(query)
        return results

    def _call_search_api(self, query: str) -> list[dict]:
        # 调用外部 API
        ...
```

______________________________________________________________________

## 最佳实践

1. **API 密钥管理**：使用环境变量存储 API 密钥，避免硬编码
1. **结果数量限制**：合理设置 `max_results` 以平衡速度和覆盖率
1. **错误处理**：搜索工具应优雅处理网络错误和 API 限流
1. **结果缓存**：对重复查询考虑缓存机制以提高效率
1. **日志记录**：使用工具内置的 logger 记录搜索行为

______________________________________________________________________

## 相关文档

- [Tools 模块概览](../tools_intro.md)
- [Agent 集成指南](../agents.md)
- [BaseTool API 参考](../../../../api-reference/libs/tools.md)

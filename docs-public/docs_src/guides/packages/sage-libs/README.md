# SAGE Applications 应用组件

SAGE Applications 是基于 SAGE Kernel 和 Middleware
构建的高级应用组件库，提供了一系列开箱即用的AI和数据处理应用模块。这些组件可以独立使用，也可以组合构建复杂的智能应用。

## 🏗️ 架构定位

```
┌─────────────────┐
│   Applications  │  ← 高级应用组件 (当前文档)
├─────────────────┤
│   Middleware    │  ← 中间件服务层
├─────────────────┤  
│   SAGE Kernel   │  ← 核心流处理引擎
└─────────────────┘
```

Applications 层是面向最终用户的高级抽象，将复杂的AI任务封装为简单易用的组件，让开发者能够快速构建生产级的智能应用。

## 🧩 核心组件

### RAG (检索增强生成)

构建强大的问答和内容生成系统：

- [RAG 应用](rag.md) - 检索增强生成的完整解决方案
- 支持多种检索策略（稀疏、密集、混合）
- 内置重排序和结果优化
- 支持多种LLM后端

### Agents (智能代理)

自主决策和任务执行的智能体：

- [智能代理](agents.md) - 自主规划和执行的AI代理
- 支持工具调用和环境交互
- 多代理协作框架
- 可插拔的推理引擎

### Tools (工具集)

即插即用的功能组件：

- [工具概览](tools_intro.md) - 工具生态系统介绍
- [Arxiv Paper Searcher](tools/arxiv_paper_searcher.md) - 学术论文搜索
- [Image Captioner](tools/image_captioner.md) - 图像描述生成
- [Nature News Fetcher](tools/nature_news_fetcher.md) - 科学新闻获取
- [Searcher Tool](tools/searcher_tool.md) - 通用搜索工具
- [Text Detector](tools/text_detector.md) - 文本检测分析
- [URL Text Extractor](tools/url_text_extractor.md) - 网页文本提取

### IO 组件

数据输入输出的标准化接口：

- [IO 模块](io.md) - 统一的数据输入输出接口
- 支持多种数据源（文件、数据库、API）
- 标准化的数据格式转换
- 流式和批量处理模式

### Context 管理

上下文和状态管理：

- [Context 管理](context.md) - 应用上下文和状态管理
- 跨组件的状态共享
- 会话和用户上下文
- 分布式状态同步

### Embedding 服务

向量化和相似性计算：

- [Embedding 服务](embedding.md) - 文本和多模态向量化
- 支持多种预训练模型
- 批量向量化处理
- 相似性搜索优化

## 🚀 快速开始

### RAG 应用示例

```python
from sage.applications.rag import RAGPipeline
from sage.applications.io import FileSource

# 创建RAG管道
rag = RAGPipeline(model_name="gpt-3.5-turbo", retriever_type="hybrid")  # 混合检索

# 添加知识库
docs = FileSource("knowledge_base/").load()
rag.add_documents(docs)

# 查询
answer = rag.query("SAGE框架的主要特性是什么？")
print(answer)
```

### Agent 应用示例

```python
from sage.applications.agents import Agent
from sage.applications.tools import ArxivSearcher, ImageCaptioner

# 创建智能代理
agent = Agent(
    name="研究助手",
    description="帮助用户进行学术研究",
    tools=[ArxivSearcher(), ImageCaptioner()],
)

# 执行任务
result = agent.execute("帮我搜索关于深度学习的最新论文，并生成摘要")
print(result)
```

### 工具组合示例

```python
from sage.applications.tools import URLTextExtractor, TextDetector
from sage.core.api import LocalEnvironment

# 创建处理管道
env = LocalEnvironment("text_analysis")

# 工具组合处理
extractor = URLTextExtractor()
detector = TextDetector()


def analyze_webpage(url):
    # 提取网页文本
    text = extractor.extract(url)

    # 检测文本特征
    analysis = detector.analyze(text)

    return {
        "url": url,
        "text_length": len(text),
        "language": analysis["language"],
        "sentiment": analysis["sentiment"],
        "topics": analysis["topics"],
    }


# 批量处理URL
urls = ["https://example1.com", "https://example2.com"]
results = [analyze_webpage(url) for url in urls]
```

## 🔧 自定义组件

### 创建自定义RAG组件

```python
from sage.applications.rag import BaseRetriever, BaseGenerator


class CustomRetriever(BaseRetriever):
    def retrieve(self, query, top_k=10):
        # 实现自定义检索逻辑
        pass


class CustomGenerator(BaseGenerator):
    def generate(self, context, query):
        # 实现自定义生成逻辑
        pass


# 使用自定义组件
rag = RAGPipeline(retriever=CustomRetriever(), generator=CustomGenerator())
```

### 创建自定义工具

```python
from sage.applications.tools import BaseTool


class WeatherTool(BaseTool):
    name = "weather_checker"
    description = "获取指定城市的天气信息"

    def execute(self, city: str) -> dict:
        # 实现天气查询逻辑
        return {"city": city, "temperature": "25°C", "description": "晴天"}


# 注册和使用工具
agent.add_tool(WeatherTool())
result = agent.execute("查询北京的天气")
```

### 创建自定义Agent

```python
from sage.applications.agents import BaseAgent


class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Research Assistant", system_prompt="你是一个专业的学术研究助手..."
        )

    def plan_task(self, task):
        # 任务规划逻辑
        pass

    def execute_step(self, step):
        # 步骤执行逻辑
        pass
```

## 🔗 组件集成

### 多组件协作

```python
from sage.applications import RAGPipeline, Agent
from sage.applications.tools import ArxivSearcher

# 创建RAG系统
rag = RAGPipeline(model_name="gpt-4")

# 创建智能代理，集成RAG
agent = Agent(name="知识助手", tools=[ArxivSearcher()], knowledge_base=rag)

# 复杂查询处理
result = agent.execute(
    """
请帮我：
1. 搜索关于Transformer架构的最新论文
2. 总结其中的关键创新点
3. 与我的知识库中的相关内容进行对比
"""
)
```

### 流水线处理

```python
from sage.core.api import LocalEnvironment
from sage.applications.io import FileSource, FileSink

env = LocalEnvironment("document_processing")

# 构建文档处理流水线
source = FileSource("documents/")
rag = RAGPipeline()
sink = FileSink("processed/")


def process_document(doc):
    # 使用RAG处理文档
    summary = rag.summarize(doc.content)
    return {"filename": doc.name, "summary": summary, "timestamp": doc.timestamp}


# 流式处理
pipeline = env.from_source(source).map(process_document).sink(sink)

pipeline.execute()
```

## 📊 性能优化

### 批量处理

```python
from sage.applications.embedding import EmbeddingService

embedding = EmbeddingService(batch_size=32)

# 批量向量化
texts = ["文本1", "文本2", "文本3", ...]
vectors = embedding.encode_batch(texts)
```

### 缓存优化

```python
from sage.applications.cache import ComponentCache

# 启用组件缓存
cache = ComponentCache(redis_url="redis://localhost:6379")

rag = RAGPipeline(cache=cache)
agent = Agent(cache=cache)

# 自动缓存查询结果
answer1 = rag.query("问题1")  # 首次查询，计算结果
answer2 = rag.query("问题1")  # 第二次查询，返回缓存结果
```

### 并行处理

```python
import asyncio
from sage.applications.async_support import AsyncRAG


# 异步处理
async def process_queries():
    rag = AsyncRAG()

    queries = ["问题1", "问题2", "问题3"]
    tasks = [rag.query_async(q) for q in queries]

    results = await asyncio.gather(*tasks)
    return results
```

## 🔒 安全和隐私

### 数据脱敏

```python
from sage.applications.privacy import DataSanitizer

sanitizer = DataSanitizer()

# 自动脱敏处理
safe_text = sanitizer.sanitize(user_input)
answer = rag.query(safe_text)
```

### 访问控制

```python
from sage.applications.auth import ComponentAuth

auth = ComponentAuth()


# 基于角色的访问控制
@auth.require_role("admin")
def admin_query(query):
    return rag.query(query)


@auth.require_permission("read:documents")
def read_documents():
    return document_store.list()
```

______________________________________________________________________

SAGE Applications
提供了构建智能应用的完整组件生态，让开发者能够快速实现从简单的文本处理到复杂的多模态AI应用。通过标准化的接口和丰富的扩展能力，您可以根据具体需求灵活组合和定制应用组件。

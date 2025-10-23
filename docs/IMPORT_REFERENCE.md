# SAGE 快速导入参考

> 最常用的导入路径快速查询手册
> 
> 最后更新：2025-10-23（已更新至最新架构）

## 🚀 执行环境

```python
# 本地执行环境
from sage.kernel.api import LocalEnvironment

# 创建环境
env = LocalEnvironment("my_pipeline")
```

## 📊 数据源和输出

```python
# I/O 工具 (注意：io_utils 已重命名为 io)
from sage.libs.io import FileSource, TerminalSink
from sage.libs.io.batch import JSONLBatch

# 使用
env.from_source(FileSource, {"file_path": "data.txt"})
env.from_batch(JSONLBatch, {"file_path": "data.jsonl"})
```

## 🔍 RAG 算子

```python
# RAG 核心算子（来自 middleware）
from sage.middleware.operators.rag import (
    ChromaRetriever,      # 向量检索
    QAPromptor,           # 提示构建
    OpenAIGenerator,      # 生成答案
    F1Evaluate,           # 评估
)

# 使用
(env
    .from_source(FileSource, {...})
    .map(ChromaRetriever, {"top_k": 5})
    .map(QAPromptor, {"template": "..."})
    .map(OpenAIGenerator, {"model": "gpt-3.5-turbo"})
    .map(F1Evaluate)
    .sink(TerminalSink)
)
```

## 🤖 Agents 和 Bots

```python
# Agents 框架（来自 libs）
from sage.libs.agents import LangChainAgentAdapter

# Pre-built Bots (新增 - 2025-10-23)
from sage.libs.agents.bots import AnswerBot, QuestionBot, SearcherBot, CriticBot

# 使用 Agents
env.map(LangChainAgentAdapter, {
    "agent_config": {...},
    "tools": [...]
})

# 使用 Bots
answer_bot = AnswerBot(config={"model": "gpt-4"})
question_bot = QuestionBot(config={"role": "interviewer"})
```

## 🔌 第三方集成

```python
# 第三方服务集成（新模块 - 2025-10-23）
from sage.libs.integrations import (
    OpenAIClient,      # OpenAI API
    MilvusBackend,     # Milvus 向量数据库
    ChromaBackend,     # ChromaDB
    HFClient,          # Hugging Face
)

# 使用示例
client = OpenAIClient(api_key="...")
response = client.chat_completion(messages=[...])
```

## 🎯 数据过滤器

```python
# 数据过滤和转换（新模块 - 2025-10-23）
from sage.libs.filters import (
    ToolFilter,        # 工具过滤
    EvaluateFilter,    # 评估过滤
    ContextSource,     # 上下文源
    ContextSink,       # 上下文汇
)
```

## 💾 内存和存储

```python
# 内存管理（来自 middleware）
from sage.middleware.components.sage_mem import MemoryManager, NeuroMemVDB

# 向量数据库（来自 middleware）
from sage.middleware.components.sage_db import VectorDBManager

# 使用
manager = MemoryManager(data_dir="./data")
collection = manager.create_collection({...})
```

## 🛠️ 基础算子

```python
# 基础 Function 类（来自 kernel）
from sage.kernel.api.function import (
    MapFunction,       # 一对一转换
    FlatMapFunction,   # 一对多转换
    FilterFunction,    # 过滤
    BatchFunction,     # 批处理源
    SourceFunction,    # 流式源
    SinkFunction,      # 输出
)

# 自定义算子
class MyMap(MapFunction):
    def execute(self, data):
        return data.upper()
```

## 🔧 核心类型

```python
# 核心数据类型（来自 common）
from sage.common.core import (
    Parameter,         # 参数类
    Record,            # 数据记录
    WindowedRecord,    # 窗口记录
)
```

## 📝 配置和日志

```python
# 配置（来自 common）
from sage.common.config import load_config

# 日志（来自 common）
from sage.common.utils.logging.custom_logger import CustomLogger

# 使用
config = load_config("config.yaml")
logger = CustomLogger("my_pipeline")
```

## 🎯 完整示例

### 简单的 RAG Pipeline

```python
from sage.kernel.api import LocalEnvironment
from sage.libs.io import FileSource, TerminalSink
from sage.middleware.operators.rag import (
    ChromaRetriever,
    QAPromptor,
    OpenAIGenerator
)

# 创建环境
env = LocalEnvironment("rag_demo")

# 构建 pipeline
(env
    .from_source(FileSource, {
        "file_path": "questions.txt"
    })
    .map(ChromaRetriever, {
        "top_k": 5,
        "collection_name": "docs"
    })
    .map(QAPromptor, {
        "template": "Answer based on: {context}\nQ: {query}\nA:"
    })
    .map(OpenAIGenerator, {
        "model": "gpt-3.5-turbo",
        "temperature": 0.7
    })
    .sink(TerminalSink)
)

# 执行
env.submit()
```

### 自定义算子

```python
from sage.kernel.api import LocalEnvironment
from sage.kernel.api.function import MapFunction, BatchFunction, SinkFunction

# 自定义数据源
class HelloBatch(BatchFunction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.count = 0
    
    def execute(self):
        if self.count >= 10:
            return None
        self.count += 1
        return f"Hello #{self.count}"

# 自定义转换
class UpperCase(MapFunction):
    def execute(self, data):
        return data.upper()

# 自定义输出
class PrintSink(SinkFunction):
    def execute(self, data):
        print(data)

# 使用
env = LocalEnvironment("custom_pipeline")
(env
    .from_batch(HelloBatch)
    .map(UpperCase)
    .sink(PrintSink)
)
env.submit(autostop=True)
```

## 📦 包结构速查

| 你需要... | 从这里导入 | 示例 |
|----------|-----------|------|
| 执行环境 | `sage.kernel.api` | `LocalEnvironment` |
| 基础算子类 | `sage.kernel.api.function` | `MapFunction` |
| I/O 工具 | `sage.libs.io` | `FileSource` |
| RAG 算子 | `sage.middleware.operators.rag` | `ChromaRetriever` |
| LLM 算子 | `sage.middleware.operators.llm` | `ChatOperator` |
| Agents | `sage.libs.agents` | `LangChainAgentAdapter` |
| 内存管理 | `sage.middleware.components.sage_mem` | `MemoryManager` |
| 向量数据库 | `sage.middleware.components.sage_db` | `VectorDBManager` |
| 核心类型 | `sage.common.core` | `Parameter`, `Record` |
| 配置 | `sage.common.config` | `load_config` |
| 日志 | `sage.common.utils.logging` | `CustomLogger` |

## 🎓 学习路径

### 初学者（从这里开始）

1. **Hello World** - 理解基本 pipeline
   ```python
   from sage.kernel.api import LocalEnvironment
   from sage.kernel.api.function import BatchFunction, MapFunction, SinkFunction
   ```

2. **数据处理** - 学习 I/O
   ```python
   from sage.libs.io import FileSource, TerminalSink
   ```

3. **RAG 基础** - 构建 RAG pipeline
   ```python
   from sage.middleware.operators.rag import ChromaRetriever, QAPromptor, OpenAIGenerator
   ```

### 进阶开发者

4. **自定义算子** - 实现复杂逻辑
5. **Agents 系统** - 构建智能代理
6. **分布式执行** - 扩展到多节点

## 💡 提示

- **总是从公共 API 导入**，不要导入内部模块
- **查看 `__init__.py`** 了解包导出了什么
- **参考 `examples/`** 目录获取更多示例
- **使用 `sage doctor`** 检查安装是否正确

## 📚 更多资源

- [完整包架构](./PACKAGE_ARCHITECTURE.md) - 详细的包结构说明
- [API 文档](../packages/) - 每个包的详细文档
- [示例代码](../examples/) - 实际可运行的示例
- [贡献指南](../CONTRIBUTING.md) - 如何参与开发

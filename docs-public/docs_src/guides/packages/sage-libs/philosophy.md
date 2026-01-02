# SAGE Libs 设计哲学

## 概述

SAGE Libs 是 SAGE 框架的核心算法库层（L3），其设计遵循"分层解耦、组合优先"的核心理念。本文档阐述了 SAGE Libs 的设计哲学和架构原则。

______________________________________________________________________

## 核心设计原则

### 1. 分层架构 (Layered Architecture)

SAGE Libs 位于 L3 层，严格遵循依赖方向规则：

```
L6: sage-cli, sage-studio, sage-tools, sage-llm-gateway  # 应用层
L5: sage-apps, sage-benchmark                        # 应用与基准测试
L4: sage-middleware                                  # 算子与编排
L3: sage-kernel, sage-libs  ← 我们在这里           # 核心与算法
L2: sage-platform                                    # 平台服务
L1: sage-common                                      # 基础设施
```

**关键规则**：

- SAGE Libs 只能依赖 L1 (`sage-common`) 和 L2 (`sage-platform`)
- 上层模块（L4-L6）可以导入 SAGE Libs，反之不行
- 这确保了算法的独立性和可复用性

### 2. 纯算法分离 (Pure Algorithm Separation)

SAGE Libs 专注于**纯算法实现**，不包含：

- Pipeline 编排逻辑（属于 L4）
- 分布式调度（属于 L2/L4）
- 用户界面（属于 L6）
- 外部服务依赖（通过接口抽象）

```python
# ✅ SAGE Libs 风格：纯算法类
class CharacterSplitter:
    """纯文本分块算法，不依赖任何 SAGE 算子"""
    def __init__(self, chunk_size: int = 512, overlap: int = 128):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> list[str]:
        # 纯 Python 实现
        ...
```

### 3. 组合优先于继承 (Composition over Inheritance)

SAGE Libs 中的组件设计为可组合的积木：

```python
# 组合使用多个组件
from sage.libs.rag import CharacterSplitter, LoaderFactory
from sage.libs.foundation.tools import BaseTool

# 加载 → 分块 → 处理
loader = LoaderFactory.create("pdf")
splitter = CharacterSplitter(chunk_size=800)

text = loader.load("document.pdf")
chunks = splitter.split(text)
```

______________________________________________________________________

## 模块组织

SAGE Libs 按功能域组织为以下模块：

| 模块           | 功能                         | 层级定位     |
| -------------- | ---------------------------- | ------------ |
| `foundation`   | 基础工具、IO、上下文管理     | 最底层工具   |
| `agentic`      | Agent 框架、工作流优化       | 高级编排     |
| `rag`          | RAG 构建块（加载器、分块器） | 检索增强生成 |
| `integrations` | 第三方服务适配器             | 外部集成     |
| `privacy`      | 机器遗忘、隐私保护算法       | 隐私计算     |
| `finetune`     | 模型微调工具                 | 模型训练     |

______________________________________________________________________

## 设计模式

### 工厂模式 (Factory Pattern)

统一创建接口，隐藏实现细节：

```python
from sage.libs.rag import LoaderFactory

# 根据文件类型自动选择加载器
loader = LoaderFactory.create("pdf")  # 返回 PDFLoader
loader = LoaderFactory.create("md")   # 返回 MarkdownLoader
```

### 策略模式 (Strategy Pattern)

可插拔的算法实现：

```python
from sage.libs.rag import CharacterSplitter, SentenceTransformersTokenTextSplitter

# 根据需求选择分块策略
splitter = CharacterSplitter(chunk_size=512)  # 字符级分块
splitter = SentenceTransformersTokenTextSplitter(chunk_size=256)  # Token 级分块
```

### 注册表模式 (Registry Pattern)

动态注册和发现组件：

```python
from sage.libs.foundation.tools import ToolRegistry

# 注册自定义工具
registry = ToolRegistry()
registry.register("my_tool", MyCustomTool)

# 按名称获取工具
tool = registry.get("my_tool")
```

______________________________________________________________________

## 与其他层的交互

### 与 L4 (sage-middleware) 的关系

- SAGE Libs 提供**算法实现**
- sage-middleware 提供**Pipeline 封装**

```python
# L3: 纯算法
from sage.libs.rag import CharacterSplitter

# L4: Pipeline 算子封装
from sage.middleware.operators.rag import ChunkerOperator  # 封装 CharacterSplitter
```

### 与 L1 (sage-common) 的关系

- sage-common 提供**基础设施**（日志、配置、工具函数）
- SAGE Libs 在此基础上构建**领域算法**

```python
# L1: 基础工具
from sage.common.utils.document_processing import chunk_text

# L3: 基于 L1 构建的高级分块器
from sage.libs.rag import CharacterSplitter  # 内部可能使用 L1 工具
```

______________________________________________________________________

## 最佳实践

1. **保持算法纯净**：避免在算法类中引入 IO、网络等副作用
1. **使用依赖注入**：通过参数传入外部依赖，而非硬编码
1. **编写单元测试**：每个算法都应有独立的单元测试
1. **文档先行**：每个公开 API 都应有清晰的文档字符串
1. **类型注解**：使用 Python 类型提示提高代码可读性

______________________________________________________________________

## 参考资料

- [SAGE 架构概览](../../architecture/overview.md)
- [sage-libs API 参考](../../../api-reference/sage-libs/README.md)
- [RAG 模块指南](./rag.md)
- [Tools 模块指南](./tools_intro.md)

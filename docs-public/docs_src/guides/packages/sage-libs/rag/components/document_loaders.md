# 文档加载组件 (Document Loading Components)

本文档详细介绍SAGE框架中`sage.libs.rag.document_loaders`模块的文档加载组件。文档加载器是RAG系统的数据入口，负责从各种数据源加载和预处理文档内容。

## 组件概述

### 核心功能

文档加载组件在RAG系统中承担以下关键职责：

- **多格式支持**：处理不同格式的文档文件
- **编码处理**：自动检测和转换文件编码
- **元数据生成**：为文档自动生成结构化元数据
- **错误处理**：提供健壮的文件读取异常管理

### 设计原则

- **可扩展性**：支持新文档格式的快速集成
- **标准化输出**：所有加载器输出统一的文档对象格式
- **性能优化**：针对大文件的内存友好处理

## TextLoader

### 组件描述

`TextLoader`是基础文本文件加载器，专门处理纯文本格式文档。该组件为其他格式加载器提供了标准实现模板。

### 技术规格

**类定义**：

```python
class TextLoader:
    def __init__(self, filepath: str, encoding: str = "utf-8", chunk_separator: str = None)
    def load(self) -> Dict[str, Any]
```

**初始化参数**：

| 参数名            | 类型 | 默认值  | 必需性 | 说明                           |
| ----------------- | ---- | ------- | ------ | ------------------------------ |
| `filepath`        | str  | -       | 必需   | 目标文本文件的绝对或相对路径   |
| `encoding`        | str  | "utf-8" | 可选   | 文件编码格式（如utf-8, gbk等） |
| `chunk_separator` | str  | None    | 可选   | 预留的分块分隔符参数           |

**输出格式**：

```python
{
    "content": str,  # 文档的完整文本内容
    "metadata": {  # 文档元数据
        "source": str,  # 源文件路径
        "encoding": str,  # 使用的编码格式
        "size": int,  # 文件大小（字节）
        "load_time": str,  # 加载时间戳
    },
}
```

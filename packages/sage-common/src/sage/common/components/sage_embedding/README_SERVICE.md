# SAGE 嵌入模型集成模块

本模块提供统一的嵌入模型接口，支持多种嵌入模型提供商的集成。

## 概述

`embedding_methods` 模块统一了各种嵌入模型API的调用方式，包括本地模型和云端API服务，为SAGE框架提供文本向量化能力。

## 支持的嵌入服务

### 本地模型
- **Hugging Face** (`hf.py`) - 本地Transformer模型
- **Instructor** (`instructor.py`) - Instructor嵌入模型
- **Ollama** (`ollama.py`) - Ollama本地部署模型
- **MockEmbedder** (`mockembedder.py`) - 测试用模拟嵌入器

### 云端API服务
- **OpenAI** (`openai.py`) - OpenAI嵌入API
- **NVIDIA OpenAI** (`nvidia_openai.py`) - NVIDIA兼容OpenAI接口
- **Bedrock** (`bedrock.py`) - AWS Bedrock嵌入服务
- **Cohere** (`_cohere.py`) - Cohere嵌入API
- **Jina** (`jina.py`) - Jina嵌入服务
- **智谱AI** (`zhipu.py`) - 智谱AI嵌入服务
- **硅基流动** (`siliconcloud.py`) - 硅基流动嵌入服务
- **LOLLMS** (`lollms.py`) - LOLLMS嵌入接口

## 核心组件

### `embedding_api.py`
统一的嵌入模型API接口，提供工厂方法创建不同类型的嵌入模型实例。

### `embedding_model.py`
定义嵌入模型的抽象基类和通用接口规范。

## 快速开始

```python
from sage.common.components.sage_embedding.embedding_api import apply_embedding_model

# 使用默认模型
model = apply_embedding_model(name="default")
embedding = model.embed("hello world")
dimension = model.get_dim()

# 使用Hugging Face模型
hf_model = apply_embedding_model(
    name="hf", 
    model="sentence-transformers/all-MiniLM-L6-v2"
)

# 使用OpenAI API
openai_model = apply_embedding_model(
    name="openai",
    api_key="your-api-key",
    model="text-embedding-ada-002"
)
```

## 使用场景

- **文档检索**: 为文档建立向量索引
- **语义搜索**: 基于语义相似度的搜索
- **文本聚类**: 文本分类和聚类分析
- **推荐系统**: 基于内容的推荐算法

## 扩展支持

可以通过实现 `EmbeddingModel` 基类来添加新的嵌入服务提供商。

更详细的使用说明请参考 [embedding.md](./embedding.md)。

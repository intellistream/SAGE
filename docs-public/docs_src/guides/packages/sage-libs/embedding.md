# Embedding 语言模型本地使用方法说明

## 概述

本文档介绍如何使用 `sage.utils.embedding_methods` 模块中的embedding功能，支持多种embedding模型的本地和远程调用。

## 快速开始

### 基本用法

```python
from sage.utils.embedding_methods.embedding_api import apply_embedding_model

# 创建embedding模型实例
model = apply_embedding_model(name="default")

# 生成文本embedding
embedding = model.embed("hello world")

# 获取embedding维度
dimension = model.get_dim()
```

## 支持的模型类型

### Default

使用默认的本能地embedding模型：

```python
from sage.utils.embedding_methods.embedding_api import apply_embedding_model

model = apply_embedding_model("default")
embedding = model.embed("hello world")
dimension = model.get_dim()
```

###Hugging Face 模型 使用Hugging Face的预训练模型：

```python
model = apply_embedding_model(name="hf", model="sentence-transformers/all-MiniLM-L6-v2")
embedding = model.embed("This is huggingface.")
dimension = model.get_dim()
```

参数说明： model: Hugging Face模型名称

### OpenAI 兼容API

使用OpenAI格式的API接口：

```python
model = apply_embedding_model(
    name="openai",
    model="BAAI/bge-m3",
    base_url="https://api.siliconflow.cn/v1",
    api_key="your_api_key_here",
)
embedding = model.embed("this is openai")
dimension = model.get_dim()
```

model: 模型名称 base_url: API基础URL api_key: API密钥

### Jina AI

使用Jina AI的embedding服务：

```python
model = apply_embedding_model(
    name="jina", model="jina-embeddings-v3", api_key="your_jina_api_key"
)
embedding = model.embed("this is jina")
dimension = model.get_dim()
```

参数说明： model: Jina模型名称 api_key: Jina API密钥

## 环境配置

### 环境变量设置

为了安全使用API密钥，建议使用环境变量：

```bash
export SILICONCLOUD_API_KEY=your_siliconcloud_key
export JINA_API_KEY=your_jina_key
export OPENAI_API_KEY=your_openai_key
...
```

或者创建`.env`文件：

```plaintext
SILICONCLOUD_API_KEY=your_siliconcloud_key
JINA_API_KEY=your_jina_key
OPENAI_API_KEY=your_openai_key
```

### 在代码中加载环境变量

```python
from dotenv import load_dotenv
import os

load_dotenv(override=False)
api_key = os.environ.get("JINA_API_KEY")
```

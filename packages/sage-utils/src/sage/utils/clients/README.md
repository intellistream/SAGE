# SAGE 客户端模块

本模块提供与外部服务和模型的客户端连接，支持多种AI服务和API的集成。

## 概述

客户端模块封装了与各种外部AI服务的通信逻辑，为SAGE框架提供标准化的模型调用接口。

## 核心组件

### `openaiclient.py`
OpenAI API客户端：
- 支持OpenAI官方API调用
- 兼容OpenAI格式的第三方服务
- 提供文本生成、嵌入等功能
- 支持流式响应和批量处理

### `hf.py`
Hugging Face客户端：
- 集成Hugging Face模型库
- 支持本地模型加载和推理
- 提供Transformers pipeline封装
- 支持多种任务类型（文本生成、分类等）

### `generator_model.py`
通用生成模型客户端：
- 提供统一的文本生成接口
- 支持多种后端模型的抽象
- 包含生成参数配置
- 支持批量生成和流式输出

## 主要特性

- **统一接口**: 为不同AI服务提供一致的调用方式
- **配置灵活**: 支持详细的参数配置和调优
- **错误处理**: 完善的异常处理和重试机制
- **性能优化**: 支持批量处理和异步调用

## 使用场景

- **文本生成**: 大语言模型文本生成任务
- **嵌入计算**: 文本向量化处理
- **模型推理**: 各种NLP任务的模型推理
- **API集成**: 与外部AI服务的集成

## 快速开始

```python
# OpenAI客户端
from sage.utils.clients.openaiclient import OpenAIClient

client = OpenAIClient(api_key="your-api-key")
response = client.generate("Hello, world!")

# Hugging Face客户端
from sage.utils.clients.hf import HuggingFaceClient

hf_client = HuggingFaceClient(model_name="gpt2")
result = hf_client.generate("Once upon a time")

# 通用生成模型
from sage.utils.clients.generator_model import GeneratorModel

model = GeneratorModel(backend="openai")
output = model.generate("Explain quantum computing")
```

## 配置说明

客户端支持多种配置方式：
- 环境变量配置
- 配置文件加载
- 运行时参数传递
- 默认配置覆盖

## 扩展开发

可以通过继承基类来添加新的客户端：
1. 实现标准接口方法
2. 添加特定服务的参数配置
3. 处理服务特有的响应格式
4. 添加相应的错误处理逻辑

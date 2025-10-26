# 生成组件 (Generation Components)

本文档详细介绍SAGE框架中生成组件（LLM Generator）的使用方法。生成组件是RAG系统的核心输出模块，负责基于检索到的上下文生成最终答案。

## 组件概述

### 核心功能

生成组件在RAG系统中承担以下关键职责：

- **多模型支持**：兼容OpenAI API、VLLM、DashScope等多种LLM服务
- **上下文融合**：将用户查询与检索上下文有效结合
- **生成质量控制**：支持温度、种子等参数精确控制
- **性能监控**：提供生成记录的追踪和分析功能

### 设计架构

生成组件采用统一的接口设计，支持多种后端实现：

```python
# 统一输入格式
input_data = [user_query, prompt]  # 或 [prompt]

# 统一输出格式
output = (user_query, generated_text)
```

## OpenAIGenerator

### 组件描述

`OpenAIGenerator`是兼容OpenAI API标准的生成器，支持调用OpenAI、VLLM、DashScope等符合OpenAI API规范的LLM服务。

### 技术规格

**支持的服务端点**：

- OpenAI GPT系列模型
- VLLM本地部署服务
- 阿里云DashScope服务
- 其他OpenAI API兼容服务

**配置参数**：

| 参数名           | 类型  | 默认值   | 说明                      |
| ---------------- | ----- | -------- | ------------------------- |
| `method`         | str   | "openai" | 服务类型标识              |
| `model_name`     | str   | -        | 模型名称（如gpt-4o-mini） |
| `base_url`       | str   | -        | API服务地址               |
| `api_key`        | str   | -        | API访问密钥               |
| `seed`           | int   | None     | 随机种子（可选）          |
| `temperature`    | float | 0.7      | 生成温度参数              |
| `max_tokens`     | int   | None     | 最大生成长度              |
| `enable_profile` | bool  | False    | 是否启用生成记录保存      |

### 实现示例

#### 基础配置与使用

```python
from sage.libs.rag.generator import OpenAIGenerator

# VLLM本地服务配置
config = {
    "method": "openai",
    "model_name": "gpt-4o-mini",
    "base_url": "http://localhost:8000/v1",
    "api_key": "your-api-key",
    "seed": 42,
    "temperature": 0.7,
}

# 初始化生成器
generator = OpenAIGenerator(config)

# 执行生成
user_query = "什么是RAG技术？"
prompt = "基于以下上下文回答问题：[检索到的上下文内容]"

user_query, generated_text = generator.execute([user_query, prompt])
print(f"用户问题: {user_query}")
print(f"生成答案: {generated_text}")
```

#### 启用性能分析

```python
# 启用生成记录保存
config["enable_profile"] = True
generator = OpenAIGenerator(config)

# 生成记录将自动保存到本地文件
result = generator.execute([user_query, prompt])
# 记录包含：输入文本、输出文本、时间戳、模型参数等
```

## HFGenerator

### 组件描述

`HFGenerator`专门用于调用HuggingFace生态的本地模型，适合无外网依赖或需要完全本地部署的场景。

### 技术规格

**适用模型**：

- HuggingFace Transformers模型
- 本地微调模型
- 量化模型（GPTQ、AWQ等）

**配置参数**：

| 参数名           | 类型  | 默认值 | 说明                           |
| ---------------- | ----- | ------ | ------------------------------ |
| `model_name`     | str   | -      | HuggingFace模型名称或本地路径  |
| `device`         | str   | "auto" | 运行设备（cuda/cpu/auto）      |
| `torch_dtype`    | str   | "auto" | 数据类型（float16/bfloat16等） |
| `load_in_4bit`   | bool  | False  | 是否启用4bit量化               |
| `temperature`    | float | 0.7    | 生成温度                       |
| `max_new_tokens` | int   | 512    | 最大新生成token数              |

### 实现示例

#### 本地模型部署

```python
from sage.libs.rag.generator import HFGenerator

# 本地模型配置
config = {
    "model_name": "microsoft/DialoGPT-medium",
    "device": "cuda",
    "temperature": 0.8,
    "max_new_tokens": 256,
}

# 初始化生成器
generator = HFGenerator(config)

# 执行生成
user_query, generated_text = generator.execute([user_query, prompt])
```

## 最佳实践

### 模型选择建议

1. **生产环境**：

   - 推荐使用OpenAIGenerator + VLLM部署
   - 支持高并发，性能稳定

1. **开发测试**：

   - 可使用OpenAI API进行快速验证
   - HFGenerator适合离线开发

1. **私有部署**：

   - HFGenerator + 本地模型
   - 完全控制数据安全

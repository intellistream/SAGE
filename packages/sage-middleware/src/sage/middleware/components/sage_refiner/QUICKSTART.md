# Refiner 快速开始

## 快速使用

### 1. 在 SAGE 管道中使用

```python
from sage.kernel.api.local_environment import LocalEnvironment
from sage.libs.rag.retriever import Wiki18FAISSRetriever
from sage.libs.rag.refiner import RefinerOperator
from sage.libs.rag.generator import OpenAIGenerator

env = LocalEnvironment()

# 配置 Refiner
refiner_config = {
    "algorithm": "simple",  # 简单算法，快速
    "budget": 2048,         # token 预算
}

# 构建管道
env.from_batch(...) \
   .map(Wiki18FAISSRetriever, retriever_config) \
   .map(RefinerOperator, refiner_config) \
   .map(OpenAIGenerator, generator_config) \
   .submit()
```

### 2. 直接使用服务

```python
from sage.middleware.components.sage_refiner import RefinerService

# 创建服务
config = {
    "algorithm": "simple",
    "budget": 2048,
    "enable_cache": True,
}
service = RefinerService(config)

# 压缩文档
result = service.refine(
    query="What is machine learning?",
    documents=[
        {"text": "Machine learning is..."},
        {"text": "Deep learning is..."},
    ]
)

print(f"压缩率: {result.metrics.compression_rate:.2f}x")
print(f"压缩后内容: {result.refined_content}")
```

## 算法选择

### Simple（推荐入门）
- **速度**: 极快 (<0.1s)
- **无依赖**: 不需要模型
- **压缩率**: 2-3x
- **适用**: 快速原型、实时场景

```python
config = {
    "algorithm": "simple",
    "budget": 2048,
}
```

### LongRefiner（高质量）
- **速度**: 较慢 (需要加载模型)
- **依赖**: Qwen 模型 + LoRA 模块
- **压缩率**: 3-5x
- **适用**: 离线处理、高质量需求

```python
config = {
    "algorithm": "long_refiner",
    "budget": 4096,
    "base_model_path": "Qwen/Qwen2.5-3B-Instruct",
    "query_analysis_module_lora_path": "/path/to/lora/query",
    "doc_structuring_module_lora_path": "/path/to/lora/doc",
    "global_selection_module_lora_path": "/path/to/lora/global",
    "score_model_path": "BAAI/bge-reranker-v2-m3",
}
```

## 常用配置

```python
config = {
    # 基础配置
    "algorithm": "simple",           # 算法选择
    "budget": 2048,                  # token 预算

    # 性能优化
    "enable_cache": True,            # 启用缓存
    "cache_size": 100,               # 缓存大小
    "cache_ttl": 3600,               # 缓存过期时间(秒)

    # 调试
    "enable_metrics": True,          # 启用性能指标
    "enable_profile": False,         # 启用数据记录
}
```

## 示例

完整示例见:
- `examples/basic_usage.py` - 基础用法
- `examples/rag_integration.py` - RAG 集成
- `examples/context_service_demo.py` - Context Service

## 更多信息

详见 [README.md](./README.md)

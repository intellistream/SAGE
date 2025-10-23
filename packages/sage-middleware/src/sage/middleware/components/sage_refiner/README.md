# SAGE Refiner - 上下文压缩组件

提供统一的上下文压缩接口，支持多种SOTA压缩算法，可作为全局Context Service的基础组件。

> **架构说明**: 核心算法实现已从 `sage-libs` 迁移到 `sage-middleware`。应用开发者可以继续使用 `sage-libs` 中的适配器，算法开发者在此添加新算法。详见 [ARCHITECTURE.md](./ARCHITECTURE.md)

## 功能特性

- 🔧 **统一接口**: 提供BaseRefiner抽象基类，支持可插拔的压缩算法
- 🚀 **多种算法**: 集成LongRefiner等SOTA方法，预留ECoRAG、xRAG等扩展接口
- ⚡ **高性能**: 支持批处理、流式处理、GPU加速
- 💾 **智能缓存**: LRU缓存机制，减少重复计算
- 📊 **性能监控**: 完整的指标追踪（压缩率、延迟、token数等）
- 🎛️ **配置驱动**: YAML/Dict配置，支持动态切换算法

## 快速开始

### 基础使用

```python
from sage.middleware.components.sage_refiner import RefinerService, RefinerConfig

# 1. 创建配置
config = RefinerConfig(
    algorithm="long_refiner",
    budget=2048,
    enable_cache=True
)

# 2. 创建服务
service = RefinerService(config)

# 3. 压缩上下文
result = service.refine(
    query="什么是人工智能？",
    documents=[
        "人工智能是计算机科学的一个分支...",
        "机器学习是人工智能的子领域...",
        "深度学习使用神经网络..."
    ]
)

print(f"压缩率: {result.metrics.compression_rate:.2f}x")
print(f"压缩后内容: {result.refined_content}")
```

### 与SAGE管道集成

```python
from sage.core.api.local_environment import LocalEnvironment
from sage.middleware.components.sage_refiner import RefinerAdapter

def rag_pipeline_with_refiner():
    config = {
        "retriever": {...},
        "refiner": {
            "algorithm": "long_refiner",
            "budget": 4000,
            "base_model_path": "Qwen/Qwen2.5-3B-Instruct",
            # ... LongRefiner配置
        },
        "generator": {...}
    }

    env = LocalEnvironment()
    (
        env.from_batch(...)
        .map(ChromaRetriever, config["retriever"])
        .map(RefinerAdapter, config["refiner"])  # 添加压缩
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"])
        .sink(...)
    )
    env.submit()
```

### 全局Context Service

```python
from sage.middleware.components.sage_refiner import ContextService

# 在应用中启用全局context service
app_config = {
    "enable_context_service": True,  # 一个flag即可开关
    "context_service": {
        "refiner": {
            "algorithm": "long_refiner",
            "budget": 2048,
            "enable_cache": True
        },
        "max_context_length": 8192,
        "auto_compress": True
    }
}

# 服务会自动管理全流程的上下文
service = ContextService.from_config(app_config["context_service"])

# 自动压缩和管理
context = service.manage_context(
    query="用户问题",
    history=[...],
    retrieved_docs=[...]
)
```

## 支持的算法

### 1. LongRefiner (SOTA)

基于三阶段的智能压缩：
- **查询分析**: 理解用户意图和关键信息需求
- **文档结构化**: 提取文档关键信息
- **全局选择**: 基于预算智能选择最相关内容

```python
config = RefinerConfig(
    algorithm="long_refiner",
    budget=2048,
    base_model_path="Qwen/Qwen2.5-3B-Instruct",
    query_analysis_module_lora_path="/path/to/lora/query",
    doc_structuring_module_lora_path="/path/to/lora/doc",
    global_selection_module_lora_path="/path/to/lora/global",
    score_model_path="BAAI/bge-reranker-v2-m3",
)
```

### 2. SimpleRefiner

轻量级压缩，不依赖模型：
- 基于相关性排序
- 头尾截断策略
- 快速处理

```python
config = RefinerConfig(
    algorithm="simple",
    budget=2048
)
```

### 3. 扩展算法（规划中）

- **ECoRAG**: 经济高效的RAG压缩
- **xRAG**: 极限压缩算法
- **自定义算法**: 继承BaseRefiner实现

## 核心组件

### BaseRefiner

所有压缩算法的抽象基类：

```python
from sage.middleware.components.sage_refiner import BaseRefiner

class MyRefiner(BaseRefiner):
    def initialize(self):
        # 初始化模型等资源
        pass

    def refine(self, query, documents, budget=None, **kwargs):
        # 实现压缩逻辑
        return RefineResult(...)

    def refine_batch(self, queries, documents_list, budget=None, **kwargs):
        # 批量处理
        return [...]
```

### RefinerConfig

统一的配置管理：

```python
config = RefinerConfig(
    # 基础配置
    algorithm="long_refiner",
    budget=2048,
    compression_ratio=0.2,  # 或使用压缩比

    # 缓存配置
    enable_cache=True,
    cache_size=1000,
    cache_ttl=3600,

    # 性能配置
    gpu_device=0,
    max_model_len=25000,
    batch_size=4,

    # 监控配置
    enable_metrics=True,
    enable_profiling=False
)
```

### RefinerService

服务层，提供缓存、监控等高级功能：

```python
service = RefinerService(config)

# 使用缓存
result = service.refine(query, docs, use_cache=True)

# 获取统计
stats = service.get_stats()
print(f"缓存命中率: {stats['cache_hit_rate']:.2%}")

# 动态切换算法
service.switch_algorithm("simple")

# 清空缓存
service.clear_cache()
```

## 性能指标

RefinerMetrics 提供完整的性能追踪：

```python
result = service.refine(query, documents)

print(f"精炼耗时: {result.metrics.refine_time:.2f}s")
print(f"原始tokens: {result.metrics.original_tokens}")
print(f"精炼后tokens: {result.metrics.refined_tokens}")
print(f"压缩率: {result.metrics.compression_rate:.2f}x")
print(f"相关性得分: {result.metrics.relevance_score}")
```

## 配置文件示例

### YAML配置

```yaml
# config/refiner.yaml
refiner:
  algorithm: long_refiner
  budget: 4000
  enable_cache: true
  cache_size: 1000

  # LongRefiner配置
  base_model_path: "Qwen/Qwen2.5-3B-Instruct"
  query_analysis_module_lora_path: "/models/lora/query_analysis"
  doc_structuring_module_lora_path: "/models/lora/doc_structuring"
  global_selection_module_lora_path: "/models/lora/global_selection"
  score_model_name: "bge-reranker-v2-m3"
  score_model_path: "BAAI/bge-reranker-v2-m3"
  max_model_len: 25000
  gpu_device: 0

  # 性能配置
  enable_metrics: true
  metrics_output_path: "./outputs/refiner_metrics.json"
```

加载配置：

```python
config = RefinerConfig.from_yaml("config/refiner.yaml")
service = RefinerService(config)
```

## 最佳实践

### 1. 选择合适的算法

```python
# 高精度场景 - 使用LongRefiner
config = RefinerConfig(algorithm="long_refiner", budget=4000)

# 低延迟场景 - 使用SimpleRefiner
config = RefinerConfig(algorithm="simple", budget=2048)

# 不压缩 - 调试或对比实验
config = RefinerConfig(algorithm="none")
```

### 2. 启用缓存

```python
config = RefinerConfig(
    enable_cache=True,
    cache_size=2000,      # 根据内存调整
    cache_ttl=7200        # 2小时
)
```

### 3. GPU资源管理

```python
# 指定GPU设备
config = RefinerConfig(
    gpu_device=0,
    score_gpu_device=1,   # 评分模型使用另一块GPU
    gpu_memory_utilization=0.7
)

# 环境变量
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
```

### 4. 批处理优化

```python
# 批量处理多个查询
results = service.refine_batch(
    queries=["问题1", "问题2", "问题3"],
    documents_list=[docs1, docs2, docs3],
    budget=2048
)
```

### 5. 上下文管理器

```python
with RefinerService(config) as service:
    result = service.refine(query, documents)
    # 自动cleanup
```

## 架构设计

```
sage-middleware/components/sage_refiner/
├── __init__.py                 # 公共接口
├── README.md                   # 文档
├── python/                     # Python实现
│   ├── __init__.py
│   ├── base.py                 # BaseRefiner接口
│   ├── config.py               # 配置管理
│   ├── service.py              # RefinerService服务层
│   ├── context_service.py      # 全局Context Service
│   ├── adapter.py              # SAGE Function适配器
│   ├── algorithms/             # 压缩算法
│   │   ├── __init__.py
│   │   ├── long_refiner.py     # LongRefiner实现
│   │   ├── simple.py           # 简单压缩
│   │   ├── ecorag.py           # (待实现)
│   │   └── xrag.py             # (待实现)
│   └── utils/                  # 工具函数
│       ├── __init__.py
│       ├── metrics.py          # 指标计算
│       └── cache.py            # 缓存实现
├── examples/                   # 示例代码
│   ├── basic_usage.py
│   ├── rag_integration.py
│   └── context_service.py
└── tests/                      # 测试
    ├── test_base.py
    ├── test_service.py
    └── test_algorithms.py
```

## API参考

详细API文档请参考各模块的docstring。

## 性能对比

| 算法 | 压缩率 | 延迟 | GPU内存 | 质量 |
|------|--------|------|---------|------|
| LongRefiner | 3-5x | ~2s | 4GB | ⭐⭐⭐⭐⭐ |
| SimpleRefiner | 2-3x | <0.1s | 0 | ⭐⭐⭐ |
| ECoRAG | 4-6x | ~1.5s | 3GB | ⭐⭐⭐⭐ |

## 贡献指南

欢迎贡献新的压缩算法！

1. 继承 `BaseRefiner`
2. 实现 `initialize()` 和 `refine()` 方法
3. 在 `RefinerAlgorithm` 枚举中添加新算法
4. 更新 `RefinerService._get_refiner()` 创建逻辑
5. 添加测试和文档

## 许可证

与SAGE项目保持一致。

## 联系方式

- 项目: https://github.com/intellistream/SAGE
- 问题: https://github.com/intellistream/SAGE/issues

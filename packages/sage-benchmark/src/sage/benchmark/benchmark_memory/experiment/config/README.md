# 配置文件说明

## 目录结构

```
config/
├── README.md              # 本文档
├── template_full.yaml     # 完整配置模板（包含所有选项）
└── [your_config].yaml     # 用户自定义配置
```

## 快速开始

1. **复制配置模板**

```bash
cp template_full.yaml my_experiment.yaml
```

2. **编辑配置文件**，根据实验需求修改参数

3. **加载配置**

```python
from sage.benchmark.benchmark_memory.experiment.utils.config_loader import RuntimeConfig

config = RuntimeConfig("config/my_experiment.yaml")
```

## 配置结构

配置文件分为三大部分：

### 1. runtime - 运行时参数

```yaml
runtime:
  verbose: true                    # 是否输出详细日志
  log_level: INFO                  # 日志级别
  timeout: 300                     # 操作超时（秒）
  max_retries: 3                   # 最大重试次数
  batch_size: 32                   # 批处理大小
  cache_dir: ".sage/cache"         # 缓存目录
```

### 2. services - 外部服务配置

```yaml
services:
  llm:
    api_type: openai               # API类型
    model: gpt-4o-mini             # 模型名称
    temperature: 0.7
    max_tokens: 4096
    
  embedding:
    type: openai                   # 或 local
    model: text-embedding-3-small
    dimension: 1536
    
  vector_store:
    type: milvus
    host: localhost
    port: 19530
```

### 3. operators - 算子配置

四个核心算子，每个算子通过 `action` 字段选择处理类型：

| 算子 | 说明 | 支持的 action |
|------|------|---------------|
| `pre_insert` | 记忆写入前预处理 | segment, extract, summarize, keyword, persona, importance |
| `post_insert` | 记忆写入后处理 | reflection, reconcile, none |
| `pre_retrieval` | 记忆检索前预处理 | rewrite, decompose, route, validate, optimize |
| `post_retrieval` | 记忆检索后处理 | rerank, filter, merge, augment, compress, format |

## 配置校验

配置文件加载时会自动校验必需字段。如果缺少必需配置，会在程序启动时立即报错（Fail-Fast 原则）。

### 错误示例

```
ConfigurationError: 缺少必需配置: operators.pre_insert.prompts.topic_segment (action=segment)
```

### 解决方法

1. 检查 `template_full.yaml` 中对应字段的完整配置
2. 将缺失的配置添加到你的配置文件中

## 配置访问

使用点号路径访问嵌套配置：

```python
# 获取配置（缺失时返回 None）
action = config.get("operators.pre_insert.action")

# 获取配置（缺失时返回默认值）
temperature = config.get("services.llm.temperature", 0.7)

# 必需配置（缺失时抛出异常）
from sage.benchmark.benchmark_memory.experiment.utils.config_validator import require_config
model = require_config(config, "services.llm.model", "LLM服务")
```

## 各算子详细配置

### pre_insert (记忆写入前预处理)

| action | 必需配置 |
|--------|----------|
| `segment` | `prompts.topic_segment` |
| `extract` | `prompts.fact_extract` |
| `summarize` | `prompts.summarize` |
| `keyword` | `prompts.keyword_extract` |
| `persona` | `prompts.persona_extract` |
| `importance` | `prompts.importance_score` |

### post_insert (记忆写入后处理)

| action | 必需配置 |
|--------|----------|
| `reflection` | `prompts.reflection`, `prompts.self_reflection`, `reflection_count`, `reflection_threshold` |
| `reconcile` | (暂无必需配置) |

### pre_retrieval (记忆检索前预处理)

| action | 必需配置 |
|--------|----------|
| `rewrite` | `prompts.rewrite` |
| `decompose` | `prompts.decompose`, `max_sub_queries` |
| `route` | `prompts.route`, `route_options` |
| `validate` | `prompts.validate` |
| `optimize` | `optimize_type`, 以及子类型相关配置 |

### post_retrieval (记忆检索后处理)

| action | 必需配置 |
|--------|----------|
| `rerank` | `rerank_type`, 以及子类型相关配置 |
| `filter` | `filter_type`, 以及子类型相关配置 |
| `merge` | `merge_type` |
| `augment` | `augment_type` |
| `compress` | `compress_type`, `compress_ratio` |
| `format` | `format_type`, 以及子类型相关配置 |

## 迁移指南

如果你有旧版本的配置文件，请参考 `template_full.yaml` 更新以下内容：

1. **所有 Prompt 模板** 现在在 `prompts` 子节点下，需要显式配置
2. **action 类型** 现在是必需配置，不再有默认值
3. **子类型相关参数** 需要根据选择的 action 类型进行配置

## 常见问题

### Q: 为什么我的程序启动就报错？

A: 这是 Fail-Fast 设计原则。配置文件必须包含所有必需字段。请检查错误信息中提到的配置项。

### Q: 如何知道哪些配置是必需的？

A: 
1. 查看本文档的"各算子详细配置"部分
2. 查看 `template_full.yaml` 中的注释
3. 查看 `config_validator.py` 中的 `get_required_fields()` 方法

### Q: 可以使用环境变量吗？

A: 是的，可以在 YAML 中使用 `${ENV_VAR}` 语法引用环境变量。

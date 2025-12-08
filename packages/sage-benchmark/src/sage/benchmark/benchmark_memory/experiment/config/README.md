# 配置文件说明

## 可用的 Pipeline 配置

| 配置文件                                 | 对应论文   | 服务类型           | 核心特点                     |
| ---------------------------------------- | ---------- | ------------------ | ---------------------------- |
| `locomo_short_term_memory_pipeline.yaml` | Baseline   | ShortTermMemory    | 滑动窗口 STM                 |
| `locomo_tim_pipeline.yaml`               | TiM        | VectorHashMemory   | 三元组 + LSH + 蒸馏          |
| `locomo_memorybank_pipeline.yaml`        | MemoryBank | HierarchicalMemory | 分层 + Ebbinghaus 遗忘       |
| `locomo_memgpt_pipeline.yaml`            | MemGPT     | HierarchicalMemory | 功能分层 + Replace           |
| `locomo_amem_pipeline.yaml`              | A-Mem      | GraphMemory        | 链接图 + Link Evolution      |
| `locomo_hipporag_pipeline.yaml`          | HippoRAG   | GraphMemory        | 知识图谱 + PPR               |
| `locomo_memoryos_pipeline.yaml`          | MemoryOS   | HierarchicalMemory | 三层 + Heat Score            |
| `locomo_ldagent_pipeline.yaml`           | LD-Agent   | HierarchicalMemory | STM+LTM + 话题重叠           |
| `locomo_scm_pipeline.yaml`               | SCM        | NeuroMemVDB        | Memory Stream + Token Budget |
| `locomo_mem0_pipeline.yaml`              | Mem0       | HybridMemory       | 事实库 + ADD/UPDATE/DELETE   |

## 目录结构

```
config/
├── README.md                              # 本文档
├── template_full.yaml                     # 完整配置模板（包含所有选项）
├── locomo_short_term_memory_pipeline.yaml # STM Baseline
├── locomo_tim_pipeline.yaml               # TiM
├── locomo_memorybank_pipeline.yaml        # MemoryBank
├── locomo_memgpt_pipeline.yaml            # MemGPT
├── locomo_amem_pipeline.yaml              # A-Mem
├── locomo_hipporag_pipeline.yaml          # HippoRAG
├── locomo_memoryos_pipeline.yaml          # MemoryOS
├── locomo_ldagent_pipeline.yaml           # LD-Agent
├── locomo_scm_pipeline.yaml               # SCM
├── locomo_mem0_pipeline.yaml              # Mem0
└── [your_config].yaml                     # 用户自定义配置
```

## 快速开始

### 运行 Pipeline

```bash
cd /home/zrc/develop_item/SAGE

# STM Baseline
python packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_test_pipeline.py \
  --config packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/locomo_short_term_memory_pipeline.yaml \
  --task_id conv-26

# TiM
python packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_test_pipeline.py \
  --config packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/locomo_tim_pipeline.yaml \
  --task_id conv-26

# MemoryBank
python packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/memory_test_pipeline.py \
  --config packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/config/locomo_memorybank_pipeline.yaml \
  --task_id conv-26

# 其他配置类似，替换配置文件名即可
```

### 创建自定义配置

1. **复制配置模板**

```bash
cp template_full.yaml my_experiment.yaml
```

2. **编辑配置文件**，根据实验需求修改参数

1. **加载配置**

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

| 算子             | 说明             | 支持的 action                                             |
| ---------------- | ---------------- | --------------------------------------------------------- |
| `pre_insert`     | 记忆写入前预处理 | segment, extract, summarize, keyword, persona, importance |
| `post_insert`    | 记忆写入后处理   | reflection, reconcile, none                               |
| `pre_retrieval`  | 记忆检索前预处理 | rewrite, decompose, route, validate, optimize             |
| `post_retrieval` | 记忆检索后处理   | rerank, filter, merge, augment, compress, format          |

## 配置校验

配置文件加载时会自动校验必需字段。如果缺少必需配置，会在程序启动时立即报错（Fail-Fast 原则）。

### 错误示例

```
ConfigurationError: 缺少必需配置: operators.pre_insert.prompts.topic_segment (action=segment)
```

### 解决方法

1. 检查 `template_full.yaml` 中对应字段的完整配置
1. 将缺失的配置添加到你的配置文件中

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

| action       | 必需配置                   |
| ------------ | -------------------------- |
| `segment`    | `prompts.topic_segment`    |
| `extract`    | `prompts.fact_extract`     |
| `summarize`  | `prompts.summarize`        |
| `keyword`    | `prompts.keyword_extract`  |
| `persona`    | `prompts.persona_extract`  |
| `importance` | `prompts.importance_score` |

### post_insert (记忆写入后处理)

| action       | 必需配置                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------- |
| `reflection` | `prompts.reflection`, `prompts.self_reflection`, `reflection_count`, `reflection_threshold` |
| `reconcile`  | (暂无必需配置)                                                                              |

### pre_retrieval (记忆检索前预处理)

| action      | 必需配置                               |
| ----------- | -------------------------------------- |
| `rewrite`   | `prompts.rewrite`                      |
| `decompose` | `prompts.decompose`, `max_sub_queries` |
| `route`     | `prompts.route`, `route_options`       |
| `validate`  | `prompts.validate`                     |
| `optimize`  | `optimize_type`, 以及子类型相关配置    |

### post_retrieval (记忆检索后处理)

| action     | 必需配置                          |
| ---------- | --------------------------------- |
| `rerank`   | `rerank_type`, 以及子类型相关配置 |
| `filter`   | `filter_type`, 以及子类型相关配置 |
| `merge`    | `merge_type`                      |
| `augment`  | `augment_type`                    |
| `compress` | `compress_type`, `compress_ratio` |
| `format`   | `format_type`, 以及子类型相关配置 |

## 迁移指南

如果你有旧版本的配置文件，请参考 `template_full.yaml` 更新以下内容：

1. **所有 Prompt 模板** 现在在 `prompts` 子节点下，需要显式配置
1. **action 类型** 现在是必需配置，不再有默认值
1. **子类型相关参数** 需要根据选择的 action 类型进行配置

## 常见问题

### Q: 为什么我的程序启动就报错？

A: 这是 Fail-Fast 设计原则。配置文件必须包含所有必需字段。请检查错误信息中提到的配置项。

### Q: 如何知道哪些配置是必需的？

A:

1. 查看本文档的"各算子详细配置"部分
1. 查看 `template_full.yaml` 中的注释
1. 查看 `config_validator.py` 中的 `get_required_fields()` 方法

### Q: 可以使用环境变量吗？

A: 是的，可以在 YAML 中使用 `${ENV_VAR}` 语法引用环境变量。

______________________________________________________________________

## Action 兼容性矩阵

### 1. PreInsert ↔ MemoryInsert Adapter 兼容性

| PreInsert.action | 必须配合的 adapter | 说明                   |
| ---------------- | ------------------ | ---------------------- |
| `none`           | `to_dialogs`       | 保持原始对话格式       |
| `tri_embed`      | `to_refactor`      | 输出三元组 + embedding |
| `transform`      | `to_refactor`      | 输出处理后文本         |
| `extract`        | `to_refactor`      | 输出带 metadata 的文本 |
| `score`          | `to_refactor`      | 输出带评分的文本       |
| `validate`       | 任意               | 只做校验，不改格式     |

### 2. PostInsert.action ↔ Service 兼容性

| PostInsert.action | 兼容的服务类型                               | 说明         |
| ----------------- | -------------------------------------------- | ------------ |
| `none`            | 全部                                         | 透传         |
| `log` / `stats`   | 全部                                         | 仅日志/统计  |
| `distillation`    | 向量类服务 (VectorHash, NeuroMemVDB, Hybrid) | 需要向量检索 |
| `link_evolution`  | GraphMemory                                  | 需要图结构   |
| `forgetting`      | Hierarchical                                 | 需要分层结构 |
| `summarize`       | Hierarchical                                 | 需要分层结构 |
| `migrate`         | Hierarchical                                 | 需要分层结构 |
| `reflection`      | 实现了 optimize() 的服务                     | 委托服务执行 |

### 3. PreRetrieval.action ↔ Service 兼容性

| PreRetrieval.action | 要求           | 说明                                    |
| ------------------- | -------------- | --------------------------------------- |
| `none`              | 无             | 服务自行处理（如 STM 不需要 embedding） |
| `embedding`         | Embedding 服务 | 生成查询向量                            |
| `multi_embed`       | Embedding 服务 | 多维查询向量                            |
| `optimize`          | LLM 或 spaCy   | 关键词/查询改写                         |
| `decompose`         | LLM            | 复杂查询分解                            |
| `route`             | LLM 或规则     | 生成检索策略 hints                      |
| `validate`          | 无             | 查询校验                                |

### 4. PostRetrieval.action 兼容性

| PostRetrieval.action | 依赖                | 说明                         |
| -------------------- | ------------------- | ---------------------------- |
| `none`               | 无                  | 基础格式化                   |
| `rerank`             | 视 rerank_type 而定 | PPR 需要 Graph 服务          |
| `filter`             | 无                  | top_k/threshold/token_budget |
| `merge`              | 服务支持多次检索    | link_expand 需要 Graph       |
| `augment`            | 服务支持额外查询    | 添加 persona 等              |
| `compress`           | LLM                 | 压缩内容                     |
| `format`             | 无                  | 自定义格式化                 |

______________________________________________________________________

## 常见兼容组合

### 组合 1: 纯 STM（最简单）

```yaml
services:
  register_memory_service: "short_term_memory"
  memory_insert_adapter: "to_dialogs"
operators:
  pre_insert: { action: "none" }
  post_insert: { action: "none" }
  pre_retrieval: { action: "none" }
  post_retrieval: { action: "none" }
```

### 组合 2: 向量检索 + 蒸馏

```yaml
services:
  register_memory_service: "vector_hash_memory"
  memory_insert_adapter: "to_refactor"
operators:
  pre_insert: { action: "tri_embed" }
  post_insert: { action: "distillation" }
  pre_retrieval: { action: "embedding" }
  post_retrieval: { action: "none" }
```

### 组合 3: 分层 + 遗忘

```yaml
services:
  register_memory_service: "hierarchical_memory"
  memory_insert_adapter: "to_refactor"
operators:
  pre_insert: { action: "transform", transform_type: "summarize" }
  post_insert: { action: "forgetting" }
  pre_retrieval: { action: "embedding" }
  post_retrieval: { action: "rerank", rerank_type: "time_weighted" }
```

### 组合 4: 图记忆 + 链接演化

```yaml
services:
  register_memory_service: "graph_memory"
  memory_insert_adapter: "to_refactor"
operators:
  pre_insert: { action: "tri_embed" }
  post_insert: { action: "link_evolution" }
  pre_retrieval: { action: "embedding" }
  post_retrieval: { action: "merge", merge_type: "link_expand" }
```

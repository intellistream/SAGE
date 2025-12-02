# 配置剥离重构任务书

## 📌 任务概述

**目标**: 将 Pipeline 各算子中硬编码的 prompt 模板和默认参数全部剥离到 YAML 配置文件中，实现\*\*"一切皆配置"\*\*的设计原则。

**核心原则**:

1. **无默认值**: 所有必需参数必须在 YAML 中显式声明，缺失则直接报错
1. **配置即文档**: YAML 配置文件本身成为功能说明文档
1. **快速失败**: 程序启动时检测配置完整性，缺少必需配置立即报错退出

**涉及文件**:

- `libs/pre_insert.py` (1264行) - 7 个硬编码 Prompt + 多处默认值
- `libs/post_insert.py` (1655行) - 8 个硬编码 Prompt + 多处默认值
- `libs/pre_retrieval.py` (910行) - 4 个硬编码 Prompt + 多处默认值
- `libs/post_retrieval.py` (1402行) - 多处默认值

______________________________________________________________________

## 🔴 问题清单

### 1. pre_insert.py 硬编码清单

#### 1.1 Prompt 模板 (行 35-100)

| 变量名                    | 行号   | 对应 action               | 需迁移至配置键                                  |
| ------------------------- | ------ | ------------------------- | ----------------------------------------------- |
| `TOPIC_SEGMENT_PROMPT`    | 35-46  | `transform.topic_segment` | `operators.pre_insert.prompts.topic_segment`    |
| `FACT_EXTRACT_PROMPT`     | 48-58  | `transform.fact_extract`  | `operators.pre_insert.prompts.fact_extract`     |
| `SUMMARIZE_PROMPT`        | 60-68  | `transform.summarize`     | `operators.pre_insert.prompts.summarize`        |
| `KEYWORD_EXTRACT_PROMPT`  | 71-80  | `extract.keyword`         | `operators.pre_insert.prompts.keyword_extract`  |
| `PERSONA_EXTRACT_PROMPT`  | 82-96  | `extract.persona`         | `operators.pre_insert.prompts.persona_extract`  |
| `IMPORTANCE_SCORE_PROMPT` | 99-109 | `score.importance`        | `operators.pre_insert.prompts.importance_score` |

#### 1.2 默认参数值

| 参数             | 当前默认值         | 行号  | 配置键                                |
| ---------------- | ------------------ | ----- | ------------------------------------- |
| `action`         | `"none"`           | 127   | `operators.pre_insert.action`         |
| `transform_type` | `"chunking"`       | 279   | `operators.pre_insert.transform_type` |
| `chunk_size`     | `512`              | 301   | `operators.pre_insert.chunk_size`     |
| `chunk_overlap`  | `50`               | 302   | `operators.pre_insert.chunk_overlap`  |
| `chunk_strategy` | `"fixed"`          | 303   | `operators.pre_insert.chunk_strategy` |
| `extract_type`   | `"keyword"`        | 约170 | `operators.pre_insert.extract_type`   |
| `max_keywords`   | `10`               | 约175 | `operators.pre_insert.max_keywords`   |
| `spacy_model`    | `"en_core_web_sm"` | 211   | `operators.pre_insert.spacy_model`    |

______________________________________________________________________

### 2. post_insert.py 硬编码清单

#### 2.1 Prompt 模板 (行 35-95)

| 变量名                                 | 行号  | 对应 action                | 需迁移至配置键                                        |
| -------------------------------------- | ----- | -------------------------- | ----------------------------------------------------- |
| `DEFAULT_REFLECTION_PROMPT`            | 35-42 | `reflection`               | `operators.post_insert.prompts.reflection`            |
| `DEFAULT_SELF_REFLECTION_PROMPT`       | 44-51 | `reflection.self`          | `operators.post_insert.prompts.self_reflection`       |
| `DEFAULT_OTHER_REFLECTION_PROMPT`      | 53-60 | `reflection.other`         | `operators.post_insert.prompts.other_reflection`      |
| `DEFAULT_AUTO_LINK_PROMPT`             | 62-71 | `link_evolution.auto_link` | `operators.post_insert.prompts.auto_link`             |
| `DEFAULT_SUMMARIZE_PROMPT`             | 73-79 | `summarize.single`         | `operators.post_insert.prompts.summarize`             |
| `DEFAULT_INCREMENTAL_SUMMARIZE_PROMPT` | 81-89 | `summarize.incremental`    | `operators.post_insert.prompts.incremental_summarize` |
| `DEFAULT_HIERARCHICAL_PROMPTS`         | 91-95 | `summarize.hierarchical`   | `operators.post_insert.prompts.hierarchical`          |

#### 2.2 默认参数值

| 参数                       | 当前默认值                  | 行号    | 配置键                                         |
| -------------------------- | --------------------------- | ------- | ---------------------------------------------- |
| `action`                   | `"none"`                    | 125     | `operators.post_insert.action`                 |
| `trigger_mode`             | `"threshold"`               | 211     | `operators.post_insert.trigger_mode`           |
| `importance_threshold`     | `100.0`                     | 215     | `operators.post_insert.importance_threshold`   |
| `importance_field`         | `"importance_score"`        | 218     | `operators.post_insert.importance_field`       |
| `interval_minutes`         | `60`                        | 225     | `operators.post_insert.interval_minutes`       |
| `memory_count`             | `50`                        | 228     | `operators.post_insert.memory_count`           |
| `reflection_depth`         | `1`                         | 236     | `operators.post_insert.reflection_depth`       |
| `max_reflections`          | `5`                         | 237     | `operators.post_insert.max_reflections`        |
| `reflection_type`          | `"general"`                 | 240     | `operators.post_insert.reflection_type`        |
| `reflection_importance`    | `8`                         | 252     | `operators.post_insert.reflection_importance`  |
| `link_policy`              | `"synonym_edge"`            | 259     | `operators.post_insert.link_policy`            |
| `knn_k`                    | `10`                        | 262     | `operators.post_insert.knn_k`                  |
| `similarity_threshold`     | `0.7`                       | 265     | `operators.post_insert.similarity_threshold`   |
| `edge_weight`              | `1.0`                       | 268     | `operators.post_insert.edge_weight`            |
| `strengthen_factor`        | `0.1`                       | 271     | `operators.post_insert.strengthen_factor`      |
| `decay_factor`             | `0.01`                      | 272     | `operators.post_insert.decay_factor`           |
| `max_weight`               | `10.0`                      | 273     | `operators.post_insert.max_weight`             |
| `activation_depth`         | `2`                         | 276     | `operators.post_insert.activation_depth`       |
| `activation_decay`         | `0.5`                       | 277     | `operators.post_insert.activation_decay`       |
| `max_auto_links`           | `5`                         | 283     | `operators.post_insert.max_auto_links`         |
| `decay_type`               | `"ebbinghaus"`              | 289     | `operators.post_insert.decay_type`             |
| `decay_rate`               | `0.1`                       | 292     | `operators.post_insert.decay_rate`             |
| `decay_floor`              | `0.1`                       | 293     | `operators.post_insert.decay_floor`            |
| `max_memories`             | `1000`                      | 296     | `operators.post_insert.max_memories`           |
| `evict_count`              | `100`                       | 297     | `operators.post_insert.evict_count`            |
| `heat_threshold` (lfu)     | `0.3`                       | 300     | `operators.post_insert.heat_threshold`         |
| `heat_decay`               | `0.1`                       | 301     | `operators.post_insert.heat_decay`             |
| `initial_strength`         | `1.0`                       | 304     | `operators.post_insert.initial_strength`       |
| `forgetting_curve`         | `"exponential"`             | 306     | `operators.post_insert.forgetting_curve`       |
| `review_boost`             | `0.5`                       | 309     | `operators.post_insert.review_boost`           |
| `factors` (hybrid)         | 见代码                      | 312-318 | `operators.post_insert.factors`                |
| `retention_min`            | `50`                        | 322     | `operators.post_insert.retention_min`          |
| `archive_before_delete`    | `True`                      | 324     | `operators.post_insert.archive_before_delete`  |
| `trigger_condition`        | `"overflow"`                | 329     | `operators.post_insert.trigger_condition`      |
| `overflow_threshold`       | `100`                       | 331     | `operators.post_insert.overflow_threshold`     |
| `periodic_interval`        | `3600`                      | 332     | `operators.post_insert.periodic_interval`      |
| `summary_strategy`         | `"hierarchical"`            | 336     | `operators.post_insert.summary_strategy`       |
| `hierarchy_levels`         | 见代码                      | 340-355 | `operators.post_insert.hierarchy_levels`       |
| `replace_originals`        | `False`                     | 365     | `operators.post_insert.replace_originals`      |
| `store_as_new`             | `True`                      | 366     | `operators.post_insert.store_as_new`           |
| `summary_importance`       | `7`                         | 367     | `operators.post_insert.summary_importance`     |
| `migrate_policy`           | `"heat"`                    | 376     | `operators.post_insert.migrate_policy`         |
| `heat_threshold` (migrate) | `0.7`                       | 379     | `operators.post_insert.heat_upgrade_threshold` |
| `cold_threshold`           | `0.3`                       | 381     | `operators.post_insert.cold_threshold`         |
| `session_gap`              | `3600`                      | 384     | `operators.post_insert.session_gap`            |
| `tier_capacities`          | `{"stm": 100, "mtm": 1000}` | 387     | `operators.post_insert.tier_capacities`        |
| `upgrade_transform`        | `"none"`                    | 392     | `operators.post_insert.upgrade_transform`      |
| `downgrade_transform`      | `"summarize"`               | 394     | `operators.post_insert.downgrade_transform`    |
| `log_level`                | `"INFO"`                    | 430     | `operators.post_insert.log_level`              |
| `stats_fields`             | `["count", "avg_len"]`      | 436     | `operators.post_insert.stats_fields`           |

______________________________________________________________________

### 3. pre_retrieval.py 硬编码清单

#### 3.1 Prompt 模板 (分散在各初始化方法中)

| 位置                        | 对应 action            | 需迁移至配置键                                              |
| --------------------------- | ---------------------- | ----------------------------------------------------------- |
| `_init_optimize` 行112-115  | `optimize.expand`      | `operators.pre_retrieval.prompts.expand`                    |
| `_init_optimize` 行119-121  | `optimize.rewrite`     | `operators.pre_retrieval.prompts.rewrite`                   |
| `_init_optimize` 行125-127  | `optimize.instruction` | `operators.pre_retrieval.prompts.instruction_prefix/suffix` |
| `_init_decompose` 行261-268 | `decompose.llm`        | `operators.pre_retrieval.prompts.decompose`                 |
| `_init_route` 行312-320     | `route.llm`            | `operators.pre_retrieval.prompts.route`                     |

#### 3.2 默认参数值

| 参数                       | 当前默认值            | 行号    | 配置键                                        |
| -------------------------- | --------------------- | ------- | --------------------------------------------- |
| `action`                   | `"none"`              | 56      | `operators.pre_retrieval.action`              |
| `optimize_type`            | `"keyword_extract"`   | 86      | `operators.pre_retrieval.optimize_type`       |
| `extractor`                | `"spacy"`             | 91      | `operators.pre_retrieval.extractor`           |
| `extract_types`            | `["NOUN", "PROPN"]`   | 93      | `operators.pre_retrieval.extract_types`       |
| `max_keywords`             | `10`                  | 96      | `operators.pre_retrieval.max_keywords`        |
| `expand_count`             | `3`                   | 106     | `operators.pre_retrieval.expand_count`        |
| `merge_strategy`           | `"union"`             | 108     | `operators.pre_retrieval.merge_strategy`      |
| `instruction_prefix`       | 见代码                | 125-127 | `operators.pre_retrieval.instruction_prefix`  |
| `instruction_suffix`       | `""`                  | 129     | `operators.pre_retrieval.instruction_suffix`  |
| `replace_original`         | `False`               | 134     | `operators.pre_retrieval.replace_original`    |
| `store_optimized`          | `True`                | 137     | `operators.pre_retrieval.store_optimized`     |
| `embeddings` (multi_embed) | 见代码                | 223-225 | `operators.pre_retrieval.embeddings`          |
| `output_format`            | `"dict"`              | 243     | `operators.pre_retrieval.output_format`       |
| `match_insert_config`      | `True`                | 245     | `operators.pre_retrieval.match_insert_config` |
| `decompose_strategy`       | `"llm"`               | 254     | `operators.pre_retrieval.decompose_strategy`  |
| `max_sub_queries`          | `5`                   | 255     | `operators.pre_retrieval.max_sub_queries`     |
| `sub_query_action`         | `"parallel"`          | 257     | `operators.pre_retrieval.sub_query_action`    |
| `split_keywords` (rule)    | 见代码                | 275-277 | `operators.pre_retrieval.split_keywords`      |
| `route_strategy`           | `"keyword"`           | 288     | `operators.pre_retrieval.route_strategy`      |
| `allow_multi_route`        | `True`                | 291     | `operators.pre_retrieval.allow_multi_route`   |
| `max_routes`               | `2`                   | 293     | `operators.pre_retrieval.max_routes`          |
| `default_route`            | `"long_term_memory"`  | 295     | `operators.pre_retrieval.default_route`       |
| `keyword_rules`            | 见代码                | 299-311 | `operators.pre_retrieval.keyword_rules`       |
| `classifier_model`         | `"intent-classifier"` | 316     | `operators.pre_retrieval.classifier_model`    |
| `route_mapping`            | 见代码                | 318-322 | `operators.pre_retrieval.route_mapping`       |
| `validation_rules`         | 见代码                | 333-336 | `operators.pre_retrieval.rules`               |
| `on_fail`                  | `"default"`           | 337     | `operators.pre_retrieval.on_fail`             |
| `default_query`            | `"Hello"`             | 338     | `operators.pre_retrieval.default_query`       |
| `preprocessing`            | 见代码                | 341-345 | `operators.pre_retrieval.preprocessing`       |
| `spacy_model`              | `"en_core_web_sm"`    | 162     | `operators.pre_retrieval.spacy_model`         |

______________________________________________________________________

### 4. post_retrieval.py 硬编码清单

#### 4.1 Prompt 模板

（post_retrieval 中 prompt 相对较少，主要是格式化相关）

| 位置                                   | 用途           | 需迁移至配置键                                        |
| -------------------------------------- | -------------- | ----------------------------------------------------- |
| `conversation_format_prompt` 行109-114 | 对话格式化前缀 | `operators.post_retrieval.conversation_format_prompt` |

#### 4.2 默认参数值

| 参数                    | 当前默认值         | 行号 | 配置键                                           |
| ----------------------- | ------------------ | ---- | ------------------------------------------------ |
| `action`                | `"none"`           | 104  | `operators.post_retrieval.action`                |
| `rerank_type`           | `"weighted"`       | 264  | `operators.post_retrieval.rerank_type`           |
| `batch_size`            | `32`               | 276  | `operators.post_retrieval.batch_size`            |
| `time_decay_rate`       | `0.1`              | 280  | `operators.post_retrieval.time_decay_rate`       |
| `time_field`            | `"timestamp"`      | 283  | `operators.post_retrieval.time_field`            |
| `damping_factor`        | `0.5`              | 288  | `operators.post_retrieval.damping_factor`        |
| `max_iterations`        | `100`              | 292  | `operators.post_retrieval.max_iterations`        |
| `convergence_threshold` | `1e-6`             | 296  | `operators.post_retrieval.convergence_threshold` |
| `personalization_nodes` | `"query_entities"` | 300  | `operators.post_retrieval.personalization_nodes` |
| `factors`               | `[]`               | 306  | `operators.post_retrieval.factors`               |
| `score_field`           | `"rerank_score"`   | 313  | `operators.post_retrieval.score_field`           |

______________________________________________________________________

## 🛠️ 实施方案

### 阶段一：配置模板设计 (0.5天)

创建标准 YAML 配置模板，包含所有必需参数的占位符。

**产出物**: `config/template_full.yaml`

```yaml
# ============================================================
# SAGE Memory Pipeline 完整配置模板
# ============================================================
# 说明：
# - 所有标记为 REQUIRED 的字段必须填写，缺失将导致程序启动失败
# - 所有 prompt 字段支持 {placeholder} 格式的变量替换
# ============================================================

runtime:
  llm_base_url: ""       # REQUIRED: LLM 服务地址
  llm_model: ""          # REQUIRED: LLM 模型名称
  embedding_base_url: "" # REQUIRED: Embedding 服务地址
  embedding_model: ""    # REQUIRED: Embedding 模型名称

services:
  register_memory_service: ""  # REQUIRED: 存储后端名称

# ============================================================
# D2: PreInsert 配置
# ============================================================
operators:
  pre_insert:
    action: ""  # REQUIRED: none | tri_embed | transform | extract | score | multi_embed | validate

    # -------------------- transform action --------------------
    transform:
      type: ""  # chunking | topic_segment | fact_extract | summarize | compress

      # chunking 参数
      chunk_size: null       # REQUIRED when type=chunking
      chunk_overlap: null    # REQUIRED when type=chunking
      chunk_strategy: ""     # fixed | sentence | paragraph

      # topic_segment 参数
      min_segment_size: null
      max_segment_size: null

    # -------------------- extract action --------------------
    extract:
      type: ""  # keyword | entity | noun | persona | all
      max_keywords: null
      entity_types: []

    # -------------------- score action --------------------
    score:
      type: ""  # importance | emotion

    # -------------------- prompts --------------------
    prompts:
      topic_segment: ""      # REQUIRED when transform.type=topic_segment
      fact_extract: ""       # REQUIRED when transform.type=fact_extract
      summarize: ""          # REQUIRED when transform.type=summarize
      keyword_extract: ""    # REQUIRED when extract.type=keyword (with llm)
      persona_extract: ""    # REQUIRED when extract.type=persona
      importance_score: ""   # REQUIRED when score.type=importance
      emotion_score: ""      # REQUIRED when score.type=emotion
      triple_extraction: ""  # REQUIRED when action=tri_embed

  # ============================================================
  # D3: PostInsert 配置
  # ============================================================
  post_insert:
    action: ""  # REQUIRED: none | distillation | log | stats | reflection | link_evolution | forgetting | summarize | migrate

    # -------------------- reflection action --------------------
    reflection:
      trigger_mode: ""       # threshold | periodic | count | manual
      importance_threshold: null
      importance_field: ""
      interval_minutes: null
      memory_count: null
      depth: null
      max_reflections: null
      type: ""               # general | self | other
      store_reflection: null
      reflection_importance: null

    # -------------------- link_evolution action --------------------
    link_evolution:
      policy: ""             # synonym_edge | strengthen | activate | auto_link
      knn_k: null
      similarity_threshold: null
      edge_weight: null
      strengthen_factor: null
      decay_factor: null
      max_weight: null
      activation_depth: null
      activation_decay: null
      max_auto_links: null

    # -------------------- forgetting action --------------------
    forgetting:
      decay_type: ""         # time_decay | lru | lfu | ebbinghaus | hybrid
      decay_rate: null
      decay_floor: null
      max_memories: null
      evict_count: null
      heat_threshold: null
      heat_decay: null
      initial_strength: null
      forgetting_curve: ""
      review_boost: null
      retention_min: null
      archive_before_delete: null
      factors: []            # for hybrid mode

    # -------------------- summarize action --------------------
    summarize:
      trigger_condition: ""  # overflow | periodic | manual
      overflow_threshold: null
      periodic_interval: null
      strategy: ""           # single | hierarchical | incremental
      hierarchy_levels: []
      replace_originals: null
      store_as_new: null
      summary_importance: null

    # -------------------- migrate action --------------------
    migrate:
      policy: ""             # heat | time | overflow | manual
      heat_threshold: null
      cold_threshold: null
      session_gap: null
      tier_capacities: {}
      upgrade_transform: ""
      downgrade_transform: ""

    # -------------------- prompts --------------------
    prompts:
      distillation: ""       # REQUIRED when action=distillation
      reflection: ""         # REQUIRED when action=reflection
      self_reflection: ""    # REQUIRED when reflection.type=self
      other_reflection: ""   # REQUIRED when reflection.type=other
      auto_link: ""          # REQUIRED when link_evolution.policy=auto_link
      summarize: ""          # REQUIRED when action=summarize (single)
      incremental_summarize: ""  # REQUIRED when summarize.strategy=incremental
      hierarchical_daily: ""     # REQUIRED when summarize.strategy=hierarchical
      hierarchical_weekly: ""
      hierarchical_global: ""

  # ============================================================
  # D4: PreRetrieval 配置
  # ============================================================
  pre_retrieval:
    action: ""  # REQUIRED: none | embedding | optimize | multi_embed | decompose | route | validate

    # -------------------- optimize action --------------------
    optimize:
      type: ""               # keyword_extract | expand | rewrite | instruction
      extractor: ""          # spacy | nltk | llm
      extract_types: []
      max_keywords: null
      expand_count: null
      merge_strategy: ""
      replace_original: null
      store_optimized: null
      embed_optimized: null

    # -------------------- multi_embed action --------------------
    multi_embed:
      embeddings: []         # REQUIRED when action=multi_embed
      output_format: ""
      match_insert_config: null

    # -------------------- decompose action --------------------
    decompose:
      strategy: ""           # llm | rule | hybrid
      max_sub_queries: null
      sub_query_action: ""
      merge_strategy: ""
      split_keywords: []     # for rule strategy
      embed_sub_queries: null

    # -------------------- route action --------------------
    route:
      strategy: ""           # keyword | classifier | llm
      allow_multi_route: null
      max_routes: null
      default_route: ""
      keyword_rules: []
      classifier_model: ""
      route_mapping: {}

    # -------------------- validate action --------------------
    validate:
      rules: []              # REQUIRED when action=validate
      on_fail: ""
      default_query: ""
      preprocessing: {}

    # -------------------- prompts --------------------
    prompts:
      keyword_extract: ""    # when optimize.type=keyword_extract with llm
      expand: ""             # REQUIRED when optimize.type=expand
      rewrite: ""            # REQUIRED when optimize.type=rewrite
      instruction_prefix: "" # when optimize.type=instruction
      instruction_suffix: ""
      decompose: ""          # REQUIRED when decompose.strategy=llm
      route: ""              # REQUIRED when route.strategy=llm

  # ============================================================
  # D5: PostRetrieval 配置
  # ============================================================
  post_retrieval:
    action: ""  # REQUIRED: none | rerank | filter | merge | augment | compress | format

    # -------------------- rerank action --------------------
    rerank:
      type: ""               # semantic | time_weighted | ppr | weighted | cross_encoder
      model: ""              # for semantic/cross_encoder
      batch_size: null
      time_decay_rate: null
      time_field: ""
      damping_factor: null   # for ppr
      max_iterations: null
      convergence_threshold: null
      personalization_nodes: ""
      factors: []            # for weighted
      top_k: null
      score_field: ""

    # -------------------- filter action --------------------
    filter:
      type: ""               # token_budget | threshold | top_k | llm | dedup
      token_budget: null
      token_counter: ""
      overflow_strategy: ""
      priority_field: ""
      score_threshold: null
      k: null
      dedup_field: ""
      dedup_threshold: null

    # -------------------- merge action --------------------
    merge:
      strategy: ""           # weighted | rrf | interleave
      weights: []
      rrf_k: null
      dedup: null

    # -------------------- augment action --------------------
    augment:
      types: []              # reflection | context | metadata | temporal
      context_window: null
      metadata_fields: []
      temporal_format: ""

    # -------------------- compress action --------------------
    compress:
      strategy: ""           # llmlingua | extractive | abstractive
      compression_ratio: null
      model: ""
      max_tokens: null
      preserve_order: null

    # -------------------- format action --------------------
    format:
      type: ""               # template | structured | chat | xml
      template: ""
      include_metadata: null
      separator: ""
      xml_root: ""
      chat_format: {}

    # -------------------- prompts --------------------
    prompts:
      conversation_format: ""  # base format prompt
      filter_llm: ""           # when filter.type=llm
      compress_abstractive: "" # when compress.strategy=abstractive
```

______________________________________________________________________

### 阶段二：配置校验器实现 (1天)

创建 `ConfigValidator` 类，在程序启动时验证配置完整性。

**产出物**: `utils/config_validator.py`

```python
class ConfigValidator:
    """配置校验器 - 实现快速失败原则"""

    # 定义每个 action 的必需参数
    REQUIRED_PARAMS = {
        "pre_insert": {
            "tri_embed": ["prompts.triple_extraction"],
            "transform.topic_segment": ["prompts.topic_segment", "transform.min_segment_size"],
            "transform.fact_extract": ["prompts.fact_extract"],
            "transform.summarize": ["prompts.summarize"],
            "transform.chunking": ["transform.chunk_size", "transform.chunk_overlap"],
            "extract.keyword": ["extract.max_keywords"],  # llm 模式额外需要 prompts.keyword_extract
            "extract.persona": ["prompts.persona_extract"],
            "score.importance": ["prompts.importance_score"],
            "score.emotion": ["prompts.emotion_score"],
            # ...
        },
        "post_insert": {
            "distillation": ["prompts.distillation", "distillation_topk"],
            "reflection": ["prompts.reflection", "reflection.trigger_mode"],
            # ...
        },
        # ...
    }

    def validate(self, config: RuntimeConfig) -> None:
        """验证配置完整性，缺失则抛出 ConfigurationError"""
        errors = []

        # 检查各算子配置
        for operator in ["pre_insert", "post_insert", "pre_retrieval", "post_retrieval"]:
            action = config.get(f"operators.{operator}.action")
            if not action:
                errors.append(f"缺少必需配置: operators.{operator}.action")
                continue

            # 检查该 action 的必需参数
            required = self._get_required_params(operator, action, config)
            for param in required:
                value = config.get(f"operators.{operator}.{param}")
                if value is None or value == "":
                    errors.append(f"缺少必需配置: operators.{operator}.{param} (action={action})")

        if errors:
            raise ConfigurationError("\n".join(errors))
```

______________________________________________________________________

### 阶段三：算子代码重构 (3-4天)

#### 3.1 重构原则

1. **删除所有顶层常量**: 移除 `DEFAULT_*_PROMPT` 等常量定义
1. **删除所有默认值**: `config.get("key", default)` → `config.get("key")` + 校验
1. **添加缺失配置报错**: 配置缺失时抛出明确错误，说明需要的配置键
1. **统一配置路径**: 规范化配置键的命名，使用层级结构

#### 3.2 示例重构

**Before** (pre_insert.py):

```python
TOPIC_SEGMENT_PROMPT = """Identify topic boundaries..."""

class PreInsert(MapFunction):
    def __init__(self, config):
        self.action = config.get("operators.pre_insert.action", "none")
        # ...

    def _transform_topic_segment(self, data):
        prompt = self.config.get("operators.pre_insert.segment_prompt", TOPIC_SEGMENT_PROMPT)
        min_size = self.config.get("operators.pre_insert.min_segment_size", 100)
```

**After**:

```python
# 无顶层常量

class PreInsert(MapFunction):
    def __init__(self, config):
        self.config = config
        self.action = self._require_config("operators.pre_insert.action")
        # ...

    def _require_config(self, key: str) -> Any:
        """获取必需配置，缺失则报错"""
        value = self.config.get(key)
        if value is None:
            raise ConfigurationError(f"缺少必需配置: {key}")
        return value

    def _transform_topic_segment(self, data):
        prompt = self._require_config("operators.pre_insert.prompts.topic_segment")
        min_size = self._require_config("operators.pre_insert.transform.min_segment_size")
```

#### 3.3 各文件改动量估算

| 文件                | 删除行数      | 修改行数                | 难度 |
| ------------------- | ------------- | ----------------------- | ---- |
| `pre_insert.py`     | ~80 (prompts) | ~150 (defaults→require) | 中   |
| `post_insert.py`    | ~70 (prompts) | ~200 (defaults→require) | 高   |
| `pre_retrieval.py`  | ~30 (prompts) | ~100 (defaults→require) | 中   |
| `post_retrieval.py` | ~10 (prompts) | ~80 (defaults→require)  | 低   |

______________________________________________________________________

### 阶段四：预设配置文件创建 (1天)

为常见使用场景创建预设配置文件。

**产出物**:

- `config/presets/stm_basic.yaml` - 短期记忆基础配置
- `config/presets/hipporag.yaml` - HippoRAG 风格配置
- `config/presets/generative_agents.yaml` - Generative Agents 风格配置
- `config/presets/memoryos.yaml` - MemoryOS 风格配置

______________________________________________________________________

### 阶段五：文档与测试 (1天)

1. **更新文档**: Pipeline_README.md 增加配置说明章节
1. **配置示例**: 每个 action 提供完整配置示例
1. **单元测试**: 测试配置缺失时的报错信息

______________________________________________________________________

## 📅 时间线

| 阶段 | 任务           | 工时  | 产出物                |
| ---- | -------------- | ----- | --------------------- |
| 1    | 配置模板设计   | 0.5天 | `template_full.yaml`  |
| 2    | 配置校验器实现 | 1天   | `config_validator.py` |
| 3    | 算子代码重构   | 3-4天 | 4个算子文件修改       |
| 4    | 预设配置文件   | 1天   | 4个预设配置           |
| 5    | 文档与测试     | 1天   | 文档更新 + 测试       |

**总计**: 6.5-7.5 人天

______________________________________________________________________

## ✅ 验收标准

1. **零默认值**: 所有算子代码中不再包含任何默认 prompt 或默认参数值
1. **快速失败**: 缺少任何必需配置时，程序启动即报错，错误信息包含缺失的配置键
1. **配置完整**: 提供至少 4 个完整可运行的预设配置文件
1. **文档完善**: 每个配置项都有明确的说明和示例

______________________________________________________________________

## 🔗 相关文件

- 需修改: `libs/pre_insert.py`, `libs/post_insert.py`, `libs/pre_retrieval.py`,
  `libs/post_retrieval.py`
- 新建: `utils/config_validator.py`, `config/template_full.yaml`, `config/presets/*.yaml`
- 更新: `mem_docs/Pipeline_README.md`

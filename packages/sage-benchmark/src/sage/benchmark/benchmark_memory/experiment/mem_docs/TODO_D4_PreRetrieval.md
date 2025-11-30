# D4: PreRetrieval 开发 TODO

## 📌 任务交接说明

**负责人**: 已完成  
**预估工时**: 12 人天  
**依赖**: 无（可独立开发）  
**交付物**: `libs/pre_retrieval.py` 中的新 action 分支实现

本维度负责**记忆检索前的查询预处理**，优化用户查询以提高检索效果。你需要实现 5 种新的 action：查询优化、多维编码、查询分解、检索路由、查询验证。这些功能可以显著提升检索的准确率和召回率。

**开发前请阅读**:
- 现有实现参考: `pre_retrieval.py` 中的 `embedding` action
- 与 D2 的对应关系: `multi_embed` 应与 D2 的 `multi_embed` 配置保持一致
- 路由功能: `route` action 需要与多个 Memory Service 协作

**验收标准**:
- [x] `optimize` 的关键词提取能正确工作
- [x] `multi_embed` 与 D2 配置对齐
- [x] `route` 能正确路由到不同存储后端
- [x] 查询处理延迟在可接受范围内

---

> **代码位置**: `libs/pre_retrieval.py`
> **配置键**: `operators.pre_retrieval.action`
> **职责**: 记忆检索前的查询预处理（向量化、改写、优化）

---

## 📊 Action 总览

| Action | 状态 | 小类参数 | 参考工作 |
|--------|------|----------|----------|
| `none` | ✅ 已实现 | - | 基础透传 |
| `embedding` | ✅ 已实现 | `embedding_model` | 通用 |
| `optimize` | ✅ 已实现 | 见下文 | LD-Agent, HippoRAG |
| `multi_embed` | ✅ 已实现 | 见下文 | EmotionalRAG |
| `decompose` | ✅ 已实现 | 见下文 | 复杂查询 |
| `route` | ✅ 已实现 | 见下文 | 多源检索 |
| `validate` | ✅ 已实现 | 见下文 | 通用 |

---

## ✅ DONE-D4-1: `optimize`

### 概述
对查询进行优化处理，包括关键词提取、查询扩展、指令增强等。

### 小类参数

```yaml
operators:
  pre_retrieval:
    action: optimize
    
    # 优化类型
    optimize_type: "keyword_extract" # keyword_extract | expand | rewrite | instruction
    
    # keyword_extract 专用 (LD-Agent)
    extractor: "spacy"               # spacy | nltk | llm
    extract_types: ["NOUN", "PROPN"] # 提取的词性
    max_keywords: 10
    keyword_prompt: |                # llm 模式专用
      Extract the key search terms from this query...
    
    # expand 专用
    expand_prompt: |
      Generate 3 alternative phrasings of this query...
    expand_count: 3
    merge_strategy: "union"          # union | intersection
    
    # rewrite 专用 (HippoRAG Query2Doc)
    rewrite_prompt: |
      Rewrite this query to be more specific and searchable...
    
    # instruction 专用 (HippoRAG)
    instruction_prefix: |
      Retrieve passages that contain information about...
    instruction_suffix: ""
    
    # 输出配置
    replace_original: false          # 是否替换原查询
    store_optimized: true            # 存储优化后的查询
```

### 参考实现分析

#### LD-Agent (keyword_extract)
- **代码位置**: `/home/zrc/develop_item/LD-Agent/`
- **核心逻辑**:
  ```python
  # spaCy 名词提取
  doc = nlp(query)
  keywords = [token.text for token in doc if token.pos_ in ["NOUN", "PROPN"]]
  
  # 用关键词检索
  results = retriever.search(" ".join(keywords))
  ```

#### HippoRAG (instruction prefix)
- **代码位置**: `/home/zrc/develop_item/HippoRAG/src/`
- **核心逻辑**:
  ```python
  # 添加检索指令前缀
  instruction = "Retrieve passages that help answer the question: "
  augmented_query = instruction + query
  
  # 生成 embedding
  query_embedding = embed(augmented_query)
  ```

### 开发任务

- [x] 实现 `keyword_extract` 子类型
  - [x] spaCy 名词提取
  - [x] NLTK 词性标注
  - [x] LLM 关键词提取
- [x] 实现 `expand` 子类型
  - [x] LLM 查询扩展
  - [x] 多查询合并
- [x] 实现 `rewrite` 子类型
  - [x] Query2Doc 改写
- [x] 实现 `instruction` 子类型
  - [x] 指令前缀/后缀添加

### 预估工时: 3 天 ✅ 已完成

---

## ✅ DONE-D4-2: `multi_embed`

### 概述
生成多维查询向量，用于多路检索。

### 小类参数

```yaml
operators:
  pre_retrieval:
    action: multi_embed
    
    # 向量配置
    embeddings:
      - name: "semantic"
        model: "text-embedding-3-small"
        weight: 0.6
      - name: "emotion"
        model: "emotion-roberta"
        weight: 0.4
    
    # 输出格式
    output_format: "dict"            # dict | list
    
    # 与 D2 multi_embed 对应
    match_insert_config: true        # 自动匹配 pre_insert 的配置
```

### 参考实现分析

#### EmotionalRAG (dual embedding)
- **代码位置**: `/home/zrc/develop_item/EmotionalRAG/`
- **核心逻辑**:
  ```python
  # 双向量查询
  semantic_emb = semantic_model.encode(query)
  emotion_emb = emotion_model.encode(query)
  
  # 多路检索
  semantic_results = semantic_index.search(semantic_emb)
  emotion_results = emotion_index.search(emotion_emb)
  
  # 融合结果
  results = fusion(semantic_results, emotion_results, weights)
  ```

### 开发任务

- [x] 多模型 embedding 生成
- [x] 与 D2 multi_embed 配置对齐
- [x] 权重配置

### 预估工时: 2 天 ✅ 已完成

---

## ✅ DONE-D4-3: `decompose`

### 概述
将复杂查询分解为多个子查询。

### 小类参数

```yaml
operators:
  pre_retrieval:
    action: decompose
    
    # 分解策略
    decompose_strategy: "llm"        # llm | rule | hybrid
    
    # llm 策略
    decompose_prompt: |
      Break down this complex question into simpler sub-questions:
      Question: {query}
      Sub-questions:
    max_sub_queries: 5
    
    # rule 策略
    split_keywords: ["and", "or", "also", "additionally"]
    
    # 子查询处理
    sub_query_action: "parallel"     # parallel | sequential
    merge_strategy: "union"          # union | intersection | rerank
```

### 开发任务

- [x] 实现 `llm` 分解策略
- [x] 实现 `rule` 分解策略
- [x] 子查询并行/串行处理
- [x] 结果合并

### 预估工时: 2 天 ✅ 已完成

---

## ✅ DONE-D4-4: `route`

### 概述
根据查询内容路由到不同的检索源。

### 小类参数

```yaml
operators:
  pre_retrieval:
    action: route
    
    # 路由策略
    route_strategy: "classifier"     # classifier | keyword | llm
    
    # classifier 策略
    classifier_model: "intent-classifier"
    route_mapping:
      factual: "knowledge_base"
      personal: "user_memory"
      recent: "short_term_memory"
    
    # keyword 策略
    keyword_rules:
      - keywords: ["remember", "recall", "last time"]
        target: "long_term_memory"
      - keywords: ["just", "now", "recently"]
        target: "short_term_memory"
    
    # llm 策略
    route_prompt: |
      Determine which memory source should be queried:
      - short_term: recent conversations
      - long_term: historical memories
      - knowledge: factual information
    
    # 多路由
    allow_multi_route: true
    max_routes: 2
```

### 参考实现分析

#### MemoryOS (multi-tier routing)
- **代码位置**: `/home/zrc/develop_item/MemoryOS/`
- **核心逻辑**:
  - 同时查询 STM, MTM, LTM
  - 结果合并

#### MemGPT (function-based routing)
- **代码位置**: `/home/zrc/develop_item/MemGPT/memgpt/`
- **核心逻辑**:
  - Function calling 决定查询哪个记忆源
  - Core/Archival/Recall 分别处理

### 开发任务

- [x] 实现 `classifier` 路由策略
- [x] 实现 `keyword` 路由策略
- [x] 实现 `llm` 路由策略
- [x] 多路由支持
- [x] 与多源检索联动

### 预估工时: 3 天 ✅ 已完成

---

## ✅ DONE-D4-5: `validate`

### 概述
查询验证和预处理。

### 小类参数

```yaml
operators:
  pre_retrieval:
    action: validate
    
    # 验证规则
    rules:
      - type: "length"
        min: 3
        max: 1000
      - type: "language"
        allowed: ["en", "zh"]
      - type: "safety"
        blocked_patterns: ["ignore previous", "system prompt"]
    
    # 失败处理
    on_fail: "default"               # default | error | skip
    default_query: "Hello"           # on_fail=default 时使用
    
    # 预处理
    preprocessing:
      - strip_whitespace: true
      - lowercase: false
      - remove_punctuation: false
```

### 开发任务

- [x] 长度验证
- [x] 语言检测
- [x] 安全检查 (prompt injection 防护)
- [x] 预处理流程
- [x] 失败处理

### 预估工时: 2 天 ✅ 已完成

---

## 📋 开发优先级

| 优先级 | Action | 小类 | 参考工作 | 预估工时 | 状态 |
|--------|--------|------|----------|----------|------|
| P0 | `optimize` | keyword_extract, expand, rewrite, instruction | LD-Agent, HippoRAG | 3天 | ✅ |
| P1 | `multi_embed` | semantic+emotion | EmotionalRAG | 2天 | ✅ |
| P1 | `route` | classifier, keyword, llm | MemoryOS, MemGPT | 3天 | ✅ |
| P2 | `decompose` | llm, rule | 复杂查询 | 2天 | ✅ |
| P2 | `validate` | length, language, safety | 通用 | 2天 | ✅ |

**总计**: 12 人天 ✅ 已全部完成

---

*文档创建时间: 2025-01-27*  
*完成时间: 2025-11-27*

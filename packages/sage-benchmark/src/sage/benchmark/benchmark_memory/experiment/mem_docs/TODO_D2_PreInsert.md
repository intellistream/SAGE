# D2: PreInsert 开发 TODO

## 📌 任务交接说明

**负责人**: GitHub Copilot  
**完成日期**: 2025-01-27  
**依赖**: 无（可独立开发）  
**交付物**: `libs/pre_insert.py` 中的新 action 分支实现

本维度负责**记忆写入前的预处理**，将原始对话/文本转换为适合存储的格式。已在 `pre_insert.py` 中扩展了 5 种新的 action：内容转换、信息抽取、重要性评分、多维编码、输入验证。每种 action 通过配置参数控制具体行为。

**实现参考**:
- 现有实现: `pre_insert.py` 中的 `none` 和 `tri_embed` action
- 新增实现: `transform`, `extract`, `score`, `multi_embed`, `validate`
- 代码模式: 在 `execute()` 方法中添加 `elif self.action == "xxx":` 分支
- 参数读取: 通过 `config.get("operators.pre_insert.xxx")` 获取配置

**验收标准**:
- [x] 每个 action 的所有小类参数都可正常工作
- [x] 与下游 MemoryInsert 算子对接正常
- [x] 边界情况处理（空输入、超长文本等）

---

> **代码位置**: `libs/pre_insert.py`
> **配置键**: `operators.pre_insert.action`
> **职责**: 记忆写入前的预处理（归一化、抽取、编码）

---

## 📊 Action 总览

| Action | 状态 | 小类参数 | 参考工作 |
|--------|------|----------|----------|
| `none` | ✅ 已实现 | - | 基础透传 |
| `tri_embed` | ✅ 已实现 | `triple_extraction_prompt` | HippoRAG |
| `transform` | ✅ 已实现 | 见下文 | MemGPT, SeCom, LoCoMo |
| `extract` | ✅ 已实现 | 见下文 | A-mem, LD-Agent, LAPS |
| `score` | ✅ 已实现 | 见下文 | Generative Agents |
| `multi_embed` | ✅ 已实现 | 见下文 | EmotionalRAG |
| `validate` | ✅ 已实现 | 见下文 | 通用 |

---

## ✅ DONE-D2-1: `transform`

### 概述
对输入内容进行格式转换，包括分块、分段、事实提取、摘要等。

### 小类参数

```yaml
operators:
  pre_insert:
    action: transform
    
    # 转换类型
    transform_type: "chunking"       # chunking | topic_segment | fact_extract | summarize | compress
    
    # chunking 专用 (MemGPT)
    chunk_size: 512
    chunk_overlap: 50
    chunk_strategy: "fixed"          # fixed | sentence | paragraph
    
    # topic_segment 专用 (SeCom)
    segment_prompt: |
      Identify topic boundaries in the following conversation...
    min_segment_size: 100
    max_segment_size: 500
    
    # fact_extract 专用 (LoCoMo)
    fact_prompt: |
      Extract factual statements from the conversation...
    fact_format: "statement"         # statement | triple | json
    
    # summarize 专用
    summary_prompt: |
      Summarize the following conversation...
    summary_max_tokens: 200
    
    # compress 专用 (SeCom - LLMLingua)
    compression_ratio: 0.5
    compression_model: "llmlingua-2"
```

### 参考实现分析

#### MemGPT (chunking)
- **代码位置**: `/home/zrc/develop_item/MemGPT/memgpt/`
- **核心逻辑**:
  - 固定大小分块 (passage chunking)
  - 句子边界对齐
  - 重叠窗口

#### SeCom (topic_segment + compress)
- **代码位置**: `/home/zrc/develop_item/SeCom/`
- **核心逻辑**:
  - LLM 驱动话题分段
  - 每段独立压缩 (LLMLingua-2)
  - 保留关键信息

#### LoCoMo (fact_extract)
- **代码位置**: `/home/zrc/develop_item/locomo/`
- **核心逻辑**:
  - 对话转事实条目
  - 结构化存储 (who, what, when, where)

### 开发任务

- [ ] 实现 `chunking` 子类型
  - [ ] 固定大小分块
  - [ ] 句子/段落边界对齐
  - [ ] 重叠窗口处理
- [ ] 实现 `topic_segment` 子类型
  - [ ] LLM 话题边界识别
  - [ ] 分段大小控制
- [ ] 实现 `fact_extract` 子类型
  - [ ] 事实陈述提取
  - [ ] 结构化输出
- [ ] 实现 `summarize` 子类型
  - [ ] 内容摘要
- [ ] 实现 `compress` 子类型
  - [ ] LLMLingua 压缩集成

### 预估工时: 5 天

---

## ✅ DONE-D2-2: `extract`

### 概述
从输入内容中抽取关键信息，包括关键词、实体、名词、Persona等。

### 小类参数

```yaml
operators:
  pre_insert:
    action: extract
    
    # 抽取类型
    extract_type: "keyword"          # keyword | entity | noun | persona | all
    
    # keyword 专用 (A-mem)
    keyword_prompt: |
      Extract key concepts and keywords from the text...
    max_keywords: 10
    
    # entity 专用 (HippoRAG, LAPS)
    ner_model: "spacy"               # spacy | flair | llm
    entity_types: ["PERSON", "ORG", "LOC", "EVENT"]
    
    # noun 专用 (LD-Agent)
    noun_extractor: "spacy"          # spacy | nltk
    include_proper_nouns: true
    
    # persona 专用 (LD-Agent)
    persona_prompt: |
      Extract personality traits and preferences from the conversation...
    persona_fields: ["traits", "preferences", "facts"]
    
    # 输出格式
    output_format: "list"            # list | dict | json
    add_to_metadata: true
```

### 参考实现分析

#### A-mem (keyword)
- **代码位置**: `/home/zrc/develop_item/A-mem/`
- **核心逻辑**:
  - LLM 提取关键词
  - 生成上下文标签
  - 用于链接建立

#### LD-Agent (noun + persona)
- **代码位置**: `/home/zrc/develop_item/LD-Agent/`
- **核心逻辑**:
  - spaCy 提取名词短语
  - LLM 提取 Persona 信息
  - 用于检索增强

#### LAPS (entity)
- **代码位置**: `/home/zrc/develop_item/laps/`
- **核心逻辑**:
  - 实体识别
  - 实体链接
  - 构建键值对

#### HippoRAG (entity + triple)
- **代码位置**: `/home/zrc/develop_item/HippoRAG/src/`
- **核心逻辑**:
  - NER 实体抽取
  - OpenIE 三元组抽取
  - 构建知识图谱节点

### 开发任务

- [ ] 实现 `keyword` 子类型
  - [ ] LLM 关键词提取
  - [ ] 上下文标签生成
- [ ] 实现 `entity` 子类型
  - [ ] spaCy NER 集成
  - [ ] 自定义实体类型
- [ ] 实现 `noun` 子类型
  - [ ] 名词短语提取
  - [ ] 专有名词处理
- [ ] 实现 `persona` 子类型
  - [ ] 人格特征提取
  - [ ] 偏好信息提取
- [ ] 实现 `all` 组合模式

### 预估工时: 4 天

---

## ✅ DONE-D2-3: `score`

### 概述
对输入内容进行重要性评分。

### 小类参数

```yaml
operators:
  pre_insert:
    action: score
    
    # 评分类型
    score_type: "importance"         # importance | relevance | novelty | emotion
    
    # importance 专用 (Generative Agents)
    importance_prompt: |
      On a scale of 1 to 10, rate the importance of this memory...
    importance_scale: [1, 10]
    
    # emotion 专用 (EmotionalRAG)
    emotion_model: "emotion-roberta"
    emotion_categories: ["joy", "sadness", "anger", "fear", "surprise"]
    
    # 输出配置
    score_field: "importance_score"
    add_to_metadata: true
```

### 参考实现分析

#### Generative Agents (importance)
- **代码位置**: `/home/zrc/develop_item/locomo/generative_agents/`
- **核心逻辑**:
  - LLM 评估重要性 (1-10)
  - 用于反思触发
  - 用于检索加权

#### EmotionalRAG (emotion)
- **代码位置**: `/home/zrc/develop_item/EmotionalRAG/`
- **核心逻辑**:
  - 情感分类
  - 情感向量生成

### 开发任务

- [ ] 实现 `importance` 子类型
  - [ ] LLM 重要性评分
  - [ ] 分数归一化
- [ ] 实现 `emotion` 子类型
  - [ ] 情感分类模型集成
  - [ ] 情感向量生成
- [ ] 分数存入 metadata

### 预估工时: 2 天

---

## ✅ DONE-D2-4: `multi_embed`

### 概述
生成多维向量表示。

### 小类参数

```yaml
operators:
  pre_insert:
    action: multi_embed
    
    # 向量配置
    embeddings:
      - name: "semantic"
        model: "text-embedding-3-small"
        field: "content"
      - name: "emotion"
        model: "emotion-roberta"
        field: "content"
      - name: "entity"
        model: "text-embedding-3-small"
        field: "entities"            # 从 extract 结果取
    
    # 输出格式
    output_format: "dict"            # dict | concat | separate
    concat_dim: null                 # concat 模式下的拼接维度
```

### 参考实现分析

#### EmotionalRAG (dual embedding)
- **代码位置**: `/home/zrc/develop_item/EmotionalRAG/`
- **核心逻辑**:
  - 语义向量 (通用 embedding)
  - 情感向量 (情感 embedding)
  - 独立存储，联合检索

### 开发任务

- [ ] 多模型 embedding 生成
- [ ] 向量输出格式处理
- [ ] 与 extract 结果联动

### 预估工时: 2 天

---

## ✅ DONE-D2-5: `validate`

### 概述
输入内容验证和过滤。

### 小类参数

```yaml
operators:
  pre_insert:
    action: validate
    
    # 验证规则
    rules:
      - type: "length"
        min: 10
        max: 10000
      - type: "language"
        allowed: ["en", "zh"]
      - type: "content"
        blacklist: ["spam", "advertisement"]
      - type: "duplicate"
        similarity_threshold: 0.95
    
    # 失败处理
    on_fail: "skip"                  # skip | warn | error | transform
    transform_action: "summarize"    # on_fail=transform 时使用
```

### 开发任务

- [ ] 长度验证
- [ ] 语言检测
- [ ] 内容过滤
- [ ] 重复检测
- [ ] 失败处理逻辑

### 预估工时: 2 天

---

## 📋 开发优先级

| 优先级 | Action | 小类 | 参考工作 | 预估工时 |
|--------|--------|------|----------|----------|
| P0 | `transform` | chunking, topic_segment, fact_extract | MemGPT, SeCom, LoCoMo | 5天 |
| P0 | `extract` | keyword, entity, noun, persona | A-mem, LD-Agent, LAPS, HippoRAG | 4天 |
| P1 | `score` | importance, emotion | Generative Agents, EmotionalRAG | 2天 |
| P1 | `multi_embed` | semantic+emotion | EmotionalRAG | 2天 |
| P2 | `validate` | length, language, content, duplicate | 通用 | 2天 |

**总计**: 15 人天

---

*文档创建时间: 2025-01-27*

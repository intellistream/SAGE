# SAGE Distributed CPU-Intensive Workload Designs

## 设计目标
设计4个**分布式CPU密集型**工作负载，充分利用SAGE的分布式调度能力和丰富的算子生态，通过增加检索、重排序、Join、Batch等计算密集型操作来测试SAGE系统的**分布式调度**和**跨节点资源管理**能力，避免过分依赖大模型推理性能。

## 核心设计原则
1. **分布式优先**: 利用SAGE的Join、KeyBy、Batch、CoMap等分布式算子
2. **CPU密集型**: 增加检索、重排序、聚合等CPU操作的数量和复杂度
3. **减少LLM依赖**: 使用小模型（如Qwen2.5-0.5B）或限制生成长度（max_tokens=50-100）
4. **多阶段处理**: 通过多个Map、Filter、Join步骤增加pipeline复杂度
5. **并行性**: 利用KeyBy分区、多路Join、Batch聚合等实现跨节点并行
6. **向量操作**: 利用embedding和相似度计算增加计算负载

---

## Workload 1: Distributed Basic RAG Pipeline
**分布式检索-生成流水线（基准测试）**

### 架构（SAGE算子）
```
QuerySource (SourceFunction)
    ↓
EmbeddingMap (MapFunction) ← 分布式: 并行embedding计算
    ↓
KeyBy(query_type) ← 按查询类型分区，负载均衡
    ↓
VDBRetrieve (MapFunction) ← 分布式: 多节点并行检索
    ↓
FilterTopK (FilterFunction) ← 过滤低分结果
    ↓
BatchAggregator (BatchFunction) ← 批处理: 聚合多个查询的结果
    ↓
LLMGenerate (MapFunction) ← 分布式: 多节点并行生成
    ↓
MetricsSink (SinkFunction)
```

### SAGE算子配置
```python
# QuerySource (SourceFunction): 查询生成源
- 输入: 200个预定义查询问题
- 频率: 20 QPS
- 查询类型: technical/financial/general (三类，用于KeyBy分区)
- 输出: {"task_id": str, "query": str, "query_type": str}

# EmbeddingMap (MapFunction): 并行Embedding计算
- 分布式: 8个节点并行处理，每节点处理~25 QPS / 8 = 3-4 QPS
- Model: bge-large-en-v1.5 (1024-dim)
- CPU密集: Transformer forward pass
- 输出: {"task_id", "query", "query_type", "query_embedding": np.array(1024)}

# KeyBy(query_type): 按查询类型分区
- 作用: 将technical/financial/general查询分配到不同节点
- 目的: 负载均衡 + 局部性优化（同类查询可能访问相同VDB分区）
- 分布式: 数据重分区（shuffle），跨节点传输

# VDBRetrieve (MapFunction): 分布式向量检索
- 分布式: 每个分区独立在不同节点执行
- Backend: SageVDB (C++ optimized)
- Index Type: HNSW
- Top-K: 15 candidates (增加后续Filter负载)
- CPU密集操作:
  1. HNSW graph traversal (CPU密集)
  2. 计算15个候选的距离分数
  3. 排序和metadata提取
- 输出: {"task_id", "query", "candidates": [15 docs with scores]}

# FilterTopK (FilterFunction): 过滤低分结果
- 作用: 过滤score < 0.6的候选，只保留高质量结果
- 分布式: 每个节点并行过滤
- CPU密集: 分数计算和阈值判断
- 可能丢弃30-40%的低分结果，减少下游负载

# BatchAggregator (BatchFunction): 批量聚合
- Batch Size: 8 (聚合8个查询的结果)
- 作用: 减少LLM调用次数，提高GPU利用率
- 分布式: 每个节点独立批处理
- CPU密集操作:
  1. 等待batch填满（状态维护）
  2. 拼接8个查询的context（字符串操作）
  3. 构造batch请求格式
- Timeout: 500ms (避免长时间等待)
- 输出: {"batch_id", "tasks": [8 tasks with contexts]}

# LLMGenerate (MapFunction): 批量生成
- 分布式: 多节点并行调用LLM服务
- Model: Qwen/Qwen2.5-0.5B-Instruct (小模型)
- Batch Mode: 一次处理8个查询（提高GPU利用率）
- Max Tokens: 50 per query (减少生成时间)
- Temperature: 0.7
- CPU密集: Prompt构造、结果解析
- 输出: {"batch_id", "results": [8 responses]}

# MetricsSink (SinkFunction): 指标收集
- 记录: 延迟、吞吐量、节点分布、batch效率
```

### 分布式特征
- ✅ **KeyBy分区**: 按查询类型分配到不同节点，负载均衡
- ✅ **并行处理**: Embedding、VDB检索、LLM生成都在多节点并行
- ✅ **批量聚合**: BatchFunction减少LLM调用次数，提高吞吐量
- ✅ **过滤优化**: FilterFunction减少下游数据量

### CPU密集型特征
- Embedding计算（1024维向量 × 200 queries）
- HNSW图遍历和距离计算（15个候选 × 200 queries）
- 批量聚合的状态维护和字符串拼接
- 使用小模型快速生成，减少GPU瓶颈

---

## Workload 2: Distributed Multi-Stage RAG with Parallel Reranking
**分布式多阶段检索-并行重排序-生成流水线**

### 架构（SAGE算子）
```
QuerySource (SourceFunction)
    ↓
SessionContextMap (MapFunction) ← 查询会话历史
    ↓
KeyBy(user_id) ← 按用户分区
    ↓
MemoryRetrieve (MapFunction) ← 分布式: 多节点并行检索历史
    ↓
ContextEnhancementMap (MapFunction) ← CPU密集: 上下文融合
    ↓
    +-------------------+-------------------+
    ↓                   ↓                   ↓
VDBRetrieve1     VDBRetrieve2     VDBRetrieve3  ← 三路并行检索（SAGE自动复制）
    ↓                   ↓                   ↓
 KeyBy(task_id)    KeyBy(task_id)    KeyBy(task_id)
    ↓                   ↓                   ↓
    +---------Join------+--------Join------+  ← 三路Join汇聚结果
                        ↓
                 RerankMap (MapFunction) ← CPU密集: 混合重排序
                        ↓
                 BatchFunction(size=10) ← 批量聚合
                        ↓
                 LLMGenerate (MapFunction)
                        ↓
                   MetricsSink
```

### SAGE算子配置
```python
# QuerySource (SourceFunction): 会话式查询源
- 输入: 300个multi-turn对话查询
- 频率: 30 QPS
- 特点: 包含user_id和上下文依赖
- 输出: {"task_id", "user_id", "query", "session_id"}

# SessionContextMap (MapFunction): 会话上下文查询
- 作用: 查询当前session的最近10轮对话
- 分布式: 多节点并行查询Session Store
- CPU密集: 会话历史解析、时间窗口过滤
- 输出: {"task_id", "user_id", "query", "session_context": [10 turns]}

# KeyBy(user_id): 按用户分区
- 作用: 将同一用户的查询路由到同一节点
- 目的: 局部性优化（同用户的历史在同一节点缓存）
- 分布式: 数据重分区（shuffle）

# MemoryRetrieve (MapFunction): 分布式记忆检索
- Backend: NeuroMem (KV Store + VDB hybrid)
- 分布式: 每个user分区在不同节点并行处理
- 操作:
  1. 查询该用户的长期记忆（LTM）
  2. 提取相关实体和关键词（CPU密集）
  3. 计算记忆的相关性分数
- Top-K: 8 relevant memory items
- CPU密集点: 
  - 关键词提取（TF-IDF计算）
  - 实体识别（NER模型）
  - 上下文拼接和格式化
- 输出: {"task_id", "user_id", "query", "session_context", "memory_context": [8 items]}

# ContextEnhancementMap (MapFunction): 上下文增强
- 作用: 融合session_context + memory_context生成增强查询
- CPU密集操作:
  1. 加权平均session和memory的embeddings
  2. 提取关键短语（CPU密集）
  3. 构造增强query（字符串操作）
- 输出: {"task_id", "enhanced_query", "enhanced_embedding", ...}

# 三路并行VDB检索（SAGE自动复制数据到三个MapFunction）
# VDBRetrieve1 (MapFunction): 技术文档库
- Backend: SageVDB (Technical docs corpus)
- Index Type: HNSW
- Top-K: 10 candidates
- 分布式: 分配到Node 1-3

# VDBRetrieve2 (MapFunction): 通用知识库
- Backend: SageVDB (General knowledge corpus)
- Index Type: IVF_FLAT
- Top-K: 10 candidates
- 分布式: 分配到Node 4-6

# VDBRetrieve3 (MapFunction): 用户生成内容库
- Backend: SageVDB (UGC corpus)
- Index Type: HNSW
- Top-K: 10 candidates
- 分布式: 分配到Node 7-8

# KeyBy(task_id): 三路检索结果重分区（按task_id）
- 作用: 将同一task的三路结果路由到同一节点
- 分布式: 跨节点shuffle

# Join (BaseJoinFunction): 三路Join汇聚
- Join Strategy: Inner Join on task_id
- Window: 2s (等待三路结果到达)
- 分布式: 每个task_id分区独立join
- CPU密集操作:
  1. 维护join window状态（内存操作）
  2. 匹配三路结果（hash join）
  3. 合并30个候选文档（10×3）
  4. 去重（基于doc_id）
- 输出: {"task_id", "all_candidates": [~25 docs after dedup], "sources": ["tech", "general", "ugc"]}

# RerankMap (MapFunction): 混合重排序
- 输入: ~25个候选文档（三个VDB的合并结果）
- 分布式: 每个节点独立rerank
- CPU密集方法:
  1. BM25得分计算（基于enhanced_query）
     - 词频统计（TF）
     - 逆文档频率（IDF）查表
     - 归一化
  2. 语义相似度得分
     - Cosine similarity计算（enhanced_embedding vs doc_embedding）
  3. Source diversity分数
     - 来自不同VDB的文档加分（鼓励多样性）
  4. Recency分数
     - 时间衰减因子
  5. 加权融合:
     - 0.35 * BM25
     - 0.35 * semantic
     - 0.20 * diversity
     - 0.10 * recency
  6. 排序选择Top-10
- 输出: {"task_id", "reranked_docs": [10 docs with scores]}
- CPU密集: ~25个候选的4维度评分 + 加权融合

# BatchFunction (BatchFunction): 批量聚合
- Batch Size: 10 (聚合10个查询)
- Timeout: 800ms
- 分布式: 每个节点独立批处理
- CPU密集: batch状态维护、context拼接

# LLMGenerate (MapFunction): 批量生成
- Model: Qwen2.5-0.5B-Instruct
- Batch: 10 queries per call
- Max Tokens: 80 per query
- 分布式: 多节点并行调用LLM

# MetricsSink (SinkFunction): 指标收集
```

### 分布式特征
- ✅ **三路并行检索**: SAGE自动复制数据到3个VDB检索算子，并行执行
- ✅ **KeyBy + Join**: 按task_id重分区后三路Join汇聚结果
- ✅ **Join Window**: 2s窗口等待三路结果到达，容忍网络抖动
- ✅ **用户分区**: KeyBy(user_id)优化Memory检索的局部性
- ✅ **批量处理**: BatchFunction减少LLM调用次数

### CPU密集型特征
- **双重检索**: Session Context + Memory检索（KV + VDB hybrid）
- **上下文增强**: Embedding加权平均、关键短语提取（NLP操作）
- **三路并行VDB**: 30个候选（10×3）的检索和合并
- **Join操作**: Hash join + 去重（O(n)复杂度）
- **混合重排序**: 25个候选的4维度评分（BM25 + Semantic + Diversity + Recency）
- **TF-IDF计算**: 词频统计和IDF查表

---

## Workload 3: Distributed Dual-Source Semantic Join + Multi-Stage RAG
**双流语义Join + 分布式多阶段检索-生成**

### 架构（SAGE算子）
```
QuerySource (Source1) ─────────┐
                               ├─→ SemanticJoin (WindowedEventJoin)
DocUpdateSource (Source2) ─────┘        ↓
                                   KeyBy(joined_id)
                                         ↓
                                  MemoryRetrieve (MapFunction)
                                         ↓
                                  ContextFusionMap (MapFunction)
                                         ↓
                          +──────────────+──────────────+
                          ↓                             ↓
                    VDBRetrieve1                  VDBRetrieve2  ← 双路并行
                          ↓                             ↓
                    SimpleRerank1                SimpleRerank2
                          ↓                             ↓
                    KeyBy(joined_id)            KeyBy(joined_id)
                          ↓                             ↓
                          +─────── Join ────────────────+
                                      ↓
                              FinalRerankMap (MapFunction) ← 融合重排序
                                      ↓
                              BatchFunction(size=8)
                                      ↓
                              LLMGenerate (MapFunction)
                                      ↓
                                 MetricsSink
```

### SAGE算子配置
```python
# QuerySource (Source1): 用户查询流
- 频率: 25 QPS
- 数据: 实时用户问题
- 输出: {"query_id", "query_text", "query_embedding", "timestamp", "user_id"}

# DocUpdateSource (Source2): 文档更新流
- 频率: 15 QPS
- 数据: 实时文档/知识更新
- 输出: {"doc_id", "content", "doc_embedding", "timestamp", "category"}

# SemanticJoin (WindowedEventJoin): 向量化语义Join
- Join Type: Sliding Window Semantic Join (SAGE内置)
- Window Size: 30s sliding window
- Join Condition: cosine_similarity(query_emb, doc_emb) > 0.65
- 分布式特性:
  1. 双流数据在join节点汇聚（跨节点传输）
  2. 每个join分区独立维护30s窗口状态
  3. 动态负载均衡（SAGE自动调度）
- CPU密集操作:
  1. 维护30s sliding window状态（内存管理）
  2. 对每个query计算与窗口内所有doc的cosine相似度
     - 平均窗口内文档数: ~450 docs (15 QPS × 30s)
     - 每个query需计算450次相似度（1024维向量点积）
     - 复杂度: O(n*m*d) = O(25 * 450 * 1024) ≈ 11.5M ops/s
  3. Top-K选择: 每个query选择最相似的5个文档
  4. Join结果合并: (query, [matched_docs])
- 输出: {
    "joined_id": str,
    "query": dict,
    "matched_docs": [5 docs],
    "join_scores": [5 float],
    "timestamp": float
  }
- **关键**: 这是CPU最密集的算子（11.5M向量操作/秒）

# KeyBy(joined_id): Join结果分区
- 作用: 将join结果按joined_id分配到不同节点
- 分布式: 数据重分区（shuffle），实现负载均衡

# MemoryRetrieve (MapFunction): 历史Join结果检索
- Backend: NeuroMem VDB
- 分布式: 每个joined_id分区独立查询
- 操作: 查询历史上类似的join结果（基于query+docs的融合embedding）
- Top-K: 10 similar historical joins
- CPU密集:
  1. 融合query和matched_docs的embeddings（加权平均）
  2. VDB相似度搜索（HNSW遍历）
  3. 历史结果解析和格式化
- 输出: {"joined_id", "query", "matched_docs", "historical_joins": [10 items]}

# ContextFusionMap (MapFunction): 上下文融合
- CPU密集操作:
  1. 拼接query + matched_docs + historical_joins
  2. 计算融合embedding（weighted average）
     - 0.5 * query_embedding
     - 0.3 * avg(matched_docs_embeddings)
     - 0.2 * avg(historical_embeddings)
  3. 提取关键词和实体（NLP操作）
  4. 构造增强检索query
- 输出: {"joined_id", "fused_embedding", "fused_query", "context"}

# 双路并行VDB检索（SAGE自动复制）
# VDBRetrieve1 (MapFunction): 专业知识库
- Backend: SageVDB (Domain-specific corpus)
- Index Type: HNSW
- Top-K: 20 candidates
- 分布式: 分配到Node 1-4
- CPU密集: HNSW遍历、距离计算

# VDBRetrieve2 (MapFunction): 通用知识库
- Backend: SageVDB (General corpus)
- Index Type: IVF_HNSW (hybrid)
- Top-K: 20 candidates
- 分布式: 分配到Node 5-8
- CPU密集: IVF聚类 + HNSW遍历

# SimpleRerank1 (MapFunction): 快速BM25重排序
- 输入: 20 candidates from VDB1
- Method: BM25 scoring
- 输出: Top-12 results
- CPU密集: 词频统计、TF-IDF计算、排序
- 分布式: 与VDB1在同一节点（避免数据传输）

# SimpleRerank2 (MapFunction): 快速语义重排序
- 输入: 20 candidates from VDB2
- Method: Lightweight cross-encoder (distilbert-based)
- 输出: Top-12 results
- CPU密集: 12次forward pass + 排序
- 分布式: 与VDB2在同一节点

# KeyBy(joined_id): 双路Rerank结果重分区
- 作用: 将同一joined_id的两路结果路由到同一节点
- 分布式: 跨节点shuffle

# Join (BaseJoinFunction): 双路Rerank结果Join
- Join Strategy: Inner Join on joined_id
- Window: 1.5s
- 分布式: 每个joined_id分区独立join
- CPU密集:
  1. 维护join window
  2. 匹配双路结果（hash join）
  3. 合并24个候选（12×2）
- 输出: {"joined_id", "vdb1_results": [12], "vdb2_results": [12]}

# FinalRerankMap (MapFunction): 深度融合重排序
- 输入: 24个候选（来自双VDB）
- 分布式: 每个节点独立rerank
- CPU密集操作（最复杂的rerank）:
  1. **去重**: 基于doc_id和内容相似度（O(n²)）
     - 计算两两相似度矩阵（24×24）
     - 识别重复文档（similarity > 0.95）
     - 合并分数（取最高）
     - 结果: ~18-20个unique docs
  2. **多维度评分**（对每个候选）:
     a. BM25得分（基于fused_query）
     b. Semantic relevance（cross-encoder，CPU密集）
     c. Source diversity（来自不同VDB的加分）
     d. Join quality（matched_docs的平均join_score）
     e. Historical relevance（与historical_joins的相似度）
  3. **加权融合**:
     - 0.25 * BM25
     - 0.30 * semantic
     - 0.20 * diversity
     - 0.15 * join_quality
     - 0.10 * historical
  4. **归一化和排序**: 选择Top-10
- 输出: {"joined_id", "final_docs": [10 docs with scores], "fusion_metadata"}
- CPU密集: 去重(O(n²)) + 20候选×5维度评分 + 加权融合

# BatchFunction (BatchFunction): 批量聚合
- Batch Size: 8
- Timeout: 600ms
- 分布式: 每个节点独立批处理

# LLMGenerate (MapFunction): 批量生成
- Model: Qwen2.5-0.5B-Instruct
- Batch: 8 queries
- Max Tokens: 100 per query
- Context: Top-10 final docs + query + matched_docs
- 分布式: 多节点并行调用LLM

# MetricsSink (SinkFunction): 详细指标
- Join throughput and latency
- 各阶段延迟（Join, Memory, VDB1/2, Rerank1/2, Final Rerank）
- CPU utilization per node
- Shuffle data volume (KeyBy)
```

### 分布式特征
- ✅ **双流Join**: 25 QPS + 15 QPS双流语义Join，30s窗口
- ✅ **多次KeyBy**: 3次数据重分区（joined_id, joined_id, joined_id）
- ✅ **双路并行VDB**: SAGE自动复制到两个检索路径
- ✅ **嵌套Join**: SemanticJoin → 双路检索 → 结果Join
- ✅ **分布式Rerank**: 每个节点独立rerank，最后融合
- ✅ **负载均衡**: KeyBy实现动态负载分配

### CPU密集型特征（极高）
- **Semantic Join**: 11.5M向量ops/s（25 queries × 450 docs × 1024 dim）
- **双重检索**: Memory + 双VDB（40个候选）
- **三阶段Rerank**: Simple1 + Simple2 + Final Rerank
- **去重算法**: O(n²)相似度矩阵计算（24×24）
- **5维度评分**: 20个候选 × 5个维度 = 100次评分
- **Context融合**: 3路embedding加权平均 + NLP提取
- **Join操作**: 两次Join（Semantic + Result Join），状态维护

### 预期CPU占用: 70-85%

---

## Workload 4: Distributed Dual-Source Join + Dual-VDB + Multi-Stage Aggregation
**双流Join + 双VDB检索 + 三阶段重排序 + 分布式聚合（极致复杂度）**

### 架构（SAGE算子）
```
QuerySource (Source1) ─────────┐
                               ├─→ SemanticJoin (WindowedEventJoin, 60s window)
DocUpdateSource (Source2) ─────┘        ↓
                                   KeyBy(joined_id, parallelism=16) ← 高并行度
                                         ↓
                                  GraphMemoryRetrieve (MapFunction) ← 图遍历
                                         ↓
                                  EmbeddingFusionMap (MapFunction)
                                         ↓
                      +──────────────────+──────────────────+
                      ↓                                     ↓
              VDB1_Branch (4-stage)              VDB2_Branch (4-stage)
                      ↓                                     ↓
              VDB1Retrieve (Map)                   VDB2Retrieve (Map)
                      ↓                                     ↓
              CategoryFilter (Filter)              CategoryFilter (Filter)
                      ↓                                     ↓
              SimpleRerank1 (Map)                  SimpleRerank2 (Map)
                      ↓                                     ↓
              KeyBy(joined_id)                     KeyBy(joined_id)
                      ↓                                     ↓
                      +────────── Join (2s window) ─────────+
                                         ↓
                                  DeduplicationMap (MapFunction) ← CPU密集去重
                                         ↓
                                  FinalRerankMap (MapFunction) ← 5维度评分
                                         ↓
                                  DiversityFilterMap (MapFunction) ← 多样性过滤
                                         ↓
                               KeyBy(category, parallelism=8)
                                         ↓
                               CategoryAggregator (BatchFunction) ← 分类聚合
                                         ↓
                               GlobalBatchFunction(size=12)
                                         ↓
                               LLMGenerate (MapFunction)
                                         ↓
                               ResultPostProcess (MapFunction)
                                         ↓
                                    MetricsSink
```

### SAGE算子配置
```python
# QuerySource (Source1): 高频查询流
- 频率: 40 QPS (更高负载)
- 数据: 多领域技术问题
- Embedding: bge-large-en-v1.5 (1024-dim)
- 输出: {"query_id", "query_text", "query_embedding", "timestamp", "domain"}

# DocUpdateSource (Source2): 多源文档流
- 频率: 25 QPS (更高负载)
- 数据: 来自不同知识库的文档更新
- 标签: source_type (wiki/paper/manual/code/forum)
- 输出: {"doc_id", "content", "doc_embedding", "timestamp", "source_type", "category"}

# SemanticJoin (WindowedEventJoin): 增强语义Join
- Join Type: Sliding Window Semantic Join
- Window Size: 60s (更大窗口 = 更多状态)
- Join Condition: cosine_similarity > 0.60 (更宽松 = 更多匹配)
- 分布式特性:
  1. 双流在join算子汇聚（跨节点传输）
  2. 60s窗口内平均文档数: ~1500 docs (25 QPS × 60s)
  3. 高并发join操作（多个join分区并行）
- CPU密集操作（极致）:
  1. 维护60s sliding window状态
     - 双端队列管理（插入/删除）
     - 过期数据清理
  2. 相似度计算量:
     - 每个query vs 窗口内所有doc: 40 queries/s × 1500 docs × 1024 dim
     - 复杂度: O(40 * 1500 * 1024) ≈ **61.4M ops/s** (极高)
  3. 动态阈值调整:
     - 基于窗口内相似度分布的自适应阈值
     - 每秒重新计算分布统计（mean, std, percentiles）
  4. Multi-field join:
     - Similarity + source_type matching（相同类型加分）
     - Domain alignment（相同领域加分）
  5. Top-K selection: 每个query选择8个最相似文档
- 输出: {
    "joined_id": str,
    "query": dict,
    "matched_docs": [8 docs],
    "join_scores": [8 float],
    "join_metadata": {"threshold_used", "matched_types", "avg_score"}
  }
- **关键**: 这是整个pipeline中CPU最密集的算子（61.4M ops/s）

# KeyBy(joined_id, parallelism=16): 高并行度分区
- 作用: 将join结果分配到16个并行分区
- 目的: 最大化并行度，充分利用8节点×2线程=16核心
- 分布式: 数据重分区（shuffle），跨节点传输

# GraphMemoryRetrieve (MapFunction): 分层记忆检索（图遍历）
- Backend: NeuroMem (Graph + VDB hybrid)
- 分布式: 16个分区并行处理
- CPU密集操作:
  1. **Graph traversal**（最CPU密集的Memory操作）:
     - 从query实体出发遍历知识图谱
     - BFS搜索相关实体（最多3-hop）
     - 路径查找和权重计算
     - 平均每个query遍历100-200个节点
  2. **VDB search**:
     - 基于融合embedding的历史检索
     - HNSW遍历
  3. **结果融合**:
     - 图遍历结果（关系强度）
     - VDB检索结果（语义相似度）
     - 加权融合: 0.6*graph_score + 0.4*vdb_score
  4. **去重和排序**: 选择Top-12 memory items
- 输出: {"joined_id", "query", "matched_docs", "memory_items": [12 items with graph paths]}
- CPU密集: 图遍历(BFS) + VDB检索 + 结果融合

# EmbeddingFusionMap (MapFunction): 多路Embedding融合
- CPU密集操作:
  1. 计算融合embedding（4路加权平均）:
     - 0.35 * query_embedding
     - 0.30 * avg(matched_docs_embeddings) [8 docs]
     - 0.25 * avg(memory_embeddings) [12 items]
     - 0.10 * domain_embedding (领域先验)
  2. 提取关键词和实体:
     - NER模型提取实体
     - TF-IDF提取关键词
     - 实体链接到知识图谱
  3. 构造增强query（多策略）:
     - Query expansion（同义词扩展）
     - Entity substitution（实体替换）
     - Context injection（上下文注入）
- 输出: {"joined_id", "fused_embedding", "expanded_queries": [3 variants], "entities", "keywords"}

# ========== 双路并行VDB分支 ==========
# VDB1_Branch: 专业知识库路径

# VDB1Retrieve (MapFunction): 专业知识检索
- Backend: SageVDB (Domain-specific corpus, 100M docs)
- Index Type: HNSW (ef_search=200, 高精度)
- Top-K: 25 candidates (增加后续处理负载)
- 分布式: 分配到Node 1-4
- CPU密集: HNSW遍历（更大的ef_search = 更多计算）

# CategoryFilter (FilterFunction): 类别过滤
- 作用: 基于domain和category过滤不相关结果
- CPU密集: 
  - 计算query domain与doc category的匹配度
  - Multi-label classification score
  - 过滤掉~30%不相关文档
- 输出: ~17-18个候选

# SimpleRerank1 (MapFunction): BM25重排序
- 输入: ~18 candidates
- Method: Enhanced BM25 (k1=1.5, b=0.75)
- CPU密集:
  - 对每个expanded_query计算BM25（3 variants）
  - 取最大得分
  - 词频统计、IDF查表、归一化
- 输出: Top-15 results

# VDB2_Branch: 通用知识库路径

# VDB2Retrieve (MapFunction): 通用知识检索
- Backend: SageVDB (General corpus, 500M docs)
- Index Type: IVF_HNSW (nprobe=50, hybrid)
- Top-K: 25 candidates
- 分布式: 分配到Node 5-8
- CPU密集: IVF聚类中心搜索 + HNSW遍历

# CategoryFilter (FilterFunction): 同上
- 输出: ~17-18个候选

# SimpleRerank2 (MapFunction): 轻量Semantic重排序
- 输入: ~18 candidates
- Method: Distilbert-based cross-encoder
- CPU密集:
  - 18个候选的forward pass
  - Softmax和排序
- 输出: Top-15 results

# ========== 双路结果汇聚 ==========

# KeyBy(joined_id): 双路结果重分区
- 作用: 将同一joined_id的双路结果路由到同一节点
- 分布式: 跨节点shuffle

# Join (BaseJoinFunction): 双路VDB结果Join
- Join Strategy: Inner Join on joined_id
- Window: 2s (容忍网络抖动)
- 分布式: 每个joined_id分区独立join
- CPU密集:
  1. 维护join window状态
  2. Hash join（O(n)）
  3. 合并30个候选（15×2）
- 输出: {"joined_id", "vdb1_results": [15], "vdb2_results": [15], "total": 30}

# DeduplicationMap (MapFunction): 智能去重
- 输入: 30个候选（来自双VDB）
- 分布式: 每个节点独立去重
- CPU密集操作（极致）:
  1. **内容哈希**:
     - 计算每个doc的SimHash/MinHash
     - O(n)复杂度，快速粗筛
  2. **相似度矩阵**:
     - 对粗筛后的候选计算两两相似度
     - 平均~25个unique hashes
     - 矩阵大小: 25×25 = 625次相似度计算
     - 每次计算: 1024维cosine similarity
  3. **聚类去重**:
     - DBSCAN聚类（eps=0.05, min_samples=1）
     - 识别重复簇
     - 每个簇选择最高分文档作为代表
  4. **分数融合**:
     - 合并重复文档的分数（取最高或平均）
  5. 结果: ~18-22个unique docs
- 输出: {"joined_id", "unique_docs": [~20 docs], "dedup_metadata": {"clusters", "merged_count"}}
- CPU密集: 哈希计算(O(n)) + 相似度矩阵(O(n²)) + DBSCAN聚类

# FinalRerankMap (MapFunction): 深度融合重排序
- 输入: ~20个unique候选
- 分布式: 每个节点独立rerank
- CPU密集操作（5维度评分，极复杂）:
  1. **BM25得分**（基于expanded_queries）:
     - 对每个expanded_query计算BM25
     - 取最大得分
  2. **Semantic relevance**:
     - Cross-encoder计算query-doc相关性
     - 20次forward pass
  3. **Source diversity**:
     - 惩罚来自同一VDB的连续文档
     - 鼓励VDB1和VDB2结果交替
  4. **Join quality**:
     - 利用matched_docs的平均join_score
     - 加权到最终得分
  5. **Graph relevance**:
     - 计算doc与memory_items中图谱实体的关联强度
     - 图距离加权（1-hop高分，3-hop低分）
  6. **加权融合**:
     - 0.25 * BM25
     - 0.30 * semantic
     - 0.20 * diversity
     - 0.15 * join_quality
     - 0.10 * graph_relevance
  7. **归一化和排序**: 选择Top-12
- 输出: {"joined_id", "final_docs": [12 docs], "dimension_scores": {5 dimensions}}
- CPU密集: 20候选×5维度 = 100次评分 + 加权融合 + 排序

# DiversityFilterMap (MapFunction): 多样性过滤
- 作用: 确保最终结果的source多样性
- CPU密集操作:
  1. 计算source_type分布（wiki/paper/manual/code/forum）
  2. 如果某种类型>50%，降权该类型的低分文档
  3. 确保至少3种不同source_type
  4. MMR (Maximal Marginal Relevance)算法重排序
- 输出: {"joined_id", "diverse_docs": [10 docs], "source_distribution"}

# KeyBy(category, parallelism=8): 按类别分区
- 作用: 将相同category的结果聚合到同一节点
- 目的: Category级别的聚合统计
- 分布式: 数据重分区

# CategoryAggregator (BatchFunction): 分类聚合
- 作用: 同一category的结果进行批量聚合
- Batch Strategy: Per-category batching（不同category独立批次）
- Max Batch Size: 5 (同一category的5个查询)
- Timeout: 300ms per category
- CPU密集操作:
  1. 维护per-category batch状态
  2. 计算category-level统计（平均分数、文档分布）
  3. 构造category-aware context
- 输出: {"category_batch": [5 tasks], "category_stats"}

# GlobalBatchFunction (BatchFunction): 全局批量聚合
- Batch Size: 12 (聚合12个查询，可能来自不同category）
- Timeout: 800ms
- 分布式: 每个节点独立批处理
- CPU密集: 12个任务的context拼接、格式化

# LLMGenerate (MapFunction): 批量生成
- Model: Qwen2.5-0.5B-Instruct
- Batch: 12 queries per call
- Max Tokens: 120 per query
- Context per query: Top-10 diverse docs + query + matched_docs + category context
- 输入token数: ~2500 tokens per query (较多，但生成较短)
- 分布式: 多节点并行调用LLM
- CPU密集: Batch prompt构造、结果解析

# ResultPostProcess (MapFunction): 结果后处理
- CPU密集操作:
  1. 解析batch结果，拆分为单个response
  2. 格式化输出（JSON/Markdown）
  3. 计算结果质量分数（基于长度、实体覆盖率）
  4. 添加引用链接（到原始文档）
- 输出: {"task_id", "response", "references", "quality_score"}

# MetricsSink (SinkFunction): 详细性能指标
- Join throughput (queries/s, docs/s)
- 各阶段延迟（Join, Graph Memory, VDB1/2, Dedup, Final Rerank, Aggregation）
- CPU utilization per node and per operator
- Memory usage (window state, join state, batch state)
- Shuffle data volume (KeyBy operations)
- End-to-end latency (P50, P95, P99)
```

### 分布式特征（极致）
- ✅ **高负载双流Join**: 40 QPS + 25 QPS，60s窗口（1500 docs in window）
- ✅ **4次KeyBy**: 多次数据重分区（joined_id×2, category, global）
- ✅ **双路4-stage VDB分支**: 检索 → 过滤 → 重排序 → 汇聚
- ✅ **嵌套Join**: Semantic Join → 双路检索 → Result Join
- ✅ **双层Batch**: Category-level + Global batch
- ✅ **16并行度**: KeyBy(parallelism=16)最大化并行
- ✅ **分布式去重**: 每个节点独立DBSCAN聚类去重
- ✅ **跨节点协调**: 多次shuffle和join操作

### CPU密集型特征（极致）
1. **Semantic Join**: **61.4M ops/s**（40 queries × 1500 docs × 1024 dim）
   - 这是整个pipeline的最大瓶颈
2. **Graph Memory Traversal**: BFS遍历（100-200节点/query）+ VDB检索
3. **4路Embedding融合**: Query + 8 Docs + 12 Memory + Domain
4. **双路VDB**: 50个候选（25×2）的HNSW/IVF遍历
5. **智能去重**: O(n²)相似度矩阵（25×25=625次） + DBSCAN聚类
6. **5维度评分**: 20候选 × 5维度 = 100次评分
7. **MMR多样性**: Maximal Marginal Relevance算法
8. **双层聚合**: Category聚合 + Global批处理
9. **Query Expansion**: NER + TF-IDF + 实体链接
10. **三次重排序**: SimpleRerank1 + SimpleRerank2 + FinalRerank

### 预期性能特征
**CPU Utilization**: **85-95%**（极高，接近满负载）

**关键瓶颈**:
1. **Semantic Join**: 61.4M ops/s（最大瓶颈）
2. **DeduplicationMap**: O(n²)相似度矩阵 + 聚类
3. **FinalRerankMap**: 100次多维度评分
4. **Graph Memory**: BFS遍历 + 路径计算

**调度挑战**:
- 协调双流速率匹配（40 vs 25 QPS）
- 60s窗口的内存管理（~1500 docs × 1KB = 1.5MB per window）
- 4次KeyBy的shuffle优化（减少跨节点传输）
- 双路VDB的并行调度（Node 1-4 vs Node 5-8）
- 双层Batch的超时协调

**分布式优势**:
- 16个并行分区充分利用8节点集群
- KeyBy(category)实现按领域的局部性优化
- 双路VDB并行减少延迟（15→8的并行加速）
- 分布式去重避免单点瓶颈

### 极致复杂度来源
1. **更大Join窗口**: 60s vs 30s（双倍状态）
2. **更高QPS**: 40+25 vs 25+15（1.5倍负载）
3. **图遍历**: BFS + 路径权重计算
4. **智能去重**: SimHash + 相似度矩阵 + DBSCAN
5. **5维度评分**: 比3维度多67%计算
6. **双层聚合**: Category + Global批处理
7. **Query Expansion**: 3个变体的并行检索和融合

---

## 实现建议

### 1. SAGE分布式算子最佳实践

```python
# 利用KeyBy实现数据分区和负载均衡
from sage.common.core.functions.keyby_function import KeyByFunction
from sage.kernel.api.local_environment import LocalEnvironment

env = LocalEnvironment()

# 示例: 按用户ID分区，实现局部性优化
source.map(processor).keyby(lambda x: x["user_id"], parallelism=8)

# 示例: 按任务ID分区，用于Join前的数据重组
vdb_results.keyby(lambda x: x["task_id"])
```

```python
# 利用Join实现多路数据汇聚
from sage.common.core.functions.join_function import BaseJoinFunction

class ResultJoin(BaseJoinFunction):
    def __init__(self, window_size=2.0, **kwargs):
        super().__init__(window_size=window_size, **kwargs)
        
    def join_logic(self, left_data, right_data):
        """自定义join逻辑"""
        # 合并两路VDB检索结果
        return {
            "task_id": left_data["task_id"],
            "vdb1_results": left_data["candidates"],
            "vdb2_results": right_data["candidates"],
            "combined": left_data["candidates"] + right_data["candidates"]
        }

# Pipeline构建
vdb1_stream.keyby(lambda x: x["task_id"]).join(
    vdb2_stream.keyby(lambda x: x["task_id"]),
    ResultJoin(window_size=2.0)
)
```

```python
# 利用BatchFunction实现批量聚合
from sage.common.core.functions.batch_function import BatchFunction

class QueryBatcher(BatchFunction):
    def __init__(self, batch_size=8, timeout_ms=500, **kwargs):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self.timeout_ms = timeout_ms
        self.buffer = []
        
    def execute(self, data):
        """批量聚合逻辑"""
        self.buffer.append(data)
        
        if len(self.buffer) >= self.batch_size:
            batch = self.buffer[:self.batch_size]
            self.buffer = self.buffer[self.batch_size:]
            return self._create_batch(batch)
        
        return None  # 等待更多数据
    
    def _create_batch(self, items):
        return {
            "batch_id": f"batch_{time.time()}",
            "items": items,
            "size": len(items)
        }

# Pipeline使用
source.map(processor).batch(QueryBatcher(batch_size=8))
```

```python
# 利用FilterFunction实现数据过滤和负载削减
from sage.common.core.functions.filter_function import FilterFunction

class QualityFilter(FilterFunction):
    def __init__(self, min_score=0.6, **kwargs):
        super().__init__(**kwargs)
        self.min_score = min_score
        
    def filter_logic(self, data):
        """过滤低质量结果"""
        return data.get("score", 0.0) >= self.min_score

# Pipeline使用（减少下游30-40%负载）
vdb_results.filter(QualityFilter(min_score=0.6))
```

### 2. 减少LLM瓶颈的策略

```python
# 策略1: 使用小模型快速生成
model_config = {
    "model": "Qwen/Qwen2.5-0.5B-Instruct",  # 500M参数，推理快
    "max_tokens": 50-120,  # 限制生成长度
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 50,
}

# 策略2: 批量调用提高GPU利用率
class BatchLLMGenerator(MapFunction):
    def __init__(self, batch_size=8, **kwargs):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        
    def execute(self, batch_data):
        """批量调用LLM"""
        queries = [item["query"] for item in batch_data["items"]]
        contexts = [item["context"] for item in batch_data["items"]]
        
        # 批量推理（一次GPU调用处理多个查询）
        responses = self.llm_client.batch_generate(
            queries=queries,
            contexts=contexts,
            max_tokens=80,
        )
        
        return [
            {"task_id": item["task_id"], "response": resp}
            for item, resp in zip(batch_data["items"], responses)
        ]

# 策略3: 预计算和缓存（减少重复推理）
class CachedLLMGenerator(MapFunction):
    def __init__(self, cache_size=1000, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}  # query_hash -> response
        
    def execute(self, data):
        query_hash = hashlib.md5(data["query"].encode()).hexdigest()
        
        # 缓存命中
        if query_hash in self.cache:
            return self.cache[query_hash]
        
        # 缓存未命中，调用LLM
        response = self.llm_client.generate(data["query"])
        self.cache[query_hash] = response
        
        return response
```

### 3. 增强CPU密集操作

```python
# CPU密集操作1: Embedding计算和相似度
class EmbeddingComputeOperator(MapFunction):
    def __init__(self, model_name="BAAI/bge-large-en-v1.5", **kwargs):
        super().__init__(**kwargs)
        self.model = SentenceTransformer(model_name)
        
    def execute(self, data):
        # CPU密集: Transformer forward pass
        embedding = self.model.encode(data["query"])  # 1024-dim
        
        # 额外CPU操作: 计算与候选的详细相似度
        candidates = data.get("candidates", [])
        scores = []
        for cand in candidates:
            # CPU密集: 1024维向量点积和归一化
            score = self._cosine_similarity(embedding, cand["embedding"])
            scores.append(score)
        
        return {
            "task_id": data["task_id"],
            "query_embedding": embedding,
            "candidate_scores": scores,
        }
    
    def _cosine_similarity(self, a, b):
        """CPU密集: 余弦相似度计算"""
        import numpy as np
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# CPU密集操作2: BM25重排序
class BM25Reranker(MapFunction):
    def __init__(self, k1=1.5, b=0.75, **kwargs):
        super().__init__(**kwargs)
        self.k1 = k1
        self.b = b
        self.avg_doc_len = 100  # 平均文档长度
        self.idf_cache = {}  # IDF查找表
        
    def execute(self, data):
        query = data["query"]
        candidates = data["candidates"]
        
        # CPU密集: 词频统计
        query_terms = self._tokenize(query)
        
        scores = []
        for doc in candidates:
            doc_terms = self._tokenize(doc["content"])
            doc_len = len(doc_terms)
            
            # CPU密集: BM25计算
            score = 0.0
            for term in query_terms:
                tf = doc_terms.count(term)
                idf = self._get_idf(term)
                
                # BM25公式
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * (doc_len / self.avg_doc_len)
                )
                score += idf * (numerator / denominator)
            
            scores.append((doc, score))
        
        # 排序（CPU密集）
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "task_id": data["task_id"],
            "reranked": [doc for doc, _ in scores[:10]],
        }
    
    def _tokenize(self, text):
        """分词（CPU密集）"""
        return text.lower().split()
    
    def _get_idf(self, term):
        """IDF查表"""
        return self.idf_cache.get(term, 1.0)

# CPU密集操作3: 去重和聚类
class DeduplicationOperator(MapFunction):
    def __init__(self, similarity_threshold=0.95, **kwargs):
        super().__init__(**kwargs)
        self.threshold = similarity_threshold
        
    def execute(self, data):
        candidates = data["candidates"]
        
        # CPU密集: SimHash计算（快速粗筛）
        hashes = [self._simhash(doc["content"]) for doc in candidates]
        
        # CPU密集: 相似度矩阵（O(n²)）
        n = len(candidates)
        similarity_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i+1, n):
                sim = self._cosine_similarity(
                    candidates[i]["embedding"],
                    candidates[j]["embedding"]
                )
                similarity_matrix[i][j] = sim
                similarity_matrix[j][i] = sim
        
        # CPU密集: DBSCAN聚类去重
        from sklearn.cluster import DBSCAN
        clustering = DBSCAN(
            eps=1-self.threshold,
            min_samples=1,
            metric="precomputed"
        )
        labels = clustering.fit_predict(1 - similarity_matrix)
        
        # 每个簇选择最高分文档
        unique_docs = []
        for label in set(labels):
            cluster_docs = [
                doc for i, doc in enumerate(candidates) if labels[i] == label
            ]
            best_doc = max(cluster_docs, key=lambda x: x.get("score", 0))
            unique_docs.append(best_doc)
        
        return {
            "task_id": data["task_id"],
            "unique_docs": unique_docs,
            "dedup_stats": {
                "original_count": n,
                "unique_count": len(unique_docs),
                "clusters": len(set(labels)),
            }
        }
    
    def _simhash(self, text):
        """SimHash计算（CPU密集）"""
        import hashlib
        tokens = text.split()
        hashes = [int(hashlib.md5(t.encode()).hexdigest(), 16) for t in tokens]
        return sum(hashes) % (2**64)
```

### 4. 参数调优建议

```python
# 调优参数集合
WORKLOAD_CONFIGS = {
    "workload_1": {
        "qps": 20,
        "top_k_vdb": 15,
        "batch_size": 8,
        "keyby_parallelism": 8,
        "filter_threshold": 0.6,
        "llm_max_tokens": 50,
    },
    "workload_2": {
        "qps": 30,
        "top_k_memory": 8,
        "top_k_vdb": [10, 10, 10],  # 三路VDB
        "join_window": 2.0,  # 秒
        "rerank_candidates": 25,
        "batch_size": 10,
        "keyby_parallelism": 8,
        "llm_max_tokens": 80,
    },
    "workload_3": {
        "query_qps": 25,
        "doc_qps": 15,
        "join_window": 30.0,  # 秒
        "join_threshold": 0.65,
        "top_k_memory": 10,
        "top_k_vdb": [20, 20],  # 双VDB
        "rerank_candidates": [12, 12],
        "batch_size": 8,
        "keyby_parallelism": 8,
        "llm_max_tokens": 100,
    },
    "workload_4": {
        "query_qps": 40,
        "doc_qps": 25,
        "join_window": 60.0,  # 秒
        "join_threshold": 0.60,
        "graph_max_hops": 3,
        "top_k_memory": 12,
        "top_k_vdb": [25, 25],  # 双VDB
        "rerank_candidates": [15, 15],
        "dedup_threshold": 0.95,
        "final_diversity_types": 3,
        "category_batch_size": 5,
        "global_batch_size": 12,
        "keyby_parallelism": 16,  # 最高并行度
        "llm_max_tokens": 120,
    },
}

# 使用示例
config = WORKLOAD_CONFIGS["workload_4"]
source = QuerySource(qps=config["query_qps"])
```

### 5. 分布式部署建议

```python
# Remote环境配置（8节点集群）
from sage.kernel.api.remote_environment import RemoteEnvironment

env = RemoteEnvironment(
    ray_address="auto",  # 自动连接Ray集群
    cluster_config={
        "num_nodes": 8,
        "cpus_per_node": 16,
        "memory_per_node": "64GB",
    }
)

# 算子分配策略
operator_placement = {
    "QuerySource": "node-1",  # 源算子固定节点
    "DocSource": "node-1",
    "SemanticJoin": ["node-2", "node-3"],  # Join需要高CPU，分配2个节点
    "KeyBy_1": "auto",  # SAGE自动调度
    "MemoryRetrieve": ["node-2", "node-3", "node-4"],  # 多节点并行
    "VDB1Retrieve": ["node-1", "node-2", "node-3", "node-4"],  # 4节点
    "VDB2Retrieve": ["node-5", "node-6", "node-7", "node-8"],  # 4节点
    "FinalRerank": "auto",
    "BatchAggregator": ["node-1", "node-5"],  # 两个batch节点
    "LLMGenerate": ["node-1", "node-5"],  # GPU节点
}

# 资源约束
resource_requirements = {
    "SemanticJoin": {"cpu": 4, "memory": "8GB"},  # Join需要更多资源
    "GraphMemoryRetrieve": {"cpu": 2, "memory": "4GB"},
    "DeduplicationOperator": {"cpu": 2, "memory": "2GB"},
    "FinalRerank": {"cpu": 2, "memory": "2GB"},
    "LLMGenerate": {"cpu": 1, "memory": "2GB", "gpu": 0.5},  # 共享GPU
}
```

### 6. 测试场景设计

```python
# 测试场景配置
TEST_SCENARIOS = {
    "scenario_1_baseline": {
        "workload": "workload_1",
        "duration": 300,  # 5分钟
        "expected_cpu": "30-50%",
        "expected_throughput": "15-20 QPS",
        "key_metrics": ["vdb_latency", "llm_latency", "e2e_latency"],
    },
    "scenario_2_medium": {
        "workload": "workload_2",
        "duration": 600,  # 10分钟
        "expected_cpu": "50-70%",
        "expected_throughput": "20-25 QPS",
        "key_metrics": [
            "join_efficiency",
            "rerank_time",
            "batch_utilization",
            "shuffle_volume",
        ],
    },
    "scenario_3_high": {
        "workload": "workload_3",
        "duration": 900,  # 15分钟
        "expected_cpu": "70-85%",
        "expected_throughput": "15-20 QPS",
        "key_metrics": [
            "semantic_join_throughput",
            "memory_graph_latency",
            "dual_vdb_latency",
            "dedup_efficiency",
        ],
    },
    "scenario_4_extreme": {
        "workload": "workload_4",
        "duration": 1200,  # 20分钟
        "expected_cpu": "85-95%",
        "expected_throughput": "10-15 QPS",
        "key_metrics": [
            "join_window_memory",
            "graph_traversal_time",
            "dedup_clustering_time",
            "multi_stage_rerank_time",
            "category_aggregation",
            "overall_scheduler_efficiency",
        ],
    },
}

# 测试执行
def run_test_scenario(scenario_name):
    scenario = TEST_SCENARIOS[scenario_name]
    workload_config = WORKLOAD_CONFIGS[scenario["workload"]]
    
    # 构建pipeline
    pipeline = build_pipeline(workload_config)
    
    # 运行测试
    metrics = pipeline.run(duration=scenario["duration"])
    
    # 验证指标
    assert metrics["cpu_utilization"] in parse_range(scenario["expected_cpu"])
    assert metrics["throughput"] in parse_range(scenario["expected_throughput"])
    
    return metrics
```

### 7. 性能优化Checklist

- [ ] **KeyBy并行度**: 根据节点数调整（8节点 → parallelism=8-16）
- [ ] **Batch大小**: 根据QPS和延迟需求调整（高QPS → 大batch）
- [ ] **Join窗口**: 根据数据到达速率调整（高QPS → 小窗口）
- [ ] **Filter阈值**: 过滤低质量数据，减少下游负载（30-40%削减）
- [ ] **VDB Top-K**: 增加候选数提高召回，但增加rerank负载
- [ ] **Rerank策略**: 轻量级（BM25）vs 重量级（Cross-Encoder）
- [ ] **LLM批量**: 批量调用提高GPU利用率，但增加延迟
- [ ] **去重策略**: SimHash粗筛 + 精确去重平衡性能和准确性
- [ ] **内存管理**: Join/Batch窗口的状态管理，避免OOM
- [ ] **Shuffle优化**: 减少KeyBy次数，合并重分区操作

---

## 预期性能特征总结

### CPU Utilization对比
| Workload | CPU占用 | 主要瓶颈 | 关键算子 |
|----------|---------|---------|---------|
| Workload 1 | 30-50% | VDB检索 | EmbeddingMap, VDBRetrieve |
| Workload 2 | 50-70% | 三路Join + Rerank | SemanticJoin(3-way), RerankMap |
| Workload 3 | 70-85% | Semantic Join + 去重 | SemanticJoin(11.5M ops/s), FinalRerank |
| Workload 4 | 85-95% | Semantic Join + 聚类去重 + 5维评分 | SemanticJoin(61.4M ops/s), DeduplicationMap, FinalRerank |

### 分布式特性对比
| Workload | KeyBy次数 | Join次数 | 并行路径 | Batch层级 |
|----------|-----------|----------|----------|-----------|
| Workload 1 | 1 | 0 | 0 | 1 (Global) |
| Workload 2 | 2 | 2 (3-way + result) | 3 (三路VDB) | 1 (Global) |
| Workload 3 | 3 | 2 (semantic + result) | 2 (双VDB) | 1 (Global) |
| Workload 4 | 4 | 2 (semantic + result) | 2 (双VDB 4-stage) | 2 (Category + Global) |

### 调度挑战对比
| Workload | 窗口状态 | 数据量 | Shuffle次数 | 资源协调 |
|----------|---------|--------|------------|----------|
| Workload 1 | 无 | 低 | 1 | 简单 |
| Workload 2 | 2s Join | 中 | 4 (KeyBy×2 + Join×2) | 中等 |
| Workload 3 | 30s Join | 中高 | 6 (KeyBy×3 + Join×2 + 双路) | 复杂 |
| Workload 4 | 60s Join | 极高 | 8 (KeyBy×4 + Join×2 + 双路 + 双层Batch) | 极复杂 |

### 性能瓶颈预测
**Workload 1 (基准)**:
- ✅ 瓶颈: VDB检索（HNSW遍历）
- ✅ 优化点: Batch size调优、Filter threshold
- ✅ 适合场景: 单机测试、基准对比

**Workload 2 (中等复杂度)**:
- ✅ 瓶颈: 三路Join + 混合Rerank
- ✅ 优化点: Join window调优、并行路径数量
- ✅ 适合场景: 多路检索融合、并行调度测试

**Workload 3 (高复杂度)**:
- ✅ 瓶颈: Semantic Join (11.5M ops/s) + 去重算法
- ✅ 优化点: Join窗口大小、去重策略
- ✅ 适合场景: 双流Join、分布式重排序测试
- ✅ 挑战: 双流速率匹配、30s窗口内存管理

**Workload 4 (极致复杂度)**:
- ✅ 瓶颈: Semantic Join (61.4M ops/s) + DBSCAN聚类 + 5维评分
- ✅ 优化点: 并行度调优（parallelism=16）、内存管理
- ✅ 适合场景: 极限压测、调度策略对比、资源管理测试
- ✅ 挑战: 
  - 60s窗口状态管理（1500 docs × 1KB ≈ 1.5MB per window）
  - 多次shuffle的网络开销
  - 双层Batch的超时协调
  - 图遍历的不确定性延迟

### 吞吐量预测
| Workload | 目标QPS | P50延迟 | P95延迟 | P99延迟 |
|----------|---------|---------|---------|---------|
| Workload 1 | 15-20 | 200ms | 400ms | 600ms |
| Workload 2 | 20-25 | 500ms | 1000ms | 1500ms |
| Workload 3 | 15-20 | 800ms | 1500ms | 2000ms |
| Workload 4 | 10-15 | 1200ms | 2000ms | 3000ms |

### SAGE调度优势体现
1. **负载均衡**: KeyBy自动分区，避免单点瓶颈
2. **并行加速**: 三路/双路并行检索，理论3x/2x加速
3. **批量优化**: BatchFunction减少LLM调用次数，提高GPU利用率
4. **容错能力**: Join window容忍网络抖动和节点故障
5. **弹性扩展**: 支持动态调整parallelism和节点数
6. **资源隔离**: 不同算子可分配到不同节点，避免资源竞争

---

## 实现路径

### Stage 1: 基准Pipeline (1-2天)
**目标**: 实现Workload 1，建立性能基线

**任务**:
1. ✅ 实现基本算子: QuerySource, EmbeddingMap, VDBRetrieve, BatchFunction, LLMGenerate
2. ✅ 配置KeyBy(query_type)实现分区
3. ✅ 配置FilterFunction过滤低分结果
4. ✅ 部署到8节点集群
5. ✅ 性能测试: 验证15-20 QPS吞吐量、30-50% CPU利用率
6. ✅ 建立监控Dashboard: CPU、内存、延迟、吞吐量

**验收标准**:
- 稳定运行5分钟
- P50延迟 < 250ms
- CPU利用率在30-50%区间
- 无OOM或崩溃

### Stage 2: 多路Join Pipeline (2-3天)
**目标**: 实现Workload 2，验证分布式Join和并行检索

**任务**:
1. ✅ 实现SessionContext和Memory检索
2. ✅ 实现三路并行VDB检索（SAGE自动复制）
3. ✅ 实现BaseJoinFunction汇聚三路结果
4. ✅ 实现RerankMap的4维度评分
5. ✅ 测试Join window调优（1s vs 2s vs 3s）
6. ✅ 测试并行度影响（parallelism=4 vs 8 vs 16）

**验收标准**:
- Join成功率 > 95%
- P95延迟 < 1200ms
- CPU利用率在50-70%区间
- 三路VDB检索时间接近（负载均衡）

### Stage 3: 双流Semantic Join (3-4天)
**目标**: 实现Workload 3，验证双流Join和分布式去重

**任务**:
1. ✅ 实现双流Source (Query + Doc)
2. ✅ 实现WindowedEventJoin (30s窗口)
3. ✅ 实现GraphMemoryRetrieve (图遍历)
4. ✅ 实现双路VDB并行检索
5. ✅ 实现DeduplicationMap (SimHash + 相似度矩阵)
6. ✅ 实现FinalRerank (5维度评分)
7. ✅ 测试窗口大小影响（15s vs 30s vs 60s）
8. ✅ 测试Join阈值影响（0.6 vs 0.65 vs 0.7）

**验收标准**:
- Join throughput: 20+ matched pairs/s
- P50延迟 < 1000ms
- CPU利用率在70-85%区间
- 去重率: 20-30%（识别重复文档）
- 窗口内存稳定（无内存泄漏）

### Stage 4: 极致复杂Pipeline (4-5天)
**目标**: 实现Workload 4，压测SAGE调度极限

**任务**:
1. ✅ 实现60s大窗口Join
2. ✅ 实现高并行度KeyBy (parallelism=16)
3. ✅ 实现双路4-stage VDB分支 (Retrieve → Filter → Rerank → Join)
4. ✅ 实现DBSCAN聚类去重
5. ✅ 实现双层Batch (Category + Global)
6. ✅ 实现MMR多样性过滤
7. ✅ 压力测试: 40 QPS query + 25 QPS doc
8. ✅ 调度策略对比: FIFO vs LoadAware vs Priority

**验收标准**:
- 稳定运行20分钟
- CPU利用率在85-95%区间
- P99延迟 < 3500ms
- 无节点崩溃或任务超时
- 调度效率: 任务分布均匀（8节点利用率差异<10%）

### Stage 5: 性能调优和对比 (2-3天)
**目标**: 对比4个Workload，生成性能报告

**任务**:
1. ✅ 统一测试环境（相同集群配置）
2. ✅ 对比实验: 
   - CPU利用率对比
   - 延迟对比（P50/P95/P99）
   - 吞吐量对比
   - 调度效率对比（负载均衡、资源利用率）
3. ✅ 瓶颈分析: 
   - 识别每个Workload的关键瓶颈算子
   - 分析shuffle开销
   - 分析join window内存开销
4. ✅ 生成性能报告和可视化图表
5. ✅ 编写Benchmark论文章节

**输出**:
- 性能对比表格（CPU、延迟、吞吐量）
- 瓶颈分析报告（火焰图、调用链追踪）
- 调度策略对比结论
- Benchmark代码和文档

---

## 附录: SAGE算子完整列表

### 核心算子
| 算子 | 功能 | 分布式特性 | 适用场景 |
|------|------|-----------|----------|
| `SourceFunction` | 数据源 | 可并行 | 生成查询、读取数据流 |
| `MapFunction` | 1-to-1转换 | 自动并行 | Embedding、检索、重排序 |
| `FilterFunction` | 过滤 | 自动并行 | 质量过滤、阈值筛选 |
| `KeyByFunction` | 分区 | 跨节点shuffle | 负载均衡、局部性优化 |
| `JoinFunction` | 多流汇聚 | 窗口join | 双流语义Join、结果合并 |
| `BatchFunction` | 批量聚合 | 节点本地 | LLM批量调用、数据聚合 |
| `SinkFunction` | 数据汇聚 | 可并行 | 指标收集、结果存储 |
| `FlatMapFunction` | 1-to-N转换 | 自动并行 | 数据扩展、Query expansion |
| `CoMapFunction` | 双流处理 | 双流协调 | 双流Join前处理 |

### 特殊算子
| 算子 | 功能 | 使用场景 |
|------|------|----------|
| `WindowedEventJoin` | 窗口语义Join | 双流时间窗口Join |
| `BaseJoinFunction` | 自定义Join | 复杂Join逻辑 |
| `LambdaFunction` | 内联函数 | 简单转换 |
| `FutureFunction` | 异步处理 | 外部API调用 |

---

---

## 硬件配置适配性分析

### 实际硬件配置
**集群规模**: 1台A6000机器 + 16个容器节点

**容器配置**:
- 节点数: 16个容器
- 每节点CPU: 8核心
- 每节点内存: 16GB
- 总计算资源: **128核心 + 256GB内存**

**宿主机服务**:
- GPU: A6000 (48GB显存)
- LLM服务: Qwen-3B-Instruct (轻量模型，推理快)
- Rerank服务: Rerank模型 (共享GPU)
- Embedding服务: 远程访问（其他机器）

### 可行性分析

#### ✅ Workload 1: 完全可行
**资源需求**:
- CPU: 30-50% × 128核 = 38-64核实际使用
- 内存: ~2GB per node × 16 = 32GB
- QPS: 20 (轻松应对)

**结论**: 
- ✅ CPU充足（128核远超需求）
- ✅ 内存充足（256GB >> 32GB）
- ✅ 3B模型推理速度快，不会成为瓶颈
- ⏱️ 预计P50延迟: 150-200ms

#### ✅ Workload 2: 完全可行
**资源需求**:
- CPU: 50-70% × 128核 = 64-90核实际使用
- 内存: ~4GB per node × 16 = 64GB
- QPS: 30
- Join Window: 2s (状态小)

**潜在瓶颈**:
- ⚠️ 三路并行VDB + Rerank需要协调
- ⚠️ Embedding远程调用可能增加延迟（+50-100ms）

**结论**:
- ✅ CPU充足
- ✅ 内存充足
- ⚠️ 需要优化Embedding批量调用减少网络往返
- ⏱️ 预计P50延迟: 400-500ms（含网络延迟）

#### ⚠️ Workload 3: 可行但需调优
**资源需求**:
- CPU: 70-85% × 128核 = 90-109核实际使用
- 内存: ~6GB per node × 16 = 96GB
- QPS: 25 (query) + 15 (doc)
- Join Window: 30s

**关键计算**:
```
Semantic Join负载:
- 窗口内文档数: 15 QPS × 30s = 450 docs
- 每秒相似度计算: 25 queries × 450 docs × 1024 dim = 11.5M ops/s
- 分配到16节点: 11.5M / 16 ≈ 720K ops/node/s
- 每核心: 720K / 8 = 90K ops/core/s
```

**内存需求**:
```
Join Window状态:
- 单窗口: 450 docs × 1KB = 450KB
- 16个分区: 450KB × 16 = 7.2MB（极小）
- 加上其他状态: ~20MB per node
- 总计: 320MB（远小于256GB）
```

**潜在瓶颈**:
- ⚠️ Semantic Join的11.5M ops/s是否能在128核上完成？
  - 假设每次相似度计算需要1000条指令
  - 11.5M × 1000 = 11.5B instructions/s
  - 128核 × 2.5GHz = 320 GIPS理论峰值
  - 利用率: 11.5B / 320G ≈ 3.6%（理论上完全可行）
- ⚠️ 去重算法的O(n²)复杂度（但n=18-22，可控）
- ⚠️ 远程Embedding调用可能成为瓶颈（需批量优化）

**优化建议**:
1. **Embedding批量调用**: batch_size=32，减少网络往返
2. **Join窗口优化**: 可以降低到20s（减少状态）
3. **KeyBy并行度**: 设置parallelism=16（对齐节点数）
4. **去重策略**: 使用SimHash快速粗筛（减少O(n²)计算）

**结论**:
- ✅ CPU充足（理论利用率仅3.6%，实际可能10-20%）
- ✅ 内存绝对充足（320MB << 256GB）
- ⚠️ 需要优化Embedding批量调用
- ⚠️ 需要监控Join算子CPU利用率
- ⏱️ 预计P50延迟: 700-900ms

#### ⚠️ Workload 4: 挑战较大但理论可行
**资源需求**:
- CPU: 85-95% × 128核 = 109-122核实际使用（接近满载）
- 内存: ~10GB per node × 16 = 160GB
- QPS: 40 (query) + 25 (doc)
- Join Window: 60s

**关键计算**:
```
Semantic Join负载（极致）:
- 窗口内文档数: 25 QPS × 60s = 1500 docs
- 每秒相似度计算: 40 queries × 1500 docs × 1024 dim = 61.4M ops/s
- 分配到16节点: 61.4M / 16 ≈ 3.84M ops/node/s
- 每核心: 3.84M / 8 = 480K ops/core/s
```

**详细CPU分析**:
```
假设现代CPU（Intel Cascade Lake / AMD EPYC）:
- SIMD加速: AVX-512可以同时处理16个float32
- 向量点积优化: 1024维 / 16 = 64次SIMD指令
- 加上其他操作（归一化等）: ~100次SIMD指令/相似度
- 每核心吞吐: 2.5GHz / 100 = 25M ops/core/s理论峰值
- 实际需求: 480K ops/core/s
- 利用率: 480K / 25M = 1.92%（理论上完全可行）

但实际情况更复杂:
- Python开销: 2-3x slowdown（没有C++/SIMD优化）
- NumPy优化: 可以接近native性能（MKL/OpenBLAS）
- 实际利用率: 5-10%（保守估计）
```

**内存需求**:
```
Join Window状态（大窗口）:
- 单窗口: 1500 docs × 1KB = 1.5MB
- 16个分区: 1.5MB × 16 = 24MB
- VDB检索缓存: ~50MB per node
- Batch状态: ~20MB per node
- 总计: ~90MB per node × 16 = 1.44GB（仍然很小）
```

**潜在瓶颈**:
- ⚠️ **Semantic Join**: 61.4M ops/s是最大挑战
  - 如果用纯Python实现: 可能无法达到
  - 如果用NumPy优化: 应该可以完成
  - 如果用C++扩展（SageVDB）: 完全没问题
- ⚠️ **DBSCAN聚类去重**: O(n²)复杂度，但n=20-25可控
  - 25×25 = 625次相似度计算
  - 每个计算1024维点积
  - 总计: 625 × 1024 ≈ 640K ops（微不足道）
- ⚠️ **图遍历**: BFS 100-200节点/query
  - CPU密集但并行性好
  - 分布在16节点上可行
- ⚠️ **远程Embedding**: 40 QPS可能需要更激进的批量
  - 建议batch_size=64，每1.6s一批
- ⚠️ **GPU资源竞争**: 
  - LLM生成（批量12个query）
  - Rerank模型（SimpleRerank1 + SimpleRerank2）
  - 两者可能竞争A6000显存和算力

**关键优化**:
1. **Semantic Join实现**: 
   - ✅ 使用NumPy/MKL加速的向量化计算
   - ✅ 或者调用SageVDB的C++接口（batch similarity）
   - ❌ 避免纯Python循环计算相似度
2. **Embedding超级批量**: batch_size=64-128（减少网络往返）
3. **Join窗口降级**: 考虑40s窗口（1000 docs）而不是60s
4. **KeyBy超并行**: parallelism=32（超配，利用Ray的任务窃取）
5. **GPU调度优化**:
   - LLM批量推理：优先级高
   - Rerank：可以CPU fallback（轻量模型）
6. **内存预分配**: 提前分配Join window buffer避免动态分配

**降级方案**:
如果性能不达标，可以调整：
- QPS: 40→30, 25→20（降低25%负载）
- Join Window: 60s→40s（减少33%状态）
- Batch Size: 12→8（降低GPU压力）
- Parallelism: 16→32（增加并行度）

**结论**:
- ✅ CPU理论充足（1.92%理论利用率，5-10%实际）
- ✅ 内存绝对充足（1.44GB << 256GB）
- ⚠️ **需要优化Semantic Join实现**（NumPy/C++）
- ⚠️ **需要监控GPU利用率**（LLM + Rerank竞争）
- ⚠️ **需要激进的Embedding批量**（batch_size=64-128）
- ⏱️ 预计P50延迟: 1000-1500ms（如果优化得当）
- ⏱️ 预计P99延迟: 2500-3500ms

### 整体结论

✅ **可以完成所有4个Workload实验**

**前提条件**:
1. ✅ Semantic Join使用NumPy向量化或SageVDB C++接口
2. ✅ Embedding远程调用使用大批量（batch_size=32-128）
3. ✅ GPU资源管理良好（LLM + Rerank不冲突）
4. ⚠️ Workload 4可能需要参数微调（降级QPS或窗口）

**推荐实验顺序**:
1. **Stage 1**: Workload 1（验证基础设施，1天）
2. **Stage 2**: Workload 2（验证并行Join，2天）
3. **Stage 3**: Workload 3（验证Semantic Join优化，3天）
4. **Stage 4**: Workload 4（极限压测，4天 + 调优）

**关键监控指标**:
- CPU利用率per node（应该均衡，±5%以内）
- Join算子延迟（Workload 3/4关键瓶颈）
- Embedding批量调用延迟（网络往返次数）
- GPU利用率（LLM推理 + Rerank）
- 内存使用（Join window状态）

**如果遇到性能瓶颈**:
- Semantic Join慢 → 使用C++ SIMD优化或降低窗口
- Embedding慢 → 增加batch_size到128
- GPU冲突 → Rerank改用CPU（轻量distilbert）
- 内存不足 → 减小Join窗口或增加分区数

---

## 总结

本文档设计了4个递进式的**分布式CPU密集型**工作负载，充分利用SAGE的：

1. **丰富的算子生态**: KeyBy、Join、Batch、Filter等
2. **分布式调度能力**: 自动并行、负载均衡、容错恢复
3. **灵活的Pipeline构建**: 多路并行、嵌套Join、多层聚合

通过逐步增加复杂度（从30% CPU到95% CPU），可以全面测试SAGE在：
- **高并发场景** (40 QPS双流输入)
- **大窗口Join** (60s窗口，1500文档)
- **复杂计算** (61.4M ops/s向量计算)
- **多阶段处理** (4-stage检索、3-stage重排序)

方面的性能和调度效率，为Benchmark论文提供充分的实验数据。

**硬件配置**: 1台A6000 + 16容器（8核16GB）完全可以支撑所有实验，但Workload 4需要精心优化。

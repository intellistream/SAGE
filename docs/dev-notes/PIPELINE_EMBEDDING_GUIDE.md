# Pipeline Builder Embedding 增强指南

## 概述

Pipeline Builder 现已集成 EmbeddingService，提供了强大的模板化 pipeline 创建能力。支持 11 种 embedding 方法和 4 个预定义模板，可快速构建生产级 RAG 和知识库系统。

## 快速开始

### 1. 分析 Embedding 方法

在构建 pipeline 前，先分析哪种 embedding 方法最适合你的场景：

```bash
# 测试默认方法（hash, mockembedder, hf）
sage pipeline analyze-embedding "如何构建 RAG pipeline"

# 对比特定方法
sage pipeline analyze-embedding "向量检索" -m hash -m openai -m hf

# 显示详细的向量信息
sage pipeline analyze-embedding "知识库构建" -m openai --show-vectors

# 调整返回结果数量
sage pipeline analyze-embedding "文档分块" -k 5
```

输出示例：
```
🔍 查询: 如何构建 RAG pipeline
📊 对比方法: hash, openai, hf
📚 知识库: SAGE Pipeline Builder

⚙️  测试方法: hash
   ✓ 检索完成 (耗时: 5.23ms, 维度: 128)

━━━ HASH ━━━
⏱️  耗时: 5.23ms | 📐 维度: 128
排名  得分      类型      文本片段
#1    0.8234   example   使用 RAG 检索增强生成...
#2    0.7891   code      class RAGPipeline...
#3    0.7456   doc       Pipeline Builder 支持...

💡 推荐建议:
⚡ 最快方法: hash (5.23ms)
🎯 最相关方法: openai (平均得分: 0.8456)

💡 使用推荐方法: sage pipeline build --embedding-method openai
```

### 2. 创建基于模板的 Pipeline

使用 `create-embedding` 命令快速创建 pipeline：

```bash
# RAG Pipeline（使用 HuggingFace）
sage pipeline create-embedding \
  --template rag \
  --embedding-method hf \
  --embedding-model BAAI/bge-small-zh-v1.5 \
  --llm-model Qwen/Qwen2.5-7B-Instruct

# 知识库构建（使用 vLLM 高性能）
sage pipeline create-embedding \
  --template knowledge-base \
  --vllm \
  --batch-size 256

# 混合检索（Dense + Sparse）
sage pipeline create-embedding \
  --template hybrid-search \
  --dense-method openai \
  --dense-model text-embedding-3-small \
  --sparse-method bm25s

# 多策略智能路由
sage pipeline create-embedding \
  --template multi-strategy \
  --query-method hash \
  --doc-method openai \
  --batch-method vllm
```

### 3. 交互式配置

使用 `-i/--interactive` 标志启动交互式向导：

```bash
sage pipeline create-embedding -i
```

向导会逐步引导你配置：
- 模板类型
- Embedding 方法和模型
- 是否使用 vLLM
- 模板特定参数（如 LLM 模型、混合检索方法等）

### 4. 运行生成的 Pipeline

```bash
# 保存后会提示运行命令
sage pipeline run output/pipelines/my-rag-pipeline.yaml

# 自动停止（批处理模式）
sage pipeline run config.yaml --autostop

# 持续运行（流式模式）
sage pipeline run config.yaml --no-autostop
```

## 模板详解

### 1. RAG Template (`rag`)

**用途**: 完整的检索增强生成系统

**特点**:
- 文档加载 → 分块 → Embedding → 向量索引 → 检索 → LLM 生成
- 支持所有 embedding 方法
- 集成 VLLMService 用于 LLM 生成
- 可选 vLLM embedding（高性能）

**参数**:
```bash
--embedding-method    # Embedding 方法（必需）
--embedding-model     # Embedding 模型名称
--llm-model           # LLM 模型名称（默认 Qwen/Qwen2.5-7B-Instruct）
--vllm                # 使用 vLLM embedding
--chunk-size          # 分块大小（默认 512）
--chunk-overlap       # 分块重叠（默认 50）
--batch-size          # 批处理大小（默认 32）
--cache/--no-cache    # 是否缓存（默认启用）
--normalize           # 向量归一化（默认启用）
```

**生成的配置结构**:
```yaml
pipeline:
  name: rag-with-embedding-service
  description: RAG pipeline powered by EmbeddingService
  type: local

services:
  - name: embedding-service
    class: sage.middleware.components.sage_embedding.service.EmbeddingService
    params:
      method: hf
      model_name: BAAI/bge-small-zh-v1.5
      cache_embeddings: true
      normalize: true

  - name: vllm-service
    class: sage.common.components.sage_vllm.service.VLLMService
    params:
      model_name: Qwen/Qwen2.5-7B-Instruct

stages:
  - id: load-documents
    kind: batch
    class: sage.libs.rag.loader.DirectoryLoader
    
  - id: chunk-documents
    kind: map
    class: sage.libs.rag.chunker.RecursiveCharacterTextSplitter
    params:
      chunk_size: 512
      chunk_overlap: 50
      
  - id: embed-documents
    kind: service
    class: embedding-service
    params:
      batch_size: 32
      
  - id: index-vectors
    kind: map
    class: sage.middleware.components.sage_db.service.SageDBService
    
  - id: retrieve
    kind: map
    class: sage.libs.rag.retriever.VectorRetriever
    params:
      top_k: 5
      
  - id: generate
    kind: service
    class: vllm-service
```

### 2. Knowledge Base Builder Template (`knowledge-base`)

**用途**: 大规模知识库构建和索引

**特点**:
- 优化批处理吞吐量
- 支持超大 batch size（vLLM 可达 512）
- 禁用缓存以节省内存
- 并行处理优化

**参数**:
```bash
--embedding-method    # Embedding 方法
--embedding-model     # Embedding 模型
--vllm                # 使用 vLLM（强烈推荐，支持 512 batch）
--chunk-size          # 分块大小（默认 512）
--chunk-overlap       # 分块重叠（默认 50）
--batch-size          # 批处理大小（默认 128，vLLM 可用 512）
```

**适用场景**:
- 索引大量文档（百万级）
- 离线批量处理
- 高吞吐量要求
- 内存受限环境（禁用缓存）

**性能优化**:
- vLLM: 512 batch size, ~10,000 docs/min
- HuggingFace: 128 batch size, ~2,000 docs/min
- OpenAI: 64 batch size, ~1,000 docs/min

### 3. Hybrid Search Template (`hybrid-search`)

**用途**: Dense + Sparse 混合检索

**特点**:
- 同时使用 Dense 和 Sparse embedding
- Reciprocal Rank Fusion 融合策略
- 双向量数据库
- 提升检索准确率

**参数**:
```bash
--dense-method        # Dense embedding 方法（如 openai, hf）
--dense-model         # Dense 模型名称
--sparse-method       # Sparse embedding 方法（默认 bm25s）
--batch-size          # 批处理大小
--normalize           # Dense 向量归一化
```

**生成的配置结构**:
```yaml
stages:
  # Dense 路径
  - id: embed-dense
    class: embedding-service-dense
    params:
      method: openai
      model_name: text-embedding-3-small
      normalize: true
      
  - id: index-dense
    class: sage.middleware.components.sage_db.service.SageDBService
    params:
      collection_name: dense_vectors
      
  # Sparse 路径
  - id: embed-sparse
    class: embedding-service-sparse
    params:
      method: bm25s
      
  - id: index-sparse
    class: sage.middleware.components.sage_db.service.SageDBService
    params:
      collection_name: sparse_vectors
      
  # 融合
  - id: hybrid-retrieval
    class: sage.libs.rag.retriever.HybridRetriever
    params:
      fusion_strategy: reciprocal_rank
      dense_weight: 0.7
      sparse_weight: 0.3
```

**使用建议**:
- Dense: 语义相似度（openai, hf 等）
- Sparse: 关键词匹配（bm25s）
- 权重调整: `dense_weight=0.7, sparse_weight=0.3`（可自定义）

### 4. Multi-Strategy Template (`multi-strategy`)

**用途**: 智能路由多 embedding 策略

**特点**:
- 针对不同场景使用不同 embedding
- 查询：快速 embedding（hash, mockembedder）
- 文档：高质量 embedding（openai, hf）
- 批量：高性能 embedding（vllm）

**参数**:
```bash
--query-method        # 查询用 embedding（默认 hash）
--doc-method          # 文档用 embedding（默认 hf）
--batch-method        # 批量处理用 embedding（默认 vllm）
```

**路由逻辑**:
```yaml
stages:
  - id: router
    kind: map
    class: sage.libs.rag.router.EmbeddingRouter
    params:
      routes:
        - condition: "input.type == 'query'"
          service: embedding-service-fast
          
        - condition: "input.type == 'document'"
          service: embedding-service-quality
          
        - condition: "input.type == 'batch'"
          service: embedding-service-batch
```

**典型场景**:
- **实时查询**: `hash` (< 1ms) → 即时响应
- **离线索引**: `openai` → 高质量向量
- **大规模批处理**: `vllm` → 高吞吐量

**性能对比**:
| 方法 | 延迟 | 吞吐量 | 质量 | 成本 |
|------|------|--------|------|------|
| hash | < 1ms | 100k/s | ⭐⭐ | 免费 |
| openai | ~50ms | 100/s | ⭐⭐⭐⭐⭐ | $$ |
| vllm | ~10ms | 10k/s | ⭐⭐⭐⭐ | 免费 |

## Embedding 方法选择指南

### 1. 本地方法（免费）

#### Hash Embedding
```bash
--embedding-method hash
```
- **速度**: ⚡⚡⚡⚡⚡ (< 1ms)
- **质量**: ⭐⭐
- **用途**: 原型开发、快速查询、冷启动
- **限制**: 语义理解能力弱

#### MockEmbedder
```bash
--embedding-method mockembedder
```
- **速度**: ⚡⚡⚡⚡⚡
- **质量**: ⭐
- **用途**: 测试、占位符
- **限制**: 随机向量，无实际检索能力

#### HuggingFace
```bash
--embedding-method hf --embedding-model BAAI/bge-small-zh-v1.5
```
- **速度**: ⚡⚡⚡ (10-50ms)
- **质量**: ⭐⭐⭐⭐
- **用途**: 中文检索、本地部署
- **推荐模型**:
  - 中文: `BAAI/bge-small-zh-v1.5`, `BAAI/bge-large-zh-v1.5`
  - 英文: `sentence-transformers/all-MiniLM-L6-v2`
  - 多语言: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

### 2. 云 API 方法

#### OpenAI
```bash
--embedding-method openai --embedding-model text-embedding-3-small
```
- **速度**: ⚡⚡⚡ (20-100ms)
- **质量**: ⭐⭐⭐⭐⭐
- **用途**: 高质量检索、英文优先
- **模型**:
  - `text-embedding-3-small`: 性价比高
  - `text-embedding-3-large`: 质量最佳
  - `text-embedding-ada-002`: 稳定版本

#### Jina AI
```bash
--embedding-method jina --embedding-model jina-embeddings-v2-base-zh
```
- **速度**: ⚡⚡⚡
- **质量**: ⭐⭐⭐⭐
- **用途**: 多语言、长文本（8192 tokens）
- **特点**: 支持超长上下文

#### 其他云服务
- **智谱 AI**: `--embedding-method zhipu`
- **Cohere**: `--embedding-method cohere`
- **AWS Bedrock**: `--embedding-method bedrock`
- **Ollama**: `--embedding-method ollama`
- **硅基流动**: `--embedding-method siliconcloud`
- **NVIDIA OpenAI**: `--embedding-method nvidia_openai`

### 3. 高性能方法

#### vLLM
```bash
--vllm
```
- **速度**: ⚡⚡⚡⚡ (5-20ms)
- **质量**: ⭐⭐⭐⭐
- **用途**: 大规模批处理、本地高性能
- **特点**:
  - 批处理大小可达 512
  - GPU 加速
  - 支持流式处理
  - 免费本地部署

**性能对比**:
```bash
# 单次请求
hash:    0.5ms
vllm:    10ms
hf:      30ms
openai:  50ms

# 批处理 1000 条（batch_size=128）
hash:     5ms   (200k docs/s)
vllm:    80ms   (12.5k docs/s)
hf:     400ms   (2.5k docs/s)
openai: 1000ms  (1k docs/s)
```

## 高级配置

### 1. 自定义批处理大小

```bash
# 小批量（低延迟）
--batch-size 16

# 中批量（平衡）
--batch-size 64

# 大批量（高吞吐）
--batch-size 256

# vLLM 超大批量
--batch-size 512 --vllm
```

### 2. 缓存策略

```bash
# 启用缓存（查询场景）
--cache

# 禁用缓存（索引场景，节省内存）
--no-cache
```

### 3. 向量归一化

```bash
# 启用归一化（提升余弦相似度计算效率）
--normalize

# 禁用归一化
--no-normalize
```

### 4. 文档分块优化

```bash
# 小分块（精细检索）
--chunk-size 256 --chunk-overlap 25

# 中分块（平衡）
--chunk-size 512 --chunk-overlap 50

# 大分块（长上下文）
--chunk-size 1024 --chunk-overlap 100
```

## 实战示例

### 示例 1: 快速原型 RAG

```bash
# 使用 hash 快速启动
sage pipeline create-embedding \
  -t rag \
  -e hash \
  --llm-model Qwen/Qwen2.5-7B-Instruct \
  -o prototypes/quick-rag.yaml

sage pipeline run prototypes/quick-rag.yaml
```

### 示例 2: 生产级中文 RAG

```bash
# HuggingFace + vLLM
sage pipeline create-embedding \
  -t rag \
  -e hf \
  -m BAAI/bge-large-zh-v1.5 \
  --vllm \
  --llm-model Qwen/Qwen2.5-14B-Instruct \
  --batch-size 64 \
  --normalize \
  -o production/chinese-rag.yaml
```

### 示例 3: 高质量英文 RAG

```bash
# OpenAI embedding + vLLM generation
sage pipeline create-embedding \
  -t rag \
  -e openai \
  -m text-embedding-3-large \
  --llm-model meta-llama/Llama-3.1-70B-Instruct \
  --batch-size 32 \
  -o production/english-rag.yaml
```

### 示例 4: 大规模知识库索引

```bash
# vLLM 高性能批处理
sage pipeline create-embedding \
  -t knowledge-base \
  --vllm \
  --batch-size 512 \
  --chunk-size 512 \
  --no-cache \
  -o indexing/large-kb.yaml
```

### 示例 5: 混合检索系统

```bash
# Dense (OpenAI) + Sparse (BM25s)
sage pipeline create-embedding \
  -t hybrid-search \
  --dense-method openai \
  --dense-model text-embedding-3-small \
  --sparse-method bm25s \
  --normalize \
  -o retrieval/hybrid.yaml
```

### 示例 6: 智能多策略路由

```bash
# 查询用 hash，文档用 OpenAI，批量用 vLLM
sage pipeline create-embedding \
  -t multi-strategy \
  --query-method hash \
  --doc-method openai \
  --batch-method vllm \
  -o advanced/multi-strategy.yaml
```

### 示例 7: 交互式配置

```bash
# 启动向导
sage pipeline create-embedding -i
```

输出示例:
```
🎯 交互式 Embedding Pipeline 配置向导

选择模板类型 [rag]: hybrid-search
Embedding 方法 (hf/openai/jina/...): openai
Embedding 模型名称: text-embedding-3-small
使用 vLLM 服务? [y/N]: n
Dense embedding 方法 [openai]: openai
Sparse embedding 方法 [bm25s]: bm25s

📋 模板: hybrid-search
🔧 Embedding: openai
🚀 vLLM: False

[生成配置...]
[显示预览...]

保存配置? [Y/n]: y
✅ 配置已保存到: /home/user/SAGE/output/pipelines/hybrid-search-pipeline.yaml

💡 运行此 pipeline:
   sage pipeline run /home/user/SAGE/output/pipelines/hybrid-search-pipeline.yaml
```

## 最佳实践

### 1. 开发流程

```bash
# Step 1: 分析 embedding 方法
sage pipeline analyze-embedding "测试查询" -m hash -m hf -m openai

# Step 2: 选择最佳方法，创建 pipeline
sage pipeline create-embedding -t rag -e openai -o dev/rag.yaml

# Step 3: 测试运行
sage pipeline run dev/rag.yaml --autostop

# Step 4: 优化参数后部署
sage pipeline create-embedding -t rag -e openai \
  --batch-size 64 \
  --normalize \
  -o production/rag.yaml --overwrite
```

### 2. 性能优化

- **低延迟场景**: 使用 `hash` 或 `vllm`
- **高质量场景**: 使用 `openai` 或 `hf` 大模型
- **大规模批处理**: 使用 `vllm` + 大 batch size
- **混合检索**: 结合 dense 和 sparse 方法

### 3. 成本优化

- **免费方案**: `hash` + `hf` + `vllm`
- **低成本方案**: `hash` (查询) + `openai text-embedding-3-small` (索引)
- **高质量方案**: `openai text-embedding-3-large` + GPT-4

### 4. 错误排查

```bash
# 检查 embedding 方法是否可用
sage pipeline analyze-embedding "test" -m <method>

# 查看生成的配置
sage pipeline create-embedding -t rag -e hf --output test.yaml
cat test.yaml

# 验证配置（dry run）
sage pipeline run test.yaml --help
```

## 常见问题

### Q: 如何选择 embedding 方法？

A: 根据场景选择：
- 原型开发 → `hash`
- 中文检索 → `hf` (BAAI/bge-*)
- 英文检索 → `openai` (text-embedding-3-*)
- 高性能 → `vllm`
- 多语言 → `jina`

### Q: vLLM 和 HuggingFace 有什么区别？

A: 
- **vLLM**: GPU 加速，批处理优化，吞吐量高
- **HuggingFace**: CPU/GPU 均可，灵活性高，模型丰富

### Q: 混合检索什么时候使用？

A: 当你需要同时匹配语义和关键词时，例如：
- 专业术语检索
- 法律文档搜索
- 代码搜索

### Q: 如何调优批处理大小？

A: 
- GPU 内存充足 → 大 batch (256-512)
- 低延迟要求 → 小 batch (16-32)
- 平衡方案 → 中 batch (64-128)

### Q: 缓存何时启用？

A: 
- **启用**: 重复查询场景（在线检索）
- **禁用**: 批量索引场景（节省内存）

## 进阶主题

### 1. 自定义 Embedding Service 参数

编辑生成的 YAML，添加更多参数：

```yaml
services:
  - name: embedding-service
    class: sage.middleware.components.sage_embedding.service.EmbeddingService
    params:
      method: hf
      model_name: BAAI/bge-large-zh-v1.5
      cache_embeddings: true
      normalize: true
      # 自定义参数
      device: cuda:0
      max_seq_length: 512
      pooling_mode: mean
```

### 2. 集成到现有 Pipeline

将 EmbeddingService 添加到现有配置：

```yaml
services:
  # 添加 embedding service
  - name: my-embedding
    class: sage.middleware.components.sage_embedding.service.EmbeddingService
    params:
      method: openai
      model_name: text-embedding-3-small

stages:
  # 使用 service
  - id: embed
    kind: service
    class: my-embedding
    params:
      batch_size: 64
```

### 3. 多模型组合

```yaml
services:
  # 查询用快速模型
  - name: query-embedding
    class: sage.middleware.components.sage_embedding.service.EmbeddingService
    params:
      method: hash
      
  # 文档用高质量模型
  - name: doc-embedding
    class: sage.middleware.components.sage_embedding.service.EmbeddingService
    params:
      method: openai
      model_name: text-embedding-3-large
```

## 总结

Pipeline Builder 的 Embedding 增强提供了：

1. **4 个生产级模板**: RAG, Knowledge Base, Hybrid Search, Multi-Strategy
2. **11 种 embedding 方法**: 从免费 hash 到高质量 OpenAI
3. **智能分析工具**: `analyze-embedding` 帮助选择最佳方法
4. **一键生成**: 简单命令即可创建完整配置
5. **灵活扩展**: 支持自定义参数和多服务组合

开始使用：

```bash
# 分析你的场景
sage pipeline analyze-embedding "你的查询"

# 创建 pipeline
sage pipeline create-embedding -t rag -e <推荐方法>

# 运行
sage pipeline run output/pipelines/your-pipeline.yaml
```

Happy building! 🚀

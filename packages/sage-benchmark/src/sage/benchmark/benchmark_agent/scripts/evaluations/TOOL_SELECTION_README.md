# Tool Selection Benchmark (Challenge 3) - 实现说明

## 概述

本实现完成了 SAGE Agent Benchmark 中「工具选择」(Tool Selection) 挑战的端到端评测流程。 目标：从 1000+ 工具中准确选择相关工具，Top-K 准确率达到
≥95%。

## 文件结构

```
packages/sage-benchmark/
├── scripts/                                    # [新建] 独立验证脚本
│   ├── prepare_tool_selection_data.py         # 数据准备和验证脚本
│   └── test_tool_selection_e2e.py             # 端到端测试脚本
│
└── src/sage/
    ├── data/sources/
    │   ├── agent_tools/data/
    │   │   └── tool_catalog.jsonl             # [已有] 1200 个工具定义
    │   └── agent_benchmark/splits/
    │       └── tool_selection.jsonl           # [已有] 500 条评测样本
    │
    └── benchmark/benchmark_agent/
        ├── experiments/
        │   └── tool_selection_exp.py          # [修改] 添加 embedding client 支持
        ├── evaluation/
        │   └── metrics.py                     # [已有] top_k_accuracy, recall, mrr 等
        └── adapter_registry.py                # [修改] 添加 hybrid selector 支持

packages/sage-libs/
└── src/sage/libs/agentic/agents/action/tool_selection/
    ├── __init__.py                            # [修改] 注册 HybridSelector
    └── hybrid_selector.py                     # [新建] 混合策略选择器
```

## 数据状态

- ✅ 工具库：1200 个工具 (超过目标 1000+)
- ✅ 评测样本：500 条 (train: 350, dev: 75, test: 75)
- ✅ 难度分布：easy 200, medium 200, hard 100
- ✅ 候选工具数：7-14 个/样本

## 策略实现

### 1. Keyword Selector (`selector.keyword`)

- 基于 BM25/TF-IDF 的关键词匹配
- 支持 n-gram 和停用词过滤
- 复杂度：O(N)

### 2. Embedding Selector (`selector.embedding`)

- 基于向量相似度的语义匹配
- 支持多种 embedding 模型（OpenAI, HF, 本地等）
- 使用向量索引加速检索

### 3. Hybrid Selector (`selector.hybrid`)

- 结合 Keyword + Embedding 的混合策略
- 支持多种融合方法：weighted_sum, max, reciprocal_rank
- 默认权重：keyword 40%, embedding 60%

## 使用方法

### 数据验证

```bash
cd /home/shuhao/SAGE
python packages/sage-benchmark/scripts/prepare_tool_selection_data.py --validate
```

### 运行测试

```bash
# 快速测试 (20 样本)
python packages/sage-benchmark/scripts/test_tool_selection_e2e.py --quick

# 标准测试 (100 样本)
python packages/sage-benchmark/scripts/test_tool_selection_e2e.py

# 完整测试 + 可视化
python packages/sage-benchmark/scripts/test_tool_selection_e2e.py --visualize --max-samples 200
```

### 生成更多数据

```bash
# 生成额外 500 条样本
python packages/sage-benchmark/scripts/prepare_tool_selection_data.py --generate --samples 500

# 创建不同候选数量的数据集
python packages/sage-benchmark/scripts/prepare_tool_selection_data.py --create-splits --num-candidates 100,500,1000
```

## 评测指标

| 指标           | 说明                       | 目标 |
| -------------- | -------------------------- | ---- |
| top_k_accuracy | Top-K 中包含正确答案的比例 | ≥95% |
| recall_at_k    | 召回率                     | -    |
| precision_at_k | 精确率                     | -    |
| mrr            | Mean Reciprocal Rank       | -    |

## 当前结果

使用 mock embedder 进行测试（随机向量）：

- Keyword: ~40-60% accuracy
- Embedding: ~65-70% accuracy
- Hybrid: ~40-60% accuracy

**注意**：使用真实 embedding 模型（如 HuggingFace 本地模型）可以显著提升准确率。

## 配置说明

### Embedding 配置（环境变量）

```bash
# 使用本地 HuggingFace 模型（推荐）
export SAGE_EMBEDDING_METHOD=hf
export SAGE_EMBEDDING_MODEL="BAAI/bge-small-zh-v1.5"

# 或使用轻量测试模型
export SAGE_EMBEDDING_METHOD=hash
```

支持的 embedding 方法：

- `hf` - HuggingFace 本地模型（推荐，高质量）
- `hash` - 轻量哈希嵌入（测试用）
- `mockembedder` - 随机向量（单元测试）
- `openai`, `jina`, `zhipu`, `cohere` 等云端 API

### 本地 LLM Rerank（可选，推荐）

Hybrid Selector 支持使用 LLM 进行重排序，可显著提升准确率。使用 `IntelligentLLMClient.create_auto()` 实现**本地优先 + 云端回退**策略：

1. **优先检测本地 vLLM** (localhost:8001, localhost:8000)
1. **本地不可用时**自动回退到云端 API (需配置 SAGE_CHAT_API_KEY)

**启动本地 LLM 服务（推荐，可节省 API 成本）：**

```bash
# 方式1: 使用 sage CLI
sage apps llm start --model "Qwen/Qwen2.5-0.5B-Instruct" --port 8001

# 方式2: 使用 sage studio (包含完整服务)
sage studio start

# 方式3: 直接使用 vLLM
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8001
```

**启用 LLM Rerank 并运行测试：**

```bash
# 启用 LLM rerank（会自动检测本地服务，本地不可用则用云端）
export SAGE_HYBRID_ENABLE_LLM_RERANK=1

# 运行测试 - 一键运行！
python packages/sage-benchmark/scripts/test_tool_selection_e2e.py --quick
```

**设计原则**：

- 本地优先：自动检测并使用本地 vLLM 服务（sageLLM 提供）
- 云端回退：本地不可用时自动使用云端 API（需配置 SAGE_CHAT_API_KEY）
- 静默降级：如果既无本地服务也无云端配置，静默跳过 LLM rerank

## 下一步优化

1. **使用真实 Embedding 模型**

   ```bash
   export SAGE_EMBEDDING_METHOD=hf
   export SAGE_EMBEDDING_MODEL="BAAI/bge-small-zh-v1.5"
   ```

   - 预期可提升到 85%+

1. **启用本地 LLM Rerank**

   ```bash
   # 先启动本地 vLLM 服务
   sage apps llm start --model "Qwen/Qwen2.5-0.5B-Instruct" --port 8001

   # 启用 LLM rerank
   export SAGE_HYBRID_ENABLE_LLM_RERANK=1
   ```

   - 使用 fine-tuned sageLLM 模型
   - 预期可达到 95%+ 目标

1. **优化 Hybrid 策略**

   - 调整 keyword/embedding 权重
   - 使用 RRF 融合方法

1. **扩展数据集**

   - 增加更多样本多样性
   - 添加更复杂的指令

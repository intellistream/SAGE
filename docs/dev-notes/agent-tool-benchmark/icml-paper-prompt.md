# ICML 2026 论文生成提示词

> 请将此提示词发送给 Claude/GPT-4 以生成完整的 LaTeX 论文

---

请帮我撰写一篇完整的 ICML 2026 论文，使用 LaTeX 格式。

## 论文信息

**标题**: SAGE-Bench: A Unified Benchmark for Evaluating Agent Capabilities in Tool-Augmented LLMs

**作者**: [待填写]

**会议**: ICML 2026

## 核心贡献

1. **统一评测框架**: 提出首个同时评估 Timing/Planning/Tool Selection 三维度的 Agent 能力基准
2. **高质量数据集**: 1,200 条标注样本 + 1,200 个工具目录，覆盖 25+ 领域；集成 ACEBench、API-Bank、ToolAlpaca 等外部数据集
3. **全面的 Baseline 对比**: 实现并评估 15+ 种方法（含训练方法），揭示当前 SOTA 的不足
4. **端到端训练框架**: 支持 SFT + RL (DPO/PPO/GRPO) + Coreset Selection + Continual Learning

## 问题定义

现有 benchmark 各自为战：
- BFCL (Berkeley): 只测 function calling syntax
- ToolBench (Tsinghua): 只测 tool retrieval
- API-Bank (Microsoft): 只测 API selection

**Gap**: 缺少统一框架同时评估 Agent 的三个核心能力：
1. **Timing Judgment**: 何时调用工具 vs 直接回答
2. **Task Planning**: 如何分解复杂任务为多步计划
3. **Tool Selection**: 从 1000+ 工具中选择正确工具

## 数据集详情

### 统计信息

| Task | Total | Train | Dev | Test |
|------|-------|-------|-----|------|
| Tool Selection | 600 | 420 | 90 | 90 |
| Task Planning | 300 | 210 | 45 | 45 |
| Timing Judgment | 300 | 210 | 45 | 45 |
| **Total** | **1,200** | 840 | 180 | 180 |

### 外部数据集集成

| Dataset | Source | Samples | Focus |
|---------|--------|---------|-------|
| **ACEBench (ToolACE)** | HuggingFace Team-ACE | 10,000+ | Tool selection with real APIs |
| **API-Bank** | Microsoft/Alibaba | 2,138 | Multi-turn API dialogues |
| **ToolAlpaca** | Microsoft | 3,928 | Tool learning conversations |
| **BFCL** | Berkeley | 2,000+ | Function calling syntax |
| **ToolBench** | Tsinghua/OpenBMB | 16,000+ | Large-scale tool retrieval |

### 工具目录
- 1,200 unique tools
- 25 categories: environment/weather, finance/payment, travel/booking, ai/vision, security/auth, data/analytics, etc.
- 每个工具包含: name, category, capabilities, inputs/outputs schema, invoke_examples, reliability_score, latency_ms

### 数据格式示例

#### Tool Selection Sample
```json
{
  "sample_id": "ts_000002",
  "instruction": "What's the weather in Paris?",
  "candidate_tools": ["environment_geography_014", "environment_weather_001", "finance_payment_024", ...],
  "ground_truth": {
    "top_k": ["environment_weather_001"],
    "explanation": "Weather query requires weather API"
  }
}
```

#### Task Planning Sample
```json
{
  "sample_id": "tp_000001",
  "instruction": "Book a flight to Tokyo and hotel for 3 nights",
  "candidate_tools": ["travel_flight_search", "travel_flight_book", "travel_hotel_search", ...],
  "ground_truth": {
    "plan_steps": [
      {"step_id": 1, "description": "Search available flights to Tokyo", "tool_id": "travel_flight_search"},
      {"step_id": 2, "description": "Book selected flight", "tool_id": "travel_flight_book"},
      {"step_id": 3, "description": "Search hotels in Tokyo", "tool_id": "travel_hotel_search"},
      {"step_id": 4, "description": "Book hotel for 3 nights", "tool_id": "travel_hotel_book"},
      {"step_id": 5, "description": "Confirm booking", "tool_id": "travel_booking_confirm"}
    ]
  }
}
```

#### Timing Judgment Sample
```json
{
  "sample_id": "tj_000001",
  "instruction": "What's the current time in Tokyo?",
  "ground_truth": {
    "should_call_tool": true,
    "reasoning": "Need to query time zone database or world clock API for real-time data"
  }
}
{
  "sample_id": "tj_000002",
  "instruction": "What is 2 + 2?",
  "ground_truth": {
    "should_call_tool": false,
    "direct_answer": "4",
    "reasoning": "Basic arithmetic, can answer directly without calculator"
  }
}
```

## 实现的方法（Baselines）

### Challenge 1: Timing Judgment Methods

| Method | Description | Reference |
|--------|-------------|-----------|
| **Rule-based** | Keyword matching + heuristic rules (检测 "current", "latest", "real-time" 等关键词) | - |
| **LLM-based** | 直接用 LLM 判断是否需要工具 | - |
| **Hybrid** | Rule 初筛 + LLM 精判，结合两者优势 | - |

### Challenge 2: Task Planning Methods

| Method | Description | Reference |
|--------|-------------|-----------|
| **Simple (Greedy)** | 贪心选择，每步选当前最匹配的工具 | - |
| **Hierarchical** | 层次规划，先分解子目标再逐个规划 | - |
| **LLM-based** | 直接用 LLM 生成完整计划 | - |
| **ReAct** | Reasoning + Acting 交替迭代 | Yao et al., 2023 |
| **Tree-of-Thoughts (ToT)** | 树搜索探索多个规划路径 | Yao et al., 2023 |

### Challenge 3: Tool Selection Methods

| Method | Description | Reference |
|--------|-------------|-----------|
| **Keyword (TF-IDF)** | 基于词频的稀疏检索 | - |
| **Keyword (BM25)** | BM25 改进的关键词匹配 | Robertson et al. |
| **Embedding** | 语义向量相似度 (BGE-M3) | BAAI |
| **Hybrid** | Keyword + Embedding 加权融合 (RRF) | - |
| **LLM Direct** | 直接用 LLM 从候选中选择 | - |
| **Gorilla-style** | 两阶段: Embedding 检索 + LLM 重排序 | Patil et al., 2023 |
| **DFSDT** | 深度优先搜索 + LLM 评分 + 多样性 prompting | Qin et al., 2023 (ToolLLM) |
| **Two-Stage** | Coarse (keyword) + Fine (embedding/LLM) | - |
| **Adaptive** | Multi-armed bandit 动态选择策略 | - |

### Training Methods (数据高效训练)

| Method | Description | Reference |
|--------|-------------|-----------|
| **SFT + LoRA** | 低秩适配微调 | Hu et al., 2022 |
| **SFT + DoRA** | 权重分解低秩适配 | Liu et al., 2024 |
| **SFT + LoRA+** | 差异化学习率的 LoRA | Hayou et al., 2024 |
| **Coreset Selection** | 基于 loss/diversity/hybrid 的样本筛选 | - |
| **Continual Learning** | 在线增量学习 + 经验回放 | - |
| **DPO** | Direct Preference Optimization | Rafailov et al., 2023 |
| **PPO** | Proximal Policy Optimization | Schulman et al., 2017 |
| **GRPO** | Group Relative Policy Optimization | Shao et al., 2024 |

#### Coreset Selection Strategies
```python
# 实现位置: sage-libs/src/sage/libs/finetune/agent/continual.py
class CoresetSelector:
    strategies = ["loss_topk", "diversity", "hybrid", "random"]
    # loss_topk: 选择 loss 最高的样本
    # diversity: 最大化样本多样性 (基于文本特征的余弦距离)
    # hybrid: 60% loss + 40% diversity
```

#### Continual Learning
```python
# 实现位置: sage-libs/src/sage/libs/finetune/agent/continual.py
class OnlineContinualLearner:
    # 维护经验回放缓冲区
    # 每次训练混合新样本 + 历史样本
    # 支持 reservoir sampling 动态更新
```

## 实验结果

### Challenge 1: Timing Judgment (Target: ≥95%)

| Method | Accuracy | Precision | Recall | F1 |
|--------|----------|-----------|--------|-----|
| Rule-based | **76.0%** | 94.4% | 60.7% | 73.9% |
| LLM-based (Qwen-7B) | 72.0% | 85.0% | 65.0% | 73.7% |
| Hybrid | 74.0% | 90.0% | 62.0% | 73.4% |

**Insights**:
- Rule-based 在 no-tool cases 上表现优秀 (95.5% accuracy)
- 但在 tool-needed cases 上 recall 低 (60.7%)，漏判较多
- LLM-based 更平衡但整体略低
- **Gap to target: -19%**

### Challenge 2: Task Planning (Target: ≥90%)

| Method | Plan Success Rate | Step Accuracy | Sequence Match |
|--------|-------------------|---------------|----------------|
| Simple (Greedy) | 20.0% | 58.0% | 20.0% |
| Hierarchical | **26.7%** | 59.0% | 26.7% |
| LLM-based (Qwen-7B) | 23.3% | 55.0% | 23.3% |
| ReAct | 25.0% | 57.0% | 25.0% |
| Tree-of-Thoughts | 28.0% | 60.0% | 28.0% |

**Insights**:
- 多步规划是最难的挑战
- 即使 ToT 也只有 28% 成功率
- Step-level 准确率 ~58% 说明单步选择尚可，但序列组合出错
- **Gap to target: -63%**

### Challenge 3: Tool Selection (Target: ≥95%)

| Method | Top-5 Acc | Top-1 Acc | MRR | Recall@5 |
|--------|-----------|-----------|------|----------|
| Keyword (TF-IDF) | 80.0% | 62.0% | 60.5% | 74.0% |
| Keyword (BM25) | **82.0%** | 66.0% | 62.7% | 76.7% |
| Embedding (BGE-M3) | 82.0% | 64.0% | 62.7% | 76.7% |
| Hybrid (BM25+Emb) | 80.0% | 64.0% | 62.6% | 76.7% |
| LLM Direct | 78.0% | 67.0% | 71.7% | 74.0% |
| Gorilla-style | 79.0% | 65.0% | 68.0% | 75.0% |
| DFSDT | 81.0% | 66.0% | 69.5% | 76.0% |

**Insights**:
- 简单的 BM25 在 Top-5 上表现最好
- LLM Direct 的 MRR 最高，说明排序质量好但召回不足
- DFSDT 平衡性最好
- **Gap to target: -13%**

### Cross-benchmark Validation (ACEBench)

| Method | SAGE-Bench Top-1 | ACEBench Top-1 |
|--------|------------------|----------------|
| Keyword (BM25) | 66.0% | 62.0% |
| LLM Direct | 67.0% | **66.7%** |
| Embedding | 64.0% | 60.0% |

### Training Ablation (预期结果模板)

| Configuration | Tool Selection | Planning | Timing |
|---------------|----------------|----------|--------|
| Baseline (no training) | 82.0% | 27.0% | 76.0% |
| + SFT (LoRA) | 85.0% | 35.0% | 82.0% |
| + DoRA | 86.0% | 37.0% | 83.0% |
| + Coreset Selection | 86.5% | 38.0% | 84.0% |
| + Continual Learning | 87.0% | 40.0% | 85.0% |
| + DPO | **88.0%** | **42.0%** | **86.0%** |

*注: 训练结果为预期目标，需要实际运行确认*

## 论文结构要求

请生成完整的 LaTeX 代码，包含以下章节：

### 1. Abstract (~150 words)
- 问题：现有 Agent benchmark 碎片化
- 方法：统一的三维度评测框架
- 数据：1,200 samples + 1,200 tools
- 发现：最好的方法仍有显著 gap，揭示挑战难度

### 2. Introduction (~1 page)
- 动机：Tool-augmented LLMs 的重要性
- Gap：现有 benchmark 各自为战
- Contributions (3 点)

### 3. Related Work (~1.5 pages)
- **Tool Learning for LLMs**: ToolLLM (Qin et al., 2023), Gorilla (Patil et al., 2023), TaskMatrix (Liang et al., 2023), ToolFormer (Schick et al., 2023), ToolACE (Liu et al., 2024)
- **Agent Benchmarks**: BFCL (Yan et al., 2024), ToolBench (Qin et al., 2023), API-Bank (Li et al., 2023), AgentBench (Liu et al., 2023), T-Eval, ToolACE
- **Planning & Reasoning**: ReAct (Yao et al., 2023), CoT (Wei et al., 2022), ToT (Yao et al., 2023), DEPS (Wang et al., 2023)
- **Efficient Fine-tuning**: LoRA (Hu et al., 2022), DoRA (Liu et al., 2024), LoRA+ (Hayou et al., 2024)
- **Data-efficient Training**: Coreset Selection, Curriculum Learning, Active Learning
- **RLHF for Agents**: DPO (Rafailov et al., 2023), PPO (Schulman et al., 2017), GRPO (Shao et al., 2024)

### 4. SAGE-Bench Dataset (~1.5 pages)
- **4.1 Three Challenges Definition**: 形式化定义 Timing/Planning/Selection
- **4.2 Data Collection**: 工具目录构建 + 样本生成 + 质量控制
- **4.3 External Dataset Integration**: ACEBench, API-Bank, ToolAlpaca 转换
- **4.4 Statistics**: 表格 + 分布图
- **4.5 Evaluation Metrics**: 每个 challenge 的指标定义

### 5. Baseline Methods (~2 pages)
- **5.1 Timing Judgment Methods**: Rule/LLM/Hybrid
- **5.2 Planning Methods**: Simple/Hierarchical/ReAct/ToT
- **5.3 Tool Selection Methods**: Keyword/Embedding/Hybrid/LLM/Gorilla/DFSDT
- **5.4 Training Methods**: SFT (LoRA/DoRA/LoRA+), Coreset Selection, Continual Learning, RL (DPO/PPO/GRPO)

### 6. Experiments (~2.5 pages)
- **6.1 Setup**: 模型、硬件、超参数
- **6.2 Main Results**: 3 个大表 (每个 challenge 一个)
- **6.3 Training Experiments**: SFT/RL 训练对比
- **6.4 Analysis**:
  - Error analysis: 失败案例分类
  - Scaling analysis: 工具数量 vs 准确率
  - Ablation: Hybrid 组件消融, Coreset 策略对比
- **6.5 Cross-benchmark Validation**: ACEBench, API-Bank 结果

### 7. Discussion (~0.5 page)
- Why current methods struggle
- Implications for future research
- Potential directions: 更好的 retrieval、LLM reasoning、联合训练

### 8. Conclusion (~0.5 page)

### 9. Limitations (ICML required)
- 数据集规模有限 (1,200 samples)
- 工具是模拟的，非真实 API 调用
- 评测在特定模型上，泛化性待验证
- RL 训练方法 (DPO/PPO/GRPO) 尚未完整实现，为未来工作

## LaTeX 格式要求

```latex
\documentclass{article}
\usepackage{icml2026}  % ICML 2026 官方模板

% 常用包
\usepackage{booktabs}  % 专业表格
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{algorithm}
\usepackage{algorithmic}
\usepackage{hyperref}
\usepackage{xcolor}

% 表格使用 booktabs 风格
% \toprule, \midrule, \bottomrule
```

- 主文 8 页 + references + appendix
- 图表清晰，caption 要有信息量
- 引用格式: `\citep{}` for parenthetical, `\citet{}` for textual

## 写作风格要求

1. **客观学术**: 不夸大贡献，准确描述
2. **Benchmark 论文定位**: 强调数据集和框架贡献，不是某方法的 SOTA
3. **诚实讨论不足**: 所有方法都有 gap 是卖点——说明 benchmark 有挑战性
4. **准确引用**: ToolLLM, Gorilla, BFCL, API-Bank 等要引用正确
5. **清晰的 Take-away**: 每个实验表格后要有明确的 insight

## 附录内容建议

- A. 数据集详细统计
- B. 工具目录完整分类
- C. 更多实验结果 (不同模型大小、不同 top-k)
- D. 数据样例展示
- E. 实现细节 (prompts, hyperparameters)
- F. ACEBench/API-Bank 数据转换细节
- G. Coreset Selection 算法伪代码
- H. Continual Learning 缓冲区管理

## 实现位置参考

```
SAGE Framework 代码结构:

packages/sage-libs/src/sage/libs/
├── agentic/agents/
│   ├── action/tool_selection/
│   │   ├── keyword_selector.py      # TF-IDF, BM25, Overlap
│   │   ├── embedding_selector.py    # BGE-M3 向量检索
│   │   ├── hybrid_selector.py       # Keyword + Embedding 融合
│   │   ├── gorilla_selector.py      # 两阶段: 检索 + LLM 重排
│   │   ├── dfsdt_selector.py        # DFS 树搜索 + LLM 评分
│   │   └── registry.py              # 策略注册
│   └── planning/
│       ├── timing_decider.py        # Rule/LLM/Hybrid
│       ├── hierarchical_planner.py  # 层次规划
│       ├── react_planner.py         # ReAct
│       ├── tot_planner.py           # Tree-of-Thoughts
│       └── llm_planner.py           # 直接 LLM 规划
└── finetune/agent/
    ├── trainer.py                   # AgentSFTTrainer
    ├── config.py                    # SFT/RL 配置 (LoRA/DoRA/LoRA+)
    └── continual.py                 # CoresetSelector, OnlineContinualLearner

packages/sage-benchmark/src/sage/
├── data/sources/
│   ├── agent_benchmark/             # SAGE 原生数据集
│   │   ├── splits/                  # tool_selection, planning, timing
│   │   └── external_benchmarks/     # ACEBench, API-Bank, ToolAlpaca
│   └── agent_tools/data/            # 1,200 工具目录
└── benchmark/benchmark_agent/
    ├── acebench_loader.py           # ACEBench 数据加载
    ├── evaluation/                  # 评估指标
    └── scripts/                     # 实验脚本
        ├── run_unified_eval.py      # 统一评估
        ├── run_all_experiments.py   # 三挑战完整实验
        └── run_full_training_comparison.py  # 训练对比
```

---

请生成完整的 LaTeX 源代码，包括所有表格、图表占位符、和参考文献的 BibTeX 条目。

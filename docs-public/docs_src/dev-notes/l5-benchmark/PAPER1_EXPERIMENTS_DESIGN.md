# SAGE-Bench Paper 1: Experiments Design

> **文档目的**: 定义 Paper 1 (Benchmark) 的完整实验设计，按论文 Experiment Section 叙述逻辑组织。

______________________________________________________________________

## 📄 论文实验章节结构

按照顶会论文的标准实验章节结构，我们的实验分为：

```
5. Experiments
   5.1 Experimental Setup
       - Datasets & Benchmarks
       - Baseline Methods  
       - Evaluation Metrics
       - Implementation Details

   5.2 Main Results (RQ1-RQ3)
       - RQ1: Timing Detection Performance
       - RQ2: Task Planning Performance
       - RQ3: Tool Selection Performance

   5.3 Analysis & Discussion
       - 5.3.1 Error Analysis
       - 5.3.2 Scaling Analysis
       - 5.3.3 Robustness Analysis
       - 5.3.4 Ablation Studies

   5.4 Cross-Dataset Generalization
```

______________________________________________________________________

## 🗂️ 实验脚本架构

### 目录结构

```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/
├── sage_bench                          # CLI 入口 (symlink)
├── sage_benchmark_cli.py               # 统一 CLI 实现
│
├── experiments/                        # 📁 实验脚本目录 (新建)
│   ├── __init__.py
│   │
│   ├── # === Section 5.2: Main Results ===
│   ├── exp_main_timing.py              # RQ1: Timing Detection
│   ├── exp_main_planning.py            # RQ2: Task Planning  
│   ├── exp_main_selection.py           # RQ3: Tool Selection
│   │
│   ├── # === Section 5.3: Analysis ===
│   ├── exp_analysis_error.py           # 5.3.1 Error Analysis
│   ├── exp_analysis_scaling.py         # 5.3.2 Scaling Analysis
│   ├── exp_analysis_robustness.py      # 5.3.3 Robustness Analysis
│   ├── exp_analysis_ablation.py        # 5.3.4 Ablation Studies
│   │
│   ├── # === Section 5.4: Generalization ===
│   ├── exp_cross_dataset.py            # Cross-dataset evaluation
│   │
│   └── # === Utilities ===
│       ├── exp_utils.py                # 共享工具函数
│       └── figure_generator.py         # 统一图表生成
│
├── run_all_experiments.py              # 保留: 向后兼容
└── README.md                           # 更新: 脚本说明
```

### CLI 命令设计

```bash
# === 完整实验 (论文复现) ===
sage-bench paper1 run                    # 运行所有 Paper 1 实验
sage-bench paper1 run --quick            # 快速模式 (少量样本)
sage-bench paper1 run --section 5.2      # 仅主实验
sage-bench paper1 run --section 5.3      # 仅分析实验

# === 单独实验 ===
sage-bench paper1 timing                 # RQ1: Timing
sage-bench paper1 planning               # RQ2: Planning
sage-bench paper1 selection              # RQ3: Selection

# === 分析实验 ===
sage-bench paper1 analysis error         # 错误分析
sage-bench paper1 analysis scaling       # Scaling 分析
sage-bench paper1 analysis robustness    # 鲁棒性分析
sage-bench paper1 analysis ablation      # 消融实验

# === 跨数据集 ===
sage-bench paper1 cross-dataset          # 跨数据集泛化
```

______________________________________________________________________

## 📊 Section 5.2: Main Results

### 5.2.1 RQ1: Timing Detection (`exp_main_timing.py`)

**研究问题**: 现有方法在判断"是否需要调用工具"上的表现如何？

**实验设计**:

| 方法                | 类型      | 描述                 |
| ------------------- | --------- | -------------------- |
| `timing.rule_based` | Baseline  | 关键词 + 正则规则    |
| `timing.embedding`  | Retrieval | 语义相似度判断       |
| `timing.llm_based`  | LLM       | 直接 LLM 推理        |
| `timing.hybrid`     | Hybrid    | Rule 初筛 + LLM 精判 |

**指标**:

- Primary: Accuracy (target ≥ 95%)
- Secondary: Precision, Recall, F1
- Tertiary: Latency (ms)

**输出**:

```
figures/fig1_timing_comparison.pdf
tables/table_timing_results.tex
results/timing_results.json
```

______________________________________________________________________

### 5.2.2 RQ2: Task Planning (`exp_main_planning.py`)

**研究问题**: 现有方法将复杂任务分解为执行步骤的能力如何？

**实验设计**:

| 方法                   | 类型          | 参考文献           |
| ---------------------- | ------------- | ------------------ |
| `planner.simple`       | Greedy        | -                  |
| `planner.hierarchical` | Decomposition | HuggingGPT         |
| `planner.llm_based`    | LLM           | CoT Prompting      |
| `planner.react`        | Interleaved   | ReAct (Yao et al.) |

**指标**:

- Primary: Plan Success Rate (target ≥ 90%)
- Secondary: Step Accuracy, Tool Coverage
- Tertiary: Average Plan Length

**输出**:

```
figures/fig2_planning_comparison.pdf
tables/table_planning_results.tex
results/planning_results.json
```

______________________________________________________________________

### 5.2.3 RQ3: Tool Selection (`exp_main_selection.py`)

**研究问题**: 现有方法从大规模工具库中选择正确工具的能力如何？

**实验设计**:

| 方法                 | 类型       | 参考文献               |
| -------------------- | ---------- | ---------------------- |
| `selector.keyword`   | Lexical    | BM25                   |
| `selector.embedding` | Semantic   | Dense Retrieval        |
| `selector.hybrid`    | Fusion     | 40% BM25 + 60% Dense   |
| `selector.gorilla`   | LLM-Rerank | Gorilla (Patil et al.) |
| `selector.dfsdt`     | LLM-Score  | ToolLLM (Qin et al.)   |

**指标**:

- Primary: Top-K Accuracy (target ≥ 95%, K=5)
- Secondary: MRR, Recall@K, Precision@K
- Tertiary: Latency (ms)

**输出**:

```
figures/fig3_selection_comparison.pdf
tables/table_selection_results.tex
results/tool_selection_results.json
```

______________________________________________________________________

## 🔬 Section 5.3: Analysis & Discussion

### 5.3.1 Error Analysis (`exp_analysis_error.py`)

**目的**: 深入分析各方法的失败模式，找出改进方向。

**实验内容**:

#### (a) Error Type Breakdown

```python
# Timing 错误分解
timing_errors = {
    "false_positive": "不该调用却调用",      # 调用频率过高
    "false_negative": "该调用却没调用",      # 错过关键时机
    "confidence_miscalibration": "高置信但错误"
}

# Planning 错误分解  
planning_errors = {
    "step_missing": "缺失关键步骤",
    "wrong_order": "步骤顺序错误",
    "invalid_step": "步骤不合理/幻觉",
    "extra_steps": "多余步骤"
}

# Selection 错误分解
selection_errors = {
    "top1_miss": "第一个选择就错",
    "rank_volatility": "Top-K 内排名不稳定",
    "category_confusion": "跨类别混淆",
    "similar_tool_confusion": "相似工具混淆"
}
```

#### (b) Failure Cascading Analysis

分析早期错误导致的级联失败：

```python
# 计算 "first error step index" 分布
# 对比正确 vs 出错轨迹的前 N 步
# 量化 rollback/recovery 能力
```

**输出**:

```
figures/fig_error_breakdown_by_challenge.pdf
figures/fig_error_cascade_distribution.pdf  
tables/table_error_analysis.tex
```

______________________________________________________________________

### 5.3.2 Scaling Analysis (`exp_analysis_scaling.py`)

**目的**: 测试方法在不同规模下的性能变化。

**实验内容**:

#### (a) Tool Set Size Scaling

```python
TOOL_COUNTS = [10, 25, 50, 100, 200, 500, 1000]

# 对每个规模测试:
# 1. 基础 accuracy
# 2. 加入 noise tools 后的 accuracy
# 3. Latency 变化
```

#### (b) LLM Size Scaling

```python
MODELS = [
    ("Qwen/Qwen2.5-0.5B-Instruct", "0.5B"),
    ("Qwen/Qwen2.5-1.5B-Instruct", "1.5B"),  
    ("Qwen/Qwen2.5-7B-Instruct", "7B"),
    ("Qwen/Qwen2.5-14B-Instruct", "14B"),
]

# 测试 Planning Challenge 在不同模型大小下的性能
# 分析是否存在 emergent ability 跳跃
```

**输出**:

```
figures/fig_scaling_tool_count.pdf
figures/fig_scaling_llm_size.pdf
tables/table_scaling_results.tex
```

______________________________________________________________________

### 5.3.3 Robustness Analysis (`exp_analysis_robustness.py`)

**目的**: 测试方法对输入变化和环境扰动的鲁棒性。

**实验内容**:

#### (a) Semantic Variation Robustness

```python
# 同一任务的不同表达方式
variations = {
    "original": "查找张伟的联系方式",
    "paraphrase": "给张伟打电话前获取他的号码",
    "formal": "请检索张伟先生的联络信息",
    "casual": "张伟电话多少",
    "adversarial": "我不想找张伟，但假如要找..."
}

# 测试各方法的一致性
```

#### (b) Instruction Quality Sensitivity

```python
instruction_types = [
    "human_written",       # 人工撰写
    "synthetic_template",  # 模板生成
    "adversarial"          # 对抗性改写
]
```

#### (c) Tool Reliability Injection

```python
# 模拟工具不可靠场景
failure_rates = [0.0, 0.05, 0.10, 0.20]
latency_spikes = [0.0, 0.10, 0.20, 0.30]

# 测试 agent 的检测、重试、恢复能力
```

**输出**:

```
figures/fig_robustness_semantic.pdf
figures/fig_robustness_instruction.pdf
figures/fig_robustness_reliability.pdf
tables/table_robustness_results.tex
```

______________________________________________________________________

### 5.3.4 Ablation Studies (`exp_analysis_ablation.py`)

**目的**: 分析各方法关键组件的贡献。

**实验内容**:

#### (a) Prompt Design Ablation

```python
prompt_variants = [
    "minimal",       # 最小信息
    "standard",      # 标准 prompt
    "with_examples", # 带 few-shot 示例
    "with_cot"       # 带 Chain-of-Thought
]
```

#### (b) Hybrid Method Component Ablation

```python
# Tool Selection Hybrid
ablation_configs = [
    {"keyword_weight": 1.0, "embedding_weight": 0.0},  # Pure BM25
    {"keyword_weight": 0.0, "embedding_weight": 1.0},  # Pure Embedding
    {"keyword_weight": 0.4, "embedding_weight": 0.6},  # Default Hybrid
    {"keyword_weight": 0.5, "embedding_weight": 0.5},  # Equal Weight
]

# Timing Hybrid
timing_ablation = [
    "rule_only",     # 仅规则
    "llm_only",      # 仅 LLM
    "rule_then_llm", # 默认: 规则初筛 + LLM
    "llm_then_rule"  # 反向: LLM 初筛 + 规则
]
```

**输出**:

```
figures/fig_ablation_prompt.pdf
figures/fig_ablation_hybrid_weights.pdf
tables/table_ablation_results.tex
```

______________________________________________________________________

## 🌐 Section 5.4: Cross-Dataset Generalization (`exp_cross_dataset.py`)

**目的**: 验证方法在不同数据集上的泛化能力。

**数据集**:

| 数据集     | 来源       | 任务类型         | 规模  |
| ---------- | ---------- | ---------------- | ----- |
| SAGE-Bench | Ours       | All 3 Challenges | ~1000 |
| ACE-Bench  | External   | Tool Selection   | ~500  |
| ToolBench  | Qin et al. | Tool Selection   | ~2000 |
| API-Bank   | Li et al.  | API Call         | ~500  |
| BFCL       | Gorilla    | Function Calling | ~1000 |

**实验设计**:

```python
# 训练/测试分离
# Train on: SAGE-Bench
# Test on: ACE-Bench, ToolBench, API-Bank, BFCL

# 指标: 各数据集上的 Top-K Accuracy, MRR
```

**输出**:

```
figures/fig_cross_dataset_comparison.pdf
tables/table_cross_dataset_results.tex
```

______________________________________________________________________

## 📈 输出文件规范

### 目录结构

```
.sage/benchmark/results/
├── paper1/                              # Paper 1 专用目录
│   ├── section_5_2_main/
│   │   ├── timing_results.json
│   │   ├── planning_results.json
│   │   └── selection_results.json
│   │
│   ├── section_5_3_analysis/
│   │   ├── error_analysis.json
│   │   ├── scaling_analysis.json
│   │   ├── robustness_analysis.json
│   │   └── ablation_analysis.json
│   │
│   ├── section_5_4_generalization/
│   │   └── cross_dataset_results.json
│   │
│   ├── figures/
│   │   ├── fig1_timing_comparison.pdf
│   │   ├── fig2_planning_comparison.pdf
│   │   ├── fig3_selection_comparison.pdf
│   │   ├── fig4_error_analysis.pdf
│   │   ├── fig5_scaling_analysis.pdf
│   │   ├── fig6_robustness_analysis.pdf
│   │   ├── fig7_ablation_study.pdf
│   │   └── fig8_cross_dataset.pdf
│   │
│   └── tables/
│       ├── table1_main_results.tex
│       ├── table2_error_breakdown.tex
│       ├── table3_scaling_results.tex
│       ├── table4_robustness_results.tex
│       ├── table5_ablation_results.tex
│       └── table6_cross_dataset.tex
│
└── all_results.json                     # 汇总 (向后兼容)
```

### Figure 命名规范

```
fig{N}_{section}_{content}.pdf

示例:
fig1_main_timing_comparison.pdf
fig2_main_planning_comparison.pdf
fig3_main_selection_comparison.pdf
fig4_analysis_error_breakdown.pdf
fig5_analysis_scaling_tool_count.pdf
fig6_analysis_scaling_llm_size.pdf
fig7_analysis_robustness.pdf
fig8_analysis_ablation.pdf
fig9_generalization_cross_dataset.pdf
```

### Table 命名规范

```
table{N}_{content}.tex

示例:
table1_main_results.tex           # 主结果汇总
table2_timing_detailed.tex        # Timing 详细
table3_planning_detailed.tex      # Planning 详细
table4_selection_detailed.tex     # Selection 详细
table5_error_breakdown.tex        # 错误分解
table6_scaling_results.tex        # Scaling 结果
table7_robustness_results.tex     # 鲁棒性结果
table8_ablation_results.tex       # 消融结果
table9_cross_dataset.tex          # 跨数据集
```

______________________________________________________________________

## ⚙️ 实现优先级

### Phase 1: 主实验 (Week 1) - P0

| 脚本                    | 状态    | 说明                              |
| ----------------------- | ------- | --------------------------------- |
| `exp_main_timing.py`    | 🔄 重构 | 基于现有 `run_all_experiments.py` |
| `exp_main_planning.py`  | 🔄 重构 | 基于现有代码                      |
| `exp_main_selection.py` | 🔄 重构 | 基于现有代码                      |

### Phase 2: 分析实验 (Week 2-3) - P1

| 脚本                         | 状态    | 复杂度 |
| ---------------------------- | ------- | ------ |
| `exp_analysis_error.py`      | 🆕 新建 | 中     |
| `exp_analysis_scaling.py`    | 🆕 新建 | 高     |
| `exp_analysis_robustness.py` | 🆕 新建 | 高     |
| `exp_analysis_ablation.py`   | 🆕 新建 | 中     |

### Phase 3: 泛化实验 (Week 4) - P2

| 脚本                   | 状态    | 依赖           |
| ---------------------- | ------- | -------------- |
| `exp_cross_dataset.py` | 🔄 扩展 | 外部数据集加载 |

______________________________________________________________________

## 🔧 共享工具模块

### `exp_utils.py`

```python
"""实验共享工具函数"""

# 环境设置
def setup_experiment_env(seed: int = 42) -> None: ...

# 数据加载
def load_benchmark_data(challenge: str, split: str = "test") -> list: ...

# 结果保存
def save_results(results: dict, section: str, name: str) -> Path: ...

# 进度显示
def create_progress_bar(total: int, desc: str) -> tqdm: ...

# LLM 客户端
def get_llm_client() -> UnifiedInferenceClient: ...
def get_embedding_client() -> EmbeddingClientAdapter: ...
```

### `figure_generator.py`

```python
"""统一图表生成"""

# 图表样式
FIGURE_STYLE = {
    "font.family": "serif",
    "font.size": 10,
    "figure.figsize": (8, 6),
    "savefig.dpi": 300,
    "savefig.format": "pdf",
}

# 颜色方案 (colorblind-friendly)
COLORS = {
    "primary": "#1f77b4",
    "secondary": "#ff7f0e",
    "success": "#2ca02c",
    "danger": "#d62728",
    "target_line": "#7f7f7f",
}

# 图表生成函数
def plot_challenge_comparison(results: dict, challenge: str) -> Figure: ...
def plot_scaling_curve(results: dict, x_label: str) -> Figure: ...
def plot_error_breakdown(errors: dict) -> Figure: ...
def plot_ablation_heatmap(ablation_results: dict) -> Figure: ...

# LaTeX 表格生成
def generate_latex_table(results: dict, template: str) -> str: ...
```

______________________________________________________________________

## ✅ 实施检查清单

### 基础设施

- [ ] 创建 `scripts/experiments/` 目录结构
- [ ] 实现 `exp_utils.py` 共享模块
- [ ] 实现 `figure_generator.py` 图表模块
- [ ] 更新 `sage_benchmark_cli.py` 支持新命令

### Section 5.2: 主实验

- [ ] `exp_main_timing.py` - 重构自现有代码
- [ ] `exp_main_planning.py` - 重构自现有代码
- [ ] `exp_main_selection.py` - 重构自现有代码
- [ ] 生成 fig1-3, table1-4

### Section 5.3: 分析实验

- [ ] `exp_analysis_error.py` - 错误分析
- [ ] `exp_analysis_scaling.py` - Scaling 分析
- [ ] `exp_analysis_robustness.py` - 鲁棒性分析
- [ ] `exp_analysis_ablation.py` - 消融实验
- [ ] 生成 fig4-8, table5-8

### Section 5.4: 泛化实验

- [ ] `exp_cross_dataset.py` - 跨数据集验证
- [ ] 生成 fig9, table9

### 集成测试

- [ ] 端到端运行 `sage-bench paper1 run --quick`
- [ ] 验证所有 figures 和 tables 生成
- [ ] CI/CD 集成

______________________________________________________________________

## 📝 控制变量说明

所有实验使用统一的控制变量配置：

```python
# packages/sage-benchmark/.../adapter_registry.py
BENCHMARK_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
BENCHMARK_LLM_TEMPERATURE = 0.1
RANDOM_SEED = 42
```

确保公平对比：

1. 所有 embedding 方法使用相同 embedding 模型
1. 所有 LLM 方法使用相同 temperature
1. 所有实验使用相同随机种子
1. 测试数据完全相同

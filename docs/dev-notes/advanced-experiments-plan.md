# SAGE-Bench Advanced Experiments Implementation Plan

## 📋 Overview

本文档详细列出为 Paper 1 扩展实验的代码改进计划。共 9 类实验，分为三大类：

1. **现象分析型 (3个)**: 暴露现有方法的盲区
2. **变量控制型 (3个)**: 系统性分析关键变量影响
3. **趋势对齐型 (3个)**: 对标顶会/大厂研究范式

---

## 🔍 一类：现象分析型 (Error Analysis)

### 1. Error Type Breakdown by Challenge

**目标**: 按 Challenge 分类统计常见错误类型

**新增文件**:
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── evaluation/analyzers/
│   ├── error_breakdown_analyzer.py      # 新增：错误类型分解分析器
│   └── __init__.py                      # 更新：导出新分析器
├── experiments/
│   └── error_analysis_exp.py            # 新增：错误分析实验
```

**代码改动清单**:

| 文件 | 改动类型 | 描述 |
|------|----------|------|
| `error_breakdown_analyzer.py` | 新增 | 实现 `ErrorBreakdownAnalyzer` 类 |
| `timing_analyzer.py` | 扩展 | 添加 false_positive/false_negative 详细分解 |
| `planning_analyzer.py` | 扩展 | 添加 step_missing/wrong_order/invalid_step 分解 |
| `tool_selection_analyzer.py` | 扩展 | 添加 top1_error/topk_rank_volatility 分解 |
| `run_all_experiments.py` | 扩展 | 添加 `--error-analysis` flag |

**关键实现**:

```python
# error_breakdown_analyzer.py
class ErrorBreakdownAnalyzer:
    """
    Unified error type breakdown analyzer across all challenges.
    """

    def analyze_timing_errors(self, predictions, references, confidences=None):
        """
        Timing 错误分解:
        - false_positive_rate: 不该调用却调用
        - false_negative_rate: 该调用却没调用
        - confidence_calibration: 高置信度但错误的比例
        """

    def analyze_planning_errors(self, predictions, references):
        """
        Planning 错误分解:
        - step_missing_rate: 缺失关键步骤
        - wrong_order_rate: 步骤顺序错误
        - invalid_step_rate: 步骤不合理/幻觉
        - extra_step_rate: 多余步骤
        """

    def analyze_selection_errors(self, predictions, references, k=5):
        """
        Selection 错误分解:
        - top1_error_rate: 第一个选择就错
        - topk_rank_volatility: top-k 内排名抖动
        - category_confusion_matrix: 跨类别混淆
        - similar_tool_confusion: 相似工具混淆率
        """
```

**输出**:
```
figures/fig_error_breakdown_timing.pdf     # FP/FN 对比柱状图
figures/fig_error_breakdown_planning.pdf   # 4种错误类型堆叠图
figures/fig_error_breakdown_selection.pdf  # 错误模式分布饼图
tables/table_error_breakdown.tex           # 详细错误统计表
```

---

### 2. Failure Cascading Analysis

**目标**: 分析早期错误导致的级联失败

**新增文件**:
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── evaluation/analyzers/
│   └── cascading_failure_analyzer.py    # 新增
├── experiments/
│   └── cascading_analysis_exp.py        # 新增
```

**代码改动清单**:

| 文件 | 改动类型 | 描述 |
|------|----------|------|
| `cascading_failure_analyzer.py` | 新增 | 实现级联失败分析 |
| `planning_exp.py` | 扩展 | 记录每步执行 trace |
| `base_experiment.py` | 扩展 | 添加 `ActionTrace` 数据模型 |
| `run_all_experiments.py` | 扩展 | 添加 `--cascade-analysis` flag |

**关键实现**:

```python
# cascading_failure_analyzer.py
class CascadingFailureAnalyzer:
    """
    Analyze failure cascading patterns in multi-step agent tasks.
    """

    def compute_first_error_distribution(self, traces):
        """
        计算 "first error step index" 分布
        - 返回直方图: [step_1_error_count, step_2_error_count, ...]
        """

    def compare_correct_vs_failed_trajectories(self, traces):
        """
        对比正确 vs 出错轨迹的前 N 步
        - 返回: divergence_point_distribution
        """

    def compute_recovery_rate(self, traces):
        """
        计算 agent 从错误中恢复的能力
        - recovery_after_error_rate: 出错后能否自我纠正
        """

# base_experiment.py 新增
@dataclass
class ActionTrace:
    """Single action in execution trace."""
    step_index: int
    action_type: str  # "tool_selection" | "planning" | "timing"
    prediction: Any
    ground_truth: Any
    is_correct: bool
    confidence: float = 0.0
    error_type: Optional[str] = None
```

**输出**:
```
figures/fig_cascade_first_error_dist.pdf     # 首次错误步骤分布
figures/fig_cascade_trajectory_compare.pdf   # 正确vs错误轨迹对比
tables/table_cascade_analysis.tex            # 级联失败统计
```

---

### 3. Cross-Task Generalization Evaluation

**目标**: 测试语义变化的鲁棒性

**新增文件**:
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── data/
│   └── semantic_variations.jsonl        # 新增：语义变体数据
├── experiments/
│   └── generalization_exp.py            # 新增
├── evaluation/analyzers/
│   └── generalization_analyzer.py       # 新增
```

**代码改动清单**:

| 文件 | 改动类型 | 描述 |
|------|----------|------|
| `generalization_exp.py` | 新增 | 实现跨任务泛化实验 |
| `generalization_analyzer.py` | 新增 | 分析语义变化鲁棒性 |
| `semantic_variations.jsonl` | 新增 | 同任务不同描述的测试数据 |
| `run_all_experiments.py` | 扩展 | 添加 `--generalization` flag |

**数据格式**:
```jsonl
{
  "task_id": "find_contact_001",
  "original": "查找张伟的联系方式",
  "variations": [
    {"type": "paraphrase", "text": "给张伟打电话前获取他的号码"},
    {"type": "formal", "text": "请检索张伟先生的联络信息"},
    {"type": "casual", "text": "张伟电话多少"},
    {"type": "adversarial", "text": "我不想找张伟，但假如要找的话怎么联系"}
  ],
  "expected_tool": "contact_search",
  "expected_timing": true
}
```

**关键实现**:

```python
# generalization_exp.py
class GeneralizationExperiment(BaseExperiment):
    """
    Test semantic variation robustness.
    """

    def run_variation_test(self, strategy, variations_data):
        """
        对每个任务测试多个语义变体:
        1. 所有变体是否选择相同工具？
        2. Timing 判断是否一致？
        3. 哪种变体类型最容易出错？
        """

# generalization_analyzer.py
class GeneralizationAnalyzer:
    def compute_consistency_score(self, results):
        """同任务不同描述的一致性得分"""

    def compute_variation_sensitivity(self, results):
        """各变体类型的敏感度分析"""

    def detect_template_overfitting(self, results):
        """检测是否过拟合特定模板"""
```

**输出**:
```
figures/fig_generalization_consistency.pdf   # 一致性得分对比
figures/fig_generalization_sensitivity.pdf   # 各变体类型敏感度
tables/table_generalization_results.tex      # 详细泛化结果
```

---

## ⚙️ 二类：变量控制型 (Ablation Studies)

### 4. Tool Set Size Scaling Curve

**目标**: 测试工具数量对准确率的影响

**新增文件**:
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── experiments/
│   └── scaling_exp.py                   # 新增
├── evaluation/analyzers/
│   └── scaling_analyzer.py              # 新增
├── data/
│   └── noise_tools.jsonl                # 新增：干扰工具库
```

**代码改动清单**:

| 文件 | 改动类型 | 描述 |
|------|----------|------|
| `scaling_exp.py` | 新增 | 实现工具数量 scaling 实验 |
| `scaling_analyzer.py` | 新增 | 分析 scaling 曲线 |
| `noise_tools.jsonl` | 新增 | 相似名称/类别的干扰工具 |
| `adapter_registry.py` | 扩展 | 支持动态工具集大小 |
| `run_all_experiments.py` | 扩展 | 添加 `--scaling-study` flag |

**关键实现**:

```python
# scaling_exp.py
class ToolSetScalingExperiment(BaseExperiment):
    """
    Test tool selection accuracy vs candidate set size.
    """

    SCALE_POINTS = [10, 25, 50, 100, 200, 500, 1000]

    def run_scaling_test(self, strategy, base_tools, noise_tools):
        """
        逐步增加候选工具数量:
        1. 基础: 10 个相关工具
        2. 逐步添加 noise tools
        3. 记录各规模下的 accuracy/MRR/latency
        """

    def add_noise_tools(self, base_tools, noise_tools, target_size):
        """
        添加干扰工具:
        - similar_name: 名称相似但功能不同
        - similar_category: 同类别但不相关
        - random: 完全无关
        """

# scaling_analyzer.py
class ScalingAnalyzer:
    def fit_scaling_curve(self, results):
        """拟合 scaling 曲线 (对数/线性/指数)"""

    def compute_noise_resistance(self, results):
        """计算各策略的抗干扰能力"""

    def find_critical_scale(self, results, threshold=0.9):
        """找到准确率下降到阈值的临界规模"""
```

**输出**:
```
figures/fig_scaling_curve.pdf                # X: 工具数, Y: accuracy
figures/fig_scaling_noise_resistance.pdf     # 各策略抗干扰对比
tables/table_scaling_results.tex             # 详细 scaling 数据
```

---

### 5. Prompt Length Ablation

**目标**: 测试 prompt 长度/内容对 LLM-based 方法的影响

**新增文件**:
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── experiments/
│   └── prompt_ablation_exp.py           # 新增
├── config/
│   └── prompt_templates/
│       ├── minimal.yaml                 # 最小 prompt
│       ├── standard.yaml                # 标准 prompt
│       ├── with_examples.yaml           # 带示例
│       └── with_cot.yaml                # 带 CoT
```

**代码改动清单**:

| 文件 | 改动类型 | 描述 |
|------|----------|------|
| `prompt_ablation_exp.py` | 新增 | 实现 prompt 消融实验 |
| `prompt_templates/*.yaml` | 新增 | 不同复杂度的 prompt 模板 |
| `adapter_registry.py` | 扩展 | 支持自定义 prompt 注入 |
| `run_all_experiments.py` | 扩展 | 添加 `--prompt-ablation` flag |

**Prompt 变体**:
```yaml
# minimal.yaml - 最小信息
system: "Select the most relevant tool."
user_template: "Query: {query}\nTools: {tools}\nAnswer:"

# standard.yaml - 标准 prompt
system: "You are a tool selection assistant. Given a user query, select the most relevant tools."
user_template: |
  Query: {query}
  Available Tools:
  {tools}
  Select the top-{k} most relevant tools.

# with_examples.yaml - 带 few-shot 示例
system: "..."
examples:
  - query: "What's the weather today?"
    tools: ["weather_api", "calendar", "news"]
    answer: ["weather_api"]
user_template: "..."

# with_cot.yaml - 带 Chain-of-Thought
system: "Think step by step before selecting tools."
user_template: |
  Query: {query}
  Tools: {tools}

  Let's think step by step:
  1. What is the user trying to do?
  2. What capabilities are needed?
  3. Which tools match these capabilities?

  Final Selection:
```

**关键实现**:

```python
# prompt_ablation_exp.py
class PromptAblationExperiment(BaseExperiment):
    """
    Ablation study on prompt design for LLM-based methods.
    """

    PROMPT_VARIANTS = ["minimal", "standard", "with_examples", "with_cot"]

    def run_ablation(self, strategy, challenge):
        """
        对每个 prompt 变体运行实验:
        - 记录 accuracy, latency, token_count
        - 分析 prompt 长度 vs 性能的关系
        """

    def measure_context_window_effect(self, strategy, max_tokens_list):
        """
        测试上下文窗口限制的影响:
        - 逐步增加候选工具数直到超出窗口
        - 记录 truncation 对性能的影响
        """
```

**输出**:
```
figures/fig_prompt_ablation.pdf              # Prompt 变体性能对比
figures/fig_prompt_length_vs_accuracy.pdf    # 长度 vs 准确率
tables/table_prompt_ablation.tex             # 详细消融结果
```

---

### 6. Tool Reliability Injection

**目标**: 测试工具失败/延迟对 agent 的影响

**新增文件**:
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── experiments/
│   └── reliability_exp.py               # 新增
├── mocks/
│   └── unreliable_tool_wrapper.py       # 新增：不可靠工具模拟
```

**代码改动清单**:

| 文件 | 改动类型 | 描述 |
|------|----------|------|
| `reliability_exp.py` | 新增 | 实现可靠性测试实验 |
| `unreliable_tool_wrapper.py` | 新增 | 模拟工具失败/延迟 |
| `run_all_experiments.py` | 扩展 | 添加 `--reliability-test` flag |

**关键实现**:

```python
# unreliable_tool_wrapper.py
class UnreliableToolWrapper:
    """
    Wrapper to inject failures/delays into tool calls.
    """

    def __init__(self, tool, failure_rate=0.05, latency_spike_rate=0.1):
        self.tool = tool
        self.failure_rate = failure_rate
        self.latency_spike_rate = latency_spike_rate

    def call(self, *args, **kwargs):
        # Random failure
        if random.random() < self.failure_rate:
            raise ToolExecutionError("Simulated failure")

        # Latency spike (2-5x normal)
        if random.random() < self.latency_spike_rate:
            time.sleep(random.uniform(2, 5) * self.base_latency)

        return self.tool.call(*args, **kwargs)

# reliability_exp.py
class ReliabilityExperiment(BaseExperiment):
    """
    Test agent robustness under tool reliability issues.
    """

    FAILURE_RATES = [0.0, 0.05, 0.10, 0.20]
    LATENCY_SPIKE_RATES = [0.0, 0.10, 0.20, 0.30]

    def run_reliability_test(self, strategy):
        """
        测试不同失败率下的 agent 行为:
        - detect_rate: 是否能检测到失败
        - retry_rate: 是否尝试重试
        - recovery_rate: 是否能恢复
        - silent_fail_rate: 静默失败率
        """

    def analyze_failure_handling(self, traces):
        """
        分析失败处理策略:
        - 有无 retry 机制
        - 有无 fallback 策略
        - 错误传播范围
        """
```

**输出**:
```
figures/fig_reliability_failure_rate.pdf     # 失败率 vs 性能
figures/fig_reliability_recovery.pdf         # 恢复能力对比
tables/table_reliability_results.tex         # 详细可靠性测试结果
```

---

## 🚀 三类：趋势对齐型 (Scaling & SOTA Comparison)

### 7. LLM Size Scaling Study

**目标**: 测试不同 LLM 大小对性能的影响

**新增文件**:
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── experiments/
│   └── llm_scaling_exp.py               # 新增
├── config/
│   └── model_configs/
│       ├── qwen_0.5b.yaml
│       ├── qwen_1.5b.yaml
│       ├── qwen_7b.yaml
│       ├── qwen_14b.yaml
│       └── gpt4.yaml
```

**代码改动清单**:

| 文件 | 改动类型 | 描述 |
|------|----------|------|
| `llm_scaling_exp.py` | 新增 | 实现 LLM scaling 实验 |
| `model_configs/*.yaml` | 新增 | 各模型配置 |
| `adapter_registry.py` | 扩展 | 支持动态模型切换 |
| `run_all_experiments.py` | 扩展 | 添加 `--llm-scaling` flag |

**关键实现**:

```python
# llm_scaling_exp.py
class LLMScalingExperiment(BaseExperiment):
    """
    Study performance scaling with LLM size.
    """

    MODELS = [
        ("Qwen/Qwen2.5-0.5B-Instruct", "0.5B"),
        ("Qwen/Qwen2.5-1.5B-Instruct", "1.5B"),
        ("Qwen/Qwen2.5-7B-Instruct", "7B"),
        ("Qwen/Qwen2.5-14B-Instruct", "14B"),
        ("gpt-4", "GPT-4"),  # via API
    ]

    def run_scaling_study(self, challenges=["planning"]):
        """
        对每个模型运行指定 challenge:
        - 记录 accuracy, latency, cost
        - 分析是否存在 "emergent ability" 跳跃
        """

    def detect_emergent_abilities(self, results):
        """
        检测非线性提升:
        - 计算各模型间的性能增量
        - 识别突然解锁的能力
        """

    def compute_cost_efficiency(self, results):
        """
        计算性价比:
        - accuracy_per_dollar
        - accuracy_per_token
        """
```

**输出**:
```
figures/fig_llm_scaling_curve.pdf            # 模型大小 vs 性能
figures/fig_llm_scaling_cost.pdf             # 性能 vs 成本
tables/table_llm_scaling.tex                 # 详细 scaling 数据
```

---

### 8. Instruction Quality Sensitivity

**目标**: 测试指令质量对性能的影响

**新增文件**:
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── experiments/
│   └── instruction_sensitivity_exp.py   # 新增
├── data/
│   └── instruction_variations.jsonl     # 新增
```

**代码改动清单**:

| 文件 | 改动类型 | 描述 |
|------|----------|------|
| `instruction_sensitivity_exp.py` | 新增 | 实现指令敏感度实验 |
| `instruction_variations.jsonl` | 新增 | 三种质量的指令数据 |
| `run_all_experiments.py` | 扩展 | 添加 `--instruction-sensitivity` flag |

**数据格式**:
```jsonl
{
  "task_id": "weather_query_001",
  "ground_truth": {"tool": "weather_api", "plan": ["get_location", "query_weather"]},
  "instructions": {
    "human_written": "What's the weather like in Beijing today?",
    "synthetic_template": "Query weather information for location: Beijing, date: today",
    "adversarial": "I definitely don't want to know the weather, but if I hypothetically did want to check conditions in Beijing..."
  }
}
```

**关键实现**:

```python
# instruction_sensitivity_exp.py
class InstructionSensitivityExperiment(BaseExperiment):
    """
    Test robustness to instruction quality variations.
    """

    INSTRUCTION_TYPES = ["human_written", "synthetic_template", "adversarial"]

    def run_sensitivity_test(self, strategy, challenge):
        """
        对每种指令类型运行测试:
        - 比较 accuracy 差异
        - 分析哪种策略对指令质量最敏感
        """

    def compute_robustness_score(self, results):
        """
        计算鲁棒性得分:
        - min_accuracy / max_accuracy 比值
        - 各类型间的方差
        """
```

**输出**:
```
figures/fig_instruction_sensitivity.pdf      # 各指令类型性能对比
figures/fig_instruction_robustness.pdf       # 鲁棒性得分
tables/table_instruction_sensitivity.tex     # 详细敏感度分析
```

---

### 9. In-Context Learning vs Fine-tuning

**目标**: 对比 ICL 和微调的效果

**新增文件**:
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── experiments/
│   └── icl_vs_finetune_exp.py           # 新增
├── training/
│   └── finetune_runner.py               # 新增：简单微调脚本
```

**代码改动清单**:

| 文件 | 改动类型 | 描述 |
|------|----------|------|
| `icl_vs_finetune_exp.py` | 新增 | 实现 ICL vs 微调对比实验 |
| `finetune_runner.py` | 新增 | 简单 LoRA 微调脚本 |
| `run_all_experiments.py` | 扩展 | 添加 `--icl-finetune` flag |

**关键实现**:

```python
# icl_vs_finetune_exp.py
class ICLvsFinetuneExperiment(BaseExperiment):
    """
    Compare In-Context Learning vs Fine-tuning approaches.
    """

    def run_icl_variants(self, model, challenge, n_shots=[0, 1, 3, 5, 10]):
        """
        测试不同 shot 数量的 ICL:
        - 0-shot (zero-shot)
        - 1-shot
        - few-shot (3, 5, 10)
        """

    def run_finetune_variants(self, model, challenge, train_sizes=[100, 500, 1000]):
        """
        测试不同训练数据量的微调:
        - 100 samples
        - 500 samples
        - 1000 samples
        """

    def compute_data_efficiency(self, icl_results, ft_results):
        """
        计算数据效率:
        - ICL: shots_needed_for_X_accuracy
        - FT: samples_needed_for_X_accuracy
        """

# finetune_runner.py
class SimpleFinetuneRunner:
    """
    Simple LoRA fine-tuning for benchmark comparison.
    """

    def finetune(self, model_id, train_data, task="planning"):
        """
        使用 LoRA 进行轻量微调:
        - lora_r: 8
        - lora_alpha: 16
        - epochs: 3
        """
```

**输出**:
```
figures/fig_icl_vs_finetune.pdf              # ICL vs FT 对比
figures/fig_data_efficiency.pdf              # 数据效率曲线
tables/table_icl_vs_finetune.tex             # 详细对比结果
```

---

## 📊 统一输出结构

```
.sage/benchmark/results/
├── all_results.json                         # 现有
├── advanced_experiments/                    # 新增目录
│   ├── error_analysis/
│   │   ├── error_breakdown.json
│   │   ├── cascading_analysis.json
│   │   └── generalization.json
│   ├── ablation_studies/
│   │   ├── tool_scaling.json
│   │   ├── prompt_ablation.json
│   │   └── reliability.json
│   └── scaling_studies/
│       ├── llm_scaling.json
│       ├── instruction_sensitivity.json
│       └── icl_vs_finetune.json
├── figures/
│   ├── fig1-5 (现有)
│   ├── fig6_error_breakdown_*.pdf           # 新增
│   ├── fig7_cascade_*.pdf
│   ├── fig8_generalization_*.pdf
│   ├── fig9_scaling_*.pdf
│   ├── fig10_prompt_*.pdf
│   ├── fig11_reliability_*.pdf
│   ├── fig12_llm_scaling_*.pdf
│   ├── fig13_instruction_*.pdf
│   └── fig14_icl_finetune_*.pdf
└── tables/
    ├── table1-2 (现有)
    ├── table_error_breakdown.tex            # 新增
    ├── table_cascade_analysis.tex
    ├── table_generalization.tex
    ├── table_scaling.tex
    ├── table_prompt_ablation.tex
    ├── table_reliability.tex
    ├── table_llm_scaling.tex
    ├── table_instruction_sensitivity.tex
    └── table_icl_vs_finetune.tex
```

---

## 🛠️ CLI 扩展

```bash
# 现有命令
sage-bench run                              # 基础实验
sage-bench run --quick                      # 快速模式

# 新增命令
sage-bench run --advanced                   # 运行所有高级实验
sage-bench run --error-analysis             # 仅错误分析
sage-bench run --cascade-analysis           # 仅级联分析
sage-bench run --generalization             # 仅泛化测试
sage-bench run --scaling-study              # 工具数量 scaling
sage-bench run --prompt-ablation            # Prompt 消融
sage-bench run --reliability-test           # 可靠性测试
sage-bench run --llm-scaling                # LLM 大小 scaling
sage-bench run --instruction-sensitivity    # 指令敏感度
sage-bench run --icl-finetune               # ICL vs 微调

# 组合
sage-bench run --error-analysis --cascade-analysis  # 现象分析类
sage-bench run --scaling-study --prompt-ablation    # 变量控制类
```

---

## 📅 实现优先级

| 优先级 | 实验 | 预估工作量 | 依赖 |
|--------|------|------------|------|
| P0 | 1. Error Type Breakdown | 2天 | 现有 analyzer |
| P0 | 4. Tool Set Scaling | 2天 | 现有 selector |
| P1 | 7. LLM Size Scaling | 3天 | vLLM 服务 |
| P1 | 3. Cross-Task Generalization | 2天 | 数据准备 |
| P2 | 2. Failure Cascading | 2天 | trace 机制 |
| P2 | 5. Prompt Length Ablation | 2天 | prompt 模板 |
| P2 | 8. Instruction Sensitivity | 2天 | 数据准备 |
| P3 | 6. Tool Reliability | 3天 | mock 工具 |
| P3 | 9. ICL vs Fine-tuning | 4天 | 微调脚本 |

**总预估**: 22 天 (单人)

---

## ✅ 实现检查清单

### Phase 1: 基础设施 (Week 1)
- [ ] 扩展 `base_experiment.py` 添加 `ActionTrace` 数据模型
- [ ] 创建 `advanced_experiments/` 输出目录结构
- [ ] 扩展 `run_all_experiments.py` 添加新 flags
- [ ] 创建统一的 figure/table 生成模板

### Phase 2: 现象分析 (Week 2)
- [ ] 实现 `error_breakdown_analyzer.py`
- [ ] 实现 `cascading_failure_analyzer.py`
- [ ] 实现 `generalization_analyzer.py`
- [ ] 创建语义变体测试数据

### Phase 3: 变量控制 (Week 3)
- [ ] 实现 `scaling_exp.py` + noise tools 数据
- [ ] 实现 `prompt_ablation_exp.py` + prompt 模板
- [ ] 实现 `reliability_exp.py` + 工具模拟器

### Phase 4: 趋势对齐 (Week 4)
- [ ] 实现 `llm_scaling_exp.py` + 模型配置
- [ ] 实现 `instruction_sensitivity_exp.py` + 数据
- [ ] 实现 `icl_vs_finetune_exp.py` + 微调脚本

### Phase 5: 集成测试 (Week 5)
- [ ] 端到端测试所有新实验
- [ ] 生成示例 figures 和 tables
- [ ] 更新文档和 README
- [ ] CI/CD 集成

---

## 📝 Notes

1. **控制变量**: 所有新实验继续使用 `BENCHMARK_EMBEDDING_MODEL` 和 `BENCHMARK_LLM_TEMPERATURE`
2. **随机种子**: 继续使用 SEED=42 确保可复现
3. **数据格式**: 新数据文件统一使用 JSONL 格式
4. **输出格式**: 所有 figures 同时输出 PDF + PNG，tables 输出 LaTeX

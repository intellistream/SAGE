# ICML 投稿并行任务分解

## 任务总览

```
Round 1 (可完全并行):
  ├── Task 1A: 结果收集器实现
  ├── Task 1B: AdaptiveCompressor Pipeline 集成
  ├── Task 1C: 统计检验模块
  └── Task 1D: LLMLingua 算法适配

Round 2 (依赖 Round 1):
  ├── Task 2A: ComparisonExperiment 重构 (依赖 1A)
  └── Task 2B: 多数据集批量运行支持 (依赖 1A)

Round 3 (依赖 Round 2):
  ├── Task 3A: 可视化增强
  └── Task 3B: LaTeX 表格导出
```

---

## Round 1: 基础模块 (可完全并行)

### Task 1A: 结果收集器实现

**目标**: 创建结果收集机制，让评测 Operators 的结果可以被程序化收集

**输出文件**: 
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/experiments/results_collector.py`
- 修改 `packages/sage-middleware/src/sage/middleware/operators/rag/evaluate.py`

**Prompt**:
```
你是 SAGE 框架的开发者。请实现一个结果收集器模块。

## 背景
当前 `sage.middleware.operators.rag.evaluate` 中的评测 Operators (F1Evaluate, TokenCountEvaluate, LatencyEvaluate, CompressionRateEvaluate) 只将结果打印到控制台，无法被程序化收集。

## 任务
1. 创建 `results_collector.py`，实现 `ResultsCollector` 类：
   - 单例模式，全局可访问
   - `add_sample(sample_id, metrics: dict)` 添加单个样本结果
   - `get_results() -> list[dict]` 获取所有结果
   - `get_aggregated() -> dict` 获取聚合统计
   - `reset()` 清空
   - `export_json(path)` 导出到文件

2. 修改 `evaluate.py` 中的评测 Operators：
   - 在 `execute()` 方法中，除了打印，还要调用 `ResultsCollector` 收集结果
   - 保持向后兼容（打印行为不变）

## 参考代码位置
- 评测 Operators: `packages/sage-middleware/src/sage/middleware/operators/rag/evaluate.py`
- 现有聚合器: 同文件中的 `MetricsAggregator` 类

## 接口示例
```python
from sage.benchmark.benchmark_refiner.experiments.results_collector import ResultsCollector

collector = ResultsCollector()
collector.reset()

# Pipeline 运行后
results = collector.get_results()
# [{"sample_id": 0, "f1": 0.35, "compression_rate": 2.5, ...}, ...]

aggregated = collector.get_aggregated()
# {"avg_f1": 0.35, "std_f1": 0.02, "avg_compression_rate": 2.5, ...}
```

## 注意事项
- 使用线程安全的实现（Pipeline 可能并行）
- 不要破坏现有的 `MetricsAggregator` 功能
- 添加单元测试到 `packages/sage-benchmark/tests/unit/benchmark_refiner/test_results_collector.py`
```

---

### Task 1B: AdaptiveCompressor Pipeline 集成

**目标**: 将新的 AdaptiveCompressor 算法集成到 benchmark 框架

**输出文件**:
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/config/config_adaptive.yaml`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/implementations/pipelines/adaptive_rag.py`
- `packages/sage-middleware/src/sage/middleware/components/sage_refiner/__init__.py` (添加导出)

**Prompt**:
```
你是 SAGE 框架的开发者。请将 AdaptiveCompressor 算法集成到 benchmark 框架。

## 背景
AdaptiveCompressor 是一个新实现的 RAG 上下文压缩算法，位于:
`packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/adaptive/`

它包含:
- `AdaptiveCompressor`: 主压缩器
- `QueryClassifier`: 查询类型分类
- `GranularitySelector`: 多粒度选择
- `InformationDensityAnalyzer`: MMR 多样性选择

## 任务
1. 创建 `AdaptiveRefinerOperator`：
   - 参考 `LongRefinerOperator`, `REFORMRefinerOperator` 的实现模式
   - 位置: `packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/adaptive/operator.py`
   - 继承 `MapFunction`，实现 `execute()` 方法
   - 输入: `{"query": str, "retrieval_results": list[dict]}`
   - 输出: 添加 `{"refining_results": list[str], "compressed_context": str, "refine_time": float}`

2. 创建配置文件 `config_adaptive.yaml`：
   - 参考 `config_longrefiner.yaml` 的结构
   - 添加 `adaptive` 配置节

3. 创建 Pipeline `adaptive_rag.py`：
   - 参考 `longrefiner_rag.py` 的结构
   - 使用 `AdaptiveRefinerOperator`

4. 更新导出：
   - 在 `sage_refiner/__init__.py` 中导出 `AdaptiveRefinerOperator`
   - 在 `sage.middleware.components.sage_refiner` 中导出

## 参考文件
- LongRefiner Operator: `algorithms/LongRefiner/operator.py`
- REFORM Operator: `algorithms/reform/operator.py`
- Pipeline 示例: `implementations/pipelines/longrefiner_rag.py`
- Config 示例: `config/config_longrefiner.yaml`

## AdaptiveCompressor 接口
```python
from sage_refiner.algorithms.adaptive import AdaptiveCompressor

compressor = AdaptiveCompressor(
    use_query_classifier=True,
    diversity_weight=0.3,
)
result = compressor.compress(
    context="...",
    question="What is...?",
    budget=2048,
)
# result.compressed_context, result.compression_rate, result.processing_time_ms
```

## 注意事项
- 保持与其他 Refiner Operators 的接口一致
- 配置文件使用 YAML 格式，支持环境变量 `${HOME}`
- 添加测试模式检测 (`SAGE_TEST_MODE`)
```

---

### Task 1C: 统计检验模块

**目标**: 实现统计显著性检验，满足 ICML 审稿要求

**输出文件**:
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/analysis/statistical.py`
- `packages/sage-benchmark/tests/unit/benchmark_refiner/test_statistical.py`

**Prompt**:
```
你是 SAGE 框架的开发者。请实现统计检验模块。

## 背景
ICML 论文需要统计显著性检验来验证算法改进是否显著。

## 任务
创建 `statistical.py`，实现以下功能：

1. **配对 t 检验**:
```python
def paired_t_test(
    baseline_scores: list[float],
    method_scores: list[float],
) -> dict:
    """
    Returns:
        {"t_statistic": float, "p_value": float, "significant": bool}
    """
```

2. **Bootstrap 置信区间**:
```python
def bootstrap_confidence_interval(
    scores: list[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """
    Returns:
        (lower_bound, upper_bound)
    """
```

3. **Cohen's d 效应量**:
```python
def cohens_d(
    baseline_scores: list[float],
    method_scores: list[float],
) -> float:
    """
    Returns:
        Effect size (small: 0.2, medium: 0.5, large: 0.8)
    """
```

4. **多重比较校正** (Bonferroni):
```python
def bonferroni_correction(
    p_values: list[float],
    alpha: float = 0.05,
) -> list[bool]:
    """
    Returns:
        List of booleans indicating significance after correction
    """
```

5. **统计报告生成**:
```python
def generate_significance_report(
    results: dict[str, list[float]],  # {"baseline": [...], "longrefiner": [...], ...}
    baseline_name: str = "baseline",
) -> str:
    """
    Returns:
        Markdown formatted significance report
    """
```

## 依赖
- 使用 `scipy.stats` 进行统计检验
- 使用 `numpy` 进行数值计算

## 输出格式示例
```
## Statistical Significance Report

| Method      | Mean F1 | 95% CI        | vs Baseline p | Cohen's d | Sig.  |
|-------------|---------|---------------|---------------|-----------|-------|
| baseline    | 0.350   | [0.34, 0.36]  | -             | -         | -     |
| longrefiner | 0.380   | [0.37, 0.39]  | 0.001**       | 0.75      | Yes   |
| reform      | 0.360   | [0.35, 0.37]  | 0.023*        | 0.25      | Yes   |
| adaptive    | 0.400   | [0.39, 0.41]  | <0.001***     | 1.20      | Yes   |

* p < 0.05, ** p < 0.01, *** p < 0.001
```

## 注意事项
- 处理样本量不足的情况（< 30 时使用 t 分布）
- 添加完整的单元测试
- 不依赖其他 benchmark_refiner 模块
```

---

### Task 1D: LLMLingua 算法适配

**目标**: 将 LLMLingua 作为 SOTA baseline 集成到 benchmark

**输出文件**:
- `packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/llmlingua/__init__.py`
- `packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/llmlingua/compressor.py`
- `packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/sage_refiner/algorithms/llmlingua/operator.py`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/config/config_llmlingua.yaml`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/implementations/pipelines/llmlingua_rag.py`

**Prompt**:
```
你是 SAGE 框架的开发者。请集成 LLMLingua 作为 SOTA baseline。

## 背景
LLMLingua 是微软发布的提示词压缩算法，是 RAG 上下文压缩领域的重要 baseline。
- 论文: https://arxiv.org/abs/2310.05736
- 官方库: https://github.com/microsoft/LLMLingua
- PyPI: `pip install llmlingua`

项目中已有部分集成代码可参考:
`packages/sage-benchmark/src/sage/benchmark/benchmark_memory/experiment/libs/pre_insert.py` (搜索 `llmlingua`)

## 任务
1. 创建 `LLMLinguaCompressor` 类：
   - 封装 `llmlingua.PromptCompressor`
   - 提供与 `AdaptiveCompressor` 一致的接口
   - 支持 LLMLingua-2 (BERT-based)

```python
class LLMLinguaCompressor:
    def __init__(
        self,
        model_name: str = "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
        use_llmlingua2: bool = True,
        device: str = "cuda",
    ):
        pass

    def compress(
        self,
        context: str,
        question: str,
        budget: int = 2048,
        compression_ratio: float = 0.5,
    ) -> CompressionResult:
        """
        Returns:
            CompressionResult with compressed_context, compression_rate, etc.
        """
        pass
```

2. 创建 `LLMLinguaRefinerOperator`：
   - 继承 `MapFunction`
   - 与其他 Refiner Operators 接口一致

3. 创建配置和 Pipeline：
   - `config_llmlingua.yaml`
   - `llmlingua_rag.py`

4. 更新算法注册：
   - 在 `algorithms/__init__.py` 中添加可选导入
   - 在 `base_experiment.py` 的 `RefinerAlgorithm` 枚举中添加

## 关键配置参数
```yaml
llmlingua:
  enabled: true
  model_name: "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
  use_llmlingua2: true
  compression_ratio: 0.5  # 目标压缩到原文的 50%
  force_tokens:  # 保留的特殊 token
    - "\n"
    - "."
    - "?"
  device: "cuda:0"
```

## 注意事项
- `llmlingua` 是可选依赖，使用 try/except 处理 ImportError
- 如果 LLMLingua 不可用，提供简单截断作为后备
- 添加测试时跳过 GPU 相关测试 (`@pytest.mark.skipif`)
```

---

## Round 2: 集成层 (依赖 Round 1)

### Task 2A: ComparisonExperiment 重构

**依赖**: Task 1A (ResultsCollector)

**目标**: 让 `ComparisonExperiment` 调用真实 Pipeline 并收集结果

**输出文件**:
- 修改 `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/experiments/comparison_experiment.py`

**Prompt**:
```
你是 SAGE 框架的开发者。请重构 ComparisonExperiment 以调用真实 Pipeline。

## 前置条件
Task 1A 已完成，`ResultsCollector` 可用：
```python
from sage.benchmark.benchmark_refiner.experiments.results_collector import ResultsCollector
```

## 背景
当前 `ComparisonExperiment._process_sample_placeholder()` 生成模拟数据。
需要修改为调用真实的 Pipeline 并收集评测结果。

## 任务
重构 `comparison_experiment.py`：

1. **删除** `_process_sample_placeholder()` 方法

2. **重写** `_execute_pipeline()` 方法：
```python
def _execute_pipeline(self, algorithm: str) -> list[dict[str, Any]]:
    """
    执行真实 Pipeline 并收集结果
    
    步骤:
    1. 加载对应的 config 文件
    2. 动态修改 config 中的 source.max_samples
    3. 重置 ResultsCollector
    4. 运行 Pipeline
    5. 从 ResultsCollector 获取结果
    """
```

3. **添加** Pipeline 运行逻辑：
```python
def _run_pipeline_module(self, algorithm: str, config: dict) -> None:
    """
    运行指定算法的 Pipeline
    
    方案: 直接 import 并调用 pipeline_run 函数
    """
    if algorithm == "baseline":
        from ...implementations.pipelines.baseline_rag import pipeline_run
    elif algorithm == "longrefiner":
        from ...implementations.pipelines.longrefiner_rag import pipeline_run
    # ... 其他算法
    
    pipeline_run(config)
```

4. **添加** 配置加载和修改：
```python
def _load_and_modify_config(self, algorithm: str) -> dict:
    """
    加载算法配置并修改实验参数
    - 修改 source.max_samples
    - 修改 source.hf_dataset_config (如果指定了数据集)
    """
```

## 参考文件
- 现有实现: `experiments/comparison_experiment.py`
- Pipeline 示例: `implementations/pipelines/baseline_rag.py`
- 配置文件: `config/config_baseline.yaml`

## 执行流程
```
ComparisonExperiment.run()
  └── for algorithm in algorithms:
        ├── _load_and_modify_config(algorithm)
        ├── ResultsCollector.reset()
        ├── _run_pipeline_module(algorithm, config)
        ├── results = ResultsCollector.get_results()
        └── metrics = _calculate_metrics(results)
```

## 注意事项
- Pipeline 运行使用 `time.sleep()` 等待，需要改为检测完成
- 处理 Pipeline 异常情况
- 支持超时配置
- 保持与现有 CLI 兼容
```

---

### Task 2B: 多数据集批量运行支持

**依赖**: Task 1A (ResultsCollector)

**目标**: 让 CLI 支持一次运行多个数据集的实验

**输出文件**:
- 修改 `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/cli.py`
- 修改 `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/experiments/base_experiment.py`

**Prompt**:
```
你是 SAGE 框架的开发者。请添加多数据集批量运行支持。

## 前置条件
Task 1A 已完成，结果可以被程序化收集。

## 背景
当前需要手动修改 config 文件的 `hf_dataset_config` 来切换数据集。
需要支持命令行一次指定多个数据集。

## 任务

1. **修改 CLI** (`cli.py`)：
```python
@click.option(
    "--datasets",
    default="nq",
    help="Comma-separated dataset names: nq,hotpotqa,triviaqa,2wikimultihopqa,asqa"
)
def compare(algorithms, datasets, samples, ...):
    dataset_list = [d.strip() for d in datasets.split(",")]
    # 对每个数据集运行实验
```

2. **修改 RefinerExperimentConfig** (`base_experiment.py`)：
```python
@dataclass
class RefinerExperimentConfig:
    # 改为支持多数据集
    datasets: list[str] = field(default_factory=lambda: ["nq"])
    # ... 其他字段
```

3. **修改 ComparisonExperiment**：
```python
def run(self) -> ExperimentResult:
    all_results = {}
    for dataset in self.config.datasets:
        self._log(f"Running on dataset: {dataset}")
        dataset_results = self._run_on_dataset(dataset)
        all_results[dataset] = dataset_results
    
    return self._aggregate_results(all_results)
```

4. **结果聚合**：
- 按数据集分组存储原始结果
- 支持跨数据集的平均性能计算
- 支持单独查看每个数据集的结果

## FlashRAG 可用数据集
```python
AVAILABLE_DATASETS = [
    "nq",           # Natural Questions
    "triviaqa",     # TriviaQA
    "hotpotqa",     # HotpotQA (multi-hop)
    "2wikimultihopqa",  # 2Wiki Multi-hop
    "musique",      # Musique (multi-hop)
    "asqa",         # ASQA (long-form)
    "popqa",        # PopQA
    "webq",         # WebQuestions
]
```

## CLI 使用示例
```bash
# 单数据集
sage-refiner-bench compare --algorithms baseline,longrefiner --datasets nq --samples 100

# 多数据集
sage-refiner-bench compare \
    --algorithms baseline,longrefiner,reform,adaptive \
    --datasets nq,hotpotqa,2wikimultihopqa \
    --samples 500 \
    --output results/icml_main.json
```

## 输出格式
```json
{
  "experiment_id": "...",
  "datasets": {
    "nq": {
      "algorithm_metrics": {...},
      "raw_results": [...]
    },
    "hotpotqa": {
      "algorithm_metrics": {...},
      "raw_results": [...]
    }
  },
  "aggregated": {
    "algorithm_metrics": {...}  // 跨数据集平均
  }
}
```

## 注意事项
- 数据集名称需要与 FlashRAG 的 config 名称一致
- 添加数据集验证
- 支持 `--datasets all` 运行所有可用数据集
```

---

## Round 3: 呈现层 (依赖 Round 2)

### Task 3A: 可视化增强

**依赖**: Task 2A, 2B (完整的实验结果)

**目标**: 添加算法对比可视化图表

**输出文件**:
- 修改 `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/analysis/visualization.py`

**Prompt**:
```
你是 SAGE 框架的开发者。请增强可视化模块。

## 前置条件
Task 2A/2B 已完成，可以获取完整的多算法、多数据集实验结果。

## 背景
当前 `visualization.py` 只有 attention head 的 MNR 曲线。
需要添加算法对比相关的可视化。

## 任务
在 `visualization.py` 中添加以下函数：

1. **算法性能对比柱状图**:
```python
def plot_algorithm_comparison(
    results: dict[str, AlgorithmMetrics],
    metric: str = "f1",  # f1, compression_rate, total_time
    output_path: str | Path = None,
    title: str = None,
) -> plt.Figure:
    """
    绘制多算法在单一指标上的对比柱状图
    - 包含误差棒 (std)
    - 标注最佳值
    """
```

2. **Pareto 前沿图**:
```python
def plot_pareto_frontier(
    results: dict[str, AlgorithmMetrics],
    x_metric: str = "compression_rate",
    y_metric: str = "f1",
    output_path: str | Path = None,
) -> plt.Figure:
    """
    绘制 F1 vs Compression 的 Pareto 前沿
    - 标注 Pareto 最优点
    - 不同算法用不同颜色/标记
    """
```

3. **延迟分解堆叠图**:
```python
def plot_latency_breakdown(
    results: dict[str, AlgorithmMetrics],
    output_path: str | Path = None,
) -> plt.Figure:
    """
    绘制各算法的延迟分解
    - 堆叠: retrieve_time, refine_time, generate_time
    """
```

4. **跨数据集热力图**:
```python
def plot_dataset_heatmap(
    results: dict[str, dict[str, AlgorithmMetrics]],  # {dataset: {algo: metrics}}
    metric: str = "f1",
    output_path: str | Path = None,
) -> plt.Figure:
    """
    绘制算法×数据集的性能热力图
    - 行: 算法
    - 列: 数据集
    - 颜色: 指标值
    """
```

5. **雷达图**:
```python
def plot_radar_chart(
    results: dict[str, AlgorithmMetrics],
    metrics: list[str] = ["f1", "compression_rate", "speed"],
    output_path: str | Path = None,
) -> plt.Figure:
    """
    多维度对比雷达图
    - 指标需要归一化到 0-1
    """
```

## 依赖
- matplotlib
- seaborn (热力图)
- numpy

## 样式要求
- 使用统一的颜色方案
- 支持保存为 PDF (论文用) 和 PNG
- 图表标题和轴标签使用英文
- DPI >= 300

## 注意事项
- 处理缺失数据
- 添加图例
- 支持自定义颜色映射
```

---

### Task 3B: LaTeX 表格导出

**依赖**: Task 2A, 2B, Task 1C (统计检验)

**目标**: 自动生成论文用的 LaTeX 表格

**输出文件**:
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/analysis/latex_export.py`

**Prompt**:
```
你是 SAGE 框架的开发者。请实现 LaTeX 表格导出功能。

## 前置条件
- Task 1C (统计检验) 已完成
- Task 2A/2B (实验结果) 已完成

## 任务
创建 `latex_export.py`，实现论文表格生成：

1. **主结果表格**:
```python
def generate_main_results_table(
    results: dict[str, dict[str, AlgorithmMetrics]],  # {dataset: {algo: metrics}}
    baseline: str = "baseline",
    metrics: list[str] = ["f1", "compression_rate", "total_time"],
    include_significance: bool = True,
) -> str:
    """
    生成主实验结果表格
    
    格式:
    \begin{table}[t]
    \caption{Main Results on RAG Benchmarks}
    \begin{tabular}{l|ccc|ccc|ccc}
    \toprule
    & \multicolumn{3}{c}{NQ} & \multicolumn{3}{c}{HotpotQA} & ...
    Method & F1 & Comp. & Time & F1 & Comp. & Time & ...
    \midrule
    Baseline & 0.35 & 1.0× & 2.5s & ...
    LongRefiner & \textbf{0.38}$^{**}$ & 3.0× & 3.5s & ...
    \bottomrule
    \end{tabular}
    \end{table}
    """
```

2. **消融实验表格**:
```python
def generate_ablation_table(
    results: dict[str, AlgorithmMetrics],
    components: list[str],  # ["w/o query classifier", "w/o MMR", ...]
) -> str:
    """
    生成消融实验表格
    """
```

3. **统计显著性表格**:
```python
def generate_significance_table(
    raw_results: dict[str, list[dict]],  # {algo: [sample_results]}
    baseline: str = "baseline",
) -> str:
    """
    生成完整的统计检验表格
    包含: p-value, Cohen's d, 95% CI
    """
```

4. **压缩案例展示**:
```python
def generate_case_study_table(
    cases: list[dict],  # [{"query": ..., "original": ..., "compressed": ...}]
    max_cases: int = 3,
) -> str:
    """
    生成压缩效果案例展示表格
    """
```

## LaTeX 格式要求
- 使用 booktabs 包 (\toprule, \midrule, \bottomrule)
- 最佳值加粗 (\textbf)
- 显著性标记: $^{*}$ (p<0.05), $^{**}$ (p<0.01), $^{***}$ (p<0.001)
- 数值保留适当小数位
- 支持多行表头

## 输出示例
```latex
\begin{table}[t]
\centering
\caption{Performance comparison on RAG benchmarks. Best results are in \textbf{bold}. 
$^{*}$/$^{**}$/$^{***}$ indicate statistical significance at p<0.05/0.01/0.001.}
\label{tab:main_results}
\begin{tabular}{l|ccc}
\toprule
Method & F1 $\uparrow$ & Compression $\uparrow$ & Latency (s) $\downarrow$ \\
\midrule
Baseline & 0.350 & 1.0× & 2.50 \\
LongRefiner & 0.380$^{**}$ & \textbf{3.0×} & 3.50 \\
REFORM & 0.360$^{*}$ & 2.5× & 2.80 \\
Adaptive (Ours) & \textbf{0.400}$^{***}$ & 3.5× & \textbf{3.00} \\
\bottomrule
\end{tabular}
\end{table}
```

## CLI 集成
```bash
sage-refiner-bench report results.json --format latex --output tables/
```

## 注意事项
- 自动处理特殊字符转义
- 支持表格拆分（过宽时）
- 添加表格注释
```

---

## 任务依赖图

```
Round 1 (并行):
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ Task 1A │  │ Task 1B │  │ Task 1C │  │ Task 1D │
│ Results │  │Adaptive │  │  Stats  │  │LLMLingua│
│Collector│  │Pipeline │  │  Tests  │  │ Adapter │
└────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘
     │            │            │            │
     └────────────┴─────┬──────┴────────────┘
                        │
Round 2 (依赖 Round 1): │
┌───────────────────────┴────────────────────────┐
│                                                │
▼                                                ▼
┌─────────┐                              ┌─────────┐
│ Task 2A │                              │ Task 2B │
│Comparison│                             │  Multi  │
│Experiment│                             │ Dataset │
└────┬────┘                              └────┬────┘
     │                                        │
     └──────────────────┬─────────────────────┘
                        │
Round 3 (依赖 Round 2): │
┌───────────────────────┴────────────────────────┐
│                                                │
▼                                                ▼
┌─────────┐                              ┌─────────┐
│ Task 3A │                              │ Task 3B │
│  Visual │                              │  LaTeX  │
│  Charts │                              │ Tables  │
└─────────┘                              └─────────┘
```

---

## 执行建议

1. **Round 1**: 分配 4 个 Copilot 并行处理，预计 2-3 天
2. **Round 2**: 等 Round 1 完成后，分配 2 个 Copilot，预计 1-2 天
3. **Round 3**: 等 Round 2 完成后，分配 2 个 Copilot，预计 1 天

**总计**: 约 4-6 天完成所有开发工作

---

## 验收标准

每个 Task 完成后需要：
1. ✅ 代码通过 `sage-dev quality --check-only`
2. ✅ 单元测试通过 `pytest <test_file> -v`
3. ✅ 无循环依赖
4. ✅ 文档字符串完整

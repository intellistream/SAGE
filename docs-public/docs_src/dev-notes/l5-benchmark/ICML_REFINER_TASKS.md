# ICML Refiner 投稿任务分解

> **位置**: `docs/dev-notes/l5-benchmark/ICML_REFINER_TASKS.md` **创建日期**: 2025-12-01 **最后更新**:
> 2025-12-02 **状态**: Round 2 已完成

## 任务总览

```
Round 1 (可完全并行) ✅ 已完成:
  ├── Task 1A: 结果收集器实现 ✅
  ├── Task 1B: LongLLMLingua Pipeline 集成 ✅
  ├── Task 1C: 统计检验模块 ✅
  └── Task 1D: LLMLingua-2 Pipeline 集成 ✅

Round 2 (依赖 Round 1) ✅ 已完成:
  ├── Task 2A: ComparisonExperiment 重构 ✅
  └── Task 2B: 多数据集批量运行支持 ✅

Round 3 (依赖 Round 2):
  ├── Task 3A: 可视化增强
  └── Task 3B: LaTeX 表格导出
```

______________________________________________________________________

## 算法概览

### 当前支持的算法

| 算法              | 类型             | 描述                      | 状态    |
| ----------------- | ---------------- | ------------------------- | ------- |
| **Baseline**      | 截断             | 简单截断，无压缩          | ✅      |
| **LongRefiner**   | LLM-based        | 基于 LLM 的上下文精炼     | ✅      |
| **REFORM**        | Attention-based  | 注意力头驱动的 token 选择 | ✅      |
| **Provence**      | Provenance-aware | 出处感知压缩              | ✅      |
| **LongLLMLingua** | LLM-PPL          | 问题感知的长文档压缩      | ✅ 新增 |
| **LLMLingua-2**   | BERT-based       | 快速 token 分类压缩       | ✅ 新增 |

### 算法位置

```
packages/sage-middleware/src/sage/middleware/components/sage_refiner/sageRefiner/
  sage_refiner/algorithms/
    ├── LongRefiner/          # LongRefiner 算法
    ├── reform/               # REFORM 算法
    ├── provence/             # Provence 算法
    ├── longllmlingua/        # LongLLMLingua 算法 (新增)
    │   ├── __init__.py
    │   ├── compressor.py     # LongLLMLinguaCompressor
    │   └── operator.py       # LongLLMLinguaOperator
    └── llmlingua2/           # LLMLingua-2 算法 (新增)
        ├── __init__.py
        ├── compressor.py     # LLMLingua2Compressor
        └── operator.py       # LLMLingua2Operator
```

______________________________________________________________________

## Round 1: 基础模块 ✅ 已完成

### Task 1A: 结果收集器实现 ✅

**状态**: 已完成 (21 tests passing)

**输出文件**:

- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/experiments/results_collector.py`
- 修改 `packages/sage-middleware/src/sage/middleware/operators/rag/evaluate.py`

**实现功能**:

- `ResultsCollector` 单例类，线程安全
- `add_sample(sample_id, **metrics)` 添加单个样本结果
- `get_results() -> list[dict]` 获取所有结果
- `get_aggregated() -> dict` 获取聚合统计
- `reset()` 清空
- `export_json(path)` / `load_json(path)` 文件 I/O
- 集成到 F1Evaluate, LatencyEvaluate, CompressionRateEvaluate

______________________________________________________________________

### Task 1B: LongLLMLingua Pipeline 集成 ✅

**状态**: 已完成

**输出文件**:

- `sage_refiner/algorithms/longllmlingua/compressor.py` - LongLLMLinguaCompressor
- `sage_refiner/algorithms/longllmlingua/operator.py` - LongLLMLinguaOperator
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/config/config_longllmlingua.yaml`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/implementations/pipelines/longllmlingua_rag.py`

**算法特性**:

- 问题感知的上下文排序 (`rank_method="longllmlingua"`)
- 对比 perplexity 评估 (`condition_compare=True`)
- 动态压缩比例 (`dynamic_context_compression_ratio=0.3`)
- 上下文重排序 (`reorder_context="sort"`)

**Paper Baseline 配置**:

```yaml
longllmlingua:
  model_name: "NousResearch/Llama-2-7b-hf"
  rate: 0.55                          # 压缩率 (论文默认)
  condition_in_question: "after"      # Question 放在 context 之后
  condition_compare: true             # 对比 perplexity
  reorder_context: "sort"             # 按相关性排序
  dynamic_context_compression_ratio: 0.3
```

**接口示例**:

```python
from sage.middleware.components.sage_refiner import LongLLMLinguaCompressor

compressor = LongLLMLinguaCompressor(
    model_name="NousResearch/Llama-2-7b-hf",
    device="cuda:0",
)
result = compressor.compress(
    context=["Document 1...", "Document 2..."],
    question="What is the main topic?",
    rate=0.55,
)
# result["compressed_prompt"], result["compression_rate"], result["processing_time"]
```

______________________________________________________________________

### Task 1C: 统计检验模块 ✅

**状态**: 已完成 (38 tests passing)

**输出文件**:

- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/analysis/statistical.py`

**实现功能**:

- `paired_t_test(baseline, method)` - 配对 t 检验
- `bootstrap_confidence_interval(scores, n_bootstrap, confidence)` - Bootstrap 置信区间
- `cohens_d(baseline, method)` - Cohen's d 效应量
- `bonferroni_correction(p_values, alpha)` - Bonferroni 多重比较校正
- `holm_bonferroni_correction(p_values, alpha)` - Holm-Bonferroni 校正
- `wilcoxon_test(baseline, method)` - Wilcoxon 符号秩检验
- `generate_significance_report(results, baseline_name)` - 生成 Markdown 报告
- `compute_all_statistics(results, baseline_name)` - 计算所有统计量

______________________________________________________________________

### Task 1D: LLMLingua-2 Pipeline 集成 ✅

**状态**: 已完成 (14 tests passing)

**输出文件**:

- `sage_refiner/algorithms/llmlingua2/compressor.py` - LLMLingua2Compressor
- `sage_refiner/algorithms/llmlingua2/operator.py` - LLMLingua2Operator
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/config/config_llmlingua2.yaml`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/implementations/pipelines/llmlingua2_rag.py`

**算法特性**:

- 基于 BERT 的快速 token 分类压缩
- 无需 LLM 推理，速度快
- 多语言支持 (mBERT, XLM-RoBERTa)
- 支持 context-level + token-level 双重过滤

**配置**:

```yaml
llmlingua2:
  model_name: "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"
  device: "cuda:0"
  rate: 0.5                           # 压缩到 50%
  use_context_level_filter: true      # 粗粒度过滤
  use_token_level_filter: true        # 细粒度过滤
  force_tokens: ["\n", ".", "?", "!"] # 保留的特殊 token
```

**接口示例**:

```python
from sage.middleware.components.sage_refiner import LLMLingua2Compressor

compressor = LLMLingua2Compressor(
    model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    device="cuda:0",
)
result = compressor.compress(
    context=["This is the first document.", "This is the second document."],
    rate=0.5,
)
# result["compressed_prompt"], result["compression_rate"]
```

______________________________________________________________________

## Round 2: 集成层 ✅ 已完成

### Task 2A: ComparisonExperiment 重构 ✅

**状态**: 已完成

**依赖**: Task 1A (ResultsCollector)

**目标**: 让 `ComparisonExperiment` 调用真实 Pipeline 并收集结果

**输出文件**:

- 修改
  `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/experiments/comparison_experiment.py`

**实现功能**:

- `_execute_pipeline(algorithm)` - 执行真实 Pipeline 并收集结果
- `_load_and_modify_config(algorithm, dataset)` - 加载并修改配置
- `_run_pipeline_module(algorithm, config)` - 动态导入并运行 Pipeline
- `_run_on_dataset(dataset)` - 在单个数据集上运行所有算法
- `_aggregate_results(all_results)` - 聚合多数据集结果
- `MultiDatasetExperimentResult` - 多数据集结果容器
- `DatasetResult` - 单数据集结果容器

**Pipeline 映射**:

| 算法          | Pipeline 模块          |
| ------------- | ---------------------- |
| baseline      | `baseline_rag.py`      |
| longrefiner   | `longrefiner_rag.py`   |
| reform        | `reform_rag.py`        |
| provence      | `provence_rag.py`      |
| longllmlingua | `longllmlingua_rag.py` |
| llmlingua2    | `llmlingua2_rag.py`    |

**参考 Prompt** (已完成，保留供参考):

````
你是 SAGE 框架的开发者。请重构 ComparisonExperiment 以调用真实 Pipeline。

## 前置条件
Task 1A 已完成，`ResultsCollector` 可用：
```python
from sage.benchmark.benchmark_refiner.experiments.results_collector import ResultsCollector
````

## 背景

当前 `ComparisonExperiment._process_sample_placeholder()` 生成模拟数据。 需要修改为调用真实的 Pipeline 并收集评测结果。

## 任务

重构 `comparison_experiment.py`：

1. **删除** `_process_sample_placeholder()` 方法

1. **重写** `_execute_pipeline()` 方法：

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

    算法到 Pipeline 映射:
    - baseline -> baseline_rag.py
    - longrefiner -> longrefiner_rag.py
    - reform -> reform_rag.py
    - provence -> provence_rag.py
    - longllmlingua -> longllmlingua_rag.py
    - llmlingua2 -> llmlingua2_rag.py
    """
    if algorithm == "baseline":
        from ...implementations.pipelines.baseline_rag import pipeline_run
    elif algorithm == "longrefiner":
        from ...implementations.pipelines.longrefiner_rag import pipeline_run
    elif algorithm == "reform":
        from ...implementations.pipelines.reform_rag import pipeline_run
    elif algorithm == "provence":
        from ...implementations.pipelines.provence_rag import pipeline_run
    elif algorithm == "longllmlingua":
        from ...implementations.pipelines.longllmlingua_rag import pipeline_run
    elif algorithm == "llmlingua2":
        from ...implementations.pipelines.llmlingua2_rag import pipeline_run

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

````

---

### Task 2B: 多数据集批量运行支持 ✅

**状态**: 已完成

**依赖**: Task 1A (ResultsCollector)

**目标**: 让 CLI 支持一次运行多个数据集的实验

**输出文件**:
- 修改 `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/cli.py`
- 修改 `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/experiments/base_experiment.py`

**实现功能**:
- `--datasets` CLI 参数，支持逗号分隔的数据集名或 "all"
- `RefinerExperimentConfig.datasets: list[str]` 字段
- `RefinerExperimentConfig.get_datasets()` 方法
- `AVAILABLE_DATASETS` 常量 (8 个 FlashRAG 数据集)
- `validate()` 方法验证数据集有效性
- 向后兼容废弃的 `--dataset` 参数

**可用数据集**:
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
````

**CLI 使用示例**:

```bash
# 单数据集
sage-refiner-bench compare --algorithms baseline,longrefiner --datasets nq --samples 100

# 多数据集
sage-refiner-bench compare \
    --algorithms baseline,longrefiner,reform,longllmlingua,llmlingua2 \
    --datasets nq,hotpotqa,2wikimultihopqa \
    --samples 500 \
    --output results/icml_main.json

# 所有数据集
sage-refiner-bench compare --algorithms baseline,longrefiner --datasets all
```

______________________________________________________________________

## Round 3: 呈现层 (依赖 Round 2)

### Task 3A: 可视化增强

**依赖**: Task 2A, 2B (完整的实验结果)

**目标**: 添加算法对比可视化图表

**输出文件**:

- 修改 `packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/analysis/visualization.py`

**Prompt**:

````
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
````

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
    LongLLMLingua & 0.37$^{*}$ & 3.2× & 4.0s & ...
    LLMLingua-2 & 0.36 & 2.8× & \textbf{1.5s} & ...
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

- 使用 booktabs 包 (\\toprule, \\midrule, \\bottomrule)
- 最佳值加粗 (\\textbf)
- 显著性标记: $^{*}$ (p\<0.05), $^{**}$ (p\<0.01), $^{***}$ (p\<0.001)
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
LongLLMLingua & 0.375$^{**}$ & 3.2× & 4.00 \\
LLMLingua-2 & 0.355 & 2.8× & \textbf{1.50} \\
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

Round 1 (并行) ✅: ┌─────────┐ ┌─────────────┐ ┌─────────┐ ┌────────────┐ │ Task 1A │ │ Task 1B │ │
Task 1C │ │ Task 1D │ │ Results │ │LongLLMLingua│ │ Stats │ │ LLMLingua2 │ │Collector│ │ Pipeline │
│ Tests │ │ Pipeline │ └────┬────┘ └──────┬──────┘ └────┬────┘ └─────┬──────┘ │ │ │ │
└──────────────┴──────┬───────┴─────────────┘ │ Round 2 (依赖 Round 1): │
┌──────────────────────────┴─────────────────────────┐ │ │ ▼ ▼ ┌─────────┐ ┌─────────┐ │ Task 2A │ │
Task 2B │ │Comparison│ │ Multi │ │Experiment│ │ Dataset │ └────┬────┘ └────┬────┘ │ │
└────────────────────┬───────────────────────┘ │ Round 3 (依赖 Round 2): │
┌─────────────────────────┴──────────────────────────┐ │ │ ▼ ▼ ┌─────────┐ ┌─────────┐ │ Task 3A │ │
Task 3B │ │ Visual │ │ LaTeX │ │ Charts │ │ Tables │ └─────────┘ └─────────┘

```

---

## 验收标准

每个 Task 完成后需要：
1. ✅ 代码通过 `sage-dev quality --check-only`
2. ✅ 单元测试通过 `pytest <test_file> -v`
3. ✅ 无循环依赖
4. ✅ 文档字符串完整

---

## 相关文档

- [benchmark_refiner README](../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/README.md)
- [ICML Roadmap](../../../../packages/sage-benchmark/src/sage/benchmark/benchmark_refiner/ICML_ROADMAP.md)
- [LLMLingua 集成任务](../l4-middleware/refiner-llmlingua-integration-tasks.md)

---

## 更新日志

- **2025-12-02**: Round 2 完成 (Task 2A ComparisonExperiment 重构, Task 2B 多数据集批量运行支持)
- **2025-12-02**: 更新算法列表，移除 Adaptive/LLMLingua，新增 LongLLMLingua/LLMLingua-2
- **2025-12-01**: 初始版本，Round 1 任务完成
```

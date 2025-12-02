# Agent Capability Benchmark (Task 2) Decomposition

## 子任务1：实验配置与运行基座（Configs & Experiment Runner Core）

### 1. 子任务概述
- **子任务名称**：Config-driven Experiment Kernel
- **核心目标**：提供统一的 YAML 配置体系、Experiment 抽象基类、三类实验 runner（工具选择/规划/时机判断），并接入 DataManager 以驱动后续评估。
- **独立性说明**：负责 `config/` 与 `experiments/` 目录及 CLI 入口，仅依赖稳定的接口（metrics 由子任务2提供、策略由子任务3实现）。通过接口/协议读取策略和评估组件，确保可单独开发和测试。

### 2. 详细规格
#### 2.1 目录结构
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── __init__.py                          # Registry 暴露
├── README.md                            # 模块说明
├── config/
│   ├── default_config.yaml              # 通用设置（数据源、日志、输出路径）
│   ├── tool_selection_exp.yaml          # 工具选择实验配置
│   ├── planning_exp.yaml                # 规划实验配置
│   └── timing_detection_exp.yaml        # 时机判断实验配置
└── experiments/
    ├── base_experiment.py               # Experiment 抽象类 + Config pydantic 模型
    ├── tool_selection_exp.py            # ToolSelectionExperiment 实现
    ├── planning_exp.py                  # PlanningExperiment 实现
    └── timing_detection_exp.py          # TimingDetectionExperiment 实现
```
> 该子任务 **不** 负责 `evaluation/`、`implementations/`。

#### 2.2 接口与数据流
- **配置模型**（示例：`ToolSelectionConfig`）
  ```python
  class ToolSelectionConfig(BaseModel):
      profile: str = "full_eval"          # agent_eval usage profile
      split: str = "dev"
      metrics: List[str] = ["top_k_accuracy", "recall@5"]
      selector: str = "baseline.keyword"
      top_k: int = 5
      output_dir: Path
  ```
- **Experiment 基类**
  ```python
  class BaseExperiment(ABC):
      def __init__(self, config: ExperimentConfig, data_manager: DataManager, adapter_registry: SelectorRegistry):
          self.config = config
          self.dm = data_manager
          self.selector_registry = adapter_registry

      @abstractmethod
      def run(self) -> ExperimentResult:
          ...
  ```
- **数据流**：
  1. 加载 YAML → pydantic Config。
  2. DataManager `get_by_usage("agent_eval")` → profile → 对应数据源 loader。
  3. Experiment 调用策略 Adapter（来自子任务3）执行推理，生成预测。
  4. 将预测结构（如 `List[ToolPrediction]`）传递给 metrics evaluator（子任务2）。
- **配置示例 (`config/tool_selection_exp.yaml`)**
  ```yaml
  experiment: tool_selection
  profile: quick_eval
  split: dev
  selector: baseline.keyword
  top_k: 5
  metrics:
    - top_k_accuracy
    - coverage@10
  report:
    format: ["json", "markdown"]
    path: ${PROJECT_ROOT}/outputs/agent_benchmark/tool_selection
  ```

#### 2.3 代码实现清单
- `ExperimentConfigLoader`：解析 YAML，支持变量替换，返回 pydantic 对象。
- `BaseExperiment`：定义生命周期（`prepare()`, `run_iteration()`, `finalize()`）。
- `ToolSelectionExperiment`：实现 `run()`，迭代 benchmark samples，调用策略 adapter 获取预测。
- `PlanningExperiment`：加载规划样本，跟踪计划步骤与实际执行。
- `TimingDetectionExperiment`：调用策略判断是否触发工具。
- `ExperimentResult` 数据类：包含原始预测、metrics 输入占位。
- CLI 入口（可选）`python -m sage.benchmark.benchmark_agent --config ...` 由该子任务提供。

#### 2.4 集成方式
- **与子任务2**：`run()` 中返回 `ExperimentResult`（包含 `predictions`, `references`, `metadata`），再交由 evaluator 处理。
- **与子任务3**：通过 `selector_registry.get(self.config.selector)` 获取策略对象，调用统一接口：
  ```python
  class ToolSelectorProtocol(Protocol):
      def predict(self, query: ToolSelectionQuery, top_k: int) -> List[ToolPrediction]: ...
  ```
- **DataManager 访问示例**：
  ```python
  dm = DataManager.get_instance()
  agent_eval = dm.get_by_usage("agent_eval")
  profile = agent_eval.load_profile(config.profile)
  benchmark_loader = profile["benchmark"]
  samples = benchmark_loader.iter_split(config.task_type, config.split)
  ```

#### 2.5 验证标准
- **单测**（位于 `packages/sage-benchmark/tests/benchmark_agent/test_experiments.py`）：
  - YAML → Config 解析正确。
  - `ToolSelectionExperiment` 在 mock DataManager + mock selector 下可运行并产出结构化结果。
  - CLI 参数解析与默认配置加载。
- **功能验证**：使用小型 mock JSONL（3 条样本）执行 `run()` 并生成临时 `ExperimentResult`。
- **扩展性**：BaseExperiment 支持批量/流式；配置可切换不同 profile；保证无阻塞地接入新策略。

### 3. 实施指导
#### 3.1 开发顺序
1. 参考 `benchmark_rag` 的 config + runner 结构，搭建 `BaseExperiment` 与 config loader。
2. 接入 DataManager mock，完成三类 Experiment skeleton。
3. 实现 CLI/entry（可选）并补齐 README 示例。
4. 编写单测，使用 fixtures 提供假样本与假 selector。

#### 3.2 技术要点
- 统一使用 `sage.common.utils.logging` 输出进度。
- Config loader 支持 env 变量/`${PROJECT_ROOT}` 插值（可复用 `benchmark_rag` 逻辑）。
- 确保 Experiment 可注入 executor（同步/异步）以支持未来并发。

#### 3.3 示例代码片段
```python
class ToolSelectionExperiment(BaseExperiment):
    def run(self) -> ExperimentResult:
        selector = self.selector_registry.get(self.config.selector)
        predictions, references = [], []
        for sample in self._iter_samples():
            pred = selector.predict(sample.query, top_k=self.config.top_k)
            predictions.append({"sample_id": sample.sample_id, "pred": pred})
            references.append(sample.ground_truth.top_k)
        return ExperimentResult(task="tool_selection", predictions=predictions, references=references)
```

### 4. 交付清单
- [ ] `config/` YAML 文件 + pydantic 模型
- [ ] `experiments/` 模块及 CLI 入口
- [ ] 文档：README 中的运行示例
- [ ] 测试：config loader & experiment runner mock tests
- [ ] 样例配置/假数据脚本（可选）

---

## 子任务2：评估指标与报告管线（Metrics, Evaluators & Analyzers）

### 1. 子任务概述
- **子任务名称**：Evaluation & Reporting Engine
- **核心目标**：实现指标计算、结果聚合、报告生成与可视化分析，覆盖三项能力；对 Experiment 输出进行消费并产生 JSON/Markdown 报告。
- **独立性说明**：负责 `evaluation/` 目录，仅依赖子任务1传入的 `ExperimentResult` 数据结构，与子任务3通过策略接口无直接耦合。

### 2. 详细规格
#### 2.1 目录结构
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
└── evaluation/
    ├── __init__.py
    ├── metrics.py                     # 指标实现（top-k accuracy, plan success, F1 等）
    ├── evaluator.py                   # EvaluationPipeline：调用 metrics + 输出报告
    ├── report_builder.py              # JSON & Markdown 报告生成
    └── analyzers/
        ├── tool_selection_analyzer.py # 误差分布、类别覆盖分析
        ├── planning_analyzer.py       # 步骤级对齐、失败原因统计
        └── timing_analyzer.py         # 混淆矩阵、置信度曲线
```

#### 2.2 接口与数据流
- **输入数据模型**：`ExperimentResult`
  ```python
  class ExperimentResult(BaseModel):
      task: Literal["tool_selection", "planning", "timing"]
      predictions: List[Dict[str, Any]]
      references: List[Dict[str, Any]]
      metadata: Dict[str, Any] = {}
  ```
- **Evaluator 接口**
  ```python
  class EvaluationPipeline:
      def __init__(self, metrics: List[Metric], analyzers: List[Analyzer], report_builder: ReportBuilder): ...
      def evaluate(self, result: ExperimentResult, config: ExperimentConfig) -> EvaluationReport:
          ...
  ```
- **Metric Protocol**
  ```python
  class Metric(Protocol):
      name: str
      def compute(self, predictions: Sequence[Any], references: Sequence[Any]) -> MetricOutput
  ```
- **报告数据结构**：
  ```python
  class EvaluationReport(BaseModel):
      task: str
      metrics: Dict[str, float]
      breakdowns: Dict[str, Any]
      artifacts: Dict[str, Path]  # JSON/Markdown 路径
  ```
- **配置示例（继承自子任务1 Config）**：
  ```yaml
  report:
    format: ["json", "markdown"]
    include_breakdowns: true
    markdown_template: report_templates/default.md.j2
  ```

#### 2.3 代码实现清单
- `metrics.py`
  - `TopKAccuracyMetric`
  - `RecallAtKMetric`
  - `PlanSuccessRate`
  - `TimingF1Metric`
  - `LatencySummary`（选填）
- `analyzers/`
  - `ToolSelectionAnalyzer`: 分类覆盖、错选工具统计
  - `PlanningAnalyzer`: 规划步骤正确率 vs 失败模式
  - `TimingAnalyzer`: 阈值扫过、ROC/F1
- `report_builder.py`
  - `JsonReportBuilder`
  - `MarkdownReportBuilder`（Jinja2 模板 or simple f-string，使用已有依赖）
- `evaluator.py`
  - `EvaluationPipeline` orchestrator
  - `load_metrics(metric_names: List[str])`
  - `save_report(EvaluationReport)`

#### 2.4 集成方式
- **来自子任务1的调用**：
  ```python
  pipeline = EvaluationPipeline.from_config(config.report, metrics_registry)
  report = pipeline.evaluate(result, config)
  ```
- **与子任务3**：无直接依赖，仅消费预测和参考。
- **DataManager**：不直接访问数据，若 analyzer 需额外信息，可从 `ExperimentResult.metadata` 中读取（由子任务1提供）。
- **可插拔策略**：Metric/Analyzer Registry 支持用户扩展。

#### 2.5 验证标准
- **单测 (`tests/benchmark_agent/test_evaluation.py`)**：
  - Metric 计算准确（使用固定预测/标签）。
  - Evaluator 可组合多个 metric/analyzer 并输出报告文件。
  - Markdown/JSON 输出内容包含指标 + 时间戳。
- **功能验证**：构造最小 `ExperimentResult`（2 条样本）运行 `evaluate()`，核对生成的文件。
- **性能**：指标计算需向量化/批处理，确保在 10k 样本下 1min 内完成（可通过 numpy/现有依赖实现）。

### 3. 实施指导
#### 3.1 开发顺序
1. 定义 Metric/Analyzer 接口 & Registry。
2. 实现核心指标（Top-K、Plan Success、Timing F1）。
3. 开发 ReportBuilder（JSON + Markdown）。
4. 编写 Evaluator orchestrator 与单测。

#### 3.2 技术要点
- 充分复用 `benchmark_rag` 的 metrics/report pipeline 代码模式。
- Markdown 报告建议使用模板生成，包含表格 + 高亮指标。
- 日志记录每个 metric 的耗时，便于优化。

#### 3.3 示例代码片段
```python
class TopKAccuracyMetric:
    name = "top_k_accuracy"

    def __init__(self, k: int = 5):
        self.k = k

    def compute(self, predictions, references):
        hit = sum(1 for pred, ref in zip(predictions, references) if set(pred[: self.k]) & set(ref))
        return {"value": hit / len(predictions), "k": self.k}
```

### 4. 交付清单
- [ ] metrics/evaluator/analyzers 源码
- [ ] 报告模板/生成器
- [ ] README 说明指标与报告
- [ ] 单元测试（metrics + evaluator）
- [ ] Demo 脚本（可选：`python -m ...evaluation.demo`）

---

## 子任务3：基线策略与被测系统适配层（Baseline Implementations & Adapter SDK）

### 1. 子任务概述
- **子任务名称**：Baseline Strategies & Adapter SDK
- **核心目标**：实现关键词/嵌入/随机等基线策略，并提供统一的 Adapter 接口，方便未来任务3接入新的代理系统。
- **独立性说明**：专注 `implementations/` 目录与 `adapters/` 接口，只与子任务1交换接口（被动被调用），无需访问评估模块或配置细节。

### 2. 详细规格
#### 2.1 目录结构
```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
└── implementations/
    ├── __init__.py
    ├── adapters.py                 # Adapter 抽象 & Registry
    ├── baseline_selector.py        # 关键词检索基线
    ├── embedding_selector.py       # 嵌入相似度基线
    ├── random_selector.py          # 随机基线
    ├── planning_agent.py           # 简单规则规划器
    ├── timing_detector.py          # 阈值式时机判断器
    └── utils/
        ├── text_preprocess.py
        └── vector_store.py         # 轻量向量缓存（可选）
```

#### 2.2 接口与数据流
- **Adapter 接口**
  ```python
  class ToolSelectorAdapter(Protocol):
      def predict(self, query: ToolSelectionQuery, top_k: int) -> List[ToolPrediction]

  class PlanningAdapter(Protocol):
      def plan(self, task: PlanningTask) -> PlanningPlan

  class TimingAdapter(Protocol):
      def decide(self, message: TimingMessage) -> TimingDecision
  ```
- **数据结构**（pydantic or dataclasses）：
  ```python
  class ToolSelectionQuery(BaseModel):
      sample_id: str
      instruction: str
      context: Dict[str, Any]
      candidate_tools: List[str]

  class ToolPrediction(BaseModel):
      tool_id: str
      score: float
  ```
- **策略配置示例（由子任务1 config 指定）**：
  ```yaml
  selector: baseline.embedding
  selector_params:
    embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
    cache_dir: ${PROJECT_ROOT}/.sage/cache/embeddings
  ```

#### 2.3 代码实现清单
- `adapters.py`
  - `AdapterRegistry`（注册/获取策略）
  - `register_adapter(name: str)` decorator
- `baseline_selector.py`
  - 关键词匹配（tf-idf 或简单 token overlap）实现
- `embedding_selector.py`
  - 使用已依赖的向量库（若无则使用 numpy + 预置 embedding）
- `random_selector.py`
  - 简单随机采样 baseline
- `planning_agent.py`
  - 基于模板/规则生成 5-10 步计划，输出 `PlanningPlan`
- `timing_detector.py`
  - 根据关键字/信号决定是否调用工具，输出 `TimingDecision`
- `utils/`
  - 文本预处理、embedding cache（若 repo 已有工具可复用）

#### 2.4 集成方式
- **与子任务1**：注册表在 `implementations/__init__.py` 初始化，供 Experiment loader 使用：
  ```python
  adapter_registry = AdapterRegistry()
  adapter_registry.register("baseline.keyword", KeywordSelectorAdapter())
  ```
- **与子任务2**：间接，通过 Experiment 输出 predictions。
- **DataManager**：策略若需工具详情，可在初始化时注入 `tools_loader = dm.get_by_source("agent_tools")`（仅读取，不写入）。
- **可插拔接口**：任务3 新策略只需实现 Protocol 并注册即可。

#### 2.5 验证标准
- **单测 (`tests/benchmark_agent/test_implementations.py`)**：
  - 每个 adapter 在 mock 数据下输出合法结构（top_k 数量正确、score 排序）。
  - Registry 注册/获取逻辑。
  - Embedding selector 可缓存向量并在重复查询时命中缓存。
- **功能验证**：通过脚本运行 baseline，与样例样本比对结果格式。
- **性能**：embedding selector 支持批量向量化、缓存，保证 1k 工具查询 < 1s（在 mock embedding 下）。

### 3. 实施指导
#### 3.1 开发顺序
1. 定义 Adapter Protocol + Registry。
2. 实现最小 baseline（random）。
3. 添加 keyword / embedding selector，并提供参数化配置。
4. 扩展到规划/时机判断适配器。
5. 编写测试与 README 使用示例。

#### 3.2 技术要点
- 复用 `packages/sage-benchmark/src/sage/benchmark/benchmark_rag/implementations/` 中的 registry 模式。
- 若需嵌入模型，优先使用仓库已有依赖（如 `sentence-transformers` 若已存在；否则提供预计算向量读取）。
- 所有策略需支持 `seed`，确保可重现实验。

#### 3.3 示例代码片段
```python
@adapter_registry.register("baseline.keyword")
class KeywordSelectorAdapter:
    def __init__(self, tokenizer=None):
        self.tokenizer = tokenizer or SimpleTokenizer()

    def predict(self, query: ToolSelectionQuery, top_k: int = 5):
        scores = [
            (tool_id, self._keyword_overlap(query.instruction, tool_id))
            for tool_id in query.candidate_tools
        ]
        scored = sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]
        return [ToolPrediction(tool_id=t, score=s) for t, s in scored]
```

### 4. 交付清单
- [ ] Adapter 接口与 Registry
- [ ] 随机/关键词/嵌入等基线实现
- [ ] 规划/时机判断策略
- [ ] 测试（adapter outputs + cache）
- [ ] README 章节：如何注册新策略
- [ ] Demo（可选：baseline quickstart）

---

## 并行开发建议
- **Git 分支建议**：
  - `feat/benchmark-agent-kernel`（子任务1）
  - `feat/benchmark-agent-eval`（子任务2）
  - `feat/benchmark-agent-baselines`（子任务3）
- **合并顺序**：
  1. 子任务1 与 子任务3 可并行；子任务1 提供接口草案，子任务3 基于协议开发。
  2. 子任务2 依赖 `ExperimentResult` 数据结构，建议等待子任务1确定结构后开始实现；但 metrics 可先行使用 mock 结构开发。
  3. 集成阶段先合并子任务1（提供运行骨架）→ 子任务3（提供策略）→ 子任务2（输出完整评估）。
- **集成测试策略**：
  - 建立 mock pipeline 测试：使用子任务1的 `ToolSelectionExperiment` + 子任务3 `random_selector` + 子任务2 `TopKAccuracyMetric` 跑通全链路。
  - 在 `packages/sage-benchmark/tests/benchmark_agent/test_end_to_end.py` 中使用 2 条样本的假数据，验证 CLI 指令生成 JSON/Markdown 报告。
  - CI 钩子：新增 `sage-dev project test --quick -k benchmark_agent`。

# Agent Core Algorithms & Runtime (Task 3) Decomposition

### 子任务1: 自适应工具选择策略库（Adaptive Tool Selection Library）

#### 1. 概述
- **核心目标**：在 L3 (`packages/sage-libs`) 层构建可插拔的高准确率工具选择策略库，覆盖关键词、嵌入、两阶段检索与自适应 rerank，满足 ≥95% Top-K 精度目标。
- **独立性说明**：只修改 `sage.libs.agentic.agents.action.tool_selection/` 及配套测试；通过抽象接口向外暴露，供子任务2/3（规划、runtime）或任务2基准直接调用。

#### 2. 详细规格
##### 2.1 目录结构
```
packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/
├── __init__.py                        # 导出注册表
├── base.py                            # ToolSelectorProtocol、SelectorConfig
├── schemas.py                         # pydantic 数据结构（ToolSelectionQuery, Prediction）
├── keyword_selector.py                # 关键词/规则选择器
├── embedding_selector.py              # 向量相似度检索
├── two_stage_selector.py              # 粗召回+精排
├── adaptive_selector.py               # 自适应策略（bandit/score fusion）
├── retriever/
│   ├── vector_index.py                # 轻量向量索引（复用现有 embedding 工具）
│   └── cache.py                       # 结果缓存
└── registry.py                        # SelectorRegistry + from_config

packages/sage-libs/tests/lib/agentic/action/tool_selection/
├── test_keyword_selector.py
├── test_embedding_selector.py
├── test_two_stage_selector.py
└── test_registry.py
```

##### 2.2 接口设计
- `ToolSelectionQuery`（pydantic）：
  ```python
  class ToolSelectionQuery(BaseModel):
      sample_id: str
      instruction: str
      context: Dict[str, Any]
      candidate_tools: List[str]
      metadata: Dict[str, Any] = {}
  ```
- `ToolPrediction`：`tool_id: str`, `score: float`, `explanation: Optional[str]`。
- 抽象类：
  ```python
  class ToolSelector(Protocol):
      name: str
      @classmethod
      def from_config(cls, config: SelectorConfig, resources: SelectorResources) -> "ToolSelector": ...
      def select(self, query: ToolSelectionQuery, top_k: int = 5) -> List[ToolPrediction]: ...
  ```
- `SelectorResources` 包含 `tools_loader`, `embedding_client`, `logger`。
- 与 Benchmark Runner 接口：通过 `SelectorRegistry.get("adaptive.v1")` 获取实例，runner 将 query（由任务2 Experiment 提供）传入 `select`。

##### 2.3 功能清单
- `KeywordSelector`: TF-IDF / token overlap（O(N)）+ 早停。
- `EmbeddingSelector`: 复用 `sage.libs.embedding` 生成向量，支持 ANN（若已有 FAISS/自研索引）。
- `TwoStageSelector`: 先关键词召回 200，再嵌入精排；复杂度 O(N log K)。
- `AdaptiveSelector`: 根据历史表现动态加权策略，支持 bandit/阈值。需提供在线更新与离线统计接口。
- `Retriever.vector_index`: 构建工具向量缓存，支持 1000+ 工具、<50ms 查找。

##### 2.4 数据与依赖
- 数据源：通过 DataManager 获取 `agent_tools` loader，加载工具元数据。
- Embedding：优先使用 `sage.libs.embedding`，若需新模型需提交理由。
- 不新增第三方依赖；如需 ANN，可复用现有 `numpy`, `scipy`。

##### 2.5 测试与验证
- **单元测试**：覆盖 selector 输入校验、Top-K 正确性、缓存命中、配置工厂。
- **基准测试**：`tests/perf/test_tool_selector_benchmark.py`（可选）评估 1000 工具耗时。
- **验收**：在 mock 数据上达到 ≥95% Top-K（80/84 命中）并通过 pytest。

#### 3. 实施指导
##### 3.1 开发步骤
1. 定义 schema + 抽象接口与 registry。
2. 实现 keyword / embedding 基线。
3. 添加 two-stage 与 adaptive，并完善缓存/向量化。
4. 编写 tests + benchmark 脚本。

##### 3.2 技术要点
- 预加载工具描述向量，使用内存映射减少延迟。
- 两阶段策略需支持可配置召回阈值与 rerank 权重。
- 错误处理：当候选为空时回退到默认工具或直接返回空列表。

##### 3.3 示例代码
```python
def select(self, query: ToolSelectionQuery, top_k: int = 5):
    coarse = self.keyword_selector.select(query, top_k=self.config.coarse_k)
    refined = self.embedding_selector.rerank(query, coarse)
    return refined[:top_k]
```

#### 4. 交付清单
- [ ] 新增 `tool_selection/` 源码与 registry
- [ ] YAML/JSON 配置示例（如 `configs/tool_selectors/adaptive.yaml`）
- [ ] 单元+性能测试
- [ ] 文档：README 或 `docs/dev-notes/tool-selection.md`
- [ ] Demo：简单脚本展示 selector 输出

---

### 子任务2: 层次化规划与时机判断引擎（Hierarchical Planning & Timing Engine）

#### 1. 概述
- **核心目标**：增强 `llm_planner.py` 并新增时机判断模块，实现 5-10 步层次规划、依赖图解析、工具调用时机 F1 ≥0.93。
- **独立性说明**：集中在 `packages/sage-libs/src/sage/libs/agentic/agents/planning/` 与 `.../control/` 目录；通过 Planner/Timing 接口与子任务1的 selector、子任务3的 runtime 相连。

#### 2. 详细规格
##### 2.1 目录结构
```
packages/sage-libs/src/sage/libs/agentic/agents/planning/
├── __init__.py
├── base.py                        # PlannerProtocol, PlanStep dataclass
├── hierarchical_planner.py        # 新 planner 主体
├── dependency_graph.py            # 任务依赖解析
├── timing_decider.py              # 时机判断逻辑
├── prompt_templates/
│   ├── planner_v2.j2
│   └── timing_guard.j2
└── utils/
    ├── repair.py                  # JSON/plan 修复
    └── validators.py              # 计划校验

packages/sage-libs/tests/lib/agentic/planning/
├── test_hierarchical_planner.py
├── test_dependency_graph.py
├── test_timing_decider.py
└── fixtures/
    └── planning_samples.json
```

##### 2.2 接口设计
- `PlanRequest`：
  ```python
  class PlanRequest(BaseModel):
      goal: str
      context: Dict[str, Any]
      tools: List[ToolMetadata]
      constraints: List[str] = []
  ```
- `PlanStep`: `id`, `action`, `inputs`, `depends_on`, `expected_outputs`, `tool_id`。
- `PlannerProtocol`：`def plan(self, request: PlanRequest) -> PlanResult`。
- `TimingDeciderProtocol`: `def decide(self, message: TimingMessage) -> TimingDecision`。
- 配置：`HierarchicalPlanner.from_config(cls, cfg: PlannerConfig, selector: ToolSelector)`。
- 集成点：
  - AgentRuntime 注入 `planner` 与 `timing_decider`。
  - Benchmark Runner 调用 `planner.plan()` & `timing_decider.decide()` 以生成基线结果。

##### 2.3 功能清单
- `HierarchicalPlanner`：
  1. 解析任务 → 子任务树（显性/隐性目标）。
  2. 调用 ToolSelector（子任务1）获取每步候选工具。
  3. 构建依赖图并拓扑排序，确保 5-10 步覆盖。
  4. 提供 plan 修复（JSON schema 校验 + best-effort 修补）。
- `DependencyGraph`：基于 DSL 或 LLM 输出解析 `depends_on`，提供 `detect_cycles()`。
- `TimingDecider`：利用规则 + 学习器判断是否调用工具，输出 `TimingDecision(decision: Literal["call", "respond"], confidence: float)`。
- 性能目标：规划生成 <1.5s；时机判断 <100ms。

##### 2.4 数据与依赖
- 使用子任务1 selector 提供工具列表；需要 `agent_benchmark` 样本（通过 DataManager）。
- 依赖 LLM（已有 `llm_planner` 的 LLM 客户端）与 `sage.libs.embedding`（用于上下文摘要）。
- 无额外第三方依赖。

##### 2.5 测试与验证
- **单测**：planner 生成步骤数量 & 依赖合法、timing 判定逻辑（mock LLM）。
- **集成测试**：结合 AgentRuntime mock，执行 plan + timing pipeline。
- **性能测试**：`tests/perf/test_planner_latency.py` 记录响应时间。
- **验收**：在基准样本上达到 ≥90% 计划成功率、Timing F1 ≥0.93（基于任务2数据）。

#### 3. 实施指导
##### 3.1 开发步骤
1. 提取/重构 `llm_planner` 为 `PlannerProtocol`，编写 base & schemas。
2. 实现 `dependency_graph` + validator。
3. 完成 `HierarchicalPlanner` 主流程，接入 selector。
4. 实现 `TimingDecider`（规则 + 学习器），补充模板与 tests。

##### 3.2 技术要点
- LLM 输出需多轮修正：实现 `repair_plan(json_str)` 捕获异常。
- 依赖图生成后务必检测环路并提供 fallback。
- Timing 判定结合对话上下文特征（如最近工具调用间隔、用户意图）。

##### 3.3 示例代码
```python
def plan(self, request: PlanRequest) -> PlanResult:
    outline = self.llm.generate_plan(prompt=self._build_prompt(request))
    steps = self.repair.parse_steps(outline)
    graph = DependencyGraph.from_steps(steps)
    graph.validate(max_steps=10)
    for step in steps:
        step.tool_id = self.selector.select(self._to_query(step))[0].tool_id
    return PlanResult(steps=graph.topologically_sorted())
```

#### 4. 交付清单
- [ ] 新 planner/timing 源码 + 模板
- [ ] 配置示例 `configs/planner/hierarchical.yaml`
- [ ] 单元/集成/性能测试
- [ ] 文档：规划指南 + API
- [ ] Demo：脚本输出计划与时机判断

---

### 子任务3: Runtime & Middleware 集成桥接（Runtime & Middleware Integration Bridge）

#### 1. 概述
- **核心目标**：在 L3 Runtime 与 L4 Middleware 中接入新策略与规划能力，提供 Benchmark & 生产复用的被测系统；包含 Operator、Adapter、运行脚本。
- **独立性说明**：聚焦 `packages/sage-libs/src/sage/libs/agentic/agents/runtime/` 与 `packages/sage-middleware/src/sage/middleware/operators/agentic/`，通过接口调用子任务1/2 输出，不修改其内部实现。

#### 2. 详细规格
##### 2.1 目录结构
```
packages/sage-libs/src/sage/libs/agentic/agents/runtime/
├── agent.py                          # 增强：注入 selector/planner/timing
├── adapters.py                       # BenchmarkAdapter, RuntimeConfig
├── orchestrator.py                   # 新：统一调度工具调用/规划执行
└── telemetry.py                      # 指标上报（供 benchmark）

packages/sage-middleware/src/sage/middleware/operators/agentic/
├── __init__.py
├── runtime.py                        # 更新以加载新 orchestrator
├── tool_selection_operator.py        # 新 Operator
├── planning_operator.py              # 新 Operator
└── timing_operator.py                # 新 Operator / hook

packages/sage-middleware/tests/operators/agentic/
├── test_tool_selection_operator.py
├── test_planning_operator.py
└── test_runtime_integration.py
```

##### 2.2 接口设计
- `RuntimeConfig`（pydantic）：
  ```python
  class RuntimeConfig(BaseModel):
      selector: SelectorConfig
      planner: PlannerConfig
      timing: TimingConfig
      max_turns: int = 8
      telemetry: TelemetryConfig
  ```
- `BenchmarkAdapter`：供任务2调用。
  ```python
  class BenchmarkAdapter:
      def __init__(self, runtime: AgentRuntime): ...
      def run_tool_selection(self, query: ToolSelectionQuery) -> List[ToolPrediction]
      def run_planning(self, request: PlanRequest) -> PlanResult
      def run_timing(self, message: TimingMessage) -> TimingDecision
  ```
- Middleware Operator 接口：`process(request: OperatorRequest) -> OperatorResponse`，读取 YAML config，实例化 runtime。

##### 2.3 功能清单
- **AgentRuntime**：
  - 新增 `inject_components(selector, planner, timing_decider)`。
  - `orchestrator` 负责执行计划、记录 telemetry。
- **ToolSelectionOperator**：REST/gRPC 入口，暴露 `POST /tool-selection`。
- **PlanningOperator / TimingOperator**：同步/异步模式，支持批量请求。
- **Telemetry**：记录 latency、命中率，供 benchmark runner & observability 使用。
- 性能：整条 pipeline 响应 <2s；Operator QPS ≥5（单实例）。

##### 2.4 数据与依赖
- 通过任务1 DataManager Accessor（在 runtime 初始化时加载 profile）。
- 依赖子任务1/2 提供的 selector/planner/timing；以接口注入。
- 仍使用现有日志工具，无新依赖。

##### 2.5 测试与验证
- **单元测试**：Runtime orchestrator、Adapter 接口。
- **集成测试**：启动 Operator（mock runtime）并发送 HTTP/gRPC 请求。
- **端到端**：结合任务2 benchmark（使用 BenchmarkAdapter）跑通一次评测。
- **验收**：Operator 返回 200，Telemetry 记录指标，并通过 `pytest packages/sage-middleware/tests/operators/agentic -v`。

#### 3. 实施指导
##### 3.1 开发步骤
1. 扩展 `AgentRuntime` 支持注入 + orchestrator。
2. 实现 `BenchmarkAdapter` & telemetry。
3. 新建 Operator（tool/planning/timing）并接线 config。
4. 编写 tests + sample configs，最后验证与任务2 runner 对接。

##### 3.2 技术要点
- 保持层次隔离：L4 仅调用 L3 暴露 API。
- Operator 配置支持热更新（监听 YAML 变更或重载）。
- 错误处理：runtime 异常需映射为 Operator 错误码并带 trace_id。

##### 3.3 示例代码
```python
class BenchmarkAdapter:
    def run_tool_selection(self, query: ToolSelectionQuery):
        selector = self.runtime.selector
        return selector.select(query, top_k=self.runtime.config.selector.top_k)
```

#### 4. 交付清单
- [ ] Runtime 扩展 + orchestrator
- [ ] Middleware Operators & configs (`configs/operators/*.yaml`)
- [ ] 单元/集成/端到端测试
- [ ] 文档：运行指南 + API
- [ ] Demo：`python -m sage.middleware.operators.agentic.tool_selection --config ...`

---

## 并行开发建议
- **分支策略**：
  - `feat/agent-tool-selection-lib`（子任务1）
  - `feat/agent-planning-timing`（子任务2）
  - `feat/agent-runtime-operators`（子任务3）
- **合并顺序**：
  1. 子任务1/2 可并行，提前对齐接口（`ToolSelector`, `PlanResult`）。
  2. 子任务3 在接口稳定后接入；可先用 mock selector/planner 完成 Operator 骨架。
  3. 最终合并顺序建议：1 → 2 → 3，确保 runtime 集成引用已落地实现。
- **集成测试计划**：
  - 阶段一：任务1/2 各自提供 mock 数据测试。
  - 阶段二：子任务3 使用真实 selector/planner 运行 end-to-end（通过 BenchmarkAdapter 调用任务2 runner）。
  - CI 中增设 `pytest packages/sage-libs/tests/lib/agentic -k tool_selection` 与 `pytest packages/sage-middleware/tests/operators/agentic`；同时提供 `sage-dev project test --quick -k benchmark_agent_runtime` 作为全链路回归。

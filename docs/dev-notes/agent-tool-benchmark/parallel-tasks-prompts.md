# Agent Benchmark 并行任务提示词

**目标**: 难题4 - Agent平台海量工具业务下的规划和工具调用准确率提升 (95%+)

**创建日期**: 2025-11-26  
**更新日期**: 2025-11-26

---

## 🔴 紧急 Bug 修复任务 (优先执行)

> 这些任务需要在其他任务之前完成，因为它们阻塞了基础评测功能。

| 任务 | 问题 | 优先级 | 预估时间 |
|------|------|--------|---------|
| **Task X1** | Tool Selection 评估返回 0% 准确率 | 🔴 P0 | 2-3h |
| **Task X2** | Hybrid Timing 在 --skip-llm 模式仍加载 LLM | 🟡 P1 | 1h |
| **Task X3** | 数据文件位置混乱需要梳理 | 🟡 P1 | 1-2h |

---

## 任务依赖图

```
                    ┌─────────────────────────────────────────┐
                    │      紧急任务组 X (Bug 修复)              │
                    │  X1: Tool Selection Bug                 │
                    │  X2: Hybrid Timing LLM                  │
                    │  X3: 数据文件位置                         │
                    └─────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         并行任务组 A (SOTA 策略实现)                      │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────┤
│  Task A1    │  Task A2    │  Task A3    │  Task A4    │  Task A5        │
│  ToolLLM    │  ReAct      │  ToT        │  Gorilla    │  API-Bank       │
│  (工具选择)  │  (规划)     │  (规划)     │  (工具选择)  │  (评测数据)      │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                         并行任务组 B (SOTA 微调方法)                      │
├─────────────┬─────────────┬─────────────┬─────────────────────────────────┤
│  Task B1    │  Task B2    │  Task B3    │  Task B4                        │
│  FireAct    │ AgentTuning │  ToolAlpaca │  DoRA/LoRA+                     │
│  (轨迹微调)  │ (Agent能力) │  (工具数据)  │  (高效微调)                      │
└─────────────┴─────────────┴─────────────┴─────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                         并行任务组 C (基础设施 + 优化)                     │
├───────────┬───────────┬───────────┬───────────┬─────────────────────────┤
│  Task C1  │  Task C2  │  Task C3  │  Task C4  │  Task C5                │
│  统一实验  │  单元测试  │  文档完善  │ 基准线优化 │  LLM 缓存              │
│  脚本整合  │  覆盖补充  │  API文档  │ (Timing)  │  机制                   │
└───────────┴───────────┴───────────┴───────────┴─────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         最终任务 D (依赖 X+A+B+C)                         │
│                   Task D1: 完整实验运行 + 论文图表生成                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔴 紧急任务组 X: Bug 修复 (最高优先级，可并行)

### Task X1: 修复 Tool Selection 评估返回 0% 准确率

**优先级**: 🔴 P0 | **预估时间**: 2-3小时 | **依赖**: 无

```markdown
# Task X1: 修复 Tool Selection 评估 Bug

## 问题描述
`run_all_experiments.py` 中的 Tool Selection 评估返回 0% 准确率，所有指标都是 0。

## 问题定位

当前代码 (`run_all_experiments.py` ~line 408):
```python
result = selector.select(query, candidate_tools, top_k=top_k)
```

## 可能原因
1. `SelectorAdapter.select()` 方法签名与调用不匹配
2. `candidate_tools` 格式不正确（应该是 tool 对象列表还是 ID 列表？）
3. 返回值解析逻辑有问题

## 任务清单

### 1. 检查 SelectorAdapter 接口
查看 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`:

```python
class SelectorAdapter:
    def predict(self, query: Any, top_k: Optional[int] = None, **kwargs) -> list:
        # 检查这个方法的实际实现
        pass
```

### 2. 检查 run_all_experiments.py 中的调用
查看 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py`:
- 找到 `run_tool_selection_evaluation()` 方法
- 检查如何构建 query 对象
- 检查如何传递 candidate_tools
- 检查返回值如何解析

### 3. 添加调试日志
```python
# 在评估循环中添加
print(f"Query: {query}")
print(f"Candidate tools count: {len(candidate_tools)}")
result = selector.select(query, candidate_tools, top_k=top_k)
print(f"Result: {result}")
print(f"Result type: {type(result)}")
```

### 4. 修复接口不匹配
根据调试结果修复:
- 如果是参数顺序问题，调整调用
- 如果是数据格式问题，添加转换逻辑
- 如果是返回值解析问题，修复解析代码

### 5. 验证修复
```bash
cd /home/shuhao/SAGE
python packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py \
    --quick --skip-llm
```

确认 Tool Selection 输出非零结果。

## 验收标准
- [ ] Tool Selection 评估返回非零准确率
- [ ] keyword/embedding/hybrid 三个策略都能输出结果
- [ ] 结果与 Timing/Planning 格式一致

## 关键文件
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
```

---

### Task X2: 修复 Hybrid Timing 在 --skip-llm 模式仍加载 LLM

**优先级**: 🟡 P1 | **预估时间**: 1小时 | **依赖**: 无

```markdown
# Task X2: 修复 Hybrid Timing LLM 加载问题

## 问题描述
即使使用 `--skip-llm` 参数，`timing.hybrid` 策略仍然会尝试加载 vLLM 模型。

## 原因分析
`timing.hybrid` 内部使用了 LLM 作为后备策略，在初始化时就会加载模型。

## 任务清单

### 1. 检查 Hybrid Timing Decider 实现
查看 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`:

```python
def _create_hybrid_timing_decider(self, resources: Optional[Any] = None) -> TimingAdapter:
    # 检查是否在初始化时就加载了 LLM
    pass
```

### 2. 方案 A: 延迟加载 LLM
修改 Hybrid 策略，只在实际需要时才加载 LLM:

```python
class HybridTimingDecider:
    def __init__(self, ...):
        self._llm_client = None  # 延迟加载

    @property
    def llm_client(self):
        if self._llm_client is None:
            self._llm_client = IntelligentLLMClient.create_auto()
        return self._llm_client
```

### 3. 方案 B: 在 --skip-llm 模式下将 Hybrid 加入跳过列表
修改 `run_all_experiments.py`:

```python
if self.skip_llm:
    strategies = ["timing.rule_based"]  # 只用 rule-based
    # 或者
    strategies = ["timing.rule_based", "timing.embedding"]  # 跳过 hybrid
```

### 4. 验证修复
```bash
python run_all_experiments.py --quick --skip-llm
# 应该不再出现 vLLM 加载日志
```

## 验收标准
- [ ] `--skip-llm` 模式下不加载 vLLM
- [ ] Hybrid 策略仍然可用（在非 skip-llm 模式）

## 关键文件
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py`
```

---

### Task X3: 梳理数据文件位置

**优先级**: 🟡 P1 | **预估时间**: 1-2小时 | **依赖**: 无

```markdown
# Task X3: 梳理数据文件位置

## 问题描述
数据文件分布在多个位置，容易混淆:

**当前状态**:
- **sageData submodule** (`packages/sage-benchmark/src/sage/data/sources/`):
  - `agent_benchmark/splits/` - 已有基础数据（600条 tool_selection, 300条 timing/planning）
  - `agent_tools/data/tool_catalog.jsonl` - 1200 个工具
  - `agent_sft/data/` - SFT 训练数据

- **运行时生成** (`.sage/benchmark/data/`):
  - `timing_judgment/` - 运行时生成的增强数据
  - `task_planning/` - 运行时生成的增强数据
  - `tool_selection/` - 运行时生成的增强数据

## 任务清单

### 1. 明确数据分类

| 类型 | 位置 | 说明 |
|------|------|------|
| 静态基准数据 | `sage-data` submodule | 版本控制，不应修改 |
| 运行时生成数据 | `.sage/benchmark/data/` | 每次运行可重新生成 |
| 模型权重/缓存 | `.sage/models/` | 下载的模型文件 |

### 2. 更新 run_all_experiments.py 数据加载逻辑

```python
def _get_data_path(self, dataset: str) -> Path:
    """获取数据路径，优先使用 submodule 中的静态数据"""
    # 1. 先检查 submodule 中的静态数据
    static_path = SAGE_DATA_ROOT / "sources" / dataset / "splits"
    if static_path.exists():
        return static_path

    # 2. 回退到运行时生成的数据
    runtime_path = DEFAULT_DATA_DIR / dataset
    if runtime_path.exists():
        return runtime_path

    # 3. 都没有则生成
    self._prepare_data(dataset)
    return runtime_path
```

### 3. 添加数据来源标记

在结果中标记数据来源:
```python
result.metadata["data_source"] = "static" or "generated"
result.metadata["data_path"] = str(data_path)
```

### 4. 更新文档

在 README 中说明数据文件位置和用途。

## 验收标准
- [ ] 数据加载逻辑优先使用 submodule 静态数据
- [ ] 结果中包含数据来源元信息
- [ ] 文档清晰说明数据位置

## 关键文件
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py`
- `packages/sage-benchmark/src/sage/data/sources/` (submodule)
```

---

## 任务组 A: SOTA 策略实现 (可完全并行)

### Task A1: 实现 ToolLLM (DFSDT) 工具选择策略

**优先级**: P0 | **预估时间**: 4-6小时 | **依赖**: 无

```markdown
# Task A1: 实现 ToolLLM (DFSDT) 工具选择策略

## 背景
ToolLLM (Qin et al., 2023) 是工具选择领域的 SOTA 方法，使用 DFSDT (Depth-First Search-based Decision Tree) 算法进行工具选择。我们需要将其集成到 SAGE benchmark 框架中作为对比 baseline。

## 参考资料
- 论文: "ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs"
- GitHub: https://github.com/OpenBMB/ToolBench

## 任务清单

### 1. 算法实现
在 `packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/` 下创建:

```python
# toolllm_selector.py
class DFSDTSelector(BaseSelector):
    """
    ToolLLM 的 DFSDT 算法实现

    核心思想:
    1. 将工具选择建模为决策树搜索
    2. 使用 LLM 在每个节点评估工具相关性
    3. 深度优先搜索找到最佳工具组合
    """

    def __init__(self, config: DFSDTConfig, llm_client: Any):
        self.max_depth = config.max_depth  # 搜索深度
        self.beam_width = config.beam_width  # 每层保留的候选数
        self.llm_client = llm_client

    def select(self, query: ToolSelectionQuery, top_k: int = 5) -> list[ToolPrediction]:
        """DFSDT 搜索选择工具"""
        # 1. 初始化搜索树
        # 2. DFS 遍历，用 LLM 评分
        # 3. 返回 top_k 工具
        pass

    def _expand_node(self, node: SearchNode, candidates: list) -> list[SearchNode]:
        """扩展搜索节点"""
        pass

    def _score_with_llm(self, query: str, tool: ToolDefinition) -> float:
        """使用 LLM 评估工具相关性"""
        pass
```

### 2. 配置类
```python
# config.py 中添加
@dataclass
class DFSDTConfig(BaseSelectorConfig):
    name: str = "dfsdt"
    max_depth: int = 3
    beam_width: int = 5
    llm_model: str = "qwen2.5-7b-instruct"
    temperature: float = 0.1
```

### 3. 注册到 AdapterRegistry
修改 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`:

```python
# 在 _register_builtins() 中添加
self._factories["selector.dfsdt"] = self._create_dfsdt_selector
self._factories["selector.toolllm"] = self._create_dfsdt_selector  # 别名

def _create_dfsdt_selector(self, resources: Optional[Any] = None) -> SelectorAdapter:
    """Create ToolLLM DFSDT selector."""
    from sage.libs.agentic.agents.action.tool_selection import (
        DFSDTSelector, DFSDTConfig
    )
    from sage.common.components.sage_llm.client import IntelligentLLMClient

    config = DFSDTConfig(max_depth=3, beam_width=5)
    llm_client = IntelligentLLMClient.create_auto()
    selector = DFSDTSelector(config, llm_client)
    return SelectorAdapter(selector)
```

### 4. 单元测试
创建 `packages/sage-libs/tests/unit/agentic/tool_selection/test_dfsdt_selector.py`

### 5. 验证
运行工具选择 benchmark，对比 DFSDT vs keyword vs embedding vs hybrid

## 验收标准
- [ ] DFSDTSelector 类实现完整
- [ ] 注册到 AdapterRegistry，可通过 "selector.toolllm" 访问
- [ ] 单元测试通过
- [ ] 在 benchmark 中可运行并输出有效结果

## 关键文件
- `packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
- `packages/sage-libs/tests/unit/agentic/tool_selection/`
```

---

### Task A2: 完善 ReAct 规划策略

**优先级**: P0 | **预估时间**: 3-4小时 | **依赖**: 无

```markdown
# Task A2: 完善 ReAct 规划策略

## 背景
ReAct (Yao et al., 2023) 是规划领域的经典方法，通过交替进行 Reasoning 和 Acting 来完成复杂任务。当前 SAGE 中有部分实现，需要完善 reasoning trace 功能。

## 参考资料
- 论文: "ReAct: Synergizing Reasoning and Acting in Language Models"
- 概念: Thought → Action → Observation 循环

## 任务清单

### 1. 检查现有实现
查看以下文件:
- `packages/sage-libs/src/sage/libs/agentic/agents/action/planning/`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`

### 2. 实现完整 ReAct Planner

```python
# packages/sage-libs/src/sage/libs/agentic/agents/action/planning/react_planner.py

@dataclass
class ReActStep:
    """ReAct 单步"""
    thought: str      # 推理过程
    action: str       # 选择的动作/工具
    action_input: dict  # 动作输入
    observation: str  # 执行结果 (可选，规划阶段为空)

@dataclass  
class ReActPlan:
    """ReAct 规划结果"""
    steps: list[ReActStep]
    final_answer: str
    reasoning_trace: str  # 完整推理链

class ReActPlanner(BasePlanner):
    """
    ReAct 规划器

    实现 Thought-Action-Observation 循环:
    1. Thought: 分析当前状态，决定下一步
    2. Action: 选择工具并准备输入
    3. Observation: (执行时获取) 工具返回结果
    """

    def __init__(self, config: ReActConfig, llm_client: Any):
        self.max_steps = config.max_steps
        self.llm_client = llm_client
        self.prompt_template = self._load_prompt_template()

    def plan(self, task: PlanningTask) -> ReActPlan:
        """生成 ReAct 风格的规划"""
        steps = []
        reasoning_trace = []

        for i in range(self.max_steps):
            # Generate thought
            thought = self._generate_thought(task, steps)
            reasoning_trace.append(f"Thought {i+1}: {thought}")

            # Decide action
            action, action_input = self._decide_action(task, thought, steps)

            if action == "finish":
                break

            step = ReActStep(
                thought=thought,
                action=action,
                action_input=action_input,
                observation=""  # 规划阶段不执行
            )
            steps.append(step)
            reasoning_trace.append(f"Action {i+1}: {action}({action_input})")

        return ReActPlan(
            steps=steps,
            final_answer=self._generate_final_answer(task, steps),
            reasoning_trace="\n".join(reasoning_trace)
        )

    def _generate_thought(self, task: PlanningTask, history: list) -> str:
        """使用 LLM 生成推理"""
        prompt = self.prompt_template.format(
            task=task.instruction,
            history=self._format_history(history)
        )
        return self.llm_client.chat([{"role": "user", "content": prompt}])
```

### 3. 注册到 AdapterRegistry

```python
# adapter_registry.py
self._factories["planner.react"] = self._create_react_planner

def _create_react_planner(self, resources: Optional[Any] = None) -> PlannerAdapter:
    from sage.libs.agentic.agents.action.planning import ReActPlanner, ReActConfig
    from sage.common.components.sage_llm.client import IntelligentLLMClient

    config = ReActConfig(max_steps=10)
    llm_client = IntelligentLLMClient.create_auto()
    planner = ReActPlanner(config, llm_client)
    return PlannerAdapter(planner)
```

### 4. 单元测试
创建 `packages/sage-libs/tests/unit/agentic/planning/test_react_planner.py`

## 验收标准
- [ ] ReActPlanner 完整实现 Thought-Action 循环
- [ ] reasoning_trace 记录完整推理链
- [ ] 注册到 AdapterRegistry
- [ ] 在 planning benchmark 中可运行

## 关键文件
- `packages/sage-libs/src/sage/libs/agentic/agents/action/planning/`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
```

---

### Task A3: 实现 Tree-of-Thoughts (ToT) 规划策略

**优先级**: P1 | **预估时间**: 5-6小时 | **依赖**: 无

```markdown
# Task A3: 实现 Tree-of-Thoughts (ToT) 规划策略

## 背景
Tree-of-Thoughts (Yao et al., 2023) 通过树搜索探索多个推理路径，比线性的 CoT 更强大。

## 参考资料
- 论文: "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
- 核心: BFS/DFS 搜索 + LLM 评估节点

## 任务清单

### 1. 实现 ToT Planner

```python
# packages/sage-libs/src/sage/libs/agentic/agents/action/planning/tot_planner.py

@dataclass
class ThoughtNode:
    """思维树节点"""
    thought: str
    score: float
    children: list["ThoughtNode"]
    parent: Optional["ThoughtNode"]
    depth: int

class TreeOfThoughtsPlanner(BasePlanner):
    """
    Tree-of-Thoughts 规划器

    算法:
    1. 生成多个候选 thought
    2. 用 LLM 评估每个 thought 的价值
    3. BFS/DFS 搜索最优路径
    4. 回溯得到最终规划
    """

    def __init__(self, config: ToTConfig, llm_client: Any):
        self.max_depth = config.max_depth
        self.branch_factor = config.branch_factor  # 每个节点生成的候选数
        self.search_method = config.search_method  # "bfs" or "dfs"
        self.llm_client = llm_client

    def plan(self, task: PlanningTask) -> PlanningPrediction:
        """生成 ToT 规划"""
        root = ThoughtNode(thought="", score=0.0, children=[], parent=None, depth=0)

        if self.search_method == "bfs":
            best_path = self._bfs_search(root, task)
        else:
            best_path = self._dfs_search(root, task)

        return self._path_to_plan(best_path, task)

    def _generate_thoughts(self, node: ThoughtNode, task: PlanningTask) -> list[str]:
        """生成多个候选 thought"""
        prompt = f"""Given task: {task.instruction}
Current path: {self._format_path(node)}

Generate {self.branch_factor} different next steps. Output as JSON list."""

        response = self.llm_client.chat([{"role": "user", "content": prompt}])
        return self._parse_thoughts(response)

    def _evaluate_thought(self, thought: str, task: PlanningTask) -> float:
        """评估 thought 的价值 (0-1)"""
        prompt = f"""Task: {task.instruction}
Proposed step: {thought}

Rate how good this step is (0-10):"""

        response = self.llm_client.chat([{"role": "user", "content": prompt}])
        return self._parse_score(response) / 10.0

    def _bfs_search(self, root: ThoughtNode, task: PlanningTask) -> list[ThoughtNode]:
        """BFS 搜索"""
        queue = [root]
        best_path = []

        while queue and queue[0].depth < self.max_depth:
            node = queue.pop(0)
            thoughts = self._generate_thoughts(node, task)

            for thought in thoughts:
                score = self._evaluate_thought(thought, task)
                child = ThoughtNode(
                    thought=thought, score=score,
                    children=[], parent=node, depth=node.depth + 1
                )
                node.children.append(child)
                queue.append(child)

            # 保留 top-k 节点
            queue.sort(key=lambda n: n.score, reverse=True)
            queue = queue[:self.branch_factor * 2]

        # 返回最高分路径
        return self._get_best_path(root)
```

### 2. 配置和注册
同 A1/A2 模式

### 3. 单元测试

## 验收标准
- [ ] ToT 树搜索算法实现
- [ ] 支持 BFS 和 DFS 两种搜索
- [ ] 注册到 AdapterRegistry
- [ ] benchmark 可运行
```

---

### Task A4: 实现 Gorilla 工具检索策略

**优先级**: P2 | **预估时间**: 3-4小时 | **依赖**: 无

```markdown
# Task A4: 实现 Gorilla 工具检索策略

## 背景
Gorilla (Patil et al., 2023) 使用 API 文档检索增强来选择工具，特别擅长处理大规模 API 库。

## 参考资料
- 论文: "Gorilla: Large Language Model Connected with Massive APIs"
- 核心: 检索增强 + API 文档理解

## 任务清单

### 1. 实现 Gorilla Selector

```python
# packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/gorilla_selector.py

class GorillaSelector(BaseSelector):
    """
    Gorilla 风格的检索增强工具选择

    流程:
    1. 用 embedding 检索相关 API 文档
    2. 将检索到的文档作为 context
    3. 让 LLM 基于文档选择最合适的工具
    """

    def __init__(self, config: GorillaConfig, embedding_client: Any, llm_client: Any):
        self.retriever = DocumentRetriever(embedding_client)
        self.llm_client = llm_client
        self.top_k_retrieve = config.top_k_retrieve

    def select(self, query: ToolSelectionQuery, top_k: int = 5) -> list[ToolPrediction]:
        # 1. 检索相关 API 文档
        docs = self.retriever.retrieve(query.instruction, k=self.top_k_retrieve)

        # 2. 构建 prompt
        prompt = self._build_prompt(query, docs)

        # 3. LLM 选择
        response = self.llm_client.chat([{"role": "user", "content": prompt}])

        # 4. 解析返回
        return self._parse_selection(response, query.candidate_tools)
```

## 验收标准
- [ ] GorillaSelector 实现检索增强
- [ ] 注册到 AdapterRegistry
- [ ] benchmark 可运行
```

---

### Task A5: 集成 API-Bank 评测数据

**优先级**: P2 | **预估时间**: 2-3小时 | **依赖**: 无

```markdown
# Task A5: 集成 API-Bank 评测数据

## 背景
API-Bank (Li et al., 2023) 是一个 API 调用评测基准，包含多种真实场景的测试用例。

## 参考资料
- 论文: "API-Bank: A Benchmark for Tool-Augmented LLMs"
- GitHub: https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/api-bank

## 任务清单

### 1. 下载并转换数据
```python
# packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/evaluations/prepare_apibank_data.py

def download_apibank():
    """下载 API-Bank 数据集"""
    # 从 GitHub 下载
    pass

def convert_to_sage_format(apibank_data: dict) -> list[dict]:
    """转换为 SAGE benchmark 格式"""
    samples = []
    for item in apibank_data:
        sample = {
            "sample_id": item["id"],
            "instruction": item["query"],
            "expected_tools": item["api_calls"],
            "context": item.get("context", {}),
            "source": "api-bank"
        }
        samples.append(sample)
    return samples
```

### 2. 集成到 DataManager

### 3. 验证数据加载

## 验收标准
- [ ] API-Bank 数据可通过 DataManager 加载
- [ ] 转换后格式与现有 benchmark 兼容
- [ ] 至少 500 条测试样本可用
```

---

## 任务组 B: SOTA 微调方法 (可完全并行)

### Task B1: 实现 FireAct 轨迹微调

**优先级**: P1 | **预估时间**: 4-5小时 | **依赖**: 无

```markdown
# Task B1: 实现 FireAct 轨迹微调

## 背景
FireAct (Chen et al., 2023) 通过收集 Agent 执行轨迹并进行微调，提升 Agent 的任务完成能力。

## 参考资料
- 论文: "FireAct: Toward Language Agent Fine-tuning"
- 核心: 轨迹收集 → 质量筛选 → SFT 微调

## 任务清单

### 1. 轨迹收集器

```python
# packages/sage-libs/src/sage/libs/finetune/agent/trajectory.py

@dataclass
class AgentTrajectory:
    """Agent 执行轨迹"""
    task_id: str
    instruction: str
    steps: list[TrajectoryStep]
    success: bool
    reward: float

@dataclass
class TrajectoryStep:
    """轨迹单步"""
    thought: str
    action: str
    action_input: dict
    observation: str
    reward: float

class TrajectoryCollector:
    """收集 Agent 执行轨迹"""

    def __init__(self, agent: Any, environment: Any):
        self.agent = agent
        self.environment = environment

    def collect(self, tasks: list[str], max_steps: int = 10) -> list[AgentTrajectory]:
        """收集多个任务的轨迹"""
        trajectories = []
        for task in tasks:
            traj = self._run_episode(task, max_steps)
            trajectories.append(traj)
        return trajectories

    def _run_episode(self, task: str, max_steps: int) -> AgentTrajectory:
        """执行单个任务，记录轨迹"""
        pass
```

### 2. 轨迹质量筛选

```python
class TrajectoryFilter:
    """筛选高质量轨迹"""

    def filter(self, trajectories: list[AgentTrajectory],
               min_reward: float = 0.5) -> list[AgentTrajectory]:
        """筛选成功且高奖励的轨迹"""
        return [t for t in trajectories if t.success and t.reward >= min_reward]
```

### 3. 轨迹转 SFT 数据

```python
class TrajectoryToSFTConverter:
    """将轨迹转换为 SFT 训练数据"""

    def convert(self, trajectories: list[AgentTrajectory]) -> list[dict]:
        """转换为对话格式"""
        sft_data = []
        for traj in trajectories:
            dialog = self._trajectory_to_dialog(traj)
            sft_data.append(dialog)
        return sft_data
```

### 4. 集成到 MethodRegistry

```python
# method_comparison.py
"E_fireact": MethodConfig(
    name="E: FireAct",
    description="Agent trajectory fine-tuning",
    use_trajectory_collection=True,
    trajectory_min_reward=0.5,
    num_epochs=2,
)
```

## 验收标准
- [ ] TrajectoryCollector 可收集轨迹
- [ ] TrajectoryFilter 可筛选高质量轨迹
- [ ] 转换后数据可用于 AgentSFTTrainer
- [ ] 在 MethodRegistry 中注册为 Method E
```

---

### Task B2: 实现 AgentTuning 通用 Agent 能力微调

**优先级**: P1 | **预估时间**: 3-4小时 | **依赖**: 无

```markdown
# Task B2: 实现 AgentTuning 通用 Agent 能力微调

## 背景
AgentTuning (Zeng et al., 2023) 通过多任务混合训练，提升模型的通用 Agent 能力。

## 参考资料
- 论文: "AgentTuning: Enabling Generalized Agent Abilities for LLMs"
- 核心: 多任务混合 + 能力泛化

## 任务清单

### 1. 多任务数据混合器

```python
# packages/sage-libs/src/sage/libs/finetune/agent/multi_task.py

class MultiTaskMixer:
    """多任务数据混合"""

    def __init__(self, task_weights: dict[str, float]):
        """
        task_weights: {
            "tool_selection": 0.35,
            "planning": 0.30,
            "timing": 0.20,
            "general": 0.15
        }
        """
        self.task_weights = task_weights

    def mix(self, task_datasets: dict[str, list]) -> list:
        """按权重混合多个任务的数据"""
        mixed = []
        total = sum(len(d) for d in task_datasets.values())

        for task, dataset in task_datasets.items():
            weight = self.task_weights.get(task, 0.1)
            sample_size = int(total * weight)
            sampled = random.sample(dataset, min(sample_size, len(dataset)))
            mixed.extend(sampled)

        random.shuffle(mixed)
        return mixed
```

### 2. 能力评估器

```python
class AgentCapabilityEvaluator:
    """评估 Agent 多维能力"""

    CAPABILITIES = ["tool_use", "planning", "reasoning", "instruction_following"]

    def evaluate(self, model, test_sets: dict) -> dict[str, float]:
        """评估各项能力"""
        scores = {}
        for cap in self.CAPABILITIES:
            if cap in test_sets:
                scores[cap] = self._eval_capability(model, test_sets[cap])
        return scores
```

### 3. 集成到 MethodRegistry

```python
"F_agenttuning": MethodConfig(
    name="F: AgentTuning",
    description="Multi-task agent capability tuning",
    use_multi_task=True,
    task_weights={
        "tool_selection": 0.35,
        "planning": 0.30,
        "timing": 0.20,
        "general": 0.15
    },
)
```

## 验收标准
- [ ] MultiTaskMixer 实现多任务混合
- [ ] 支持自定义任务权重
- [ ] 在 MethodRegistry 中注册为 Method F
```

---

### Task B3: 集成 ToolAlpaca 工具使用数据

**优先级**: P2 | **预估时间**: 2-3小时 | **依赖**: 无

```markdown
# Task B3: 集成 ToolAlpaca 工具使用数据

## 背景
ToolAlpaca (Tang et al., 2023) 提供了大量工具使用的训练数据。

## 参考资料
- 论文: "ToolAlpaca: Generalized Tool Learning for Language Models"
- 数据: 包含 3000+ 工具使用示例

## 任务清单

### 1. 下载数据
```python
# packages/sage-data/src/sage/data/sources/tool_alpaca.py

class ToolAlpacaDataLoader(BaseDataLoader):
    """ToolAlpaca 数据加载器"""

    SOURCE_URL = "https://github.com/tangqiaoyu/ToolAlpaca"

    def load(self) -> list[dict]:
        """加载并转换数据"""
        pass
```

### 2. 转换为 SAGE 格式

### 3. 注册到 DataManager

## 验收标准
- [ ] ToolAlpaca 数据可加载
- [ ] 格式与 agent_sft 兼容
- [ ] 可用于 AgentSFTTrainer
```

---

### Task B4: 实现 DoRA/LoRA+ 高效微调方法

**优先级**: P2 | **预估时间**: 3-4小时 | **依赖**: 无

```markdown
# Task B4: 实现 DoRA/LoRA+ 高效微调方法

## 背景
DoRA 和 LoRA+ 是 2024 年提出的改进版 LoRA，训练效果更好。

## 参考资料
- DoRA: "DoRA: Weight-Decomposed Low-Rank Adaptation"
- LoRA+: "LoRA+: Efficient Low Rank Adaptation of Large Models"

## 任务清单

### 1. 集成 DoRA (通过 PEFT)

```python
# packages/sage-libs/src/sage/libs/finetune/agent/config.py

@dataclass
class AgentSFTConfig:
    # 现有字段...

    # 新增 DoRA 支持
    use_dora: bool = False

    def get_peft_config(self):
        if self.use_dora:
            return LoraConfig(
                use_dora=True,  # PEFT >= 0.9.0 支持
                r=self.lora_r,
                lora_alpha=self.lora_alpha,
                # ...
            )
```

### 2. 实现 LoRA+ 学习率调度

```python
class LoRAPlusScheduler:
    """LoRA+ 的不同学习率策略"""

    def __init__(self, base_lr: float, lora_lr_ratio: float = 16.0):
        """
        LoRA+ 建议 A/B 矩阵使用不同学习率
        A 矩阵: base_lr
        B 矩阵: base_lr * lora_lr_ratio
        """
        self.base_lr = base_lr
        self.lora_lr_ratio = lora_lr_ratio

    def get_param_groups(self, model) -> list[dict]:
        """返回参数组配置"""
        pass
```

### 3. 注册到 MethodRegistry

```python
"G_dora": MethodConfig(
    name="G: DoRA",
    description="Weight-decomposed LoRA",
    use_dora=True,
),
"H_lora_plus": MethodConfig(
    name="H: LoRA+",
    description="LoRA with differentiated learning rates",
    use_lora_plus=True,
    lora_lr_ratio=16.0,
)
```

## 验收标准
- [ ] DoRA 通过 PEFT 配置启用
- [ ] LoRA+ 学习率调度实现
- [ ] 在 MethodRegistry 中注册
```

---

## 任务组 C: 基础设施 (可并行)

### Task C1: 统一实验脚本整合

**优先级**: P0 | **预估时间**: 2-3小时 | **依赖**: 无

```markdown
# Task C1: 统一实验脚本整合

## 背景
当前 `run_all_experiments.py` 只支持评测，需要整合 SFT 训练对比功能。

## 任务清单

### 1. 添加 --train 模式

修改 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py`:

```python
parser.add_argument("--train", action="store_true",
                    help="Run training comparison (Methods A-H)")
parser.add_argument("--train-methods", nargs="+",
                    default=["A_baseline", "D_combined"],
                    help="Methods to compare")
parser.add_argument("--train-model", default="Qwen/Qwen2.5-1.5B-Instruct",
                    help="Base model for training")
```

### 2. 集成训练流程

```python
def run_training_comparison(self, methods: list[str], base_model: str):
    """运行训练方法对比"""
    from sage.benchmark.benchmark_agent.experiments.method_comparison import (
        MethodComparisonExperiment, MethodRegistry
    )

    exp = MethodComparisonExperiment(
        output_dir=self.output_dir / "training",
        base_model=base_model,
        methods={k: MethodRegistry.get_all_methods()[k] for k in methods}
    )

    results = exp.run_all_methods()
    self.results.training = results

    # 生成训练对比图表
    exp.generate_comparison_chart()
```

### 3. 更新 main() 流程

```python
if args.train:
    runner.run_training_comparison(
        methods=args.train_methods,
        base_model=args.train_model
    )
```

### 4. 更新文档

## 验收标准
- [ ] `--train` 模式可用
- [ ] 训练结果保存到 `.sage/benchmark/results/training/`
- [ ] 生成训练对比图表
```

---

### Task C2: 单元测试覆盖补充

**优先级**: P1 | **预估时间**: 3-4小时 | **依赖**: 无

```markdown
# Task C2: 单元测试覆盖补充

## 背景
`sage-libs/finetune/agent/` 模块缺少单元测试。

## 任务清单

### 1. 测试 CoresetSelector

```python
# packages/sage-libs/tests/unit/finetune/agent/test_continual.py

class TestCoresetSelector:
    def test_loss_topk_selection(self):
        """测试 loss_topk 策略"""
        selector = CoresetSelector(strategy="loss_topk", target_size=100)
        samples = [{"id": i, "loss": random.random()} for i in range(1000)]
        selected = selector.select(samples)
        assert len(selected) == 100
        # 验证选择的是 loss 最高的

    def test_diversity_selection(self):
        """测试 diversity 策略"""
        pass

    def test_hybrid_selection(self):
        """测试 hybrid 策略"""
        pass
```

### 2. 测试 OnlineContinualLearner

```python
class TestOnlineContinualLearner:
    def test_buffer_management(self):
        """测试 replay buffer 管理"""
        pass

    def test_replay_sampling(self):
        """测试 replay 采样"""
        pass
```

### 3. 测试 AgentSFTTrainer (mock)

### 4. 运行测试

```bash
pytest packages/sage-libs/tests/unit/finetune/agent/ -v --cov
```

## 验收标准
- [ ] CoresetSelector 测试覆盖三种策略
- [ ] OnlineContinualLearner 测试覆盖 buffer 管理
- [ ] 测试通过率 100%
- [ ] 覆盖率 >= 80%
```

---

### Task C3: API 文档完善

**优先级**: P2 | **预估时间**: 2-3小时 | **依赖**: 无

```markdown
# Task C3: API 文档完善

## 背景
Agent 训练相关模块缺少 API 文档。

## 任务清单

### 1. 更新 README

更新 `packages/sage-libs/README.md`，添加 agent finetune 部分:

```markdown
## Agent Fine-tuning

### Quick Start

```python
from sage.libs.finetune.agent import AgentSFTConfig, AgentSFTTrainer

config = AgentSFTConfig(
    base_model="Qwen/Qwen2.5-1.5B-Instruct",
    train_data="agent_sft:train",
    num_epochs=1,
)

trainer = AgentSFTTrainer(config)
trainer.train()
```

### Available Methods

| Method | Description | Config |
|--------|-------------|--------|
| A: Baseline | Standard SFT | `use_coreset=False, use_continual=False` |
| B: Coreset | Sample selection | `use_coreset=True, coreset_strategy="hybrid"` |
| C: Continual | Experience replay | `use_continual=True` |
| D: Combined | Coreset + Continual | `use_coreset=True, use_continual=True` |
```

### 2. 添加 docstring

确保所有公共类和方法有完整的 docstring。

### 3. 生成 API 参考

## 验收标准
- [ ] README 包含使用示例
- [ ] 所有公共 API 有 docstring
- [ ] 方法对比表格完整
```

---

### Task C4: 优化 Rule-based Timing Decider 基准线

**优先级**: P1 | **预估时间**: 2-3小时 | **依赖**: Task X1 完成

```markdown
# Task C4: 优化 Rule-based Timing Decider 基准线

## 背景
当前基准线性能未达标:

| Challenge | Best Strategy | Score | Target | Gap |
|-----------|---------------|-------|--------|-----|
| Timing Detection | Rule-based | 78.0% | 95% | -17% |
| Task Planning | Hierarchical | 26.7% | 90% | -63.3% |
| Tool Selection | - | 需修复后重测 | 95% | - |

Timing Detection 的 Rule-based 策略只有 78%，需要优化关键词匹配策略。

## 任务清单

### 1. 分析当前规则
查看 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`:

```python
def _create_rule_based_decider(self, resources):
    # 检查当前使用的规则
    pass
```

### 2. 分析错误样本
```python
# 收集 rule-based 判断错误的样本
errors = []
for sample in test_data:
    pred = decider.decide(sample.message)
    if pred.should_call_tool != sample.should_call_tool:
        errors.append({
            "message": sample.message,
            "expected": sample.should_call_tool,
            "predicted": pred.should_call_tool,
            "reasoning": pred.reasoning
        })

# 分析错误模式
print(f"False Positives: {len([e for e in errors if e['predicted']])}")
print(f"False Negatives: {len([e for e in errors if not e['predicted']])}")
```

### 3. 改进规则

基于错误分析改进规则:

```python
class ImprovedRuleBasedDecider:
    """改进的规则判断器"""

    # 需要工具的关键词
    TOOL_KEYWORDS = [
        # 动作类
        "查询", "搜索", "计算", "转换", "获取", "查找", "分析",
        "search", "query", "calculate", "convert", "get", "find",
        # 意图类
        "帮我", "请帮", "能否", "可以",
        "please", "can you", "could you", "help me",
        # 数据类
        "天气", "股票", "汇率", "日期", "时间",
        "weather", "stock", "exchange rate", "date", "time",
    ]

    # 不需要工具的关键词
    DIRECT_KEYWORDS = [
        # 闲聊类
        "你好", "谢谢", "再见", "是什么", "什么是",
        "hello", "thanks", "bye", "what is", "who are",
        # 知识类
        "解释", "描述", "介绍", "为什么",
        "explain", "describe", "introduce", "why",
    ]

    def decide(self, message: str) -> TimingDecision:
        message_lower = message.lower()

        # 计算工具关键词匹配分数
        tool_score = sum(1 for kw in self.TOOL_KEYWORDS if kw in message_lower)
        direct_score = sum(1 for kw in self.DIRECT_KEYWORDS if kw in message_lower)

        # 长度因素：较长的消息更可能是复杂任务
        length_factor = min(len(message) / 100, 1.0)

        # 综合判断
        should_call = (tool_score > direct_score) or (tool_score > 0 and length_factor > 0.5)
        confidence = min((tool_score + length_factor) / 3, 1.0)

        return TimingDecision(
            should_call_tool=should_call,
            confidence=confidence,
            reasoning=f"Tool keywords: {tool_score}, Direct keywords: {direct_score}"
        )
```

### 4. 验证改进效果
```bash
python run_all_experiments.py --quick --skip-llm
# 检查 Timing Detection 准确率是否提升
```

## 验收标准
- [ ] 分析出主要错误模式
- [ ] 改进规则后准确率 >= 85%
- [ ] 没有引入新的严重问题

## 关键文件
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
- `packages/sage-libs/src/sage/libs/agentic/agents/action/timing/`
```

---

### Task C5: 实现 LLM 服务缓存/预加载机制

**优先级**: P2 | **预估时间**: 2-3小时 | **依赖**: 无

```markdown
# Task C5: 实现 LLM 服务缓存机制

## 背景
每次运行 Hybrid/LLM 策略都要重新加载 vLLM 模型（约30秒），影响开发效率。

## 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| A: 模型缓存单例 | 简单，同进程复用 | 进程退出后失效 |
| B: 外部 API 服务 | 多进程共享，持久化 | 需要额外启动服务 |
| C: 模型预加载脚本 | 提前准备好 | 需要手动运行 |

## 任务清单

### 1. 方案 A: 实现 LLM Client 单例模式

```python
# packages/sage-common/src/sage/common/components/sage_llm/client.py

class IntelligentLLMClient:
    _instances: dict[str, "IntelligentLLMClient"] = {}

    @classmethod
    def get_instance(cls, model_name: str = None, **kwargs) -> "IntelligentLLMClient":
        """获取或创建 LLM 客户端单例"""
        key = model_name or "default"
        if key not in cls._instances:
            cls._instances[key] = cls.create_auto(model_name=model_name, **kwargs)
        return cls._instances[key]

    @classmethod
    def clear_instances(cls):
        """清理所有缓存的实例"""
        cls._instances.clear()
```

### 2. 更新 adapter_registry.py 使用单例

```python
def _create_llm_timing_decider(self, resources):
    # 使用单例而不是每次创建新实例
    llm_client = IntelligentLLMClient.get_instance()
    return TimingAdapter(LLMTimingDecider(llm_client))
```

### 3. 方案 B: 推荐使用外部服务

在文档中推荐用户预先启动 vLLM 服务:

```bash
# 推荐: 先启动 vLLM 服务
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8001

# 然后运行实验 (会自动检测到本地服务)
python run_all_experiments.py --full
```

### 4. 添加启动检测提示

```python
# run_all_experiments.py
def check_llm_service():
    """检查并提示 LLM 服务状态"""
    from sage.common.components.sage_llm.client import IntelligentLLMClient

    # 检测本地服务
    for port in [8001, 8000]:
        result = IntelligentLLMClient._probe_vllm_service(f"http://localhost:{port}/v1")
        if result:
            print(f"✅ 检测到本地 vLLM 服务: localhost:{port} (model: {result})")
            return True

    print("⚠️  未检测到本地 vLLM 服务")
    print("   建议先启动: vllm serve Qwen/Qwen2.5-7B-Instruct --port 8001")
    print("   或使用 --skip-llm 跳过 LLM 策略")
    return False
```

## 验收标准
- [ ] LLM Client 单例模式实现
- [ ] 第二次调用 LLM 策略无需重新加载
- [ ] 文档说明推荐的服务启动方式

## 关键文件
- `packages/sage-common/src/sage/common/components/sage_llm/client.py`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py`
```

---

## 最终任务 D: 完整实验运行 (依赖 X+A+B+C)

### Task D1: 完整实验运行与论文图表生成

**优先级**: P0 | **预估时间**: 4-6小时 | **依赖**: A1-A5, B1-B4, C1

```markdown
# Task D1: 完整实验运行与论文图表生成

## 背景
所有 SOTA 方法实现完成后，运行完整实验并生成论文所需的图表和表格。

## 前置条件
- Task A1-A5 完成 (SOTA 策略)
- Task B1-B4 完成 (SOTA 微调)
- Task C1 完成 (统一脚本)

## 任务清单

### 1. 运行完整评测实验

```bash
cd /home/shuhao/SAGE

# 完整评测 (所有策略)
python packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py \
    --eval-only \
    --max-samples 500

# 结果位置: ~/.sage/benchmark/results/
```

### 2. 运行完整训练对比

```bash
# 完整训练对比 (Methods A-H)
python packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py \
    --train \
    --train-methods A_baseline B3_coreset_hybrid C_continual D_combined E_fireact F_agenttuning G_dora \
    --train-model Qwen/Qwen2.5-7B-Instruct

# 需要 A100 或更高配置 GPU
```

### 3. 生成论文图表

```bash
# 生成所有图表和表格
python packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py \
    --paper-only \
    --results-dir ~/.sage/benchmark/results/
```

### 4. 验证结果

确认生成的文件:
- `~/.sage/benchmark/results/figures/fig1_strategy_comparison.pdf`
- `~/.sage/benchmark/results/figures/fig2_training_comparison.pdf`
- `~/.sage/benchmark/results/figures/fig3_ablation.pdf`
- `~/.sage/benchmark/results/tables/table1_main_results.tex`
- `~/.sage/benchmark/results/tables/table2_sota_comparison.tex`

### 5. 更新 TODO.md

将所有 ❌ 更新为 ✅

## 验收标准
- [ ] 所有策略在三个 Challenge 上有真实评测结果
- [ ] 所有训练方法有对比数据
- [ ] 论文图表 PDF 生成
- [ ] LaTeX 表格可直接用于论文
- [ ] 至少一个方法在每个 Challenge 达到目标 (95%/90%/95%)
```

---

## 📊 任务总览与分配建议

### 任务总览

| 任务组 | 任务 ID | 任务名称 | 优先级 | 预估时间 | 可并行 |
|--------|---------|----------|--------|----------|--------|
| **X: Bug 修复** | X1 | Tool Selection 评估 Bug | 🔴 P0 | 2-3h | ✅ |
| | X2 | Hybrid Timing LLM 问题 | 🟡 P1 | 1h | ✅ |
| | X3 | 数据文件位置梳理 | 🟡 P1 | 1-2h | ✅ |
| **A: SOTA 策略** | A1 | ToolLLM (DFSDT) | 🔴 P0 | 4-6h | ✅ |
| | A2 | ReAct 完善 | 🔴 P0 | 3-4h | ✅ |
| | A3 | Tree-of-Thoughts | 🟡 P1 | 5-6h | ✅ |
| | A4 | Gorilla | 🟢 P2 | 3-4h | ✅ |
| | A5 | API-Bank 数据 | 🟢 P2 | 2-3h | ✅ |
| **B: SOTA 微调** | B1 | FireAct | 🟡 P1 | 4-5h | ✅ |
| | B2 | AgentTuning | 🟡 P1 | 3-4h | ✅ |
| | B3 | ToolAlpaca 数据 | 🟢 P2 | 2-3h | ✅ |
| | B4 | DoRA/LoRA+ | 🟢 P2 | 3-4h | ✅ |
| **C: 基础设施** | C1 | 统一实验脚本整合 | 🔴 P0 | 2-3h | ✅ |
| | C2 | 单元测试覆盖 | 🟡 P1 | 3-4h | ✅ |
| | C3 | API 文档完善 | 🟢 P2 | 2-3h | ✅ |
| | C4 | Rule-based 基准线优化 | 🟡 P1 | 2-3h | ✅ |
| | C5 | LLM 缓存机制 | 🟢 P2 | 2-3h | ✅ |
| **D: 最终整合** | D1 | 完整实验 + 论文图表 | 🔴 P0 | 4-6h | ❌ |

### 任务依赖关系

```
X1 (Tool Selection Bug) ─────┐
X2 (Hybrid Timing LLM) ──────┼──→ 可立即开始 A/B/C 任务
X3 (数据位置梳理) ───────────┘

A1-A5 (SOTA 策略) ──────────┐
B1-B4 (SOTA 微调) ──────────┼──→ D1 (完整实验)
C1-C5 (基础设施) ───────────┘
```

### 推荐分配方案 (6 个 Agent)

```
🔴 Agent 0 (紧急): Task X1 + X2 + X3 (Bug 修复, 最先执行)

🔵 Agent 1: Task A1 (ToolLLM) + Task A4 (Gorilla)         [7-10h]
🔵 Agent 2: Task A2 (ReAct) + Task A3 (ToT)               [8-10h]
🔵 Agent 3: Task B1 (FireAct) + Task B2 (AgentTuning)     [7-9h]
🔵 Agent 4: Task B3 + Task B4 + Task A5                   [7-10h]
🔵 Agent 5: Task C1 + C2 + C3 + C4 + C5                   [11-16h]

🟢 最后: 任意 Agent 执行 Task D1 (完整实验)
```

### 精简分配方案 (3 个 Agent)

```
🔴 Agent 1: X1 + X2 + X3 + C1 + C4 (Bug 修复 + 基础评测)   [8-12h]
🔵 Agent 2: A1 + A2 + A3 (SOTA 策略核心)                   [12-16h]
🔵 Agent 3: B1 + B2 + B4 (SOTA 微调核心)                   [10-13h]

🟢 最后: Agent 1 执行 Task D1
```

---

## 重要文件路径速查

```
# 工具选择策略
packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/

# 规划策略
packages/sage-libs/src/sage/libs/agentic/agents/action/planning/

# Timing 策略
packages/sage-libs/src/sage/libs/agentic/agents/action/timing/

# 微调训练
packages/sage-libs/src/sage/libs/finetune/agent/

# Benchmark 适配器注册
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py

# 方法对比框架
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/experiments/method_comparison.py

# 统一实验脚本
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py

# 数据目录 (静态)
packages/sage-benchmark/src/sage/data/sources/agent_benchmark/
packages/sage-benchmark/src/sage/data/sources/agent_tools/
packages/sage-benchmark/src/sage/data/sources/agent_sft/

# 数据目录 (运行时)
~/.sage/benchmark/data/

# 结果目录
~/.sage/benchmark/results/
```

---

## ✅ 已完成的工作 (参考)

1. **三个挑战的评估框架**
   - Timing Detection: rule_based, llm_based, hybrid 策略
   - Task Planning: simple, hierarchical, llm_based 策略
   - Tool Selection: keyword, embedding, hybrid 策略

2. **数据准备脚本**
   - `prepare_timing_data.py` - 生成 1000 条 timing judgment 样本
   - `prepare_planning_data.py` - 生成 300 条 planning 样本
   - `prepare_tool_selection_data.py` - 生成 tool selection 样本

3. **论文材料生成**
   - 5 个图表 (PDF + PNG)
   - 4 个 LaTeX 表格
   - 论文引用的文件名别名

4. **一键运行脚本**
   - `--quick` 快速模式
   - `--skip-llm` 跳过 LLM 策略
   - `--paper-only` 仅生成论文材料

5. **基础微调框架**
   - AgentSFTTrainer + AgentSFTConfig
   - CoresetSelector (loss_topk, diversity, hybrid)
   - OnlineContinualLearner

---

## 📝 使用说明

1. **分发任务**: 复制对应 Task 的 markdown 代码块给不同的 Agent
2. **并行执行**: 同一任务组内的任务可以并行执行
3. **验收检查**: 每个任务完成后检查「验收标准」列表
4. **依赖顺序**: Task D1 需要等其他任务完成后执行

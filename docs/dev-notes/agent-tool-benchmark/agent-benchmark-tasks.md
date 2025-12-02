# Agent Benchmark 开发任务拆分（可并行版本）

> 当前状态：测试框架基本完成，但缺少真实数据和真实执行能力。图表中的数据是模拟的示例数据。

## 背景

**难题4: Agent平台海量工具业务下的规划和工具调用准确率提升**

三个核心挑战：
1. **时机判断** (Timing Detection): 对话/融合回复时机判断，目标 ≥95%
2. **任务规划** (Task Planning): 隐式任务规划 (5-10步)，目标 ≥90%  
3. **工具选择** (Tool Selection): 全量候选工具调用 (1000+ tools)，目标 ≥95%

---

## 任务依赖说明

这三个任务按**挑战维度**拆分，每个任务独立完成一个挑战的**端到端**流程：

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   任务 A        │  │   任务 B        │  │   任务 C        │
│  时机判断       │  │  任务规划       │  │  工具选择       │
│  (Challenge 1)  │  │  (Challenge 2)  │  │  (Challenge 3)  │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • 数据准备      │  │ • 数据准备      │  │ • 数据准备      │
│ • 策略实现      │  │ • 策略实现      │  │ • 策略实现      │
│ • 评测执行      │  │ • 评测执行      │  │ • 评测执行      │
│ • 结果可视化    │  │ • 结果可视化    │  │ • 结果可视化    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
        ↓                    ↓                    ↓
        └────────────────────┼────────────────────┘
                             ↓
                    ┌─────────────────┐
                    │   最终整合      │
                    │  (3任务完成后)  │
                    └─────────────────┘
```

**✅ 可并行原因**：每个任务负责一个独立的挑战，不依赖其他任务的产出。

---

## 任务 A: 时机判断 (Timing Detection) 端到端实现

### 目标
完成挑战1「对话/融合回复时机判断」的完整评测流程，目标准确率 ≥95%。

### 范围
- 数据：timing_judgment 数据集准备
- 策略：TimingDecider 实现（Rule-based / LLM-based / Hybrid）
- 评测：TimingDetectionExperiment 真实执行
- 可视化：时机判断准确率图表

### Copilot 提示词

```
请帮我完成 SAGE 的「时机判断」(Timing Detection) 挑战的端到端实现：

## 背景
挑战1: 对话/融合回复时机判断 - 判断用户消息是否需要调用工具，目标准确率 ≥95%

## 任务清单

### 1. 数据准备
查看并实现 timing_judgment 数据加载：
- 检查 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/experiments/timing_detection_exp.py`
- 理解 Sample 需要的字段: sample_id, message, should_call_tool (bool), direct_answer, context
- 创建数据准备脚本 `packages/sage-benchmark/scripts/prepare_timing_data.py`：
  - 从公开数据集转换（如 ToolBench 的对话数据）
  - 或生成合成数据（需要调用/不需要调用的消息各 500 条）
  - 数据格式：JSONL，每行包含上述字段
- 配置 DataManager 能够加载这些数据

### 2. 策略实现
检查并完善 TimingDecider：
- 查看 `packages/sage-libs/src/sage/libs/agentic/agents/action/` 下的实现
- 确保有以下策略可用：
  - `timing.rule_based`: 基于规则的判断（关键词匹配等）
  - `timing.llm_based`: 基于 LLM 的判断
  - `timing.hybrid`: 混合策略
- 每个策略需实现 `decide(message) -> TimingDecision` 接口
- TimingDecision 包含: should_call_tool (bool), confidence (float), reasoning (str)

### 3. 评测执行
修复并运行 TimingDetectionExperiment：
- 检查 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/experiments/timing_detection_exp.py`
- 确保 `prepare()` 能正确加载数据和策略
- 确保 `run()` 能输出 predictions 和 references
- 检查 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/evaluation/metrics.py`
- 实现或修复 timing 相关指标：accuracy, precision, recall, f1

### 4. 验证脚本
创建端到端验证脚本 `packages/sage-benchmark/scripts/test_timing_e2e.py`：
```python
#!/usr/bin/env python3
"""End-to-end test for Timing Detection (Challenge 1)"""
from sage.benchmark.benchmark_agent import (
    TimingDetectionConfig,
    TimingDetectionExperiment,
    get_adapter_registry
)
from sage.benchmark.benchmark_agent.evaluation import compute_metrics
from sage.data import DataManager

def main():
    dm = DataManager.get_instance()
    registry = get_adapter_registry()

    # 测试不同策略
    for detector in ["timing.rule_based", "timing.llm_based", "timing.hybrid"]:
        print(f"\n{'='*50}")
        print(f"Testing: {detector}")
        print(f"{'='*50}")

        config = TimingDetectionConfig(
            profile="timing_eval",
            split="test",
            detector=detector,
            threshold=0.5,
            max_samples=100,
            verbose=True
        )

        exp = TimingDetectionExperiment(config, dm, registry)
        exp.prepare()
        result = exp.run()

        metrics = compute_metrics(
            task="timing_detection",
            predictions=result.predictions,
            references=result.references,
            metrics=["accuracy", "precision", "recall", "f1"]
        )

        print(f"Results: {metrics}")
        print(f"Target: accuracy >= 95%")

if __name__ == "__main__":
    main()
```

### 5. 结果可视化
在验证脚本中添加图表生成，对比不同策略的准确率。

## 验证标准
- [ ] 数据加载成功，至少 500 条样本
- [ ] 三种策略都能执行
- [ ] 输出真实的 accuracy 指标
- [ ] 生成策略对比图表

请逐步完成以上任务。
```

### 预期产出
- `scripts/prepare_timing_data.py` - 数据准备脚本
- `scripts/test_timing_e2e.py` - 端到端验证脚本
- timing_judgment 数据集 (500+ 条)
- 时机判断准确率报告和图表

---

## 任务 B: 任务规划 (Task Planning) 端到端实现

### 目标
完成挑战2「隐式任务规划」的完整评测流程，5-10步规划成功率 ≥90%。

### 范围
- 数据：task_planning 数据集准备
- 策略：HierarchicalPlanner 实现
- 评测：PlanningExperiment 真实执行
- 可视化：规划成功率图表

### Copilot 提示词

```
请帮我完成 SAGE 的「任务规划」(Task Planning) 挑战的端到端实现：

## 背景
挑战2: 隐式任务规划 - 将复杂指令分解为5-10步的工具调用序列，目标成功率 ≥90%

## 任务清单

### 1. 数据准备
查看并实现 task_planning 数据加载：
- 检查 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/experiments/planning_exp.py`
- 理解 Sample 需要的字段: sample_id, instruction, context, available_tools, ground_truth_steps
- ground_truth_steps 是一个列表，每个 step 包含: step_id, description, tool_id, dependencies
- 创建数据准备脚本 `packages/sage-benchmark/scripts/prepare_planning_data.py`：
  - 从 ToolBench/APIBench 等数据集转换
  - 或基于工具库生成合成的多步任务（5-10步）
  - 确保包含工具依赖关系
- 配置 DataManager 能够加载这些数据

### 2. 策略实现
检查并完善 Planner：
- 查看 `packages/sage-libs/src/sage/libs/agentic/agents/planning/` 下的实现
- 确保有以下策略可用：
  - `planner.simple`: 简单的线性规划
  - `planner.hierarchical`: 层次化规划（支持依赖图）
  - `planner.llm_based`: 基于 LLM 的规划
- 每个策略需实现 `plan(task) -> Plan` 接口
- Plan 包含: steps (list), tool_sequence (list), dependencies (dict)

### 3. 评测执行
修复并运行 PlanningExperiment：
- 检查 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/experiments/planning_exp.py`
- 注意：当前代码直接使用 `self.config.verbose`，需改为 `getattr(self.config, "verbose", False)`
- 确保 `prepare()` 能正确加载数据和策略
- 确保 `run()` 能输出 predictions 和 references
- 检查指标计算：
  - step_accuracy: 步骤预测准确率
  - sequence_match: 工具序列完全匹配率
  - dependency_accuracy: 依赖关系准确率

### 4. 验证脚本
创建端到端验证脚本 `packages/sage-benchmark/scripts/test_planning_e2e.py`：
```python
#!/usr/bin/env python3
"""End-to-end test for Task Planning (Challenge 2)"""
from sage.benchmark.benchmark_agent import (
    PlanningConfig,
    PlanningExperiment,
    get_adapter_registry
)
from sage.benchmark.benchmark_agent.evaluation import compute_metrics
from sage.data import DataManager

def main():
    dm = DataManager.get_instance()
    registry = get_adapter_registry()

    # 测试不同策略
    for planner in ["planner.simple", "planner.hierarchical", "planner.llm_based"]:
        print(f"\n{'='*50}")
        print(f"Testing: {planner}")
        print(f"{'='*50}")

        config = PlanningConfig(
            profile="planning_eval",
            split="test",
            planner=planner,
            max_steps=10,
            max_samples=100,
            verbose=True
        )

        exp = PlanningExperiment(config, dm, registry)
        exp.prepare()
        result = exp.run()

        metrics = compute_metrics(
            task="task_planning",
            predictions=result.predictions,
            references=result.references,
            metrics=["step_accuracy", "sequence_match", "plan_success_rate"]
        )

        print(f"Results: {metrics}")
        print(f"Target: plan_success_rate >= 90%")

if __name__ == "__main__":
    main()
```

### 5. 结果可视化
生成规划成功率对比图表，展示不同策略和不同步数(5/7/10步)的成功率。

## 验证标准
- [ ] 数据加载成功，至少 300 条多步任务样本
- [ ] 三种策略都能执行
- [ ] 输出真实的 plan_success_rate 指标
- [ ] 生成策略对比图表

请逐步完成以上任务。
```

### 预期产出
- `scripts/prepare_planning_data.py` - 数据准备脚本
- `scripts/test_planning_e2e.py` - 端到端验证脚本
- task_planning 数据集 (300+ 条)
- 规划成功率报告和图表

---

## 任务 C: 工具选择 (Tool Selection) 端到端实现

### 目标
完成挑战3「全量候选工具调用」的完整评测流程，1000+工具选择准确率 ≥95%。

### 范围
- 数据：tool_selection 数据集准备（含1000+工具库）
- 策略：EmbeddingSelector / KeywordSelector / HybridSelector 实现
- 评测：ToolSelectionExperiment 真实执行
- 可视化：工具选择准确率图表

### Copilot 提示词

```
请帮我完成 SAGE 的「工具选择」(Tool Selection) 挑战的端到端实现：

## 背景
挑战3: 全量候选工具调用 - 从1000+工具中准确选择，目标 Top-K 准确率 ≥95%

## 任务清单

### 1. 数据准备
查看并实现 tool_selection 数据加载：
- 检查 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/experiments/tool_selection_exp.py`
- 理解 Sample 需要的字段: sample_id, instruction, context, candidate_tools, ground_truth_tools, top_k
- candidate_tools 是候选工具列表（测试大规模时需 100-1000 个）
- ground_truth_tools 是正确答案列表（通常 1-5 个）
- 创建数据准备脚本 `packages/sage-benchmark/scripts/prepare_tool_selection_data.py`：
  - 准备工具库（1000+ 工具定义，每个包含 name, description, parameters）
  - 可从 ToolBench、BFCL、Gorilla 等数据集获取
  - 生成评测样本：instruction + 从工具库采样的 candidate_tools + ground_truth
- 配置 DataManager 能够加载这些数据

### 2. 策略实现
检查并完善 Selector：
- 查看 `packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/` 下的实现
- 确保有以下策略可用：
  - `selector.keyword`: 基于关键词匹配的选择器
  - `selector.embedding`: 基于嵌入相似度的选择器（需要 embedding_client）
  - `selector.hybrid`: 混合策略（关键词 + 嵌入）
  - `selector.llm_rerank`: LLM 重排序
- 每个策略需实现 `predict(query, top_k) -> list[ToolPrediction]` 接口
- ToolPrediction 包含: tool_id, score, reason

### 3. 评测执行
修复并运行 ToolSelectionExperiment：
- 检查 `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/experiments/tool_selection_exp.py`
- 注意第90行: `embedding_client=None,  # TODO: Add embedding support`
- 需要实现 embedding_client 的初始化（可用 OpenAI/Jina/本地模型）
- 确保 `prepare()` 能正确加载数据、工具库和策略
- 确保 `run()` 能输出 predictions 和 references
- 检查指标计算：
  - top_k_accuracy: Top-K 中包含正确答案的比例
  - recall_at_k: 召回率
  - precision_at_k: 精确率
  - mrr: Mean Reciprocal Rank

### 4. 验证脚本
创建端到端验证脚本 `packages/sage-benchmark/scripts/test_tool_selection_e2e.py`：
```python
#!/usr/bin/env python3
"""End-to-end test for Tool Selection (Challenge 3)"""
from sage.benchmark.benchmark_agent import (
    ToolSelectionConfig,
    ToolSelectionExperiment,
    get_adapter_registry
)
from sage.benchmark.benchmark_agent.evaluation import compute_metrics
from sage.data import DataManager

def main():
    dm = DataManager.get_instance()
    registry = get_adapter_registry()

    # 测试不同规模和策略
    for num_candidates in [100, 500, 1000]:
        for selector in ["selector.keyword", "selector.embedding", "selector.hybrid"]:
            print(f"\n{'='*50}")
            print(f"Testing: {selector} with {num_candidates} candidates")
            print(f"{'='*50}")

            config = ToolSelectionConfig(
                profile="tool_selection_eval",
                split="test",
                selector=selector,
                top_k=5,
                num_candidates=num_candidates,  # 控制候选工具数量
                max_samples=100,
                verbose=True
            )

            exp = ToolSelectionExperiment(config, dm, registry)
            exp.prepare()
            result = exp.run()

            metrics = compute_metrics(
                task="tool_selection",
                predictions=result.predictions,
                references=result.references,
                metrics=["top_k_accuracy", "recall_at_k", "precision_at_k", "mrr"],
                k=5
            )

            print(f"Results: {metrics}")
            print(f"Target: top_k_accuracy >= 95%")

if __name__ == "__main__":
    main()
```

### 5. 结果可视化
生成图表展示：
- 不同候选工具数量(100/500/1000)下的准确率变化
- 不同策略的对比（Keyword vs Embedding vs Hybrid）
- 不同 Top-K (1/3/5/10) 的准确率

## 验证标准
- [ ] 工具库加载成功，至少 1000 个工具定义
- [ ] 数据加载成功，至少 500 条样本
- [ ] 三种策略都能执行
- [ ] 输出真实的 top_k_accuracy 指标
- [ ] 生成不同规模和策略的对比图表

请逐步完成以上任务。
```

### 预期产出
- `scripts/prepare_tool_selection_data.py` - 数据准备脚本
- `scripts/test_tool_selection_e2e.py` - 端到端验证脚本
- 工具库 (1000+ 工具定义)
- tool_selection 数据集 (500+ 条)
- 工具选择准确率报告和图表

---

## 最终整合（三个任务完成后）

当任务 A、B、C 都完成后，运行以下命令生成综合报告：

```bash
# 运行综合测试脚本
python packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_tests_and_visualize.py --full

# 或分别运行
python packages/sage-benchmark/scripts/test_timing_e2e.py
python packages/sage-benchmark/scripts/test_planning_e2e.py  
python packages/sage-benchmark/scripts/test_tool_selection_e2e.py
```

整合后的图表应展示：
- 三个挑战的综合对比（雷达图）
- 各挑战的达标情况（vs 95%/90%/95% 目标线）
- SAGE 方案 vs Baseline 的提升幅度

---

## 文件结构

```
packages/sage-benchmark/
├── scripts/                              # [新建] 独立验证脚本
│   ├── prepare_timing_data.py           # 任务A: 时机判断数据
│   ├── prepare_planning_data.py         # 任务B: 任务规划数据
│   ├── prepare_tool_selection_data.py   # 任务C: 工具选择数据
│   ├── test_timing_e2e.py               # 任务A: 端到端测试
│   ├── test_planning_e2e.py             # 任务B: 端到端测试
│   └── test_tool_selection_e2e.py       # 任务C: 端到端测试
├── src/sage/benchmark/benchmark_agent/
│   ├── experiments/
│   │   ├── timing_detection_exp.py      # 任务A: 实验类
│   │   ├── planning_exp.py              # 任务B: 实验类
│   │   └── tool_selection_exp.py        # 任务C: 实验类
│   └── evaluation/
│       └── metrics.py                    # 各任务指标计算
└── data/                                 # [新建] 评测数据
    ├── timing_judgment/                  # 任务A 数据
    ├── task_planning/                    # 任务B 数据
    └── tool_selection/                   # 任务C 数据
```

---

## 任务分配建议

| 任务 | 复杂度 | 预估时间 | 可并行 |
|-----|--------|---------|--------|
| **任务 A: 时机判断** | 中等 | 2-3小时 | ✅ |
| **任务 B: 任务规划** | 较高 | 3-4小时 | ✅ |
| **任务 C: 工具选择** | 较高 | 3-4小时 | ✅ |

三个任务可以分配给不同的 Copilot 会话并行完成。

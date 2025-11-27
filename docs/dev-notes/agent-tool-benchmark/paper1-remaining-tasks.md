# Paper 1 (SAGE-Bench) 剩余任务 - 完整指南

> 本文档定义了完成 SAGE-Bench Benchmark 论文所需的所有任务
> 每个任务都可以分配给不同的 Copilot Agent 并行执行
>
> **生成日期**: 2025-11-27

---

## 🚀 统一入口 CLI (重要)

**在执行任何实验之前，请优先使用统一的交互式 CLI 入口：**

```bash
# 进入脚本目录
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts

# 方式 1: 交互式运行 (推荐)
python sage_benchmark_cli.py

# 方式 2: 直接指定实验 (跳过确认)
python sage_benchmark_cli.py --paper 1 --experiment tool_selection --yes
python sage_benchmark_cli.py --paper 1 --experiment all_challenges --yes

# 方式 3: 列出所有可用实验
python sage_benchmark_cli.py --list
```

**⚠️ 注意**: 使用 `--yes` 或 `-y` 参数可以跳过确认提示，直接运行实验。

**CLI 支持的 Paper 1 实验：**

| ID | 名称 | 描述 | 预估时间 |
|----|------|------|----------|
| `timing` | Challenge 1 | 评测何时调用工具 | ~10 min |
| `planning` | Challenge 2 | 评测任务分解与规划 | ~15 min |
| `tool_selection` | Challenge 3 | 评测工具检索与选择 | ~20 min |
| `all_challenges` | 完整评测 | 运行所有 3 个 Challenge | ~2 hours |
| `cross_dataset` | 跨数据集 | SAGE + ACEBench + ToolBench | ~30 min |
| `quick_benchmark` | 快速评测 | 跳过 LLM 方法 | ~30 min |

---

## 📊 当前状态概览

| 组件 | 状态 | 说明 |
|------|------|------|
| 数据集 (SAGE-Bench) | ✅ 完成 | 1,200 样本 + 1,200 工具 |
| ACEBench 集成 | ✅ 完成 | HuggingFace 加载正常 |
| Keyword/Embedding/Hybrid | ✅ 工作 | 基础方法正常 |
| **Gorilla** | ❌ Bug | 工具索引 ID 不匹配 |
| **DFSDT** | ❌ Bug | 工具索引 ID 不匹配 |
| **Timing Decider** | ❌ Bug | 接口不兼容 (dict vs object) |
| LLM-based 方法 | ⚠️ 未完整测试 | 需要验证 |
| 论文图表 | ⚠️ 需完善 | 需要最终结果 |

### 当前性能基准

| Challenge | Best Method | Current | Target | Gap |
|-----------|-------------|---------|--------|-----|
| Timing | Rule-based | 76% | 95% | -19% |
| Planning | Hierarchical | 27% | 90% | -63% |
| Tool Selection | BM25 | 82% | 95% | -13% |

---

## 🔧 Task 1: 修复 Timing Decider 接口不兼容

### 问题描述

`timing.rule_based`, `timing.llm_based`, `timing.hybrid` 期望的是带 `.message` 属性的对象，但 benchmark 传入的是 dict。

### 提示词

```
请帮我修复 SAGE benchmark 中 Timing Decider 的接口不兼容问题。

## 问题描述

Timing Decider 方法 (`timing.rule_based`, `timing.llm_based`, `timing.hybrid`)
期望输入是带 `.message` 属性的对象，但 benchmark 传入的是 dict 格式。

## 关键文件位置

- Adapter Registry: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
- Timing Decider: `packages/sage-libs/src/sage/libs/agentic/agents/planning/timing_decider.py`
- Schemas: `packages/sage-libs/src/sage/libs/agentic/agents/planning/schemas.py`

## 修复方案

在 `TimingAdapter.decide()` 中添加输入转换：

```python
def decide(self, message: Any, **kwargs) -> Any:
    # 如果是 dict，转换为 TimingMessage
    if isinstance(message, dict):
        from sage.libs.agentic.agents.planning.schemas import TimingMessage
        message = TimingMessage(
            message=message.get('instruction', ''),
            context=message.get('context', {})
        )
    return self.decider.decide(message)
```

## 统一入口 CLI

修复后，使用统一 CLI 验证：
```bash
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
python sage_benchmark_cli.py --paper 1 --experiment timing
```

## 成功标准

- `timing.rule_based` 返回有效的 true/false 判断
- `timing.llm_based` 正常调用 LLM
- `timing.hybrid` 组合判断正常
- 无 AttributeError 或 KeyError
```

---

## 🔧 Task 2: 修复 Gorilla/DFSDT 工具索引问题

### 问题描述

当前 Gorilla 和 DFSDT 选择器在评测时返回 0% 准确率，原因是：
- 选择器构建索引时使用的是 mock 工具 ID (`tool_000`, `tool_001`...)
- 但数据集中的 `candidate_tools` 使用的是实际工具 ID (`environment_weather_001`, `finance_payment_001`...)

### 提示词

```
请帮我修复 SAGE benchmark 中 Gorilla 和 DFSDT 选择器的工具索引问题。

## 问题描述

当前 Gorilla 和 DFSDT 选择器在评测时返回 0% 准确率，原因是：
- 选择器构建索引时使用的是 mock 工具 ID (`tool_000`, `tool_001`...)
- 但数据集中的 `candidate_tools` 使用的是实际工具 ID (`environment_weather_001`, `finance_payment_001`...)

## 关键文件位置

- 工具目录: `packages/sage-benchmark/src/sage/data/sources/agent_tools/data/tool_catalog.jsonl` (1,200 个工具)
- 评测数据: `packages/sage-benchmark/src/sage/data/sources/agent_benchmark/splits/tool_selection.jsonl`
- Adapter Registry: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
- Gorilla 实现: `packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/gorilla_selector.py`
- DFSDT 实现: `packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/dfsdt_selector.py`

## 工具目录格式 (tool_catalog.jsonl)

每行一个 JSON 对象：
{
  "tool_id": "environment_weather_001",
  "name": "Weather Fetch 1",
  "category": "environment/weather",
  "capabilities": ["forecast", "radar"],
  "inputs": [...],
  "outputs": [...],
  ...
}

## 数据样本格式 (tool_selection.jsonl)

{
  "sample_id": "ts_000002",
  "instruction": "What's the weather in Paris?",
  "candidate_tools": ["environment_weather_001", "finance_payment_024", ...],
  "ground_truth": {"top_k": ["environment_weather_001"]}
}

## 需要完成的工作

1. **创建 SageToolsLoader 类**
   - 位置: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/tools_loader.py` (新文件)
   - 功能: 加载 `tool_catalog.jsonl` 中的 1,200 个工具
   - 实现 `iter_all()` 方法，返回工具对象

2. **修改 adapter_registry.py**
   - 在创建 Gorilla/DFSDT 时，使用 SageToolsLoader 而非 mock tools
   - 确保 `SelectorResources.tools_loader` 使用正确的加载器

3. **验证修复**
   - 使用统一 CLI: `python sage_benchmark_cli.py --paper 1 --experiment tool_selection`
   - 或直接运行: `python run_unified_eval.py --dataset sage --methods gorilla,dfsdt --samples 20`
   - 预期: 准确率应该 > 0%

## 统一入口 CLI

```bash
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
python sage_benchmark_cli.py --paper 1 --experiment tool_selection
```

## 成功标准

- Gorilla Top-5 准确率 > 60%
- DFSDT Top-5 准确率 > 60%
- 无 "No tools retrieved" 警告
```

---

## 🔧 Task 3: 完善 LLM-based 方法测试

### 提示词

```
请帮我完善 SAGE benchmark 中 LLM-based 方法的测试和验证。

## 背景

SAGE-Bench 需要评测以下 LLM-based 方法：
- Tool Selection: `llm_direct` (直接用 LLM 选择工具)
- Timing: `timing.llm_based` (用 LLM 判断是否需要工具)
- Planning: `planner.llm_based`, `planner.react`, `planner.tot`

这些方法需要 LLM 服务支持，可以使用：
1. 本地 vLLM 服务 (localhost:8001)
2. Embedded vLLM (进程内加载)
3. 云端 API (DashScope)

## 关键文件位置

- **统一入口 CLI**: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/sage_benchmark_cli.py`
- Unified Eval: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_unified_eval.py`
- All Experiments: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py`
- Adapter Registry: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
- LLM Client: `packages/sage-common/src/sage/common/components/sage_llm/client.py`

## 需要完成的工作

1. **验证 LLM-based Selector**
   - 测试 `llm_direct` 方法在 SAGE 数据集上的表现
   - 确保正确调用 IntelligentLLMClient

2. **验证 LLM-based Timing**
   - 测试 `timing.llm_based` 方法
   - 检查 prompt 模板是否合理

3. **验证 LLM-based Planning**
   - 测试 `planner.llm_based`, `planner.react`, `planner.tot`
   - 确保规划结果格式正确

4. **添加 --use-embedded 模式支持**
   - 确保 `run_unified_eval.py --use-embedded` 正常工作
   - 默认使用 Qwen/Qwen2.5-0.5B-Instruct 进行测试

## 统一入口 CLI (推荐)

```bash
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts

# 交互式运行
python sage_benchmark_cli.py

# 或直接指定
python sage_benchmark_cli.py --paper 1 --experiment all_challenges
```

## 测试命令 (备用)

```bash
# 测试 LLM-based selector
python run_unified_eval.py --dataset sage --methods llm_direct --samples 10 -v

# 使用 embedded vLLM
python run_unified_eval.py --dataset sage --methods llm_direct --samples 10 --use-embedded -v

# 测试所有 LLM 方法
python run_all_experiments.py --quick --max-samples 10
```

## 成功标准

- `llm_direct` 返回有效的工具选择结果
- `timing.llm_based` 返回合理的 true/false 判断
- `planner.react` 和 `planner.tot` 返回有效的规划步骤
- 无 API 调用错误或超时

## 注意事项

- 如果本地没有 LLM 服务，使用 `IntelligentLLMClient.create_auto()` 会自动回退到云端
- 云端 API 需要 `SAGE_CHAT_API_KEY` 环境变量
- Embedded 模式需要足够的 GPU 内存
```

---

## 🔧 Task 4: 跨数据集验证完善

### 提示词

```
请帮我完善 SAGE benchmark 的跨数据集验证功能。

## 背景

SAGE-Bench 论文需要在多个数据集上验证工具选择方法：
1. **SAGE-Bench** (自有数据集): 600 tool selection 样本
2. **ACEBench/ToolACE** (外部数据集): HuggingFace Team-ACE/ToolACE
3. **API-Bank** (可选): Microsoft 多轮 API 对话
4. **ToolAlpaca** (可选): Microsoft 工具学习对话

## 关键文件位置

- **统一入口 CLI**: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/sage_benchmark_cli.py`
- Unified Eval: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_unified_eval.py`
- ACEBench Loader: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/acebench_loader.py`
- External Benchmarks: `packages/sage-benchmark/src/sage/data/sources/agent_benchmark/external_benchmarks/`

## 当前状态

- SAGE 数据集: ✅ 正常加载
- ACEBench: ✅ 可从 HuggingFace 加载，但需要验证所有方法
- API-Bank: ⚠️ 有原始数据，未集成
- ToolAlpaca: ⚠️ 有原始数据，未集成

## 需要完成的工作

1. **验证 ACEBench 在所有方法上的评测**
   - 使用统一 CLI: `python sage_benchmark_cli.py --paper 1 --experiment cross_dataset`
   - 确保结果格式与 SAGE 一致

2. **集成 API-Bank 数据集** (可选)
   - 创建 `apibank_loader.py`
   - 转换为统一的 ToolSelectionSample 格式

3. **生成跨数据集对比表格**
   - 格式: Dataset × Method × Metric

## 统一入口 CLI

```bash
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts

# 跨数据集对比
python sage_benchmark_cli.py --paper 1 --experiment cross_dataset

# 或手动指定
python run_unified_eval.py --dataset acebench --methods keyword,embedding,hybrid --samples 100
```

## 成功标准

- ACEBench 上所有方法正常运行
- 结果可以与 SAGE 数据集结果对比
- 生成统一格式的 JSON 结果文件
```

---

## 🔧 Task 5: Scaling 分析实验

### 提示词

```
请帮我完成 SAGE benchmark 的 Scaling 分析实验。

## 背景

论文需要分析工具数量对选择准确率的影响，生成 Tool Count vs Accuracy 曲线。

## 实验配置

- 工具数量: 100, 500, 1000, 1200 (full)
- 方法: keyword, embedding, hybrid
- 样本数: 200 per configuration

## 统一入口 CLI

```bash
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts

# 先确认 CLI 可用
python sage_benchmark_cli.py --list
```

## 需要完成的工作

1. **在 run_unified_eval.py 中添加 --num-candidate-tools 参数**

2. **运行 Scaling 实验**
```bash
for num_tools in 100 500 1000 1200; do
    python run_unified_eval.py --dataset sage --num-candidate-tools $num_tools --samples 200
done
```

3. **生成可视化图表**
   - X 轴: Tool Count
   - Y 轴: Top-5 Accuracy
   - 多条线: 不同方法

## 成功标准

- 生成 scaling_analysis.png 图表
- 数据保存到 JSON 文件
```

---

## 🔧 Task 6: 消融实验

### 提示词

```
请帮我完成 SAGE benchmark 的消融实验。

## Hybrid Selector 消融

测试不同 keyword_weight 对 hybrid 选择器的影响：
- keyword_weight = 0.0 (纯 embedding)
- keyword_weight = 0.5 (平衡)
- keyword_weight = 1.0 (纯 keyword)

## Timing Hybrid 消融

测试不同组合策略：
- rule_only
- llm_only
- hybrid (rule + llm)

## 统一入口 CLI

```bash
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
python sage_benchmark_cli.py --paper 1 --experiment all_challenges
```

## 成功标准

- 生成消融实验结果表格
- 结果保存到 ablation_results.json
```

---

## 🔧 Task 7: 论文图表生成

### 提示词

```
请帮我生成 SAGE-Bench 论文所需的图表。

## 需要生成的图表

1. **Main Results Table**: 所有方法在 3 个 Challenge 上的表现
2. **Cross-Dataset Comparison**: SAGE vs ACEBench vs API-Bank
3. **Scaling Analysis**: Tool Count vs Accuracy
4. **Ablation Study**: Hybrid selector 消融

## 数据来源

- 主结果: `.sage/benchmark/results/all_results.json`
- 跨数据集: `.sage/benchmark/results/cross_dataset/`
- Scaling: `.sage/benchmark/results/scaling/`

## 统一入口 CLI

先运行完整实验：
```bash
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
python sage_benchmark_cli.py --paper 1 --experiment all_challenges
```

## 输出位置

- 图表: `experiment_results/figures/`
- 表格: `experiment_results/tables/`
```

---

## 📋 优先级排序

### P0 - 必须完成 (阻塞论文)

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 1 | 修复 Timing Decider 接口 | ❌ | 接口不兼容 |
| 2 | 修复 Gorilla/DFSDT 索引 | ❌ | 返回 0% 准确率 |
| 3 | 完成 SAGE 完整实验 | ⚠️ | 需要修复 Bug 后运行 |
| 4 | 完成 ACEBench 实验 | ⚠️ | 需要验证所有方法 |

### P1 - 重要 (论文完善)

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 5 | LLM-based 方法测试 | ⚠️ | 需要验证 |
| 6 | Scaling 分析实验 | ❌ | 未开始 |
| 7 | 消融实验 | ❌ | 未开始 |
| 8 | 论文图表生成 | ❌ | 依赖实验结果 |

### P2 - 可选增强

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| 9 | API-Bank 集成 | ❌ | 可选 |
| 10 | 不同 LLM 模型对比 | ❌ | 可选 |

---

## 📋 任务依赖和执行顺序

```
┌─────────────────────────────────────────────────────────────┐
│                    可并行执行的任务                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Task 1              Task 2              Task 3             │
│  (Timing 接口)       (Gorilla/DFSDT)     (LLM-based)        │
│       │                  │                   │              │
│       └──────────────────┼───────────────────┘              │
│                          │                                  │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────┐          │
│  │ Task 4: 跨数据集验证                           │          │
│  └───────────────────────────────────────────────┘          │
│                          │                                  │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────┐          │
│  │ Task 5-6: Scaling + 消融实验                   │          │
│  └───────────────────────────────────────────────┘          │
│                          │                                  │
│                          ▼                                  │
│  ┌───────────────────────────────────────────────┐          │
│  │ Task 7: 论文图表生成                           │          │
│  └───────────────────────────────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**执行建议**:
- Task 1, 2, 3 可以分配给 3 个不同的 Copilot Agent 并行执行
- Task 4-7 需要等 Task 1-3 基本完成后执行
- 每个 Task 预计 2-3 小时

---

## 🛠️ 快速开始

```bash
# 1. 进入脚本目录
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts

# 2. 使用统一 CLI (推荐)
python sage_benchmark_cli.py

# 3. 或直接运行特定实验
python sage_benchmark_cli.py --paper 1 --experiment tool_selection

# 4. 列出所有可用实验
python sage_benchmark_cli.py --list
```

---

## 📁 文件位置参考

```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/
├── scripts/
│   ├── sage_benchmark_cli.py      # 🌟 统一交互式入口 (推荐)
│   ├── run_all_experiments.py     # 三 Challenge 完整实验
│   ├── run_unified_eval.py        # Tool Selection 评估
│   └── README.md                  # 脚本文档
├── adapter_registry.py            # 需要修复: 接口适配
├── acebench_loader.py             # ACEBench 数据加载
└── experiments/                   # 实验定义

packages/sage-benchmark/src/sage/data/sources/
├── agent_tools/data/
│   └── tool_catalog.jsonl         # 1,200 个工具定义
└── agent_benchmark/splits/
    └── tool_selection.jsonl       # 评测数据

packages/sage-libs/src/sage/libs/agentic/agents/
├── action/tool_selection/
│   ├── gorilla_selector.py        # 需要修复: 工具索引
│   └── dfsdt_selector.py          # 需要修复: 工具索引
└── planning/
    ├── timing_decider.py          # 需要修复: 接口
    └── schemas.py                 # TimingMessage 定义
```

---

## 🔧 环境准备

```bash
# 确保在正确的分支
cd /home/shuhao/SAGE
git checkout feature/agent_tools_plan

# 激活环境
conda activate sage

# 验证安装
python -c "from sage.benchmark.benchmark_agent.adapter_registry import get_adapter_registry; print('OK')"
```

---

## 📝 提交规范

完成任务后，请使用以下 commit 格式：

```bash
# Task 1
git commit -m "fix(benchmark): resolve Timing Decider interface compatibility issue"

# Task 2
git commit -m "fix(benchmark): resolve Gorilla/DFSDT tool index mismatch issue"

# Task 3
git commit -m "feat(benchmark): complete LLM-based methods testing and validation"

# Task 4
git commit -m "feat(benchmark): enhance cross-dataset validation with ACEBench"

# Task 5-6
git commit -m "feat(benchmark): add scaling analysis and ablation experiments"

# Task 7
git commit -m "docs(benchmark): generate ICML paper figures and LaTeX tables"
```

---

## ⚠️ 重要提醒

1. **优先使用统一 CLI**: `sage_benchmark_cli.py` 是所有实验的统一入口
2. **修复 Bug 优先**: Task 1-2 是 P0 优先级，阻塞后续实验
3. **LLM 服务**: LLM-based 方法需要 API Key 或本地服务
4. **GPU 内存**: Embedded vLLM 模式需要足够的 GPU 内存

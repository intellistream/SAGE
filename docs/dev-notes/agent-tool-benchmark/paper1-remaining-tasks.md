# Paper 1 (SAGE-Bench) 剩余任务 - 并行执行指南

> 本文档定义了完成 SAGE-Bench Benchmark 论文所需的 4 个独立任务
> 每个任务都可以分配给不同的 Copilot Agent 并行执行

---

## 📊 当前状态概览

| 组件 | 状态 | 说明 |
|------|------|------|
| 数据集 (SAGE-Bench) | ✅ 完成 | 1,200 样本 + 1,200 工具 |
| ACEBench 集成 | ✅ 完成 | HuggingFace 加载正常 |
| Keyword/Embedding/Hybrid | ✅ 工作 | 基础方法正常 |
| **Gorilla** | ❌ Bug | 工具索引 ID 不匹配 |
| **DFSDT** | ❌ Bug | 工具索引 ID 不匹配 |
| LLM-based 方法 | ⚠️ 未完整测试 | 需要验证 |
| 论文图表 | ⚠️ 需完善 | 需要最终结果 |

---

## Task 1: 修复 Gorilla/DFSDT 工具索引问题

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
   - 运行: `python run_unified_eval.py --dataset sage --methods gorilla,dfsdt --samples 20`
   - 预期: 准确率应该 > 0%

## 验证命令

cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
python run_unified_eval.py --dataset sage --methods keyword,gorilla,dfsdt --samples 50 -v

## 成功标准

- Gorilla Top-5 准确率 > 60%
- DFSDT Top-5 准确率 > 60%
- 无 "No tools retrieved" 警告
```

---

## Task 2: 完善 LLM-based 方法测试

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

## 测试命令

# 测试 LLM-based selector (需要 LLM 服务)
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts

# 使用云端 API
python run_unified_eval.py --dataset sage --methods llm_direct --samples 10 -v

# 使用 embedded vLLM
python run_unified_eval.py --dataset sage --methods llm_direct --samples 10 --use-embedded --model Qwen/Qwen2.5-0.5B-Instruct -v

# 测试所有 LLM 方法
python run_all_experiments.py --quick --max-samples 10

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

## Task 3: 跨数据集验证完善

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
   - 运行: `python run_unified_eval.py --dataset acebench --methods keyword,embedding,hybrid --samples 100`
   - 确保结果格式与 SAGE 一致

2. **完善 ACEBench 数据加载**
   - 检查 `acebench_loader.py` 中的格式转换是否正确
   - 确保 candidate_tools 和 ground_truth 正确映射

3. **生成跨数据集对比表格**
   - 修改 `run_unified_eval.py`，支持 `--dataset all` 同时评测 SAGE 和 ACEBench
   - 生成 LaTeX 格式的对比表格

4. **(可选) 添加 API-Bank 支持**
   - 数据位置: `external_benchmarks/converted/raw/apibank/`
   - 创建 `apibank_loader.py` 加载数据

## 测试命令

cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts

# 测试 SAGE 数据集
python run_unified_eval.py --dataset sage --methods keyword,embedding,hybrid --samples 100 -v

# 测试 ACEBench 数据集
python run_unified_eval.py --dataset acebench --methods keyword,embedding,hybrid --samples 100 -v

# 跨数据集对比
python run_unified_eval.py --dataset all --methods keyword,embedding,hybrid --samples 100 -v

## 预期输出格式

================================================================================
Cross-Dataset Tool Selection Comparison
================================================================================
Method          | SAGE Top-5 | ACEBench Top-5 | Avg
----------------+------------+----------------+------
keyword         |    82.0%   |     78.0%      | 80.0%
embedding       |    82.0%   |     76.0%      | 79.0%
hybrid          |    84.0%   |     80.0%      | 82.0%
================================================================================

## 成功标准

- ACEBench 数据正确加载，无格式错误
- 所有方法在 ACEBench 上返回有效结果
- 生成跨数据集对比表格（Markdown 和 LaTeX）
```

---

## Task 4: 实验结果整理和论文图表生成

### 提示词

```
请帮我完善 SAGE benchmark 的实验结果整理和论文图表生成。

## 背景

SAGE-Bench 论文需要以下图表和表格：
1. **Table 1**: 三个 Challenge 的主要结果对比
2. **Table 2**: 跨数据集验证结果
3. **Figure 1**: Timing Detection 方法对比
4. **Figure 2**: Task Planning 方法对比
5. **Figure 3**: Tool Selection 方法对比
6. **Figure 4**: 工具数量 vs 准确率 (Scaling Analysis)
7. **Figure 5**: 错误类型分析

## 关键文件位置

- All Experiments: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py`
- 结果输出目录: `.sage/benchmark/results/`
- 图表输出: `.sage/benchmark/results/figures/`
- 表格输出: `.sage/benchmark/results/tables/`

## 当前生成的文件

运行 `python run_all_experiments.py --quick` 后生成：
- `figures/fig1_timing_comparison.pdf`
- `figures/fig2_planning_comparison.pdf`
- `figures/fig3_tool_selection_comparison.pdf`
- `figures/fig4_overall_comparison.pdf`
- `tables/table1_projected_performance.tex`
- `tables/table2_observed_benchmark.tex`

## 需要完成的工作

1. **完善图表样式**
   - 使用 ICML 2026 论文格式
   - 字体大小、颜色方案符合学术规范
   - 添加图例和轴标签

2. **生成 Scaling Analysis 图表**
   - X 轴: 候选工具数量 (10, 50, 100, 500, 1000)
   - Y 轴: Top-5 准确率
   - 对比: keyword, embedding, hybrid, gorilla, dfsdt

3. **生成 Error Analysis 图表**
   - 错误类型分布: 漏选、错选、排序错误
   - 按难度级别分析: easy, medium, hard

4. **生成 LaTeX 表格**
   - 使用 booktabs 样式
   - 包含置信区间或标准差
   - 最佳结果加粗

5. **整合所有结果到 JSON**
   - 结构化的实验结果汇总
   - 便于后续引用和更新

## 图表代码位置

`run_all_experiments.py` 中的 `generate_paper_materials()` 函数

## 运行命令

cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts

# 快速测试图表生成
python run_all_experiments.py --quick --max-samples 50

# 完整评测 + 图表生成 (需要 Task 1-3 完成)
python run_all_experiments.py --eval-only --max-samples 200

# 仅生成图表 (使用已有结果)
python run_all_experiments.py --paper-only --results-dir .sage/benchmark/results

## 预期输出

figures/
├── fig1_timing_comparison.pdf
├── fig2_planning_comparison.pdf
├── fig3_tool_selection_comparison.pdf
├── fig4_scaling_analysis.pdf
├── fig5_error_analysis.pdf
└── fig6_cross_dataset.pdf

tables/
├── table1_main_results.tex
├── table2_cross_dataset.tex
├── table3_ablation.tex
└── table4_challenge_details.tex

## 成功标准

- 所有图表使用统一的学术风格
- LaTeX 表格可直接复制到论文中
- 图表清晰、可读性好
- 包含所有 Paper 需要的数据可视化
```

---

## 📋 任务依赖和执行顺序

```
┌─────────────────────────────────────────────────────────────┐
│                    可并行执行的任务                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Task 1                Task 2               Task 3          │
│  (Gorilla/DFSDT)       (LLM-based)          (跨数据集)       │
│       │                    │                    │           │
│       └────────────────────┼────────────────────┘           │
│                            │                                │
│                            ▼                                │
│                       Task 4                                │
│                   (论文图表生成)                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**执行建议**:
- Task 1, 2, 3 可以分配给 3 个不同的 Copilot Agent 并行执行
- Task 4 需要等 Task 1-3 基本完成后执行
- 每个 Task 预计 2-3 小时

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
git commit -m "fix(benchmark): resolve Gorilla/DFSDT tool index mismatch issue"

# Task 2
git commit -m "feat(benchmark): complete LLM-based methods testing and validation"

# Task 3
git commit -m "feat(benchmark): enhance cross-dataset validation with ACEBench"

# Task 4
git commit -m "docs(benchmark): generate ICML paper figures and LaTeX tables"
```

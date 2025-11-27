# Agent Benchmark 剩余任务清单

> 创建时间: 2025-11-26
> 分支: feature/agent_tools_plan

## 📋 概述

三个挑战的基础框架已完成，但仍有一些问题需要解决才能达到论文所需的完整性。

## 🔴 高优先级问题

### 1. Tool Selection 评估未能正常运行

**问题**: `run_all_experiments.py` 中的 Tool Selection 评估返回 0% 准确率

**原因分析**:
- Selector 的 `select()` 方法调用可能与实际接口不匹配
- 数据格式可能与 selector 期望的格式不一致

**需要修复**:
```python
# 当前代码 (run_all_experiments.py ~line 408)
result = selector.select(query, candidate_tools, top_k=top_k)
```

**建议**:
1. 检查 `SelectorAdapter.select()` 的实际签名
2. 验证 `candidate_tools` 格式是否正确（应该是 tool 对象列表还是 ID 列表）
3. 添加调试日志查看实际返回值

### 2. 数据文件位置混乱

**问题**: 数据文件分布在多个位置

**当前状态**:
- **sageData submodule** (`packages/sage-benchmark/src/sage/data/sources/`):
  - `agent_benchmark/splits/` - 已有基础数据（600条 tool_selection, 300条 timing/planning）
  - `agent_tools/data/tool_catalog.jsonl` - 1200 个工具
  - `agent_sft/data/` - SFT 训练数据

- **运行时生成** (`.sage/benchmark/data/`):
  - `timing_judgment/` - 运行时生成的增强数据
  - `task_planning/` - 运行时生成的增强数据
  - `tool_selection/` - 运行时生成的增强数据

**建议**:
1. 明确区分「静态基准数据」和「运行时生成数据」
2. 静态数据应该只在 sageData submodule 中
3. 运行时生成数据应该在 `.sage/` 目录（已在 .gitignore）

### 3. Hybrid Timing Decider 仍在使用 LLM

**问题**: 即使使用 `--skip-llm`，Hybrid 策略仍然会加载 vLLM

**原因**: `timing.hybrid` 内部使用了 LLM 作为后备

**建议**:
- 在 `--skip-llm` 模式下，Hybrid 应该只使用 rule-based 部分
- 或者将 Hybrid 也加入跳过列表

---

## 🟡 中优先级问题

### 4. 基准线性能未达标

**当前性能** (基准线，未微调):

| Challenge | Best Strategy | Score | Target | Gap |
|-----------|---------------|-------|--------|-----|
| Timing Detection | Rule-based | 78.0% | 95% | -17% |
| Task Planning | Hierarchical | 26.7% | 90% | -63.3% |
| Tool Selection | - | 0% | 95% | -95% |

**分析**:
- Timing: Rule-based 的关键词匹配策略需要优化
- Planning: Simple/Hierarchical 是简单的模板匹配，需要 LLM 策略
- Tool Selection: 评估代码有 bug，需要修复后重测

### 5. LLM 策略加载缓慢

**问题**: 每次运行 Hybrid/LLM 策略都要重新加载 vLLM 模型（约30秒）

**建议**:
1. 实现模型缓存/预加载机制
2. 或者使用外部 API 服务模式（`IntelligentLLMClient.create_auto()`）

### 6. 论文材料完整性

**已完成**:
- ✅ fig1_timing_comparison.png
- ✅ fig2_planning_comparison.png
- ✅ fig3_tool_selection_comparison.png（但数据为空）
- ✅ fig4_overall_comparison.png
- ✅ fig5_planning_by_complexity.png
- ✅ table1_projected_performance.tex
- ✅ table2_observed_benchmark.tex
- ✅ planning_comparison.png, planning_by_complexity.png, tool_selection_results.png (别名)

**需要补充**:
- [ ] Tool Selection 图表需要真实数据
- [ ] 表格中 Tool Selection 部分为空

---

## 🟢 低优先级 / 增强项

### 7. 测试覆盖

- [ ] 为 `run_all_experiments.py` 添加单元测试
- [ ] 为各个评估逻辑添加集成测试
- [ ] 验证生成的 LaTeX 表格在论文中的渲染效果

### 8. 文档更新

- [ ] 更新 `docs/dev-notes/agent-benchmark-tasks.md`
- [ ] 添加使用示例到 README

### 9. 代码清理

- [ ] 移除 `run_all_experiments.py` 中的重复 SUMMARY 输出
- [ ] 统一日志格式
- [ ] 添加更详细的进度条

---

## 📁 相关文件

### 主要脚本
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py`
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/evaluations/prepare_*.py`

### 数据文件 (sageData submodule)
- `packages/sage-benchmark/src/sage/data/sources/agent_benchmark/splits/`
- `packages/sage-benchmark/src/sage/data/sources/agent_tools/data/tool_catalog.jsonl`

### 策略实现
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`

### 输出目录
- `.sage/benchmark/results/` - 评估结果
- `.sage/benchmark/data/` - 运行时生成数据

---

## ✅ 已完成的工作

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

---

## 🚀 下一步行动建议

1. **紧急**: 修复 Tool Selection 评估 bug
2. **重要**: 优化 Rule-based Timing Decider 达到更好的基准线
3. **可选**: 实现 LLM 服务缓存机制

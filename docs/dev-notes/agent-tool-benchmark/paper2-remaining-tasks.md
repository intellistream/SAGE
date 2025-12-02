# Paper 2 (SAGE-Agent Method) 剩余任务 - 完整指南

> 本文档定义了完成 SAGE-Agent 方法论文所需的所有任务
> 论文核心：Streaming Adaptive Learning for Tool-Augmented LLM Agents
>
> **生成日期**: 2025-11-27

---

## 🚀 统一入口 CLI

```bash
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts

# 方式 1: 交互式运行
python sage_benchmark_cli.py

# 方式 2: 直接指定实验 (跳过确认)
python sage_benchmark_cli.py --paper 2 --experiment streaming_comparison --yes
python sage_benchmark_cli.py --paper 2 --experiment full_training --yes

# 方式 3: 列出所有可用实验
python sage_benchmark_cli.py --list
```

**CLI 支持的 Paper 2 实验：**

| ID | 名称 | 描述 | 预估时间 |
|----|------|------|----------|
| `streaming_comparison` | 流式 vs 批量 | 对比 Streaming 和 Batch 训练 | ~2 hours |
| `full_training` | 完整训练对比 | 所有方法训练对比 | ~8 hours |
| `coreset_ablation` | Coreset 消融 | 样本选择策略消融 | ~1 hour |
| `continual_learning` | 持续学习 | 新工具增量学习 | ~2 hours |

---

## 📊 当前状态概览

| 组件 | 状态 | 说明 |
|------|------|------|
| SSIS (Sample Importance) | ⚠️ 需验证 | 已有框架，需端到端测试 |
| Coreset Selection | ⚠️ 需验证 | 有实现，未充分测试 |
| Streaming Training | ⚠️ 需验证 | 基础流程完成 |
| Continual Learning | ❌ 未完成 | EWC/ER 策略需实现 |
| RL Fine-tuning | ❌ 未完成 | PPO/DPO 集成需验证 |
| 论文图表 | ❌ 未开始 | 需要训练结果 |

---

## 🔧 Task 1: Streaming vs Batch 训练对比

### 目标
验证 Streaming Learning 相对 Batch Learning 的优势：
- 样本效率（Sample Efficiency）
- 计算效率（Compute Efficiency）
- 适应性（Adaptation Speed）

### 关键文件

```
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/
  run_full_training_comparison.py   # 训练对比脚本

packages/sage-libs/src/sage/libs/agentic/training/
  streaming_trainer.py              # 流式训练器
  batch_trainer.py                  # 批量训练器
```

### 实验配置

```python
# 对比实验设置
experiments = {
    "batch_full": {"method": "batch", "data_ratio": 1.0},
    "batch_50pct": {"method": "batch", "data_ratio": 0.5},
    "streaming_full": {"method": "streaming", "buffer_size": 1000},
    "streaming_coreset": {"method": "streaming", "coreset": True},
}
```

---

## 🔧 Task 2: Coreset Selection 消融实验

### 目标
验证不同样本选择策略的效果：
- Random Sampling
- Uncertainty Sampling
- Diversity Sampling
- SSIS (Our Method)

### 关键文件

```
packages/sage-libs/src/sage/libs/agentic/training/
  coreset/
    random_selector.py
    uncertainty_selector.py
    diversity_selector.py
    ssis_selector.py     # Streaming Sample Importance Scorer
```

---

## 🔧 Task 3: Continual Learning 实验

### 目标
验证模型在新工具持续增加时的性能：
- 避免灾难性遗忘
- 快速适应新工具
- 知识迁移

### 实验设计

```python
# Phase 1: 在 1000 工具上训练
train(tools[:1000])

# Phase 2: 增量学习 200 新工具
# 对比: Fine-tune vs EWC vs Experience Replay vs SAGE-Agent
continual_learn(tools[1000:1200])

# 评估: 旧工具性能 + 新工具性能
evaluate(tools[:1200])
```

---

## 🔧 Task 4: RL Fine-tuning 验证

### 目标
验证基于执行反馈的强化学习微调效果：
- PPO (Proximal Policy Optimization)
- DPO (Direct Preference Optimization)

### 关键文件

```
packages/sage-libs/src/sage/libs/agentic/training/
  rl/
    ppo_trainer.py
    dpo_trainer.py
    reward_model.py
```

---

## 🔧 Task 5: 论文图表生成

### 需要的图表

1. **Figure 1**: SAGE-Agent 架构图
2. **Figure 2**: Streaming vs Batch 学习曲线
3. **Figure 3**: Coreset Selection 消融
4. **Figure 4**: Continual Learning 遗忘曲线
5. **Figure 5**: RL Fine-tuning 效果

### 需要的表格

1. **Table 1**: 与 SOTA 方法对比（Gorilla, ToolLLM, etc.）
2. **Table 2**: 三个 Challenge 上的结果
3. **Table 3**: 消融实验结果
4. **Table 4**: 跨数据集泛化结果

---

## 🔧 Task 6: 完整训练流程

### 训练脚本

```bash
# 完整训练对比 (需要 GPU)
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
python run_full_training_comparison.py --config config/full_training.yaml
```

### LLM 推理方式选择

**推荐**: 使用 `UnifiedInferenceClient` + 本地 vLLM Server

原因：
1. **资源共享**: 多个训练进程可以共享一个 LLM 服务
2. **显存管理**: vLLM 的 PagedAttention 优化显存
3. **吞吐量**: 批量请求可以合并处理
4. **可观测性**: 服务端有统一的监控和日志

```python
# 推荐用法
from sage.common.components.sage_llm import UnifiedInferenceClient

client = UnifiedInferenceClient.create_auto()
# 自动检测: 本地 vLLM → 云端 API
```

---

## 📝 执行顺序建议

1. ✅ Task 1: Streaming vs Batch (获得核心实验数据)
2. Task 2: Coreset Ablation (验证样本选择)
3. Task 3: Continual Learning (验证适应性)
4. Task 4: RL Fine-tuning (验证强化学习)
5. Task 5: 图表生成 (论文写作)
6. Task 6: 完整训练 (最终验证)

---

## 🔗 相关文档

- [Paper 1 任务](./paper1-remaining-tasks.md) - SAGE-Bench Benchmark 论文
- [ICML 方法论文提示词](./icml-method-paper-prompt.md) - 论文生成提示词
- [架构说明](./task3-decomposition-plan.md) - 系统架构设计

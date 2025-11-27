# SAGE-Bench 剩余开发任务

> 生成日期: 2025-11-27
> 目标: 完成两篇 ICML 论文所需的实验和代码

---

## 论文 1: SAGE-Bench (Benchmark 论文)

### 当前状态

| Challenge | Best Method | Current | Target | Gap |
|-----------|-------------|---------|--------|-----|
| Timing | Rule-based | 76% | 95% | -19% |
| Planning | Hierarchical | 27% | 90% | -63% |
| Tool Selection | BM25 | 82% | 95% | -13% |

### 需要修复的问题

#### 1. Timing Decider 接口不兼容

**问题**: `timing.rule_based`, `timing.llm_based`, `timing.hybrid` 期望的是带 `.message` 属性的对象，但 benchmark 传入的是 dict

**影响文件**:
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
- `packages/sage-libs/src/sage/libs/agentic/agents/planning/timing_decider.py`

**修复方案**:
```python
# 在 TimingAdapter.decide() 中添加输入转换
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

#### 2. Gorilla/DFSDT Selector 返回空结果

**问题**: `selector.gorilla` 和 `selector.dfsdt` 需要预加载 tool corpus，直接传入 candidate_tools 不生效

**影响文件**:
- `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/adapter_registry.py`
- `packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/gorilla_selector.py`
- `packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/dfsdt_selector.py`

**修复方案**:
```python
# 在 SelectorAdapter.select() 中，如果 selector 返回空且有 candidate_tools
# 则 fallback 到 keyword/embedding 预处理
def select(self, query, candidate_tools=None, top_k=5):
    result = self.selector.select(query, top_k=top_k)
    if not result and candidate_tools:
        # Fallback: 使用 candidate_tools 作为检索范围
        ...
```

### 需要补充的实验

#### 3. 完整的 Cross-benchmark 验证

**当前**: 只有 ACEBench 部分结果
**需要**: 在所有外部数据集上运行所有方法

```bash
# 运行脚本
cd packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts

# ACEBench 完整评估
python run_unified_eval.py --dataset acebench --methods keyword,embedding,hybrid,llm_direct,gorilla,dfsdt --samples 500

# API-Bank 评估 (需要先转换数据)
python run_unified_eval.py --dataset apibank --methods keyword,embedding,hybrid --samples 500

# SAGE 内部数据集完整评估
python run_unified_eval.py --dataset sage --methods all --samples 500
```

#### 4. 更多 baseline 方法的实验数据

**需要补充**:
- Two-Stage selector 实验结果
- Adaptive selector 实验结果
- 不同 LLM 模型 (Qwen-7B, Qwen-14B, GPT-4) 对比

#### 5. Scaling 分析

**需要**: 工具数量 vs 准确率曲线
- 100 tools
- 500 tools
- 1000 tools
- 1200 tools (full)

```python
# 生成不同规模的实验
for num_tools in [100, 500, 1000, 1200]:
    python run_unified_eval.py --dataset sage --num-candidate-tools {num_tools} --samples 200
```

#### 6. 消融实验

**Hybrid selector 消融**:
- keyword_weight = 0.0 (纯 embedding)
- keyword_weight = 0.5 (平衡)
- keyword_weight = 1.0 (纯 keyword)

**Timing hybrid 消融**:
- rule_only
- llm_only
- hybrid (rule + llm)

---

## 论文 2: SAGE-Agent (方法论文)

### 核心创新点

1. **Coreset Selection**: 基于 loss/diversity 的样本筛选
2. **Continual Learning**: 在线增量学习 + 经验回放
3. **联合训练**: 三任务 (Timing/Planning/Selection) 统一优化

### 需要完成的实现

#### 7. RL 训练流程

**当前状态**: 配置已定义，训练流程未完成

**需要实现**:
- `packages/sage-libs/src/sage/libs/finetune/agent/rl_trainer.py` (新文件)
- DPO 训练循环
- PPO 训练循环 (可选)
- GRPO 训练循环 (可选)

```python
# DPO 训练配置示例
config = RLTrainingConfig(
    algorithm="dpo",
    sft_model_path="./output/agent_sft",
    dpo_config={"beta": 0.1, "loss_type": "sigmoid"}
)
trainer = AgentRLTrainer(config)
trainer.train()
```

#### 8. 训练实验脚本

**需要创建**:
```bash
# 完整训练对比脚本
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_training_ablation.py

# 实验配置:
# 1. Baseline: 无训练 (直接推理)
# 2. SFT only: 标准监督微调
# 3. SFT + Coreset: 加入样本筛选
# 4. SFT + Continual: 加入增量学习
# 5. SFT + Coreset + Continual: 完整方法
# 6. + DPO: 加入强化学习
```

#### 9. Coreset Selection 消融

**需要实验**:
- `loss_topk` vs `diversity` vs `hybrid` vs `random`
- 不同 coreset size: 25%, 50%, 75%, 100%

#### 10. Continual Learning 消融

**需要实验**:
- buffer_size: 512, 1024, 2048, 4096
- replay_ratio: 0.1, 0.25, 0.5

---

## 优先级排序

### P0 - 必须完成 (论文 1 基础)

1. [ ] 修复 Timing Decider 接口不兼容
2. [ ] 修复 Gorilla/DFSDT 空结果问题
3. [ ] 完成 SAGE 数据集完整实验 (所有方法)
4. [ ] 完成 ACEBench 完整实验

### P1 - 重要 (论文 1 完善)

5. [ ] API-Bank 数据集评估
6. [ ] Scaling 分析实验
7. [ ] Hybrid 消融实验
8. [ ] 不同 LLM 模型对比

### P2 - 论文 2 核心

9. [ ] DPO 训练流程实现
10. [ ] 训练消融实验脚本
11. [ ] Coreset Selection 完整实验
12. [ ] Continual Learning 完整实验

### P3 - 可选增强

13. [ ] PPO/GRPO 训练实现
14. [ ] 更多外部数据集集成
15. [ ] 可视化图表生成

---

## 快速开始命令

```bash
# 1. 修复接口问题后，运行完整实验
cd /home/shuhao/SAGE

# 2. Tool Selection 完整评估
python packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_unified_eval.py \
    --dataset sage --methods keyword,embedding,hybrid,llm_direct --samples 200

# 3. 三挑战完整实验
python packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/run_all_experiments.py \
    --samples 100

# 4. 查看结果
cat .sage/benchmark/results/all_results.json | python -m json.tool
```

---

## 文件位置参考

```
关键文件:
├── adapter_registry.py          # 需要修复接口
├── run_unified_eval.py          # Tool Selection 评估
├── run_all_experiments.py       # 三挑战完整实验
├── continual.py                 # Coreset + Continual 实现
├── trainer.py                   # SFT 训练
└── config.py                    # DPO/PPO/GRPO 配置 (训练未实现)
```

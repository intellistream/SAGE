# ICLR 2026 论文生成提示词

请使用以下提示词让大模型生成 ICLR 格式的研究论文。

---

## 提示词

```
你是一位顶级的 AI 系统研究者，擅长写作高质量的学术论文。请帮我撰写一篇投稿 ICLR 2026 的研究论文，要求：

### 研究主题
**SAGE-Agent: Efficient Tool Learning for LLM Agents via Hierarchical Planning and Adaptive Sample Selection**

### 核心贡献（请围绕以下三个技术贡献展开）

#### 贡献 1: 分层规划与时机判断引擎 (Hierarchical Planning & Timing Engine)
- **HierarchicalPlanner**: 多步任务分解，支持依赖图管理和拓扑排序
- **TimingDecider**: 规则基、LLM基、混合三种时机判断策略
- **DependencyGraph**: DAG依赖验证，检测循环依赖，支持并行执行优化
- 技术细节：
  - 输入：用户目标 + 工具库 + 约束条件
  - 输出：带依赖关系的执行计划 (PlanStep[])
  - 支持计划修复 (repair_json, extract_and_repair_plan)
  - 验证器：validate_step_dependencies, check_plan_constraints

#### 贡献 2: 高效工具选择 (Efficient Tool Selection)
- **KeywordSelector**: 基于 BM25 的关键词匹配选择器
- **EmbeddingSelector**: 基于向量相似度的语义选择器
- **Two-Stage Selector**: 粗筛（关键词） + 精排（embedding）的两阶段策略
- 技术细节：
  - 支持 1200+ 工具的大规模工具库
  - Top-K 准确率、MRR、Recall@K 等评估指标
  - 可插拔的选择器注册机制 (SelectorRegistry)

#### 贡献 3: 自适应样本选择与持续学习的 Agent 微调 (Adaptive Agent Fine-tuning)
- **CoresetSelector**: 三种核心集选择策略
  - loss_topk: 基于损失值的困难样本挖掘
  - diversity: 基于特征距离的多样性采样
  - hybrid: 60%困难样本 + 40%多样性样本
- **OnlineContinualLearner**: 经验回放缓冲区 + 在线增量学习
- **AgentSFTTrainer**: LoRA微调 + 梯度检查点 + bf16训练
- 技术细节：
  - 支持 4 类任务：tool_selection, multi_step_planning, timing_decision, tool_retrieval
  - 数据格式：Agent对话格式（多轮工具调用）
  - 训练目标：95%+ 工具选择准确率

### 实验设置

#### 数据集
- **AgentBench**: 1200 个工具，覆盖 12 个类别（environment, finance, communication 等）
- **训练集**: 4000 条 agent 对话（含工具调用轨迹）
- **测试集**: 按任务类型划分（tool_selection: 75, task_planning: 50, timing_judgment: 30）

#### 基线方法对比
- **Method A (Baseline SFT)**: 标准监督微调，无样本选择
- **Method B1 (Coreset-Loss)**: 基于损失的 Top-K 样本选择
- **Method B2 (Coreset-Diversity)**: 基于多样性的样本选择
- **Method B3 (Coreset-Hybrid)**: 混合策略
- **Method C (Continual Learning)**: 经验回放的持续学习
- **Method D (Combined)**: Coreset + Continual Learning

#### 评估指标
- **工具选择**: Top-K Accuracy, MRR, Recall@K, Precision@K
- **规划质量**: Step Validity, Dependency Correctness, Plan Executability
- **时机判断**: Decision Accuracy, False Positive Rate
- **效率**: Training Time, Sample Efficiency, GPU Memory

### 论文结构要求

1. **Abstract** (150词): 强调三个贡献和主要实验结果
2. **Introduction** (1.5页):
   - 问题动机：LLM Agent 工具调用的挑战
   - 现有方法不足：数据效率低、缺乏分层规划
   - 我们的方法概述
3. **Related Work** (1页):
   - Tool-augmented LLMs (Toolformer, ToolLLM, API-Bank)
   - Agent Planning (ReAct, Chain-of-Thought, Tree-of-Thoughts)
   - Continual Learning for LLMs
   - Coreset Selection
4. **Method** (3页):
   - 3.1 Problem Formulation
   - 3.2 Hierarchical Planning Engine
   - 3.3 Tool Selection Module
   - 3.4 Adaptive Fine-tuning with Coreset Selection
   - 3.5 Training Pipeline
5. **Experiments** (2.5页):
   - 5.1 Experimental Setup
   - 5.2 Main Results (Table 1: 方法对比)
   - 5.3 Ablation Study (各组件贡献)
   - 5.4 Analysis (样本效率、规划质量可视化)
6. **Conclusion** (0.5页)

### 写作风格
- 使用 ICLR 2026 LaTeX 模板
- 正式学术英语，避免口语化表达
- 每个 claim 都有实验支持
- 图表清晰专业（建议 2-3 个 Figure，2-3 个 Table）

### 关键术语定义
- **Coreset**: 能代表完整数据集特征的核心子集
- **Experience Replay**: 从历史数据中采样以防止灾难性遗忘
- **LoRA (Low-Rank Adaptation)**: 低秩参数高效微调
- **Hierarchical Planning**: 将复杂任务分解为可执行子步骤的规划方法

### 请生成完整的论文 LaTeX 代码

包括：
1. 完整的论文正文
2. 参考文献（至少 30 篇相关工作）
3. 附录（算法伪代码、额外实验结果）

论文长度：正文 8 页 + 参考文献 + 附录（不限）
```

---

## 使用说明

1. 将上述提示词复制给支持长文本生成的大模型（如 Claude、GPT-4）
2. 可以分步生成：先生成大纲，再逐节生成
3. 生成后需要：
   - 补充真实实验数据（运行 `run_full_training_comparison.py` 获取）
   - 调整参考文献为真实论文
   - 添加实际的图表

## 补充材料

### 实验数据获取命令

```bash
# 运行完整的方法对比实验
cd packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
export HF_ENDPOINT=https://hf-mirror.com

# 快速测试（500样本，1轮）
python run_full_training_comparison.py --quick --output ./results

# 完整实验（全量数据，3轮）
python run_full_training_comparison.py --full --output ./results

# 单个方法测试
python run_full_training_comparison.py --method D_combined --output ./results
```

### 核心代码位置

| 组件 | 位置 |
|------|------|
| HierarchicalPlanner | `packages/sage-libs/src/sage/libs/agentic/agents/planning/hierarchical_planner.py` |
| TimingDecider | `packages/sage-libs/src/sage/libs/agentic/agents/planning/timing_decider.py` |
| ToolSelector | `packages/sage-libs/src/sage/libs/agentic/agents/action/tool_selection/` |
| CoresetSelector | `packages/sage-libs/src/sage/libs/finetune/agent/continual.py` |
| AgentSFTTrainer | `packages/sage-libs/src/sage/libs/finetune/agent/trainer.py` |
| Benchmark | `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/` |
| 数据集 | `packages/sage-benchmark/src/sage/data/sources/agent_benchmark/` |

### 推荐的论文标题备选

1. **SAGE-Agent: Hierarchical Planning and Adaptive Sample Selection for Efficient Tool Learning**
2. **Learning to Use Tools: A Unified Framework for Hierarchical Planning, Selection, and Fine-tuning**
3. **Efficient Agent Fine-tuning via Coreset Selection and Continual Learning**
4. **Beyond Simple Tool Calling: Hierarchical Planning with Adaptive Training for LLM Agents**

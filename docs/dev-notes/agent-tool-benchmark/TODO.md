# Feature Branch: agent_tools_plan - 待办事项清单

**分支**: `feature/agent_tools_plan`  
**更新日期**: 2025-11-26  
**状态**: 进行中

---

## ✅ 已完成工作

### 1. 核心功能实现
- [x] **HierarchicalPlanner**: 分层规划引擎，支持依赖图管理
- [x] **TimingDecider**: 规则/LLM/混合三种时机判断策略
- [x] **ToolSelector**: KeywordSelector + EmbeddingSelector + Registry
- [x] **AgentSFTTrainer**: LoRA 微调训练器
- [x] **CoresetSelector**: loss_topk/diversity/hybrid 三种策略
- [x] **OnlineContinualLearner**: 经验回放持续学习

### 2. 数据集构建
- [x] **agent_tools**: 1200 个工具库
- [x] **agent_benchmark**: 工具选择/任务规划/时机判断测试集
- [x] **agent_sft**: 4000 条训练对话数据

### 3. Benchmark 框架
- [x] 方法对比实验脚本 (`run_full_training_comparison.py`)
- [x] 评估指标计算 (Top-K Accuracy, MRR, Recall@K)
- [x] 结果可视化图表生成

### 4. 基础设施修复
- [x] **PyTorch CUDA 自动安装**: `pytorch_cuda_installer.sh`
- [x] **HuggingFace 镜像自动检测**: trainer.py 中 `_setup_hf_mirror()`
- [x] **依赖版本统一**: transformers/tokenizers 版本冲突解决
- [x] **核心依赖整合**: finetune 依赖从可选变为必选

### 5. 文件重组织
- [x] `sage-tools/agent_training/` → `sage-libs/finetune/agent/`
- [x] 实验脚本移至 `sage-benchmark/benchmark_agent/scripts/`
- [x] 向后兼容垫片 (deprecation warning)

---

## 🔄 进行中

### 1. 训练实验
- [ ] 运行完整的 6 种方法对比实验 (A, B1-B3, C, D)
- [ ] 使用 7B 模型进行完整训练（当前只测试了 0.5B）
- [ ] 收集并记录实验数据

### 2. Bug 修复
- [x] `evaluation_strategy` → `eval_strategy` (transformers 4.46+)
- [x] `torch_dtype` → `dtype` 弃用警告
- [x] `DataManager.load()` → `get_by_source().iter_split()` API 修复
- [ ] 梯度计算问题（已尝试修复，需验证）

---

## 📋 待完成工作

### 优先级 P0 - 必须在合并前完成

#### 1. 代码质量
- [ ] 运行 `sage-dev quality` 修复代码风格问题
- [ ] 运行 `sage-dev project test --coverage` 确保测试通过
- [ ] 更新 CHANGELOG.md

#### 2. 提交当前更改
```bash
# 当前未提交的文件需要整理提交
git add -A
git commit -m "feat(agent-training): fix dependencies and evaluation bugs"
```

#### 3. 验证训练流程
```bash
# 快速验证
cd packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
python run_full_training_comparison.py --method A_baseline --quick --output ./results

# 确保无错误完成训练和评估
```

### 优先级 P1 - 重要但可延后

#### 4. 完整实验
- [ ] 在 A100 上运行 6 种方法的完整对比
- [ ] 收集训练时间、显存占用、样本效率数据
- [ ] 生成最终的对比图表

#### 5. 文档完善
- [ ] 更新 README.md 中的 agent training 使用说明
- [ ] 补充 API 文档
- [x] 生成 ICLR 论文提示词 (`iclr_paper_prompt.md`)

#### 6. 单元测试
- [ ] 为 `sage-libs/finetune/agent/` 添加单元测试
- [ ] 测试 CoresetSelector 各策略
- [ ] 测试 OnlineContinualLearner

### 优先级 P2 - 后续迭代

#### 7. 性能优化
- [ ] DeepSpeed 分布式训练支持
- [ ] 更大模型 (14B/32B) 的训练配置
- [ ] 混合精度训练优化

#### 8. 功能增强
- [ ] 添加更多 Coreset 选择策略
- [ ] 支持 DPO/GRPO 强化学习训练
- [ ] 添加 RewardModel 训练流程

---

## 📁 需要提交的文件清单

### 新增文件
```
docs/dev-notes/agent-tool-benchmark/
├── file-reorganization-plan.md
├── how-to-add-sota-methods.md
├── iclr_paper_prompt.md
└── TODO.md (本文件)

packages/sage-libs/src/sage/libs/finetune/agent/
├── __init__.py
├── config.py
├── trainer.py
├── continual.py
├── dialog_processor.py
├── data_formatter.py
├── evaluator.py
└── reward_model.py

packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/
├── run_full_training_comparison.py
└── results/ (gitignore)

tools/install/fixes/
└── pytorch_cuda_installer.sh
```

### 修改文件
```
packages/sage-libs/pyproject.toml          # 依赖更新
packages/sage-apps/pyproject.toml          # transformers 版本
packages/sage-middleware/pyproject.toml    # transformers 版本
packages/sage-benchmark/pyproject.toml     # agent-training 依赖
quickstart.sh                              # PyTorch CUDA 安装
tools/install/installation_table/core_installer.sh  # Step 0/5
```

### 删除/移动文件
```
# 移动到 sage-libs
packages/sage-tools/src/sage/tools/agent_training/* → packages/sage-libs/src/sage/libs/finetune/agent/

# 移动到正确位置
examples/tutorials/agent_sft_demo.py → examples/tutorials/L3-libs/
examples/tutorials/embedding_server_example.py → examples/tutorials/L1-common/
```

---

## 🚀 合并前检查清单

- [ ] `sage-dev quality --check-only` 通过
- [ ] `sage-dev project test --quick` 通过
- [ ] 至少一个训练方法完整运行成功
- [ ] 所有 pyproject.toml 版本冲突解决
- [ ] CHANGELOG.md 已更新
- [ ] PR 描述清晰，包含测试结果截图

---

## 📝 备注

### 运行训练的命令
```bash
cd /home/shuhao/SAGE/packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
export HF_ENDPOINT=https://hf-mirror.com

# 快速测试 (0.5B 模型)
python run_full_training_comparison.py --method A_baseline --quick --model Qwen/Qwen2.5-0.5B-Instruct

# 完整实验 (7B 模型)
python run_full_training_comparison.py --full --model Qwen/Qwen2.5-7B-Instruct
```

### 已知问题
1. HuggingFace 模型下载可能较慢，已添加镜像自动检测
2. 0.5B 模型的评估结果仅供验证流程，实际论文需要 7B 模型数据
3. **`torch_dtype` 弃用警告**: transformers 新版本建议使用 `dtype` 替代 `torch_dtype`，需要在 `trainer.py` 中修复
4. **模型评估返回 0% 准确率**: 当前 `_evaluate_with_model()` 评估逻辑可能有问题，模型推理的工具评分逻辑需要调试
   - 症状：训练完成后评估显示 `Top-K Acc: 0.00%, MRR: 0.00%`
   - 可能原因：prompt 格式不匹配、评分解析失败、候选工具集不正确
5. **Generation flags 警告**: `['temperature', 'top_p', 'top_k']` 被忽略，需要检查 generate 参数

---

## 🔬 待集成的 SOTA 方法

当前实现的方法（A-D）主要是基础方法，以下是论文中应该对比的真正 SOTA 方法：

### 工具选择 SOTA
| 方法 | 论文 | 状态 | 备注 |
|------|------|------|------|
| ToolLLM | Qin et al., 2023 | ❌ 未集成 | 需要实现 DFSDT 搜索算法 |
| ToolBench | Xu et al., 2023 | ❌ 未集成 | 需要适配其评估协议 |
| API-Bank | Li et al., 2023 | ❌ 未集成 | API 调用评估基准 |
| Gorilla | Patil et al., 2023 | ❌ 未集成 | API 文档检索增强 |
| TaskMatrix | Liang et al., 2023 | ❌ 未集成 | 多模态工具调用 |

### 规划 SOTA
| 方法 | 论文 | 状态 | 备注 |
|------|------|------|------|
| ReAct | Yao et al., 2023 | ⚠️ 部分实现 | 需要完善 reasoning trace |
| Tree-of-Thoughts | Yao et al., 2023 | ❌ 未集成 | 树搜索规划 |
| Graph-of-Thoughts | Besta et al., 2023 | ❌ 未集成 | 图结构规划 |
| DEPS | Wang et al., 2023 | ❌ 未集成 | 依赖感知规划 |

### 微调 SOTA  
| 方法 | 论文 | 状态 | 备注 |
|------|------|------|------|
| FireAct | Chen et al., 2023 | ❌ 未集成 | Agent 轨迹微调 |
| AgentTuning | Zeng et al., 2023 | ❌ 未集成 | 通用 Agent 能力微调 |
| ToolAlpaca | Tang et al., 2023 | ❌ 未集成 | 工具使用微调数据 |

### 集成计划
详见 `how-to-add-sota-methods.md` 中的添加指南。优先级：
1. **P0**: ToolLLM (工具选择核心对比)
2. **P1**: ReAct 完善、FireAct (规划+微调)
3. **P2**: 其他方法按需添加

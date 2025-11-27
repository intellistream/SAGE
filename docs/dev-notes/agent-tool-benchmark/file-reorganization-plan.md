# Agent Tool Benchmark - 文件重组计划

## ✅ 重组已完成 (2025-11-26)

## 问题分析

当前 `feature/agent_tools_plan` 分支相对于 `main-dev` 有 **114 个文件改动**，部分文件位置不符合 SAGE 架构规范。

### SAGE 架构回顾 (L1-L6)

```
L6: sage-cli, sage-studio, sage-tools, sage-gateway  # 接口、开发工具、API网关
L5: sage-apps, sage-benchmark                        # 应用 & 基准测试
L4: sage-middleware                                  # 算子 (C++ 扩展)
L3: sage-kernel, sage-libs                           # 核心 & 算法库
L2: sage-platform                                    # 平台服务
L1: sage-common                                      # 基础组件
```

**关键原则**:
- L3 `sage-libs` = 核心算法库（微调、选择器、规划器等可复用算法）
- L5 `sage-benchmark` = 基准测试和实验框架
- L6 `sage-tools` = 开发者工具（代码生成、脚手架、但**不是**运行时算法）

---

## 文件位置问题列表

### ❌ 问题1: `agent_training` 放错位置

**当前位置**: `packages/sage-tools/src/sage/tools/agent_training/`
**正确位置**: `packages/sage-libs/src/sage/libs/finetune/agent/`

| 文件 | 说明 | 应属于 |
|-----|------|-------|
| `sft_trainer.py` | Agent SFT 训练器 | sage-libs (finetune) |
| `continual.py` | CoresetSelector, OnlineContinualLearner | sage-libs (finetune) |
| `config.py` | AgentSFTConfig | sage-libs (finetune) |
| `dialog_processor.py` | 对话处理 | sage-libs (finetune) |
| `data_formatter.py` | 数据格式化 | sage-libs (finetune) |
| `evaluator.py` | 训练评估 | sage-libs (finetune) |
| `reward_model.py` | 奖励模型 | sage-libs (finetune) |

**理由**: 这些是核心算法组件，不是开发工具。`sage-tools` 应该只包含 CLI、代码生成等开发辅助工具。

---

### ❌ 问题2: 实验脚本放错位置

**当前位置**: `examples/tutorials/L5-apps/`
**正确位置**: `packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/`

| 文件 | 说明 | 应属于 |
|-----|------|-------|
| `run_method_comparison.py` | 方法对比实验入口 | sage-benchmark (scripts) |
| `agent_sft_training_example.py` | SFT 训练示例 | sage-benchmark (scripts) |
| `run_full_training_comparison.py` | 完整训练对比 | sage-benchmark (scripts) |

**理由**:
- `examples/tutorials/` 应该是**教程和入门示例**
- 正式实验脚本应该在 `sage-benchmark` 包内，可以通过 CLI 调用

---

### ❌ 问题3: 部分示例放错层级

**当前位置**: `examples/tutorials/` (根目录)
**正确位置**: `examples/tutorials/L3-libs/` 或 `L1-common/`

| 文件 | 说明 | 应属于层级 |
|-----|------|----------|
| `embedding_server_example.py` | Embedding 服务示例 | L1-common |
| `agent_sft_demo.py` | SFT 演示 | L3-libs (finetune) |

---

## 重构方案

### Phase 1: 移动 agent_training 到 sage-libs

```bash
# 源目录
packages/sage-tools/src/sage/tools/agent_training/

# 目标目录 (整合到现有 finetune 模块)
packages/sage-libs/src/sage/libs/finetune/agent/
```

新结构:
```
sage-libs/src/sage/libs/finetune/
├── __init__.py           # 现有
├── config.py             # 现有 LoRA 配置
├── service.py            # 现有微调服务
├── trainer.py            # 现有 LoRATrainer
└── agent/                # 新增: Agent 专用微调
    ├── __init__.py
    ├── config.py         # AgentSFTConfig
    ├── trainer.py        # AgentSFTTrainer
    ├── continual.py      # CoresetSelector, OnlineContinualLearner
    ├── dialog_processor.py
    ├── data_formatter.py
    ├── evaluator.py
    └── reward_model.py
```

### Phase 2: 移动实验脚本到 sage-benchmark

```bash
# 源目录
examples/tutorials/L5-apps/run_method_comparison.py
examples/tutorials/L5-apps/agent_sft_training_example.py
examples/tutorials/L5-apps/run_full_training_comparison.py

# 目标目录
packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts/
```

新结构:
```
sage-benchmark/src/sage/benchmark/benchmark_agent/
├── __init__.py
├── __main__.py           # CLI 入口
├── experiments/          # 实验框架
│   ├── method_comparison.py
│   └── ...
└── scripts/              # 新增: 可执行脚本
    ├── __init__.py
    ├── run_method_comparison.py
    ├── run_full_training.py
    └── run_single_experiment.py
```

### Phase 3: 整理示例文件

```bash
# 移动到正确层级
examples/tutorials/embedding_server_example.py → examples/tutorials/L1-common/
examples/tutorials/agent_sft_demo.py → examples/tutorials/L3-libs/
```

---

## 影响范围

### 需要更新的导入

1. `from sage.tools.agent_training import ...` → `from sage.libs.finetune.agent import ...`
2. Benchmark 中的 adapter_registry 引用
3. 测试文件路径

### 需要保留兼容性的位置

可以在 `sage-tools` 保留 re-export 以保持向后兼容:
```python
# packages/sage-tools/src/sage/tools/agent_training/__init__.py
from sage.libs.finetune.agent import *  # Re-export for backward compatibility
```

---

## 执行顺序

1. ✅ 创建此文档
2. ✅ 在 sage-libs/finetune/ 创建 agent/ 子目录
3. ✅ 移动 agent_training 代码
4. ✅ 更新所有导入
5. ✅ 在 sage-benchmark 创建 scripts/ 目录
6. ✅ 移动实验脚本
7. ✅ 整理 examples/tutorials/
8. ✅ 运行测试验证
9. ⬜ 提交并推送

---

## 可选: 同时考虑的改进

1. **统一 selector 接口**: `sage-libs/agentic/agents/action/tool_selection/` 与 benchmark adapter 整合
2. **实验 CLI 增强**: `sage-dev benchmark agent run --method D_combined --quick`
3. **配置文件标准化**: 统一使用 YAML 配置实验参数

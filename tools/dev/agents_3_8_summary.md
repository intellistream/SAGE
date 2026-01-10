# Agents 3-8: 提示词汇总

本文件包含剩余 6 个 Agent 的简化任务说明。

## Agent-3: Fine-tuning Refactoring

**目标**：创建 finetune 接口层，实现迁移到 isage-finetune

**核心接口**：

- `BaseTrainer`: 训练器基类
- `BaseStrategy`: 训练策略（LoRA, QLoRA, Full FT）
- `BaseCallback`: 训练回调
- Factory: register_trainer, create_trainer

**独立库内容**：

- LoRA/QLoRA 实现
- PEFT (Parameter-Efficient Fine-Tuning)
- 分布式训练支持
- 检查点管理

______________________________________________________________________

## Agent-4: Evaluation Refactoring

**目标**：创建 eval 接口层（新建），实现到 isage-eval

**核心接口**：

- `BaseMetric`: 评估指标基类（Accuracy, F1, BLEU, ROUGE）
- `BaseProfiler`: 性能剖析器
- `BaseBenchmark`: Benchmark 基类
- Factory: register_metric, create_metric

**独立库内容**：

- 常用 NLP/CV 指标
- LLM-as-Judge 评估
- 性能分析工具
- A/B 测试框架

______________________________________________________________________

## Agent-5: Privacy Refactoring

**目标**：创建 privacy 接口层，迁移 unlearning 实现到 isage-privacy

**当前状态**：

- sage-libs/privacy/unlearning/ 已有实现（Laplace, Gaussian）

**核心接口**：

- `BaseUnlearner`: 机器遗忘基类
- `BasePrivacyMechanism`: 隐私机制
- `BaseDPOptimizer`: 差分隐私优化器
- Factory: register_unlearner, create_unlearner

**独立库内容**：

- 机器遗忘算法（SISA, Amnesiac）
- 差分隐私（Laplace, Gaussian, CDP, RDP）
- 联邦学习
- 同态加密（可选）

______________________________________________________________________

## Agent-6: Safety Refactoring (可选, P3)

**目标**：保持 sage-libs/safety/ 基础实现，可选创建高级接口

**当前状态**：

- sage-libs/safety/ 已有：content_filter, pii_scrubber, policy_check

**策略**：

- **保留** 基础实现在 sage-libs（无依赖）
- **可选** 创建 safety/interface/ 用于高级功能
- **可选** 创建 isage-safety 独立库（Jailbreak 检测，对抗样本）

**核心接口**（如果创建）：

- `BaseGuardrail`: 安全护栏
- `BaseJailbreakDetector`: 越狱检测
- `BaseAdversarialDefense`: 对抗防御

______________________________________________________________________

## Agent-7: Documentation Refactoring

**目标**：重构 sage-libs 文档，清理过时内容，突出 5 大领域

**任务**：

1. **更新 README.md**

   - 5 大接口领域架构图
   - 安装指南（extras: agentic, rag, all）
   - 快速开始示例

1. **精简 docs/**

   - 保留：架构概览、接口说明、集成指南
   - 删除：具体实现细节（移到独立库）
   - 新增：跨库集成教程

1. **独立库文档**

   - 每个库的 README 模板
   - API 参考
   - 使用示例

1. **生成架构图**

   - 使用 Mermaid 绘制依赖关系
   - 5 大领域组件图

______________________________________________________________________

## Agent-8: Integration Validation & Publishing

**目标**：集成测试、版本对齐、PyPI 发布

**任务**：

### 1. 集成测试

```python
# tests/integration/test_all_libs.py
def test_agentic_integration():
    import isage_agentic
    from sage.libs.agentic.interface import list_agents
    assert "react" in list_agents()

def test_rag_integration():
    import isage_rag
    from sage.libs.rag.interface import list_loaders
    assert "pdf" in list_loaders()

def test_cross_lib_integration():
    """Test RAG + Agentic integration."""
    from sage.libs.rag.interface import create_loader, create_retriever
    from sage.libs.agentic.interface import create_agent

    loader = create_loader("pdf")
    retriever = create_retriever("dense")
    agent = create_agent("react")
    # Test full pipeline
```

### 2. 版本对齐

- 所有库版本号统一为 0.1.0
- 依赖版本约束：isage-libs>=0.2.0

### 3. PyPI 发布流程

```bash
# 使用 sage-pypi-publisher
cd /home/shuhao/sage-pypi-publisher

# TestPyPI 测试
./publish.sh isage-agentic --test-pypi --version 0.1.0
./publish.sh isage-rag --test-pypi --version 0.1.0
./publish.sh isage-privacy --test-pypi --version 0.1.0
./publish.sh isage-finetune --test-pypi --version 0.1.0
./publish.sh isage-eval --test-pypi --version 0.1.0

# 验证安装
pip install -i https://test.pypi.org/simple/ isage-agentic

# 正式发布
./publish.sh isage-agentic --version 0.1.0
./publish.sh isage-rag --version 0.1.0
# ... 其他库
```

### 4. 更新主仓库

```toml
# packages/sage-libs/pyproject.toml
[project.optional-dependencies]
agentic = ["isage-agentic>=0.1.0"]
rag = ["isage-rag>=0.1.0"]
privacy = ["isage-privacy>=0.1.0"]
finetune = ["isage-finetune>=0.1.0"]
eval = ["isage-eval>=0.1.0"]
safety = ["isage-safety>=0.1.0"]
all = [
    "isage-agentic>=0.1.0",
    "isage-rag>=0.1.0",
    "isage-privacy>=0.1.0",
    "isage-finetune>=0.1.0",
    "isage-eval>=0.1.0",
]
```

______________________________________________________________________

## 📊 总体进度追踪

| Agent   | 任务          | 状态      | 预计时间 |
| ------- | ------------- | --------- | -------- |
| Agent-0 | 仓库准备      | 🔲 待开始 | 30min    |
| Agent-1 | Agentic       | 🔲 待开始 | 3h       |
| Agent-2 | RAG           | 🔲 待开始 | 2h       |
| Agent-3 | Fine-tuning   | 🔲 待开始 | 2h       |
| Agent-4 | Evaluation    | 🔲 待开始 | 1.5h     |
| Agent-5 | Privacy       | 🔲 待开始 | 2h       |
| Agent-6 | Safety (可选) | 🔲 待开始 | 1h       |
| Agent-7 | Documentation | 🔲 待开始 | 2h       |
| Agent-8 | Validation    | 🔲 待开始 | 2h       |

**总计**: 约 15.5 小时（不含 Safety）

**并行策略**：

- Phase 1: Agent-0 单独执行（30min）
- Phase 2: Agent-1, 2, 3, 4, 5 并行（3h）
- Phase 3: Agent-7 与 Phase 2 部分重叠（2h）
- Phase 4: Agent-8 串行（2h）

**实际总时长**: 约 7-8 小时（并行优化）

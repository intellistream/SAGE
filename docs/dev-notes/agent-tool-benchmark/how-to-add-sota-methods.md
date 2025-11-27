# 如何添加新的 SOTA 训练方法

## 📍 添加位置

添加新方法涉及 **3个层级**，请按需修改：

### 1️⃣ 算法实现 (sage-libs/finetune/agent/)

如果新 SOTA 方法需要新的算法组件（如新的样本选择策略），在这里添加：

```
packages/sage-libs/src/sage/libs/finetune/agent/
├── continual.py        # CoresetSelector, OnlineContinualLearner
├── trainer.py          # AgentSFTTrainer - 训练循环
└── YOUR_NEW_ALGO.py    # 新增: 如 curriculum_learning.py
```

**示例：添加 Curriculum Learning**

```python
# packages/sage-libs/src/sage/libs/finetune/agent/curriculum.py

class CurriculumScheduler:
    """按难度渐进式安排训练样本"""

    def __init__(self, strategy: str = "loss_based"):
        self.strategy = strategy

    def sort_samples(self, samples: list, metrics: dict) -> list:
        """按难度排序，先简单后复杂"""
        if self.strategy == "loss_based":
            # 低 loss = 简单，先学
            return sorted(samples, key=lambda s: metrics.get(s.id, 0))
        ...
```

### 2️⃣ 方法配置 (method_comparison.py)

在 `MethodRegistry` 中注册新方法配置：

```python
# packages/sage-benchmark/src/sage/benchmark/benchmark_agent/experiments/method_comparison.py

class MethodRegistry:
    @staticmethod
    def get_all_methods() -> dict[str, MethodConfig]:
        return {
            # ... 现有方法 A-D ...

            # 🆕 添加新的 SOTA 方法
            "E_curriculum": MethodConfig(
                name="E: Curriculum Learning",
                description="Easy-to-hard progressive training",
                use_coreset=False,
                use_continual=False,
                use_curriculum=True,  # 需要先在 MethodConfig 添加此字段
                curriculum_strategy="loss_based",
            ),

            "F_data_augmentation": MethodConfig(
                name="F: Data Augmentation",
                description="Augment training data with paraphrases",
                use_augmentation=True,
                augmentation_factor=2.0,
            ),

            "G_knowledge_distillation": MethodConfig(
                name="G: Knowledge Distillation",
                description="Distill from larger teacher model",
                use_distillation=True,
                teacher_model="Qwen/Qwen2.5-72B-Instruct",
            ),
        }
```

### 3️⃣ 训练器集成 (trainer.py)

在 `AgentSFTTrainer` 中集成新算法：

```python
# packages/sage-libs/src/sage/libs/finetune/agent/trainer.py

class AgentSFTTrainer:
    def __init__(self, config: AgentSFTConfig, ...):
        ...
        self.curriculum_scheduler = self._build_curriculum_scheduler()  # 新增

    def prepare_datasets(self) -> None:
        ...
        # 🆕 添加 curriculum learning 支持
        if self.curriculum_scheduler and self.config.use_curriculum:
            self._train_samples = self.curriculum_scheduler.sort_samples(
                self._train_samples,
                metrics=self._collect_metrics(...)
            )
```

---

## 🔬 当前 SOTA 方法对比

| 方法 | 论文/来源 | 当前实现状态 |
|------|----------|-------------|
| **Coreset Selection** | "Selection Via Proxy" (2019) | ✅ 已实现 (B1-B4) |
| **Continual Learning** | "Experience Replay" (2017) | ✅ 已实现 (C) |
| **Curriculum Learning** | "Self-Paced Learning" (2010) | ⬜ 待添加 |
| **Data Augmentation** | "Back Translation" (2016) | ⬜ 待添加 |
| **Knowledge Distillation** | "DistilBERT" (2019) | ⬜ 待添加 |
| **Active Learning** | "Uncertainty Sampling" | ⬜ 待添加 |
| **LoRA+** | "LoRA+: Efficient Low Rank" (2024) | ⬜ 待添加 |
| **DoRA** | "Weight-Decomposed LoRA" (2024) | ⬜ 待添加 |

---

## ✅ 当前微调是否可用？

**是的！** 当前代码已经可以真实微调大模型：

### 已实现功能

1. **完整训练流程** (`AgentSFTTrainer.train()`)
   - 加载模型 + Tokenizer
   - 应用 LoRA 适配器
   - 数据预处理和 tokenization
   - HuggingFace Trainer 训练循环
   - 保存 LoRA 权重

2. **优化技术**
   - LoRA (r=64, alpha=128)
   - 8-bit/4-bit 量化
   - Gradient Checkpointing
   - bf16/fp16 混合精度

3. **样本选择** (Coreset)
   - Loss Top-K
   - Diversity-based
   - Hybrid (60/40)
   - Random baseline

4. **持续学习** (Continual)
   - Experience Replay Buffer
   - Replay Ratio 控制

### 运行微调

```bash
# 快速测试 (~15分钟)
cd packages/sage-benchmark/src/sage/benchmark/benchmark_agent/scripts
python run_full_training_comparison.py --method D_combined --quick

# 完整训练 (~3-4小时)
python run_full_training_comparison.py --full

# 单独运行 Baseline
python run_full_training_comparison.py --method A_baseline --full
```

### 输出位置

```
~/.sage/agent_training/
├── checkpoints/     # 训练检查点
├── logs/            # TensorBoard 日志
└── lora_weights/    # 最终 LoRA 权重
```

---

## 🚀 建议的下一步

1. **运行一次真实训练**验证流程正常
2. **添加 Curriculum Learning** 作为 Method E
3. **添加评估流程**使用微调后的模型评估 benchmark
4. **集成 DoRA/LoRA+** 最新的高效微调方法

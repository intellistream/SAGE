# Agent RL/SFT 训练管线设计

## 1. 技术目标对齐

针对华为**技术目标1：大模型Agent核心能力提升**的训练方案设计：

| 挑战 | 训练目标 | 方法 |
|------|----------|------|
| 工具选择困难 | 提升工具调用准确率 | SFT + 工具选择专项数据 |
| 计划能力薄弱 | 增强多步推理能力 | 多步骤规划 SFT + Outcome Reward |
| 时机判断不准 | 优化调用时机决策 | RL with timing rewards |
| 千级工具检索 | 大规模检索能力 | Embedding + Contrastive Learning |

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Agent Training Pipeline                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│   │   Stage 1   │    │   Stage 2    │    │   Stage 3    │    │   Stage 4    │  │
│   │   Warmup    │───▶│  SFT/CPT     │───▶│  RL (DPO/    │───▶│  Evaluation  │  │
│   │   (可选)    │    │  基础训练    │    │  PPO/GRPO)   │    │   & Deploy   │  │
│   └─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                                                  │
│   数据流:                                                                        │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  agent_sft (5K dialogs) ──▶ SFT 格式转换 ──▶ 训练                       │   │
│   │  agent_tools (1.2K)     ──▶ Contrastive Learning ──▶ 工具检索优化       │   │
│   │  agent_benchmark (1.1K) ──▶ RL Reward / Evaluation ──▶ 策略优化         │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 3. 训练阶段详解

### 3.1 Stage 1: Warmup (可选)

**目标**: 让基础模型熟悉 Agent 任务格式

```yaml
warmup:
  enabled: false  # 如果基础模型已有 Agent 能力可跳过
  data_source: "agent_sft"
  samples: 1000  # 少量样本
  focus:
    - tool_format_understanding
    - basic_planning_structure
```

### 3.2 Stage 2: SFT (Supervised Fine-Tuning)

**目标**: 建立核心 Agent 能力

#### 3.2.1 数据配置

```python
@dataclass
class AgentSFTConfig:
    """Agent SFT 训练配置"""

    # 数据源
    train_data: str = "agent_sft:train"
    dev_data: str = "agent_sft:dev"

    # 训练目标分布
    task_weights: dict = field(default_factory=lambda: {
        "tool_selection": 0.35,     # 工具选择 (挑战1)
        "multi_step_planning": 0.30, # 多步规划 (挑战2)
        "timing_decision": 0.20,    # 时机判断 (挑战3)
        "tool_retrieval": 0.15,     # 工具检索 (挑战4)
    })

    # 模型配置
    base_model: str = "Qwen/Qwen2.5-7B-Instruct"
    max_length: int = 4096

    # LoRA 配置
    lora_r: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    lora_target_modules: list = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ])

    # 训练超参
    num_epochs: int = 3
    batch_size: int = 4
    gradient_accumulation: int = 8
    learning_rate: float = 2e-5
    warmup_ratio: float = 0.1
    lr_scheduler: str = "cosine"
```

> ✨ **New:** `AgentSFTConfig` 现已支持 coreset 过滤与在线复习开关。

- `use_coreset_selection`: 在 tokenizer 前启用 `CoresetSelector`，优先保留高 loss / 多样化样本。
- `coreset_target_size`: 限制每轮送入模型的样本上限。
- `coreset_strategy`: `loss_topk`, `diversity`, `hybrid`, `random` 四种策略可选。
- `use_online_continual`: 启用 `OnlineContinualLearner`，自动拼接 replay 样本。
- `continual_buffer_size` & `continual_replay_ratio`: 控制 rehearsal buffer 容量与每轮 replay 比例。

```python
sft_config = AgentSFTConfig(
    base_model="Qwen/Qwen2.5-0.5B-Instruct",
    use_coreset_selection=True,
    coreset_target_size=8000,
    coreset_strategy="hybrid",
    use_online_continual=True,
    continual_buffer_size=4096,
    continual_replay_ratio=0.3,
)
```

#### 3.2.2 数据格式转换

```python
class AgentSFTFormatter:
    """将 agent_sft 对话转换为训练格式"""

    TEMPLATE = """<|system|>
你是一个智能助手，擅长使用工具完成复杂任务。
可用工具：
{tool_descriptions}
<|user|>
{user_query}
<|assistant|>
{plan_and_execution}"""

    def format_dialog(self, dialog: AgentSFTDialog) -> dict:
        """
        转换单个对话为 SFT 格式

        Returns:
            {"input": str, "output": str, "task_type": str}
        """
        # 提取用户请求
        user_turns = [t for t in dialog.turns if t.role == "user"]
        user_query = user_turns[0].content if user_turns else ""

        # 构建工具描述 (从 agent_tools 获取)
        tool_descriptions = self._get_tool_descriptions(dialog.target_tools)

        # 构建助手响应 (包含规划和执行)
        assistant_output = self._format_assistant_response(dialog)

        # 确定任务类型
        task_type = self._classify_task(dialog)

        return {
            "input": self.TEMPLATE.format(
                tool_descriptions=tool_descriptions,
                user_query=user_query,
                plan_and_execution=""
            ),
            "output": assistant_output,
            "task_type": task_type,
            "metadata": dialog.metadata
        }

    def _format_assistant_response(self, dialog: AgentSFTDialog) -> str:
        """格式化助手响应，包含思考过程和工具调用"""
        response_parts = []

        for turn in dialog.turns:
            if turn.role == "assistant":
                response_parts.append(f"<think>{turn.content}</think>")
            elif turn.role == "tool":
                response_parts.append(
                    f"<tool_call>{turn.tool_id}</tool_call>\n"
                    f"<tool_result>{turn.result}</tool_result>"
                )

        return "\n".join(response_parts)
```

#### 3.2.3 Coreset 选择 & 在线复习

- `CoresetSelector`: 支持 `loss_topk`、`diversity`、`hybrid`、`random` 四种策略，对 `ProcessedDialog` 做轻量采样。
- `OnlineContinualLearner`: 维护 rehearsal buffer，并在 `prepare_datasets()` 阶段按 `replay_ratio` 追加历史样本。
- `AgentSFTTrainer` 会根据 `AgentSFTConfig` 的新开关自动实例化并应用上述组件。
- `AgentDialogProcessor` 会为每条 `ProcessedDialog` 追加 `loss`（难度 proxy）、`token_length`、`lexical_diversity` 等指标，供 coreset/replay 筛选使用；若原始 metadata 已带 `loss`，则尊重该值。

```python
from sage.tools.agent_training import AgentSFTTrainer, AgentSFTConfig

config = AgentSFTConfig(
    use_coreset_selection=True,
    coreset_target_size=6000,
    use_online_continual=True,
    continual_buffer_size=3000,
    continual_replay_ratio=0.4,
)

trainer = AgentSFTTrainer(config)
trainer.prepare_datasets()  # 内部自动触发 coreset + replay
```

### 3.3 Stage 3: RL Training

**目标**: 通过强化学习优化策略

#### 3.3.1 奖励设计

```python
@dataclass
class AgentRewardConfig:
    """Agent RL 奖励配置"""

    # 奖励权重
    weights: dict = field(default_factory=lambda: {
        "task_completion": 0.4,      # 任务完成奖励
        "tool_accuracy": 0.25,       # 工具选择准确性
        "efficiency": 0.15,          # 执行效率 (步数)
        "timing_quality": 0.10,      # 调用时机质量
        "format_compliance": 0.10,   # 格式符合度
    })

    # 惩罚项
    penalties: dict = field(default_factory=lambda: {
        "wrong_tool": -0.3,          # 选错工具
        "redundant_call": -0.2,      # 冗余调用
        "format_error": -0.1,        # 格式错误
        "timeout": -0.5,             # 超时
    })


class AgentRewardModel:
    """Agent 奖励模型"""

    def __init__(self, config: AgentRewardConfig):
        self.config = config
        self.tool_verifier = ToolVerifier()  # 工具调用验证器
        self.plan_evaluator = PlanEvaluator()  # 规划质量评估器

    def compute_reward(
        self,
        query: str,
        response: str,
        ground_truth: dict,
        execution_trace: list
    ) -> dict:
        """
        计算综合奖励分数

        Args:
            query: 用户请求
            response: 模型响应
            ground_truth: 标准答案
            execution_trace: 执行轨迹

        Returns:
            {
                "total": float,
                "breakdown": dict,
                "feedback": str
            }
        """
        rewards = {}

        # 1. 任务完成度
        rewards["task_completion"] = self._eval_task_completion(
            response, ground_truth, execution_trace
        )

        # 2. 工具选择准确性
        rewards["tool_accuracy"] = self._eval_tool_accuracy(
            response, ground_truth["target_tools"]
        )

        # 3. 执行效率
        rewards["efficiency"] = self._eval_efficiency(
            execution_trace, ground_truth.get("optimal_steps", 5)
        )

        # 4. 时机质量
        rewards["timing_quality"] = self._eval_timing(
            response, execution_trace
        )

        # 5. 格式合规性
        rewards["format_compliance"] = self._eval_format(response)

        # 加权求和
        total = sum(
            rewards[k] * self.config.weights[k]
            for k in rewards
        )

        return {
            "total": total,
            "breakdown": rewards,
            "feedback": self._generate_feedback(rewards)
        }

    def _eval_tool_accuracy(self, response: str, target_tools: list) -> float:
        """评估工具选择准确率"""
        predicted_tools = self._extract_tool_calls(response)

        if not target_tools:
            return 1.0 if not predicted_tools else 0.5

        # Precision & Recall
        correct = len(set(predicted_tools) & set(target_tools))
        precision = correct / len(predicted_tools) if predicted_tools else 0
        recall = correct / len(target_tools)

        # F1 Score
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)
```

#### 3.3.2 RL 算法选择

```python
@dataclass
class RLTrainingConfig:
    """RL 训练配置"""

    # 算法选择
    algorithm: Literal["dpo", "ppo", "grpo"] = "dpo"

    # DPO 配置 (推荐，更稳定)
    dpo_config: dict = field(default_factory=lambda: {
        "beta": 0.1,
        "reference_free": False,
        "label_smoothing": 0.0,
        "loss_type": "sigmoid",  # sigmoid, hinge, ipo
    })

    # PPO 配置 (需要更多资源)
    ppo_config: dict = field(default_factory=lambda: {
        "kl_coef": 0.02,
        "clip_range": 0.2,
        "vf_coef": 0.5,
        "num_rollouts": 128,
        "chunk_size": 64,
    })

    # GRPO 配置 (Group Relative Policy Optimization)
    grpo_config: dict = field(default_factory=lambda: {
        "group_size": 4,
        "beta": 0.1,
        "use_advantage": True,
    })


class AgentRLTrainer:
    """Agent RL 训练器"""

    def __init__(
        self,
        config: RLTrainingConfig,
        base_model_path: str,
        sft_model_path: str,  # Stage 2 的输出
        reward_model: AgentRewardModel,
    ):
        self.config = config
        self.reward_model = reward_model

        # 加载模型
        if config.algorithm == "dpo":
            self._setup_dpo(base_model_path, sft_model_path)
        elif config.algorithm == "ppo":
            self._setup_ppo(base_model_path, sft_model_path)
        elif config.algorithm == "grpo":
            self._setup_grpo(base_model_path, sft_model_path)

    def generate_preference_pairs(
        self,
        prompts: list[str],
        num_samples: int = 4
    ) -> list[dict]:
        """
        为 DPO 生成偏好对

        Returns:
            [{"prompt": str, "chosen": str, "rejected": str}, ...]
        """
        pairs = []

        for prompt in prompts:
            # 生成多个候选响应
            responses = self._sample_responses(prompt, num_samples)

            # 用 reward model 打分
            scores = [
                self.reward_model.compute_reward(
                    query=prompt,
                    response=r,
                    ground_truth={},  # online generation
                    execution_trace=[]
                )["total"]
                for r in responses
            ]

            # 选择最好和最差的作为偏好对
            best_idx = max(range(len(scores)), key=lambda i: scores[i])
            worst_idx = min(range(len(scores)), key=lambda i: scores[i])

            if scores[best_idx] > scores[worst_idx]:
                pairs.append({
                    "prompt": prompt,
                    "chosen": responses[best_idx],
                    "rejected": responses[worst_idx],
                    "chosen_score": scores[best_idx],
                    "rejected_score": scores[worst_idx],
                })

        return pairs
```

### 3.4 Stage 4: Evaluation

**目标**: 验证训练效果

```python
class AgentTrainingEvaluator:
    """训练效果评估器"""

    def __init__(self, benchmark_loader):
        self.benchmark = benchmark_loader

    def evaluate(
        self,
        model,
        split: str = "test",
        metrics: list = None
    ) -> dict:
        """
        在 agent_benchmark 上评估

        Metrics:
            - tool_selection_accuracy: 工具选择准确率
            - plan_success_rate: 规划成功率  
            - step_efficiency: 步骤效率
            - timing_precision: 时机准确率
            - end_to_end_success: 端到端成功率
        """
        metrics = metrics or [
            "tool_selection_accuracy",
            "plan_success_rate",
            "step_efficiency",
            "timing_precision",
            "end_to_end_success"
        ]

        results = {m: [] for m in metrics}

        for sample in self.benchmark.iter_samples(split):
            # 生成响应
            response = model.generate(sample.instruction)

            # 评估各项指标
            if "tool_selection_accuracy" in metrics:
                acc = self._eval_tool_selection(response, sample)
                results["tool_selection_accuracy"].append(acc)

            if "plan_success_rate" in metrics:
                success = self._eval_plan_success(response, sample)
                results["plan_success_rate"].append(success)

            # ... 其他指标

        # 聚合结果
        return {
            m: {
                "mean": np.mean(v),
                "std": np.std(v),
                "count": len(v)
            }
            for m, v in results.items()
        }
```

## 4. 数据流集成

### 4.1 与现有数据源的集成

```python
# 在 sage/data/usages/ 下添加 agent_training/

class AgentTrainingUsage:
    """Agent 训练数据用法配置"""

    SOURCES = {
        "sft": "agent_sft",
        "tools": "agent_tools",
        "benchmark": "agent_benchmark",
    }

    def get_sft_data(self, split: str = "train") -> Iterator:
        """获取 SFT 训练数据"""
        loader = self.manager.get_by_source("agent_sft")
        formatter = AgentSFTFormatter()

        for dialog in loader.iter_dialogs(split):
            yield formatter.format_dialog(dialog)

    def get_preference_data(self) -> Iterator:
        """获取 DPO 偏好数据 (需要预先生成)"""
        # 从 agent_benchmark 生成偏好对
        benchmark = self.manager.get_by_source("agent_benchmark")

        for sample in benchmark.iter_samples("train"):
            # 返回预生成的偏好对
            yield sample.preference_pair

    def get_evaluation_data(self, split: str = "test") -> Iterator:
        """获取评估数据"""
        return self.manager.get_by_source("agent_benchmark").iter_samples(split)
```

### 4.2 与现有训练框架的集成

```python
# 扩展 sage-tools/finetune

class AgentLoRATrainer(LoRATrainer):
    """Agent 专用 LoRA 训练器"""

    def __init__(self, config: AgentSFTConfig):
        # 转换为基础训练配置
        base_config = TrainingConfig(
            model_name=config.base_model,
            max_length=config.max_length,
            lora_r=config.lora_r,
            lora_alpha=config.lora_alpha,
            lora_dropout=config.lora_dropout,
            num_train_epochs=config.num_epochs,
            per_device_train_batch_size=config.batch_size,
            gradient_accumulation_steps=config.gradient_accumulation,
            learning_rate=config.learning_rate,
        )
        super().__init__(base_config)

        self.agent_config = config
        self.data_usage = AgentTrainingUsage()

    def prepare_data(self):
        """准备 Agent SFT 数据"""
        # 加载并格式化数据
        train_data = list(self.data_usage.get_sft_data("train"))

        # 按任务类型采样
        sampled_data = self._weighted_sample(
            train_data,
            self.agent_config.task_weights
        )

        # 转换为 HuggingFace Dataset
        self.dataset = Dataset.from_list(sampled_data)

        print(f"✅ 准备了 {len(self.dataset)} 条训练数据")
        print(f"   任务分布: {self._get_task_distribution(sampled_data)}")
```

## 5. 完整训练流程

### 5.1 CLI 命令

```bash
# Stage 2: SFT 训练
sage-dev agent train sft \
    --base-model Qwen/Qwen2.5-7B-Instruct \
    --data agent_sft:train \
    --output ./output/agent_sft_v1 \
    --epochs 3 \
    --task-weights '{"tool_selection":0.35,"planning":0.30,"timing":0.20,"retrieval":0.15}'

# Stage 3: DPO 训练
sage-dev agent train dpo \
    --sft-model ./output/agent_sft_v1 \
    --data agent_benchmark:train \
    --output ./output/agent_dpo_v1 \
    --beta 0.1 \
    --num-samples 4

# Stage 4: 评估
sage-dev agent evaluate \
    --model ./output/agent_dpo_v1 \
    --benchmark agent_benchmark:test \
    --metrics tool_accuracy,plan_success,efficiency
```

### 5.2 Python API

```python
from sage.tools.agent_training import (
    AgentSFTConfig,
    AgentLoRATrainer,
    RLTrainingConfig,
    AgentRLTrainer,
    AgentRewardModel,
    AgentTrainingEvaluator
)

# 1. SFT 阶段
sft_config = AgentSFTConfig(
    base_model="Qwen/Qwen2.5-7B-Instruct",
    num_epochs=3,
)
sft_trainer = AgentLoRATrainer(sft_config)
sft_trainer.train()
sft_trainer.save_model("./output/agent_sft")

# 2. RL 阶段 (DPO)
rl_config = RLTrainingConfig(algorithm="dpo")
reward_model = AgentRewardModel(AgentRewardConfig())
rl_trainer = AgentRLTrainer(
    config=rl_config,
    base_model_path="Qwen/Qwen2.5-7B-Instruct",
    sft_model_path="./output/agent_sft",
    reward_model=reward_model
)
rl_trainer.train()
rl_trainer.save_model("./output/agent_dpo")

# 3. 评估
evaluator = AgentTrainingEvaluator(benchmark_loader)
results = evaluator.evaluate(
    model=rl_trainer.model,
    split="test"
)
print(f"Tool Selection Accuracy: {results['tool_selection_accuracy']['mean']:.2%}")
print(f"Plan Success Rate: {results['plan_success_rate']['mean']:.2%}")
```

## 6. 资源估算

### 6.1 训练资源需求

| 阶段 | GPU | 显存 | 训练时间 | 数据量 |
|------|-----|------|----------|--------|
| SFT | 1x A100-80G | ~60GB | ~8h | 4K dialogs |
| DPO | 1x A100-80G | ~70GB | ~4h | 2K pairs |
| PPO | 2x A100-80G | ~140GB | ~12h | online |

### 6.2 推荐配置

```yaml
# 开发/测试 (RTX 4090 24GB)
development:
  base_model: "Qwen/Qwen2.5-1.5B-Instruct"
  lora_r: 16
  batch_size: 1
  gradient_accumulation: 16
  max_length: 2048
  load_in_4bit: true

# 生产 (A100 80GB)
production:
  base_model: "Qwen/Qwen2.5-7B-Instruct"
  lora_r: 64
  batch_size: 4
  gradient_accumulation: 8
  max_length: 4096
  load_in_8bit: true
```

## 7. 下一步计划

1. **Phase 1** (1-2周):
   - 实现 `AgentSFTFormatter` 数据格式转换
   - 扩展 `LoRATrainer` 支持 Agent 任务
   - 基础 SFT 训练流程
    - Coreset Selection + 在线复习（RTX 3060 友好）

2. **Phase 2** (2-3周):
   - 实现 `AgentRewardModel` 奖励模型
   - DPO 训练管线
   - 评估框架集成

3. **Phase 3** (3-4周):
   - PPO/GRPO 支持 (可选)
   - 在线学习支持
   - 完整评估报告

## 8. 相关文件

```
packages/
├── sage-tools/src/sage/tools/
│   ├── finetune/              # 现有 LoRA 训练
│   └── agent_training/        # 新增 Agent 训练
│       ├── __init__.py
│       ├── config.py          # 配置定义
│       ├── data_formatter.py  # 数据格式转换
│       ├── sft_trainer.py     # SFT 训练器
│       ├── rl_trainer.py      # RL 训练器
│       ├── reward_model.py    # 奖励模型
│       └── evaluator.py       # 评估器
│
└── sage-benchmark/src/sage/data/
    ├── sources/
    │   ├── agent_sft/         # SFT 数据 (5K)
    │   ├── agent_tools/       # 工具元数据 (1.2K)
    │   └── agent_benchmark/   # 评估数据 (1.1K)
    └── usages/
        └── agent_training/    # 训练用法配置
```

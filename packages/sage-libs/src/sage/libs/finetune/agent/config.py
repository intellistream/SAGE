"""
Agent Training Configuration

Defines configuration classes for:
- SFT training
- RL training (DPO/PPO/GRPO)
- Reward model
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional


@dataclass
class AgentSFTConfig:
    """Agent SFT 训练配置

    配置 Agent 监督微调训练，针对工具选择、规划、时机判断等能力。

    Attributes:
        base_model: 基础模型名称或路径
        train_data: 训练数据源 (格式: "source:split")
        dev_data: 验证数据源
        task_weights: 各任务类型的采样权重
        max_length: 最大序列长度
        lora_r: LoRA rank
        lora_alpha: LoRA alpha
        lora_dropout: LoRA dropout
        lora_target_modules: LoRA 目标模块
        num_epochs: 训练轮数
        batch_size: 批次大小
        gradient_accumulation: 梯度累积步数
        learning_rate: 学习率
        warmup_ratio: 预热比例
        lr_scheduler: 学习率调度器
        output_dir: 输出目录
        use_coreset_selection: 是否启用 coreset 过滤
        coreset_target_size: 每次训练的最大 coreset 样本数
        use_online_continual: 是否启用在线增量/复习
        continual_buffer_size: 在线复习缓冲区大小

    Example:
        >>> config = AgentSFTConfig(
        ...     base_model="Qwen/Qwen2.5-7B-Instruct",
        ...     num_epochs=3,
        ...     task_weights={"tool_selection": 0.4, "planning": 0.3}
        ... )
    """

    # 数据源
    train_data: str = "agent_sft:train"
    dev_data: str = "agent_sft:dev"

    # 任务权重 (用于按任务类型采样)
    task_weights: dict = field(
        default_factory=lambda: {
            "tool_selection": 0.35,  # 工具选择
            "multi_step_planning": 0.30,  # 多步规划
            "timing_decision": 0.20,  # 时机判断
            "tool_retrieval": 0.15,  # 工具检索
        }
    )

    # 模型配置
    base_model: str = "Qwen/Qwen2.5-7B-Instruct"
    max_length: int = 4096
    load_in_8bit: bool = True
    load_in_4bit: bool = False
    fp16: bool = True
    bf16: bool = False
    gradient_checkpointing: bool = True
    optim: str = "paged_adamw_8bit"
    padding_strategy: Literal["max_length", "longest", "do_not_pad"] = "max_length"
    padding_side: Literal["left", "right"] = "right"
    output_format: Literal["alpaca", "sharegpt", "chatml"] = "chatml"
    shuffle_train: bool = True
    shuffle_eval: bool = False
    max_train_samples: Optional[int] = None
    max_eval_samples: Optional[int] = 512

    # Coreset & continual learning
    use_coreset_selection: bool = False
    coreset_target_size: Optional[int] = None
    coreset_strategy: Literal["loss_topk", "diversity", "hybrid", "random"] = "loss_topk"
    coreset_metric_key: str = "loss"
    use_online_continual: bool = False
    continual_buffer_size: int = 2048
    continual_replay_ratio: float = 0.25

    # LoRA 配置
    lora_r: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    lora_target_modules: list = field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    )

    # DoRA 配置 (Weight-Decomposed Low-Rank Adaptation)
    # 参考: "DoRA: Weight-Decomposed Low-Rank Adaptation" (Liu et al., 2024)
    use_dora: bool = False

    # LoRA+ 配置 (Efficient Low Rank Adaptation with differentiated learning rates)
    # 参考: "LoRA+: Efficient Low Rank Adaptation of Large Models" (Hayou et al., 2024)
    use_lora_plus: bool = False
    lora_plus_lr_ratio: float = 16.0  # B 矩阵学习率 = base_lr * ratio

    # 训练超参
    num_epochs: int = 3
    batch_size: int = 1
    gradient_accumulation: int = 16
    learning_rate: float = 2e-5
    warmup_ratio: float = 0.1
    lr_scheduler: str = "cosine"

    # 输出配置
    output_dir: Path = field(default_factory=lambda: Path.home() / ".sage" / "agent_training")
    logging_steps: int = 10
    save_steps: int = 500
    eval_steps: int = 200
    eval_strategy: Literal["no", "steps", "epoch"] = "steps"
    save_total_limit: int = 3
    report_to: Literal["none", "tensorboard", "wandb"] = "none"
    load_best_model: bool = True
    metric_for_best_model: str = "eval_loss"
    greater_is_better: bool = False
    dataloader_num_workers: int = 0
    seed: int = 42

    def __post_init__(self) -> None:
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "logs").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "lora_weights").mkdir(parents=True, exist_ok=True)
        self.padding_side = self.padding_side or "right"

    @property
    def checkpoint_dir(self) -> Path:
        return self.output_dir / "checkpoints"

    @property
    def log_dir(self) -> Path:
        return self.output_dir / "logs"

    @property
    def lora_dir(self) -> Path:
        return self.output_dir / "lora_weights"

    @property
    def effective_batch_size(self) -> int:
        """有效批次大小"""
        return self.batch_size * self.gradient_accumulation


@dataclass
class RLTrainingConfig:
    """RL 训练配置

    支持 DPO, PPO, GRPO 三种算法。

    Attributes:
        algorithm: RL 算法选择
        sft_model_path: SFT 模型路径 (Stage 2 输出)
        reference_model_path: 参考模型路径 (用于 KL 约束)
        dpo_config: DPO 算法配置
        ppo_config: PPO 算法配置
        grpo_config: GRPO 算法配置

    Example:
        >>> config = RLTrainingConfig(
        ...     algorithm="dpo",
        ...     sft_model_path="./output/agent_sft",
        ...     dpo_config={"beta": 0.1}
        ... )
    """

    # 算法选择
    algorithm: Literal["dpo", "ppo", "grpo"] = "dpo"

    # 模型路径
    sft_model_path: Optional[str] = None
    reference_model_path: Optional[str] = None  # None = 使用 SFT 模型作为参考

    # DPO 配置
    dpo_config: dict = field(
        default_factory=lambda: {
            "beta": 0.1,  # KL 惩罚系数
            "reference_free": False,  # 是否免参考模型
            "label_smoothing": 0.0,  # 标签平滑
            "loss_type": "sigmoid",  # sigmoid, hinge, ipo
        }
    )

    # PPO 配置
    ppo_config: dict = field(
        default_factory=lambda: {
            "kl_coef": 0.02,  # KL 系数
            "clip_range": 0.2,  # PPO clip 范围
            "vf_coef": 0.5,  # 价值函数系数
            "num_rollouts": 128,  # 每次更新的 rollout 数
            "chunk_size": 64,  # 分块大小
            "gamma": 0.99,  # 折扣因子
            "lam": 0.95,  # GAE lambda
        }
    )

    # GRPO 配置 (Group Relative Policy Optimization)
    grpo_config: dict = field(
        default_factory=lambda: {
            "group_size": 4,  # 每组样本数
            "beta": 0.1,  # 温度参数
            "use_advantage": True,  # 使用优势函数
        }
    )

    # 训练超参
    num_epochs: int = 1
    batch_size: int = 2
    gradient_accumulation: int = 8
    learning_rate: float = 5e-6

    # 数据生成
    num_samples_per_prompt: int = 4  # 每个 prompt 生成的响应数

    # 输出配置
    output_dir: Path = field(default_factory=lambda: Path.home() / ".sage" / "agent_rl")


@dataclass
class AgentRewardConfig:
    """Agent 奖励模型配置

    定义各项奖励和惩罚的权重。

    Attributes:
        weights: 正向奖励权重
        penalties: 惩罚项

    Example:
        >>> config = AgentRewardConfig()
        >>> config.weights["tool_accuracy"]
        0.25
    """

    # 奖励权重 (总和应为 1.0)
    weights: dict = field(
        default_factory=lambda: {
            "task_completion": 0.40,  # 任务完成奖励
            "tool_accuracy": 0.25,  # 工具选择准确性
            "efficiency": 0.15,  # 执行效率 (步数)
            "timing_quality": 0.10,  # 调用时机质量
            "format_compliance": 0.10,  # 格式符合度
        }
    )

    # 惩罚项 (负值)
    penalties: dict = field(
        default_factory=lambda: {
            "wrong_tool": -0.3,  # 选错工具
            "redundant_call": -0.2,  # 冗余调用
            "format_error": -0.1,  # 格式错误
            "timeout": -0.5,  # 超时
            "hallucination": -0.4,  # 幻觉工具 (不存在的工具)
        }
    )

    # 评估配置
    max_steps: int = 10  # 最大允许步数
    timeout_seconds: float = 60.0  # 执行超时


@dataclass
class TrainingPipelineConfig:
    """完整训练管线配置

    组合 SFT 和 RL 配置，定义完整的训练流程。

    Example:
        >>> config = TrainingPipelineConfig(
        ...     run_sft=True,
        ...     run_rl=True,
        ...     sft_config=AgentSFTConfig(num_epochs=3),
        ...     rl_config=RLTrainingConfig(algorithm="dpo")
        ... )
    """

    # 阶段控制
    run_warmup: bool = False
    run_sft: bool = True
    run_rl: bool = True
    run_eval: bool = True

    # 各阶段配置
    sft_config: AgentSFTConfig = field(default_factory=AgentSFTConfig)
    rl_config: RLTrainingConfig = field(default_factory=RLTrainingConfig)
    reward_config: AgentRewardConfig = field(default_factory=AgentRewardConfig)

    # 全局配置
    seed: int = 42
    wandb_project: Optional[str] = None
    wandb_run_name: Optional[str] = None

    # 输出配置
    experiment_name: str = "agent_training"
    output_base_dir: Path = field(default_factory=lambda: Path.home() / ".sage" / "experiments")

    @property
    def experiment_dir(self) -> Path:
        """实验输出目录"""
        return self.output_base_dir / self.experiment_name

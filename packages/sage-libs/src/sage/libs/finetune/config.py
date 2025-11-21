"""
配置管理模块

定义训练配置和 LoRA 配置
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LoRAConfig:
    """LoRA 配置"""

    r: int = 8
    """LoRA rank"""

    lora_alpha: int = 16
    """LoRA alpha 参数"""

    target_modules: list[str] = field(
        default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    """要应用 LoRA 的模块"""

    lora_dropout: float = 0.05
    """LoRA dropout 率"""

    bias: str = "none"
    """Bias 训练方式"""

    task_type: str = "CAUSAL_LM"
    """任务类型"""


@dataclass
class TrainingConfig:
    """训练配置"""

    # 模型配置
    model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    """基础模型名称"""

    load_in_8bit: bool = True
    """使用 8-bit 量化加载（节省显存）"""

    load_in_4bit: bool = False
    """使用 4-bit 量化加载（更节省显存，但可能影响效果）"""

    # 数据配置
    data_path: Path | None = None
    """训练数据路径"""

    max_length: int = 1024
    """最大序列长度（RTX 3060 建议 1024，更大的卡可以用 2048）"""

    # 训练超参数
    output_dir: Path = Path.home() / ".sage" / "finetune_output"
    """输出目录（默认：~/.sage/finetune_output）"""

    num_train_epochs: int = 3
    """训练轮数"""

    per_device_train_batch_size: int = 1
    """每个设备的 batch size（RTX 3060 建议 1）"""

    gradient_accumulation_steps: int = 16
    """梯度累积步数（有效 batch size = batch_size * 累积步数）"""

    learning_rate: float = 5e-5
    """学习率"""

    lr_scheduler_type: str = "cosine"
    """学习率调度器类型"""

    warmup_ratio: float = 0.1
    """预热比例"""

    # 优化配置
    fp16: bool = True
    """使用 FP16 混合精度训练"""

    bf16: bool = False
    """使用 BF16 混合精度训练（需要 Ampere 架构）"""

    gradient_checkpointing: bool = True
    """启用梯度检查点（节省显存，略微降低速度）"""

    optim: str = "paged_adamw_8bit"
    """优化器（8-bit 优化器节省显存）"""

    # 日志和保存
    logging_steps: int = 10
    """日志记录步数"""

    save_steps: int = 500
    """模型保存步数"""

    save_total_limit: int = 2
    """最多保存的检查点数量"""

    report_to: str = "tensorboard"
    """报告工具 (tensorboard/wandb/none)"""

    # LoRA 配置
    lora: LoRAConfig = field(default_factory=LoRAConfig)
    """LoRA 配置"""

    # 其他
    seed: int = 42
    """随机种子"""

    dataloader_num_workers: int = 0
    """数据加载器工作进程数（0 避免多进程内存占用）"""

    def __post_init__(self):
        """初始化后处理"""
        # 确保 output_dir 是 Path 对象
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        if isinstance(self.data_path, str):
            self.data_path = Path(self.data_path)

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 验证配置
        if self.load_in_4bit and self.load_in_8bit:
            raise ValueError("不能同时使用 4-bit 和 8-bit 量化")

        if self.fp16 and self.bf16:
            raise ValueError("不能同时使用 FP16 和 BF16")

    @property
    def effective_batch_size(self) -> int:
        """有效的 batch size"""
        return self.per_device_train_batch_size * self.gradient_accumulation_steps

    @property
    def checkpoint_dir(self) -> Path:
        """检查点目录"""
        return self.output_dir / "checkpoints"

    @property
    def lora_dir(self) -> Path:
        """LoRA 权重目录"""
        return self.output_dir / "lora_weights"

    @property
    def log_dir(self) -> Path:
        """日志目录"""
        return self.output_dir / "logs"

    def to_dict(self) -> dict:
        """转换为字典"""
        import dataclasses

        return dataclasses.asdict(self)

    def save(self, path: Path) -> None:
        """保存配置到文件"""
        import json

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def load(cls, path: Path) -> "TrainingConfig":
        """从文件加载配置"""
        import json

        with open(path) as f:
            data = json.load(f)
        return cls(**data)


# 预设配置
class PresetConfigs:
    """预设配置集合"""

    @staticmethod
    def rtx_3060() -> TrainingConfig:
        """RTX 3060 (12GB) 优化配置"""
        return TrainingConfig(
            load_in_8bit=True,
            max_length=1024,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=16,
            gradient_checkpointing=True,
            optim="paged_adamw_8bit",
        )

    @staticmethod
    def rtx_4090() -> TrainingConfig:
        """RTX 4090 (24GB) 优化配置"""
        return TrainingConfig(
            load_in_8bit=False,
            max_length=2048,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            gradient_checkpointing=False,
            optim="adamw_torch",
        )

    @staticmethod
    def a100() -> TrainingConfig:
        """A100 (40GB/80GB) 优化配置"""
        return TrainingConfig(
            load_in_8bit=False,
            bf16=True,
            fp16=False,
            max_length=4096,
            per_device_train_batch_size=8,
            gradient_accumulation_steps=2,
            gradient_checkpointing=False,
            optim="adamw_torch",
        )

    @staticmethod
    def minimal() -> TrainingConfig:
        """最小配置（适合显存 < 8GB）"""
        return TrainingConfig(
            load_in_4bit=True,
            load_in_8bit=False,
            max_length=512,
            per_device_train_batch_size=1,
            gradient_accumulation_steps=32,
            gradient_checkpointing=True,
            optim="paged_adamw_8bit",
            lora=LoRAConfig(r=4, lora_alpha=8),  # 更小的 LoRA rank
        )

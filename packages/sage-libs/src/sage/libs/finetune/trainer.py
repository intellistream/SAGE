"""
LoRA 训练器模块

提供简单易用的 LoRA 微调接口
"""

import sys
from pathlib import Path

import torch
from peft import LoraConfig as PeftLoraConfig
from peft import get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

from .config import TrainingConfig
from .data import prepare_dataset


class LoRATrainer:
    """LoRA 微调训练器

    示例:
        >>> config = TrainingConfig(
        ...     model_name="Qwen/Qwen2.5-Coder-1.5B-Instruct",
        ...     data_path="./data.json",
        ...     output_dir="./output",
        ... )
        >>> trainer = LoRATrainer(config)
        >>> trainer.train()
    """

    def __init__(self, config: TrainingConfig):
        """初始化训练器

        Args:
            config: 训练配置
        """
        self.config = config
        self.model = None
        self.tokenizer = None
        self.dataset = None
        self.trainer = None

    def load_model_and_tokenizer(self):
        """加载模型和分词器"""
        print("🤖 加载模型和分词器...")

        # 量化配置
        if self.config.load_in_8bit or self.config.load_in_4bit:
            # 检查 bitsandbytes 是否可用
            try:
                import bitsandbytes  # noqa: F401
            except ImportError as e:
                raise ImportError(
                    "使用量化训练需要安装 bitsandbytes 库。\n"
                    "请运行: pip install -U bitsandbytes\n"
                    "或安装完整依赖: pip install 'isage-libs[finetune-gpu]'"
                ) from e

        if self.config.load_in_8bit:
            print("⚠️  使用 8-bit 量化加载（节省显存）")
            from transformers import BitsAndBytesConfig

            load_kwargs = {
                "quantization_config": BitsAndBytesConfig(load_in_8bit=True),
                "device_map": "auto",
                "torch_dtype": torch.float16,
            }
        elif self.config.load_in_4bit:
            print("⚠️  使用 4-bit 量化加载（最大化节省显存）")
            from transformers import BitsAndBytesConfig

            load_kwargs = {
                "quantization_config": BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                ),
                "device_map": "auto",
            }
        else:
            print("📦 正常加载模型")
            load_kwargs = {
                "torch_dtype": "auto",
                "device_map": "auto",
            }

        # 加载模型
        self.model = AutoModelForCausalLM.from_pretrained(self.config.model_name, **load_kwargs)

        # 加载分词器
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)

        # 设置 pad_token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # 为量化训练准备模型（必须在应用 LoRA 之前）
        if self.config.load_in_8bit or self.config.load_in_4bit:
            print("🔧 为量化训练准备模型...")
            self.model = prepare_model_for_kbit_training(
                self.model,
                use_gradient_checkpointing=self.config.gradient_checkpointing,
            )

        print(f"✅ 模型加载完成: {self.config.model_name}\n")

    def apply_lora(self):
        """应用 LoRA 适配器"""
        print("🔧 应用 LoRA 适配器...")

        # 转换配置
        lora_config = PeftLoraConfig(
            r=self.config.lora.r,
            lora_alpha=self.config.lora.lora_alpha,
            target_modules=self.config.lora.target_modules,
            lora_dropout=self.config.lora.lora_dropout,
            bias=self.config.lora.bias,  # type: ignore[arg-type]
            task_type=self.config.lora.task_type,
        )

        self.model = get_peft_model(self.model, lora_config)  # type: ignore[arg-type]
        self.model.print_trainable_parameters()
        print()

    def prepare_data(self):
        """准备训练数据"""
        print("📊 准备数据集...")

        if self.config.data_path is None:
            raise ValueError("未指定数据路径 (data_path)")

        self.dataset = prepare_dataset(
            self.config.data_path,
            self.tokenizer,
            self.config.max_length,
        )
        print()

    def setup_trainer(self):
        """设置 Trainer"""
        print("⚙️  配置训练器...")

        # 训练参数
        training_args = TrainingArguments(
            output_dir=str(self.config.checkpoint_dir),
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            lr_scheduler_type=self.config.lr_scheduler_type,
            warmup_ratio=self.config.warmup_ratio,
            fp16=self.config.fp16,
            bf16=self.config.bf16,
            gradient_checkpointing=self.config.gradient_checkpointing,
            optim=self.config.optim,
            logging_steps=self.config.logging_steps,
            save_steps=self.config.save_steps,
            save_total_limit=self.config.save_total_limit,
            logging_dir=str(self.config.log_dir),
            report_to=self.config.report_to,
            dataloader_num_workers=self.config.dataloader_num_workers,
            seed=self.config.seed,
        )

        # 创建 Trainer
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=self.dataset,
            data_collator=DataCollatorForLanguageModeling(self.tokenizer, mlm=False),  # type: ignore[arg-type]
        )

        print("✅ 训练器配置完成")
        print(f"   • 有效 batch size: {self.config.effective_batch_size}")
        dataset_len = len(self.dataset) if self.dataset else 0  # type: ignore[arg-type]
        print(f"   • 总样本数: {dataset_len}")
        print(f"   • 训练轮数: {self.config.num_train_epochs}")
        estimated_steps = (
            dataset_len // self.config.effective_batch_size * self.config.num_train_epochs
        )
        print(f"   • 预计步数: ~{estimated_steps}")
        print()

    def train(self):
        """执行训练"""
        # 1. 加载模型
        if self.model is None:
            self.load_model_and_tokenizer()

        # 2. 应用 LoRA
        if not hasattr(self.model, "peft_config"):
            self.apply_lora()

        # 3. 准备数据
        if self.dataset is None:
            self.prepare_data()

        # 4. 设置训练器
        if self.trainer is None:
            self.setup_trainer()

        # 5. 开始训练
        print("🚀 开始训练...\n")
        print("💡 建议:")
        print("  • 在终端中运行以避免 VS Code 崩溃")
        print("  • 监控显存: watch -n 1 nvidia-smi")
        if self.config.load_in_8bit:
            print("  • 当前使用 8-bit 量化")
        if self.config.gradient_checkpointing:
            print("  • 当前启用梯度检查点")
        print()

        try:
            self.trainer.train()
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                print("\n❌ 显存不足 (OOM) 错误!")
                print("\n💡 建议:")
                print(
                    f"  1. 减小 max_length (当前 {self.config.max_length} -> {self.config.max_length // 2})"
                )
                print(f"  2. 减小 batch_size (当前 {self.config.per_device_train_batch_size})")
                if not self.config.load_in_8bit and not self.config.load_in_4bit:
                    print("  3. 启用量化: load_in_8bit=True")
                if not self.config.gradient_checkpointing:
                    print("  4. 启用梯度检查点: gradient_checkpointing=True")
                print(f"  5. 减小 LoRA rank (当前 {self.config.lora.r} -> 4)")
                sys.exit(1)
            else:
                raise

        # 6. 保存模型
        self.save_model()

        # 7. 显示完成信息
        self.print_completion_info()

    def save_model(self):
        """保存模型"""
        print("\n💾 保存模型...")

        # 保存 LoRA 权重
        self.model.save_pretrained(str(self.config.lora_dir))
        self.tokenizer.save_pretrained(str(self.config.lora_dir))

        # 保存配置
        self.config.save(self.config.output_dir / "training_config.json")

        print(f"✅ 模型已保存到: {self.config.lora_dir}")

    def print_completion_info(self):
        """打印完成信息"""
        print(f"\n{'=' * 60}")
        print("🎉 训练完成！")
        print(f"{'=' * 60}")
        print("\n📁 输出文件:")
        print(f"  • LoRA 权重: {self.config.lora_dir}")
        print(f"  • 检查点: {self.config.checkpoint_dir}")
        print(f"  • 训练日志: {self.config.log_dir}")
        print(f"  • 训练配置: {self.config.output_dir / 'training_config.json'}")
        print("\n💡 下一步操作:")
        print("  • 查看训练曲线:")
        print(f"    tensorboard --logdir {self.config.log_dir}")
        print("  • 合并权重:")
        print(f"    sage finetune merge {self.config.output_dir.name}")
        print("  • 测试模型:")
        print(f"    sage finetune chat {self.config.output_dir.name}")
        print()


def train_from_meta(output_dir: str | Path):
    """从元信息文件训练

    这个函数用于兼容旧的 simple_finetune.py 脚本

    Args:
        output_dir: 输出目录（包含 finetune_meta.json）

    Raises:
        FileNotFoundError: 当元信息文件不存在时
    """
    output_dir = Path(output_dir)

    # 读取元信息
    meta_file = output_dir / "finetune_meta.json"
    if not meta_file.exists():
        error_msg = f"❌ 未找到元信息文件: {meta_file}\n请先运行: sage finetune quickstart"
        print(error_msg)
        raise FileNotFoundError(error_msg)

    import json

    with open(meta_file) as f:
        meta = json.load(f)

    # 创建配置
    config = TrainingConfig(
        model_name=meta.get("model", "Qwen/Qwen2.5-Coder-1.5B-Instruct"),
        data_path=Path(meta.get("dataset")),
        output_dir=output_dir,
    )

    # 创建训练器并训练
    trainer = LoRATrainer(config)
    trainer.train()


if __name__ == "__main__":
    # 支持命令行调用
    if len(sys.argv) < 2:
        print("用法: python -m sage.libs.finetune.trainer <output_dir>")
        print("\n示例:")
        print("  python -m sage.libs.finetune.trainer finetune_output/code")
        sys.exit(1)

    try:
        train_from_meta(sys.argv[1])
    except FileNotFoundError:
        sys.exit(1)

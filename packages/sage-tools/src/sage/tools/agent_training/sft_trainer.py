"""Supervised fine-tuning trainer for agent dialogs."""

from __future__ import annotations

import logging
import sys
from typing import Optional

import torch
from datasets import Dataset
from peft import LoraConfig as PeftLoraConfig
from peft import get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)

# Import SIAS components from their new location
from sage.libs.sias import CoresetSelector, OnlineContinualLearner

from .config import AgentSFTConfig
from .dialog_processor import AgentDialogProcessor, ProcessedDialog

logger = logging.getLogger(__name__)


class AgentSFTTrainer:
    """Agent-specific LoRA SFT trainer optimized for 12GB GPUs."""

    def __init__(
        self,
        config: AgentSFTConfig,
        dialog_processor: Optional[AgentDialogProcessor] = None,
    ) -> None:
        self.config = config
        self.dialog_processor = dialog_processor or AgentDialogProcessor()
        self.model = None
        self.tokenizer = None
        self.train_dataset: Optional[Dataset] = None
        self.eval_dataset: Optional[Dataset] = None
        self.trainer: Optional[Trainer] = None
        self._train_samples: list[ProcessedDialog] = []
        self._eval_samples: list[ProcessedDialog] = []
        self.coreset_selector = self._build_coreset_selector()
        self.continual_learner = self._build_continual_learner()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def train(self) -> None:
        """Execute the complete SFT pipeline."""

        if self.model is None or self.tokenizer is None:
            self.load_model_and_tokenizer()

        if not hasattr(self.model, "peft_config"):
            self.apply_lora()

        if self.train_dataset is None:
            self.prepare_datasets()

        if self.trainer is None:
            self.setup_trainer()

        self._print_training_banner()

        try:
            self.trainer.train()
        except RuntimeError as err:  # pragma: no cover - runtime safeguard
            if "out of memory" in str(err).lower():
                self._handle_oom()
            raise

        self.save_model()
        self.print_completion_info()

    def load_model_and_tokenizer(self) -> None:
        """Load base model/tokenizer with quantization hints."""

        load_kwargs = self._build_quantization_kwargs()
        logger.info("Loading base model %s", self.config.base_model)
        self.model = AutoModelForCausalLM.from_pretrained(self.config.base_model, **load_kwargs)
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.base_model, use_fast=True)

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = self.config.padding_side

    def apply_lora(self) -> None:
        """Attach LoRA adapters with agent-friendly defaults."""

        if self.model is None:
            raise ValueError("Model must be loaded before applying LoRA")

        lora_config = PeftLoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            target_modules=self.config.lora_target_modules,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM",
        )
        self.model = get_peft_model(self.model, lora_config)  # type: ignore[arg-type]
        self.model.print_trainable_parameters()

    def prepare_datasets(self) -> None:
        """Process dialogs and tokenize into HF datasets."""

        if self.tokenizer is None:
            raise ValueError("Tokenizer must be loaded before preparing datasets")

        self._train_samples = self.dialog_processor.build_samples(
            self.config.train_data,
            limit=self.config.max_train_samples,
            output_format=self.config.output_format,
            task_weights=self.config.task_weights,
            shuffle=self.config.shuffle_train,
        )
        if not self._train_samples:
            raise ValueError("No training samples were produced")

        if self.coreset_selector and self.config.coreset_target_size:
            metrics = self._collect_metrics(self._train_samples, self.config.coreset_metric_key)
            self._train_samples = self.coreset_selector.select(
                self._train_samples,
                target_size=self.config.coreset_target_size,
                metrics=metrics,
            )

        if self.continual_learner:
            metrics = self._collect_metrics(self._train_samples, self.config.coreset_metric_key)
            self._train_samples = self.continual_learner.update_buffer(
                self._train_samples,
                metrics=metrics,
            )

        self._eval_samples = self.dialog_processor.build_samples(
            self.config.dev_data,
            limit=self.config.max_eval_samples,
            output_format=self.config.output_format,
            task_weights=None,
            shuffle=self.config.shuffle_eval,
        )

        self.train_dataset = self._tokenize_samples(self._train_samples)
        self.eval_dataset = (
            self._tokenize_samples(self._eval_samples) if self._eval_samples else None
        )
        self._log_dataset_stats()

    def setup_trainer(self) -> None:
        """Configure HuggingFace Trainer."""

        if self.model is None or self.tokenizer is None or self.train_dataset is None:
            raise ValueError("Model, tokenizer and dataset must be prepared before Trainer")

        evaluation_strategy = self.config.eval_strategy if self.eval_dataset is not None else "no"
        report_to = self.config.report_to if self.config.report_to != "none" else "none"

        training_args = TrainingArguments(
            output_dir=str(self.config.checkpoint_dir),
            num_train_epochs=self.config.num_epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation,
            learning_rate=self.config.learning_rate,
            warmup_ratio=self.config.warmup_ratio,
            lr_scheduler_type=self.config.lr_scheduler,
            logging_dir=str(self.config.log_dir),
            logging_steps=self.config.logging_steps,
            save_steps=self.config.save_steps,
            save_total_limit=self.config.save_total_limit,
            evaluation_strategy=evaluation_strategy,
            eval_steps=self.config.eval_steps,
            report_to=report_to,
            fp16=self.config.fp16,
            bf16=self.config.bf16,
            gradient_checkpointing=self.config.gradient_checkpointing,
            optim=self.config.optim,
            load_best_model_at_end=self.config.load_best_model,
            metric_for_best_model=self.config.metric_for_best_model,
            greater_is_better=self.config.greater_is_better,
            seed=self.config.seed,
            dataloader_num_workers=self.config.dataloader_num_workers,
        )

        data_collator = DataCollatorForLanguageModeling(self.tokenizer, mlm=False)

        self.training_args = training_args
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=self.train_dataset,
            eval_dataset=self.eval_dataset if evaluation_strategy != "no" else None,
            data_collator=data_collator,
        )

    def save_model(self) -> None:
        """Persist LoRA weights and tokenizer."""

        if self.model is None or self.tokenizer is None:
            raise ValueError("Model and tokenizer must exist to save")

        self.model.save_pretrained(str(self.config.lora_dir))
        self.tokenizer.save_pretrained(str(self.config.lora_dir))
        logger.info("Saved LoRA weights to %s", self.config.lora_dir)

    def print_completion_info(self) -> None:
        """Print helpful follow-up instructions."""

        divider = "=" * 60
        print(divider)
        print("🎉 Agent SFT training complete!")
        print(divider)
        print(f"LoRA weights: {self.config.lora_dir}")
        print(f"Checkpoints : {self.config.checkpoint_dir}")
        print(f"Logs        : {self.config.log_dir}")
        print("Next steps:")
        print(f"  • Merge weights: sage finetune merge {self.config.output_dir.name}")
        print(f"  • Chat:        sage finetune chat {self.config.output_dir.name}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_quantization_kwargs(self) -> dict:
        if self.config.load_in_8bit:
            return {
                "load_in_8bit": True,
                "device_map": "auto",
                "torch_dtype": torch.float16,
            }
        if self.config.load_in_4bit:
            from transformers import BitsAndBytesConfig

            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            return {"quantization_config": quant_config, "device_map": "auto"}
        return {"device_map": "auto", "torch_dtype": "auto"}

    def _tokenize_samples(self, samples: list[ProcessedDialog]) -> Dataset:
        dataset = Dataset.from_list([sample.to_record() for sample in samples])

        def tokenize(batch):
            tokenized = self.tokenizer(  # type: ignore[call-arg]
                batch["text"],
                truncation=True,
                max_length=self.config.max_length,
                padding=self.config.padding_strategy,
            )
            tokenized["labels"] = tokenized["input_ids"]
            return tokenized

        return dataset.map(tokenize, batched=True, remove_columns=dataset.column_names)

    def _log_dataset_stats(self) -> None:
        def summarize(samples: list[ProcessedDialog]) -> str:
            counts: dict[str, int] = {}
            for sample in samples:
                counts[sample.task_type] = counts.get(sample.task_type, 0) + 1
            return ", ".join(f"{task}: {count}" for task, count in sorted(counts.items()))

        logger.info(
            "Train samples: %d (%s)",
            len(self._train_samples),
            summarize(self._train_samples),
        )
        if self._eval_samples:
            logger.info(
                "Eval samples: %d (%s)",
                len(self._eval_samples),
                summarize(self._eval_samples),
            )

    def _print_training_banner(self) -> None:
        print("🚀 Starting Agent SFT training\n")
        print(f"Effective batch size : {self.config.effective_batch_size}")
        print(f"Train samples        : {len(self._train_samples)}")
        if self._eval_samples:
            print(f"Eval samples         : {len(self._eval_samples)}")
        print("Tips:")
        print("  • Monitor GPU memory: watch -n 1 nvidia-smi")
        if self.config.load_in_8bit:
            print("  • 8-bit loading enabled for RTX 3060 budgets")
        if self.config.gradient_checkpointing:
            print("  • Gradient checkpointing is ON")
        print()

    def _handle_oom(self) -> None:
        print("\n❌ Detected CUDA OOM. Suggestions:")
        print(f"  1. Reduce max_length (currently {self.config.max_length})")
        print(f"  2. Reduce batch_size (currently {self.config.batch_size})")
        print("  3. Increase gradient_accumulation")
        if not self.config.load_in_8bit and not self.config.load_in_4bit:
            print("  4. Enable 8-bit loading: load_in_8bit=True")
        if not self.config.gradient_checkpointing:
            print("  5. Enable gradient checkpointing")
        print()
        sys.exit(1)

    def _build_coreset_selector(self) -> Optional[CoresetSelector]:
        if not self.config.use_coreset_selection:
            return None
        return CoresetSelector(
            strategy=self.config.coreset_strategy,
            metric_key=self.config.coreset_metric_key,
            random_seed=self.config.seed,
        )

    def _build_continual_learner(self) -> Optional[OnlineContinualLearner]:
        if not self.config.use_online_continual:
            return None
        selector = self.coreset_selector or CoresetSelector(
            strategy="hybrid",
            metric_key=self.config.coreset_metric_key,
            random_seed=self.config.seed,
        )
        return OnlineContinualLearner(
            buffer_size=self.config.continual_buffer_size,
            replay_ratio=self.config.continual_replay_ratio,
            selector=selector,
            random_seed=self.config.seed,
        )

    def _collect_metrics(self, samples: list[ProcessedDialog], key: str) -> dict[str, float]:
        metrics: dict[str, float] = {}
        for sample in samples:
            value = sample.metadata.get(key)
            if isinstance(value, (int, float)):
                metrics[sample.dialog_id] = float(value)
        return metrics

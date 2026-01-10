"""Base classes and interfaces for finetune.

This module defines abstract interfaces for LLM fine-tuning:
- FineTuner: Core fine-tuning interface
- TrainingConfig: Training configuration
- LoRAConfig: LoRA-specific configuration
- DatasetLoader: Training data loading

Implementations are provided by the external 'isage-finetune' package.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional


@dataclass
class TrainingConfig:
    """Configuration for model fine-tuning."""

    # Model settings
    model_name_or_path: str
    output_dir: str

    # Training hyperparameters
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    per_device_eval_batch_size: int = 4
    learning_rate: float = 5e-5
    weight_decay: float = 0.01
    warmup_steps: int = 500

    # Optimization
    gradient_accumulation_steps: int = 1
    max_grad_norm: float = 1.0
    fp16: bool = False
    bf16: bool = False

    # Logging and checkpointing
    logging_steps: int = 10
    eval_steps: int = 500
    save_steps: int = 500
    save_total_limit: int = 3

    # Misc
    seed: int = 42
    report_to: list[str] = field(default_factory=lambda: ["tensorboard"])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.__dict__


@dataclass
class LoRAConfig:
    """Configuration for LoRA (Low-Rank Adaptation) fine-tuning."""

    r: int = 8  # Rank of update matrices
    lora_alpha: int = 16  # LoRA scaling factor
    target_modules: list[str] = None  # Modules to apply LoRA
    lora_dropout: float = 0.05
    bias: str = "none"  # "none", "all", or "lora_only"
    task_type: str = "CAUSAL_LM"  # "CAUSAL_LM", "SEQ_2_SEQ_LM", etc.

    def __post_init__(self):
        if self.target_modules is None:
            # Default: target query and value projections
            self.target_modules = ["q_proj", "v_proj"]


class FineTuner(ABC):
    """Abstract base class for LLM fine-tuning.

    Examples of implementations:
    - LoRA Trainer: Low-rank adaptation fine-tuning
    - Full Fine-tuning: Full parameter fine-tuning
    - QLoRA: Quantized LoRA (4-bit/8-bit)
    """

    @abstractmethod
    def train(
        self,
        train_dataset: Any,
        eval_dataset: Optional[Any] = None,
        config: Optional[TrainingConfig] = None,
    ) -> dict[str, Any]:
        """Train the model on the dataset.

        Args:
            train_dataset: Training dataset
            eval_dataset: Evaluation dataset (optional)
            config: Training configuration

        Returns:
            Training metrics dictionary containing:
              - train_loss: Final training loss
              - eval_loss: Final evaluation loss (if eval_dataset provided)
              - training_time: Total training time in seconds
        """
        pass

    @abstractmethod
    def evaluate(self, eval_dataset: Any) -> dict[str, float]:
        """Evaluate the model on a dataset.

        Args:
            eval_dataset: Evaluation dataset

        Returns:
            Evaluation metrics (loss, perplexity, etc.)
        """
        pass

    @abstractmethod
    def save_model(self, output_dir: str) -> None:
        """Save the fine-tuned model.

        Args:
            output_dir: Directory to save the model
        """
        pass

    @abstractmethod
    def load_model(self, model_path: str) -> None:
        """Load a fine-tuned model.

        Args:
            model_path: Path to the saved model
        """
        pass

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate text using the fine-tuned model (optional).

        Args:
            prompt: Input prompt
            **kwargs: Generation parameters (max_length, temperature, etc.)

        Returns:
            Generated text
        """
        raise NotImplementedError("generate() not implemented")


class DatasetLoader(ABC):
    """Abstract base class for training dataset loading.

    Examples of implementations:
    - HuggingFace Loader: Load from HuggingFace datasets
    - JSON Loader: Load from JSONL files
    - Agent Trajectory Loader: Load agent execution trajectories
    """

    @abstractmethod
    def load(self, data_path: str, **kwargs: Any) -> Any:
        """Load dataset from path.

        Args:
            data_path: Path to dataset file or directory
            **kwargs: Loader-specific parameters

        Returns:
            Loaded dataset (format depends on implementation)
        """
        pass

    @abstractmethod
    def preprocess(self, dataset: Any, tokenizer: Any) -> Any:
        """Preprocess dataset for training.

        Args:
            dataset: Raw dataset
            tokenizer: Tokenizer instance

        Returns:
            Preprocessed dataset ready for training
        """
        pass

    def stream(self, data_path: str, **kwargs: Any) -> Iterator[dict[str, Any]]:
        """Stream dataset samples (optional, for large datasets).

        Args:
            data_path: Path to dataset
            **kwargs: Loader-specific parameters

        Yields:
            Individual dataset samples
        """
        # Default: load all then iterate
        dataset = self.load(data_path, **kwargs)
        yield from dataset


__all__ = [
    "TrainingConfig",
    "LoRAConfig",
    "FineTuner",
    "DatasetLoader",
]

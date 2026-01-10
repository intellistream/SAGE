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


class TrainingCallback(ABC):
    """Abstract base class for training callbacks.

    Callbacks provide hooks into the training loop for:
    - Logging metrics
    - Early stopping
    - Learning rate scheduling
    - Custom checkpoint logic

    Examples of implementations:
    - WandBCallback: Log metrics to Weights & Biases
    - TensorBoardCallback: Log to TensorBoard
    - EarlyStoppingCallback: Stop training based on metrics
    """

    def on_train_begin(self, trainer: "FineTuner", **kwargs: Any) -> None:
        """Called at the start of training.

        Args:
            trainer: The trainer instance
            **kwargs: Additional training state
        """
        pass

    def on_train_end(self, trainer: "FineTuner", **kwargs: Any) -> None:
        """Called at the end of training.

        Args:
            trainer: The trainer instance
            **kwargs: Final training state and metrics
        """
        pass

    def on_epoch_begin(self, trainer: "FineTuner", epoch: int, **kwargs: Any) -> None:
        """Called at the start of each epoch.

        Args:
            trainer: The trainer instance
            epoch: Current epoch number (0-indexed)
            **kwargs: Additional state
        """
        pass

    def on_epoch_end(
        self, trainer: "FineTuner", epoch: int, metrics: dict[str, float], **kwargs: Any
    ) -> None:
        """Called at the end of each epoch.

        Args:
            trainer: The trainer instance
            epoch: Current epoch number
            metrics: Epoch metrics (loss, accuracy, etc.)
            **kwargs: Additional state
        """
        pass

    def on_step_begin(self, trainer: "FineTuner", step: int, **kwargs: Any) -> None:
        """Called at the start of each training step.

        Args:
            trainer: The trainer instance
            step: Global step number
            **kwargs: Batch data and state
        """
        pass

    def on_step_end(
        self, trainer: "FineTuner", step: int, loss: float, **kwargs: Any
    ) -> Optional[bool]:
        """Called at the end of each training step.

        Args:
            trainer: The trainer instance
            step: Global step number
            loss: Step loss value
            **kwargs: Gradients and additional state

        Returns:
            If True, stop training early. None or False to continue.
        """
        pass

    def on_evaluate(self, trainer: "FineTuner", metrics: dict[str, float], **kwargs: Any) -> None:
        """Called after evaluation.

        Args:
            trainer: The trainer instance
            metrics: Evaluation metrics
            **kwargs: Additional state
        """
        pass

    def on_save(self, trainer: "FineTuner", output_dir: str, **kwargs: Any) -> None:
        """Called when model is saved.

        Args:
            trainer: The trainer instance
            output_dir: Directory where model is saved
            **kwargs: Additional state
        """
        pass


class TrainingStrategy(ABC):
    """Abstract base class for training strategies.

    Strategies define HOW the model is fine-tuned:
    - Parameter-efficient methods (LoRA, QLoRA, Prefix Tuning)
    - Full fine-tuning
    - Distillation
    - Quantization-aware training

    Examples of implementations:
    - LoRAStrategy: Low-Rank Adaptation
    - QLoRAStrategy: 4-bit quantized LoRA
    - FullFTStrategy: Standard full fine-tuning
    - PrefixTuningStrategy: Prefix-tuning approach
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the strategy name (e.g., 'lora', 'qlora', 'full')."""
        pass

    @abstractmethod
    def prepare_model(self, model: Any, config: Optional["LoRAConfig"] = None) -> Any:
        """Prepare the model for this training strategy.

        Args:
            model: Base model to prepare
            config: Strategy-specific configuration (e.g., LoRAConfig)

        Returns:
            Model prepared for training with this strategy
        """
        pass

    @abstractmethod
    def get_trainable_parameters(self, model: Any) -> Iterator[Any]:
        """Get parameters that should be trained.

        Args:
            model: The prepared model

        Yields:
            Trainable parameters
        """
        pass

    def get_optimizer_grouped_parameters(
        self, model: Any, weight_decay: float = 0.01
    ) -> list[dict[str, Any]]:
        """Get parameter groups for optimizer (optional).

        By default, applies weight decay to all trainable parameters.
        Override for custom parameter grouping.

        Args:
            model: The prepared model
            weight_decay: Weight decay value

        Returns:
            List of parameter group dictionaries
        """
        trainable_params = list(self.get_trainable_parameters(model))
        return [{"params": trainable_params, "weight_decay": weight_decay}]

    def merge_and_unload(self, model: Any) -> Any:
        """Merge adapter weights into base model (for PEFT methods).

        Args:
            model: Model with adapter weights

        Returns:
            Model with merged weights (no adapter overhead)
        """
        # Default: return as-is (for non-PEFT strategies)
        return model


__all__ = [
    "TrainingConfig",
    "LoRAConfig",
    "FineTuner",
    "DatasetLoader",
    "TrainingCallback",
    "TrainingStrategy",
]

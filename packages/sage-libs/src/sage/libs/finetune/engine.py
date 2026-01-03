# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the SAGE project

"""Fine-tune engine for integrating with Control Plane (L3 implementation).

This module provides the FinetuneEngine class that integrates fine-tuning
capabilities into the Control Plane architecture. It wraps the existing
sage.libs.finetune.manager.FinetuneManager to provide engine lifecycle
management, progress tracking, and resource coordination.

Architecture:
    This is an L3 (sage-libs) implementation that can be used by the Control
    Plane (L1) through dynamic import. This follows the Kubernetes Controller
    pattern where the core defines interfaces and implementations register
    themselves.

    Control Plane (L1, sage-llm-core) manages fine-tune engines similar to LLM/embedding engines:
    - Start: Launch training process with specified model and dataset
    - Stop: Save checkpoint and gracefully stop training
    - Status: Track training progress (loss, epoch, ETA)
    - Resource coordination: Pause inference engines if GPU memory needed

Example:
    >>> from sage.libs.finetune.engine import FinetuneEngine, FinetuneConfig
    >>> from sage.llm.control_plane.types import EngineInfo
    >>>
    >>> # Create engine info
    >>> engine_info = EngineInfo(
    ...     engine_id="finetune-001",
    ...     model_id="Qwen/Qwen2.5-0.5B-Instruct",
    ...     host="localhost",
    ...     port=0,  # No HTTP endpoint for finetune
    ...     engine_kind="finetune",
    ... )
    >>>
    >>> # Create configuration
    >>> config = FinetuneConfig(
    ...     base_model="Qwen/Qwen2.5-0.5B-Instruct",
    ...     dataset_path="/path/to/dataset.json",
    ...     output_dir="/path/to/output",
    ...     lora_rank=8,
    ...     epochs=3,
    ... )
    >>>
    >>> # Create and start engine
    >>> engine = FinetuneEngine(engine_info=engine_info, config=config)
    >>> await engine.start()
    >>>
    >>> # Monitor progress
    >>> status = await engine.get_status()
    >>> print(f"Progress: {status['progress']}%, Loss: {status['loss']}")
    >>>
    >>> # Stop and save checkpoint
    >>> await engine.stop()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.llm.control_plane.types import EngineInfo, EngineState
else:
    # Runtime imports to avoid circular dependencies
    EngineInfo = Any
    EngineState = Any

logger = logging.getLogger(__name__)


@dataclass
class FinetuneConfig:
    """Configuration for a fine-tuning task.

    This dataclass contains all parameters needed to start a fine-tuning job,
    including model selection, dataset path, training hyperparameters, and
    output configuration.

    Attributes:
        base_model: Base model to fine-tune (e.g., "Qwen/Qwen2.5-7B-Instruct").
        dataset_path: Path to training dataset (JSON/JSONL format).
        output_dir: Directory to save checkpoints and final model.
        lora_rank: LoRA rank for parameter-efficient fine-tuning (default: 8).
        lora_alpha: LoRA alpha scaling factor (default: 16).
        learning_rate: Learning rate for training (default: 5e-5).
        epochs: Number of training epochs (default: 3).
        batch_size: Training batch size (default: 4).
        gradient_accumulation_steps: Steps to accumulate gradients (default: 4).
        max_seq_length: Maximum sequence length (default: 2048).
        use_flash_attention: Whether to use Flash Attention 2 (default: True).
        quantization_bits: Quantization bits (4, 8, or None for full precision).
        auto_download: Whether to auto-download base model if not found.
        metadata: Additional configuration metadata.
    """

    base_model: str
    dataset_path: str
    output_dir: str
    lora_rank: int = 8
    lora_alpha: int = 16
    learning_rate: float = 5e-5
    epochs: int = 3
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    max_seq_length: int = 2048
    use_flash_attention: bool = True
    quantization_bits: int | None = 4  # 4-bit quantization by default
    auto_download: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "base_model": self.base_model,
            "dataset_path": self.dataset_path,
            "output_dir": self.output_dir,
            "lora_rank": self.lora_rank,
            "lora_alpha": self.lora_alpha,
            "learning_rate": self.learning_rate,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "max_seq_length": self.max_seq_length,
            "use_flash_attention": self.use_flash_attention,
            "quantization_bits": self.quantization_bits,
            "auto_download": self.auto_download,
            "metadata": self.metadata,
        }


class FinetuneEngine:
    """Fine-tune engine that integrates with Control Plane.

    This class wraps sage.libs.finetune.manager.FinetuneManager to provide
    Control Plane-compatible engine lifecycle management for fine-tuning tasks.

    The engine lifecycle follows Control Plane patterns:
        1. STARTING: Engine is being initialized, training not yet started
        2. READY: Training is active and progressing
        3. DRAINING: Training is stopping, saving checkpoint
        4. STOPPED: Training completed or stopped
        5. ERROR: Training failed

    Attributes:
        engine_info: Control Plane engine registration info.
        config: Fine-tuning configuration parameters.
        task_id: Unique identifier for this fine-tuning task.
        _manager: Reference to FinetuneManager singleton.
        _training_task: Background asyncio task running the training loop.
        _start_time: Timestamp when training started.
        _stop_requested: Flag indicating stop has been requested.
    """

    def __init__(
        self,
        engine_info: EngineInfo,
        config: FinetuneConfig,
    ):
        """Initialize fine-tune engine.

        Args:
            engine_info: Control Plane engine registration info.
            config: Fine-tuning configuration parameters.
        """
        self.engine_info = engine_info
        self.config = config
        self.task_id = engine_info.engine_id
        self._manager = None  # Lazy-loaded FinetuneManager
        self._training_task: asyncio.Task | None = None
        self._start_time: datetime | None = None
        self._stop_requested = False

        logger.info(
            f"FinetuneEngine initialized: {self.task_id}, "
            f"model={config.base_model}, dataset={config.dataset_path}"
        )

    async def start(self) -> None:
        """Start the fine-tuning process.

        This method:
        1. Validates GPU resources are available
        2. Creates a fine-tune task in FinetuneManager
        3. Launches background training in asyncio task
        4. Updates engine state to READY

        Raises:
            RuntimeError: If GPU resources insufficient or training fails to start.
        """
        logger.info(f"Starting fine-tune engine: {self.task_id}")

        try:
            # Import EngineState at runtime
            # Import FinetuneManager from same package (L3 → L3, no violation!)
            from sage.libs.finetune.manager import FinetuneManager, check_gpu_resources
            from sage.llm.control_plane.types import EngineState

            # Check GPU resources before starting
            gpu_status = check_gpu_resources()
            if not gpu_status["available"]:
                error_msg = (
                    f"Insufficient GPU resources: {gpu_status.get('warning', 'Unknown error')}"
                )
                logger.error(error_msg)
                self.engine_info.state = EngineState.ERROR
                raise RuntimeError(error_msg)

            # Get FinetuneManager singleton
            self._manager = FinetuneManager()

            # Create fine-tune task
            output_path = Path(self.config.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            task = self._manager.create_task(
                model_name=self.config.base_model,
                dataset_path=self.config.dataset_path,
                output_dir=str(output_path),
                config={
                    "lora_rank": self.config.lora_rank,
                    "lora_alpha": self.config.lora_alpha,
                    "learning_rate": self.config.learning_rate,
                    "num_epochs": self.config.epochs,
                    "batch_size": self.config.batch_size,
                    "gradient_accumulation_steps": self.config.gradient_accumulation_steps,
                    "max_seq_length": self.config.max_seq_length,
                    "use_flash_attention_2": self.config.use_flash_attention,
                    "quantization_bit": self.config.quantization_bits,
                },
            )

            logger.info(f"Created fine-tune task: {task.task_id}")

            # Start training in background asyncio task
            self._training_task = asyncio.create_task(self._run_training())
            self._start_time = datetime.now()

            # Update engine state
            self.engine_info.state = EngineState.READY
            logger.info(f"Fine-tune engine started successfully: {self.task_id}")

        except Exception as e:
            logger.error(f"Failed to start fine-tune engine: {e}", exc_info=True)
            # Import EngineState if not already imported
            try:
                from sage.llm.control_plane.types import EngineState

                self.engine_info.state = EngineState.ERROR
            except ImportError:
                pass
            raise

    async def _run_training(self) -> None:
        """Background task that runs the training loop.

        This method wraps the synchronous FinetuneManager.start_training()
        method and runs it in a thread pool to avoid blocking the event loop.
        """
        try:
            # Import EngineState at runtime
            from sage.llm.control_plane.types import EngineState

            logger.info(f"Training loop started for task: {self.task_id}")

            # Run synchronous training in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,  # Use default thread pool
                self._manager.start_training,
                self.task_id,
            )

            # Training completed successfully
            logger.info(f"Training completed successfully: {self.task_id}")
            self.engine_info.state = EngineState.STOPPED

        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            try:
                from sage.llm.control_plane.types import EngineState

                self.engine_info.state = EngineState.ERROR
            except ImportError:
                pass

    async def stop(self, graceful: bool = True) -> None:
        """Stop the fine-tuning process.

        This method:
        1. Sets stop flag to prevent new work
        2. If graceful, waits for current epoch to finish
        3. Saves checkpoint at current state
        4. Cancels training task
        5. Updates engine state to STOPPED

        Args:
            graceful: If True, wait for current epoch before stopping.
        """
        logger.info(f"Stopping fine-tune engine: {self.task_id} (graceful={graceful})")

        # Import EngineState at runtime
        from sage.llm.control_plane.types import EngineState

        self._stop_requested = True
        self.engine_info.state = EngineState.DRAINING

        try:
            if self._manager:
                # Request training stop
                self._manager.stop_training(self.task_id, force=not graceful)

            # Wait for training task to finish (with timeout)
            if self._training_task and not self._training_task.done():
                try:
                    await asyncio.wait_for(self._training_task, timeout=30.0 if graceful else 5.0)
                except TimeoutError:
                    logger.warning(
                        f"Training task did not stop within timeout, canceling: {self.task_id}"
                    )
                    self._training_task.cancel()
                    try:
                        await self._training_task
                    except asyncio.CancelledError:
                        pass

            self.engine_info.state = EngineState.STOPPED
            logger.info(f"Fine-tune engine stopped: {self.task_id}")

        except Exception as e:
            logger.error(f"Error stopping fine-tune engine: {e}", exc_info=True)
            self.engine_info.state = EngineState.ERROR

    async def get_status(self) -> dict[str, Any]:
        """Get current training status and metrics.

        Returns:
            Dictionary containing:
            - state: Current engine state (STARTING/READY/DRAINING/STOPPED/ERROR)
            - progress: Training progress percentage (0-100)
            - current_epoch: Current training epoch
            - total_epochs: Total number of epochs
            - loss: Current training loss
            - eta_minutes: Estimated time remaining in minutes
            - gpu_memory_used_gb: GPU memory usage in GB
            - elapsed_time_seconds: Time elapsed since training started
            - logs: Recent log messages
        """
        status = {
            "engine_id": self.task_id,
            "state": self.engine_info.state.value
            if hasattr(self.engine_info.state, "value")
            else str(self.engine_info.state),
            "progress": 0.0,
            "current_epoch": 0,
            "total_epochs": self.config.epochs,
            "loss": 0.0,
            "eta_minutes": None,
            "gpu_memory_used_gb": None,
            "elapsed_time_seconds": None,
            "logs": [],
        }

        # Calculate elapsed time
        if self._start_time:
            elapsed = (datetime.now() - self._start_time).total_seconds()
            status["elapsed_time_seconds"] = round(elapsed, 2)

        # Get detailed status from FinetuneManager
        if self._manager:
            try:
                task = self._manager.get_task_status(self.task_id)
                if task:
                    status.update(
                        {
                            "state": task.status.value,
                            "progress": task.progress,
                            "current_epoch": task.current_epoch,
                            "total_epochs": task.total_epochs,
                            "loss": task.loss,
                            "logs": task.logs[-20:],  # Last 20 log lines
                        }
                    )

                    # Estimate time remaining
                    if status["progress"] > 0 and status["elapsed_time_seconds"]:
                        total_estimated = status["elapsed_time_seconds"] / (
                            status["progress"] / 100.0
                        )
                        remaining = total_estimated - status["elapsed_time_seconds"]
                        status["eta_minutes"] = round(remaining / 60.0, 1)

            except Exception as e:
                logger.warning(f"Failed to get detailed task status: {e}")

        # Get GPU memory usage
        try:
            import torch

            if torch.cuda.is_available():
                memory_allocated = torch.cuda.memory_allocated(0) / (1024**3)
                status["gpu_memory_used_gb"] = round(memory_allocated, 2)
        except Exception:
            pass

        return status

    async def health_check(self) -> bool:
        """Check if the fine-tune engine is healthy.

        Returns:
            True if training is progressing normally, False otherwise.
        """
        try:
            from sage.llm.control_plane.types import EngineState

            if self.engine_info.state in (EngineState.ERROR, EngineState.STOPPED):
                return False
        except ImportError:
            pass

        if self._training_task and self._training_task.done():
            # Check if task failed
            try:
                self._training_task.result()
            except Exception:
                return False

        return True

    async def cleanup(self) -> None:
        """Cleanup resources when engine is removed from Control Plane."""
        logger.info(f"Cleaning up fine-tune engine: {self.task_id}")

        try:
            from sage.llm.control_plane.types import EngineState

            # Ensure training is stopped
            if self.engine_info.state not in (EngineState.STOPPED, EngineState.ERROR):
                await self.stop(graceful=False)
        except ImportError:
            # If we can't import EngineState, just stop anyway
            await self.stop(graceful=False)

        # Cancel training task
        if self._training_task and not self._training_task.done():
            self._training_task.cancel()
            try:
                await self._training_task
            except asyncio.CancelledError:
                pass

        logger.info(f"Fine-tune engine cleanup complete: {self.task_id}")

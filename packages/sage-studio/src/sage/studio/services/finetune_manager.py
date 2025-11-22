"""
Fine-tune Task Manager for SAGE Studio

Manages fine-tuning tasks, progress tracking, and model switching.
"""

import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class FinetuneStatus(str, Enum):
    """Fine-tune task status"""

    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FinetuneTask:
    """Fine-tune task information"""

    task_id: str
    model_name: str
    dataset_path: str
    output_dir: str
    status: FinetuneStatus = FinetuneStatus.PENDING
    progress: float = 0.0  # 0-100
    current_epoch: int = 0
    total_epochs: int = 3
    loss: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    logs: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "model_name": self.model_name,
            "dataset_path": self.dataset_path,
            "output_dir": self.output_dir,
            "status": self.status.value,
            "progress": self.progress,
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "loss": self.loss,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error_message": self.error_message,
            "logs": self.logs[-50:],  # Last 50 logs
            "config": self.config,
        }


class FinetuneManager:
    """Singleton manager for fine-tuning tasks"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self.tasks: dict[str, FinetuneTask] = {}
            self.current_model: str = os.getenv("SAGE_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
            self.active_task_id: str | None = None
            self._initialized = True

            # Create output directory
            self.output_base = Path.home() / ".sage" / "studio_finetune"
            self.output_base.mkdir(parents=True, exist_ok=True)

            # Load existing tasks
            self._load_tasks()

    def _load_tasks(self):
        """Load existing tasks from disk"""
        task_file = self.output_base / "tasks.json"
        if task_file.exists():
            try:
                with open(task_file) as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = FinetuneTask(**task_data)
                        task.status = FinetuneStatus(task.status)
                        self.tasks[task.task_id] = task
                    self.current_model = data.get("current_model", "Qwen/Qwen2.5-7B-Instruct")
            except Exception as e:
                print(f"Failed to load tasks: {e}")

    def _save_tasks(self):
        """Save tasks to disk"""
        task_file = self.output_base / "tasks.json"
        try:
            data = {
                "tasks": [task.to_dict() for task in self.tasks.values()],
                "current_model": self.current_model,
            }
            with open(task_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save tasks: {e}")

    def create_task(
        self, model_name: str, dataset_path: str, config: dict[str, Any]
    ) -> FinetuneTask:
        """Create a new fine-tune task"""
        task_id = f"finetune_{int(time.time())}_{len(self.tasks)}"
        output_dir = str(self.output_base / task_id)

        task = FinetuneTask(
            task_id=task_id,
            model_name=model_name,
            dataset_path=dataset_path,
            output_dir=output_dir,
            config=config,
            total_epochs=config.get("num_epochs", 3),
        )

        self.tasks[task_id] = task
        self._save_tasks()
        return task

    def get_task(self, task_id: str) -> FinetuneTask | None:
        """Get task by ID"""
        return self.tasks.get(task_id)

    def list_tasks(self) -> list[FinetuneTask]:
        """List all tasks"""
        return sorted(self.tasks.values(), key=lambda t: t.created_at, reverse=True)

    def update_task_status(
        self,
        task_id: str,
        status: FinetuneStatus,
        progress: float | None = None,
        epoch: int | None = None,
        loss: float | None = None,
        error: str | None = None,
    ):
        """Update task status"""
        task = self.tasks.get(task_id)
        if not task:
            return

        task.status = status
        if progress is not None:
            task.progress = progress
        if epoch is not None:
            task.current_epoch = epoch
        if loss is not None:
            task.loss = loss
        if error:
            task.error_message = error

        if status == FinetuneStatus.TRAINING and not task.started_at:
            task.started_at = datetime.now().isoformat()
        elif status in (FinetuneStatus.COMPLETED, FinetuneStatus.FAILED):
            task.completed_at = datetime.now().isoformat()
            if self.active_task_id == task_id:
                self.active_task_id = None

        self._save_tasks()

    def add_task_log(self, task_id: str, log: str):
        """Add log entry to task"""
        task = self.tasks.get(task_id)
        if task:
            task.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log}")
            # Keep only last 100 logs
            if len(task.logs) > 100:
                task.logs = task.logs[-100:]

    def start_training(self, task_id: str) -> bool:
        """Start training in background thread"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        if self.active_task_id:
            return False  # Already training

        self.active_task_id = task_id
        thread = threading.Thread(target=self._train_worker, args=(task_id,))
        thread.daemon = True
        thread.start()
        return True

    def _train_worker(self, task_id: str):
        """Background worker for training"""
        task = self.tasks.get(task_id)
        if not task:
            return

        try:
            self.update_task_status(task_id, FinetuneStatus.PREPARING)
            self.add_task_log(task_id, "Preparing training environment...")

            # Import training modules
            from sage.tools.finetune import LoRATrainer, TrainingConfig

            self.add_task_log(task_id, "Loading training configuration...")

            # Create training config
            config = TrainingConfig(
                model_name=task.model_name,
                data_path=Path(task.dataset_path),
                output_dir=Path(task.output_dir),
                num_train_epochs=task.config.get("num_epochs", 3),
                per_device_train_batch_size=task.config.get("batch_size", 1),
                gradient_accumulation_steps=task.config.get("gradient_accumulation_steps", 16),
                learning_rate=task.config.get("learning_rate", 5e-5),
                max_length=task.config.get("max_length", 1024),
                load_in_8bit=task.config.get("load_in_8bit", True),
            )

            self.add_task_log(task_id, f"Base model: {task.model_name}")
            self.add_task_log(task_id, f"Dataset: {task.dataset_path}")
            self.add_task_log(task_id, f"Output: {task.output_dir}")

            self.update_task_status(task_id, FinetuneStatus.TRAINING, progress=5.0)
            self.add_task_log(task_id, "Starting training...")

            # Create trainer
            trainer = LoRATrainer(config)

            # Train (this will block)
            trainer.train()

            self.update_task_status(task_id, FinetuneStatus.COMPLETED, progress=100.0)
            self.add_task_log(task_id, "Training completed successfully!")
            self.add_task_log(task_id, f"Model saved to: {task.output_dir}")

        except Exception as e:
            self.update_task_status(task_id, FinetuneStatus.FAILED, error=str(e))
            self.add_task_log(task_id, f"Training failed: {e}")
            import traceback

            self.add_task_log(task_id, traceback.format_exc())

    def switch_model(self, model_path: str) -> bool:
        """Switch current model"""
        self.current_model = model_path
        os.environ["SAGE_CHAT_MODEL"] = model_path
        self._save_tasks()
        return True

    def get_current_model(self) -> str:
        """Get current model"""
        return self.current_model

    def list_available_models(self) -> list[dict[str, Any]]:
        """List available models (base + fine-tuned)"""
        models = [
            {
                "name": "Qwen/Qwen2.5-7B-Instruct",
                "type": "base",
                "description": "Default Qwen 2.5 7B model",
            }
        ]

        # Add fine-tuned models
        for task in self.tasks.values():
            if task.status == FinetuneStatus.COMPLETED:
                models.append(
                    {
                        "name": task.output_dir,
                        "type": "finetuned",
                        "description": f"Fine-tuned from {task.model_name}",
                        "task_id": task.task_id,
                        "created_at": task.completed_at,
                    }
                )

        return models


# Global instance
finetune_manager = FinetuneManager()

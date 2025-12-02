"""
Fine-tune Task Manager for SAGE Studio

Manages fine-tuning tasks, progress tracking, and model switching.
"""

import json
import os
import signal
import subprocess
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
    QUEUED = "queued"  # 等待 GPU 资源
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
    process_id: int | None = None  # 添加进程 ID 字段

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
            "process_id": self.process_id,  # 添加进程 ID
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
            # Default finetune base model (for UI display only, not for chat)
            # Chat will use IntelligentLLMClient's auto-detection
            self.current_model: str = os.getenv(
                "SAGE_FINETUNE_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct"
            )
            self.active_task_id: str | None = None
            self._initialized = True

            # Create output directory
            self.output_base = Path.home() / ".sage" / "studio_finetune"
            self.output_base.mkdir(parents=True, exist_ok=True)

            # Load existing tasks
            self._load_tasks()

            # 恢复训练中的任务状态
            self._recover_running_tasks()

    def _load_tasks(self):
        """Load existing tasks from disk (will merge with existing tasks in memory)"""
        task_file = self.output_base / "tasks.json"
        if task_file.exists():
            try:
                with open(task_file) as f:
                    data = json.load(f)
                    loaded_count = 0
                    for task_data in data.get("tasks", []):
                        task_id = task_data.get("task_id")
                        # 只加载内存中没有的任务（避免覆盖运行中任务的状态）
                        if task_id and task_id not in self.tasks:
                            task = FinetuneTask(**task_data)
                            task.status = FinetuneStatus(task.status)
                            self.tasks[task_id] = task
                            loaded_count += 1
                    self.current_model = data.get("current_model", "Qwen/Qwen2.5-7B-Instruct")
                print(
                    f"[FinetuneManager] Loaded {loaded_count} new tasks from {task_file} (total: {len(self.tasks)})"
                )
            except Exception as e:
                import traceback

                print(f"[FinetuneManager] Failed to load tasks: {e}")
                print(traceback.format_exc())

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

    def _recover_running_tasks(self):
        """恢复 Studio 重启前正在运行的任务"""
        for task_id, task in self.tasks.items():
            # 如果任务状态是 training/preparing，检查进程是否还在运行
            if task.status in (FinetuneStatus.TRAINING, FinetuneStatus.PREPARING):
                if task.process_id and self._is_process_running(task.process_id):
                    # 进程还在运行，启动监控线程
                    print(f"[FinetuneManager] 恢复任务 {task_id}，进程 PID={task.process_id}")
                    self.active_task_id = task_id
                    thread = threading.Thread(target=self._monitor_process, args=(task_id,))
                    thread.daemon = True
                    thread.start()
                else:
                    # 进程已停止，标记为失败
                    print(f"[FinetuneManager] 任务 {task_id} 进程已停止，标记为失败")
                    self.update_task_status(
                        task_id,
                        FinetuneStatus.FAILED,
                        error="Training process terminated (Studio restarted)",
                    )

    def _is_process_running(self, pid: int) -> bool:
        """检查进程是否还在运行"""
        try:
            # 发送信号 0 检查进程是否存在（不会真正发送信号）
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _monitor_process(self, task_id: str):
        """监控独立进程的状态"""
        task = self.tasks.get(task_id)
        if not task or not task.process_id:
            return

        try:
            # 定期检查进程状态和日志
            log_file = Path(task.output_dir) / "training.log"
            last_position = 0

            while self._is_process_running(task.process_id):
                # 读取新的日志内容
                if log_file.exists():
                    with open(log_file) as f:
                        f.seek(last_position)
                        new_logs = f.read()
                        last_position = f.tell()

                        if new_logs:
                            for line in new_logs.strip().split("\n"):
                                self.add_task_log(task_id, line)

                                # 解析进度信息
                                if "epoch" in line.lower():
                                    try:
                                        # 示例: "Epoch 2/3"
                                        parts = line.split("/")
                                        if len(parts) >= 2:
                                            current = int(parts[0].split()[-1])
                                            total = int(parts[1].split()[0])
                                            progress = (current / total) * 100
                                            self.update_task_status(
                                                task_id,
                                                FinetuneStatus.TRAINING,
                                                progress=progress,
                                                epoch=current,
                                            )
                                    except Exception:
                                        pass

                time.sleep(2)  # 每 2 秒检查一次

            # 进程结束，检查是否成功
            if log_file.exists():
                with open(log_file) as f:
                    content = f.read()
                    if "training completed" in content.lower() or "success" in content.lower():
                        self.update_task_status(task_id, FinetuneStatus.COMPLETED, progress=100.0)
                        self.add_task_log(task_id, "Training completed successfully!")
                    else:
                        self.update_task_status(
                            task_id,
                            FinetuneStatus.FAILED,
                            error="Training process exited unexpectedly",
                        )
                        self.add_task_log(task_id, "Training failed or was interrupted")
            else:
                self.update_task_status(task_id, FinetuneStatus.FAILED, error="No log file found")

        except Exception as e:
            self.update_task_status(task_id, FinetuneStatus.FAILED, error=str(e))
            self.add_task_log(task_id, f"Monitor error: {e}")

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
        """Get task by ID (with auto-reload if not found)"""
        task = self.tasks.get(task_id)
        if task is None:
            # 尝试重新加载任务（以防任务是在后端启动后创建的）
            print(f"[FinetuneManager] Task {task_id} not found in memory, reloading tasks...")
            self._load_tasks()
            task = self.tasks.get(task_id)
        return task

    def list_tasks(self) -> list[FinetuneTask]:
        """List all tasks (with runtime health check)"""
        # 检查正在运行的任务的进程健康状态
        for task in self.tasks.values():
            if task.status in (FinetuneStatus.TRAINING, FinetuneStatus.PREPARING):
                if task.process_id and not self._is_process_running(task.process_id):
                    # 进程已停止，标记为失败
                    print(
                        f"[FinetuneManager] 检测到任务 {task.task_id} 进程已终止 (PID={task.process_id})"
                    )
                    self.update_task_status(
                        task.task_id,
                        FinetuneStatus.FAILED,
                        error="Training process terminated unexpectedly",
                    )

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
                # 任务完成，尝试启动下一个排队任务
                self._start_next_queued_task()

        self._save_tasks()

    def _start_next_queued_task(self):
        """启动下一个排队任务"""
        # 查找第一个 QUEUED 状态的任务
        for task in sorted(self.tasks.values(), key=lambda t: t.created_at):
            if task.status == FinetuneStatus.QUEUED:
                print(f"[FinetuneManager] 启动排队任务: {task.task_id}")
                # 重置状态为 PENDING，然后启动
                task.status = FinetuneStatus.PENDING
                self.start_training(task.task_id)
                break

    def add_task_log(self, task_id: str, log: str):
        """Add log entry to task"""
        task = self.tasks.get(task_id)
        if task:
            task.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log}")
            # Keep only last 100 logs
            if len(task.logs) > 100:
                task.logs = task.logs[-100:]

    def start_training(self, task_id: str) -> bool:
        """Start training in independent process (survives Studio restart)"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        # 如果已有任务在运行，则加入队列
        if self.active_task_id:
            self.update_task_status(task_id, FinetuneStatus.QUEUED)
            self.add_task_log(
                task_id, f"任务已加入队列，等待 GPU 资源释放（当前运行: {self.active_task_id}）"
            )
            self._save_tasks()
            return True  # 返回 True 表示成功加入队列

        try:
            # 创建训练脚本
            script_path = self._create_training_script(task)

            # 启动独立进程
            log_file = Path(task.output_dir) / "training.log"
            log_file.parent.mkdir(parents=True, exist_ok=True)

            with open(log_file, "w") as f:
                process = subprocess.Popen(
                    ["python", str(script_path)],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,  # 创建新的进程组，脱离父进程
                )

            # 保存进程 ID
            task.process_id = process.pid
            self.active_task_id = task_id
            self.update_task_status(task_id, FinetuneStatus.PREPARING)
            self._save_tasks()

            # 启动监控线程
            thread = threading.Thread(target=self._monitor_process, args=(task_id,))
            thread.daemon = True
            thread.start()

            self.add_task_log(task_id, f"Training started in process PID={process.pid}")
            self.add_task_log(task_id, f"Log file: {log_file}")

            return True

        except Exception as e:
            self.update_task_status(task_id, FinetuneStatus.FAILED, error=str(e))
            self.add_task_log(task_id, f"Failed to start training: {e}")
            return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务（仅允许删除已完成、失败或取消的任务）"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        # 只允许删除非运行中的任务
        if task.status in (
            FinetuneStatus.TRAINING,
            FinetuneStatus.PREPARING,
            FinetuneStatus.QUEUED,
        ):
            print(f"[FinetuneManager] 无法删除运行中或排队中的任务: {task_id}")
            return False

        # 如果任务有输出目录，可选择删除
        # output_dir = Path(task.output_dir)
        # if output_dir.exists():
        #     import shutil
        #     shutil.rmtree(output_dir)

        # 从任务列表中删除
        del self.tasks[task_id]
        self._save_tasks()
        print(f"[FinetuneManager] 已删除任务: {task_id}")
        return True

    def cancel_task(self, task_id: str) -> bool:
        """取消运行中的任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        # 只能取消运行中或排队中的任务
        if task.status not in (
            FinetuneStatus.TRAINING,
            FinetuneStatus.PREPARING,
            FinetuneStatus.QUEUED,
        ):
            print(f"[FinetuneManager] 任务不在运行中，无需取消: {task_id}")
            return False

        # 如果任务在排队，直接标记为取消
        if task.status == FinetuneStatus.QUEUED:
            self.update_task_status(task_id, FinetuneStatus.CANCELLED)
            self.add_task_log(task_id, "任务已从队列中取消")
            return True

        # 如果任务正在运行，终止进程
        if task.process_id and self._is_process_running(task.process_id):
            try:
                os.kill(task.process_id, signal.SIGTERM)  # 发送终止信号
                self.add_task_log(task_id, f"已发送终止信号到进程 PID={task.process_id}")

                # 等待进程结束（最多5秒）
                for _ in range(10):
                    if not self._is_process_running(task.process_id):
                        break
                    time.sleep(0.5)

                # 如果进程还在运行，强制杀死
                if self._is_process_running(task.process_id):
                    os.kill(task.process_id, signal.SIGKILL)
                    self.add_task_log(task_id, f"强制终止进程 PID={task.process_id}")

                self.update_task_status(task_id, FinetuneStatus.CANCELLED)

                # 如果这是当前活动任务，清除并启动下一个
                if self.active_task_id == task_id:
                    self.active_task_id = None
                    self._start_next_queued_task()

                return True
            except Exception as e:
                self.add_task_log(task_id, f"取消任务失败: {e}")
                return False
        else:
            # 进程已经不在运行，直接标记为取消
            self.update_task_status(task_id, FinetuneStatus.CANCELLED)
            return True

    def _create_training_script(self, task: FinetuneTask) -> Path:
        """创建独立的训练脚本（带 OOM 保护）"""
        script_path = Path(task.output_dir) / "train.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)

        script_content = f'''"""
Auto-generated training script for task {task.task_id}
With OOM protection and auto-recovery
"""
import sys
import gc
import torch
from pathlib import Path
from sage.libs.finetune import LoRATrainer, TrainingConfig

def clear_gpu_memory():
    """清理 GPU 缓存"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()

def get_safe_config(base_config, gpu_memory_gb):
    """根据显存大小调整配置（OOM 保护）"""
    config = base_config.copy()

    # 根据显存调整 batch size
    if gpu_memory_gb < 8:
        config["per_device_train_batch_size"] = 1
        config["gradient_accumulation_steps"] = 32
        config["max_length"] = 512
    elif gpu_memory_gb < 12:
        config["per_device_train_batch_size"] = 1
        config["gradient_accumulation_steps"] = 16
        config["max_length"] = 1024
    elif gpu_memory_gb < 16:
        config["per_device_train_batch_size"] = 2
        config["gradient_accumulation_steps"] = 8
        config["max_length"] = 1024
    else:
        config["per_device_train_batch_size"] = 4
        config["gradient_accumulation_steps"] = 4
        config["max_length"] = 2048

    # 强制启用内存优化选项
    config["load_in_8bit"] = True
    config["gradient_checkpointing"] = True

    return config

def main():
    print("=" * 50)
    print("SAGE Fine-tuning Task: {task.task_id}")
    print("=" * 50)

    # 清理 GPU 缓存
    clear_gpu_memory()

    # 检测 GPU 显存
    gpu_memory_gb = 0
    if torch.cuda.is_available():
        gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"GPU: {{torch.cuda.get_device_name(0)}}")
        print(f"GPU Memory: {{gpu_memory_gb:.1f}} GB")
    else:
        print("WARNING: No GPU detected, using CPU (very slow!)")

    # 基础配置
    base_config = {{
        "num_train_epochs": {task.config.get("num_epochs", 3)},
        "per_device_train_batch_size": {task.config.get("batch_size", 1)},
        "gradient_accumulation_steps": {task.config.get("gradient_accumulation_steps", 16)},
        "learning_rate": {task.config.get("learning_rate", 5e-5)},
        "max_length": {task.config.get("max_length", 1024)},
        "load_in_8bit": {task.config.get("load_in_8bit", True)},
        "gradient_checkpointing": True,
    }}

    # 应用安全配置（OOM 保护）
    safe_config = get_safe_config(base_config, gpu_memory_gb)

    config = TrainingConfig(
        model_name="{task.model_name}",
        data_path=Path("{task.dataset_path}"),
        output_dir=Path("{task.output_dir}"),
        **safe_config
    )

    print(f"Base model: {task.model_name}")
    print(f"Dataset: {task.dataset_path}")
    print(f"Output: {task.output_dir}")
    print(f"Epochs: {{config.num_train_epochs}}")
    print(f"Batch size: {{config.per_device_train_batch_size}}")
    print(f"Gradient accumulation: {{config.gradient_accumulation_steps}}")
    print(f"Max length: {{config.max_length}}")
    print(f"8-bit quantization: {{config.load_in_8bit}}")
    print(f"Gradient checkpointing: {{config.gradient_checkpointing}}")
    print("=" * 50)

    try:
        trainer = LoRATrainer(config)

        # 训练前再次清理缓存
        clear_gpu_memory()

        trainer.train()

        # 训练后清理缓存
        clear_gpu_memory()

        print("=" * 50)
        print("Training completed successfully!")
        print(f"Model saved to: {task.output_dir}")
        print("=" * 50)
        return 0
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print("=" * 50)
            print("OOM ERROR: GPU out of memory!")
            print("Suggestions:")
            print("  1. Reduce batch_size to 1")
            print("  2. Reduce max_length to 512")
            print("  3. Increase gradient_accumulation_steps to 32")
            print("  4. Use a smaller model (0.5B instead of 1.5B)")
            print("=" * 50)
            clear_gpu_memory()
        else:
            print("=" * 50)
            print(f"Training failed: {{e}}")
            print("=" * 50)
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print("=" * 50)
        print(f"Training failed: {{e}}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''

        with open(script_path, "w") as f:
            f.write(script_content)

        return script_path

    def switch_model(self, model_path: str) -> bool:
        """Switch current model (for finetuning base model selection)

        Note: This only affects the finetuning UI's model selection.
        Chat mode will use IntelligentLLMClient's auto-detection (local first).
        """
        self.current_model = model_path
        # Removed: os.environ["SAGE_CHAT_MODEL"] = model_path
        # Chat should use auto-detection, not be affected by finetune settings
        self._save_tasks()
        return True

    def get_current_model(self) -> str:
        """Get current model"""
        return self.current_model

    def apply_finetuned_model(self, model_path: str) -> dict[str, Any]:
        """Apply a finetuned model to the running LLM service (hot-swap)

        This will restart the local LLM service with the new model.
        Gateway will automatically detect the new model.

        Args:
            model_path: Path to the finetuned model (local path or HF model name)

        Returns:
            Dict with status and message
        """
        from sage.studio.chat_manager import ChatModeManager

        try:
            # Get ChatModeManager instance
            chat_manager = ChatModeManager()

            # Check if LLM service is running
            if not chat_manager.llm_service or not chat_manager.llm_service.is_running():
                return {
                    "success": False,
                    "message": "本地 LLM 服务未运行。请先启动 Studio 的 LLM 服务。",
                }

            print(f"🔄 正在切换到微调模型: {model_path}")

            # Stop current LLM service
            print("   停止当前 LLM 服务...")
            chat_manager.llm_service.stop()

            # Update config with new model
            import time

            time.sleep(2)  # Wait for cleanup

            import os

            from sage.common.components.sage_llm import LLMAPIServer, LLMServerConfig

            config = LLMServerConfig(
                model=model_path,
                backend="vllm",
                host="0.0.0.0",
                port=8001,
                gpu_memory_utilization=float(os.getenv("SAGE_STUDIO_LLM_GPU_MEMORY", "0.9")),
                max_model_len=4096,
                disable_log_stats=True,
            )

            # Start new service with finetuned model
            print(f"   启动新模型: {model_path}")
            chat_manager.llm_service = LLMAPIServer(config)
            success = chat_manager.llm_service.start(background=True)

            if success:
                # Update current_model for UI display
                self.current_model = model_path
                self._save_tasks()

                print("✅ 模型切换成功！")
                print(f"   当前模型: {model_path}")
                print("   Gateway 会自动检测到新模型")

                return {
                    "success": True,
                    "message": f"成功切换到模型: {model_path}",
                    "model": model_path,
                }
            else:
                return {
                    "success": False,
                    "message": "LLM 服务启动失败，请查看日志",
                }

        except Exception as e:
            import traceback

            print(f"❌ 模型切换失败: {e}")
            print(traceback.format_exc())
            return {
                "success": False,
                "message": f"切换失败: {str(e)}",
            }

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

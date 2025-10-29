"""
Checkpoint 管理实现

负责任务状态的保存和恢复的具体实现。
"""

import os
import pickle
from pathlib import Path
from typing import Any

from sage.common.core import CheckpointError, TaskID


class CheckpointManagerImpl:
    """
    Checkpoint 管理器实现

    负责保存和恢复任务的状态快照。
    """

    def __init__(self, checkpoint_dir: str = ".sage/checkpoints"):
        """
        初始化 Checkpoint 管理器

        Args:
            checkpoint_dir: checkpoint 存储目录
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        task_id: TaskID,
        state: dict[str, Any],
        checkpoint_id: str | None = None,
    ) -> str:
        """
        保存 checkpoint

        Args:
            task_id: 任务 ID
            state: 要保存的状态字典
            checkpoint_id: checkpoint ID（如果为 None，使用时间戳）

        Returns:
            checkpoint 文件路径

        Raises:
            CheckpointError: 如果保存失败
        """
        try:
            # 生成 checkpoint ID
            if checkpoint_id is None:
                import time

                checkpoint_id = f"{int(time.time())}"

            # 构建文件路径
            checkpoint_path = self.checkpoint_dir / f"{task_id}_{checkpoint_id}.ckpt"

            # 保存状态
            with open(checkpoint_path, "wb") as f:
                pickle.dump(state, f)

            return str(checkpoint_path)

        except Exception as e:
            raise CheckpointError(f"Failed to save checkpoint for {task_id}: {e}")

    def load_checkpoint(
        self, task_id: TaskID, checkpoint_id: str | None = None
    ) -> dict[str, Any] | None:
        """
        加载 checkpoint

        Args:
            task_id: 任务 ID
            checkpoint_id: checkpoint ID（如果为 None，加载最新的）

        Returns:
            状态字典，如果不存在返回 None

        Raises:
            CheckpointError: 如果加载失败
        """
        try:
            if checkpoint_id:
                # 加载指定的 checkpoint
                checkpoint_path = self.checkpoint_dir / f"{task_id}_{checkpoint_id}.ckpt"
            else:
                # 加载最新的 checkpoint
                checkpoints = list(self.checkpoint_dir.glob(f"{task_id}_*.ckpt"))
                if not checkpoints:
                    return None
                checkpoint_path = max(checkpoints, key=os.path.getmtime)

            if not checkpoint_path.exists():
                return None

            # 加载状态
            with open(checkpoint_path, "rb") as f:
                return pickle.load(f)

        except Exception as e:
            raise CheckpointError(f"Failed to load checkpoint for {task_id}: {e}")

    def delete_checkpoint(self, task_id: TaskID, checkpoint_id: str | None = None):
        """
        删除 checkpoint

        Args:
            task_id: 任务 ID
            checkpoint_id: checkpoint ID（如果为 None，删除所有相关的）
        """
        try:
            if checkpoint_id:
                # 删除指定的 checkpoint
                checkpoint_path = self.checkpoint_dir / f"{task_id}_{checkpoint_id}.ckpt"
                if checkpoint_path.exists():
                    checkpoint_path.unlink()
            else:
                # 删除所有相关 checkpoint
                for ckpt in self.checkpoint_dir.glob(f"{task_id}_*.ckpt"):
                    ckpt.unlink()

        except Exception as e:
            raise CheckpointError(f"Failed to delete checkpoint for {task_id}: {e}")

    def list_checkpoints(self, task_id: TaskID) -> list[dict[str, Any]]:
        """
        列出任务的所有 checkpoint

        Args:
            task_id: 任务 ID

        Returns:
            checkpoint 信息列表
        """
        checkpoints = []

        for ckpt_path in self.checkpoint_dir.glob(f"{task_id}_*.ckpt"):
            # 提取 checkpoint ID
            filename = ckpt_path.stem  # task_id_checkpoint_id
            parts = filename.split("_")
            if len(parts) >= 2:
                checkpoint_id = "_".join(parts[1:])
            else:
                checkpoint_id = "unknown"

            checkpoints.append(
                {
                    "task_id": task_id,
                    "checkpoint_id": checkpoint_id,
                    "path": str(ckpt_path),
                    "size": ckpt_path.stat().st_size,
                    "mtime": ckpt_path.stat().st_mtime,
                }
            )

        # 按修改时间排序
        checkpoints.sort(key=lambda x: x["mtime"], reverse=True)

        return checkpoints

    def cleanup_old_checkpoints(self, task_id: TaskID, keep_last_n: int = 5):
        """
        清理旧的 checkpoint，只保留最新的 N 个

        Args:
            task_id: 任务 ID
            keep_last_n: 保留最新的 N 个 checkpoint
        """
        checkpoints = self.list_checkpoints(task_id)

        # 删除多余的 checkpoint
        for ckpt in checkpoints[keep_last_n:]:
            try:
                Path(ckpt["path"]).unlink()
            except Exception:
                pass

    def get_checkpoint_info(
        self, task_id: TaskID, checkpoint_id: str | None = None
    ) -> dict[str, Any] | None:
        """
        获取 checkpoint 信息

        Args:
            task_id: 任务 ID
            checkpoint_id: checkpoint ID（如果为 None，获取最新的）

        Returns:
            checkpoint 信息字典
        """
        if checkpoint_id:
            checkpoint_path = self.checkpoint_dir / f"{task_id}_{checkpoint_id}.ckpt"
        else:
            checkpoints = list(self.checkpoint_dir.glob(f"{task_id}_*.ckpt"))
            if not checkpoints:
                return None
            checkpoint_path = max(checkpoints, key=os.path.getmtime)

        if not checkpoint_path.exists():
            return None

        stat = checkpoint_path.stat()
        return {
            "task_id": task_id,
            "checkpoint_id": checkpoint_id,
            "path": str(checkpoint_path),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }


__all__ = ["CheckpointManagerImpl"]

"""
Python Queue Descriptor - Python标准库队列描述符

支持本地进程内队列（queue.Queue）和多进程队列（multiprocessing.Queue）
"""

from queue import Queue
from typing import Any, Optional

from .base_queue_descriptor import BaseQueueDescriptor


class PythonQueueDescriptor(BaseQueueDescriptor):
    """
    Python标准库队列描述符

    只支持 queue.Queue (本地进程内队列)
    """

    def __init__(
        self,
        maxsize: int = 0,
        use_multiprocessing: bool = False,
        queue_id: Optional[str] = None,
    ):
        """
        初始化Python队列描述符

        Args:
            maxsize: 队列最大大小，0表示无限制
            use_multiprocessing: 是否使用multiprocessing.Queue
            queue_id: 队列唯一标识符
        """
        self.maxsize = maxsize
        self.use_multiprocessing = use_multiprocessing
        self._initialized = False  # 是否已初始化队列实例
        super().__init__(queue_id=queue_id)

    @property
    def queue_type(self) -> str:
        """队列类型标识符"""
        return "python"

    @property
    def can_serialize(self) -> bool:
        return not self._initialized  # 未初始化时可以序列化

    @property
    def metadata(self) -> dict[str, Any]:
        """元数据字典"""
        base_metadata = {
            "maxsize": self.maxsize,
            "use_multiprocessing": self.use_multiprocessing,
        }

        # 只有在不可序列化时才包含队列实例引用
        if not self.can_serialize:
            base_metadata["queue_instance"] = self.queue_instance

        return base_metadata

    def clone(self, new_queue_id: Optional[str] = None) -> "PythonQueueDescriptor":
        """克隆描述符（共享队列实例以避免竞态条件）

        重要：如果原描述符已初始化队列实例，克隆体将共享同一个队列实例。
        这对于服务通信至关重要 - 服务端和客户端必须使用相同的队列实例，
        否则会导致间歇性超时（竞态条件）。

        Args:
            new_queue_id: 新的队列ID，如果为None则自动生成

        Returns:
            新的描述符实例，如果原实例已初始化则共享队列实例
        """
        # 创建同类型的新实例，保留原始配置
        cloned = PythonQueueDescriptor(
            maxsize=self.maxsize,  # 保留原始配置
            use_multiprocessing=self.use_multiprocessing,
            queue_id=new_queue_id,
        )

        # 【关键修复】共享队列实例，避免竞态条件
        # 如果原描述符已经初始化了队列实例，克隆体应该共享同一个实例
        # 这确保服务端和客户端使用相同的队列，防止响应丢失
        if self._initialized:
            cloned._queue_instance = self._queue_instance
            cloned._initialized = True

        return cloned

    @property
    def queue_instance(self) -> Any:
        """获取队列实例，如果未初始化则创建"""
        if not self._initialized:
            self._queue_instance = Queue(maxsize=self.maxsize)
            self._initialized = True
        return self._queue_instance

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PythonQueueDescriptor":
        """从字典创建实例"""
        metadata = data.get("metadata", {})
        instance = cls(
            maxsize=metadata.get("maxsize", 0),
            use_multiprocessing=metadata.get("use_multiprocessing", False),
            queue_id=data["queue_id"],
        )
        instance.created_timestamp = data.get("created_timestamp", instance.created_timestamp)
        return instance

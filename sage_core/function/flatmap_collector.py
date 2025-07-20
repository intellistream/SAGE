from typing import Optional, List, Any, Dict, Tuple
from sage_jobmanager.factory.runtime_context import RuntimeContext
from sage_runtime.router.base_router import BaseRouter
class Collector:
    """
    Enhanced Collector class for collecting data from a function.
    Supports both immediate emission and batched collection.
    """

    def __init__(self, ctx:RuntimeContext, router:BaseRouter):
        # 数据收集缓存
        self.ctx = ctx
        self._collected_data: List[Any] = []
        
        self.logger.debug(f"Collector initialized with batch_mode={self._batch_mode}") if self.logger else None
        
    def collect(self, data: Any):
        """
        Collect data. Behavior depends on batch_mode setting.
        
        Args:
            data: The data to collect
            tag: Optional output tag
        """
        # 批处理模式：先收集，后输出
        self._collected_data.append(data)
        self.logger.debug(f"Data collected in batch mode: {data} data")

    def get_collected_data(self) -> List[Any]:
        """
        Get all collected data.
        
        Returns:
            List[Any]: List of data tuples
        """
        return self._collected_data.copy()

    def get_collected_count(self) -> int:
        """
        Get the number of collected items.
        
        Returns:
            int: Number of collected items
        """
        return len(self._collected_data)

    def clear(self):
        """
        Clear all collected data.
        """
        count = len(self._collected_data)
        self._collected_data.clear()
        if self.logger and count > 0:
            self.logger.debug(f"Cleared {count} collected items")


    @property
    def logger(self):
        return self.ctx.logger
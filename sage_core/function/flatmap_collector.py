from typing import Optional, List, Any, Dict, Tuple
from sage_utils.custom_logger import CustomLogger


class Collector:
    """
    Enhanced Collector class for collecting data from a function.
    Supports both immediate emission and batched collection.
    """

    def __init__(self, operator=None, session_folder: str = None, name: str = None):
        self.operator = operator
        self.logger = CustomLogger(
            filename=f"Node_{name}",
            session_folder=session_folder,
            console_output=False,
            file_output=True,
            global_output=True,
            name=f"{name}_Collector"
        ) if name else None
        
        # 数据收集缓存
        self._collected_data: List[Any] = []
        self._batch_mode = True  # 默认启用批处理模式
        
        self.logger.debug(f"Collector initialized with batch_mode={self._batch_mode}") if self.logger else None

    def collect(self, data: Any):
        """
        Collect data. Behavior depends on batch_mode setting.
        
        Args:
            data: The data to collect
            tag: Optional output tag
        """
        if self._batch_mode:
            # 批处理模式：先收集，后输出
            self._collected_data.append(data)
            if self.logger:
                self.logger.debug(f"Data collected in batch mode: {data} data")
        else:
            # 即时模式：立即输出
            if self.operator:
                self.operator.emit(data)
                if self.logger:
                    self.logger.debug(f"Data emitted immediately: {data} data")
            else:
                # 没有operator，只能收集
                self._collected_data.append(data)
                if self.logger:
                    self.logger.warning(f"No operator set, data collected: {data} data")

    def collect_multiple(self, data_list: List[Any], tag: Optional[str] = None):
        """
        Collect multiple data items at once.
        
        Args:
            data_list: List of data items to collect
            tag: Optional output tag for all items
        """
        for data in data_list:
            self.collect(data)
        
        if self.logger:
            self.logger.debug(f"Collected {len(data_list)} items via collect_multiple")

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

    def flush(self):
        """
        Flush all collected data to the operator (emit all collected items).
        Only works when operator is set.
        """
        if not self.operator:
            if self.logger:
                self.logger.warning("Cannot flush: no operator set")
            return
        
        count = 0
        for data, tag in self._collected_data:
            try:
                self.operator.emitdata
                count += 1
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error emitting data during flush: {e}", exc_info=True)
        
        if self.logger:
            self.logger.debug(f"Flushed {count} items to operator")
        
        self.clear()

    def set_batch_mode(self, batch_mode: bool):
        """
        Set the batch mode for the collector.
        
        Args:
            batch_mode: True for batch mode, False for immediate mode
        """
        old_mode = self._batch_mode
        self._batch_mode = batch_mode
        if self.logger:
            self.logger.debug(f"Batch mode changed from {old_mode} to {batch_mode}")

    def is_batch_mode(self) -> bool:
        """
        Check if collector is in batch mode.
        
        Returns:
            bool: True if in batch mode, False otherwise
        """
        return self._batch_mode

    def set_operator(self, operator):
        """
        Set the operator for this collector.
        
        Args:
            operator: The operator instance
        """
        self.operator = operator
        if self.logger:
            self.logger.debug(f"Operator set: {operator.__class__.__name__}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get collector statistics.
        
        Returns:
            Dict[str, Any]: Statistics dictionary
        """
        tag_counts = {}
        for _, tag in self._collected_data:
            tag_key = tag if tag is not None else "default"
            tag_counts[tag_key] = tag_counts.get(tag_key, 0) + 1
        
        return {
            "total_collected": len(self._collected_data),
            "batch_mode": self._batch_mode,
            "has_operator": self.operator is not None,
            "tag_distribution": tag_counts
        }

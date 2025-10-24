from typing import Any


class Collector:
    """
    Enhanced Collector class for collecting data from a function.
    Supports both immediate emission and batched collection.
    """

    def __init__(self, *args, **kwargs):
        self._collected_data: list[Any] = []
        self.logger: Any = kwargs.get("logger")  # Can be Logger or CustomLogger

    def collect(self, data: Any):
        """
        Collect data. Behavior depends on batch_mode setting.

        Args:
            data: The data to collect
            tag: Optional output tag
        """
        # 批处理模式：先收集，后输出
        self._collected_data.append(data)
        if self.logger:
            self.logger.debug(f"Data collected in batch mode: {data} data")

    def get_collected_data(self) -> list[Any]:
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

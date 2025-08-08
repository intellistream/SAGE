from abc import abstractmethod
from typing import Any, List, Tuple, Type, Iterable, Optional, Union
from sage.core.api.function.base_function import BaseFunction
from sage.core.api.function.flatmap_collector import Collector



class FlatMapFunction(BaseFunction):
    """
    FlatMapFunction is a specialized function for FlatMap operations.
    It provides an 'out' collector for emitting multiple output values.
    
    This function supports two usage patterns:
    1. Use self.collect() to emit individual items
    2. Return an iterable object that will be automatically flattened
    
    Example usage:
        # Pattern 1: Using self.collect()
        def execute(self, data):
            words = data.value.split()
            for word in words:
                self.collect(word)
        
        # Pattern 2: Return iterable
        def execute(self, data):
            words = data.value.split()
            return words
    """
    
    def __init__(self, *args, **kwargs):
        self.out: Optional[Collector] = None

    def insert_collector(self, collector: Collector):
        """
        Insert a collector into the function for data collection.
        This method is called by the operator to provide the collector.
        
        Args:
            collector: The collector instance to be inserted.
        """
        self.out = collector
        self.out.logger = self.logger
        self.logger.debug(f"Collector inserted into FlatMapFunction '{self.__class__.__name__}'")

    def collect(self, data: Any):
        """
        Convenience method to collect data using the out collector.
        
        Args:
            data: The data to collect
            tag: Optional output tag
        """
        if self.out is None:
            raise RuntimeError("Collector not initialized. This should be set by the operator.")
        
        self.out.collect(data)
        self.logger.debug(f"Data collected: {data}")

    @abstractmethod
    def execute(self, data: Any) -> Optional[Iterable[Any]]:
        """
        Abstract method to be implemented by subclasses.
        
        Args:
            data: 输入数据，可以是裸数据或Data封装
            
        Returns:
            Optional[Iterable[Any]]: Optional iterable of output data
        """
        pass


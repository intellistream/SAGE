from abc import abstractmethod
from typing import Any, List, Tuple, Type, Iterable, Optional, Union
from sage_core.api.base_function import BaseFunction
from sage_core.api.collector import Collector
from sage_core.api.tuple import Data


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
                self.collect(Data(word))
        
        # Pattern 2: Return iterable
        def execute(self, data):
            words = data.value.split()
            return [Data(word) for word in words]
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.out: Optional[Collector] = None
        self.logger.debug(f"FlatMapFunction '{self.__class__.__name__}' initialized")

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

    def collect(self, data: Any, tag: Optional[str] = None):
        """
        Convenience method to collect data using the out collector.
        
        Args:
            data: The data to collect
            tag: Optional output tag
        """
        if self.out is None:
            raise RuntimeError("Collector not initialized. This should be set by the operator.")
        
        self.out.collect(data, tag)
        self.logger.debug(f"Data collected: {data}")

    def collect_multiple(self, data_list: Iterable[Any], tag: Optional[str] = None):
        """
        Convenience method to collect multiple data items at once.
        
        Args:
            data_list: Iterable of data items to collect
            tag: Optional output tag
        """
        if self.out is None:
            raise RuntimeError("Collector not initialized. This should be set by the operator.")
        
        count = 0
        for item in data_list:
            self.out.collect(item, tag)
            count += 1
        
        self.logger.debug(f"Collected {count} items via collect_multiple")

    @abstractmethod
    def execute(self, data: Union[Any, Data]) -> Optional[Iterable[Any]]:
        """
        Abstract method to be implemented by subclasses.
        
        Args:
            data: 输入数据，可以是裸数据或Data封装
            
        Returns:
            Optional[Iterable[Any]]: Optional iterable of output data
        """
        pass

    @classmethod
    def declare_outputs(cls) -> List[Tuple[str, Type]]:
        """
        Default output declaration for FlatMap functions.
        Can be overridden by subclasses for multiple outputs.
        
        Returns:
            List[Tuple[str, Type]]: List of output declarations
        """
        return [("default", Any)]

    @classmethod
    def declare_inputs(cls) -> List[Tuple[str, Type]]:
        """
        Default input declaration for FlatMap functions.
        Can be overridden by subclasses for multiple inputs.
        
        Returns:
            List[Tuple[str, Type]]: List of input declarations
        """
        return [("default", Any)]


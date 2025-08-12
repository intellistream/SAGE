from abc import abstractmethod
from typing import Any

from .base_function import BaseFunction


class BaseCoMapFunction(BaseFunction):
    """
    Base class for CoMap functions that process multiple inputs separately.
    
    CoMap functions are used with ConnectedStreams to process each input stream
    independently using dedicated mapN methods (map0, map1, map2, etc.).
    
    Unlike regular functions that merge all inputs into a single execute() call,
    CoMap functions maintain stream boundaries and process each input through
    its corresponding mapN method.
    """
    
    @property 
    def is_comap(self) -> bool:
        """Identify this as a CoMap function for operator routing"""
        return True
    
    @abstractmethod
    def map0(self, data: Any) -> Any:
        """
        Process data from input stream 0 (required)
        
        Args:
            data: Data from the first input stream
            
        Returns:
            Processed result for stream 0
        """
        pass
    
    @abstractmethod
    def map1(self, data: Any) -> Any:
        """
        Process data from input stream 1 (required)
        
        Args:
            data: Data from the second input stream
            
        Returns:
            Processed result for stream 1
        """
        pass
    
    def map2(self, data: Any) -> Any:
        """
        Process data from input stream 2 (optional)
        
        Args:
            data: Data from the third input stream
            
        Returns:
            Processed result for stream 2
        """
        return None
    
    def map3(self, data: Any) -> Any:
        """
        Process data from input stream 3 (optional)
        
        Args:
            data: Data from the fourth input stream
            
        Returns:
            Processed result for stream 3
        """
        return None
    
    def map4(self, data: Any) -> Any:
        """
        Process data from input stream 4 (optional)
        
        Args:
            data: Data from the fifth input stream
            
        Returns:
            Processed result for stream 4
        """
        return None
    
    def execute(self, data: Any) -> Any:
        """
        Standard execute method for compatibility with BaseFunction interface.
        
        For CoMap functions, this should not be called directly - the CoMapOperator
        will route to specific mapN methods based on input_index.
        
        Args:
            data: Input data
            
        Returns:
            Never returns - always raises NotImplementedError
            
        Raises:
            NotImplementedError: Always, since CoMap functions use mapN methods
        """
        raise NotImplementedError(
            f"CoMap function {self.__class__.__name__} should use mapN methods, "
            f"not execute(). This is handled by CoMapOperator."
        )

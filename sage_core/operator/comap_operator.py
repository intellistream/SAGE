from .base_operator import BaseOperator
from typing import Union, Any
from sage_utils.custom_logger import CustomLogger
from sage_runtime.io.packet import Packet


class CoMapOperator(BaseOperator):
    """
    CoMap操作符 - 处理多输入流的分别处理操作
    
    CoMapOperator专门用于处理CoMap函数，它会根据输入的input_index
    直接路由到相应的mapN方法，而不是使用统一的execute方法。
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 验证函数类型（在运行时初始化后进行）
        self._validate_function()
        self._validated = True

    
    def _validate_function(self) -> None:
        """
        验证函数是否为CoMap函数
        
        Raises:
            TypeError: 如果函数不是CoMap函数
        """
        if not hasattr(self.function, 'is_comap') or not self.function.is_comap:
            raise TypeError(
                f"{self.__class__.__name__} requires CoMap function with is_comap=True, "
                f"got {type(self.function).__name__}"
            )
        
        # 验证必需的map0和map1方法
        required_methods = ['map0', 'map1']
        for method_name in required_methods:
            if not hasattr(self.function, method_name):
                raise TypeError(
                    f"CoMap function {type(self.function).__name__} must implement {method_name} method"
                )
        
        self.logger.debug(f"Validated CoMap function {type(self.function).__name__}")
    
    def process(self, raw_data: Any = None, input_index: int = 0) -> Any:
        """
        处理数据，根据input_index路由到相应的mapN方法
        
        Args:
            raw_data: 输入数据
            input_index: 输入流索引，决定调用哪个mapN方法
            
        Returns:
            处理后的结果
            
        Raises:
            NotImplementedError: 如果对应的mapN方法未实现
        """
        if not self._validated:
            raise RuntimeError("CoMapOperator not properly initialized.")
        
        if raw_data is None:
            self.logger.warning(f"CoMapOperator {self.name} received empty data for input_index {input_index}")
            return None
        
        try:
            # 根据input_index构造方法名
            method_name = f"map{input_index}"
            
            # 检查方法是否存在
            if not hasattr(self.function, method_name):
                raise NotImplementedError(
                    f"Method {method_name} not implemented for CoMap function "
                    f"{self.function.__class__.__name__}. Available input streams: 0-{self._get_max_supported_index()}"
                )
            
            # 获取并调用对应的mapN方法
            method = getattr(self.function, method_name)
            result = method(raw_data)
            
            self.logger.debug(
                f"CoMapOperator {self.name} processed data via {method_name} with result: {result}"
            )
            
            return result
            
        except NotImplementedError:
            # 重新抛出NotImplementedError，不包装
            raise
        except Exception as e:
            self.logger.error(
                f"Error in {self.name}.process() calling {method_name}: {e}", 
                exc_info=True
            )
            raise
    
    def _get_max_supported_index(self) -> int:
        """
        获取支持的最大输入流索引
        
        Returns:
            int: 最大支持的输入流索引
        """
        max_index = -1
        index = 0
        
        # 检查有多少个mapN方法被实现
        while True:
            method_name = f"map{index}"
            if hasattr(self.function, method_name):
                try:
                    # 尝试调用方法看是否抛出NotImplementedError
                    method = getattr(self.function, method_name)
                    # 检查方法是否为抽象方法或抛出NotImplementedError
                    if not getattr(method, '__isabstractmethod__', False):
                        max_index = index
                except:
                    # 如果获取方法时出错，停止检查
                    break
                index += 1
            else:
                break
        
        return max_index
    
    def get_supported_input_methods(self) -> list[str]:
        """
        获取所有支持的mapN方法列表
        
        Returns:
            list[str]: 支持的方法名列表
        """
        methods = []
        index = 0
        
        while True:
            method_name = f"map{index}"
            if hasattr(self.function, method_name):
                method = getattr(self.function, method_name)
                if not getattr(method, '__isabstractmethod__', False):
                    methods.append(method_name)
                index += 1
            else:
                break
        
        return methods
    
    def __repr__(self) -> str:
        if hasattr(self, 'function') and self.function:
            function_name = self.function.__class__.__name__
            if self._validated:
                max_index = self._get_max_supported_index()
                return f"<{self.__class__.__name__} {function_name} supports:0-{max_index}>"
            else:
                return f"<{self.__class__.__name__} {function_name} (not validated)>"
        else:
            return f"<{self.__class__.__name__} (no function)>"

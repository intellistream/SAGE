from typing import Callable, Any, List, Tuple, Type, Optional, Hashable
from sage.core.function.base_function import BaseFunction
from sage.core.function.map_function import MapFunction
from sage.core.function.filter_function import FilterFunction
from sage.core.function.flatmap_function import FlatMapFunction
from sage.core.function.sink_function import SinkFunction
from sage.core.function.source_function import SourceFunction
from sage.core.function.keyby_function import KeyByFunction
import inspect

class LambdaMapFunction(MapFunction):
    """将 lambda 函数包装为 MapFunction"""
    
    def __init__(self, lambda_func: Callable[[Any], Any], **kwargs):
        self.lambda_func = lambda_func
    
    def execute(self, data: Any) -> Any:
        return self.lambda_func(data)
    
class LambdaFilterFunction(FilterFunction):
    """将返回布尔值的 lambda 函数包装为 FilterFunction"""
    
    def __init__(self, lambda_func: Callable[[Any], bool], **kwargs):
        self.lambda_func = lambda_func
    
    def execute(self, data: Any) -> bool:
        return self.lambda_func(data)
    
class LambdaFlatMapFunction(FlatMapFunction):
    """将返回列表的 lambda 函数包装为 FlatMapFunction"""
    
    def __init__(self, lambda_func: Callable[[Any], List[Any]], **kwargs):
        self.lambda_func = lambda_func
    
    def execute(self, data: Any) -> List[Any]:
        result = self.lambda_func(data)
        if not isinstance(result, list):
            raise TypeError(f"FlatMap lambda function must return a list, got {type(result)}")
        return result
    
class LambdaSinkFunction(SinkFunction):
    """将 lambda 函数包装为 SinkFunction"""
    
    def __init__(self, lambda_func: Callable[[Any], None], **kwargs):
        self.lambda_func = lambda_func
    
    def execute(self, data: Any) -> None:
        self.lambda_func(data)

class LambdaSourceFunction(BaseFunction):
    """将无参数 lambda 函数包装为 SourceFunction"""
    
    def __init__(self, lambda_func: Callable[[], Any], **kwargs):
        self.lambda_func = lambda_func
    
    def execute(self) -> Any:
        return self.lambda_func()

class LambdaKeyByFunction(KeyByFunction):
    """
    Wrapper for lambda-based key extraction.
    
    Example:
        # For lambda x: x.user_id
        extractor = LambdaKeyByFunction(lambda x: x.user_id)
    """
    
    def __init__(self, lambda_func, **kwargs):
        self.lambda_func = lambda_func
        self.logger.debug(f"LambdaKeyByFunction initialized with lambda")

    def execute(self, data: Any) -> Hashable:
        """
        Execute lambda function on data.
        
        Args:
            data: Input data
            
        Returns:
            Hashable: Result of lambda function
        """
        try:
            return self.lambda_func(data)
        except Exception as e:
            self.logger.error(f"Lambda key extraction failed: {e}")
            raise





def detect_lambda_type(func: Callable) -> str:
    """
    根据 lambda 函数的签名和返回类型注解检测其类型
    
    Args:
        func: lambda 函数
        
    Returns:
        函数类型: 'map', 'filter', 'flatmap', 'sink', 'source'
    """
    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        return_annotation = sig.return_annotation
        
        # 无参数 -> source
        if len(params) == 0:
            return 'source'
        
        # 有参数但非单参数 -> 暂不支持
        if len(params) != 1:
            raise ValueError(f"Lambda function must have 0 or 1 parameter, got {len(params)}")
        
        # 根据返回类型注解判断
        if return_annotation == bool:
            return 'filter'
        elif hasattr(return_annotation, '__origin__') and return_annotation.__origin__ == list:
            return 'flatmap'
        elif return_annotation == type(None) or return_annotation is None:
            return 'sink'
        else:
            # 默认为 map
            return 'map'
    except Exception:
        # 如果无法检测，默认为 map
        return 'map'
    





def wrap_lambda(func: Callable, func_type: str = None) -> Type[BaseFunction]:
    """
    将 lambda 函数包装为对应的 Function 类
    
    Args:
        func: lambda 函数
        func_type: 强制指定函数类型，如果为 None 则自动检测
        
    Returns:
        包装后的 Function 类
    """
    if func_type is None:
        func_type = detect_lambda_type(func)
    
    if func_type == 'map':
        class WrappedMapFunction(LambdaMapFunction):
            def __init__(self, **kwargs):
                super().__init__(func, **kwargs)
        return WrappedMapFunction
    
    elif func_type == 'filter':
        class WrappedFilterFunction(LambdaFilterFunction):
            def __init__(self, **kwargs):
                super().__init__(func, **kwargs)
        return WrappedFilterFunction
    
    elif func_type == 'flatmap':
        class WrappedFlatMapFunction(LambdaFlatMapFunction):
            def __init__(self, **kwargs):
                super().__init__(func, **kwargs)
        return WrappedFlatMapFunction
    
    elif func_type == 'sink':
        class WrappedSinkFunction(LambdaSinkFunction):
            def __init__(self, **kwargs):
                super().__init__(func, **kwargs)
        return WrappedSinkFunction
    
    elif func_type == 'source':
        class WrappedSourceFunction(LambdaSourceFunction):
            def __init__(self, **kwargs):
                super().__init__(func, **kwargs)
        return WrappedSourceFunction
    
    elif func_type == 'keyby':
        class WrappedKeyByFunction(LambdaKeyByFunction):
            def __init__(self, **kwargs):
                super().__init__(func, **kwargs)
        return WrappedKeyByFunction

    else:
        raise ValueError(f"Unsupported function type: {func_type}")
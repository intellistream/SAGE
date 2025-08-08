from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage.core.transformation.base_transformation import BaseTransformation
if TYPE_CHECKING:
    from sage.core.api.function.comap_function import BaseCoMapFunction
    from sage.core.api.base_environment import BaseEnvironment


class CoMapTransformation(BaseTransformation):
    """
    CoMap变换 - 多输入流分别处理变换
    
    CoMap变换用于处理ConnectedStreams，将每个输入流分别路由到
    对应的mapN方法进行处理，而不是将所有输入合并到单一方法。
    """
    
    def __init__(
        self,
        env: 'BaseEnvironment',
        function: Type['BaseCoMapFunction'],
        *args,
        **kwargs
    ):
        # 验证函数是否为CoMap函数
        if not hasattr(function, 'is_comap') or not function.is_comap:
            raise ValueError(f"Function {function.__name__} is not a CoMap function. "
                           f"CoMap functions must inherit from BaseCoMapFunction and have is_comap=True.")
        
        # 验证必需的map0和map1方法
        self._validate_required_methods(function)
        
        # 导入operator类（延迟导入避免循环依赖）
        from sage.core.operator.comap_operator import CoMapOperator
        self.operator_class = CoMapOperator
        
        super().__init__(env, function, *args, **kwargs)
        
        self.logger.debug(f"Created CoMapTransformation with function {function.__name__}")
    
    def _validate_required_methods(self, function_class: Type['BaseCoMapFunction']) -> None:
        """
        验证CoMap函数是否实现了必需的方法
        
        Args:
            function_class: CoMap函数类
            
        Raises:
            ValueError: 如果缺少必需的方法
        """
        required_methods = ['map0', 'map1']
        missing_methods = []
        
        for method_name in required_methods:
            if not hasattr(function_class, method_name):
                missing_methods.append(method_name)
            else:
                method = getattr(function_class, method_name)
                # 检查是否为抽象方法（未实现）
                if getattr(method, '__isabstractmethod__', False):
                    missing_methods.append(method_name)
        
        if missing_methods:
            raise ValueError(
                f"CoMap function {function_class.__name__} must implement required methods: "
                f"{', '.join(missing_methods)}"
            )
    
    @property
    def supported_input_count(self) -> int:
        """
        获取支持的输入流数量
        
        Returns:
            int: 支持的最大输入流数量
        """
        count = 0
        method_index = 0
        
        # 检查有多少个mapN方法被实现
        while True:
            method_name = f"map{method_index}"
            if hasattr(self.function_class, method_name):
                method = getattr(self.function_class, method_name)
                # 如果方法存在且不是抽象方法
                if not getattr(method, '__isabstractmethod__', False):
                    count += 1
                    method_index += 1
                else:
                    break
            else:
                break
        
        return count
    
    def validate_input_streams(self, input_count: int) -> None:
        """
        验证输入流数量是否匹配
        
        Args:
            input_count: 实际输入流数量
            
        Raises:
            ValueError: 如果输入流数量超过支持的数量
        """
        supported_count = self.supported_input_count
        
        if input_count > supported_count:
            raise ValueError(
                f"CoMap function {self.function_class.__name__} supports maximum "
                f"{supported_count} input streams, but {input_count} streams provided. "
                f"Please implement map{supported_count} through map{input_count-1} methods."
            )
        
        if input_count < 2:
            raise ValueError(
                f"CoMap transformation requires at least 2 input streams, "
                f"but only {input_count} provided."
            )
    
    def __repr__(self) -> str:
        cls_name = self.function_class.__name__
        supported_inputs = self.supported_input_count
        return (f"<{self.__class__.__name__} {cls_name} "
                f"supports:{supported_inputs} streams at {hex(id(self))}>")

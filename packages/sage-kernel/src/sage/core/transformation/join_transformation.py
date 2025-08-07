from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage.core.transformation.base_transformation import BaseTransformation
if TYPE_CHECKING:
    from sage.core.api.function.join_function import BaseJoinFunction
    from sage.core.api.base_environment import BaseEnvironment


class JoinTransformation(BaseTransformation):
    """
    Join变换 - 多输入流按键关联变换
    
    Join变换用于处理ConnectedStreams，将来自不同输入流的具有
    相同分区键的数据进行关联处理，生成join结果。
    """
    
    def __init__(
        self,
        env: 'BaseEnvironment',
        function: Type['BaseJoinFunction'],
        *args,
        **kwargs
    ):
        # 验证函数是否为Join函数
        if not hasattr(function, 'is_join') or not function.is_join:
            raise ValueError(f"Function {function.__name__} is not a Join function. "
                           f"Join functions must inherit from BaseJoinFunction and have is_join=True.")
        
        # 验证必需的execute方法
        self._validate_required_methods(function)
        
        # 导入operator类（延迟导入避免循环依赖）
        from sage.core.operator.join_operator import JoinOperator
        self.operator_class = JoinOperator
        
        super().__init__(env, function, *args, **kwargs)
        
        self.logger.debug(f"Created JoinTransformation with function {function.__name__}")
    
    def _validate_required_methods(self, function_class: Type['BaseJoinFunction']) -> None:
        """
        验证Join函数是否实现了必需的方法
        
        Args:
            function_class: Join函数类
            
        Raises:
            ValueError: 如果缺少必需的方法
        """
        required_methods = ['execute']
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
                f"Join function {function_class.__name__} must implement required methods: "
                f"{', '.join(missing_methods)}"
            )
        
        # 验证execute方法的签名
        self._validate_execute_signature(function_class)
    
    def _validate_execute_signature(self, function_class: Type['BaseJoinFunction']) -> None:
        """
        验证execute方法的签名是否正确
        
        Args:
            function_class: Join函数类
            
        Raises:
            ValueError: 如果方法签名不正确
        """
        import inspect
        
        try:
            execute_method = getattr(function_class, 'execute')
            signature = inspect.signature(execute_method)
            params = list(signature.parameters.keys())
            
            # 期望的参数：self, payload, key, tag
            expected_params = ['self', 'payload', 'key', 'tag']
            
            if len(params) < len(expected_params):
                raise ValueError(
                    f"Join function {function_class.__name__}.execute() must accept parameters: "
                    f"{', '.join(expected_params[1:])}. Got: {', '.join(params[1:])}"
                )
            
            # 检查前几个参数名是否匹配（允许额外参数）
            for i, expected_param in enumerate(expected_params):
                if i < len(params) and params[i] != expected_param:
                    self.logger.warning(
                        f"Join function {function_class.__name__}.execute() parameter {i} "
                        f"expected '{expected_param}', got '{params[i]}'. "
                        f"This may cause runtime issues."
                    )
                    
        except Exception as e:
            self.logger.warning(f"Could not validate execute method signature: {e}")
    
    @property
    def supported_input_count(self) -> int:
        """
        获取支持的输入流数量
        
        对于Join操作，目前支持2个输入流
        
        Returns:
            int: 支持的输入流数量 (固定为2)
        """
        return 2  # Join操作目前只支持2个输入流
    
    @property
    def max_supported_streams(self) -> int:
        """
        获取理论上支持的最大输入流数量
        
        可以通过检查join function的实现来动态确定，
        但目前固定为2流join
        
        Returns:
            int: 最大支持的输入流数量
        """
        # 未来可以扩展为多流join，现在固定为2
        return 2
    
    def validate_input_streams(self, input_count: int) -> None:
        """
        验证输入流数量是否匹配
        
        Args:
            input_count: 实际输入流数量
            
        Raises:
            ValueError: 如果输入流数量不匹配
        """
        supported_count = self.supported_input_count
        max_supported = self.max_supported_streams
        
        if input_count != supported_count:
            raise ValueError(
                f"Join function {self.function_class.__name__} requires exactly "
                f"{supported_count} input streams, but {input_count} streams provided."
            )
        
        if input_count > max_supported:
            raise ValueError(
                f"Join transformation supports maximum {max_supported} input streams, "
                f"but {input_count} streams provided. "
                f"Consider using multiple join operations for more complex scenarios."
            )
        
        if input_count < 2:
            raise ValueError(
                f"Join transformation requires at least 2 input streams, "
                f"but only {input_count} provided."
            )
    
    def validate_keyed_streams(self, stream_transformations: List['BaseTransformation']) -> None:
        """
        验证所有输入流都是keyed的
        
        Args:
            stream_transformations: 输入流的transformation列表
            
        Raises:
            ValueError: 如果有流没有被keyed
        """
        from sage.core.transformation.keyby_transformation import KeyByTransformation
        
        for i, transformation in enumerate(stream_transformations):
            # 检查是否是KeyByTransformation或者其下游
            if not self._is_keyed_stream(transformation):
                raise ValueError(
                    f"Join requires all input streams to be keyed. "
                    f"Stream {i} (transformation: {transformation.function_class.__name__}) "
                    f"is not keyed. Use .keyby() before .join()"
                )
    
    def _is_keyed_stream(self, transformation: 'BaseTransformation') -> bool:
        """
        检查transformation是否产生keyed stream
        
        Args:
            transformation: 要检查的transformation
            
        Returns:
            bool: 是否为keyed stream
        """
        from sage.core.transformation.keyby_transformation import KeyByTransformation
        
        # 直接是KeyByTransformation
        if isinstance(transformation, KeyByTransformation):
            return True
        
        # 检查上游是否有KeyByTransformation
        current = transformation
        visited = set()
        
        while current and id(current) not in visited:
            visited.add(id(current))
            
            if isinstance(current, KeyByTransformation):
                return True
            
            # 检查直接上游
            if current.upstreams:
                # 对于合并操作，所有上游都应该是keyed的
                if len(current.upstreams) == 1:
                    current = current.upstreams[0]
                else:
                    # 多个上游，检查是否都是keyed的
                    return all(self._is_keyed_stream(upstream) for upstream in current.upstreams)
            else:
                break
        
        return False
    
    @property
    def is_merge_operation(self) -> bool:
        """
        Join是特殊的合并操作，需要区分输入流
        
        Returns:
            bool: False，表示不是普通的合并操作
        """
        return False  # Join需要区分不同的输入流
    
    def get_join_configuration(self) -> Dict[str, Any]:
        """
        获取Join配置信息
        
        Returns:
            Dict[str, Any]: Join配置字典
        """
        return {
            "function_class": self.function_class.__name__,
            "supported_inputs": self.supported_input_count,
            "max_inputs": self.max_supported_streams,
            "is_keyed_required": True,
            "join_type": getattr(self.function_class, 'join_type', 'custom'),
            "function_args": self.function_args,
            "function_kwargs": self.function_kwargs
        }
    
    def debug_print_join_info(self) -> None:
        """打印Join配置调试信息"""
        config = self.get_join_configuration()
        print(f"\n🔗 JoinTransformation '{self.basename}' Configuration:")
        print(f"   Function: {config['function_class']}")
        print(f"   Supported inputs: {config['supported_inputs']}")
        print(f"   Max inputs: {config['max_inputs']}")
        print(f"   Requires keyed streams: {config['is_keyed_required']}")
        print(f"   Join type: {config['join_type']}")
        if config['function_args']:
            print(f"   Function args: {config['function_args']}")
        if config['function_kwargs']:
            print(f"   Function kwargs: {config['function_kwargs']}")
        print(f"   Upstreams: {[up.basename for up in self.upstreams]}")
    
    def __repr__(self) -> str:
        cls_name = self.function_class.__name__
        supported_inputs = self.supported_input_count
        join_type = getattr(self.function_class, 'join_type', 'custom')
        return (f"<{self.__class__.__name__} {cls_name} "
                f"type:{join_type} inputs:{supported_inputs} at {hex(id(self))}>")
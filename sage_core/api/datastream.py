from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List, Tuple, TypeVar, Generic, get_args, get_origin
from sage_core.api.enum import PlatformType
from sage_core.api.transformation import TransformationType, Transformation
from sage_core.api.base_function import BaseFunction
from .connected_streams import ConnectedStreams
from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:
    from .env import BaseEnvironment
    from .datastream import DataStream

T = TypeVar("T")


class DataStream(Generic[T]):
    """表示单个transformation生成的流结果"""
    def __init__(self, env:BaseEnvironment, transformation: Transformation):
        self.logger = CustomLogger(
            filename=f"Datastream_{transformation.function_class.__name__}",
            env_name = env.name,
            console_output="WARNING",
            file_output=True,
            global_output = "DEBUG",
        )
        self._environment = env
        self.transformation = transformation
        self._type_param = self._resolve_type_param()

        self.logger.debug(f"DataStream created with transformation: {transformation.function_class.__name__}, type_param: {self._type_param}")


    # ---------------------------------------------------------------------
    # 内部帮助：把新 Transformation 接入管线
    # ---------------------------------------------------------------------
    def _apply(self, tr: Transformation) -> "DataStream":

        # 连接到第一个输入
        tr.add_upstream(self.transformation)
        
        self._environment._pipeline.append(tr)
        return DataStream(self._environment, tr)
    
    # ---------------------------------------------------------------------
    # 表示对于当前 DataStream 的变换操作，生成变换算子的第一个输出 Datastream
    # ---------------------------------------------------------------------
    def map(
        self, 
        function: Union[BaseFunction, Type[BaseFunction] ],
        *args, 
        platform: PlatformType = PlatformType.LOCAL,
        name: str = None,
        **kwargs
    ) -> "DataStream":
        
        tr = Transformation(
            self._environment,
            TransformationType.MAP, 
            function,
            *args,
            platform = platform,
            name = name,
            **kwargs)
        return self._apply(tr)

    def filter(
        self, 
        function: Union[BaseFunction, Type[BaseFunction]],
        *args, 
        platform: PlatformType = PlatformType.LOCAL,
        name: str = None,
        **kwargs
    ) -> "DataStream":
        """
        对数据流进行过滤操作
        
        Args:
            function: 过滤函数，应该是FilterFunction的子类
            *args: 传递给function的位置参数
            platform: 运行平台类型
            name: 操作名称
            **kwargs: 传递给function的关键字参数
            
        Returns:
            DataStream: 过滤后的数据流
        """
        tr = Transformation(
            self._environment,
            TransformationType.FILTER, 
            function,
            *args,
            platform = platform,
            name = name,
            **kwargs)
        return self._apply(tr)

    def flatmap(
        self, 
        function: Union[BaseFunction, Type[BaseFunction]],
        *args, 
        platform: PlatformType = PlatformType.LOCAL,
        name: str = None,
        **kwargs
    ) -> "DataStream":
        """
        对数据流进行扁平化映射操作
        
        Args:
            function: 扁平化映射函数，应该是FlatMapFunction的子类
            *args: 传递给function的位置参数
            platform: 运行平台类型
            name: 操作名称
            **kwargs: 传递给function的关键字参数
            
        Returns:
            DataStream: 扁平化映射后的数据流
        """
        tr = Transformation(
            self._environment,
            TransformationType.FLATMAP, 
            function,
            *args,
            platform = platform,
            name = name,
            **kwargs)
        return self._apply(tr)



    # ---------------------------------------------------------------------
    # 表示对于当前 DataStream 进行输出
    # ---------------------------------------------------------------------
    def sink(
        self, 
        function: Union[BaseFunction, Type[BaseFunction]],
        *args, 
        platform:  PlatformType    = PlatformType.LOCAL,
        name:      str             = None,
        **kwargs
    ) -> "DataStream":
        
        tr = Transformation(
            self._environment,
            TransformationType.SINK, 
            function,
            *args,
            platform = platform,
            name = name, 
            **kwargs
            )
        return self._apply(tr)

    def connect(self, other: "DataStream") -> 'ConnectedStreams':
        """连接两个数据流，返回ConnectedStreams"""
        return ConnectedStreams(self._environment, [
            self.transformation,
            other.transformation
        ])

    def _resolve_type_param(self):
        # 利用 __orig_class__ 捕获 T
        orig = getattr(self, "__orig_class__", None)
        if orig and get_origin(orig) == DataStream:
            return get_args(orig)[0]
        else:
            return Any  # fallback，如果泛型没有显式写就为 None

# 目前没支持filter 和 flatmap，因为connected streams整体还需要重做


from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, List, Tuple
from sage_core.api.enum import PlatformType
from sage_core.api.transformation import TransformationType, Transformation
from sage_core.api.base_function import BaseFunction

# datastream应该描述多个算子的流结果
# 核心数据结构为：[(transformation1, o3), (transformation2, o2), ...]
# 然后在创建下游运算new_transformation时，会把(t1,o3)接入到(new_t,i1), (t2,o2)接入到(new_t, i2)中。
# 所以说我们在transformation中，需要维护它的每一个输出channel会供给的多个下游


class DataStream:
    """表示单个transformation生成的流结果"""
    def __init__(self, env, transformation: Transformation, output_tag: str = None):
        self._environment = env
        self.transformation = transformation
        
        if output_tag is None:
            # 使用默认输出标签（第一个）
            self.output_tag = transformation.function_class.declare_outputs()[0][0]
        else:
            # 验证输出标签是否有效
            declared_tags = [tag for tag, _ in transformation.function_class.declare_outputs()]
            if output_tag not in declared_tags:
                raise ValueError(f"Output tag '{output_tag}' is not declared in function {transformation.function_class.__name__}")
            self.output_tag = output_tag


    # ---------------------------------------------------------------------
    # 内部帮助：把新 Transformation 接入管线
    # ---------------------------------------------------------------------
    def _apply(self, tr: Transformation) -> "DataStream":
        # 从tr.function_class.declare_inputs中获取输出标签列表
        # 然后和self.transformations中的每一个transformation输出标签进行匹配
        # 输入可以少于function desired inputs数量，但是不能多
        declared_inputs = tr.function_class.declare_inputs()  # ["in1", "in2", ...]
        if len(declared_inputs) == 0:
            raise ValueError(f"Function {tr.function_class.__name__} declares no inputs but is being connected")

        # 连接到第一个输入
        input_tag = declared_inputs[0][0]
        tr.add_upstream(input_tag=input_tag, upstream_trans=self.transformation, upstream_tag=self.output_tag)
        
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

    def side_output(self, output_tag:str):
        """获取该transformation的指定输出标签的数据流"""
        declared_tags = [tag for tag, _ in self.transformation.function_class.declare_outputs()]
        if output_tag not in declared_tags:
            raise ValueError(f"Output tag '{output_tag}' is not declared in function {self.transformation.function_class.__name__}")
        
        return DataStream(self._environment, self.transformation, output_tag)

    def connect(self, other: "DataStream") -> "ConnectedStreams":
        """连接两个数据流，返回ConnectedStreams"""
        return ConnectedStreams(self._environment, [
            (self.transformation, self.output_tag),
            (other.transformation, other.output_tag)
        ])


# 目前没支持filter 和 flatmap，因为connected streams整体还需要重做

class ConnectedStreams:
    """表示多个transformation连接后的流结果"""
    def __init__(self, env, transformations: List[Tuple[Transformation, str]]):
        self._environment = env
        self.transformations = transformations

    def _apply(self, tr: Transformation) -> "DataStream":
        """将新 Transformation 接入管线"""
        declared_inputs = tr.function_class.declare_inputs()
        
        if len(self.transformations) > len(declared_inputs):
            raise ValueError(
                f"Too many upstream connections: "
                f"{len(self.transformations)} provided vs {len(declared_inputs)} expected in {tr.function_class.__name__}"
            )

        # 按顺序连接每个上游transformation到对应的输入
        for (upstream_trans, output_tag), (input_tag, input_type) in zip(self.transformations, declared_inputs):
            tr.add_upstream(input_tag=input_tag, upstream_trans=upstream_trans, upstream_tag=output_tag)

        self._environment._pipeline.append(tr)
        return DataStream(self._environment, tr)

    def map(self, function: Union[BaseFunction, Type[BaseFunction]], *args, **kwargs) -> "DataStream":
        tr = Transformation(self._environment,TransformationType.MAP, function, *args, **kwargs)
        return self._apply(tr)

    def sink(self, function: Union[BaseFunction, Type[BaseFunction]], *args, **kwargs) -> "DataStream":
        tr = Transformation(self._environment, TransformationType.SINK, function, *args, **kwargs)
        return self._apply(tr)

    def connect(self, other: Union["DataStream", "ConnectedStreams"]) -> "ConnectedStreams":
        """连接更多数据流"""
        if isinstance(other, DataStream):
            new_transformations = self.transformations + [(other.transformation, other.output_tag)]
        else:  # ConnectedStreams
            new_transformations = self.transformations + other.transformations
        
        return ConnectedStreams(self._environment, new_transformations)
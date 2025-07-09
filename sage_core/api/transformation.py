# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from enum import Enum
from sage_core.api.base_function import BaseFunction
# from sage_core.api.env import BaseEnvironment
from sage_core.core.operator.map_operator import MapOperator
from sage_utils.custom_logger import CustomLogger
from sage_core.api.enum import PlatformType
from sage_utils.name_server import get_name
if TYPE_CHECKING:
    from sage_core.core.operator.base_operator import BaseOperator



class TransformationType(Enum):
    MAP = "map"
    FILTER = "filter"
    FLATMAP = "flatmap"
    SINK = "sink"
    SOURCE = "source"

class Transformation:
    TO_OPERATOR = {
        TransformationType.MAP: MapOperator,
        # TODO: 添加其他transformation类型的映射
        # TransformationType.FILTER: FilterOperator,
        # TransformationType.FLATMAP: FlatMapOperator,
        TransformationType.SINK: MapOperator,
        TransformationType.SOURCE: MapOperator,
    }
    def __init__(
        self,
        # env, # :BaseEnvironment,
        type: TransformationType,
        function: Type[BaseFunction],
        *args,
        name:str = None,
        parallelism: int = 1,
        platform:PlatformType = PlatformType.LOCAL,
        **kwargs
    ):
        #self.env = env
        self.type = type
        if isinstance(function, Type):
            self.is_instance = False
            self.function = None
            self.function_class = function
        else:
            raise ValueError(
                f"Unsupported rag type: {type(function)}"
            )


        if name is None:
            self.basename = get_name(self.function_class.__name__)
        else:
            self.basename = get_name(name)
        # self.basename = get_name(name) or get_name(self.function_class.__name__)
        # 这个basename会沿用到生成的dagnode， operator和functions上

        self.logger = CustomLogger(
            filename=get_name(f"Transformation_{self.basename}"),
            console_output=False,
            file_output=True
        )
        self.logger.debug(f"Creating Transformation of type {type} with rag {self.function_class.__name__}")
        # 创建OperatorFactory来处理operator的创建
        self.operator_class = self.TO_OPERATOR.get(type, None)

        self.operator_factory = OperatorFactory(
            operator_class=self.operator_class,
            function_class=self.function_class,
            function_args=args,
            function_kwargs=kwargs,  # 将kwargs传递给function
            is_spout = self.is_spout(),
            basename=self.basename
        )


        self.upstreams:Dict[str, Tuple[Transformation, str]] = {}
        # {"input_tag": (upstream_transformation, upstream_output_channel) }


        self.downstreams:Dict[str, Set[Tuple[Transformation, str]]] = {}
        
        for output_tag, output_type in self.function_class.declare_outputs():
            # 初始化每个输出标签对应的下游变换列表
            self.downstreams[output_tag] = set()
        # ("output_tag", { (downstream_transformation, "downstream_input_tag") } )


        self.parallelism = parallelism  
        # 生成的平行节点名字：f"{transformation.function_class.__name__}_{i}"
        self.function_args = args
        self.kwargs = kwargs


        
    # 双向连接
    def add_upstream(self,input_tag:str,  upstream_trans: "Transformation", upstream_tag:str) -> None:
        self.upstreams[input_tag] = (upstream_trans, upstream_tag)
        upstream_trans.downstreams[upstream_tag].add((self, input_tag))

    # 这个方法不要使用，避免重复连接
    # def add_downstream(self, child: "Transformation") -> None:
    #     self.downstream.append(child)
    #     child.upstream.append(self)

    # ---------------- 编译器接口 ----------------
    # @abstractmethod
    # def get_operator_factory(self) -> "BaseOperatorFactory":
    #     """返回生成 Operator 的工厂。"""

    # ---------------- 工具函数 ----------------
    def build_instance(self, **kwargs) -> 'BaseOperator':
        """如果尚未实例化，则根据 op_class 和 kwargs 实例化。"""
        function = self.function_class(*self.function_args, **kwargs)
        self.logger.debug(f"Created function instance: {self.function_class.__name__} with args {self.function_args} and kwargs {kwargs}")
        return self.operator_class(function, **kwargs)
    
    def is_spout(self) -> bool:
        """检查当前变换是否为源节点（spout）。"""
        return self.type == TransformationType.SOURCE


    def __repr__(self) -> str:
        cls_name = self.function_class.__name__
        return f"<Transformation {cls_name} at {hex(id(self))}>"


class OperatorFactory:
    """
    Operator工厂类，负责创建各种类型的Operator实例
    可以被序列化传递给Ray Actor
    """

    def __init__(self, 
                 is_spout:bool, 
                 operator_class: Type[BaseOperator],
                 function_class: Type[BaseFunction],
                 function_args: Tuple = (),
                 function_kwargs: Dict[str, Any] = None,
                 operator_kwargs: Dict[str, Any] = None,
                 
                 basename: str = None):
        """
        初始化OperatorFactory
        
        Args:
            transformation: 变换
            function_class: 函数类（不是实例）
            function_args: 函数构造参数
            function_kwargs: 函数构造关键字参数
            operator_kwargs: operator构造关键字参数
            basename: 基础名称
        """
        self.is_spout = is_spout
        self.operator_class = operator_class

        self.function_class = function_class
        self.function_args = function_args or ()
        self.function_kwargs = function_kwargs or {}
        self.operator_kwargs = operator_kwargs or {}
        
        # 生成基础名称
        if basename is None:
            self.basename = get_name(self.function_class.__name__)
        else:
            self.basename = get_name(basename)

    def build_instance(self, 
                       session_folder: Optional[str] = None, 
                       name: Optional[str] = None,
                       **additional_kwargs) -> BaseOperator:
        """
        创建operator实例
        
        Args:
            session_folder: 会话文件夹
            name: 节点名称
            **additional_kwargs: 额外的关键字参数
            
        Returns:
            BaseOperator: 创建的operator实例
        """
        name = name or self.basename
        # 创建logger用于调试
        logger = CustomLogger(
            filename=f"OperatorFactory_{name}",
            session_folder=session_folder,
            console_output="WARNING",
            file_output="DEBUG",
            global_output="WARNING",
            name=f"OperatorFactory_{name}"
        )
        
        try:
            # 合并所有kwargs
            merged_function_kwargs = {
                **self.function_kwargs,
                'session_folder': session_folder,
                'name': name,
                **additional_kwargs
            }
            merged_operator_kwargs = {
                **self.operator_kwargs,
                'session_folder': session_folder,
                'name': name,
                **additional_kwargs
            }
            
            # 创建function实例
            function_instance = self.function_class(*self.function_args, **merged_function_kwargs)
            logger.debug(f"Created function instance: {self.function_class.__name__} "
                        f"with args {self.function_args} and kwargs {merged_function_kwargs}")
            
            # 创建operator实例
            operator_instance = self.operator_class(function_instance, **merged_operator_kwargs)
            logger.debug(f"Created operator instance: {self.operator_class.__name__} "
                        f"with function {self.function_class.__name__}")
            
            return operator_instance
            
        except Exception as e:
            logger.error(f"Failed to create operator: {e}", exc_info=True)
            raise
from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, TYPE_CHECKING, List
import pip
from sage.api.datastream import DataStream
from sage.api.base_function import BaseFunction
from sage.core.operator.base_operator import BaseOperator
from sage.core.operator.transformation import TransformationType, Transformation

# from sage.core.graph.sage_graph import SageGraph

class Environment:

    @classmethod
    def createLocalEnvironment(cls, name:str = "local_environment", config: dict | None = None) -> Environment:
        config = config or {}
        config["platform"] = "local"
        instance = object.__new__(cls)
        instance.name = name
        instance.config = config
        instance._pipeline = [] # List[Transformation]
        return instance

    @classmethod
    def createRemoteEnvironment(cls, name:str = "remote_environment", config: dict | None = None) -> Environment:
        config = config or {}
        config["platform"] = "ray"
        instance = object.__new__(cls)
        instance.name = name
        instance.config = config
        instance._pipeline = [] # List[Transformation]
        return instance
    
    @classmethod
    def createTestEnvironment(cls, name:str = "remote_environment", config: dict | None = None) -> Environment:
        config = config or {}
        config["platform"] = "hybrid"
        instance = object.__new__(cls)
        instance.name = name
        instance.config = config
        instance._pipeline = [] # List[Transformation]
        return instance

    def __init__(self,name:str = "default_environment", config: dict = {}):
        raise RuntimeError(
            "🚫 Direct instantiation of StreamingExecutionEnvironment is not allowed.\n"
            "✅ Please use one of the following:\n"
            " - StreamingExecutionEnvironment.createLocalEnvironment()\n"
            " - StreamingExecutionEnvironment.createRemoteEnvironment()\n"
            " - StreamingExecutionEnvironment.createTestEnvironment()\n"
        )
        # self.name = name
        # self.config = config
        # self._pipeline: List[Transformation] = []   # Transformation DAG

    def from_source(self, function: Union[BaseFunction, Type[BaseFunction]],*args,  **kwargs: Any) -> DataStream:
        """用户 API：声明一个数据源并返回 DataStream 起点。"""
        transformation = Transformation(TransformationType.SOURCE, function,*args,  **kwargs)
        self._pipeline.append(transformation)
        return DataStream(self, transformation)

    def execute(self):
        from sage.core.engine import Engine
        engine = Engine.get_instance()
        engine.submit_env(self)

    @property
    def pipeline(self) -> List[Transformation]:  # noqa: D401
        """返回 Transformation 列表（Compiler 会使用）。"""
        return self._pipeline
    


"""
可变默认对象是会共享的
def foo(config: dict = {}):
    config["a"] = config.get("a", 0) + 1
    print(config)

foo()  # {'a': 1}
foo()  # {'a': 2}  → 看到了吗！它在共享
foo()  # {'a': 3}

"""
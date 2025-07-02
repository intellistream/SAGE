from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any, TYPE_CHECKING, List
import pip
from sage.api.datastream import DataStream
from sage.api.base_function import BaseFunction
from sage.core.operator.base_operator import BaseOperator
from sage.core.operator.transformation import TransformationType, Transformation
from sage_examples.external_memory_ingestion_pipeline import config
from sage_memory.embeddingmodel import MockTextEmbedder
from sage_memory.memory_manager import MemoryManager


# from sage.core.compiler.sage_graph import SageGraph

class Environment:

    @classmethod
    def local_env(cls, name:str = "local_environment", config: dict | None = None) -> Environment:
        config = config or {}
        config["platform"] = "local"
        instance = object.__new__(cls)
        instance.name = name
        instance.config = config
        instance._pipeline = [] # List[Transformation]
        return instance

    @classmethod
    def remote_env(cls, name:str = "remote_environment", config: dict | None = None) -> Environment:
        config = config or {}
        config["platform"] = "ray"
        instance = object.__new__(cls)
        instance.name = name
        instance.config = config
        instance._pipeline = [] # List[Transformation]
        return instance
    
    @classmethod
    def dev_env(cls, name:str = "remote_environment", config: dict | None = None) -> Environment:
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

    def set_memory(self):
        """初始化内存管理器并创建测试集合"""
        default_model = MockTextEmbedder(fixed_dim=128)
        manager = MemoryManager()
        col = manager.create_collection(
            name="vdb_test",
            backend_type="VDB",
            embedding_model=default_model,
            dim=128,
            description="operator_test vdb collection",
            as_ray_actor=False,
        )
        col.add_metadata_field("owner")
        col.add_metadata_field("show_type")
        texts = [
            ("hello world", {"owner": "ruicheng", "show_type": "text"}),
            ("你好，世界", {"owner": "Jun", "show_type": "text"}),
            ("こんにちは、世界", {"owner": "Lei", "show_type": "img"}),
        ]
        for text, metadata in texts:
            col.insert(text, metadata)
        col.create_index(index_name="vdb_index")
        config["writer"]["ltm_collection"] = col

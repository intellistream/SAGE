from __future__ import annotations

import time
from typing import Type, Union, Any, List

import sage_memory.api
from sage.api.base_function import BaseFunction
from sage.api.datastream import DataStream
from sage.core.operator.transformation import TransformationType, Transformation
from sage_memory.embeddingmodel import MockTextEmbedder
from sage_memory.memory_manager import MemoryManager


class BaseEnvironment:

    def __init__(self, name: str, config: dict | None, *, platform: str, ):
        self.name = name
        self.config: dict = dict(config or {})
        self.config["platform"] = platform
        # 用于收集所有 Transformation，供 Compiler 构建 DAG
        self._pipeline: List[Transformation] = []
        self.runtime_context = dict  # 需要在compiler里面实例化。
        self.memory_collection = None  # 用于存储内存集合

    def from_source(self, function: Union[BaseFunction, Type[BaseFunction]], *args, **kwargs: Any) -> DataStream:
        """用户 API：声明一个数据源并返回 DataStream 起点。"""
        transformation = Transformation(TransformationType.SOURCE, function, *args, **kwargs)
        self._pipeline.append(transformation)
        return DataStream(self, transformation)

    # TODO: add a new type of source with handler returned.
    def create_source(self):
        pass

    def execute(self, name="example_pipeline"):
        from sage.core.engine import Engine
        engine = Engine.get_instance()
        engine.submit_env(self)
        # time.sleep(10) # 等待管道启动
        while (self.initlized() is False):
            time.sleep(1)

    @property
    def pipeline(self) -> List[Transformation]:  # noqa: D401
        """返回 Transformation 列表（Compiler 会使用）。"""
        return self._pipeline

    def set_memory(self, config):
        self.memory_collection = sage_memory.api.create_memory(config)

    # TODO: 写一个判断Env 是否已经完全初始化并开始执行的函数
    def initlized(self):
        pass


class LocalEnvironment(BaseEnvironment):
    """
    本地执行环境（不使用 Ray），用于开发调试或小规模测试。
    """

    def __init__(self, name: str = "local_environment", config: dict | None = None):
        super().__init__(name, config, platform="local")


class RemoteEnvironment(BaseEnvironment):
    """
    分布式执行环境（Ray），用于生产或大规模部署。
    """

    def __init__(self, name: str = "remote_environment", config: dict | None = None):
        super().__init__(name, config, platform="remote")


class DevEnvironment(BaseEnvironment):
    """
    混合执行环境，可根据配置动态选择本地或 Ray。
    config 中可包含 'use_ray': bool 来切换运行时。
    """

    def __init__(self, name: str = "dev_environment", config: dict | None = None):
        cfg = dict(config or {})
        # 默认不启用 Ray，除非显式指定
        use_ray_flag = cfg.get("use_ray", False)
        super().__init__(name, cfg, platform="hybrid")

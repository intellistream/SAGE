from __future__ import annotations

import time
from typing import Type, Union, Any, List
from enum import Enum
import sage_memory.api
from sage_core.api.base_function import BaseFunction
from sage_core.api.datastream import DataStream
from sage_core.core.operator.transformation import TransformationType, Transformation
from sage_utils.custom_logger import CustomLogger
from sage_core.api.enum import PlatformType

class BaseEnvironment:

    def __init__(self, name: str, config: dict | None, *, platform: PlatformType = PlatformType.LOCAL):
        self.name = name
        self.logger = CustomLogger(
            object_name=f"Environment_{name}",
            console_output=False,
            file_output=True
        )
        self.config: dict = dict(config or {})
        self.platform:PlatformType = platform
        # 用于收集所有 Transformation，供 Compiler 构建 DAG
        self._pipeline: List[Transformation] = []
        self.runtime_context = dict  # 需要在compiler里面实例化。
        self.memory_collection = None  # 用于存储内存集合
        self.is_running = False

    def from_source(
        self, 
        function: Union[BaseFunction, Type[BaseFunction]], 
        *args, 
        platform:PlatformType = PlatformType.LOCAL,
        **kwargs: Any) -> DataStream:
        
        """用户 API：声明一个数据源并返回 DataStream 起点。"""
        transformation = Transformation(
            self, 
            TransformationType.SOURCE, 
            function, 
            *args,
            platform = platform,  
            **kwargs
            )
        
        self._pipeline.append(transformation)
        return DataStream(self, transformation)

    # TODO: add a new type of source with handler returned.
    def create_source(self):
        pass

    def submit(self, name="example_pipeline"):
        from sage_core.core.engine import Engine
        engine = Engine.get_instance()
        engine.submit_env(self)
        # time.sleep(10) # 等待管道启动
        while (self.initlized() is False):
            time.sleep(1)

    def run_once(self, node:str = None):
        """
        运行一次管道，适用于测试或调试。
        """
        if(self.is_running):
            raise RuntimeError("Pipeline is already running. Please stop it before running again.")
        from sage_core.core.engine import Engine
        engine = Engine.get_instance()
        engine.run_once(self)
        # time.sleep(10) # 等待管道启动

    def run_streaming(self, node: str = None):
        """
        运行管道，适用于生产环境。
        """
        from sage_core.core.engine import Engine
        engine = Engine.get_instance()
        engine.run_streaming(self)
        # time.sleep(10) # 等待管道启动

    def stop(self):
        """
        停止管道运行。
        """
        from sage_core.core.engine import Engine
        engine = Engine.get_instance()
        engine.stop(self)


    @property
    def pipeline(self) -> List[Transformation]:  # noqa: D401
        """返回 Transformation 列表（Compiler 会使用）。"""
        return self._pipeline

    def set_memory(self, config):
        self.memory_collection = sage_memory.api.create_memory(config, remote = (self.config.get("platform", "local") == "remote"))

    # TODO: 写一个判断Env 是否已经完全初始化并开始执行的函数
    def initlized(self):
        pass


class LocalEnvironment(BaseEnvironment):
    """
    本地执行环境（不使用 Ray），用于开发调试或小规模测试。
    """

    def __init__(self, name: str = "local_environment", config: dict | None = None):
        super().__init__(name, config, platform=PlatformType.LOCAL)


class RemoteEnvironment(BaseEnvironment):
    """
    分布式执行环境（Ray），用于生产或大规模部署。
    """

    def __init__(self, name: str = "remote_environment", config: dict | None = None):
        super().__init__(name, config, platform=PlatformType.REMOTE)


class DevEnvironment(BaseEnvironment):
    """
    混合执行环境，可根据配置动态选择本地或 Ray。
    config 中可包含 'use_ray': bool 来切换运行时。
    """

    def __init__(self, name: str = "dev_environment", config: dict | None = None):
        cfg = dict(config or {})
        super().__init__(name, cfg, platform=PlatformType.HYBRID)

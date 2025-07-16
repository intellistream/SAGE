from __future__ import annotations

import time
from typing import Type, Union, Any, List
from enum import Enum
import sage_memory.api
from sage_core.function.base_function import BaseFunction
from sage_core.api.datastream import DataStream
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.transformation.source_transformation import SourceTransformation
from sage_core.transformation.future_transformation import FutureTransformation
from sage_utils.custom_logger import CustomLogger
from sage_utils.name_server import get_name
from sage_core.function.lambda_function import wrap_lambda



class BaseEnvironment:

    def __init__(self, name: str, config: dict | None, *, platform: str = "local"):
        self.name = get_name(name)
        self.logger = CustomLogger(
            filename=f"Environment_{name}",
            env_name = name,
            console_output="WARNING",
            file_output=True,
            global_output = "DEBUG",
        )
        

        self.config: dict = dict(config or {})
        self.platform:str = platform
        # 用于收集所有 BaseTransformation，供 Compiler 构建 DAG
        self._pipeline: List[BaseTransformation] = []
        self._filled_futures: dict = {}  # 记录已填充的future stream信息：name -> {future_transformation, actual_transformation, filled_at}
        self.runtime_context = dict  # 需要在compiler里面实例化。
        self.memory_collection = None  # 用于存储内存集合
        self.is_running = False



    def from_source(self, function: Union[Type[BaseFunction], callable], *args, **kwargs) -> DataStream:
        if callable(function) and not isinstance(function, type):
            # 这是一个 lambda 函数或普通函数
            function = wrap_lambda(function, 'flatmap')
        transformation = SourceTransformation(self, function, *args,**kwargs)
        
        self._pipeline.append(transformation)
        return DataStream(self, transformation)

    def from_future(self, name: str) -> DataStream:
        """
        创建一个future stream占位符，用于建立反馈边。
        
        Args:
            name: future stream的名称，用于标识和调试
            
        Returns:
            DataStream: 包含FutureTransformation的数据流
            
        Example:
            future_stream = env.from_future("feedback_loop")
            # 使用future_stream参与pipeline构建
            result = source.connect(future_stream).comap(CombineFunction)
            # 最后填充future
            result.fill_future(future_stream)
        """
        transformation = FutureTransformation(self, name)
        self._pipeline.append(transformation)
        return DataStream(self, transformation)

    # TODO: add a new type of source with handler returned.
    def create_source(self):
        pass

    def submit(self, name="example_pipeline"):
        # self.debug_print_pipeline()
        from sage_core.engine import Engine
        engine = Engine.get_instance()
        engine.submit_env(self)
        # time.sleep(10) # 等待管道启动
        while (self.initialized() is False):
            time.sleep(1)

    def run_once(self, node:str = None):
        """
        运行一次管道，适用于测试或调试。
        """
        if(self.is_running):
            self.logger.warning("Pipeline is already running. ")
            return
        from sage_core.engine import Engine
        engine = Engine.get_instance()
        engine.run_once(self)
        # time.sleep(10) # 等待管道启动

    def run_streaming(self, node: str = None):
        """
        运行管道，适用于生产环境。
        """
        from sage_core.engine import Engine
        engine = Engine.get_instance()
        engine.run_streaming(self)
        # time.sleep(10) # 等待管道启动

    def stop(self):
        """
        停止管道运行。
        """
        self.logger.info("Stopping pipeline...")
        from sage_core.engine import Engine
        engine = Engine.get_instance()
        engine.stop_pipeline(self)
        # self.close()

    def close(self):
        """
        关闭管道运行。
        """
        from sage_core.engine import Engine
        engine = Engine.get_instance()
        # 1) 停止本环境对应的 DAG 执行
        engine.stop_pipeline(self)
        # 2) 关闭该环境在 Engine 中的引用，并在无剩余环境时彻底 shutdown Engine
        engine.close_pipeline(self)
        # 3) 清理自身引用，以打破循环链
        self._pipeline.clear()



    def set_memory(self, config):
        self.memory_collection = sage_memory.api.get_memory(config=config, remote=(self.platform != "local"), env_name=self.name)

    def set_memory_collection(self, collection):

        self.memory_collection = collection 
        
    # TODO: 写一个判断Env 是否已经完全初始化并开始执行的函数
    def initialized(self):
        pass

    def get_filled_futures(self) -> dict:
        """
        获取所有已填充的future stream信息
        
        Returns:
            dict: 已填充的future stream信息，格式为:
                {
                    'future_name': {
                        'future_transformation': FutureTransformation,
                        'actual_transformation': BaseTransformation,
                        'filled_at': timestamp
                    }
                }
        """
        return self._filled_futures.copy()
    
    def has_unfilled_futures(self) -> bool:
        """
        检查pipeline中是否还有未填充的future streams
        
        Returns:
            bool: 如果存在未填充的future streams返回True，否则返回False
        """
        from sage_core.transformation.future_transformation import FutureTransformation
        for transformation in self._pipeline:
            if isinstance(transformation, FutureTransformation) and not transformation.filled:
                return True
        return False
    
    def validate_pipeline_for_compilation(self) -> None:
        """
        验证pipeline是否可以进行编译
        检查是否存在未填充的future streams
        
        Raises:
            RuntimeError: 如果存在未填充的future streams
        """
        from sage_core.transformation.future_transformation import FutureTransformation
        unfilled_futures = []
        
        for transformation in self._pipeline:
            if isinstance(transformation, FutureTransformation) and not transformation.filled:
                unfilled_futures.append(transformation.future_name)
        
        if unfilled_futures:
            raise RuntimeError(
                f"Cannot compile pipeline with unfilled future streams: {unfilled_futures}. "
                f"Please fill all future streams using fill_future() before compilation."
            )

    ########################################################
    #                auxiliary methods                     #
    ########################################################

    def _append(self, transformation: BaseTransformation):
        """将 BaseTransformation 添加到管道中（Compiler 会使用）。"""
        self.pipeline.append(transformation)
        return DataStream(self, transformation)
    
    @property
    def pipeline(self) -> List[BaseTransformation]:  # noqa: D401
        """返回 BaseTransformation 列表（Compiler 会使用）。"""
        return self._pipeline


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
        super().__init__(name, cfg, platform="hybrid")

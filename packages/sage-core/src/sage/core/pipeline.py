"""
Pipeline模块 - 核心数据处理管道
"""

from typing import Any, List, Dict, Optional, Union, Callable
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class Pipeline:
    """
    SAGE核心数据处理管道
    
    用于构建和执行数据处理流水线
    """
    
    def __init__(self, name: str = "sage_pipeline"):
        self.name = name
        self.steps = []
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    def add_step(self, step: 'PipelineStep') -> 'Pipeline':
        """添加处理步骤"""
        self.steps.append(step)
        self.logger.info(f"Added step: {step.name}")
        return self
        
    def execute(self, data: Any) -> Any:
        """执行管道处理"""
        self.logger.info(f"Executing pipeline: {self.name}")
        result = data
        
        for step in self.steps:
            self.logger.debug(f"Executing step: {step.name}")
            result = step.process(result)
            
        self.logger.info(f"Pipeline {self.name} completed")
        return result
        
    def __repr__(self) -> str:
        return f"Pipeline(name='{self.name}', steps={len(self.steps)})"


class PipelineStep(ABC):
    """管道步骤抽象基类"""
    
    def __init__(self, name: str):
        self.name = name
        
    @abstractmethod
    def process(self, data: Any) -> Any:
        """处理数据"""
        pass
        
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


class DataTransformStep(PipelineStep):
    """数据转换步骤"""
    
    def __init__(self, name: str, transform_func: Callable[[Any], Any]):
        super().__init__(name)
        self.transform_func = transform_func
        
    def process(self, data: Any) -> Any:
        return self.transform_func(data)


class FilterStep(PipelineStep):
    """数据过滤步骤"""
    
    def __init__(self, name: str, filter_func: Callable[[Any], bool]):
        super().__init__(name)
        self.filter_func = filter_func
        
    def process(self, data: Any) -> Any:
        if isinstance(data, (list, tuple)):
            return [item for item in data if self.filter_func(item)]
        return data if self.filter_func(data) else None


# 便利函数
def create_pipeline(name: str = "sage_pipeline") -> Pipeline:
    """创建一个新的管道"""
    return Pipeline(name)


def transform_step(name: str, func: Callable[[Any], Any]) -> DataTransformStep:
    """创建数据转换步骤"""
    return DataTransformStep(name, func)


def filter_step(name: str, func: Callable[[Any], bool]) -> FilterStep:
    """创建数据过滤步骤"""
    return FilterStep(name, func)

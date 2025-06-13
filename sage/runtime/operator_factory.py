# sage/runtime/operator_factory.py
from typing import TypeVar, Any, Type
import ray
import logging
from sage.runtime.operator_wrapper import OperatorWrapper
T = TypeVar("T")

class OperatorFactory:
    """简化的算子工厂，全局控制本地或远程创建"""
    
    def __init__(self, use_ray: bool = True):
        self.use_ray = use_ray
        self.logger = logging.getLogger(__name__)
        self._ray_remote_classes = {}  # 缓存Ray远程类
        
        if self.use_ray and not ray.is_initialized():
            self.logger.warning("Ray not initialized, falling back to local mode")
            self.use_ray = False
    

    def create(self, operator_class:Type[T], config:dict) -> T:
        """
        创建算子实例
        
        Args:
            operator_class: 算子类（如 FileSource）
            config: 算子配置
            
        Returns:
            算子实例（本地对象或Ray Actor Handle）
        """
        if self.use_ray:
            raw_operator = self._create_ray_operator(operator_class, config)
        else:
            raw_operator = self._create_local_operator(operator_class, config)
        
        wrapped_operator = OperatorWrapper(raw_operator)
        return wrapped_operator


    def _create_ray_operator(self, operator_class, config):
        """创建Ray远程算子"""
        class_name = operator_class.__name__
        
        # 从缓存获取或创建Ray远程类
        if class_name not in self._ray_remote_classes:
            self._ray_remote_classes[class_name] = ray.remote(operator_class)
        
        ray_remote_class = self._ray_remote_classes[class_name]
        return ray_remote_class.remote(config)
    
    def _create_local_operator(self, operator_class, config):
        """创建本地算子"""
        return operator_class(config)
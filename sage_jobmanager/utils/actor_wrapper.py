import ray
import asyncio
import concurrent.futures
from typing import Any, Union
import logging
from ray.actor import ActorHandle
from sage_utils.custom_logger import CustomLogger

class ActorWrapper:
    """万能包装器，可以将任意对象包装成本地对象或Ray Actor"""
    
    def __init__(self, 
                 obj: Union[Any, ActorHandle], 
                 name: str = "ActorWrapper",
                 env_name: str = None):
        # 使用 __dict__ 直接设置，避免触发 __setattr__
        object.__setattr__(self, '_obj', obj)
        object.__setattr__(self, '_execution_mode', self._detect_execution_mode())
        object.__setattr__(self, '_name', name)
        
        # 初始化 logger
        logger = CustomLogger(
            filename=f"{name}_Wrapper",
            env_name=env_name,
            console_output="WARNING",
            file_output="DEBUG", 
            global_output="DEBUG",
            name=f"{name}_UniversalWrapper"
        )
        object.__setattr__(self, 'logger', logger)
        
        self.logger.debug(f"Created ActorWrapper for {type(obj).__name__} in {self._execution_mode} mode")
    
    def _detect_execution_mode(self) -> str:
        """检测执行模式"""
        try:
            if isinstance(self._obj, ray.actor.ActorHandle):
                return "ray_actor"
        except (ImportError, AttributeError):
            pass
        return "local"
    
    def __getattr__(self, name: str):
        """透明代理属性访问"""
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        # 获取原始属性/方法
        try:
            original_attr = getattr(self._obj, name)
        except AttributeError:
            raise AttributeError(f"'{type(self._obj).__name__}' object has no attribute '{name}'")
        
        # 如果是方法，需要包装
        if callable(original_attr):
            if self._execution_mode == "ray_actor":
                # Ray Actor方法：返回同步调用包装器
                def ray_method_wrapper(*args, **kwargs):
                    self.logger.debug(f"Calling Ray Actor method '{name}' with args={args}, kwargs={kwargs}")
                    future = original_attr.remote(*args, **kwargs)
                    result = ray.get(future)
                    self.logger.debug(f"Ray Actor method '{name}' completed")
                    return result
                return ray_method_wrapper
            else:
                # 本地方法：直接返回
                return original_attr
        else:
            # 普通属性：直接返回
            return original_attr
    
    def __setattr__(self, name: str, value: Any):
        """代理属性设置"""
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._obj, name, value)
    
    def __repr__(self):
        return f"ActorWrapper[{self._execution_mode}]({repr(self._obj)})"
    
    def get_wrapped_object(self):
        """获取被包装的原始对象"""
        return self._obj
    
    def is_ray_actor(self) -> bool:
        """检查是否为Ray Actor"""
        return self._execution_mode == "ray_actor"
    
    def is_local(self) -> bool:
        """检查是否为本地对象"""
        return self._execution_mode == "local"
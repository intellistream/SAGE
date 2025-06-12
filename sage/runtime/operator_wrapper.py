# sage/runtime/operator_wrapper.py
import ray
import asyncio
from typing import Any, Dict, Optional, Type

class OperatorWrapper:
    """透明的算子包装器，外部代码无感知"""
    
    def __init__(self, operator: Any):
        # 使用 __dict__ 直接设置，避免触发 __setattr__
        object.__setattr__(self, '_operator', operator)
        object.__setattr__(self, '_execution_mode', self._detect_execution_mode())
        object.__setattr__(self, '_method_cache', {})
        object.__setattr__(self, '_attribute_cache', {})
    
    def _detect_execution_mode(self) -> str:
        """检测执行模式"""
        if isinstance(self._operator, ray.actor.ActorHandle):
            return "ray_actor"
        elif hasattr(self._operator, 'remote'):
            return "ray_function"
        else:
            return "local"
    
    # 完美代理所有属性访问
    def __getattr__(self, name: str):
        """透明代理属性访问"""
        # 先检查缓存
        if name in self._attribute_cache:
            return self._attribute_cache[name]
        
        original_attr = getattr(self._operator, name)
        
        # 如果是方法，则包装成统一调用
        if callable(original_attr):
            if self._execution_mode == "ray_actor":
                # Ray Actor方法需要特殊处理
                wrapped_method = self._create_ray_actor_method(name, original_attr)
            elif self._execution_mode == "ray_function":
                wrapped_method = self._create_ray_function_method(name, original_attr)
            else:
                # 本地方法，检查是否需要异步包装
                wrapped_method = self._create_local_method(name, original_attr)
            
            self._attribute_cache[name] = wrapped_method
            return wrapped_method
        else:
            # 普通属性直接返回
            self._attribute_cache[name] = original_attr
            return original_attr
    
    def __setattr__(self, name: str, value: Any):
        """代理属性设置"""
        if name.startswith('_'):
            # 内部属性直接设置
            object.__setattr__(self, name, value)
        else:
            # 外部属性设置到原算子
            setattr(self._operator, name, value)
    
    def __dir__(self):
        """代理dir()调用"""
        return dir(self._operator)
    
    def __repr__(self):
        """代理repr()"""
        return f"OperatorWrapper({repr(self._operator)})"
    
    def __str__(self):
        """代理str()"""
        return str(self._operator)
    
    def _create_ray_actor_method(self, method_name: str, original_method):
        """创建Ray Actor方法包装"""
        async def async_wrapper(*args, **kwargs):
            future = original_method.remote(*args, **kwargs)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, ray.get, future)
        
        def sync_wrapper(*args, **kwargs):
            future = original_method.remote(*args, **kwargs)
            return ray.get(future)
        
        # 根据原方法是否异步来决定返回哪个包装器
        # 由于Ray Actor方法调用总是返回Future，我们提供两个版本
        async_wrapper.sync = sync_wrapper
        sync_wrapper.async_version = async_wrapper
        
        # 默认返回异步版本
        return async_wrapper
    
    def _create_ray_function_method(self, method_name: str, original_method):
        """创建Ray Function方法包装"""
        async def wrapper(*args, **kwargs):
            future = original_method.remote(*args, **kwargs)
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, ray.get, future)
        
        return wrapper
    
    def _create_local_method(self, method_name: str, original_method):
        """创建本地方法包装"""
        if asyncio.iscoroutinefunction(original_method):
            # 已经是异步方法，直接返回
            return original_method
        else:
            # 同步方法，创建异步包装
            async def async_wrapper(*args, **kwargs):
                return original_method(*args, **kwargs)
            
            # 同时保留同步版本
            async_wrapper.sync = original_method
            original_method.async_version = async_wrapper
            
            # 默认返回异步版本
            return 
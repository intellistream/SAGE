# sage/runtime/operator_wrapper.py
import ray
import asyncio
from typing import Any, Dict, Optional, Type
from sage.api.operator.base_operator_api import BaseOperator
class OperatorWrapper:
    """
    透明的算子包装器，提供统一的同步接口
    
    该包装器自动处理本地对象、Ray Actor和Ray Function的差异，
    对外提供一致的同步调用接口。
    
    支持的执行模式：
    - local: 本地对象直接调用
    - ray_actor: Ray Actor远程调用，自动处理ray.get()
    - ray_function: Ray Function远程调用，自动处理ray.get()
    
    示例:
        # 本地模式
        local_op = FileSource(config)
        wrapper = OperatorWrapper(local_op)
        result = wrapper.read()  # 直接调用
        
        # Ray Actor模式
        ray_actor = ray.remote(FileSource).remote(config)
        wrapper = OperatorWrapper(ray_actor)
        result = wrapper.read()  # 自动处理ray.get()
    """
    
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
        if name in self._attribute_cache:
            return self._attribute_cache[name]
        
        original_attr = getattr(self._operator, name)
        
        # 如果是方法，则包装成统一的同步调用
        if callable(original_attr):
            wrapped_method = self._create_unified_method(name, original_attr)
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
    
    def _create_unified_method(self, method_name: str, original_method):
        """创建统一的方法包装 - 对外始终提供同步接口"""
        
        if self._execution_mode == "ray_actor":
            # Ray Actor: 同步调用，内部处理Ray异步
            def sync_ray_actor_wrapper(*args, **kwargs):
                try:
                    future = original_method.remote(*args, **kwargs)
                    result = ray.get(future)
                    return result
                except Exception as e:
                    raise RuntimeError(f"Ray Actor method '{method_name}' failed: {e}")
            
            return sync_ray_actor_wrapper
            
        elif self._execution_mode == "ray_function":
            # Ray Function: 同步调用
            def sync_ray_function_wrapper(*args, **kwargs):
                try:
                    future = original_method.remote(*args, **kwargs)
                    result = ray.get(future)
                    return result
                except Exception as e:
                    raise RuntimeError(f"Ray function '{method_name}' failed: {e}")
            
            return sync_ray_function_wrapper
            
        else:
            # 本地方法: 处理异步方法，统一返回同步结果
            if asyncio.iscoroutinefunction(original_method):
                def sync_local_async_wrapper(*args, **kwargs):
                    try:
                        # 检查是否已在事件循环中
                        try:
                            loop = asyncio.get_running_loop()
                            # 如果在事件循环中，需要在新线程中运行
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(asyncio.run, original_method(*args, **kwargs))
                                return future.result()
                        except RuntimeError:
                            # 不在事件循环中，直接使用asyncio.run
                            return asyncio.run(original_method(*args, **kwargs))
                    except Exception as e:
                        raise RuntimeError(f"Local async method '{method_name}' failed: {e}")
                
                return sync_local_async_wrapper
            else:
                # 本地同步方法，直接返回
                return original_method
    
    # 可选：提供异步接口给需要的场景
    def get_async_method(self, method_name: str):
        """获取异步版本的方法（可选功能）"""
        original_method = getattr(self._operator, method_name)
        
        if self._execution_mode == "ray_actor":
            async def async_ray_actor_wrapper(*args, **kwargs):
                future = original_method.remote(*args, **kwargs)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, ray.get, future)
            return async_ray_actor_wrapper
            
        elif self._execution_mode == "ray_function":
            async def async_ray_function_wrapper(*args, **kwargs):
                future = original_method.remote(*args, **kwargs)
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, ray.get, future)
            return async_ray_function_wrapper
            
        else:
            if asyncio.iscoroutinefunction(original_method):
                return original_method
            else:
                async def async_local_wrapper(*args, **kwargs):
                    return original_method(*args, **kwargs)
                return async_local_wrapper
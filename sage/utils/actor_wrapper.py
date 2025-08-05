import ray
import asyncio
import concurrent.futures
from typing import Any, Union
import logging
from ray.actor import ActorHandle


# 目前的actor wrapper的远程方法调用都是同步阻塞调用。
class ActorWrapper:
    """万能包装器，可以将任意对象包装成本地对象或Ray Actor"""
    
    def __init__(self, 
                 obj: Union[Any, ActorHandle]):
        # 使用 __dict__ 直接设置，避免触发 __setattr__
        object.__setattr__(self, '_obj', obj)
        object.__setattr__(self, '_execution_mode', self._detect_execution_mode())
    
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
                    future = original_attr.remote(*args, **kwargs)
                    result = ray.get(future)
                    return result
                return ray_method_wrapper
            else:
                # 本地方法：直接返回
                return original_attr
        else:
            # 普通属性：直接返回
            return original_attr
    
    def call_async(self, method_name: str, *args, **kwargs):
        """异步调用Ray Actor方法，返回ObjectRef"""
        if self._execution_mode != "ray_actor":
            raise RuntimeError("call_async only available for Ray actors")
        
        method = getattr(self._obj, method_name)
        if not callable(method):
            raise AttributeError(f"'{method_name}' is not a callable method")
        
        return method.remote(*args, **kwargs)
    
    def __setattr__(self, name: str, value: Any):
        """代理属性设置"""
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._obj, name, value)
    
    def __repr__(self):
        return f"ActorWrapper[{self._execution_mode}]({repr(self._obj)})"
    
    def get_object(self):
        """获取被包装的原始对象"""
        return self._obj
    
    def is_ray_actor(self) -> bool:
        """检查是否为Ray Actor"""
        return self._execution_mode == "ray_actor"
    
    def is_local(self) -> bool:
        """检查是否为本地对象"""
        return self._execution_mode == "local"
    
    def kill_actor(self, no_restart: bool = True):
        """
        终止Ray Actor
        
        Args:
            no_restart: 是否禁止重启 (默认True)
            
        Returns:
            bool: 对于Ray Actor返回True表示kill成功，对于本地对象返回False
        """
        if self._execution_mode != "ray_actor":
            # 对于本地对象，无需kill操作
            return False
            
        try:
            import ray
            ray.kill(self._obj, no_restart=no_restart)
            return True
        except Exception as e:
            # 记录错误但不抛出异常，让调用者决定如何处理
            print(f"Warning: Failed to kill Ray actor {self._obj}: {e}")
            return False
    
    def cleanup_and_kill(self, cleanup_timeout: float = 5.0, no_restart: bool = True):
        """
        先调用cleanup方法（如果存在），然后kill actor
        
        Args:
            cleanup_timeout: cleanup方法的超时时间（秒）
            no_restart: 是否禁止重启 (默认True)
            
        Returns:
            tuple: (cleanup_success, kill_success)
        """
        cleanup_success = False
        kill_success = False
        
        if self._execution_mode != "ray_actor":
            return cleanup_success, kill_success
        
        # 尝试调用cleanup方法
        if hasattr(self._obj, 'cleanup'):
            try:
                import ray
                # 异步调用cleanup，设置超时
                cleanup_ref = self._obj.cleanup.remote()
                ray.get(cleanup_ref, timeout=cleanup_timeout)
                cleanup_success = True
            except Exception as e:
                print(f"Warning: Cleanup failed for {self._obj}: {e}")
        
        # 无论cleanup是否成功，都尝试kill actor
        kill_success = self.kill_actor(no_restart=no_restart)
        
        return cleanup_success, kill_success
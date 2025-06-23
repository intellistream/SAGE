import ray
import asyncio
import concurrent.futures
from typing import Any


class CollectionWrapper:
    """透明的集合包装器，自动适配本地执行、Ray Actor、Ray Function等多种模式"""

    def __init__(self, collection: Any):
        # 使用 __dict__ 直接设置，避免触发 __setattr__
        object.__setattr__(self, '_collection', collection)
        object.__setattr__(self, '_execution_mode', self._detect_execution_mode())
        object.__setattr__(self, '_method_cache', {})
        object.__setattr__(self, '_attribute_cache', {})

    def _detect_execution_mode(self) -> str:
        """检测执行模式"""
        try:
            # 1. 检查是否是Ray Actor
            import ray
            if isinstance(self._collection, ray.actor.ActorHandle):
                return "ray_actor"
            # 2. 检查是否有远程调用方法
            if hasattr(self._collection, 'remote') and callable(self._collection.remote):
                return "ray_function"
        except ImportError:
            # 如果Ray不可用，忽略
            pass

        # 3. 默认作为本地对象处理
        return "local"

    # 属性访问代理
    def __getattr__(self, name: str):
        """透明代理属性访问"""
        # 缓存查找
        if name in self._attribute_cache:
            return self._attribute_cache[name]

        # 获取原始属性
        try:
            original_attr = getattr(self._collection, name)
        except AttributeError:
            raise AttributeError(f"'{type(self._collection).__name__}' object has no attribute '{name}'")

        # 处理方法调用
        if callable(original_attr):
            # 创建统一调用方式
            wrapped_method = self._create_unified_method(name, original_attr)
            self._attribute_cache[name] = wrapped_method
            return wrapped_method

        # 普通属性
        self._attribute_cache[name] = original_attr
        return original_attr

    # 属性设置代理
    def __setattr__(self, name: str, value: Any):
        """代理属性设置"""
        if name.startswith('_'):
            # 内部属性直接设置
            object.__setattr__(self, name, value)
        else:
            # 外部属性设置到原集合
            setattr(self._collection, name, value)

    # 辅助方法
    def __dir__(self):
        """代理dir()调用"""
        return dir(self._collection)

    def __repr__(self):
        """代理repr()"""
        return f"CollectionWrapper({repr(self._collection)})"

    def __str__(self):
        """代理str()"""
        return str(self._collection)

    def _create_unified_method(self, method_name: str, original_method):
        """创建统一的方法包装 - 对外始终提供同步接口"""
        if self._execution_mode == "ray_actor":
            # Ray Actor处理
            def ray_actor_wrapper(*args, **kwargs):
                try:
                    # 获取远程方法引用
                    remote_method = getattr(self._collection, method_name)
                    # 执行远程调用
                    future = remote_method.remote(*args, **kwargs)
                    # 同步获取结果
                    return ray.get(future)
                except Exception as e:
                    raise RuntimeError(f"Ray Actor method '{method_name}' failed: {str(e)}")

            return ray_actor_wrapper

        elif self._execution_mode == "ray_function":
            # Ray函数处理
            def ray_function_wrapper(*args, **kwargs):
                try:
                    # 执行远程调用
                    future = original_method(*args, **kwargs)
                    # 同步获取结果
                    return ray.get(future)
                except Exception as e:
                    raise RuntimeError(f"Ray function '{method_name}' failed: {str(e)}")

            return ray_function_wrapper

        else:
            # 本地方法处理
            if asyncio.iscoroutinefunction(original_method):
                # 异步方法转同步
                def async_wrapper(*args, **kwargs):
                    try:
                        # 检查事件循环
                        try:
                            loop = asyncio.get_running_loop()
                            # 在独立线程中执行异步任务
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                result = executor.submit(
                                    asyncio.run,
                                    original_method(*args, **kwargs)
                                ).result()
                            return result
                        except RuntimeError:
                            # 直接运行异步方法
                            return asyncio.run(original_method(*args, **kwargs))
                    except Exception as e:
                        raise RuntimeError(f"Local async method '{method_name}' failed: {str(e)}")

                return async_wrapper
            else:
                # 同步方法直接返回
                return original_method
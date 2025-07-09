import ray
import asyncio
import concurrent.futures
from typing import Any, Union
import logging
from ray.actor import ActorHandle
from sage_utils.custom_logger import CustomLogger

class OperatorWrapper:
    """透明的 Operator 包装器，自动适配本地 Operator 和 Ray Actor Operator"""

    def __init__(self, operator: Union[Any, ActorHandle], name:str):
        # 使用 __dict__ 直接设置，避免触发 __setattr__
        object.__setattr__(self, '_operator', operator)
        object.__setattr__(self, '_execution_mode', self._detect_execution_mode())
        object.__setattr__(self, '_method_cache', {})
        object.__setattr__(self, '_attribute_cache', {})
        
        # 初始化 logger
        logger = CustomLogger(
            filename=f"Node_{name}",
            console_output="WARNING",
            file_output="DEBUG",
            global_output="DEBUG",
            name=f"{name}_OperatorWrapper"
        )
        
        object.__setattr__(self, 'logger', logger)
        self.logger.debug(f"Created OperatorWrapper for {type(operator).__name__} in {self._execution_mode} mode")
        
    def _detect_execution_mode(self) -> str:
        """检测执行模式"""
        try:
            # 检查是否是Ray Actor
            if isinstance(self._operator, ray.actor.ActorHandle):
                return "ray_actor"
        except (ImportError, AttributeError):
            # 如果Ray不可用，忽略
            pass

        # 默认作为本地对象处理
        return "local"

    def __getattr__(self, name: str):
        """透明代理属性访问"""
        # 防止循环引用 - 检查是否访问内部属性
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        # 防止访问 _operator 时的循环引用
        if '_operator' not in self.__dict__:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        # 缓存查找
        if hasattr(self, '_attribute_cache') and name in self._attribute_cache:
            return self._attribute_cache[name]

        # 获取原始属性
        try:
            if self._execution_mode == "ray_actor":
                # 对于 Ray Actor，直接获取属性（不调用 .remote()）
                original_attr = getattr(self._operator, name)
            else:
                # 对于本地对象，正常获取属性
                original_attr = getattr(self._operator, name)
        except AttributeError:
            raise AttributeError(f"'{type(self._operator).__name__}' object has no attribute '{name}'")

        # 处理方法调用
        if callable(original_attr):
            # 创建统一调用方式
            wrapped_method = self._create_unified_method(name, original_attr)
            if hasattr(self, '_attribute_cache'):
                self._attribute_cache[name] = wrapped_method
            return wrapped_method

        # 普通属性
        if hasattr(self, '_attribute_cache'):
            self._attribute_cache[name] = original_attr
        return original_attr

    def __setattr__(self, name: str, value: Any):
        """代理属性设置"""
        if name.startswith('_'):
            # 内部属性直接设置
            object.__setattr__(self, name, value)
        else:
            # 外部属性设置到原 operator
            if self._execution_mode == "ray_actor":
                # Ray Actor 属性设置需要通过远程调用
                # 注意：这可能需要在 operator 中实现 set_attribute 方法
                self.logger.warning(f"Setting attribute '{name}' on Ray Actor - this may not work as expected")
                setattr(self._operator, name, value)
            else:
                setattr(self._operator, name, value)

    def __dir__(self):
        """代理dir()调用"""
        if self._execution_mode == "ray_actor":
            # Ray Actor 的 dir() 可能不完整，返回常见的 operator 方法
            return ['process_data', 'start_spout_loop', 'stop_actor', 'get_actor_status']
        else:
            return dir(self._operator)

    def __repr__(self):
        """代理repr()"""
        mode_info = f"[{self._execution_mode}]"
        return f"OperatorWrapper{mode_info}({repr(self._operator)})"

    def __str__(self):
        """代理str()"""
        return f"OperatorWrapper({str(self._operator)})"

    def _create_unified_method(self, method_name: str, original_method):
        """创建统一的方法包装 - 对外始终提供同步接口"""
        
        if self._execution_mode == "ray_actor":
            # Ray Actor处理
            def ray_actor_wrapper(*args, **kwargs):
                try:
                    self.logger.debug(f"Calling Ray Actor method '{method_name}' with args={args}, kwargs={kwargs}")
                    
                    # 执行远程调用，original_method 已经是 remote 方法
                    future = original_method.remote(*args, **kwargs)
                    
                    # 同步获取结果
                    result = ray.get(future)
                    self.logger.debug(f"Ray Actor method '{method_name}' completed successfully")
                    return result
                    
                except Exception as e:
                    self.logger.error(f"Ray Actor method '{method_name}' failed: {str(e)}")
                    raise RuntimeError(f"Ray Actor method '{method_name}' failed: {str(e)}")

            return ray_actor_wrapper

        else:
            # 本地方法处理
            if asyncio.iscoroutinefunction(original_method):
                # 异步方法转同步
                def async_wrapper(*args, **kwargs):
                    try:
                        self.logger.debug(f"Calling local async method '{method_name}'")
                        
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
                        self.logger.error(f"Local async method '{method_name}' failed: {str(e)}")
                        raise RuntimeError(f"Local async method '{method_name}' failed: {str(e)}")

                return async_wrapper
            else:
                # 同步方法直接返回
                def sync_wrapper(*args, **kwargs):
                    try:
                        self.logger.debug(f"Calling local sync method '{method_name}'")
                        result = original_method(*args, **kwargs)
                        self.logger.debug(f"Local sync method '{method_name}' completed successfully")
                        return result
                    except Exception as e:
                        self.logger.error(f"Local sync method '{method_name}' failed: {str(e)}")
                        raise

                return sync_wrapper

    # 添加一些 operator 特有的便利方法
    def is_ray_actor(self) -> bool:
        """检查是否为 Ray Actor"""
        return self._execution_mode == "ray_actor"

    def is_local(self) -> bool:
        """检查是否为本地 operator"""
        return self._execution_mode == "local"

    def get_execution_mode(self) -> str:
        """获取执行模式"""
        return self._execution_mode

    def get_wrapped_operator(self):
        """获取被包装的原始 operator（谨慎使用）"""
        return self._operator

    # # 为常见的 operator 方法提供类型提示和文档
    # def process_data(self, channel: str, data: Any) -> Any:
    #     """
    #     处理数据的统一接口
        
    #     Args:
    #         channel: 输入通道名称
    #         data: 输入数据
            
    #     Returns:
    #         处理后的数据
    #     """
    #     # 这个方法会被 __getattr__ 拦截并返回包装后的方法
    #     pass

    # def start_spout_loop(self):
    #     """
    #     启动 spout 循环（仅适用于 spout operator）
    #     """
    #     # 这个方法会被 __getattr__ 拦截并返回包装后的方法
    #     pass

    # def stop_actor(self):
    #     """
    #     停止 operator（适用于 Ray Actor）
    #     """
    #     # 这个方法会被 __getattr__ 拦截并返回包装后的方法
    #     pass

    # def get_actor_status(self) -> dict:
    #     """
    #     获取 operator 状态
    #     """
    #     # 这个方法会被 __getattr__ 拦截并返回包装后的方法
    #     pass
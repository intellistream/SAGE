import logging
from abc import ABC
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sage.kernel.runtime.context.service_context import ServiceContext


class BaseService(ABC):  # noqa: B024
    """
    BaseService is the abstract base class for all services in SAGE.
    It defines the core interface and provides access to runtime context and logger.
    """

    def __init__(self, *args, **kwargs):
        """
        初始化基础服务

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Note:
            ctx 会在实例创建时由 ServiceFactory 自动注入，
            服务类不需要在构造函数中声明 ctx 参数
        """
        # ctx 由 ServiceFactory 在 __init__ 调用前通过 __new__ 方法注入
        if not hasattr(self, "ctx"):
            # Initialize ctx as Optional[ServiceContext] - will be injected by ServiceFactory
            self.ctx: Optional[ServiceContext] = None
        self._logger = None

    @property
    def logger(self):
        """获取logger，优先使用ctx.logger，否则使用默认logger"""
        if not hasattr(self, "_logger") or self._logger is None:
            if self.ctx is None:
                self._logger = logging.getLogger(self.__class__.__name__)
            else:
                self._logger = self.ctx.logger
        return self._logger

    @property
    def name(self):
        """获取服务名称，如果有ctx则使用ctx.name，否则使用类名"""
        if self.ctx is not None:
            return self.ctx.name
        return self.__class__.__name__

    def call_service(
        self,
        service_name: str,
        *args,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs,
    ):
        """
        同步服务调用语法糖

        用法:
            result = self.call_service("cache_service", key, method="get")
            data = self.call_service("pipeline_name", payload)
        """
        if self.ctx is None:
            raise RuntimeError("Service context not initialized. Cannot access services.")

        return self.ctx.call_service(service_name, *args, timeout=timeout, method=method, **kwargs)

    def call_service_async(
        self,
        service_name: str,
        *args,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs,
    ):
        """
        异步服务调用语法糖

        用法:
            future = self.call_service_async("cache_service", key, method="get")
            result = future.result()  # 阻塞等待结果

            # 或者非阻塞检查
            if future.done():
                result = future.result()
        """
        if self.ctx is None:
            raise RuntimeError("Service context not initialized. Cannot access services.")

        return self.ctx.call_service_async(
            service_name, *args, timeout=timeout, method=method, **kwargs
        )

    def setup(self):  # noqa: B027
        """
        服务初始化设置方法，在service_instance创建后调用
        子类可以重写此方法来进行初始化设置
        """
        pass

    def cleanup(self):  # noqa: B027
        """
        服务清理方法，在服务停止时调用
        子类可以重写此方法来进行资源清理
        """
        pass

    def start(self):  # noqa: B027
        """
        服务启动方法，在服务启动时调用
        子类可以重写此方法来进行启动逻辑
        """
        pass

    def stop(self):  # noqa: B027
        """
        服务停止方法，在服务停止时调用
        子类可以重写此方法来进行停止逻辑
        """
        pass

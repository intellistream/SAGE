from concurrent.futures import Future
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.kernel.runtime.proxy.proxy_manager import ProxyManager
    from sage.kernel.runtime.service.service_caller import ServiceManager


class BaseRuntimeContext:
    """
    Base runtime context class providing common functionality
    for TaskContext and ServiceContext
    """

    def __init__(self):
        # 服务调用相关
        self._proxy_manager: ProxyManager | None = None

    @property
    def logger(self) -> "CustomLogger":
        """Logger property - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement logger property")

    # def __getstate__(self):
    #     """自定义序列化：排除不可序列化的属性"""
    #     state = self.__dict__.copy()
    #     # 移除不可序列化的对象
    #     state.pop('_service_manager', None)
    #     state.pop('_service_dict', None)
    #     state.pop('_async_service_dict', None)
    #     # 如果子类定义了__state_exclude__属性，移除指定的属性
    #     if hasattr(self, '__state_exclude__'):
    #         for attr in self.__state_exclude__:
    #             state.pop(attr, None)
    #     return state

    # def __setstate__(self, state):
    #     """反序列化时恢复状态"""
    #     self.__dict__.update(state)
    #     # 重置服务管理器相关属性为None，它们会在需要时被懒加载
    #     self._service_manager = None
    #     self._service_dict = None
    #     self._async_service_dict = None

    @property
    def proxy_manager(self) -> "ProxyManager":
        """Lazy-loaded proxy manager wrapping service communication."""
        if self._proxy_manager is None:
            from sage.kernel.runtime.proxy.proxy_manager import ProxyManager

            self._proxy_manager = ProxyManager(self, logger=self.logger)
        return self._proxy_manager

    @property
    def service_manager(self) -> "ServiceManager":
        """Backward-compatible accessor for the underlying service manager."""
        return self.proxy_manager.service_manager

    # ------------------------------------------------------------------
    # Unified service invocation helpers
    # ------------------------------------------------------------------
    def call_service(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Invoke a service synchronously using the shared proxy layer."""

        return self.proxy_manager.call_sync(
            service_name, *args, timeout=timeout, method=method, **kwargs
        )

    def call_service_async(
        self,
        service_name: str,
        *args: Any,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs: Any,
    ) -> Future:
        """Invoke a service asynchronously and return a Future."""

        return self.proxy_manager.call_async(
            service_name, *args, timeout=timeout, method=method, **kwargs
        )

    def cleanup_service_manager(self):
        """清理服务管理器资源"""
        if self._proxy_manager is not None:
            try:
                self._proxy_manager.shutdown()
            except Exception as e:
                self.logger.warning(f"Error shutting down proxy manager: {e}")
            finally:
                self._proxy_manager = None

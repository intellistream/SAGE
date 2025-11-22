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
        # Keyed state support - tracks current packet's key
        self._current_packet_key: Any = None

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

            # ProxyManager expects logging.Logger but CustomLogger is compatible
            self._proxy_manager = ProxyManager(self, logger=self.logger)  # type: ignore[arg-type]
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

    # ------------------------------------------------------------------
    # Keyed State Support
    # ------------------------------------------------------------------
    def set_current_key(self, key: Any) -> None:
        """
        Set the current packet's key for keyed state operations.

        This method is called by operators when processing a packet to make
        the packet's key available to functions via get_key().

        Args:
            key: The key associated with the current packet being processed
        """
        self._current_packet_key = key

    def get_key(self) -> Any:
        """
        Get the key of the currently processing packet.

        This method allows functions to access the key of the packet being
        processed, enabling keyed state management patterns. Returns None
        if no key is set (e.g., for unkeyed streams).

        Returns:
            The current packet's key, or None if not set

        Example:
            >>> class UserSessionFunction(StatefulFunction):
            ...     def __init__(self, **kwargs):
            ...         super().__init__(**kwargs)
            ...         self.user_sessions = {}  # Keyed state
            ...
            ...     def execute(self, event_data):
            ...         user_id = self.ctx.get_key()
            ...         if user_id not in self.user_sessions:
            ...             self.user_sessions[user_id] = {'count': 0}
            ...         self.user_sessions[user_id]['count'] += 1
            ...         return self.user_sessions[user_id]
        """
        return self._current_packet_key

    def clear_key(self) -> None:
        """
        Clear the current packet's key.

        This method is called by operators after packet processing is complete
        to ensure the key doesn't leak into subsequent operations.
        """
        self._current_packet_key = None

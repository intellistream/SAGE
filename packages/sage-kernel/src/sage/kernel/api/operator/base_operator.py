from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from sage.kernel.runtime.communication.packet import StopSignal

if TYPE_CHECKING:
    from sage.common.core.functions import BaseFunction
    from sage.common.utils.logging.custom_logger import CustomLogger
    from sage.kernel.runtime.communication.packet import Packet
    from sage.kernel.runtime.context.task_context import TaskContext
    from sage.kernel.runtime.factory.function_factory import FunctionFactory


class BaseOperator(ABC):
    """
    Operator 的抽象基类
    """

    # 控制状态保存的类属性（子类可覆盖）
    __state_include__: list[str] = []
    __state_exclude__: list[str] = ["ctx", "function", "logger", "_logger"]

    def __init__(self, function_factory: "FunctionFactory", ctx: "TaskContext", *args, **kwargs):
        self.ctx: TaskContext = ctx
        self.function: BaseFunction
        try:
            self.function = function_factory.create_function(self.name, ctx)
            self.logger.debug(f"Created function instance with {function_factory}")

        except Exception as e:
            self.logger.error(f"Failed to create function instance: {e}", exc_info=True)
            raise

    def send_packet(self, packet: "Packet") -> bool:
        """通过TaskContext发送数据包"""
        return self.ctx.send_packet(packet)  # type: ignore

    def send_stop_signal(self, stop_signal: "StopSignal") -> None:
        """通过TaskContext发送停止信号"""
        self.ctx.send_stop_signal(stop_signal)

    def get_routing_info(self) -> dict[str, Any]:
        """获取路由信息"""
        return self.ctx.get_routing_info()

    @property
    def router(self):
        return self.ctx.router

    def receive_packet(self, packet: "Packet"):
        """接收数据包并处理"""
        if packet is None:
            self.logger.warning(f"Received None packet in {self.name}")
            return
        self.logger.debug(f"Operator {self.name} received packet: {packet}")

        try:
            # Set the current packet key for keyed state support
            # Packet always has partition_key attribute, but it may be None
            self.ctx.set_current_key(packet.partition_key)

            # Process the packet
            self.process_packet(packet)
        finally:
            # Always clear the key after processing to prevent leakage
            self.ctx.clear_key()

    @abstractmethod
    def process_packet(self, packet: "Packet | None" = None):
        return

    def get_state(self) -> dict[str, Any]:
        """
        获取 Operator 的状态用于 checkpoint

        默认实现会保存 function 的状态和 operator 自身的可序列化属性。
        子类可以覆盖此方法来自定义状态保存逻辑。

        Returns:
            包含可序列化状态的字典
        """
        state: dict[str, Any] = {
            "operator_type": self.__class__.__name__,
        }

        # 保存 function 的状态
        if hasattr(self.function, "get_state"):
            try:
                state["function_state"] = self.function.get_state()
            except Exception as e:
                self.logger.warning(f"Failed to get function state: {e}")

        # 保存 operator 自身的状态
        operator_attrs = {}
        all_attrs = set(vars(self).keys())

        # 确定要保存的属性
        if self.__state_include__:
            attrs_to_save = set(self.__state_include__) & all_attrs
        else:
            exclude_set = set(self.__state_exclude__)
            attrs_to_save = all_attrs - exclude_set

        # 过滤私有属性
        if not self.__state_include__:
            attrs_to_save = {attr for attr in attrs_to_save if not attr.startswith("_")}

        # 收集可序列化的状态
        for attr_name in attrs_to_save:
            try:
                value = getattr(self, attr_name)
                if self._is_serializable(value):
                    operator_attrs[attr_name] = value
            except Exception as e:
                self.logger.warning(f"Failed to get operator attribute '{attr_name}': {e}")

        if operator_attrs:
            state["operator_attrs"] = operator_attrs

        return state

    def restore_state(self, state: dict[str, Any]):
        """
        从 checkpoint 恢复 Operator 的状态

        Args:
            state: 保存的状态字典
        """
        # 恢复 function 的状态
        if "function_state" in state and hasattr(self.function, "restore_state"):
            try:
                self.function.restore_state(state["function_state"])
                self.logger.info(f"Function state restored for operator {self.name}")
            except Exception as e:
                self.logger.warning(f"Failed to restore function state: {e}")

        # 恢复 operator 自身的状态
        if "operator_attrs" in state:
            for attr_name, value in state["operator_attrs"].items():
                try:
                    setattr(self, attr_name, value)
                except Exception as e:
                    self.logger.warning(f"Failed to restore operator attribute '{attr_name}': {e}")

    def _is_serializable(self, value: Any) -> bool:
        """检查值是否可序列化（与 BaseFunction 中的实现相同）"""
        if isinstance(value, (int, float, str, bool, type(None))):
            return True

        if isinstance(value, (list, tuple)):
            return all(self._is_serializable(item) for item in value)

        if isinstance(value, dict):
            return all(
                self._is_serializable(k) and self._is_serializable(v) for k, v in value.items()
            )

        import pickle

        try:
            pickle.dumps(value)
            return True
        except (TypeError, pickle.PicklingError, AttributeError):
            return False

    @property
    def name(self) -> str:
        """获取任务名称"""
        return self.ctx.name

    @property
    def logger(self) -> "CustomLogger":
        """获取当前任务的日志记录器"""
        return self.ctx.logger

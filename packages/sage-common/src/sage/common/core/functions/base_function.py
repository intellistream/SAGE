import logging
import pickle
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sage.kernel.runtime.context.task_context import TaskContext


class BaseFunction(ABC):
    """
    BaseFunction is the abstract base class for all operator functions in SAGE.
    It defines the core interface and initializes a logger.
    """

    # 子类可以覆盖这些属性来控制状态保存行为
    __state_include__: list[str] = []  # 如果非空，只保存这些字段
    __state_exclude__: list[str] = ["ctx", "_logger", "logger"]  # 排除这些字段

    # 不可序列化的类型（会被自动排除）
    __unserializable_types__ = (
        type(lambda: None),  # function
        type,  # class
        type(None).__class__,  # NoneType
        logging.Logger,
    )

    def __init__(self, *args, **kwargs):
        self.ctx: TaskContext | None = None  # 运行时注入
        self._logger = None

    @property
    def logger(self):
        if not hasattr(self, "_logger") or self._logger is None:
            if self.ctx is None:
                self._logger = logging.getLogger("")
            else:
                self._logger = self.ctx.logger
        return self._logger

    @property
    def name(self):
        if self.ctx is None:
            return self.__class__.__name__
        return self.ctx.name

    def call_service(
        self,
        service_name: str,
        *args,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs,
    ):
        """同步服务调用语法糖"""
        if self.ctx is None:
            raise RuntimeError("Runtime context not initialized. Cannot access services.")

        return self.ctx.call_service(service_name, *args, timeout=timeout, method=method, **kwargs)

    def call_service_async(
        self,
        service_name: str,
        *args,
        timeout: float | None = None,
        method: str | None = None,
        **kwargs,
    ):
        """异步服务调用语法糖"""
        if self.ctx is None:
            raise RuntimeError("Runtime context not initialized. Cannot access services.")

        return self.ctx.call_service_async(
            service_name, *args, timeout=timeout, method=method, **kwargs
        )

    def get_state(self) -> dict[str, Any]:
        """
        获取 Function 的状态用于 checkpoint

        子类可以覆盖此方法来自定义状态保存逻辑，或者通过设置
        __state_include__ 和 __state_exclude__ 来控制哪些字段被保存。

        Returns:
            包含可序列化状态的字典
        """
        state = {}

        # 获取所有实例属性
        all_attrs = set(vars(self).keys())

        # 确定要保存的属性
        if self.__state_include__:
            # 如果指定了 include，只保存这些字段
            attrs_to_save = set(self.__state_include__) & all_attrs
        else:
            # 否则保存所有字段，但排除 exclude 列表中的
            exclude_set = set(self.__state_exclude__)
            attrs_to_save = all_attrs - exclude_set

        # 过滤掉私有属性（以 _ 开头的，除非在 include 中明确指定）
        if not self.__state_include__:
            attrs_to_save = {
                attr
                for attr in attrs_to_save
                if not attr.startswith("_") or attr in self.__state_include__
            }

        # 收集可序列化的状态
        for attr_name in attrs_to_save:
            try:
                value = getattr(self, attr_name)

                # 检查是否可序列化
                if self._is_serializable(value):
                    state[attr_name] = value
                else:
                    # 对于不可序列化的对象，尝试保存其类型信息
                    if hasattr(value, "__class__"):
                        state[f"__{attr_name}_type__"] = value.__class__.__name__

            except Exception as e:
                # 如果获取属性失败，记录但继续
                if hasattr(self, "logger"):
                    self.logger.warning(f"Failed to get state for attribute '{attr_name}': {e}")

        # 保存类属性（如 use_metronome）
        state["__class_attrs__"] = self._get_class_attributes()

        return state

    def restore_state(self, state: dict[str, Any]):
        """
        从 checkpoint 恢复 Function 的状态

        子类可以覆盖此方法来自定义状态恢复逻辑。

        Args:
            state: 保存的状态字典
        """
        # 恢复实例属性
        for attr_name, value in state.items():
            # 跳过元数据
            if attr_name.startswith("__") and attr_name.endswith("__"):
                continue

            try:
                setattr(self, attr_name, value)
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.warning(f"Failed to restore attribute '{attr_name}': {e}")

        # 恢复类属性
        if "__class_attrs__" in state:
            self._restore_class_attributes(state["__class_attrs__"])

    def _is_serializable(self, value: Any) -> bool:
        """
        检查值是否可序列化

        Args:
            value: 要检查的值

        Returns:
            True 如果可序列化
        """
        # 基本类型
        if isinstance(value, int | float | str | bool | type(None)):
            return True

        # 容器类型（递归检查）
        if isinstance(value, list | tuple):
            return all(self._is_serializable(item) for item in value)

        if isinstance(value, dict):
            return all(
                self._is_serializable(k) and self._is_serializable(v) for k, v in value.items()
            )

        # 检查是否是不可序列化的类型
        if isinstance(value, self.__unserializable_types__):
            return False

        # 尝试判断是否可以被 pickle 序列化
        try:
            pickle.dumps(value)
            return True
        except (TypeError, pickle.PicklingError, AttributeError):
            return False

    def _get_class_attributes(self) -> dict[str, Any]:
        """
        获取类属性（如 use_metronome）

        Returns:
            类属性字典
        """
        class_attrs = {}

        # 遍历类的 __dict__
        for cls in self.__class__.__mro__:
            if cls is BaseFunction or cls is ABC:
                break

            for attr_name, value in cls.__dict__.items():
                # 跳过特殊属性和方法
                if attr_name.startswith("_") or callable(value):
                    continue

                # 只保存可序列化的类属性
                if self._is_serializable(value):
                    class_attrs[attr_name] = value

        return class_attrs

    def _restore_class_attributes(self, class_attrs: dict[str, Any]):
        """
        恢复类属性

        Note: 类属性是在类级别定义的，恢复时会在实例上创建同名属性，
        这样不会影响类定义，但会覆盖类属性的值。

        Args:
            class_attrs: 类属性字典
        """
        for attr_name, value in class_attrs.items():
            try:
                setattr(self, attr_name, value)
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.warning(f"Failed to restore class attribute '{attr_name}': {e}")

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        Abstract method to be implemented by subclasses.

        Each function must define its own execute logic that processes input data
        and returns the output.

        Subclasses can define their own signature:
        - Standard functions: execute(self, data: Any) -> Any
        - Join functions: execute(self, payload: Any, key: Any, tag: int) -> list[Any]
        - CoMap functions: execute(self, payload: Any, key: Any, tag: int) -> list[Any]
        - Batch functions: execute(self) -> Any
        - Source functions: execute(self, data: Any = None) -> Any

        :param args: Positional arguments (typically data)
        :param kwargs: Keyword arguments (for additional context)
        :return: Output data.
        """
        pass

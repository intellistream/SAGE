# sage/api/operator/base.py

from abc import ABC, abstractmethod
from typing import Any


class Operator(ABC):
    """
    API 层 Operator 抽象基类。
    将用户编写的 Function 包装，负责生命周期管理、
    并行度、状态等（可扩展）。
    """

    def __init__(self, function: Any):
        """
        :param function: 已初始化并 open() 的 Function 实例
        """
        self.fn = function

    def setup(self) -> None:
        """
        Operator 级别的初始化钩子。
        例如可以在此设置分区、状态后端接入等。
        """
        pass

    @abstractmethod
    def run(self, record: Any) -> Any:
        """
        对单条记录执行包装后的 Function 逻辑。
        子类必须实现并返回 downstream 的输出数据，
        可以是单条记录或记录列表。
        :param record: 上游传入的数据
        :return: 下游记录或记录列表
        """
        ...

    def teardown(self) -> None:
        """
        Operator 级别的清理钩子。
        默认调用底层 Function 的 close() 方法。
        """
        try:
            self.fn.close()
        except Exception:
            pass

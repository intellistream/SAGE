from abc import abstractmethod
from typing import Any

from sage.common.core.functions.base_function import BaseFunction


class BatchFunction(BaseFunction):
    """
    批处理函数基类

    和SourceFunction一样简单，只需要实现execute方法。
    当execute返回None时，BatchOperator会自动发送停止信号。

    流量控制通过Queue的自然阻塞机制实现，无需额外同步。
    """

    @abstractmethod
    def execute(self) -> Any:
        """
        执行批处理函数逻辑

        Returns:
            Any: 生产的数据，如果已完成则返回None
        """
        pass

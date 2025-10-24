from abc import abstractmethod
from typing import Any

from sage.common.core.functions.base_function import BaseFunction


class SourceFunction(BaseFunction):
    """
    源函数基类 - 数据生产者

    源函数不接收输入数据，只产生输出数据
    通常用于读取文件、数据库、API等外部数据源
    """

    @abstractmethod
    def execute(self, data=None) -> Any:
        """
        执行源函数逻辑，生产数据

        Args:
            data: 输入数据（对于源函数通常为 None，但保留参数以符合基类接口）

        Returns:
            生产的数据
        """
        pass

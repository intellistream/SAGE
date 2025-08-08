from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING
from sage.core.api.function.base_function import BaseFunction

class BatchFunction(BaseFunction):
    """
    批处理函数基类
    
    和SourceFunction一样简单，只需要实现execute方法。
    当execute返回None时，BatchOperator会自动发送停止信号。
    """

    @abstractmethod
    def execute(self) -> Any:
        """
        执行批处理函数逻辑
        
        Returns:
            Any: 生产的数据，如果已完成则返回None
        """
        pass


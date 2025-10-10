from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from sage.kernel.api.function.base_function import BaseFunction

if TYPE_CHECKING:
    from sage.kernel.runtime.communication.metronome import Metronome


class BatchFunction(BaseFunction):
    """
    批处理函数基类

    和SourceFunction一样简单，只需要实现execute方法。
    当execute返回None时，BatchOperator会自动发送停止信号。
    """

    # 子类可以设置这个属性来启用metronome同步
    use_metronome: bool = False
    metronome: Optional["Metronome"] = None

    @abstractmethod
    def execute(self) -> Any:
        """
        执行批处理函数逻辑

        Returns:
            Any: 生产的数据，如果已完成则返回None
        """
        pass

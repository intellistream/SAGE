from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Type, Union

from sage.core.api.function.base_function import BaseFunction

if TYPE_CHECKING:
    from sage.core.communication.metronome import Metronome


class SinkFunction(BaseFunction):
    """
    汇聚函数基类 - 数据消费者

    汇聚函数接收输入数据，通常不产生输出
    用于数据存储、发送、打印等终端操作
    """

    # 子类可以设置这个属性来启用metronome同步
    use_metronome: bool = False
    metronome: Optional["Metronome"] = None

    @abstractmethod
    def execute(self, data: Any) -> None:
        """
        执行汇聚操作

        Args:
            data: 输入数据
        """
        pass

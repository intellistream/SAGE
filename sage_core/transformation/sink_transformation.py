from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage_core.transformation.base_transformation import BaseTransformation
if TYPE_CHECKING:
    from sage_core.operator.base_operator import BaseOperator
    from sage_core.operator.sink_operator import SinkOperator
    from sage_core.function.base_function import BaseFunction
    from sage_core.api.env import BaseEnvironment


class SinkTransformation(BaseTransformation):
    """汇聚变换 - 数据消费者"""
    
    def __init__(
        self,
        env: 'BaseEnvironment',
        function: Type['BaseFunction'],
        *args,
        batch_size: int = 1,  # Sink 特有的批处理大小， 可以减少系统调用次数
        **kwargs
    ):
        self.batch_size = batch_size
        super().__init__(env, function, *args, **kwargs)

    @property
    def delay(self) -> float:
        return 0.1  # 固定的内部事件监听循环延迟

    def get_operator_class(self) -> Type['BaseOperator']:
        return SinkOperator

    def is_spout(self) -> bool:
        return False
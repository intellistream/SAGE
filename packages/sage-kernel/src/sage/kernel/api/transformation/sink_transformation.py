from __future__ import annotations

from typing import TYPE_CHECKING

from sage.kernel.api.operator.sink_operator import SinkOperator
from sage.kernel.api.transformation.base_transformation import BaseTransformation

if TYPE_CHECKING:
    from sage.common.core.functions import BaseFunction
    from sage.kernel.api.base_environment import BaseEnvironment


class SinkTransformation(BaseTransformation):
    """汇聚变换 - 数据消费者"""

    def __init__(
        self,
        env: BaseEnvironment,
        function: type[BaseFunction],
        *args,
        batch_size: int = 1,  # Sink 特有的批处理大小， 可以减少系统调用次数
        **kwargs,
    ):
        self.operator_class = SinkOperator
        self.batch_size = batch_size
        super().__init__(env, function, *args, **kwargs)

    @property
    def is_sink(self) -> bool:
        return True

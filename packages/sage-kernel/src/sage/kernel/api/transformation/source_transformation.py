from __future__ import annotations

from typing import TYPE_CHECKING

from sage.kernel.api.operator.source_operator import SourceOperator
from sage.kernel.api.transformation.base_transformation import BaseTransformation

if TYPE_CHECKING:
    from sage.common.core.functions import BaseFunction
    from sage.kernel.api.base_environment import BaseEnvironment


class SourceTransformation(BaseTransformation):
    """源变换 - 数据生产者"""

    def __init__(
        self,
        env: BaseEnvironment,
        function: type[BaseFunction],
        *args,
        delay: float = 1.0,  # Source 节点可配置延迟
        **kwargs,
    ):
        self.operator_class = SourceOperator
        self._delay = delay
        super().__init__(env, function, *args, **kwargs)

    @property
    def delay(self) -> float:
        return self._delay

    @property
    def is_spout(self) -> bool:
        return True

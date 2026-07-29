from __future__ import annotations

from typing import TYPE_CHECKING

from sage.kernel.api.operator.flatmap_operator import FlatMapOperator
from sage.kernel.api.transformation.base_transformation import BaseTransformation

if TYPE_CHECKING:
    from sage.common.core.functions import BaseFunction
    from sage.kernel.api.base_environment import BaseEnvironment


class FlatMapTransformation(BaseTransformation):
    """扁平映射变换 - 一对多数据变换"""

    def __init__(self, env: BaseEnvironment, function: type[BaseFunction], *args, **kwargs):
        self.operator_class = FlatMapOperator
        super().__init__(env, function, *args, **kwargs)

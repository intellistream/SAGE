from __future__ import annotations

from typing import TYPE_CHECKING, Type

from sage.core.operator.flatmap_operator import FlatMapOperator
from sage.core.transformation.base_transformation import BaseTransformation

if TYPE_CHECKING:
    from sage.core.api.base_environment import BaseEnvironment
    from sage.core.api.function.base_function import BaseFunction


class FlatMapTransformation(BaseTransformation):
    """扁平映射变换 - 一对多数据变换"""

    def __init__(
        self, env: "BaseEnvironment", function: Type["BaseFunction"], *args, **kwargs
    ):
        self.operator_class = FlatMapOperator
        super().__init__(env, function, *args, **kwargs)

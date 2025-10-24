from __future__ import annotations

from typing import TYPE_CHECKING, Type

from sage.kernel.api.operator.filter_operator import FilterOperator
from sage.kernel.api.transformation.base_transformation import BaseTransformation

if TYPE_CHECKING:
    from sage.kernel.api.base_environment import BaseEnvironment
    from sage.common.core.functions import BaseFunction


class FilterTransformation(BaseTransformation):
    """过滤变换 - 数据过滤"""

    def __init__(
        self, env: "BaseEnvironment", function: Type["BaseFunction"], *args, **kwargs
    ):
        self.operator_class = FilterOperator
        super().__init__(env, function, *args, **kwargs)

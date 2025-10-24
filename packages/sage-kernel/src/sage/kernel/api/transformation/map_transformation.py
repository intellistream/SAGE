from __future__ import annotations

from typing import TYPE_CHECKING, Type

from sage.kernel.api.operator.map_operator import MapOperator
from sage.kernel.api.transformation.base_transformation import BaseTransformation

if TYPE_CHECKING:
    from sage.kernel.api.base_environment import BaseEnvironment
    from sage.common.core.functions import BaseFunction


class MapTransformation(BaseTransformation):
    """映射变换 - 一对一数据变换"""

    def __init__(
        self, env: "BaseEnvironment", function: Type["BaseFunction"], *args, **kwargs
    ):
        self.operator_class = MapOperator
        super().__init__(env, function, *args, **kwargs)

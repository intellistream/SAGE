from __future__ import annotations

from typing import (TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Type,
                    Union)

from sage.core.operator.filter_operator import FilterOperator
from sage.core.transformation.base_transformation import BaseTransformation

if TYPE_CHECKING:
    from sage.core.api.base_environment import BaseEnvironment
    from sage.core.api.function.base_function import BaseFunction
    from sage.core.operator.base_operator import BaseOperator


class FilterTransformation(BaseTransformation):
    """过滤变换 - 数据过滤"""

    def __init__(
        self, env: "BaseEnvironment", function: Type["BaseFunction"], *args, **kwargs
    ):
        self.operator_class = FilterOperator
        super().__init__(env, function, *args, **kwargs)

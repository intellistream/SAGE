from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from core.transformation.base_transformation import BaseTransformation
from core.operator.filter_operator import FilterOperator
if TYPE_CHECKING:
    from core.operator.base_operator import BaseOperator
    from core.function.base_function import BaseFunction
    from core.environment.base_environment import BaseEnvironment




class FilterTransformation(BaseTransformation):
    """过滤变换 - 数据过滤"""
    
    def __init__(
        self,
        env: 'BaseEnvironment',
        function: Type['BaseFunction'],
        *args,
        **kwargs
    ):
        self.operator_class = FilterOperator
        super().__init__(env, function, *args, **kwargs)

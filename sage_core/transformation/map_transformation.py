from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage_core.transformation.base_transformation import BaseTransformation
from sage_core.operator.map_operator import MapOperator
if TYPE_CHECKING:
    from sage_core.function.base_function import BaseFunction
    from sage_core.api.base_environment import BaseEnvironment

class MapTransformation(BaseTransformation):
    """映射变换 - 一对一数据变换"""
    
    def __init__(
        self,
        env: 'BaseEnvironment',
        function: Type['BaseFunction'],
        *args,
        **kwargs
    ):
        self.operator_class = MapOperator
        super().__init__(env, function, *args, **kwargs)

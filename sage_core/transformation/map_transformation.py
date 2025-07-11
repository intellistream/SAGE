from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage_core.transformation.base_transformation import BaseTransformation
if TYPE_CHECKING:
    from sage_core.operator.map_operator import MapOperator
    from sage_core.api.base_function import BaseFunction
    from sage_core.api.env import BaseEnvironment

class MapTransformation(BaseTransformation):
    """映射变换 - 一对一数据变换"""
    
    def __init__(
        self,
        env: 'BaseEnvironment',
        function: Type['BaseFunction'],
        *args,
        **kwargs
    ):
        super().__init__(env, function, *args, **kwargs)

    @property
    def operator_class(self):
        """获取对应的操作符类"""
        return MapOperator
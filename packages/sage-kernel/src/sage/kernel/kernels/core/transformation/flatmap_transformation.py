from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage.kernel.kernels.core.transformation.base_transformation import BaseTransformation
from sage.kernel.kernels.core.operator.flatmap_operator import FlatMapOperator
if TYPE_CHECKING:
    from sage.kernel.api.function.base_function import BaseFunction
    from sage.kernel.api.base_environment import BaseEnvironment


class FlatMapTransformation(BaseTransformation):
    """扁平映射变换 - 一对多数据变换"""
    
    def __init__(
        self,
        env: 'BaseEnvironment',
        function: Type['BaseFunction'],
        *args,
        **kwargs
    ):
        self.operator_class = FlatMapOperator
        super().__init__(env, function, *args, **kwargs)

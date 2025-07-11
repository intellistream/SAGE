from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage_core.transformation.base_transformation import BaseTransformation
if TYPE_CHECKING:
    from sage_core.operator.base_operator import BaseOperator
    from sage_core.operator.flatmap_operator import FlatMapOperator
    from sage_core.api.base_function import BaseFunction
    from sage_core.api.env import BaseEnvironment


class FlatMapTransformation(BaseTransformation):
    """扁平映射变换 - 一对多数据变换"""
    
    def __init__(
        self,
        env: 'BaseEnvironment',
        function: Type['BaseFunction'],
        *args,
        **kwargs
    ):
        super().__init__(env, function, *args, **kwargs)

    @property
    def delay(self) -> float:
        return 0.1  # 固定的内部事件监听循环延迟

    def get_operator_class(self) -> Type['BaseOperator']:
        return FlatMapOperator

    def is_spout(self) -> bool:
        return False
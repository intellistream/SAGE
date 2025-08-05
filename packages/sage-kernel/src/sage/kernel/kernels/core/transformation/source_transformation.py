from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage.kernel.kernels.core.transformation.base_transformation import BaseTransformation
from sage.kernel.kernels.core.operator.source_operator import SourceOperator
if TYPE_CHECKING:
    from sage.kernel.api.function.base_function import BaseFunction
    from sage.kernel.api.base_environment import BaseEnvironment


class SourceTransformation(BaseTransformation):
    """源变换 - 数据生产者"""
    
    def __init__(
        self,
        env: 'BaseEnvironment',
        function: Type['BaseFunction'],
        *args,
        delay: float = 1.0,  # Source 节点可配置延迟
        **kwargs
    ):
        self.operator_class = SourceOperator
        self._delay = delay
        super().__init__(env, function, *args, **kwargs)

    @property
    def delay(self) -> float:
        return self._delay
    
    @property
    def is_spout(self) -> bool:
        return True

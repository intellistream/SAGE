from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage_core.transformation.base_transformation import BaseTransformation
if TYPE_CHECKING:
    from sage_core.operator.source_operator import SourceOperator
    from sage_core.api.base_function import BaseFunction
    from sage_core.api.env import BaseEnvironment


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
        return True  # 固定的内部事件监听循环延迟
    
    @property
    def operator_class(self):
        """获取对应的操作符类"""
        return SourceOperator
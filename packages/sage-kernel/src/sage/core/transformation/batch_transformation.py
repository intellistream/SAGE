from __future__ import annotations
from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage.core.transformation.base_transformation import BaseTransformation
from sage.core.operator.batch_operator import BatchOperator
if TYPE_CHECKING:
    from sage.core.api.function.base_function import BaseFunction
    from sage.core.api.base_environment import BaseEnvironment


class BatchTransformation(BaseTransformation):
    """批处理变换 - 预定义批次大小的数据生产者"""
    
    def __init__(
        self,
        env: 'BaseEnvironment',
        function: Type['BaseFunction'],
        *args,
        delay: float = 0.1,  # 批处理节点通常处理速度更快
        progress_log_interval: int = 100,  # 进度日志间隔
        **kwargs
    ):
        self.operator_class = BatchOperator
        self._delay = delay
        self._progress_log_interval = progress_log_interval
        super().__init__(env, function, *args, **kwargs)

    @property
    def delay(self) -> float:
        return self._delay
    
    @property 
    def progress_log_interval(self) -> int:
        return self._progress_log_interval
    
    @property
    def is_spout(self) -> bool:
        return True

    def get_operator_kwargs(self) -> dict:
        """获取创建算子时需要的额外参数"""
        kwargs = {
            'progress_log_interval': self._progress_log_interval
        }
        return kwargs

from typing import Type, TYPE_CHECKING
from sage.kernel.kernels.jobmanager.utils.name_server import get_name

if TYPE_CHECKING:
    from sage.kernel.kernels.core.operator.base_operator import BaseOperator
    from sage.kernel.kernels.runtime.factory.function_factory import FunctionFactory
    from sage.kernel.kernels.runtime.task_context import TaskContext


class OperatorFactory:
    # 由transformation初始化
    def __init__(self, 
                 operator_class: Type['BaseOperator'],
                 function_factory: 'FunctionFactory',
                 basename: str = None,
                 env_name:str = None,
                 remote:bool = False,
                 **operator_kwargs):
        self.operator_class = operator_class
        self.operator_kwargs = operator_kwargs  # 保存额外的operator参数
        self.function_factory = function_factory
        self.env_name = env_name
        self.basename = get_name(basename) or get_name(self.function_factory.function_class.__name__)
        self.remote = remote

    def create_operator(self, runtime_context: 'TaskContext') -> 'BaseOperator':
            operator_class = self.operator_class
            operator_instance = operator_class(
                self.function_factory,
                runtime_context,
                **self.operator_kwargs
            )
            return operator_instance
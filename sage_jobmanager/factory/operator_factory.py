from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage_utils.name_server import get_name
from sage_utils.custom_logger import CustomLogger
if TYPE_CHECKING:
    from sage_core.operator.base_operator import BaseOperator
    from sage_core.function.base_function import BaseFunction
    from ray.actor import ActorHandle
    from sage_jobmanager.factory.function_factory import FunctionFactory
    from sage_jobmanager.factory.runtime_context import RuntimeContext
import ray

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

    def create_operator(self, runtime_context: 'RuntimeContext') -> 'BaseOperator':
            Operator_class = self.operator_class
            operator_instance = Operator_class(
                self.function_factory,
                runtime_context,
                **self.operator_kwargs
            )
            return operator_instance
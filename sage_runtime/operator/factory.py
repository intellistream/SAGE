from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage_utils.name_server import get_name
from sage_utils.custom_logger import CustomLogger
from sage_runtime.operator.operator_wrapper import OperatorWrapper
if TYPE_CHECKING:
    from sage_core.operator.base_operator import BaseOperator
    from sage_core.function.base_function import BaseFunction
    from ray.actor import ActorHandle
    from sage_runtime.function.factory import FunctionFactory
    from sage_runtime.runtime_context import RuntimeContext
import ray

class OperatorFactory:
    # 由transformation初始化
    def __init__(self, 
                 operator_class: Type['BaseOperator'],
                 function_factory: 'FunctionFactory',
                 basename: str = None,
                 env_name:str = None,
                 remote:bool = False):
        self.operator_class = operator_class
        self.function_factory = function_factory
        self.env_name = env_name
        self.basename = get_name(basename) or get_name(self.function_factory.function_class.__name__)
        self.remote = remote

    def create_operator(self, 
                       name: str,
                       runtime_context: 'RuntimeContext',
                       **additional_kwargs) -> 'OperatorWrapper':
        """
        创建operator实例
        
        Args:
            session_folder: 会话文件夹
            name: 节点名称
            **additional_kwargs: 额外的关键字参数
            
        Returns:
            BaseOperator: 创建的operator实例
        """
        # 创建logger用于调试
        logger = CustomLogger(
            filename=f"OperatorFactory_{name}",
            console_output="WARNING",
            file_output="DEBUG",
            global_output="WARNING",
            name=f"OperatorFactory_{name}",
            env_name = self.env_name
        )
        
        try:
            if self.remote:
                Operator_class = ray.remote(self.operator_class)
                operator_instance = Operator_class.remote(
                    self.function_factory,
                    runtime_context,
                    **additional_kwargs
                )
                logger.debug(f"Building Ray Actor operator instance: {self.operator_class.__name__}")
            else:
                Operator_class = self.operator_class
                operator_instance = Operator_class(
                    self.function_factory,
                    runtime_context,
                    **additional_kwargs
                )
                logger.debug(f"Building local operator instance: {self.operator_class.__name__}")


            # 用OperatorWrapper包装
            wrapped_operator = OperatorWrapper(operator_instance, name, self.env_name)
            logger.debug(f"Wrapped operator with OperatorWrapper")
            
            return wrapped_operator
            
        except Exception as e:
            logger.error(f"Failed to create operator: {e}", exc_info=True)
            raise
            
        except Exception as e:
            logger.error(f"Failed to create operator: {e}", exc_info=True)
            raise
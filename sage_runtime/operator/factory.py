from typing import List, Type, Union, Tuple, Dict, Set, TYPE_CHECKING, Any, Optional
from sage_utils.name_server import get_name
from sage_utils.custom_logger import CustomLogger
from sage_runtime.operator.operator_wrapper import OperatorWrapper
if TYPE_CHECKING:
    from sage_core.core.operator.base_operator import BaseOperator
    from sage_core.api.base_function import BaseFunction
    from ray.actor import ActorHandle

import ray

class OperatorFactory:
    """
    Operator工厂类，负责创建各种类型的Operator实例
    可以被序列化传递给Ray Actor
    """

    def __init__(self, 
                 is_spout:bool, 
                 operator_class: Type['BaseOperator'],
                 function_class: Type['BaseFunction'],
                 function_args: Tuple = (),
                 function_kwargs: Dict[str, Any] = None,
                 operator_kwargs: Dict[str, Any] = None,
                 
                 basename: str = None,
                 env_name:str = None):
        """
        初始化OperatorFactory
        
        Args:
            transformation: 变换
            function_class: 函数类（不是实例）
            function_args: 函数构造参数
            function_kwargs: 函数构造关键字参数
            operator_kwargs: operator构造关键字参数
            basename: 基础名称
        """
        self.is_spout = is_spout
        self.operator_class = operator_class

        self.function_class = function_class
        self.function_args = function_args or ()
        self.function_kwargs = function_kwargs or {}
        self.operator_kwargs = operator_kwargs or {}
        self.env_name = env_name
        # 生成基础名称
        if basename is None:
            self.basename = get_name(self.function_class.__name__)
        else:
            self.basename = get_name(basename)

    def build_instance(self, 
                       session_folder: Optional[str] = None, 
                       name: Optional[str] = None,
                       remote: bool = False,
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
        name = name or self.basename
        # 创建logger用于调试
        logger = CustomLogger(
            filename=f"OperatorFactory_{name}",
            session_folder=session_folder,
            console_output="WARNING",
            file_output="DEBUG",
            global_output="WARNING",
            name=f"OperatorFactory_{name}",
            env_name = self.env_name
        )
        
        try:
            # 合并所有kwargs
            merged_function_kwargs = {
                **self.function_kwargs,
                'session_folder': session_folder or CustomLogger.get_session_folder(),
                'name': name,
                'env_name': self.env_name,  # 添加env_name到function_kwargs
                **additional_kwargs
            }
            merged_operator_kwargs = {
                **self.operator_kwargs,
                'session_folder': session_folder or CustomLogger.get_session_folder(),
                'name': name,
                'env_name': self.env_name,  # 添加env_name到operator_kwargs
                **additional_kwargs
            }
            
            if remote:
                # 创建Ray Actor版本的Operator
                # 将function类和参数传递给operator，让operator自己创建function实例
                Operator_class = ray.remote(self.operator_class)
                operator_instance = Operator_class.remote(
                    function_class=self.function_class,
                    function_args=self.function_args,
                    function_kwargs=merged_function_kwargs,
                    **merged_operator_kwargs
                )
                logger.debug(f"Created Ray Actor operator instance: {self.operator_class.__name__}")
            else:
                # 创建本地Operator实例
                # 同样传递function类和参数
                operator_instance = self.operator_class(
                    function_class=self.function_class,
                    function_args=self.function_args,
                    function_kwargs=merged_function_kwargs,
                    **merged_operator_kwargs
                )
                logger.debug(f"Created local operator instance: {self.operator_class.__name__}")

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
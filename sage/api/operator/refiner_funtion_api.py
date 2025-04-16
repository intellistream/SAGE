from abc import abstractmethod
from sage.api.operator.base_operator_api import BaseOperator
class RefinerFunction(BaseOperator):
    """
    Operator for compress the prompt to speed up inference
    """
    def __init__(self):
        """
        :param model_name: 模型名称/路径
        """
        super().__init__()

    @abstractmethod
    def execute(self):
        raise NotImplementedError("RefinerFunction must implement execute().")
from abc import abstractmethod
from sage.api.operator.base_operator_api import BaseOperator
class RefinerFuction(BaseOperator):

    def __init__(self):
        """
        :param model_name: 模型名称/路径
        """
        super().__init__()

    @abstractmethod
    def execute(self):
        raise NotImplementedError("RefinerFunction must implement execute().")
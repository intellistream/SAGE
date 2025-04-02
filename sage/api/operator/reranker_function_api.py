from abc import abstractmethod
from sage.api.operator.base_operator_api import BaseOperator
class RerankerFuction(BaseOperator):

    def __init__(self, model_name: str):
        """
        :param model_name: 模型名称/路径
        """
        super().__init__()
        self.model_name = model_name
        self.model = None

    @abstractmethod
    def _load_model(self,model_name):
        pass

    @abstractmethod
    def execute(self, input_data, **kwargs):
        pass
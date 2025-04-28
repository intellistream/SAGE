from sage.api.operator.base_operator_api import BaseOperator


class EvaluateFunction(BaseOperator):
    def __init__(self):
        super().__init__()

    def execute(self, inputs, context=None):
        raise NotImplementedError("EvaluateFunction must implement execute().")
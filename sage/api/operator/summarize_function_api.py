from sage.api.operator.base_operator_api import BaseOperator


class SummarizeFunction(BaseOperator):
    def __init__(self):
        super().__init__()

    def execute(self, inputs, context=None):
        raise NotImplementedError("WriterFunction must implement execute().")
class BaseOperator:
    def __init__(self):
        self.upstream = None
        self.downstream = None
        self._name = self.__class__.__name__

    def set_upstream(self, op):
        self.upstream = op
        if op:
            op.downstream = self

    def set_downstream(self, op):
        self.downstream = op
        if op:
            op.upstream = self

    def get_name(self):
        return self._name

    def execute(self, *args, **kwargs):
        """
        Override this method with actual operator logic in subclasses.
        """
        raise NotImplementedError(f"{self._name}.execute() is not implemented")
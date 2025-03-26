class WriterFunction:
    def __init__(self):
        self.upstream = None
        self.downstream = None

    def set_upstream(self, op):
        self.upstream = op

    def set_downstream(self, op):
        self.downstream = op

    def execute(self, inputs, context=None):
        raise NotImplementedError("WriterFunction must implement execute().")
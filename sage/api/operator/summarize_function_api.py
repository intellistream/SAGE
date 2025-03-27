class SummarizeFunction:
    def __init__(self):
        self.upstream = None
        self.downstream = None

    def execute(self, inputs, context=None):
        raise NotImplementedError("WriterFunction must implement execute().")
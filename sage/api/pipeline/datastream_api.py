class DataStream:
    def __init__(self, operator, pipeline, name=None):
        self.operator = operator
        self.pipeline = pipeline
        self.name = name or f"DataStream_{id(self)}"
        self.upstreams = []

        # Register the operator in the pipeline
        self.pipeline._register_operator(operator)

    def _transform(self, name: str, next_operator_class):
        op = next_operator_class()
        stream = DataStream(op, self.pipeline, name=name)

        # Wire dependencies
        stream.upstreams.append(self)
        self.operator.set_downstream(op)
        op.set_upstream(self.operator)

        return stream

    def retrieve(self, retriever_op):
        return self._transform("retrieve", lambda: retriever_op)

    def construct_prompt(self, prompt_op):
        return self._transform("construct_prompt", lambda: prompt_op)

    def generate_response(self, generator_op):
        return self._transform("generate_response", lambda: generator_op)

    def get_operator(self):
        return self.operator

    def get_upstreams(self):
        return self.upstreams

    def name_as(self, name):
        self.name = name
        return self
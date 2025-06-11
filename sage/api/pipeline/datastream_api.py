from __future__ import annotations
from typing import TYPE_CHECKING, Union, Any
# 只在类型检查时导入，运行时不导入
if TYPE_CHECKING:
    from sage.api.pipeline.pipeline_api import Pipeline
class DataStream:
    def __init__(self, operator, pipeline, name=None):
        self.operator = operator
        self.pipeline = pipeline
        self.name = name or f"DataStream_{id(self)}"
        self.upstreams = []
        self.downstreams=[]
        # Register the operator in the pipeline
        self.pipeline._register_operator(operator)

    def _transform(self, name: str, op, config) -> DataStream:
        new_instance = self.pipeline.operator_factory.create(op, config)
        # op = next_operator_class
        new_stream = DataStream(new_instance, self.pipeline, name=name)
        self.pipeline.data_streams.append(new_stream)
        # Wire dependencies
        new_stream.upstreams.append(self)
        self.downstreams.append(new_stream)
        return new_stream

    def retrieve(self, retriever_op, config)-> DataStream:
        return self._transform("retrieve",  retriever_op, config)

    def construct_prompt(self, prompt_op, config)-> DataStream:
        return self._transform("construct_prompt", prompt_op, config)

    def generate_response(self, generator_op, config)-> DataStream:
        return self._transform("generate_response",  generator_op, config)

    def save_context(self, writer_op, config)-> DataStream:
        return self._transform("save_context",  writer_op, config)
    def sink(self, sink_op, config)-> DataStream:
        return self._transform("sink",  sink_op, config)

    def chunk(self, chunk_op, config)-> DataStream:
        return self._transform("chunk",  chunk_op, config)

    def summarize(self, summarize_op, config)-> DataStream:
        return self._transform("summarize",summarize_op, config)
    def write_mem(self,writer_op, config)-> DataStream:
        return self._transform("write_mem",writer_op, config)

    def generalize(self, generalize_op,op_type)-> DataStream:
        return self._transform(op_type, generalize_op)

    def get_operator(self):
        return self.operator
    def get_upstreams(self):
        return self.upstreams

    def name_as(self, name):
        self.name = name
        return self
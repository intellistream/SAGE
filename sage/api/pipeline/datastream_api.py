from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any

# 只在类型检查时导入，运行时不导入
if TYPE_CHECKING:
    from sage.api.pipeline.pipeline_api import Pipeline
    from sage.api.operator.base_operator_api import BaseOperator
    from sage.api.operator import RetrieverFunction
    from sage.api.operator import PromptFunction
    from sage.api.operator import GeneratorFunction
    from sage.api.operator import WriterFunction
    from sage.api.operator import SinkFunction
    from sage.api.operator import ChunkFunction
    from sage.api.operator import SummarizeFunction
    from sage.archive.operator_wrapper import OperatorWrapper


    
class DataStream:
    name:str
    operator: Type[BaseOperator]
    pipeline: Pipeline
    upstreams: list[DataStream]
    downstreams: list[DataStream]
    def __init__(self, op_class: Type[BaseOperator], pipeline:Pipeline, name:str=None, config:dict=None):
        self.operator = op_class
        self.pipeline = pipeline
        self.name = name or f"DataStream_{id(self)}"
        self.upstreams = []
        self.downstreams=[]
        # Register the operator in the pipeline
        self.pipeline._register_operator(op_class)
        self.config = config or {}
    def _transform(self, name: str, operator_class:Type[BaseOperator], config) -> DataStream:
        # operator_instance = self.pipeline.operator_factory.create(operator_class, config)
        # op = next_operator_class
        new_stream = DataStream(operator_class, self.pipeline, name=name, config = config)
        self.pipeline.data_streams.append(new_stream)
        # Wire dependencies
        new_stream.upstreams.append(self)
        self.downstreams.append(new_stream)
        return new_stream

    def retrieve(self, retriever_class:Type[RetrieverFunction], config)-> DataStream:
        return self._transform("retrieve",  retriever_class, config)

    def construct_prompt(self, prompt_operator_class:Type[PromptFunction], config)-> DataStream:
        return self._transform("construct_prompt", prompt_operator_class, config)

    def generate_response(self, generator_operator_class:Type[GeneratorFunction], config)-> DataStream:
        return self._transform("generate_response",  generator_operator_class, config)

    def save_context(self, writer_operator_class:Type[WriterFunction], config)-> DataStream:
        return self._transform("save_context",  writer_operator_class, config)
    
    def sink(self, sink_operator_class:Type[SinkFunction], config)-> DataStream:
        return self._transform("sink",  sink_operator_class, config)

    def chunk(self, chunk_operator_class:Type[ChunkFunction], config)-> DataStream:
        return self._transform("chunk",  chunk_operator_class, config)

    def summarize(self, summarize_operator_class:Type[SummarizeFunction], config)-> DataStream:
        return self._transform("summarize",summarize_operator_class, config)
    

    def write_mem(self,writer_operator_class:Type[WriterFunction], config)-> DataStream:
        return self._transform("write_mem",writer_operator_class, config)

    def generalize(self, generalize_operator_class,op_type)-> DataStream:
        return self._transform(op_type, generalize_operator_class)

    def get_operator(self):
        return self.operator
    def get_upstreams(self):
        return self.upstreams

    def name_as(self, name):
        self.name = name
        return self
from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any

# 只在类型检查时导入，运行时不导入
if TYPE_CHECKING:
    from sage.api.pipeline.pipeline_api import Pipeline
    from sage.api.operator.base_operator_api import BaseFuction
    from sage.api.operator import RetrieverFunction
    from sage.api.operator import PromptFunction
    from sage.api.operator import GeneratorFunction
    from sage.api.operator import WriterFunction
    from sage.api.operator import SinkFunction
    from sage.api.operator import ChunkFunction



    
class DataStream:
    name:str
    operator: Type[BaseFuction]
    pipeline: Pipeline
    upstreams: list[DataStream]
    downstreams: list[DataStream]
    def __init__(self, op_class: Type[BaseFuction], pipeline:Pipeline, name:str=None, config:dict=None, node_type:str="normal"):
        self.operator = op_class
        self.pipeline = pipeline
        self.name = name or f"DataStream_{id(self)}"
        self.upstreams = []
        self.downstreams=[]
        # Register the operator in the pipeline
        self.pipeline._register_operator(op_class)
        self.config = config or {}
        self.node_type = node_type  # "source", "sink", "normal" or other types

    def _transform(self, name: str, function_class:Type[BaseFuction], config) -> DataStream:
        # operator_instance = self.pipeline.operator_factory.create(function_class, config)
        # op = next_operator_class
        new_stream = DataStream(function_class, self.pipeline, name=name, config = config, node_type="normal")
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
        new_stream = DataStream(sink_operator_class, self.pipeline, name="sink", config = config, node_type="sink")
        self.pipeline.data_streams.append(new_stream)
        # Wire dependencies
        new_stream.upstreams.append(self)
        self.downstreams.append(new_stream)
        return new_stream
    
    def chunk(self, chunk_operator_class:Type[ChunkFunction], config)-> DataStream:
        return self._transform("chunk",  chunk_operator_class, config)

    def rerank(self, rerank_operator_class:Type[BaseFuction], config)-> DataStream:
        return self._transform("rerank", rerank_operator_class, config)
    
    def write_mem(self,writer_operator_class:Type[WriterFunction], config)-> DataStream:
        return self._transform("write_mem",writer_operator_class, config)

    def generalize(self, op_type,generalize_operator_class,config)-> DataStream:
        return self._transform(op_type, generalize_operator_class,config)
    
    def get_operator(self):
        return self.operator
    def get_upstreams(self):
        return self.upstreams

    def name_as(self, name):
        self.name = name
        return self
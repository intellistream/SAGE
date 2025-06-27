from __future__ import annotations
from typing import Type, TYPE_CHECKING, Union, Any

# 只在类型检查时导入，运行时不导入
if TYPE_CHECKING:
    from sage.api.pipeline.pipeline_api import Pipeline
    from sage.api.operator.base_operator_api import BaseFunction
    from sage.api.operator import RetrieverFunction
    from sage.api.operator import PromptFunction
    from sage.api.operator import GeneratorFunction
    from sage.api.operator import WriterFunction
    from sage.api.operator import SinkFunction
    from sage.api.operator import ChunkFunction



    
class DataStream:
    name:str
    function: Union[BaseFunction, Type[BaseFunction] ]
    pipeline: Pipeline
    upstreams: list[DataStream]
    downstreams: list[DataStream]
    def __init__(self, 
                 function: Union[BaseFunction, Type[BaseFunction] ], pipeline:Pipeline, name:str=None, config:dict=None, node_type:str="normal"):
        self.function = function
        self.pipeline = pipeline
        self.name = name or f"DataStream_{id(self)}"
        self.upstreams = []
        self.downstreams=[]
        # Register the operator in the pipeline
        self.pipeline._register_operator(function)
        self.config = config or {}
        self.node_type = node_type  # "source", "sink", "normal" or other types

    def _transform(self, name: str, function:Union[BaseFunction, Type[BaseFunction] ], config) -> DataStream:
        # operator_instance = self.pipeline.operator_factory.create(function, config)
        # op = next_function
        new_stream = DataStream(function, self.pipeline, name=name, config = config, node_type="normal")
        self.pipeline.data_streams.append(new_stream)
        # Wire dependencies
        new_stream.upstreams.append(self)
        self.downstreams.append(new_stream)
        return new_stream

    def retrieve(self, retriever, config)-> DataStream:
        return self._transform("retrieve",  retriever, config)

    def construct_prompt(self, prompt_function, config)-> DataStream:
        return self._transform("construct_prompt", prompt_function, config)

    def generate_response(self, generator_function, config)-> DataStream:
        return self._transform("generate_response",  generator_function, config)

    def save_context(self, writer_function, config)-> DataStream:
        return self._transform("save_context",  writer_function, config)
    
    def sink(self, sink_function, config)-> DataStream:
        new_stream = DataStream(sink_function, self.pipeline, name="sink", config = config, node_type="sink")
        self.pipeline.data_streams.append(new_stream)
        # Wire dependencies
        new_stream.upstreams.append(self)
        self.downstreams.append(new_stream)
        return new_stream
    
    def chunk(self, chunk_function, config)-> DataStream:
        return self._transform("chunk",  chunk_function, config)

    def rerank(self, rerank_function, config)-> DataStream:
        return self._transform("rerank", rerank_function, config)
    
    def write_mem(self,writer_function, config)-> DataStream:
        return self._transform("write_mem",writer_function, config)

    def generalize(self, op_type,generalize_function,config)-> DataStream:
        return self._transform(op_type, generalize_function,config)
    
    def get_function(self):
        return self.function
    def get_upstreams(self):
        return self.upstreams

    def name_as(self, name):
        self.name = name
        return self
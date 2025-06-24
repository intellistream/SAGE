from typing import Tuple, List, Optional
from .. import operator, model, memory, pipeline
from sympy.multipledispatch.dispatcher import source
import logging
import sage
from sage.api.operator.operator_impl.promptor import QAPromptor, SummarizationPromptor
from sage.api.operator.operator_impl.generator import OpenAIGenerator, HFGenerator
from sage.api.operator.operator_impl.reranker import BGEReranker, LLMbased_Reranker
import time
from sage.api.operator.operator_impl.refiner import AbstractiveRecompRefiner
from sage.api.operator.operator_impl.source import FileSource
from sage.api.operator.operator_impl.sink import TerminalSink, FileSink, RetriveSink
# from sage.api.operator.operator_impl.writer import LongTimeWriter
from sage.api.operator.operator_impl.retriever import DenseRetriever
from sage.api.operator.operator_impl.sink import TerminalSink
from sage.api.operator import Data
from typing import Tuple, List
import yaml
import ray

from ..model import apply_generator_model

query_pipeline = None

class StaticSource(operator.SourceFunction):
    def __init__(self, input_query: str):
        super().__init__()
        self.query = input_query

    def execute(self, context=None) -> Data[str]:
        return Data(self.query)

    def get_query(self):
        return self.query

    def set_query(self, query):
        self.query = query

def run_query(query: str, config=None) -> str:
    """
    High-level entry point for users to execute a query using a submitted pipeline.
    Supports optional session for STM-based memory.
    """
    operator_cls_mapping = {
        "StaticSource": StaticSource,
        "OpenAIGenerator": OpenAIGenerator,
        "HFGenerator": HFGenerator,
        "SimpleRetriever": DenseRetriever,
        "QAPromptor": QAPromptor,
        "SummarizationPromptor": SummarizationPromptor,
        "AbstractiveRecompRefiner": AbstractiveRecompRefiner,
        "BGEReranker": BGEReranker,
        "LLMbased_Reranker": LLMbased_Reranker,
        "TerminalSink": TerminalSink,
        "FileSource": FileSource,
        # "LongTimeWriter": LongTimeWriter,
        "RetriveSink": RetriveSink,
    }

    global query_pipeline

    if query_pipeline is None:
        query_pipeline = pipeline.Pipeline("query_pipeline")
        print(f"query in run_query{query}")
        query_pipeline.add_operator_config(config)
        query_pipeline.add_operator_cls(operator_cls_mapping)
        query_stream = query_pipeline.add_source(StaticSource,config)
        query_stream.operator.set_query(query)
    else :
        query_pipeline.data_streams[0].operator.set_query(query)

    generate_model = apply_generator_model(method = "openai",base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",api_key="sk-b21a67cf99d14ead9d1c5bf8c2eb90ef",model_name="qwen-max",seed=42)
    # generate_model = apply_generator_model(method = "openai",base_url="https://api.siliconflow.cn/v1",api_key="sk-tclnlwchkbzbjhkhwmygvbnvzhxmkamlkekmqqwwfglmmkdu",model_name="THUDM/glm-4-9b-chat",seed=42)
    query_pipeline.submit(config={"is_long_running": False,"query":query},generate_func = generate_model.generate)


    return f"Pipeline submitted for session: {'default'}"

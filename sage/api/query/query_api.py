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
from sage.api.operator.operator_impl.writer import LongTimeWriter
from sage.api.operator.operator_impl.retriever import SimpleRetriever
from sage.api.operator.operator_impl.sink import TerminalSink
from sage.api.operator import Data
from typing import Tuple, List
import yaml
import ray

from ..model import apply_generator_model

query_pipeline = None
@ray.remote
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
#
# class SimpleRetriever(operator.RetrieverFunction):
#     def __init__(self, session_id: Optional[str] = None):
#         super().__init__()
#         self.embedding_model = model.apply_embedding_model("default")
#
#         # session-aware STM name fallback
#         stm_name = f"short_term_memory_{session_id}" if session_id else "short_term_memory"
#
#         # create session STM if not exists
#         try:
#             memory.create_table(memory_table_name=stm_name, memory_table_backend="kv_store.rocksdb")
#         except Exception:
#             pass
#
#         self.memory_collections = memory.connect(
#             stm_name, "long_term_memory", "dynamic_contextual_memory"
#         )
#         self.retrieval_func = memory.retrieve_func
#
#     def execute(self, input_query: str, context=None) -> Tuple[str, List[str]]:
#         embedding = self.embedding_model.embed(input_query)
#         chunks = self.memory_collections.retrieve(embedding, self.retrieval_func)
#         return input_query, chunks
#
#
# class SimplePromptConstructor(operator.PromptFunction):
#     def __init__(self):
#         super().__init__()
#         self.prompt_constructor = self.set_prompt_constructor("default")
#
#     def execute(self, inputs: Tuple[str, List[str]], context=None) -> Tuple[str, str]:
#         query, chunks = inputs
#         return query, self.prompt_constructor.construct(query, chunks)
#
#
# class LlamaGenerator(operator.GeneratorFunction):
#     def __init__(self):
#         super().__init__()
#         self.model = model.apply_generator_model("llama_8b")
#
#     def execute(self, combined_prompt: str, context=None) -> str:
#         return self.model.generate(combined_prompt)
#
#
# class ContextWriter(operator.WriterFunction):
#     def __init__(self, session_id: Optional[str] = None):
#         super().__init__()
#         self.embedding_model = model.apply_embedding_model("default")
#         stm_name = f"short_term_memory_{session_id}" if session_id else "short_term_memory"
#
#         # Create if not exists
#         try:
#             memory.create_table(memory_table_name=stm_name, memory_table_backend="kv_store.rocksdb")
#         except Exception:
#             pass
#
#         self.memory_collections = memory.connect(stm_name)
#         self.write_func = memory.write_func
#
#     def execute(self, inputs: Tuple[str, List[str]], context=None) -> None:
#         self.memory_collections.write(inputs, self.write_func)


def run_query(query: str, config=None) -> str:
    """
    High-level entry point for users to execute a query using a submitted pipeline.
    Supports optional session for STM-based memory.
    """
    operator_cls_mapping = {
        "StaticSource": StaticSource,
        "OpenAIGenerator": OpenAIGenerator,
        "HFGenerator": HFGenerator,
        "SimpleRetriever": SimpleRetriever,
        "QAPromptor": QAPromptor,
        "SummarizationPromptor": SummarizationPromptor,
        "AbstractiveRecompRefiner": AbstractiveRecompRefiner,
        "BGEReranker": BGEReranker,
        "LLMbased_Reranker": LLMbased_Reranker,
        "TerminalSink": TerminalSink,
        "FileSource": FileSource,
        "LongTimeWriter": LongTimeWriter,
        "RetriveSink": RetriveSink,
    }

    global query_pipeline

    if query_pipeline is None:
        query_pipeline = pipeline.Pipeline("query_pipeline")
        print(f"query in run_query{query}")
        query_pipeline.add_operator_config(config)
        query_pipeline.add_operator_cls(operator_cls_mapping)
        source = StaticSource.remote(query)
        query_stream = query_pipeline.add_source(source)
    else :
        query_pipeline.data_streams[0].operator.set_query.remote(query)
        # query_pipeline.add_operator_config(config)





    # pipeline : source -> ?
    # query_and_chunks_stream = query_stream.retrieve(SimpleRetriever.remote(config))
    # # Step 3: Construct a prompt by combining the query and the retrieved chunks
    # prompts = query_and_chunks_stream.construct_prompt(QAPromptor.remote(config))
    # # Step 4: Generate the final response using a language model
    # response = prompts.generate_response(OpenAIGenerator.remote(config))
    # memory_write = response.write_mem(LongTimeWriter.remote(config))
    # sink_stream = memory_write.sink(TerminalSink.remote(config))

    generate_model = apply_generator_model(method = "openai",base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",api_key="sk-b21a67cf99d14ead9d1c5bf8c2eb90ef",model_name="qwen-max",seed=42)
    # generate_model = apply_generator_model(method = "openai",base_url="https://api.siliconflow.cn/v1",api_key="sk-tclnlwchkbzbjhkhwmygvbnvzhxmkamlkekmqqwwfglmmkdu",model_name="THUDM/glm-4-9b-chat",seed=42)
    query_pipeline.submit(config={"is_long_running": False,"query":query},generate_func = generate_model.generate)


    return f"Pipeline submitted for session: {'default'}"

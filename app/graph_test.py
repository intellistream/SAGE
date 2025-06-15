# python -m app.datastream_rag_pipeline


# 导入 Sage 中的 Pipeline 和相关组件
import logging
import time
from typing import Tuple, List, Type, TYPE_CHECKING, Union, Any
import yaml
# import ray
import asyncio
# from ray import serve
from sage.api.pipeline import Pipeline
from sage.api.memory.memory_service import MemoryManagerService
from sage.api.operator.operator_impl.promptor import QAPromptor
from sage.api.operator.operator_impl.generator import OpenAIGenerator
from sage.api.operator.operator_impl.reranker import BGEReranker
from sage.api.operator.operator_impl.refiner import AbstractiveRecompRefiner
from sage.api.operator.operator_impl.source import FileSource
from sage.api.operator.operator_impl.sink import TerminalSink, FileSink
from sage.api.operator.operator_impl.writer import LongTimeWriter
from sage.api.operator.operator_impl.retriever import SimpleRetriever
from sage.api.operator.operator_impl.sink import TerminalSink
from sympy.multipledispatch.dispatcher import source
from sage.api.graph import SageGraph
if TYPE_CHECKING:
    from sage.api.pipeline.datastream_api import DataStream

# 加载配置文件
def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

config = load_config('./app/graph_config.yaml')  # 加载配置文件
logging.basicConfig(level=logging.INFO)

def init_graph():
    graph = SageGraph(name = "example_graph", config=config["graph"])
    graph.add_node("filesource",
                    input_streams=None, 
                    output_streams="query_stream", 
                    operator_class=FileSource,
                    # operator_config=config["source"])
                    operator_config=config)
    graph.add_node("promptor",
                    input_streams="query_stream", 
                    output_streams="prompt_stream", 
                    operator_class=QAPromptor,
                    operator_config=config)
                    #operator_config=config["promptor"])
    graph.add_node("generator",
                    input_streams="prompt_stream", 
                    output_streams="response_stream", 
                    operator_class=OpenAIGenerator,
                    operator_config=config)
                    #operator_config=config["generator"])
    
    graph.add_node("sink",
                    input_streams="response_stream", 
                    output_streams=None, 
                    operator_class=FileSink,
                    operator_config=config)
                    #operator_config=config["sink"])
    
    graph.submit()

    # 等待管道运行一段时间
    time.sleep(100)

# 调用异步函数初始化内存和管道
if __name__ == '__main__':
    init_graph()

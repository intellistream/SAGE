# python -m app.datastream_rag_pipeline


# 导入 Sage 中的 Pipeline 和相关组件
import logging
import time
from typing import Tuple, List, Type, TYPE_CHECKING, Union, Any
import yaml
import ray
import asyncio
from ray import serve
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
from sage.core.neuromem.memory_manager import MemoryManager
from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder
if TYPE_CHECKING:
    from sage.api.pipeline.datastream_api import DataStream

# 加载配置文件
def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

config = load_config('./app/config.yaml')  # 加载配置文件
logging.basicConfig(level=logging.INFO)

default_model = MockTextEmbedder(fixed_dim=128)
manager = MemoryManager()

col = manager.create_collection(
    name="vdb_test",
    backend_type="VDB",
    embedding_model=default_model,
    dim=128,
    description="test vdb collection 0"
)

col.add_metadata_field("owner")
col.add_metadata_field("show_type")

texts = [
            ("hello world", {"owner": "ruicheng", "show_type": "text"}),
            ("你好，世界", {"owner": "Jun", "show_type": "text"}),
            ("こんにちは、世界", {"owner": "Lei", "show_type": "img"}),
        ]
inserted_ids = [col.insert(text, metadata) for text, metadata in texts]
col.create_index( # type: ignore
    index_name="vdb_index"
)
config["retriever"]["ltm_collection"] = col

def init_memory_and_pipeline():

    # 创建一个新的管道实例
    pipeline = Pipeline(name="example_pipeline", use_ray=False)
    # 步骤 1: 定义数据源（例如，来自用户的查询）
    query_stream: DataStream = pipeline.add_source(source_class=FileSource, config=config)  # 从文件源读取数据
    # 步骤 2: 使用 SimpleRetriever 从向量内存中检索相关数据块
    query_and_chunks_stream: DataStream = query_stream.retrieve(SimpleRetriever, config)

    # 步骤 3: 使用 QAPromptor 构建查询提示
    prompt_stream: DataStream = query_and_chunks_stream.construct_prompt(QAPromptor, config)


    # 步骤 4: 使用 OpenAIGenerator 生成最终的响应
    response_stream:DataStream = prompt_stream.generate_response(OpenAIGenerator, config)

    # 步骤 5: 输出到终端或文件
    sink_stream:DataStream = response_stream.sink(FileSink, config)

    # 提交管道到 SAGE 运行时
    pipeline.submit(config={"is_long_running": True})

    # 等待管道运行一段时间
    time.sleep(100)

# 调用异步函数初始化内存和管道
if __name__ == '__main__':
    init_memory_and_pipeline()

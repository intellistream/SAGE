# python -m app.datastream_rag_pipeline


# 导入 Sage 中的 Pipeline 和相关组件
import logging
import time

from typing import Tuple, List, Type, TYPE_CHECKING, Union, Any
import yaml
import ray
import asyncio
# from ray import serve
from sage.api.pipeline import Pipeline
# from sage.api.memory.memory_service import MemoryManagerService

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


if TYPE_CHECKING:
    from sage.api.pipeline.datastream_api import DataStream

# # 初始化 Ray 并设置日志级别
# ray.init(
#     logging_level=logging.CRITICAL,  # 设置 Ray 日志为 CRITICAL 级别，只显示关键日志
# )
# logging.basicConfig(level=logging.DEBUG)  # 设置基础日志级别为 DEBUG

# # 关闭并启动 Ray 服务
# serve.shutdown()
# serve.start(detached=True)

# # 创建 MemoryManagerService 并启动应用
# app = MemoryManagerService.bind()
# serve.run(app, name="MemoryApp")

# # 获取 MemoryManagerService 的句柄，供后续使用
# manager_handle = serve.get_deployment_handle(deployment_name="MemoryManagerService", app_name="MemoryApp")


# 加载配置文件
def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

config = load_config('./app/config.yaml')  # 加载配置文件
logging.basicConfig(level=logging.DEBUG)




# 创建collection，collection应连接到retriever
from sage.core.neuromem.memory_manager import MemoryManager
from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder

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

config["collection"] = col
result = col.retrieve("世界", topk=2, index_name="vdb_index")# type: ignore 
for i in result:
    print(i)
# print() 

# # ---- Initialize and Submit Pipeline ----
# # 创建新的数据流管道实例
# pipeline = Pipeline(name="example_pipeline", use_ray=True)

# # 步骤 1: 定义数据源（例如，来自用户的查询）
# query_stream:DataStream = pipeline.add_source(source_class=FileSource, config=config)  # 从文件源读取数据

# # 步骤 2: 使用 SimpleRetriever 从向量内存中检索相关数据块
# query_and_chunks_stream:DataStream = query_stream.retrieve(SimpleRetriever, config)

# # 步骤 3: 使用 QAPromptor 构建查询提示
# prompt_stream:DataStream = query_and_chunks_stream.construct_prompt(QAPromptor, config)

# # 步骤 4: 使用 OpenAIGenerator 生成最终的响应
# response_stream:DataStream = prompt_stream.generate_response(OpenAIGenerator, config)

# # 步骤 5: 输出到终端或文件
# sink_stream:DataStream = response_stream.sink(FileSink, config)

# async def init_memory_and_pipeline():
#     # 创建 LTM 内存表，并通过 handle 调用远程方法
#     ltm = await manager_handle.create_table.remote("long_term_memory", default_model)
#     # 这里可以向内存表中存储数据（例如: ltm.store.remote("This is LTM data")）

#     # 配置文件中添加 memory_manager 和 LTM 表
#     config["memory_manager"] = manager_handle
#     config["ltm_collection"] = ltm
#     config["dcm_collection"] = None
#     config["stm_collection"] = None
#     # 创建一个新的管道实例
#     pipeline = Pipeline(name="example_pipeline", use_ray=True)

#     # 步骤 1: 定义数据源（例如，来自用户的查询）
#     query_stream:DataStream = pipeline.add_source(source_class=FileSource, config=config)  # 从文件源读取数据

#     # 步骤 2: 使用 SimpleRetriever 从向量内存中检索相关数据块
#     query_and_chunks_stream:DataStream = query_stream.retrieve(SimpleRetriever, config)

#     # 步骤 3: 使用 QAPromptor 构建查询提示
#     prompt_stream:DataStream = query_and_chunks_stream.construct_prompt(QAPromptor, config)

#     # 步骤 4: 使用 OpenAIGenerator 生成最终的响应
#     response_stream:DataStream = prompt_stream.generate_response(OpenAIGenerator, config)

#     # 步骤 5: 输出到终端或文件
#     sink_stream:DataStream = response_stream.sink(FileSink, config)

#     # 提交管道到 SAGE 运行时
#     pipeline.submit(config={"is_long_running": True})

#     # 等待管道运行一段时间
#     time.sleep(100)

# # 调用异步函数初始化内存和管道
# asyncio.run(init_memory_and_pipeline())



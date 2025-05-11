# python -m app.datastream_rag_pipeline


# 导入 Sage 中的 Pipeline 和相关组件
import logging
import time
from typing import Tuple, List
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

# 初始化 Ray 并设置日志级别
ray.init(
    logging_level=logging.CRITICAL,  # 设置 Ray 日志为 CRITICAL 级别，只显示关键日志
)
logging.basicConfig(level=logging.DEBUG)  # 设置基础日志级别为 DEBUG

# 关闭并启动 Ray 服务
serve.shutdown()
serve.start(detached=True)

# 创建 MemoryManagerService 并启动应用
app = MemoryManagerService.bind()
serve.run(app, name="MemoryApp")

# 获取 MemoryManagerService 的句柄，供后续使用
manager_handle = serve.get_deployment_handle(deployment_name="MemoryManagerService", app_name="MemoryApp")

# 加载配置文件
def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)

config = load_config('./app/config.yaml')  # 加载配置文件
logging.basicConfig(level=logging.DEBUG)

# ---- Initialize and Submit Pipeline ----
# 创建新的数据流管道实例

# 创建长时间存储（LTM）内存表
from sage.core.neuromem.mem_test.memory_api_test_ray import default_model



async def init_memory_and_pipeline():
    # 创建 LTM 内存表，并通过 handle 调用远程方法
    ltm = await manager_handle.create_table.remote("long_term_memory", default_model)
    # 这里可以向内存表中存储数据（例如: ltm.store.remote("This is LTM data")）

    # 配置文件中添加 memory_manager 和 LTM 表
    config["memory_manager"] = manager_handle
    config["ltm_collection"] = ltm
    config["dcm_collection"] = None
    config["stm_collection"] = None
    # 创建一个新的管道实例
    pipeline = Pipeline("example_pipeline")

    # 步骤 1: 定义数据源（例如，来自用户的查询）
    query_stream = pipeline.add_source(FileSource.remote(config))  # 从文件源读取数据

    # 步骤 2: 使用 SimpleRetriever 从向量内存中检索相关数据块
    query_and_chunks_stream = query_stream.retrieve(SimpleRetriever.remote(config))

    # 步骤 3: 使用 QAPromptor 构建查询提示
    prompt_stream = query_and_chunks_stream.construct_prompt(QAPromptor.remote(config))

    # 步骤 4: 使用 OpenAIGenerator 生成最终的响应
    response_stream = prompt_stream.generate_response(OpenAIGenerator.remote(config))

    # 步骤 5: 输出到终端或文件
    sink_stream = response_stream.sink(FileSink.remote(config))

    # 提交管道到 SAGE 运行时
    pipeline.submit(config={"is_long_running": True})

    # 等待管道运行一段时间
    time.sleep(100)

# 调用异步函数初始化内存和管道
asyncio.run(init_memory_and_pipeline())

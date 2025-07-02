# python -m sage_examples.datastream_rag_pipeline


# 导入 Sage 中的 Environment 和相关组件
import logging
import time
from typing import TYPE_CHECKING
from sage.api.env import Environment
from sage_lib import QAPromptor
from sage_lib.function.generator import OpenAIGenerator
from sage_lib import AbstractiveRecompRefiner
from sage_lib.function.source import FileSource
from sage_lib.function.sink import FileSink
# from sage.core.operator.operator_impl.writer import LongTimeWriter
# from sage.core.operator.operator_impl.retriever import SimpleRetriever

from sage.utils.config_loader import load_config
from sage.utils.logging_utils import configure_logging

if TYPE_CHECKING:
    from sage.api.datastream import DataStream

def init_memory_and_pipeline():
    # 创建一个新的管道实例
    pipeline = Environment(name="example_pipeline",
                                             config={"is_long_running": True, "use_ray": False})

    # 步骤 1: 定义数据源（例如，来自用户的查询）
    query_stream: DataStream = pipeline.from_source(FileSource, source_class=FileSource, config=config)  # 从文件源读取数据

    # 步骤 3: 使用 QAPromptor 构建查询提示
    prompt_stream: DataStream = query_stream.map(QAPromptor, config)

    # routestreram = prompt_stream.route(router,config)

    # 步骤 4: 使用 OpenAIGenerator 生成最终的响应
    response_stream: DataStream = prompt_stream.map(OpenAIGenerator, config)
    summarize_stream: DataStream = prompt_stream.map(AbstractiveRecompRefiner, config)

    # 步骤 5: 输出到终端或文件
    sink_stream: DataStream = response_stream.sink(FileSink, config)
    # print(pipeline.get_graph_preview())

    # 提交管道到 SAGE 运行时
    pipeline.execute()

    # 等待管道运行一段时间
    time.sleep(100)


# 调用异步函数初始化内存和管道
if __name__ == '__main__':
    configure_logging(level=logging.INFO)
    # 加载配置并初始化日志
    config = load_config('config_hf.yaml')
    init_memory_and_pipeline()

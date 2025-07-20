# python -m sage_examples.datastream_rag_pipeline


# 导入 Sage 中的 Environment 和相关组件
import logging
import time
from typing import TYPE_CHECKING

from sage_core.api.local_environment import LocalStreamEnvironment
from sage_common_funs.io.sink import FileSink
from sage_common_funs.io.source import FileSource
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.refiner import AbstractiveRecompRefiner

from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging

if TYPE_CHECKING:
    from sage_core.api.datastream import DataStream

def init_memory_and_pipeline():
    # 创建一个新的管道实例
    pipeline = LocalStreamEnvironment()

    # 步骤 1: 定义数据源（例如，来自用户的查询）
    query_stream: DataStream = pipeline.from_source(FileSource,config["source"])  # 从文件源读取数据

    # 步骤 3: 使用 QAPromptor 构建查询提示
    prompt_stream: DataStream = query_stream.map(QAPromptor, config["promptor"])  # 使用 QAPromptor 处理查询

    # routestreram = prompt_stream.route(router,config)

    # 步骤 4: 使用 OpenAIGenerator 生成最终的响应
    response_stream: DataStream = prompt_stream.map(OpenAIGenerator, config["generator"])
    summarize_stream: DataStream = prompt_stream.map(AbstractiveRecompRefiner, config["refiner"])

    # 步骤 5: 输出到终端或文件
    sink_stream: DataStream = response_stream.sink(FileSink, config["sink"])
    # print(pipeline.get_graph_preview())

    # 提交管道到 SAGE 运行时
    pipeline.submit(name="example_pipeline")

    # 等待管道运行一段时间
    time.sleep(100)


# 调用异步函数初始化内存和管道
if __name__ == '__main__':
    configure_logging(level=logging.INFO)
    # 加载配置并初始化日志
    config = load_config('config_hf.yaml')
    init_memory_and_pipeline()

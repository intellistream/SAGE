from dotenv import load_dotenv
import os, time
from sage_core.api.env import LocalEnvironment, RemoteEnvironment
from sage_common_funs.io.source import FileSource
from sage_common_funs.io.chatsink import ChatTerminalSink
from sage_common_funs.map.generator import OpenAIGenerator
from sage_common_funs.map.promptor import QAPromptor
from sage_common_funs.map.retriever import DenseRetriever
from sage_common_funs.map.templater import Templater
from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging



def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    env.set_memory(config=None)
    # 构建数据处理流程
    query_stream = (env
                    .from_source(FileSource, config["source"])  # 拿到原始question
                    .map(Templater)  # 将原始问题转换为AI_Template对象
                    .map(DenseRetriever, config["retriever"])
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"])
                    .sink(ChatTerminalSink, config["sink"])
                    )
    try:
        env.submit()
        env.run_streaming()  # 启动管道
        time.sleep(60)  # 等待管道运行
        env.stop()
    finally:
        env.close()

if __name__ == '__main__':
    # 加载配置
    config = load_config("config_enhanced.yaml")
    pipeline_run()

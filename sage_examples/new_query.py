import logging

from sage_core.api.env import LocalEnvironment
from sage_common_funs.io.sink import TerminalSink
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.retriever import DenseRetriever
from sage_utils.config_loader import load_config
from sage_utils.custom_logger import CustomLogger
from sage_utils.logging_utils import configure_logging


def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    env.set_memory(config=None)  # 初始化内存配置
    # 构建数据处理流程
    manual_source = env.create_source()
    query_and_chunks_stream = manual_source.map(DenseRetriever, config["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"])
    response_stream.sink(TerminalSink, config["sink"])

    # 提交管道并运行
    env.submit(name="example_pipeline")
    env.run_streaming()  # 启动管道

    while(True):
        user_input = input("\n>>> ").strip()
        if user_input.lower() == "exit":
            logging.info("Exiting SAGE Interactive Console")
            print("Goodbye!")
            break
        manual_source.push(user_input)

if __name__ == '__main__':
    CustomLogger.disable_global_console_debug()  # 禁用全局控制台调试输出
    configure_logging(level=logging.INFO)
    # 加载配置并初始化日志
    config = load_config('./config_instance.yaml')
    # 初始化内存并运行管道
    pipeline_run()

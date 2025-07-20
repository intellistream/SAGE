import time

# 导入 Sage 相关模块
from sage_core.api.local_environment import LocalStreamEnvironment
from sage_libs.rag.generator import OpenAIGenerator
from sage_libs.rag.promptor import QAPromptor
from sage_libs.rag.retriever import DenseRetriever
from sage_libs.rag.refiner import AbstractiveRecompRefiner
from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink
from sage_utils.config_loader import load_config


def pipeline_run():
    """创建并运行数据处理管道

    该函数会初始化环境，加载配置，设置数据处理流程，并启动管道。
    """
    # 初始化环境
    env = LocalStreamEnvironment()
    env.set_memory(config=None)  # 初始化内存配置

    # 构建数据处理流程
    query_stream = (env.from_source(FileSource, config["source"])
                    .map(DenseRetriever, config["retriever"])
                    .map(AbstractiveRecompRefiner, config["refiner"])  
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"])
                    .sink(TerminalSink, config["sink"])
                    )

    # 提交管道并运行
    env.submit()
    # env.run_streaming()
    time.sleep(5)
    env.close()


if __name__ == '__main__':
    # 加载配置文件
    config = load_config('config_refiner.yaml')
    
    # 运行管道
    pipeline_run()

import time

# 导入 Sage 相关模块
from sage.core.api.local_environment import LocalBatchEnvironment
from sage.lib.io.sink import TerminalSink
from sage.lib.io.source import FileSource
from sage.lib.rag.generator import OpenAIGenerator
from sage.lib.rag.promptor import QAPromptor
from sage.lib.rag.retriever import DenseRetriever
from sage.lib.rag.refiner import AbstractiveRecompRefiner
from sage.utils.config_loader import load_config


def pipeline_run():
    """创建并运行数据处理管道

    该函数会初始化环境，加载配置，设置数据处理流程，并启动管道。
    """
    # 初始化环境
    env = LocalBatchEnvironment()
    env.set_memory(config=None)  # 初始化内存配置

    # 构建数据处理流程
    query_stream = (env.from_collection(FileSource, config["source"])
                    .map(DenseRetriever, config["retriever"])
                    .map(AbstractiveRecompRefiner, config["refiner"])  
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"]["local"])
                    .sink(TerminalSink, config["sink"])
                    )

    # 提交管道并运行
    env.submit()

if __name__ == '__main__':
    # 加载配置文件
    config = load_config('config_refiner.yaml')
    
    # 运行管道
    pipeline_run()

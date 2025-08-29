import time

# 导入 Sage 相关模块
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import ChromaRetriever
from sage.libs.rag.reranker import BGEReranker
from sage.libs.io_utils.batch import JSONLBatch
from sage.libs.io_utils.sink import TerminalSink
from sage.common.utils.config.loader import load_config


def pipeline_run():
    """创建并运行数据处理管道

    该函数会初始化环境，加载配置，设置数据处理流程，并启动管道。
    """
    # 初始化环境
    env = LocalEnvironment()
    #env.set_memory(config=None)  # 初始化内存配置

    # 构建数据处理流程
    query_stream = (env.from_source(JSONLBatch, config["source"])
                    .map(ChromaRetriever, config["retriever"])
                    .map(BGEReranker, config["reranker"])  
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"]["vllm"])
                    .sink(TerminalSink, config["sink"])
                    )

    # 提交管道并运行
    env.submit()

    # 等待一段时间确保任务完成
    time.sleep(20)
    
    # 关闭环境
    env.close()


if __name__ == '__main__':
    import os
    from sage.common.utils.logging.custom_logger import CustomLogger
    # CustomLogger.disable_global_console_debug()
    # 加载配置文件
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config_rerank.yaml")
    config = load_config(config_path)
    
    # 运行管道
    pipeline_run()

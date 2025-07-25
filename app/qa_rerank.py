import time

# 导入 Sage 相关模块
from sage.core.api.local_environment import LocalEnvironment
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.libs.rag.retriever import DenseRetriever
from sage.libs.rag.reranker import BGEReranker
from sage.libs.io.source import FileSource
from sage.libs.io.sink import TerminalSink
from sage.utils.config_loader import load_config


def pipeline_run():
    """创建并运行数据处理管道

    该函数会初始化环境，加载配置，设置数据处理流程，并启动管道。
    """
    # 初始化环境
    env = LocalEnvironment()
    env.set_memory(config=None)  # 初始化内存配置

    # 构建数据处理流程
    query_stream = (env.from_source(FileSource, config["source"])
                    .map(DenseRetriever, config["retriever"])
                    .map(BGEReranker, config["reranker"])  
                    .map(QAPromptor, config["promptor"])
                    .map(OpenAIGenerator, config["generator"]["local"])
                    .sink(TerminalSink, config["sink"])
                    )

    # 提交管道并运行
    env.submit()

    # 等待一段时间确保任务完成
    time.sleep(5)
    
    # 关闭环境
    env.close()


if __name__ == '__main__':
    # 加载配置文件
    config = load_config('config_rerank.yaml')
    
    # 运行管道
    pipeline_run()

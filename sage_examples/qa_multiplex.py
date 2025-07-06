from dotenv import load_dotenv
import os, time
from sage_core.api.env import LocalEnvironment, RemoteEnvironment
from sage_common_funs.io.source import FileSource
from sage_common_funs.io.sink import TerminalSink, FileSink
from sage_common_funs.rag.generator import OpenAIGenerator
from sage_common_funs.rag.promptor import QAPromptor
from sage_common_funs.rag.retriever import DenseRetriever
from sage_common_funs.dataflow.splitter import Splitter
from sage_common_funs.dataflow.merger import Merger
from sage_utils.config_loader import load_config
from sage_utils.logging_utils import configure_logging

def pipeline_run():
    """创建并运行数据处理管道"""
    env = LocalEnvironment()
    env.set_memory(config = None)
    # 构建数据处理流程
    response_stream = (env
        .from_source(FileSource, config["source"])
        .map(DenseRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"])
    )
    true_stream = response_stream.map(Splitter)
    false_stream = true_stream.side_output("false")  # 获取第二个输出流
    true_stream.sink(FileSink, config["sink_true"])
    false_stream.sink(FileSink, config["sink_false"])

    connected_streams = true_stream.connect(false_stream)  # 连接两个流
    
    merged_stream = connected_streams.map(Merger)
    merged_stream.sink(TerminalSink, config["sink_terminal"])  # 输出到终端
    env.submit()
    env.run_streaming()  # 启动管道

    time.sleep(100)  # 等待管道运行


if __name__ == '__main__':


    # 加载配置
    config = load_config("config_multiplex.yaml")
    load_dotenv(override=False)

    api_key = os.environ.get("ALIBABA_API_KEY")
    if api_key:
        config.setdefault("generator", {})["api_key"] = api_key

    pipeline_run()
import logging
import time


from sage.api.env import Environment
from sage_lib import QAPromptor
from sage_lib.function.generator import OpenAIGenerator
from sage_lib.function.retriever import DenseRetriever
from sage_lib.function.manual_source import ManualSource
from sage_lib.function.sink import TerminalSink
from sage.core.neuromem.memory_manager import MemoryManager
from sage.utils.config_loader import load_config
from sage.utils.logging_utils import configure_logging
from sage.api.model.model_api import apply_embedding_model
from sage.utils.custom_logger import CustomLogger
def memory_init():
    """初始化内存管理器并创建测试集合"""
    manager = MemoryManager()
    embedding_model = apply_embedding_model("hf", model="sentence-transformers/all-MiniLM-L6-v2")
    col = manager.create_collection(
        name="vdb_test",
        backend_type="VDB",
        embedding_model=embedding_model,
        dim=embedding_model.get_dim(),
        description="test vdb collection",
        as_ray_actor=True
    )
    col.add_metadata_field("owner")
    col.add_metadata_field("show_type")
    texts = [
        ("hello world", {"owner": "ruicheng", "show_type": "text"}),
        ("你好，世界", {"owner": "Jun", "show_type": "text"}),
        ("こんにちは、世界", {"owner": "Lei", "show_type": "img"}),
    ]
    for text, metadata in texts:
        col.insert(text, metadata)
    col.create_index(index_name="vdb_index")
    config["retriever"]["ltm_collection"] = col._collection





def pipeline_run():
    """创建并运行数据处理管道"""

    pipeline = Environment(name="example_pipeline")
    # 构建数据处理流程
    manual_source = ManualSource(config["source"])
    query_stream = pipeline.from_source(manual_source)
    query_and_chunks_stream = query_stream.map(DenseRetriever, config["retriever"])
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    pipeline.execute()
    time.sleep(10) # 等待管道启动
    while(True):
        user_input = input("\n>>> ").strip()
        if user_input.lower() == "exit":
            logging.info("Exiting SAGE Interactive Console")
            print("Goodbye!")
            break
        manual_source.push(user_input)
    # manual_source.push("What is the capital of France?")
    # manual_source.push("What is the capital of China?")
    # manual_source.push("What is the capital of Japan?")



if __name__ == '__main__':
    CustomLogger.disable_global_console_debug()  # 禁用全局控制台调试输出
    configure_logging(level=logging.INFO)
    # 加载配置并初始化日志
    config = load_config('./config_instance.yaml')
    # 初始化内存并运行管道
    memory_init()
    pipeline_run()

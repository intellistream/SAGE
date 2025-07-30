import logging
import time
from dotenv import load_dotenv
import os
from sage.core.function.map_function import MapFunction
from sage.core.api.remote_environment import RemoteEnvironment
from sage.service.memory.memory_service import MemoryService
from sage.utils.embedding_methods.embedding_api import apply_embedding_model
from sage.lib.io.source import FileSource
from sage.lib.io.sink import FileSink
from sage.lib.io.sink import TerminalSink
from sage.lib.rag.generator import OpenAIGenerator
from sage.lib.rag.promptor import QAPromptor
from sage.lib.rag.retriever import DenseRetriever
from sage.utils.config_loader import load_config
from sage.utils.logging_utils import configure_logging

class BiologyRetriever(MapFunction):
    """生物学知识检索器"""
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.collection_name = config.get("collection_name", "biology_rag_knowledge")
        self.index_name = config.get("index_name", "biology_index")
        self.topk = config.get("ltm", {}).get("topk", 3)

    def execute(self, data):
        if not data:
            return None

        query = data

        # 从生物学知识库检索相关知识
        try:
            result = self.call_service["memory_service"].retrieve_data(
                collection_name=self.collection_name,
                query_text=query,
                topk=self.topk,
                index_name=self.index_name,
                with_metadata=True
            )

            if result['status'] == 'success':
                # 返回包含查询和检索结果的元组
                retrieved_texts = [item.get('text', '') for item in result['results']]
                return (query, retrieved_texts)
            else:
                return (query, [])

        except Exception as e:
            return (query, [])

 # 注册memory service并连接到生物学知识库
def memory_service_factory():
    # 创建memory service实例
    embedding_model = apply_embedding_model("default")
    memory_service = MemoryService()

    # 检查生物学知识库是否存在
    try:
        collections = memory_service.list_collections()
        if collections["status"] != "success":
            return None

        collection_names = [c["name"] for c in collections["collections"]]
        if "biology_rag_knowledge" not in collection_names:
            return None

        # 连接到现有的知识库
        collection = memory_service.manager.connect_collection("biology_rag_knowledge", embedding_model)
        if not collection:
            return None

    except Exception as e:
        return None

    return memory_service





        
def pipeline_run():
    """创建并运行数据处理管道"""
    env = RemoteEnvironment(name="qa_dense_retrieval_ray")
    # 注册服务到环境中
    env.register_service("memory_service", memory_service_factory)
    # 构建数据处理流程
    query_stream = env.from_source(FileSource, config["source"])
    query_and_chunks_stream = query_stream.map(BiologyRetriever, config["retriever"])  # 使用BiologyRetriever
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"]["remote"])
    response_stream.sink(TerminalSink, config["sink"])
    # 提交管道并运行
    env.submit()
      # 启动管道
    time.sleep(100)





if __name__ == '__main__':
    configure_logging(level=logging.INFO)
    # 加载配置并初始化日志
    config = load_config('config_ray.yaml')
    # load_dotenv(override=False)

    # api_key = os.environ.get("ALIBABA_API_KEY")
    # if api_key:
    #     config.setdefault("generator", {})["api_key"] = api_key
    pipeline_run()

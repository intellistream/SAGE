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

class SafeBiologyRetriever(MapFunction):
    """带超时保护的生物学知识检索器"""
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.collection_name = config.get("collection_name", "biology_rag_knowledge")
        self.index_name = config.get("index_name", "biology_index")
        self.topk = config.get("ltm", {}).get("topk", 3)
        self.memory_service = None
        self._init_memory_service()

    def _init_memory_service(self):
        """安全地初始化memory service"""
        def init_service():
            try:
                from sage.service.memory.memory_service import MemoryService
                from sage.utils.embedding_methods.embedding_api import apply_embedding_model
                
                embedding_model = apply_embedding_model("default")
                memory_service = MemoryService()
                
                # 检查集合是否存在
                collections = memory_service.list_collections()
                if collections["status"] == "success":
                    collection_names = [c["name"] for c in collections["collections"]]
                    if self.collection_name in collection_names:
                        return memory_service
                return None
            except Exception as e:
                print(f"初始化memory service失败: {e}")
                return None

        try:
            with ThreadPoolExecutor() as executor:
                future = executor.submit(init_service)
                self.memory_service = future.result(timeout=5)  # 5秒超时
                if self.memory_service:
                    print("Memory service初始化成功")
                else:
                    print("Memory service初始化失败")
        except TimeoutError:
            print("Memory service初始化超时")
            self.memory_service = None
        except Exception as e:
            print(f"Memory service初始化异常: {e}")
            self.memory_service = None

    def execute(self, data):
        if not data:
            return None

        query = data

        if self.memory_service:
            # 尝试真实检索
            try:
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(self._retrieve_real, query)
                    result = future.result(timeout=3)  # 3秒超时
                    return result
            except TimeoutError:
                self.logger.error(f"检索超时: {query}")
                return (query, [])
            except Exception as e:
                self.logger.error(f"检索异常: {e}")
                return (query, [])
        else:
            # Memory service 不可用，返回空结果
            print(f"Memory service 不可用，返回空结果: {query}")
            return (query, [])

    def _retrieve_real(self, query):
        """真实检索"""
        result = self.memory_service.retrieve_data(
            collection_name=self.collection_name,
            query_text=query,
            topk=self.topk,
            index_name=self.index_name,
            with_metadata=True
        )

        if result['status'] == 'success':
            retrieved_texts = [item.get('text', '') for item in result['results']]
            return (query, retrieved_texts)
        else:
            return (query, [])






        
def pipeline_run(config):
    """创建并运行数据处理管道"""
    env = RemoteEnvironment(name="qa_dense_retrieval_ray", host="base-sage", port=19001)  # 连接到base-sage上的JobManager
    
    # 直接注册 MemoryService 类
    from sage.service.memory.memory_service import MemoryService
    env.register_service("memory_service", SafeBiologyRetriever)
    # 构建数据处理流程
    query_stream = env.from_source(FileSource, config["source"])
    query_and_chunks_stream = query_stream.map(SafeBiologyRetriever, config["retriever"])  # 使用BiologyRetriever
    prompt_stream = query_and_chunks_stream.map(QAPromptor, config["promptor"])
    response_stream = prompt_stream.map(OpenAIGenerator, config["generator"]["remote"])
    response_stream.sink(FileSink, config["sink"])
    # 提交管道并运行
    env.submit()
      # 启动管道
    time.sleep(100)





if __name__ == '__main__':
    # 加载配置并初始化日志
    config = load_config('../config/config_ray.yaml')
    # load_dotenv(override=False)

    # api_key = os.environ.get("ALIBABA_API_KEY")
    # if api_key:
    #     config.setdefault("generator", {})["api_key"] = api_key
    pipeline_run(config)

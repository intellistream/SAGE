import time
from dotenv import load_dotenv
from sage.utils.custom_logger import CustomLogger
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.batch_function import BatchFunction
from sage.core.function.map_function import MapFunction
from sage.lib.io.sink import TerminalSink
from sage.lib.rag.generator import OpenAIGenerator
from sage.lib.rag.promptor import QAPromptor
from sage.utils.config_loader import load_config
from sage.service.memory.memory_service import MemoryService
from sage.utils.embedding_methods.embedding_api import apply_embedding_model


class QABatch(BatchFunction):
    """
    QA批处理数据源：从配置文件中读取数据文件并逐行返回
    """
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.data_path = config["data_path"]
        self.counter = 0
        self.questions = []
        self._load_questions()

    def _load_questions(self):
        """从文件加载问题"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as file:
                self.questions = [line.strip() for line in file.readlines() if line.strip()]
        except Exception as e:
            print(f"Error loading file {self.data_path}: {e}")
            self.questions = []

    def execute(self):
        """返回下一个问题，如果没有更多问题则返回None"""
        if self.counter >= len(self.questions):
            return None  # 返回None表示批处理完成

        question = self.questions[self.counter]
        self.counter += 1
        return question


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


def pipeline_run(config: dict) -> None:
    """
    创建并运行数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """
    env = LocalEnvironment()

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

    # 注册服务到环境中
    env.register_service("memory_service", memory_service_factory)

    # 构建数据处理流程 - 使用自定义的生物学检索器
    (env
        .from_batch(QABatch, config["source"])
        .map(BiologyRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )

    env.submit()
    time.sleep(10)  # 增加等待时间确保处理完成
    env.close()


if __name__ == '__main__':
    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)
    config = load_config("config_batch.yaml")
    pipeline_run(config)
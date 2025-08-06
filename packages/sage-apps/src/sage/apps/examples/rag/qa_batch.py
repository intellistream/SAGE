import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dotenv import load_dotenv
from sage.kernel.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment
from sage.kernel.api.function.batch_function import BatchFunction
from sage.kernel.api.function.map_function import MapFunction
from sage.apps.lib.io_utils.sink import TerminalSink
from sage.apps.lib.rag.generator import OpenAIGenerator
from sage.apps.lib.rag.promptor import QAPromptor
from sage.kernel.utils.config.loader import load_config


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
                from sage.middleware.services.memory.memory_service import MemoryService
                from sage.kernel.utils.embedding_methods.embedding_api import apply_embedding_model
                
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
                print(f"检索超时: {query}")
                return (query, [])
            except Exception as e:
                print(f"检索异常: {e}")
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


def pipeline_run(config: dict) -> None:
    """
    创建并运行数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """
    env = LocalEnvironment()

    # 构建数据处理流程 - 使用安全的生物学检索器
    (env
        .from_batch(QABatch, config["source"])
        .map(SafeBiologyRetriever, config["retriever"])
        .map(QAPromptor, config["promptor"])
        .map(OpenAIGenerator, config["generator"]["vllm"])
        .sink(TerminalSink, config["sink"])
    )

    try:
        print("开始QA处理...")
        env.submit()
        time.sleep(10)  # 增加等待时间确保处理完成
    except KeyboardInterrupt:
        print("测试中断")
    finally:
        print("测试结束")
        env.close()


if __name__ == '__main__':
    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)
    config = load_config("../../resources/config/config_batch.yaml")
    pipeline_run(config)
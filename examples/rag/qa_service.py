import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dotenv import load_dotenv
from sage.core.api.remote_environment import RemoteEnvironment
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.map_function import MapFunction
from sage.libs.io_utils.sink import TerminalSink
from sage.libs.rag.generator import OpenAIGenerator
from sage.libs.rag.promptor import QAPromptor
from sage.common.utils.config.loader import load_config
from sage.middleware.services.memory.memory_service import MemoryService

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

    def execute(self, data):
        if not data:
            return None

        query = data
        return self.call_service["memory_service"].retrieve_data(query)


def pipeline_run(config: dict) -> None:
    """
    创建并运行数据处理管道

    Args:
        config (dict): 包含各模块配置的配置字典。
    """
    env = RemoteEnvironment()
    env.register_service("memory_service", MemoryService)

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
    import os
    CustomLogger.disable_global_console_debug()
    load_dotenv(override=False)
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "config_batch.yaml")
    config = load_config(config_path)
    
    pipeline_run(config)
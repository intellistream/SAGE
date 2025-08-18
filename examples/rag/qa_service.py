
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Dict, List
from sage.core.api.service.base_service import BaseService
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
class MockMemoryService(BaseService):
    """
    模拟记忆服务
    
    用于在memory service未完成时提供基本的retrieve_data功能
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.mock_biology_knowledge = [
            {
                "id": "bio_001",
                "content": "DNA（脱氧核糖核酸）是生物遗传信息的载体，由四种碱基A、T、G、C组成双螺旋结构。",
                "score": 0.95,
                "metadata": {"type": "molecular_biology", "topic": "DNA"}
            },
            {
                "id": "bio_002", 
                "content": "细胞膜是由磷脂双分子层构成的生物膜，控制物质进出细胞，维持细胞内外环境的稳定。",
                "score": 0.90,
                "metadata": {"type": "cell_biology", "topic": "cell_membrane"}
            },
            {
                "id": "bio_003",
                "content": "光合作用是植物利用光能将二氧化碳和水转化为葡萄糖和氧气的生化过程。",
                "score": 0.88,
                "metadata": {"type": "plant_biology", "topic": "photosynthesis"}
            },
            {
                "id": "bio_004",
                "content": "蛋白质是由氨基酸组成的生物大分子，具有催化、结构、运输、免疫等多种功能。",
                "score": 0.92,
                "metadata": {"type": "biochemistry", "topic": "protein"}
            },
            {
                "id": "bio_005",
                "content": "基因表达是将基因的遗传信息转录为mRNA，再翻译为蛋白质的过程。",
                "score": 0.87,
                "metadata": {"type": "molecular_biology", "topic": "gene_expression"}
            },
            {
                "id": "bio_006",
                "content": "酶是具有催化功能的蛋白质，能够降低化学反应的活化能，加速生化反应。",
                "score": 0.91,
                "metadata": {"type": "biochemistry", "topic": "enzyme"}
            },
            {
                "id": "bio_007",
                "content": "细胞分裂包括DNA复制、纺锤体形成、染色体分离等步骤，确保遗传信息准确传递。",
                "score": 0.89,
                "metadata": {"type": "cell_biology", "topic": "cell_division"}
            },
            {
                "id": "bio_008",
                "content": "ATP（腺苷三磷酸）是细胞内主要的能量载体，为各种生物学过程提供化学能。",
                "score": 0.93,
                "metadata": {"type": "biochemistry", "topic": "ATP"}
            }
        ]
        
    def _start_service_instance(self):
        """启动Mock Memory服务实例"""
        print(f"Mock Memory Service '{getattr(self, 'service_name', 'mock_memory_service')}' started")
    
    def _stop_service_instance(self):
        """停止Mock Memory服务实例"""
        print(f"Mock Memory Service '{getattr(self, 'service_name', 'mock_memory_service')}' stopped")
    
    def retrieve_data(self, query: str, topk: int = 3) -> List[Dict[str, Any]]:
        """
        模拟检索相关的生物学知识数据
        
        Args:
            query (str): 查询字符串
            topk (int): 返回的结果数量，默认为3
            
        Returns:
            List[Dict[str, Any]]: 模拟的检索结果列表
        """
        # 简单的关键词匹配逻辑
        query_lower = query.lower()
        relevant_docs = []
        
        # 根据查询内容匹配相关文档
        for doc in self.mock_biology_knowledge:
            content_lower = doc["content"].lower()
            
            # 简单的关键词匹配
            if (any(keyword in content_lower for keyword in ["dna", "基因", "遗传"]) and 
                any(keyword in query_lower for keyword in ["dna", "基因", "遗传", "分子"])):
                relevant_docs.append(doc)
            elif (any(keyword in content_lower for keyword in ["细胞", "膜"]) and 
                  any(keyword in query_lower for keyword in ["细胞", "膜", "生物膜"])):
                relevant_docs.append(doc)
            elif (any(keyword in content_lower for keyword in ["光合", "植物"]) and 
                  any(keyword in query_lower for keyword in ["光合", "植物", "叶绿素"])):
                relevant_docs.append(doc)
            elif (any(keyword in content_lower for keyword in ["蛋白", "氨基酸"]) and 
                  any(keyword in query_lower for keyword in ["蛋白", "氨基酸", "酶"])):
                relevant_docs.append(doc)
            elif (any(keyword in content_lower for keyword in ["atp", "能量"]) and 
                  any(keyword in query_lower for keyword in ["atp", "能量", "代谢"])):
                relevant_docs.append(doc)
        
        # 如果没有匹配的，随机返回一些结果
        if not relevant_docs:
            import random
            relevant_docs = random.sample(self.mock_biology_knowledge, min(topk, len(self.mock_biology_knowledge)))
        
        # 按分数排序并返回topk个结果
        relevant_docs.sort(key=lambda x: x["score"], reverse=True)
        return relevant_docs[:topk]
    
    def search_memories(self, query_vector=None, **kwargs) -> List[Dict[str, Any]]:
        """
        兼容原有search_memories接口的方法
        """
        # 如果有查询向量，模拟向量检索
        return random.sample(self.mock_biology_knowledge, min(3, len(self.mock_biology_knowledge)))


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
    env.register_service("memory_service", MockMemoryService)

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
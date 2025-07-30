#!/usr/bin/env python3
"""
修复版的QA批处理 - 添加超时和错误处理
"""
import time
import signal
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.batch_function import BatchFunction
from sage.core.function.map_function import MapFunction
from sage.core.function.sink_function import SinkFunction
from sage.utils.custom_logger import CustomLogger
from sage.utils.config_loader import load_config

class TimeoutQABatch(BatchFunction):
    """
    带超时的QA批处理数据源
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
            print(f"加载了 {len(self.questions)} 个问题")
        except Exception as e:
            print(f"Error loading file {self.data_path}: {e}")
            self.questions = []

    def execute(self):
        """返回下一个问题，如果没有更多问题则返回None"""
        if self.counter >= len(self.questions):
            print(f"TimeoutQABatch: 完成，已处理 {self.counter} 个问题")
            return None

        question = self.questions[self.counter]
        self.counter += 1
        print(f"TimeoutQABatch: 生成问题 #{self.counter}: {question}")
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
                    print("Memory service初始化失败，将使用模拟数据")
        except TimeoutError:
            print("Memory service初始化超时，将使用模拟数据")
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
                print(f"检索超时，使用模拟数据: {query}")
                return self._retrieve_mock(query)
            except Exception as e:
                print(f"检索异常，使用模拟数据: {e}")
                return self._retrieve_mock(query)
        else:
            # 使用模拟数据
            return self._retrieve_mock(query)

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

    def _retrieve_mock(self, query):
        """模拟检索"""
        mock_texts = [
            "减数分裂产生的四个子细胞在基因上是不同的，这是因为交叉互换和独立分配的结果。",
            "减数分裂通过两次连续的细胞分裂，将二倍体细胞转变为四个单倍体配子。",
            "减数分裂的关键特征是同源染色体配对和分离，这与有丝分裂不同。"
        ]
        return (query, mock_texts)

class SimpleTerminalSink(SinkFunction):
    """简单终端输出"""
    def execute(self, data):
        print(f"\n=== QA结果 ===")
        print(data)
        print("===============\n")
        return data

def main():
    print("=== 修复版QA批处理测试 ===")
    
    env = LocalEnvironment("fixed_qa_test")
    
    try:
        config = load_config("config_batch.yaml")
    except:
        # 如果配置文件有问题，使用默认配置
        config = {
            "source": {"data_path": "data/sample/one_question.txt"},
            "retriever": {
                "collection_name": "biology_rag_knowledge",
                "index_name": "biology_index",
                "ltm": {"topk": 3}
            },
            "sink": {"platform": "local"}
        }
    
    # 构建处理管道
    (env
        .from_batch(TimeoutQABatch, config["source"])
        .map(SafeBiologyRetriever, config["retriever"])
        .sink(SimpleTerminalSink, config["sink"])
    )
    
    try:
        print("开始QA处理...")
        env.submit()
        time.sleep(10)  # 等待处理完成
    except KeyboardInterrupt:
        print("测试中断")
    finally:
        print("测试结束")
        env.close()

if __name__ == '__main__':
    CustomLogger.disable_global_console_debug()
    main()

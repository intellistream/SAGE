import json
import os

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

# 使用 .sage 目录存储测试数据
manager_path = ".sage/examples/memory/rag_memory_manager"

config = {
    "name": "RAGMemoryCollection",
    "backend_type": "VDB",
    "description": "rag memory collection",
    "index_config": {
        "name": "test_index",
        "embedding_model": "mockembedder",
        "dim": 128,
        "backend_type": "FAISS",
        "description": "rag memory index",
        "index_parameter": {},
    },
}


class RAGMemoryManager:
    def __init__(self, config):
        self.init_status = False
        self.logger = CustomLogger()
        self.memory_manager = MemoryManager(manager_path)

        if self.memory_manager.has_collection(config.get("name")):
            self.rag_collection = self.memory_manager.get_collection(config.get("name"))
            self.logger.info("Successfully load rag memory from disk")
            self.init_status = True
        else:
            self.rag_collection = self.memory_manager.create_collection(config)
            self.rag_collection.create_index(config.get("index_config"))
            self.logger.info("Successfully create rag memory")

    def init(self, texts, metadatas):
        self.rag_collection.batch_insert_data(texts, metadatas)
        self.rag_collection.init_index("test_index")

    def store(self):
        self.memory_manager.store_collection()

    def list(self):
        pass

    def insert(self, data):
        pass

    def retrieve(self, data):

        results = self.rag_collection.retrieve(
            raw_data=data,
            index_name="test_index",
            topk=5,
            threshold=0.1,
            with_metadata=True,
        )

        return results


def init_history_memory():
    memory = RAGMemoryManager(config)

    if not memory.init_status:
        base_dir = os.path.dirname(__file__)
        file_path = os.path.join(base_dir, "data/toy_memory.json")

        # Check if data file exists
        if not os.path.exists(file_path):
            print(f"⚠️  Data file not found: {file_path}")
            print("Creating sample data for demonstration...")
            # Create sample data inline
            data = [
                {
                    "text": "我一写代码就喜欢抓点零食，不吃东西嘴巴就觉得空空的，有什么健康的替代吗？",
                    "metadata": {
                        "answer": "你可以准备一些低热量的小零食，比如坚果、黄瓜条，既能满足嘴馋又不容易发胖。",
                        "topic": "健康-个性化",
                    },
                },
                {
                    "text": "我不太喜欢喝白开水，基本都靠饮料补水，这样是不是会让身体负担太重？",
                    "metadata": {
                        "answer": "饮料里常常含糖量很高，长期会增加肥胖和糖尿病风险。可以试试在水里加柠檬片或薄荷叶，口感会好些。",
                        "topic": "健康-个性化",
                    },
                },
            ]
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        texts = [item["text"] for item in data]
        metadatas = [item.get("metadata", {}) for item in data]
        memory.init(texts, metadatas)

        memory.store()
        print("RAG memory has been initialized")
    else:
        print("RAG memory has already been initialized")


def test_retrieve():
    memory = RAGMemoryManager(config)
    print(memory.retrieve("我刚刚喝了很多奶茶，会不会有问题？"))


if __name__ == "__main__":
    init_history_memory()
    test_retrieve()

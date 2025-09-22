import logging
import json
import logging
import os

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.middleware.components.neuromem.memory_manager import MemoryManager

manager_path = "examples/memory/data/neuromem"

config = {
    "name": "RAGMemoryCollection",
    "backend_type": "VDB",
    "description": "rag memory collection",
    "index_config": {
        "name": "test_index",
        "embedding_model": "default",
        "dim": 384,
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
            self.logger.info(f"Successfully load rag memory from disk")
            self.init_status = True
        else:
            self.rag_collection = self.memory_manager.create_collection(config)
            self.rag_collection.create_index(config.get("index_config"))
            self.logger.info(f"Successfully create rag memory")

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
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        texts = [item["text"] for item in data]
        metadatas = [item.get("metadata", {}) for item in data]
        memory.init(texts, metadatas)

        memory.store()
        logging.info("RAG memory has been initialized")
    else:
        logging.info("RAG memory has already been initialized")


def test_retrieve():
    memory = RAGMemoryManager(config)
    logging.info(memory.retrieve("我刚刚喝了很多奶茶，会不会有问题？"))


if __name__ == "__main__":
    init_history_memory()
    test_retrieve()

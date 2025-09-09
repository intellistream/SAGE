import os
import json
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
                "index_parameter": {}
    }
}

class RAGMemoryManager():
    def __init__(self, config):
        self.logger = CustomLogger()
        self.memory_manager = MemoryManager(manager_path)

        if self.memory_manager.has_collection(config.get("name")):
            self.rag_collection = self.memory_manager.get_collection(config.get("name"))
            self.logger.info(f"Successfully load rag memory from disk")
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
            with_metadata=True
        )
    
        return results

def init_history_memory():
    memory = RAGMemoryManager(config)

    base_dir = os.path.dirname(__file__)   
    file_path = os.path.join(base_dir, "data/toy_memory.json")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts = [item["text"] for item in data]
    metadatas = [item.get("metadata", {}) for item in data]
    memory.init(texts, metadatas)   
    
    memory.store()
    
    
def test_retrieve():
    memory = RAGMemoryManager(config)
    print(memory.retrieve("我每天都喝牛奶，有没有副作用？"))


if __name__ == "__main__":
    init_history_memory()
    test_retrieve()

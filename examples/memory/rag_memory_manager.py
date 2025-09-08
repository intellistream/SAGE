from sage.core.api.service.base_service import BaseService
from sage.middleware.components.neuromem.memory_manager import MemoryManager

class RAGMemoryManager():
    def __init__(self, config):
        self.memory_manager = MemoryManager("examples/memory/data")
        if self.memory_manager.has_collection("RAGMemoryCollection"):
            self.rag_collection = self.memory_manager.get_collection("RAGMemoryCollection")
        else:
            config.update({"name": "RAGMemoryCollection"})
            self.rag_collection = self.memory_manager.create_collection(config)
            print("RAGMemoryCollection created")

    def list(self):
        pass
    
    def insert(self, data):
        pass

    def retrieve(self, data):
        pass

config = {"backend_type": "vdb", "dim": 384, "embedding_model": "default"}

a = RAGMemoryManager(config)

# print()

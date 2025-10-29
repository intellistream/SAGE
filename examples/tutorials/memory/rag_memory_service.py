from typing import Any

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.service.base_service import BaseService
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager

config = {
    "manager_path": ".sage/examples/memory/rag_memory_service",
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


class RAGMemoryService(BaseService):
    def __init__(self, config=None, **kwargs):
        super().__init__()

        self._logger = CustomLogger()

        # 如果 config 为 None，尝试从 kwargs 构建
        if config is None:
            config = kwargs

        # 如果还是空，说明有问题
        if not config:
            raise ValueError("RAGMemoryService requires configuration")

        self.memory_manager = MemoryManager(config.get("manager_path"))

        # Try to load existing collection; if missing, create one locally with mock/offline embeddings
        if self.memory_manager.has_collection(config.get("name")):
            self.rag_collection = self.memory_manager.get_collection(config.get("name"))
            self._logger.info("Successfully loaded RAG memory from disk")
        else:
            self._logger.warning(
                "RAG Memory collection not found on disk, creating a fresh one for this session"
            )
            # Ensure a local, network-free embedding is used by honoring model name via embedding layer fallback
            self.rag_collection = self.memory_manager.create_collection(config)
            self.rag_collection.create_index(config.get("index_config"))
            # Optional: do not init_index here; will be built upon insert or explicit init in callers

    def retrieve(self, data: str):
        results = self.rag_collection.retrieve(
            raw_data=data,
            index_name="test_index",
            topk=5,
            threshold=0.1,
            with_metadata=True,
        )

        # 重新格式化结果
        formatted_results = []
        for result in results:
            formatted_result = {
                "history_query": result["text"],
                "answer": result["metadata"].get("answer", ""),
            }
            formatted_results.append(formatted_result)

        return formatted_results

    def insert(self, data: str, metadata: dict[str, Any] | None = None):
        result = self.rag_collection.insert(
            raw_data=data, index_name="test_index", metadata=metadata
        )
        if result:
            self._logger.info("Successfully insert data into rag memory")
        else:
            self._logger.info("Failed to insert data into rag memory")


if __name__ == "__main__":

    def test():
        memory = RAGMemoryService(config)
        memory.insert(
            "我刚刚心脏悸动，很难受，不会有什么问题吧？",
            {"answer": "可能是心理因素导致的", "topic": "健康-个性化"},
        )
        print(memory.retrieve("我刚刚心脏悸动，很难受，不会有什么问题吧？"))
        # print(memory.retrieve("我每天都喝牛奶，有没有副作用？"))

    test()

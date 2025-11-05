from typing import Any

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.service.base_service import BaseService
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.middleware.components.sage_mem.neuromem.memory_collection.vdb_collection import (
    VDBMemoryCollection,
)

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
        self.rag_collection: VDBMemoryCollection | None = None

        # 如果 config 为 None，尝试从 kwargs 构建
        if config is None:
            config = kwargs

        # 如果还是空，说明有问题
        if not config:
            raise ValueError("RAGMemoryService requires configuration")

        self.memory_manager = MemoryManager(config.get("manager_path"))

        # Try to load existing collection; if missing, create one locally with mock/offline embeddings
        collection_name = config.get("name")
        if not collection_name:
            raise ValueError("Collection name is required in config")

        if self.memory_manager.has_collection(collection_name):
            collection = self.memory_manager.get_collection(collection_name)
            # 类型安全的转换：验证是 VDB 类型
            if isinstance(collection, VDBMemoryCollection):
                self.rag_collection = collection
                self._logger.info("Successfully loaded RAG memory from disk")
            else:
                raise TypeError(
                    f"Expected VDBMemoryCollection, got {type(collection).__name__}"
                )
        else:
            self._logger.warning(
                "RAG Memory collection not found on disk, creating a fresh one for this session"
            )
            # Ensure a local, network-free embedding is used by honoring model name via embedding layer fallback
            collection = self.memory_manager.create_collection(config)
            # 类型安全的转换：验证是 VDB 类型
            if isinstance(collection, VDBMemoryCollection):
                self.rag_collection = collection
            else:
                raise TypeError(
                    f"Expected VDBMemoryCollection, got {type(collection).__name__}"
                )
            index_config = config.get("index_config")
            if index_config and self.rag_collection:
                self.rag_collection.create_index(index_config)
            # Optional: do not init_index here; will be built upon insert or explicit init in callers

    def retrieve(self, data: str):
        if not self.rag_collection:
            return []

        # VDBMemoryCollection.retrieve 方法签名
        results = self.rag_collection.retrieve(
            raw_data=data,
            index_name="test_index",
            topk=5,
            threshold=0.1,
            with_metadata=True,
        )

        if not results:
            return []

        # 重新格式化结果
        formatted_results = []
        for result in results:
            if isinstance(result, dict):
                formatted_result = {
                    "history_query": result.get("text", ""),
                    "answer": result.get("metadata", {}).get("answer", "")
                    if isinstance(result.get("metadata"), dict)
                    else "",
                }
                formatted_results.append(formatted_result)

        return formatted_results

    def insert(self, data: str, metadata: dict[str, Any] | None = None):
        if not self.rag_collection:
            self._logger.error("RAG collection not initialized")
            return

        # VDBMemoryCollection.insert 方法签名
        result = self.rag_collection.insert(
            index_name="test_index",
            raw_data=data,
            metadata=metadata,
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

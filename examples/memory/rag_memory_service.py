import logging
from typing import Any, Dict, Optional

from sage.common.utils.logging.custom_logger import CustomLogger
from sage.core.api.service.base_service import BaseService
from sage.middleware.components.neuromem.memory_manager import MemoryManager

config = {
    "manager_path": "examples/memory/data/neuromem",
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


class RAGMemoryService(BaseService):
    def __init__(self, config):
        super().__init__()

        self._logger = CustomLogger()

        self.memory_manager = MemoryManager(config.get("manager_path"))

        try:
            self.memory_manager.has_collection(config.get("name"))
            self.rag_collection = self.memory_manager.get_collection(config.get("name"))
            self._logger.info(f"Successfully load rag memory from disk")
        except:
            raise ValueError(
                "RAG Memory collection not found, please initialize first."
            )

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

    def insert(self, data: str, metadata: Optional[Dict[str, Any]] = None):
        result = self.rag_collection.insert(
            raw_data=data, index_name="test_index", metadata=metadata
        )
        if result:
            self._logger.info(f"Successfully insert data into rag memory")
        else:
            self._logger.info(f"Failed to insert data into rag memory")


if __name__ == "__main__":

    def test():
        memory = RAGMemoryService(config)
        memory.insert(
            "我刚刚心脏悸动，很难受，不会有什么问题吧？",
            {"answer": "可能是心理因素导致的", "topic": "健康-个性化"},
        )
        logging.info(memory.retrieve("我刚刚心脏悸动，很难受，不会有什么问题吧？"))
        # logging.info(memory.retrieve("我每天都喝牛奶，有没有副作用？"))

    test()

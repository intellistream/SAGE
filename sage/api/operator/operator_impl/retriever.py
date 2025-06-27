from typing import Tuple, List
import time  # 替换 asyncio 为 time 用于同步延迟
from sage.api.operator import Data, StateRetrieverFunction
import logging
from sage.utils.custom_logger import CustomLogger


# 更新后的 SimpleRetriever
class DenseRetriever(StateRetrieverFunction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config

        
        if self.config.get("ltm", False):
            self.ltm = self.config.get("ltm_collection")
            self.ltm_config = self.config.get("ltm", {})
        else:
            self.ltm = None


        # if self.config.get("dcm", False):
        #     self.dcm = self.config.get("dcm_collection")
        #     self.dcm_config = self.config.get("dcm_config", {})
        # else:
        #     self.dcm = None


        self.logger = CustomLogger(
            object_name=f"DenseRetriever",
            session_folder=config["session_folder"] or None,
            log_level="DEBUG",
            console_output=False,
            file_output=True
        )

        

        self.memory_adapter = self._create_memory_adapter()
        self.memory_adapter.logger = self.logger

        # 取消继承 root logger 的 stdout handler
        # self.logger.propagate = False
    def _create_memory_adapter(self):
        """创建内存适配器，处理不同类型的memory collection"""
        from sage.core.runtime.memory_adapter import MemoryAdapter
        return MemoryAdapter()

    def execute(self, data: Data[str]) -> Data[Tuple[str, List[str]]]:

        input_query = data.data
        chunks = []
        self.logger.debug(f"Starting retrieval for query: {input_query}")


        # LTM 检索
        if self.config.get("ltm", False) and self.ltm:
            self.logger.debug("Retrieving from LTM")
            try:

                # 使用LTM配置和输入查询调用检索
                ltm_results = self.memory_adapter.retrieve(
                    self.ltm,
                    query=input_query,
                    collection_config=self.ltm_config
                )
                self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Retrieval Results: {ltm_results}\033[0m ")

                chunks.extend(ltm_results)
                self.logger.debug(f"Retrieved {len(ltm_results)} from LTM")

                # 保留原有的延迟逻辑
                time.sleep(1)
                self.logger.debug("Completed LTM delay")
            except Exception as e:
                self.logger.error(f"LTM retrieval failed: {str(e)}")

        return Data((input_query, chunks))
    
class BM25sRetriever(StateRetrieverFunction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config["retriever"]
        self.bm25s_collection = self.config.get("bm25s_collection")
        self.bm25s_config = self.config.get("bm25s_config", {})

        # 创建内存适配器并设置日志
        self.memory_adapter = self._create_memory_adapter()
        self.memory_adapter.logger = self.logger

    def _create_memory_adapter(self):
        from sage.core.runtime.memory_adapter import MemoryAdapter
        return MemoryAdapter()

    def execute(self, data: Data[str]) -> Data[Tuple[str, List[str]]]:
        input_query = data.data
        chunks = []
        self.logger.debug(f"Starting BM25s retrieval for query: {input_query}")

        if not self.bm25s_collection:
            raise ValueError("BM25s collection is not configured.")

        try:
            # 使用BM25s配置和输入查询调用检索
            bm25s_results = self.memory_adapter.retrieve(
                self.bm25s_collection,
                query=input_query,
                collection_config=self.bm25s_config
            )
            chunks.extend(bm25s_results)
            self.logger.info(f"\033[32m[ {self.__class__.__name__}]:Query: {input_query} Retrieved {len(bm25s_results)} from BM25s\033[0m ")
            print(input_query)
            print(bm25s_results)
        except Exception as e:
            self.logger.error(f"BM25s retrieval failed: {str(e)}")

        return Data((input_query, chunks))
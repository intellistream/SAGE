from typing import Tuple, List
import time  # 替换 asyncio 为 time 用于同步延迟

from sage_core.function.map_function import MapFunction
from sage_core.function.base_function import MemoryFunction, StatefulFunction
from sage_runtime.runtime_context import RuntimeContext

# 更新后的 SimpleRetriever
class DenseRetriever(MapFunction):
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)

        self.config = config

        
        if self.config.get("ltm", False):
            self.ltm_config = self.config.get("ltm", {})
        else:
            self.ltm = None

    def execute(self, data: str) -> Tuple[str, List[str]]:

        input_query = data[0] if isinstance(data, tuple) and len(data) > 0 else data
        chunks = []
        self.logger.info(f"[ {self.__class__.__name__}]: Retrieving from LTM")
        self.logger.info(f"Starting retrieval for query: {input_query}")
        # LTM 检索
        if self.config.get("ltm", False):
            self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Retrieving from LTM \033[0m ")
            try:
                # 使用LTM配置和输入查询调用检索
                ltm_results = self.ctx.retrieve(
                    query=input_query,
                    collection_config=self.ltm_config
                )
                self.logger.info(f"Retrieved {len(ltm_results)} from LTM")
                self.logger.info(f"\033[32m[ {self.__class__.__name__}]: Retrieval Results: {ltm_results}\033[0m ")
                chunks.extend(ltm_results)

            except Exception as e:
                self.logger.error(f"LTM retrieval failed: {str(e)}")

        return (input_query, chunks)
    
class BM25sRetriever(MapFunction): # 目前runtime context还只支持ltm
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.bm25s_collection = self.config.get("bm25s_collection")
        self.bm25s_config = self.config.get("bm25s_config", {})


    def execute(self, data: str) -> Tuple[str, List[str]]:
        input_query = data
        chunks = []
        self.logger.debug(f"Starting BM25s retrieval for query: {input_query}")

        if not self.bm25s_collection:
            raise ValueError("BM25s collection is not configured.")

        try:
            # 使用BM25s配置和输入查询调用检索
            bm25s_results = self.ctx.retrieve(
                # self.bm25s_collection,
                query=input_query,
                collection_config=self.bm25s_config
            )
            chunks.extend(bm25s_results)
            self.logger.info(f"\033[32m[ {self.__class__.__name__}]:Query: {input_query} Retrieved {len(bm25s_results)} from BM25s\033[0m ")
            print(input_query)
            print(bm25s_results)
        except Exception as e:
            self.logger.error(f"BM25s retrieval failed: {str(e)}")

        return (input_query, chunks)
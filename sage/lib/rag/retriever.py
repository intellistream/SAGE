from typing import Tuple, List
import time  # 替换 asyncio 为 time 用于同步延迟
import os
import json

from sage.core.function.map_function import MapFunction
from sage.core.function.base_function import MemoryFunction, StatefulFunction

# 更新后的 SimpleRetriever
class DenseRetriever(MapFunction):
    def __init__(self, config, enable_profile=False, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.enable_profile = enable_profile

        if self.config.get("ltm", False):
            self.ltm_config = self.config.get("ltm", {})
        else:
            self.ltm = None

        # 只有启用profile时才设置数据存储路径
        if self.enable_profile:
            if hasattr(self.ctx, 'env_base_dir') and self.ctx.env_base_dir:
                self.data_base_path = os.path.join(self.ctx.env_base_dir, ".sage_states", "retriever_data")
            else:
                # 使用默认路径
                self.data_base_path = os.path.join(os.getcwd(), ".sage_states", "retriever_data")

            os.makedirs(self.data_base_path, exist_ok=True)
            self.data_records = []

    def _save_data_record(self, query, retrieved_docs):
        """保存检索数据记录"""
        if not self.enable_profile:
            return

        record = {
            'timestamp': time.time(),
            'query': query,
            'retrieved_docs': retrieved_docs,
            'collection_config': self.ltm_config if self.config.get("ltm", False) else {}
        }
        self.data_records.append(record)
        self._persist_data_records()

    def _persist_data_records(self):
        """将数据记录持久化到文件"""
        if not self.enable_profile or not self.data_records:
            return

        timestamp = int(time.time())
        filename = f"retriever_data_{timestamp}.json"
        path = os.path.join(self.data_base_path, filename)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.data_records, f, ensure_ascii=False, indent=2)
            self.data_records = []
        except Exception as e:
            self.logger.error(f"Failed to persist data records: {e}")

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

                # 保存数据记录（只有enable_profile=True时才保存）
                if self.enable_profile:
                    self._save_data_record(input_query, chunks)

            except Exception as e:
                self.logger.error(f"LTM retrieval failed: {str(e)}")

        return (input_query, chunks)

    def __del__(self):
        """确保在对象销毁时保存所有未保存的记录"""
        if hasattr(self, 'enable_profile') and self.enable_profile:
            try:
                self._persist_data_records()
            except:
                pass

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
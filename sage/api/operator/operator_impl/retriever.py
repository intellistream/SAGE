from typing import Tuple, List
import time  # 替换 asyncio 为 time 用于同步延迟
from sage.api.operator import Data, RetrieverFunction


# 更新后的 SimpleRetriever
class SimpleRetriever(RetrieverFunction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config["retriever"]

        # 初始化各类型集合
        if self.config.get("stm", False):
            self.stm = self.config.get("stm_collection")
            self.stm_config = self.config.get("stm_config", {})
        else:
            self.stm = None

        if self.config.get("ltm", False):
            self.ltm = self.config.get("ltm_collection")
            self.ltm_config = self.config.get("ltm_config", {})
        else:
            self.ltm = None

        if self.config.get("dcm", False):
            self.dcm = self.config.get("dcm_collection")
            self.dcm_config = self.config.get("dcm_config", {})
        else:
            self.dcm = None

        self.top_k = self.config.get("top_k", 5)

        # 创建内存适配器并设置日志
        self.memory_adapter = self._create_memory_adapter()
        self.memory_adapter.logger = self.logger

    def _create_memory_adapter(self):
        from sage.runtime.memory_adapter import MemoryAdapter
        return MemoryAdapter()

    def execute(self, data: Data[str]) -> Data[Tuple[str, List[str]]]:
        input_query = data.data
        chunks = []
        self.logger.debug(f"Starting retrieval for query: {input_query}")

        # STM 检索
        if self.config.get("stm", False) and self.stm:
            self.logger.debug("Retrieving from STM")
            try:
                # 使用STM配置调用检索
                stm_results = self.memory_adapter.retrieve(
                    self.stm,
                    collection_config=self.stm_config
                )
                chunks.extend(stm_results)
                self.logger.debug(f"Retrieved {len(stm_results)} from STM")
            except Exception as e:
                self.logger.error(f"STM retrieval failed: {str(e)}")

        # LTM 检索
        if self.config.get("ltm", False) and self.ltm:
            self.logger.debug("Retrieving from LTM")
            try:
                # 添加LTM特定配置参数
                if "index_name" not in self.ltm_config:
                    self.ltm_config["index_name"] = "default"
                if "topk" not in self.ltm_config:
                    self.ltm_config["topk"] = self.top_k

                # 使用LTM配置和输入查询调用检索
                ltm_results = self.memory_adapter.retrieve(
                    self.ltm,
                    query=input_query,
                    collection_config=self.ltm_config
                )
                chunks.extend(ltm_results)
                self.logger.debug(f"Retrieved {len(ltm_results)} from LTM")

                # 保留原有的延迟逻辑
                time.sleep(1)
                self.logger.debug("Completed LTM delay")
            except Exception as e:
                self.logger.error(f"LTM retrieval failed: {str(e)}")

        # DCM 检索
        if self.config.get("dcm", False) and self.dcm:
            self.logger.debug("Retrieving from DCM")
            try:
                # 使用DCM配置调用检索
                dcm_results = self.memory_adapter.retrieve(
                    self.dcm,
                    collection_config=self.dcm_config
                )
                chunks.extend(dcm_results)
                self.logger.debug(f"Retrieved {len(dcm_results)} from DCM")
            except Exception as e:
                self.logger.error(f"DCM retrieval failed: {str(e)}")

        self.logger.info(f"{self._name} retrieve {len(chunks)} results for query: '{input_query[:20]}...'")
        return Data((input_query, chunks))
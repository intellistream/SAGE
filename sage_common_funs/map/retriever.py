from typing import Tuple, List
import time  # 替换 asyncio 为 time 用于同步延迟
from sage_core.api.tuple import Data
from sage_core.api.base_function import BaseFunction, MemoryFunction, StatefulFunction
from sage_utils.custom_logger import CustomLogger
from sage_runtime.operator.runtime_context import RuntimeContext
from sage_common_funs.utils.template import AI_Template

# 更新后的 SimpleRetriever
class DenseRetriever(BaseFunction):
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)

        self.config = config

        
        if self.config.get("ltm", False):
            self.ltm_config = self.config.get("ltm", {})
        else:
            self.ltm = None


        # if self.config.get("dcm", False):
        #     self.dcm = self.config.get("dcm_collection")
        #     self.dcm_config = self.config.get("dcm_config", {})
        # else:
        #     self.dcm = None

    

    def execute(self, data: Data[AI_Template]) -> Data[AI_Template]:
        input_template = data.data
        raw_question:str = input_template.raw_question
        self.logger.debug(f"Starting retrieval for raw_question: {raw_question}")
        # LTM 检索
        if self.config.get("ltm", False):
            self.logger.debug("Retrieving from LTM")
            try:
                # 使用LTM配置和输入查询调用检索
                ltm_results = self.runtime_context.retrieve(
                    query=raw_question,
                    collection_config=self.ltm_config
                )
                self.logger.info(f"Retrieval Results: {ltm_results}")
                input_template.retriver_chunks.extend(ltm_results)
                self.logger.debug(f"Retrieved {len(ltm_results)} from LTM")
                # TODO: 为什么这里需要有延迟？
                # time.sleep(1)
            except Exception as e:
                self.logger.error(f"LTM retrieval failed: {str(e)}", exc_info=True)

        return Data(input_template)
    
class BM25sRetriever(BaseFunction): # 目前runtime context还只支持ltm
    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.bm25s_collection = self.config.get("bm25s_collection")
        self.bm25s_config = self.config.get("bm25s_config", {})


    def execute(self, data: Data[AI_Template]) -> Data[AI_Template]:
        input_template = data.data
        raw_question: str = input_template.raw_question
        chunks = []
        self.logger.debug(f"Starting BM25s retrieval for query: {raw_question}")

        if not self.bm25s_collection:
            raise ValueError("BM25s collection is not configured.")

        try:
            # 使用BM25s配置和输入查询调用检索
            bm25s_results = self.runtime_context.retrieve(
                # self.bm25s_collection,
                query=raw_question,
                collection_config=self.bm25s_config
            )
            chunks.extend(bm25s_results)
            self.logger.info(f"Retrieved {len(bm25s_results)} from BM25s\033[0m ")
            input_template.retriver_chunks.extend(bm25s_results)
        except Exception as e:
            self.logger.error(f"BM25s retrieval failed: {str(e)}")

        return Data(input_template)
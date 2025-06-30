from typing import Union, List, Tuple, Optional, Dict
from sage.api.base_function import BaseFunction
from sage.api.base_operator import Data
from sage.core.runtime.memory_adapter import MemoryAdapter


class MemoryWriter(BaseFunction):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        # 初始化各类型集合
        self.collections = {}

        # 配置STM
        if self.config.get("stm", False):
            stm_config = self.config.get("stm_config", {})
            self.collections["stm"] = {
                "collection": self.config.get("stm_collection"),
                "config": stm_config
            }

        # 配置LTM
        if self.config.get("ltm", False):
            ltm_config = self.config.get("ltm_config", {})
            self.collections["ltm"] = {
                "collection": self.config.get("ltm_collection"),
                "config": ltm_config
            }

        # 配置DCM
        if self.config.get("dcm", False):
            dcm_config = self.config.get("dcm_config", {})
            self.collections["dcm"] = {
                "collection": self.config.get("dcm_collection"),
                "config": dcm_config
            }

        # 创建内存适配器
        self.memory_adapter = MemoryAdapter()
        # 适配器日志关联算子日志
        self.memory_adapter.logger = self.logger

    def execute(self, data: Data[Union[str, List[str], Tuple[str, str]]]) -> Data:
        input_data = data.data

        # 统一数据类型处理
        processed_data = []
        if isinstance(input_data, list):
            processed_data = input_data
        elif isinstance(input_data, tuple) and len(input_data) == 2:
            processed_data = [f"{input_data[0]}{input_data[1]}"]  # 拼接元组
        elif isinstance(input_data, str):
            processed_data = [input_data]
        else:
            self.logger.error(f"Unsupported data type: {type(input_data)}")
            return data

        # 写入所有启用的集合
        for mem_type, settings in self.collections.items():
            collection = settings["collection"]
            config = settings["config"]
            if not collection:
                self.logger.warning(f"{mem_type.upper()} collection not initialized")
                continue

            try:
                self.memory_adapter.store(
                    collection=collection,
                    documents=processed_data,
                    collection_config=config
                )
                self.logger.debug(f"Stored {len(processed_data)} chunks to {mem_type.upper()}")
            except Exception as e:
                self.logger.error(f"Failed to store to {mem_type.upper()}: {str(e)}")

        return data  # 返回原始数据
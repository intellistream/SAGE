# file: sage/core/sage_memory/memory_collection/base_collection.py
# python -m sage.core.sage_memory.memory_collection.base_collection

import os
import hashlib
from dotenv import load_dotenv
from typing import Dict, Optional, Callable, Any, List
from neuromem.storage_engine.text_storage import TextStorage
from neuromem.storage_engine.metadata_storage import MetadataStorage




# 加载工程根目录下 sage/.env 配置
# Load configuration from .env file under the sage directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../../.env'))

class BaseMemoryCollection:
    """
    Base memory collection with support for raw text and metadata management.
    支持原始文本和元数据管理的基础内存集合类。
    """

    def __init__(self, name: str):
        self.name = name
        self.text_storage = TextStorage()
        self.metadata_storage = MetadataStorage()

    def _get_stable_id(self, raw_text: str) -> str:
        """
        Generate stable ID from raw text using SHA256.
        使用 SHA256 生成稳定的文本 ID。
        """
        return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    def filter_ids(
        self,
        ids: List[str],
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **metadata_conditions
    ) -> List[str]:
        """
        Filter given IDs based on metadata filter function or exact match conditions.
        基于元数据过滤函数或条件筛选给定ID列表中的条目。
        """
        matched_ids = []

        for item_id in ids:
            metadata = self.metadata_storage.get(item_id)

            if metadata_filter_func:
                if metadata_filter_func(metadata):
                    matched_ids.append(item_id)
            else:
                if all(metadata.get(k) == v for k, v in metadata_conditions.items()):
                    matched_ids.append(item_id)

        return matched_ids

    def get_all_ids(self) -> List[str]:
        """
        Get all stored item IDs.
        获取所有存储的条目ID。
        """
        return self.text_storage.get_all_ids()
        # return list(self.text_storage._store.keys())

    def add_metadata_field(self, field_name: str):
        """
        Register a metadata field.
        注册一个元数据字段。
        """
        self.metadata_storage.add_field(field_name)

    def insert(self, raw_text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store raw text with optional metadata.
        存储原始文本与可选的元数据。
        """
        stable_id = self._get_stable_id(raw_text)
        self.text_storage.store(stable_id, raw_text)

        if metadata:
            self.metadata_storage.store(stable_id, metadata)

        return stable_id
    
    def retrieve(
        self,
        with_metadata: bool = False,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **metadata_conditions
    ):
        """
        Retrieve raw texts optionally filtered by metadata.
        根据元数据（条件或函数）检索原始文本。
        """
        all_ids = self.get_all_ids()
        matched_ids = self.filter_ids(all_ids, metadata_filter_func, **metadata_conditions)
        # return [self.text_storage.get(i) for i in matched_ids]
        if with_metadata:
            return [{"text": self.text_storage.get(i), "metadata": self.metadata_storage.get(i)} for i in matched_ids]
        else:
            return [self.text_storage.get(i) for i in matched_ids]
        
    def clear(self):
        """
        Clear all stored text and metadata.
        清空所有存储的文本和元数据。
        """
        self.text_storage.clear()
        self.metadata_storage.clear()
        

def get_default_data_dir():
    # 找到 sage 的父目录，并拼 data/sage_memory
    this_file = os.path.abspath(__file__)
    parts = this_file.split(os.sep)
    try:
        sage_idx = parts.index('sage')
    except ValueError:
        sage_idx = len(parts) - 1
    project_root = os.sep.join(parts[:sage_idx+1])
    data_dir = os.path.join(os.path.dirname(project_root), "data", "sage_memory")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

    
if __name__ == "__main__":

    def basetest():
        import time
        from datetime import datetime
        col = BaseMemoryCollection("demo")
        col.add_metadata_field("source")
        col.add_metadata_field("lang")
        col.add_metadata_field("timestamp")  # 添加时间戳字段

        # 添加带时间戳的数据
        current_time = time.time()
        col.insert("hello world", {"source": "user", "lang": "en", "timestamp": current_time - 3600})  # 1小时前
        col.insert("你好，世界", {"source": "user", "lang": "zh", "timestamp": current_time - 1800})  # 30分钟前
        col.insert("bonjour le monde", {"source": "web", "lang": "fr", "timestamp": current_time})  # 现在

        print("=== Filter by keyword ===")
        res1 = col.retrieve(source="user")
        for r in res1:
            print(r)

        print("\n=== Filter by custom function (language) ===")
        res2 = col.retrieve(metadata_filter_func=lambda m: m.get("lang") in {"zh", "fr"})
        for r in res2:
            print(r)

        print(f"\nCurrent time: {datetime.fromtimestamp(current_time)}")
        
        print("\n=== Filter by timestamp (last 45 minutes) ===")
        time_threshold = current_time - 2700  # 45分钟前
        matched_ids = col.filter_ids(col.get_all_ids(), metadata_filter_func=lambda m: m.get("timestamp", 0) > time_threshold)
        for item_id in matched_ids:
            text = col.text_storage.get(item_id)
            metadata = col.metadata_storage.get(item_id)
            print(f"{text} (timestamp: {datetime.fromtimestamp(metadata['timestamp']).strftime('%Y-%m-%d %H:%M:%S')})")

        print("\n=== Filter by timestamp range (30-60 minutes ago) ===")
        start_time = current_time - 3600  # 1小时前
        end_time = current_time - 1800    # 30分钟前
        matched_ids = col.filter_ids(col.get_all_ids(), metadata_filter_func=lambda m: start_time <= m.get("timestamp", 0) <= end_time)
        for item_id in matched_ids:
            text = col.text_storage.get(item_id)
            metadata = col.metadata_storage.get(item_id)
            print(f"{text} (timestamp: {datetime.fromtimestamp(metadata['timestamp']).strftime('%Y-%m-%d %H:%M:%S')})")


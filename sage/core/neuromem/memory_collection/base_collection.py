# file: sage/core/neuromem/memory_collection/base_collection.py
# python -m sage.core.neuromem.memory_collection.base_collection

import os
import hashlib
import numpy as np
from dotenv import load_dotenv
from typing import Dict, Optional, Callable, Any, List
from sage.core.neuromem.storage_engine.text_storage import TextStorage
from sage.core.neuromem.storage_engine.metadata_storage import MetadataStorage
from sage.core.neuromem.storage_engine.vector_storage import VectorStorage

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
        return list(self.text_storage._store.keys())

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
        
class KVMemoryCollection(BaseMemoryCollection):
    pass

class GraphMemoryCollection(BaseMemoryCollection):
    pass

class VDBMemoryCollection(BaseMemoryCollection):
    """
    Memory collection with vector database support.
    支持向量数据库功能的内存集合类。
    """
    def __init__(self, name: str, embedding_model: Any, dim: int):
        if not hasattr(embedding_model, "encode"):
            raise TypeError("embedding_model must have an 'encode' method")
        
        super().__init__(name)
        self.embedding_model = embedding_model
        self.dim = dim
        self.vector_storage = VectorStorage()
        self.default_topk = int(os.getenv("VDB_TOPK", 3))
        self.backend_type = os.getenv("VDB_BACKEND", "FAISS")
        self.indexes = {}  # index_name -> dict: { index, description, filter_func, conditions }

    def create_index(
        self,
        index_name: str,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        description: str = "",
        **metadata_conditions
    ):
        """
        使用元数据筛选条件创建新的向量索引。
        """
        if self.backend_type == "FAISS":
            from sage.core.neuromem.search_engine.vdb_index.faiss_index import FaissBackend

            all_ids = self.get_all_ids()
            filtered_ids = self.filter_ids(all_ids, metadata_filter_func, **metadata_conditions)

            vectors = [self.vector_storage.get(i) for i in filtered_ids]
            index = FaissBackend(index_name, self.dim, vectors, filtered_ids)

            self.indexes[index_name] = {
                "index": index,
                "description": description,
                "metadata_filter_func": metadata_filter_func,
                "metadata_conditions": metadata_conditions,
            }

    def delete_index(self, index_name: str):
        """
        删除指定名称的索引。
        """
        if index_name in self.indexes:
            del self.indexes[index_name]
        else:
            raise ValueError(f"Index '{index_name}' does not exist.")

    def rebuild_index(self, index_name: str):
        """
        使用原始创建条件重建指定索引。
        """
        if index_name not in self.indexes:
            raise ValueError(f"Index '{index_name}' does not exist.")
        
        info = self.indexes[index_name]
        self.delete_index(index_name)  # 删除旧索引以避免冲突
        self.create_index(
            index_name=index_name,
            metadata_filter_func=info["metadata_filter_func"],
            description=info["description"],
            **info["metadata_conditions"]
        )

    def list_index(self) -> List[Dict[str, str]]:
        """
        列出当前所有索引及其描述信息。
        返回结构：[{"name": ..., "description": ...}, ...]
        """
        return [
            {"name": name, "description": info["description"]}
            for name, info in self.indexes.items()
        ]
    
    def insert(
        self,
        raw_text: str,
        metadata: Optional[Dict[str, Any]] = None,
        *index_names: str
    ) -> str:
        stable_id = self._get_stable_id(raw_text)
        self.text_storage.store(stable_id, raw_text)

        if metadata:
            self.metadata_storage.store(stable_id, metadata)

        embedding = self.embedding_model.encode(raw_text)
        
        if hasattr(embedding, "detach") and hasattr(embedding, "cpu"):
            embedding = embedding.detach().cpu().numpy().astype("float32")
            
        self.vector_storage.store(stable_id, embedding)
        
        for index_name in index_names:
            if index_name not in self.indexes:
                raise ValueError(f"Index '{index_name}' does not exist.")
            index = self.indexes[index_name]["index"]
            index.insert(embedding, stable_id)  # 不用加 []

        return stable_id

    def update(
        self,
        former_text: str,
        new_text: str,
        new_metadata: Optional[Dict[str, Any]] = None,
        *index_names: str
    ) -> str:
        old_id = self._get_stable_id(former_text)
        if not self.text_storage.has(old_id):
            raise ValueError("Original text not found.")

        self.text_storage.delete(old_id)
        self.metadata_storage.delete(old_id)
        self.vector_storage.delete(old_id)

        for index in self.indexes.values():
            index["index"].delete(old_id)

        return self.insert(new_text, new_metadata, *index_names)

    def delete(self, raw_text: str):
        stable_id = self._get_stable_id(raw_text)
        self.text_storage.delete(stable_id)
        self.metadata_storage.delete(stable_id)
        self.vector_storage.delete(stable_id)

        for index in self.indexes.values():
            index["index"].delete(stable_id)

    def retrieve(
        self,
        raw_text: str,
        topk: Optional[int] = None,
        index_name: Optional[str] = None,
        with_metadata: bool = False,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **metadata_conditions
    ) :
        if index_name is None or index_name not in self.indexes:
            raise ValueError(f"Index '{index_name}' does not exist.")

        if topk is None:
            topk = self.default_topk

        query_embedding = self.embedding_model.encode(raw_text)

        if hasattr(query_embedding, "detach") and hasattr(query_embedding, "cpu"):
            query_embedding = query_embedding.detach().cpu().numpy()
        elif isinstance(query_embedding, list):
            # 处理 Python 列表
            query_embedding = np.array(query_embedding, dtype=np.float32)
        sub_index = self.indexes[index_name]["index"]
        top_k_ids, _ = sub_index.search(query_embedding, topk=topk)

        if top_k_ids and isinstance(top_k_ids[0], (list, np.ndarray)):
            top_k_ids = top_k_ids[0]
        top_k_ids = [str(i) for i in top_k_ids]

        filtered_ids = self.filter_ids(top_k_ids, metadata_filter_func, **metadata_conditions)

        # 检查是否返回数量不足，自动重建索引并重试
        if len(filtered_ids) < topk:
            self.rebuild_index(index_name)
            sub_index = self.indexes[index_name]["index"]
            top_k_ids, _ = sub_index.search(query_embedding, topk=topk * 2)
            if top_k_ids and isinstance(top_k_ids[0], (list, np.ndarray)):
                top_k_ids = top_k_ids[0]
            top_k_ids = [str(i) for i in top_k_ids]
            filtered_ids = self.filter_ids(top_k_ids, metadata_filter_func, **metadata_conditions)
            filtered_ids = filtered_ids[:topk]

        if with_metadata:
            return [{"text": self.text_storage.get(i), "metadata": self.metadata_storage.get(i)}for i in filtered_ids]
        else:
            return [self.text_storage.get(i) for i in filtered_ids]

    
if __name__ == "__main__":

    def basetest():
        import time
        from datetime import datetime, timedelta
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
            
    def vdbtest():
        import time
        from datetime import datetime
        from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder

        default_model = MockTextEmbedder(fixed_dim=128)

        # Initialize VDBMemoryCollection
        col = VDBMemoryCollection("vdb_demo", default_model, 128)
        col.add_metadata_field("source")
        col.add_metadata_field("lang")
        col.add_metadata_field("timestamp")

        # Insert test data
        current_time = time.time()
        texts = [
            ("hello world", {"source": "user", "lang": "en", "timestamp": current_time - 3600}),
            ("你好，世界", {"source": "user", "lang": "zh", "timestamp": current_time - 1800}),
            ("bonjour le monde", {"source": "web", "lang": "fr", "timestamp": current_time}),
        ]
        inserted_ids = [col.insert(text, metadata) for text, metadata in texts]

        # Test 1: Create index by language
        print("=== 测试1：按语言创建索引 (English and French only) ===")
        col.create_index(
            index_name="en_fr_index",
            metadata_filter_func=lambda m: m.get("lang") in {"en", "fr"}
        )
        results = col.retrieve(
            "test query", topk=10, index_name="en_fr_index",
            metadata_filter_func=lambda m: m.get("lang") in {"en", "fr"}
        )
        expected_texts = ["hello world", "bonjour le monde"]
        print("Expected Texts:", expected_texts)
        print("Actual Texts:", results)
        print("Test 1 Pass:", set(results) == set(expected_texts))

        # Test 2: Create index by timestamp
        print("\n=== 测试2：按时间范围创建索引 (Last 45 minutes) ===")
        time_threshold = current_time - 2700
        col.create_index(
            index_name="recent_index",
            metadata_filter_func=lambda m: m.get("timestamp", 0) > time_threshold
        )
        results = col.retrieve(
            "test query", topk=10, index_name="recent_index",
            metadata_filter_func=lambda m: m.get("timestamp", 0) > time_threshold
        )
        expected_texts = ["你好，世界", "bonjour le monde"]
        print("Expected Texts:", expected_texts)
        print("Actual Texts:", results)
        print("Test 2 Pass:", set(results) == set(expected_texts))

        # Test 3: Vector search using en_fr_index
        print("\n=== 测试3：向量搜索 (Vector Search using retrieve) ===")
        query_text = "hello"
        results = col.retrieve(query_text, topk=2, index_name="en_fr_index")
        expected_top_text = ["hello world"]
        for text in results:
            item_id = col._get_stable_id(text)# type: ignore
            metadata = col.metadata_storage.get(item_id)
            timestamp = datetime.fromtimestamp(metadata['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{text} (lang: {metadata['lang']}, timestamp: {timestamp})")
        print("Expected Top Text:", expected_top_text)
        print("Actual Texts:", results)
        print("Test 3 Pass:", results[0] in expected_top_text if results else False)

        # Test 4: Combined metadata + vector search (user only)
        print("\n=== 测试4：元数据过滤与向量搜索结合 (User source + Vector Search) ===")
        results = col.retrieve(
            query_text, topk=1, index_name="en_fr_index",
            metadata_filter_func=lambda m: m.get("source") == "user"
        )
        expected_top_text = ["hello world"]
        for text in results:
            item_id = col._get_stable_id(text) # type: ignore
            metadata = col.metadata_storage.get(item_id)
            timestamp = datetime.fromtimestamp(metadata['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{text} (lang: {metadata['lang']}, timestamp: {timestamp})")
        print("Expected Top Text:", expected_top_text)
        print("Actual Texts:", results)
        print("Test 4 Pass:", results[0] in expected_top_text if results else False)

        # Test 5: Recent + Vector Search
        print("\n=== 测试5：时间范围过滤与向量搜索 (Last 45 minutes + Vector Search) ===")
        results = col.retrieve(
            query_text, topk=2, index_name="recent_index",
            metadata_filter_func=lambda m: m.get("timestamp", 0) > time_threshold
        )
        expected_top_text = ["你好，世界", "bonjour le monde"]
        for text in results:
            item_id = col._get_stable_id(text)# type: ignore
            metadata = col.metadata_storage.get(item_id)
            timestamp = datetime.fromtimestamp(metadata['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{text} (lang: {metadata['lang']}, timestamp: {timestamp})")
        print("Expected Top Text:", expected_top_text)
        print("Actual Texts:", results)
        print("Test 5 Pass:", results[0] in expected_top_text if results else False)
        
        # Test 6: Delete index and ensure it's gone
        print("\n=== 测试6：删除索引 (Delete Index Test) ===")
        col.delete_index("en_fr_index")
        try:
            col.retrieve("hello", index_name="en_fr_index")
            print("Test 6 Fail: Retrieval should have raised an error.")
        except ValueError as e:
            print("Caught expected error:", str(e))
            print("Test 6 Pass: Index deletion effective.")

        print("\n=== 测试7：重建索引 (Rebuild Index Test) ===")

        # 先打印重建前索引中向量数量（假设FaissBackend有ntotal属性）
        index_obj = col.indexes["recent_index"]["index"]
        old_size = getattr(index_obj, "ntotal", None)
        print(f"Index size before rebuild: {old_size}")

        # 重建索引
        col.rebuild_index("recent_index")

        index_obj = col.indexes["recent_index"]["index"]
        new_size = getattr(index_obj, "ntotal", None)
        print(f"Index size after rebuild: {new_size}")

        print("Test 7 Pass:", new_size is not None and new_size > 0)

        # 测试重建后是否能正常检索
        results = col.retrieve("hello", index_name="recent_index")
        print("Results after rebuild:", results)


        print("\n=== 测试8：列出索引信息 (List Index Info) ===")

        # 创建一个示例索引，带描述
        def lang_filter(meta):
            return meta.get("lang") in ("en", "fr")

        col.create_index(
            "lang_index",
            metadata_filter_func=lang_filter,
            description="English and French only"
        )

        # 列出所有索引及其描述
        index_info = col.list_index()
        for info in index_info:
            print(f"Index Name: {info['name']}, Description: {info['description']}")

        expected_names = {"recent_index", "lang_index"}
        actual_names = {info["name"] for info in index_info}
        print("Test 8 Pass:", expected_names.issubset(actual_names))

        print("\n=== 测试9：插入文本时直接加入索引 ===")

        col.create_index(
            index_name="user_index",
            metadata_filter_func=lambda m: m.get("source") == "user"
        )

        # 插入数据并指定立即加入索引
        col.insert("hi there", {"source": "user", "lang": "en"}, "user_index")

        results = col.retrieve("hi", index_name="user_index")
        print("Expected: ['hi there']")
        print("Actual:", results)
        print("Test 9 Pass:", "hi there" in results)

        print("\n=== 测试10：更新文本，删除旧的并加入新索引 ===")

        # 更新“hello world”为新文本，并加进 recent_index
        col.update("hello world", "hello new world", {"source": "user", "lang": "en", "timestamp": current_time}, "recent_index")

        # 检查旧的是否被删除，新内容是否存在
        results = col.retrieve("hello", index_name="recent_index")
        print("Expected: ['hello new world']")
        print("Actual:", results)
        print("Test 10 Pass:", "hello new world" in results and "hello world" not in results)

        print("\n=== 测试11：删除文本后检索失败 ===")

        # 删除刚插入的“hi there”
        col.delete("hi there")

        # 重新检索看看还在不在
        results = col.retrieve("hi", index_name="user_index")
        print("Expected: []")
        print("Actual:", results)
        print("Test 11 Pass:", "hi there" not in results)

        print("\n=== 测试12：向量检索不足触发索引重建 ===")

        # 假设我们手动删除 recent_index 中某条向量
        some_id = col._get_stable_id("bonjour le monde")
        col.indexes["recent_index"]["index"].delete(some_id)

        # 再次查询，索引应重建
        results = col.retrieve("bonjour", topk=2, index_name="recent_index")
        print("Results:", results)
        print("Test 12 Pass:", "bonjour le monde" in results)

        print("\n=== 测试13：插入时指定不存在的索引名 ===")

        try:
            col.insert("invalid index test", {"source": "user"}, "non_existing_index")
            print("Test 13 Fail: Expected error for non-existent index.")
        except ValueError as e:
            print("Caught expected error:", str(e))
            print("Test 13 Pass: Error raised as expected.")


    vdbtest()

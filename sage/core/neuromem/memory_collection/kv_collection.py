# file sage/core/neuromem/memory_collection/kv_collection.py
# python -m sage.core.neuromem.memory_collection.kv_collection

import yaml
import warnings
from sage.core.neuromem.memory_collection.base_collection import BaseMemoryCollection
from typing import Union, Optional, Dict, Any, List, Callable


def load_config(path: str) -> dict:
    """加载YAML配置文件"""
    with open(path, 'r') as f:
        return yaml.safe_load(f)

class KVMemoryCollection(BaseMemoryCollection):
    """
    基于键值对的内存集合，继承自 BaseMemoryCollection
    提供基本的键值存储和检索功能
    """
    def __init__(
        self,
        name: str,
        config_path: Optional[str] = None,
        load_path: Optional[str] = None,
        ):
        super().__init__(name)
        
        self.indexes = {} # index_name -> {index_type, description, filter_func, filter_conditions}
        
        if load_path is not None and config_path is None:
            pass
        
        if config_path is not None and load_path is None:
            config = load_config(config_path)
            self.default_topk = config.get("kv_default_topk", 10)
            self.default_index_type = config.get("kv_default_index_type", "bm25s")

        else:
            self.default_topk = 5
            self.default_index_type = "bm25s"

    def insert(
        self,
        raw_text: str, 
        metadata: Optional[Dict[str, Any]] = None,
        *index_names: str
    ):

        stable_id = self._get_stable_id(raw_text)
        self.text_storage.store(stable_id, raw_text)
        if metadata:
            self.metadata_storage.store(stable_id, metadata)
                
        for index_name in index_names:
            if index_name not in self.indexes:
                warnings.warn(f"Index '{index_name}' does not exist.", category=UserWarning)
                continue
            index = self.indexes[index_name]["index"]
            index.insert(raw_text, stable_id)
                
        return stable_id
    
    def delete(self, raw_text: str):
        stable_id = self._get_stable_id(raw_text)
        self.text_storage.delete(stable_id)
        self.metadata_storage.delete(stable_id)

        for index in self.indexes.values():
            index["index"].delete(stable_id)
    
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

        for index in self.indexes.values():
            index["index"].delete(old_id)
            
        return self.insert(new_text, new_metadata, *index_names)
    
    def retrieve(
        self,
        raw_text: str,
        topk: Optional[int] = None,
        with_metadata: Optional[bool] = False,
        index_name: Optional[str] = None,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **metadata_conditions
    ):
        if index_name is None or index_name not in self.indexes:
            warnings.warn(f"Index '{index_name}' does not exist.", category=UserWarning)
            return []
        
        if topk is None:
            topk = self.default_topk
        
        index = self.indexes[index_name]["index"]
        topk_ids = index.search(raw_text, topk=topk)
        filtered_ids = self.filter_ids(topk_ids, metadata_filter_func, **metadata_conditions)
        
        # # 检查是否返回数量不足，自动重建索引并重试
        # if len(filtered_ids) < topk:
        if with_metadata:
            return [{"text": self.text_storage.get(i), "metadata": self.metadata_storage.get(i)}for i in filtered_ids]
        else:
            return [self.text_storage.get(i) for i in filtered_ids]

    
    def create_index(
        self,
        index_name: str,
        index_type: Optional[str] = None,
        description: Optional[str] = None,
        metadata_filter_func: Optional[Callable[[Dict[str, Any]], bool]] = None,
        **metadata_conditions
        ):

        if index_type is None:
            index_type = self.default_index_type
        if description is None:
            description = ""
                
        all_ids = self.get_all_ids()
        filtered_ids = self.filter_ids(all_ids, metadata_filter_func, **metadata_conditions)
        texts = [self.text_storage.get(i) for i in filtered_ids]
            
        if index_type == "bm25s":
            from sage.core.neuromem.search_engine.kv_index.bm25s_index import BM25sIndex
            index = BM25sIndex(index_name, texts=texts, ids=filtered_ids)
            
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
        if index_name not in self.indexes:
            warnings.warn(f"Index '{index_name}' does not exist.", category=UserWarning)
            return False
        
        info = self.indexes[index_name]
        self.delete_index(index_name) 
        self.create_index(
            index_name=index_name,
            metadata_filter_func=info["metadata_filter_func"],
            description=info["description"],
            **info["metadata_conditions"]
        )
        return True
    
    def list_index(self) -> List[Dict[str, str]]:
        """
        列出当前所有索引及其描述信息。
        返回结构：[{"name": ..., "description": ...}, ...]
        """
        return [
            {"name": name, "description": info["description"]}
            for name, info in self.indexes.items()
        ]
        
def colored(text, color):
    # color: "green", "red", "yellow"
    colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "reset": "\033[0m"}
    return colors.get(color, "") + text + colors["reset"]

def print_test_case(desc, expected, actual):
    status = "通过" if expected == actual or (isinstance(expected, set) and set(expected) == set(actual)) else "不通过"
    color = "green" if status == "通过" else "red"
    print(f"【{desc}】")
    print(f"预期结果：{expected}")
    print(f"实际结果：{actual}")
    print(f"测试情况：{colored(status, color)}\n")

if __name__ == "__main__":
    col = KVMemoryCollection(name="demo")

    col.add_metadata_field("field1")
    col.add_metadata_field("field2")
    col.add_metadata_field("field3")

    id1 = col.insert("Hello Jack.", {"field1": "1", "field2": "0", "field3": "3"})
    id2 = col.insert("Hello Tom.", {"field1": "1", "field2": "1"})
    id3 = col.insert("Hello Alice.", {"field1": "0", "field2": "1"})

    col.create_index("global_index")
    col.create_index("f2_1_index", metadata_filter_func=lambda m: m.get("field2") == "1")

    # 1. 关键词检索（全局）
    res1 = col.retrieve("Jack", topk=1, index_name="global_index")
    print_test_case("检索全局单条", ["Hello Jack."], res1)

    # 2. 带 metadata_filter_func 检索
    res2 = col.retrieve("Alice", topk=1, index_name="global_index", metadata_filter_func=lambda m: m.get("field2") == "1")
    print_test_case("metadata_filter_func 检索", ["Hello Alice."], res2)

    # 3. 只用元数据索引
    res3 = col.retrieve("Tom", topk=2, index_name="f2_1_index")
    print_test_case("基于条件索引检索", {"Hello Tom.", "Hello Alice."}, set(res3))

    # 4. 删除测试
    col.delete("Hello Tom.")
    res4 = col.retrieve("Tom", topk=3, index_name="global_index")
    test_pass = "Hello Tom." not in res4
    print_test_case("删除功能", True, test_pass)

    # 5. 更新测试
    col.update("Hello Jack.", "Hello Jacky.", {"field1": "2", "field2": "9", "field3": "8"}, "global_index", "f2_1_index")
    res5 = col.retrieve("Jacky", topk=1, index_name="global_index")
    print_test_case("更新功能", ["Hello Jacky."], res5)

    # 6. 检查元数据同步
    meta = col.metadata_storage.get(col._get_stable_id("Hello Jacky."))
    print_test_case("元数据同步", {"field1": "2", "field2": "9", "field3": "8"}, meta)

    # 7. 非法删除
    try:
        col.delete("NonExistentText")
        print_test_case("非法删除异常", "无异常", "无异常")
    except Exception as e:
        print_test_case("非法删除异常", "无异常", f"异常：{e}")

    # 8. 非法索引检索
    try:
        col.retrieve("anything", index_name="non_exist_index")
        print_test_case("非法索引检索", "无异常", "无异常")
    except Exception as e:
        print_test_case("非法索引检索", "无异常", f"异常：{e}")

    # 9. 删除索引测试
    col.delete_index("f2_1_index")
    print_test_case("删除索引", False, "f2_1_index" in col.indexes)

    # 10. 重建索引测试
    rebuild_res = col.rebuild_index("global_index")
    print_test_case("重建索引", True, rebuild_res)

    
# file sage/core/neuromem/memory_collection/kv_collection.py
# python -m sage.core.neuromem.memory_collection.kv_collection

import os
import json
import yaml
import shutil
import inspect
import warnings
from sage.core.neuromem.memory_collection.base_collection import BaseMemoryCollection, get_default_data_dir
from typing import Union, Optional, Dict, Any, List, Callable

# 通过config文件指定默认索引，neuromem默认索引，用户指定索引

def get_func_source(func):
    if func is None:
        return None
    try:
        return inspect.getsource(func).strip()
    except Exception:
        return str(func)  # 对于lambda等可能只能保存 repr

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
            self._load(load_path)   # 自动加载全部内容
        
        if config_path is not None and load_path is None:
            config = load_config(config_path)
            self.default_topk = config.get("kv_default_topk", 10)
            self.default_index_type = config.get("kv_default_index_type", "bm25s")

        else:
            self.default_topk = 5
            self.default_index_type = "bm25s"

    @classmethod
    def load(cls, name: str, load_path: Optional[str] = None) -> "KVMemoryCollection":
        if load_path is None:
            load_path = os.path.join(get_default_data_dir(), "kv_collection", name)
        else:
            load_path = os.path.join(load_path, "kv_collection", name)
        return cls(name=name, load_path=load_path)


    def store(self, store_path: Optional[str] = None) -> Dict[str, Any]:
        if store_path is None:
            store_path = get_default_data_dir()
        # 加上kv_collection
        collection_dir = os.path.join(store_path, "kv_collection", self.name)
        os.makedirs(collection_dir, exist_ok=True)

        # 存储 text 和 metadata
        text_path = os.path.join(collection_dir, "text_storage.json")
        metadata_path = os.path.join(collection_dir, "metadata_storage.json")
        self.text_storage.store_to_disk(text_path)
        self.metadata_storage.store_to_disk(metadata_path)

        # 存储每个 index
        index_info = {}
        for index_name, info in self.indexes.items():
            idx_type = info["index_type"]
            idx = info["index"]
            idx_type_dir = os.path.join(collection_dir, idx_type)
            idx_path = os.path.join(idx_type_dir, index_name)
            os.makedirs(idx_path, exist_ok=True)
            idx.store(idx_path)
            index_info[index_name] = {
                "index_type": idx_type,
                "description": info.get("description", ""),
                "metadata_filter_func": get_func_source(info.get("metadata_filter_func")),
                "metadata_conditions": info.get("metadata_conditions", {}),
            }


        config = {
            "name": self.name,
            "default_topk": self.default_topk,
            "default_index_type": self.default_index_type,
            "indexes": index_info,
        }
        config_path = os.path.join(collection_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return {"collection_path": collection_dir}

    def _load(self, load_path: str):
        config_path = os.path.join(load_path, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No config found for collection at {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        self.default_topk = config.get("default_topk", 5)
        self.default_index_type = config.get("default_index_type", "bm25s")

        # 恢复 text 和 metadata
        text_path = os.path.join(load_path, "text_storage.json")
        metadata_path = os.path.join(load_path, "metadata_storage.json")
        self.text_storage.load_from_disk(text_path)
        self.metadata_storage.load_from_disk(metadata_path)

        # 加载各 index
        for index_name, idx_info in config.get("indexes", {}).items():
            idx_type = idx_info["index_type"]
            idx_path = os.path.join(load_path, idx_type, index_name)
            if idx_type == "bm25s":
                from sage.core.neuromem.search_engine.kv_index.bm25s_index import BM25sIndex
                idx = BM25sIndex.load(index_name, idx_path)
            else:
                raise NotImplementedError(f"Index type {idx_type} not supported")
            self.indexes[index_name] = {
                "index": idx,
                "index_type": idx_type,
                "description": idx_info.get("description", ""),
                "metadata_filter_func": idx_info.get("metadata_filter_func"),
                "metadata_conditions": idx_info.get("metadata_conditions", {}),
            }

    @staticmethod
    def clear(name: str, clear_path: Optional[str] = None) -> None:
        if clear_path is None:
            clear_path = get_default_data_dir()
        collection_dir = os.path.join(clear_path, "kv_collection", name)
        try:
            shutil.rmtree(collection_dir)
            print(f"Cleared collection: {collection_dir}")
        except FileNotFoundError:
            print(f"Collection does not exist: {collection_dir}")
        except Exception as e:
            print(f"Failed to clear: {e}")

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
            "index_type": index_type,
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

if __name__ == "__main__":
    import inspect

    def colored(text, color):
        colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "reset": "\033[0m"}
        return colors.get(color, "") + text + colors["reset"]

    def print_test_case(desc, expected, actual):
        status = "通过" if expected == actual or (isinstance(expected, set) and set(expected) == set(actual)) else "不通过"
        color = "green" if status == "通过" else "red"
        print(f"【{desc}】")
        print(f"预期结果：{expected}")
        print(f"实际结果：{actual}")
        print(f"测试情况：{colored(status, color)}\n")

    # ==== 基础数据构建 ====
    col = KVMemoryCollection(name="demo")

    col.add_metadata_field("field1")
    col.add_metadata_field("field2")
    col.add_metadata_field("field3")

    # 多样化插入
    id1 = col.insert("Hello Jack.", {"field1": "1", "field2": "0", "field3": "3"})
    id2 = col.insert("Hello Tom.", {"field1": "1", "field2": "1", "field3": "3"})
    id3 = col.insert("Hello Alice.", {"field1": "0", "field2": "1", "field3": "3"})
    id4 = col.insert("Jack and Tom say hi.", {"field1": "1", "field2": "0", "field3": "8"})
    id5 = col.insert("Alice in Wonderland.", {"field1": "0", "field2": "1", "field3": "5"})
    id6 = col.insert("Jacky is not Jack.", {"field1": "2", "field2": "9", "field3": "8"})

    col.create_index("global_index")
    col.create_index("f2_1_index", metadata_filter_func=lambda m: m.get("field2") == "1")
    col.create_index(
        "f1_1_index",
        metadata_filter_func=lambda m: m.get("field1") == "1",
        description="field1等于1的子集索引",
        field1="1"
    )
    col.create_index(
        "field3_8_index",
        metadata_filter_func=lambda m: m.get("field3") == "8",
        description="field3等于8的子集",
        field3="8"
    )

    # ==== 功能测试 ====
    print("【数据与索引初始化完毕】\n")
    res1 = col.retrieve("Jack", topk=3, index_name="global_index")
    print_test_case("检索'Jack'相关top3", {"Hello Jack.", "Jack and Tom say hi.", "Jacky is not Jack."}, set(res1))

    res2 = col.retrieve("Alice", topk=2, index_name="global_index", metadata_filter_func=lambda m: m.get("field2") == "1")
    print_test_case("metadata_filter_func检索Alice", {"Hello Alice.", "Alice in Wonderland."}, set(res2))

    res3 = col.retrieve("Tom", topk=2, index_name="f2_1_index")
    print_test_case("基于f2_1_index索引检索Tom", {"Hello Tom.", "Hello Alice."}, set(res3))

    res4 = col.retrieve("Jack", index_name="f1_1_index")
    print_test_case("f1_1_index功能（Jack相关）", {"Hello Jack.", "Hello Tom.", "Jack and Tom say hi."}, set(res4))

    res5 = col.retrieve("Jack", index_name="field3_8_index")
    print_test_case("field3_8_index功能", {"Jack and Tom say hi.", "Jacky is not Jack."}, set(res5))

    # 删除一条不会导致全部为空
    col.delete("Hello Tom.")
    res6 = col.retrieve("Tom", index_name="global_index")
    test_pass = "Hello Tom." not in res6
    print_test_case("删除功能", True, test_pass)

    # 更新 Jacky
    col.update("Hello Jack.", "Hello Jacky.", {"field1": "2", "field2": "9", "field3": "8"}, "global_index", "f2_1_index", "f1_1_index", "field3_8_index")
    res7 = col.retrieve("Jacky", index_name="global_index")
    print_test_case("更新功能", ['Jacky is not Jack.', 'Hello Jacky.', 'Hello Alice.', 'Jack and Tom say hi.', 'Alice in Wonderland.'], res7)

    meta = col.metadata_storage.get(col._get_stable_id("Hello Jacky."))
    print_test_case("元数据同步", {"field1": "2", "field2": "9", "field3": "8"}, meta)

    # 删除全部不会报错
    try:
        col.delete("NonExistentText")
        print_test_case("非法删除异常", "无异常", "无异常")
    except Exception as e:
        print_test_case("非法删除异常", "无异常", f"异常：{e}")

    try:
        col.retrieve("anything", index_name="non_exist_index")
        print_test_case("非法索引检索", "无异常", "无异常")
    except Exception as e:
        print_test_case("非法索引检索", "无异常", f"异常：{e}")

    # 删除索引
    col.delete_index("f2_1_index")
    print_test_case("删除索引", False, "f2_1_index" in col.indexes)

    rebuild_res = col.rebuild_index("global_index")
    print_test_case("重建索引", True, rebuild_res)

    # ==== 持久化保存、恢复测试 ====
    print("\n--- 持久化测试开始 ---")
    store_path = get_default_data_dir()
    col_name = "demo"
    col.store(store_path)
    print(colored("数据已保存到磁盘！", "yellow"))
    print("目录为：", os.path.join(store_path, "kv_collection", col_name))

    del col
    print(colored("内存对象已清除。", "yellow"))

    user_input = input(colored("输入 yes 加载刚才保存的数据: ", "yellow"))
    if user_input.strip().lower() == "yes":
        col2 = KVMemoryCollection.load(col_name)
        print(colored("数据已从磁盘恢复！", "green"))

        res = col2.retrieve("Jacky", index_name="global_index")
        print_test_case("持久化后检索", ['Jacky is not Jack.', 'Hello Jacky.', 'Hello Alice.', 'Jack and Tom say hi.', 'Alice in Wonderland.'], res)
        meta = col2.metadata_storage.get(col2._get_stable_id("Hello Jacky."))
        print_test_case("持久化后元数据", {"field1": "2", "field2": "9", "field3": "8"}, meta)

        idx_meta = col2.indexes["f1_1_index"]
        print_test_case("f1_1_index恢复metadata_conditions", {"field1": "1"}, idx_meta.get("metadata_conditions", {}))
        print_test_case("f1_1_index恢复filter_func存在", True, idx_meta.get("metadata_filter_func") is not None)
        resx2 = col2.retrieve("Jack", index_name="f1_1_index")
        print_test_case("持久化后f1_1_index检索", {"Jack and Tom say hi."}, set(resx2) & {"Jack and Tom say hi."})

    else:
        print(colored("跳过加载测试。", "yellow"))

    user_input = input(colored("输入 yes 删除磁盘所有数据: ", "yellow"))
    if user_input.strip().lower() == "yes":
        KVMemoryCollection.clear(col_name)
        print(colored("所有数据已删除！", "green"))
    else:
        print(colored("未执行删除。", "yellow"))


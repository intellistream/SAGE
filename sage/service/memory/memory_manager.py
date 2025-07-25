
import os
import json
import shutil
from typing import Any, Dict, List, Optional, Union

from sage_utils.custom_logger import CustomLogger
from sage.service.memory.memory_collection.base_collection import get_default_data_dir
from sage.service.memory.memory_collection.base_collection import BaseMemoryCollection
from sage.service.memory.memory_collection.graph_collection import GraphMemoryCollection
from sage.service.memory.memory_collection.kv_collection import KVMemoryCollection
from sage.service.memory.memory_collection.vdb_collection import VDBMemoryCollection

from sage.service.memory.memory_collection.base_collection import BaseMemoryCollection
from sage.service.memory.memory_collection.graph_collection import GraphMemoryCollection
from sage.service.memory.memory_collection.kv_collection import KVMemoryCollection
from sage.service.memory.memory_collection.vdb_collection import VDBMemoryCollection
from sage_utils.embedding_methods.embedding_api import apply_embedding_model
from sage.service.memory.memory_collection.base_collection import get_default_data_dir

class MemoryManager:
    """
    内存管理器，管理不同类型的 MemoryCollection 实例
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.logger = CustomLogger()
        
        self.collections: Dict[str, BaseMemoryCollection] = {}
        self.collection_metadata: Dict[str, Dict[str, Any]] = {}
        self.collection_status: Dict[str, str] = {}  # 状态表: "loaded" or "on_disk"
        
        # 从默认目录data/sage_memory获取disk中的manager(如果有)
        self.data_dir = data_dir or get_default_data_dir()
        self.manager_path = os.path.join(self.data_dir, "manager.json")
        self._load_manager()  

    def create_collection(
            self,
            name: str,
            backend_type: str,
            description: str = "",
            embedding_model: Optional[Any] = None,
            dim: Optional[int] = None,
    ) -> BaseMemoryCollection:
        """
        创建新的集合
        直接返回collection
        """
        
        if name in self.collection_metadata:
            self.logger.warning(f"Collection with name '{name}' already exists.")
            return None

        metadata = {
        "description": description,
        "backend_type": backend_type
        }

        # 创建基础集合
        if backend_type == "VDB":
            if embedding_model is None or dim is None:
                self.logger.warning(f"VDB requires parameter 'embedding_model' and 'dim', use default values.")
                embedding_model = apply_embedding_model("default")
                dim = embedding_model.get_dim()

            new_collection = VDBMemoryCollection(name, embedding_model, dim)
            metadata.update({
                "embedding_model_method": embedding_model.method_name,
                "embedding_dim": dim
            })
        elif backend_type == "KV":
            new_collection = KVMemoryCollection(name)
        elif backend_type == "GRAPH":
            new_collection = GraphMemoryCollection(name)
        else:
            self.logger.error(f"Unsupported backend_type: {backend_type}")

        # 存储到 collections
        self.collections[name] = new_collection
        self.collection_metadata[name] = metadata
        self.collection_status[name] = "loaded"
        return new_collection

    def get_collection(self, name: str) -> Optional[BaseMemoryCollection]:
        """优先返回内存collection，不在内存则尝试磁盘懒加载并发警告"""
        if name in self.collections:
            return self.collections[name]
        elif name in self.collection_metadata:
            self.logger.warning(f"Collection '{name}' not in memory, loading from disk.")
            return self._load_collection(name)
        else:
            self.logger.warning(f"Collection '{name}' not found.")
            return None

    def delete_collection(self, name: str):
        """删除collection：内存、元数据、磁盘三处都要删"""
        existed = False
        # 内存
        if name in self.collections:
            del self.collections[name]
            existed = True
        # 元信息
        if name in self.collection_metadata:
            backend_type = self.collection_metadata[name].get("backend_type")
            del self.collection_metadata[name]
            self.collection_status.pop(name, None)
            existed = True
            # 磁盘
            if backend_type == "VDB":
                path = os.path.join(self.data_dir, "vdb_collection", name)
            elif backend_type == "KV":
                path = os.path.join(self.data_dir, "kv_collection", name)
            elif backend_type == "GRAPH":
                path = os.path.join(self.data_dir, "graph_collection", name)
            else:
                path = None
            if path and os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except Exception as e:
                    self.logger.warning(f"Failed to delete disk collection '{name}': {e}")
        if not existed:
            self.logger.warning(f"Collection '{name}' not found.")
        self._save_manager()
        
    def connect_collection(self, name: str, embedding_model=None) -> Optional[BaseMemoryCollection]:
        """类似get_collection，但支持外部embedding_model"""
        if name in self.collections:
            return self.collections[name]
        if name not in self.collection_metadata:
            self.logger.warning(f"Collection '{name}' not found in metadata.")
            return None
        meta = self.collection_metadata[name]
        backend_type = meta.get("backend_type")
        if backend_type == "VDB":
            vdb_path = os.path.join(self.data_dir, "vdb_collection", name)
            if embedding_model is None:
                method_name = meta.get("embedding_model_method", "default")
                embedding_model = apply_embedding_model(method_name)
            collection = VDBMemoryCollection.load(name, embedding_model, vdb_path)
        elif backend_type == "KV":
            kv_path = os.path.join(self.data_dir, "kv_collection", name)
            collection = KVMemoryCollection.load(name, kv_path)
        elif backend_type == "GRAPH":
            graph_path = os.path.join(self.data_dir, "graph_collection", name)
            collection = GraphMemoryCollection.load(name, graph_path)
        else:
            self.logger.warning(f"Unknown backend_type: {backend_type}")
            return None
        self.collections[name] = collection
        self.collection_status[name] = "loaded"
        return collection

    def store_collection(self, name: Optional[str] = None):
        """
        只保存已加载（即被用过的）的collection及manager信息
        """
        # 指定name只存一个，否则只存所有已加载collection
        collections_to_save = [name] if name else [
            n for n, status in self.collection_status.items() if status == "loaded"
        ]
        for cname in collections_to_save:
            if cname not in self.collections:
                continue
            wrapper = self.collections[cname]
            col_obj = wrapper.obj if hasattr(wrapper, "obj") else wrapper
            if hasattr(col_obj, "store"):
                col_obj.store(self.data_dir)
        self._save_manager()
        
    def _save_manager(self):
        with open(self.manager_path, "w", encoding="utf-8") as f:
            json.dump(self.collection_metadata, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Manager info saved to {self.manager_path}")  
          
    def _load_manager(self):
        """只加载collection_metadata和状态，不加载任何collection本体"""
        if not os.path.exists(self.manager_path):
            return
        with open(self.manager_path, "r", encoding="utf-8") as f:
            self.collection_metadata = json.load(f)
        for name in self.collection_metadata:
            self.collection_status[name] = "on_disk"
    
    def _load_collection(self, name: str) -> Optional[BaseMemoryCollection]:
        """懒加载collection进内存"""
        if name not in self.collection_metadata:
            self.logger.warning(f"Collection '{name}' metadata not found in manager.")
            return None

        meta = self.collection_metadata[name]
        backend_type = meta.get("backend_type")
        if backend_type == "VDB":
            vdb_path = os.path.join(self.data_dir, "vdb_collection", name)
            method_name = meta.get("embedding_model_method", "default")
            embedding_model = apply_embedding_model(method_name)
            collection = VDBMemoryCollection.load(name, embedding_model, vdb_path)
        elif backend_type == "KV":
            kv_path = os.path.join(self.data_dir, "kv_collection", name)
            collection = KVMemoryCollection.load(name, kv_path)
        elif backend_type == "GRAPH":
            graph_path = os.path.join(self.data_dir, "graph_collection", name)
            collection = GraphMemoryCollection.load(name, graph_path)
        else:
            self.logger.warning(f"Unknown backend_type: {backend_type}")
            return None

        self.collections[name] = collection
        self.collection_status[name] = "loaded"
        return collection
    
            
    def list_collection(self, name: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        列出一个或所有 collection 的基本信息。
        List basic info of one or all collections.
        """
        if name:
            if name not in self.collection_metadata:
                self.logger.warning(f"Collection '{name}' not found.")
                return None
            return {"name": name, "status": self.collection_status.get(name, "unknown"), **self.collection_metadata[name]}
        else:
            return [
                {"name": n, "status": self.collection_status.get(n, "unknown"), **meta}
                for n, meta in self.collection_metadata.items()
            ]

    def rename(self, former_name: str, new_name: str, new_description: Optional[str] = None):
        """重命名 collection 并更新描述"""
        if former_name not in self.collection_metadata:
            self.logger.warning(f"Collection '{former_name}' not found.")
            return False
        if new_name in self.collection_metadata:
            self.logger.warning(f"Collection '{new_name}' already exists.")
            return False

        # 重命名内存对象
        if former_name in self.collections:
            collection = self.collections.pop(former_name)
            collection.name = new_name
            self.collections[new_name] = collection

        # 重命名状态表
        if former_name in self.collection_status:
            self.collection_status[new_name] = self.collection_status.pop(former_name)

        # 更新元信息
        metadata = self.collection_metadata.pop(former_name)
        metadata["description"] = new_description or metadata.get("description", "")
        self.collection_metadata[new_name] = metadata

        # 重命名磁盘目录/文件
        backend_type = metadata.get("backend_type")
        def get_path(n):
            if backend_type == "VDB":
                return os.path.join(self.data_dir, "vdb_collection", n)
            elif backend_type == "KV":
                return os.path.join(self.data_dir, "kv_collection", n)
            elif backend_type == "GRAPH":
                return os.path.join(self.data_dir, "graph_collection", n)
        old_path = get_path(former_name)
        new_path = get_path(new_name)
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
        self._save_manager()
        return True



if __name__ == "__main__":
    import os
    import shutil

    def print_result(expect, actual, passed):
        green = '\033[92m'
        red = '\033[91m'
        endc = '\033[0m'
        print(f"预期结果：{expect}")
        print(f"实际结果：{actual}")
        print("是否通过测试：", end="")
        print(f"{green}是{endc}" if passed else f"{red}否{endc}")
        print("="*50)

    def clear_all_data(manager):
        # 删除data_dir下所有collection目录和manager.json
        base = manager.data_dir
        for subdir in ["vdb_collection"]:
            path = os.path.join(base, subdir)
            if os.path.exists(path):
                shutil.rmtree(path)
        if os.path.exists(manager.manager_path):
            os.remove(manager.manager_path)

    # 测试1: 创建新VDB collection
    manager = MemoryManager()
    c1 = manager.create_collection(name="test_vdb", backend_type="VDB")
    passed = c1 is not None and "test_vdb" in manager.collections
    print_result("新建test_vdb后能在collections中查到", str("test_vdb" in manager.collections), passed)

    # 测试2: 再次新建同名collection应警告并返回None
    c2 = manager.create_collection(name="test_vdb", backend_type="VDB")
    passed = c2 is None
    print_result("新建已存在collection应返回None", str(c2 is None), passed)

    # 测试3: list_collection返回正确，状态为loaded
    info = manager.list_collection("test_vdb")
    passed = info is not None and info['status'] == "loaded"
    print_result("list_collection显示状态为loaded", f"{info}", passed)

    # 测试4: get_collection取已存在的
    c3 = manager.get_collection("test_vdb")
    passed = c3 is c1
    print_result("get_collection能返回内存已加载对象", f"id相同: {c3 is c1}", passed)

    # 测试5: store_collection只保存已加载collection
    manager.store_collection()
    path = os.path.join(manager.data_dir, "vdb_collection", "test_vdb")
    passed = os.path.exists(path)
    print_result("store_collection后磁盘应有数据目录", str(os.path.exists(path)), passed)

    # 测试6: 模拟“只在磁盘不在内存”的懒加载
    del manager.collections["test_vdb"]
    manager.collection_status["test_vdb"] = "on_disk"
    passed = "test_vdb" not in manager.collections and os.path.exists(os.path.join(manager.data_dir, "vdb_collection", "test_vdb"))
    print_result("未加载collection不会在collections", str(passed), passed)

    # 测试7: get_collection能从磁盘懒加载
    c4 = manager.get_collection("test_vdb")
    passed = c4 is not None and "test_vdb" in manager.collections and manager.collection_status["test_vdb"] == "loaded"
    print_result("get_collection能懒加载on_disk collection", str(passed), passed)

    # 测试8: rename
    r = manager.rename("test_vdb", "renamed_vdb", "renamed desc")
    passed = r and "renamed_vdb" in manager.collections
    print_result("rename操作成功", str(r), passed)

    # store 一下，保证磁盘有数据
    manager.store_collection("renamed_vdb")

    print("\n==中间测试==")
    print("请确认manager.json、collection磁盘文件已经存在。")
    print("输入yes继续从磁盘加载测试，否则中止（将自动清理）:")
    ans = input().strip().lower()
    if ans != "yes":
        print("用户中止，已清理所有测试数据。")
        clear_all_data(manager)
        exit(0)

    # 测试9: 用新manager对象从磁盘懒加载
    manager2 = MemoryManager(manager.data_dir)
    loaded = "renamed_vdb" in manager2.collection_metadata and manager2.collection_status.get("renamed_vdb") == "on_disk"
    print_result("新manager能从磁盘加载管理信息（collection未自动加载）", str(loaded), loaded)

    # 测试10: list_collection（全部）
    all_info = manager.list_collection()
    passed = isinstance(all_info, list)
    print_result("list_collection()能返回所有collection列表", str(passed), passed)

    print("\n==中间测试==")
    print("请确认manager.json、collection磁盘文件已经存在。")
    print("输入yes继续从磁盘加载测试，否则中止（将自动清理）:")
    ans = input().strip().lower()
    if ans != "yes":
        print("用户中止，已清理所有测试数据。")
        clear_all_data(manager)
        exit(0)

    # 测试11: 用新manager对象从磁盘懒加载
    manager2 = MemoryManager(manager.data_dir)
    loaded = "test_vdb" in manager2.collection_metadata or "renamed_vdb" in manager2.collection_metadata
    print_result("新manager能从磁盘加载管理信息（collection未自动加载）", str(loaded), loaded)

    # 如果上面已重命名并删除，理论上只有空的或剩余collection
    # 为了测试懒加载，再新建并保存一次
    cnew = manager2.create_collection("lazy_test", backend_type="VDB")
    manager2.store_collection()
    del manager2.collections["lazy_test"]
    manager2.collection_status["lazy_test"] = "on_disk"
    c5 = manager2.get_collection("lazy_test")
    passed = c5 is not None and manager2.collection_status["lazy_test"] == "loaded"
    print_result("新manager懒加载on_disk collection后状态变为loaded", str(passed), passed)

    # 清理所有
    clear_all_data(manager)
    print("\n所有测试完成，已清理测试数据！")



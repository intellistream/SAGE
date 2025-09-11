import os
from logging import Manager
from re import M
from typing import Any, Dict, List, Optional, Union

from sage.middleware.components.neuromem.memory_collection.vdb_collection import \
    VDBMemoryCollection
from sage.middleware.components.neuromem.memory_manager import MemoryManager


class NeuroMemVDB:
    def __init__(self):
        self.manager = MemoryManager(self._get_default_data_dir())
        self.online_register_collection: Dict[str, VDBMemoryCollection] = {}

    def register_collection(self, collection_name: str, config=None):
        # 检查collection是否已存在
        existing_collections = self.manager.list_collection()
        collection_exists = (
            any(c["name"] == collection_name for c in existing_collections)
            if isinstance(existing_collections, list)
            else False
        )

        if collection_exists:
            if config is not None:
                print(
                    f"警告: Collection '{collection_name}' 已存在，忽略传入的config参数"
                )
            # 正常连接并注册到online_register_collection
            collection = self.manager.get_collection(collection_name)
            if collection:
                self.online_register_collection[collection_name] = collection
                print(f"成功连接已存在的collection: {collection_name}")
        else:
            if config is not None:
                # 正常通过Manager创建并注册到online_register_collection
                embedding_model = config.get("embedding_model")
                dim = config.get("dim")
                description = config.get(
                    "description", f"VDB collection: {collection_name}"
                )
                collection = self.manager.create_collection(
                    name=collection_name,
                    backend_type="VDB",
                    description=description,
                    embedding_model=embedding_model,
                    dim=dim,
                )
                if collection:
                    self.online_register_collection[collection_name] = collection
                    print(f"成功创建新collection: {collection_name}")
            else:
                # 警告 用默认参数创建一个collection并注册到online_register_collection
                print(
                    f"警告: Collection '{collection_name}' 不存在且未提供config，使用默认参数创建"
                )
                collection = self.manager.create_collection(
                    name=collection_name,
                    backend_type="VDB",
                    description=f"Default VDB collection: {collection_name}",
                )
                if collection:
                    self.online_register_collection[collection_name] = collection
                    print(f"成功创建默认collection: {collection_name}")

    def insert(self, raw_data: Any, metadata: Optional[Dict[str, Any]] = None):
        # 该方法在所有 online_register_collection 均插入数据
        if not self.online_register_collection:
            print("警告: 没有注册的collection，无法插入数据")
            return

        results = {}
        for collection_name, collection in self.online_register_collection.items():
            try:
                stable_id = collection.insert(raw_data, metadata)
                results[collection_name] = stable_id
                print(
                    f"成功在collection '{collection_name}' 中插入数据，ID: {stable_id}"
                )
            except Exception as e:
                print(f"在collection '{collection_name}' 插入数据失败: {str(e)}")
                results[collection_name] = None
        return results

    def retrieve(self, raw_data: Any, topk: int = 5):
        # 测试类型的retrieve方法，不返回任何值，直接print出检索结果
        if not self.online_register_collection:
            print("警告: 没有注册的collection，无法检索数据")
            return

        print(f"检索查询: {raw_data}")
        print("=" * 50)

        for collection_name, collection in self.online_register_collection.items():
            try:
                results = collection.retrieve(raw_data, topk=topk, with_metadata=True)
                print(f"Collection '{collection_name}' 检索结果:")
                if results:
                    for i, result in enumerate(results, 1):
                        print(f"  {i}. 文本: {result['text']}")
                        if result["metadata"]:
                            print(f"     元数据: {result['metadata']}")
                else:
                    print("  无结果")
                print("-" * 30)
            except Exception as e:
                print(f"Collection '{collection_name}' 检索失败: {str(e)}")
                print("-" * 30)

    def build_index(
        self, index_name: str = "global_index", description: str = "全局索引"
    ):
        # 该方法在所有 online_register_collection 创建指定索引
        if not self.online_register_collection:
            print("警告: 没有注册的collection，无法创建索引")
            return

        results = {}
        for collection_name, collection in self.online_register_collection.items():
            try:
                collection.create_index(index_name, description=description)
                results[collection_name] = True
                print(f"成功在collection '{collection_name}' 中创建索引 '{index_name}'")
            except Exception as e:
                print(f"在collection '{collection_name}' 创建索引失败: {str(e)}")
                results[collection_name] = False
        return results

    def store_to_disk(self):
        # 调用manager的store_collection()方法，触发一次全局落盘
        try:
            self.manager.store_collection()
            print("成功将所有collection数据保存到磁盘")
        except Exception as e:
            print(f"保存数据到磁盘失败: {str(e)}")

    def clean_collection(self, collection_name: str):
        # 清空某个collection的所有数据(包括磁盘中存在的)
        try:
            # 从在线注册列表中移除
            if collection_name in self.online_register_collection:
                del self.online_register_collection[collection_name]
                print(f"已从在线注册列表中移除collection: {collection_name}")

            # 通过manager删除collection（包括磁盘数据）
            self.manager.delete_collection(collection_name)
            print(f"成功清理collection: {collection_name}")
        except Exception as e:
            print(f"清理collection '{collection_name}' 失败: {str(e)}")

    @classmethod
    def _get_default_data_dir(cls):
        """获取默认数据目录"""
        cur_dir = os.getcwd()
        data_dir = os.path.join(cur_dir, "data", "neuromem_vdb")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir


if __name__ == "__main__":
    print("默认数据目录:", NeuroMemVDB._get_default_data_dir())
    print("\n" + "=" * 60)
    print("开始测试 NeuroMemVDB")
    print("=" * 60)

    # 创建NeuroMemVDB实例
    vdb = NeuroMemVDB()

    # 测试1: 注册不存在的collection（无config，应该警告并使用默认参数）
    print("\n1. 测试注册不存在的collection（无config）")
    vdb.register_collection("test_collection1")

    # 测试2: 注册不存在的collection（有config）
    print("\n2. 测试注册不存在的collection（有config）")
    config = {
        "description": "测试用的VDB集合",
        "embedding_model": None,  # 使用默认embedding模型
        "dim": None,  # 使用默认维度
    }
    vdb.register_collection("test_collection2", config)

    # 测试3: 插入数据
    print("\n3. 测试插入数据")
    vdb.insert("Python是一种编程语言", {"type": "test", "priority": "high"})
    vdb.insert("机器学习是人工智能的重要分支", {"type": "demo", "priority": "low"})
    vdb.insert("向量数据库用于存储和检索高维向量数据")

    # 测试4: 创建索引
    print("\n4. 测试创建索引")
    vdb.build_index("custom_index", "自定义测试索引")

    # 测试5: 检索数据
    print("\n5. 测试检索数据")
    vdb.retrieve("编程语言", topk=3)

    # 测试6: 保存到磁盘
    print("\n6. 测试保存到磁盘")
    vdb.store_to_disk()

    # 测试7: 重新注册已存在的collection（应该警告）
    print("\n7. 测试重新注册已存在的collection")
    vdb.register_collection("test_collection1", {"description": "这个config应该被忽略"})

    # 测试8: 清理collection
    print("\n8. 测试清理collection")
    vdb.clean_collection("test_collection1")

    # 测试9: 再次检索（应该只有test_collection2的结果）
    print("\n9. 清理后再次检索")
    vdb.retrieve("编程语言", topk=3)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

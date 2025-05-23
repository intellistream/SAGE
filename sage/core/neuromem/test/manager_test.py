# file sage.core/neuromem/test/manager_test.py
# python -m sage.core.neuromem.test.manager_test

from sage.core.neuromem.memory_manager import MemoryManager
from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder

default_model = MockTextEmbedder(fixed_dim=128)

manager = MemoryManager()

# 创建一个 VDB 类型的 collection
col = manager.create_collection(
    name="vdb_test",
    backend_type="VDB",
    embedding_model=default_model,
    dim=128,
    description="test vdb collection"
)
print("创建完成：", manager.list_collection("vdb_test"))

# 重命名 collection
manager.rename("vdb_test", "vdb_renamed", "renamed description")
print("重命名后：", manager.list_collection("vdb_renamed"))

# 连接已存在 collection
connected_col = manager.connect_collection("vdb_renamed")
print("连接成功：", connected_col)

# 列出所有 collections
print("所有集合：", manager.list_collection())

# 删除 collection
manager.delete_collection("vdb_renamed")
print("删除成功。剩余集合：", manager.list_collection())
# file: sage/core/neuromem/test_memory_manager.py
"""
Quick-n-dirty smoke-test for your MemoryManager.

运行：
    python -m sage.core.neuromem.test_memory_manager
"""

import os, shutil, tempfile
from pathlib import Path

from sage.core.neuromem.memory_manager import MemoryManager
from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder
from sage.core.neuromem.memory_collection.vdb_collection import VDBMemoryCollection

# ────────────────────────────────────────────────────────────
# 0. 乾坤大挪移：把默认 ./memory_storage 清空，以免旧数据干扰
# ────────────────────────────────────────────────────────────
root = Path("./memory_storage")
if root.exists():
    shutil.rmtree(root)
root.mkdir(parents=True, exist_ok=True)

print("storage root =", root.resolve())

# ────────────────────────────────────────────────────────────
# 1. 启动 Manager（此时磁盘为空）
# ────────────────────────────────────────────────────────────
mgr = MemoryManager()
print("manager boot, collections on disk:", mgr.list_collection())

# ────────────────────────────────────────────────────────────
# 2. 创建一个 VDB collection，并写两条数据
# ────────────────────────────────────────────────────────────
embedder = MockTextEmbedder(fixed_dim=128)
coll = mgr.create_collection(
    name="demo_vdb",
    backend_type="VDB",
    embedding_model=embedder,
    dim=128,
    description="vector test",
)
coll.add_metadata_field("lang")
coll.insert("hello vector", {"lang": "en"})
coll.insert("你好，向量",    {"lang": "zh"})
coll.flush()                                # 写 manifest + index（此处仅 manifest）

print(" after insert, mgr.list_collection():")
for info in mgr.list_collection():
    print("  ", info)

# ────────────────────────────────────────────────────────────
# 3. 卸载再加载，验证数据仍可取
# ────────────────────────────────────────────────────────────
mgr.release_collection("demo_vdb")
print("released. currently-loaded =", list(mgr.collections.keys()))

coll2 = mgr.load_collection("demo_vdb")
coll2.create_index("default")  # 重新创建索引对象
# 以 “hello” 作为查询，使用默认索引 “default”
print("reloaded texts:", coll2.retrieve("hello", index_name="default", with_metadata=True))

# ────────────────────────────────────────────────────────────
# 4. 重命名
# ────────────────────────────────────────────────────────────
mgr.rename("demo_vdb", "renamed_vdb", new_description="after rename")
print("after rename ->", mgr.list_collection("renamed_vdb") )

# ────────────────────────────────────────────────────────────
# 5. 删除
# ────────────────────────────────────────────────────────────
mgr.delete_collection("renamed_vdb")
print("deleted. collections on disk now:", mgr.list_collection())

# ────────────────────────────────────────────────────────────
# 6.（可选）KV 测试一次
# ────────────────────────────────────────────────────────────
kv = mgr.create_collection("demo_kv", "KV", description="kv test")
kv.add_metadata_field("tag")
kv.insert("plain text 1", {"tag": "t1"})
print("KV retrieve:", kv.retrieve(with_metadata=True))

# ────────────────────────────────────────────────────────────
# 7. 结束前强制 save_all（索引/manifest）
# ────────────────────────────────────────────────────────────
mgr.save_all()
print("save_all done.")

# ────────────────────────────────────────────────────────────
# 清理示例目录（如果你想保留结果可注释掉）
# ────────────────────────────────────────────────────────────
tmp_keep = False          # 设 True 可手动检查生成的文件
if not tmp_keep:
    shutil.rmtree(root)
    print("cleaned storage dir.")

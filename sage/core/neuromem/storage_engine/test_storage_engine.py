# test_locked_storage.py
# file sage/core/neuromem/storage_engine/test_storage_engine.py
# python sage/core/neuromem/storage_engine/test_storage_engine.py

from pathlib import Path
import tempfile
import shutil
import numpy as np
from sage.core.neuromem.storage_engine.storage_engine_locked import (
    TextStorageLocked,
    MetadataStorageLocked,
    VectorStorageLocked,
)
# 创建一个临时目录
tmp = Path(tempfile.mkdtemp())

# ---------- TextStorage 测试 ----------
text_file = tmp / "text.jsonl"
text_store = TextStorageLocked(text_file)
text_store.append("id1", "hello")
text_store.append("id2", "world")
text_store.clear_cache()
text_store.load()
print("text:", text_store.get("id1"), text_store.get("id2"))

# ---------- MetadataStorage 测试 ----------
meta_file = tmp / "meta.jsonl"
meta_store = MetadataStorageLocked(meta_file)
meta_store.add_field("age")
meta_store.append("id1", {"age": 18})
meta_store.append("id2", {"age": 25})
meta_store.clear_cache()
meta_store.add_field("age")
meta_store.load()
print("meta:", meta_store.get("id1"), meta_store.get("id2"))

# ---------- VectorStorage 测试 ----------
vec_file = tmp / "vec.npy"
vec_id_file = tmp / "vec_ids.jsonl"
vec_store = VectorStorageLocked(vec_file, vec_id_file, dim=3)
vec_store.append("id1", np.array([1.0, 2.0, 3.0]))
vec_store.append("id2", np.array([4.0, 5.0, 6.0]))
vec_store.clear_cache()
vec_store.load()
print("vec:", vec_store.get("id1"), vec_store.get("id2"))

# 清理
shutil.rmtree(tmp)

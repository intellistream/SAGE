# file sage/sage_tests/neuromem_test/core_test/collection_test/vdb_collection_test.py

import os
import time
import pytest
from memory.memory_collection.base_collection import get_default_data_dir
from utils.embedding_methods.mockembedder import MockTextEmbedder
from memory.memory_collection.vdb_collection import VDBMemoryCollection


def almost_equal_dict(d1, d2, float_tol=1e-3):
    # 只对所有值都是float的dict做容忍，否则严格等价
    if d1.keys() != d2.keys():
        return False
    for k in d1:
        v1, v2 = d1[k], d2[k]
        if isinstance(v1, float) and isinstance(v2, float):
            if abs(v1 - v2) > float_tol:
                return False
        else:
            if v1 != v2:
                return False
    return True

@pytest.fixture
def setup_vdb_collection():
    default_model = MockTextEmbedder(fixed_dim=16)
    col = VDBMemoryCollection("vdb_demo", default_model, 16)
    col.add_metadata_field("source")
    col.add_metadata_field("lang")
    col.add_metadata_field("timestamp")

    current_time = time.time()
    texts = [
        ("hello world", {"source": "user", "lang": "en", "timestamp": current_time - 3600}),
        ("你好，世界", {"source": "user", "lang": "zh", "timestamp": current_time - 1800}),
        ("bonjour le monde", {"source": "web", "lang": "fr", "timestamp": current_time}),
    ]
    for t, meta in texts:
        col.insert(t, meta)

    col.create_index("global_index")
    col.create_index("en_index", metadata_filter_func=lambda m: m.get("lang") == "en", description="English only")
    col.create_index("user_index", metadata_filter_func=lambda m: m.get("source") == "user")
    return col, current_time

def test_vdb_persist(setup_vdb_collection):
    col, current_time = setup_vdb_collection

    # 检索校验
    res = col.retrieve("hello", topk=3, index_name="global_index")
    assert set(res) & {"hello world"} == {"hello world"}

    res = col.retrieve("hello", index_name="en_index")
    assert set(res) & {"hello world"} == {"hello world"}

    res = col.retrieve("你好", index_name="user_index")
    assert set(res) & {"你好，世界"} == {"你好，世界"}

    # 持久化保存
    store_path = get_default_data_dir()
    col_name = "vdb_demo"
    col.store(store_path)

    # 清除内存对象
    del col

    # 恢复对象并回归测试
    default_model2 = MockTextEmbedder(fixed_dim=16)
    col2 = VDBMemoryCollection.load(col_name, embedding_model=default_model2)

    # 再检索
    res = col2.retrieve("hello", index_name="global_index")
    assert set(res) & {"hello world"} == {"hello world"}

    res = col2.retrieve("你好", index_name="user_index")
    assert set(res) & {"你好，世界"} == {"你好，世界"}

    # 校验metadata一致性
    meta = col2.metadata_storage.get(col2._get_stable_id("hello world"))
    assert almost_equal_dict(meta, {"source": "user", "lang": "en", "timestamp": current_time - 3600})

    # 校验索引条件
    idx_meta = col2.indexes["en_index"]
    assert idx_meta.get("description", "") == "English only"

    # 删除磁盘数据
    VDBMemoryCollection.clear(col_name)
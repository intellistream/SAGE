# file sage/tests/neuromem_test/core_test/collection_test/kv_collection_test.py
# python -m sage.tests.neuromem_test.core_test.collection_test.kv_collection_test

import os
import pytest
from sage.core.neuromem.memory_collection.kv_collection import KVMemoryCollection
from sage.core.neuromem.memory_collection.base_collection import get_default_data_dir

def test_kv_collection():
    # ==== 基础数据构建 ====
    col = KVMemoryCollection(name="demo")

    col.add_metadata_field("field1")
    col.add_metadata_field("field2")
    col.add_metadata_field("field3")

    # 多样化插入
    col.insert("Hello Jack.", {"field1": "1", "field2": "0", "field3": "3"})
    col.insert("Hello Tom.", {"field1": "1", "field2": "1", "field3": "3"})
    col.insert("Hello Alice.", {"field1": "0", "field2": "1", "field3": "3"})
    col.insert("Jack and Tom say hi.", {"field1": "1", "field2": "0", "field3": "8"})
    col.insert("Alice in Wonderland.", {"field1": "0", "field2": "1", "field3": "5"})
    col.insert("Jacky is not Jack.", {"field1": "2", "field2": "9", "field3": "8"})

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
    res1 = col.retrieve("Jack", topk=3, index_name="global_index")
    assert set(res1) == {"Hello Jack.", "Jack and Tom say hi.", "Jacky is not Jack."}

    res2 = col.retrieve("Alice", topk=2, index_name="global_index", metadata_filter_func=lambda m: m.get("field2") == "1")
    assert set(res2) == {"Hello Alice.", "Alice in Wonderland."}

    res3 = col.retrieve("Tom", topk=2, index_name="f2_1_index")
    assert set(res3) == {"Hello Tom.", "Hello Alice."}

    res4 = col.retrieve("Jack", index_name="f1_1_index")
    assert set(res4) == {"Hello Jack.", "Hello Tom.", "Jack and Tom say hi."}

    res5 = col.retrieve("Jack", index_name="field3_8_index")
    assert set(res5) == {"Jack and Tom say hi.", "Jacky is not Jack."}

    # 删除一条不会导致全部为空
    col.delete("Hello Tom.")
    res6 = col.retrieve("Tom", index_name="global_index")
    assert "Hello Tom." not in res6

    # 更新 Jacky
    col.update("Hello Jack.", "Hello Jacky.", {"field1": "2", "field2": "9", "field3": "8"}, "global_index", "f2_1_index", "f1_1_index", "field3_8_index")
    res7 = col.retrieve("Jacky", index_name="global_index")
    assert set(res7) == set(['Jacky is not Jack.', 'Hello Jacky.', 'Hello Alice.', 'Jack and Tom say hi.', 'Alice in Wonderland.'])

    meta = col.metadata_storage.get(col._get_stable_id("Hello Jacky."))
    assert meta == {"field1": "2", "field2": "9", "field3": "8"}

    # 删除全部不会报错
    try:
        col.delete("NonExistentText")
    except Exception as e:
        assert False, f"非法删除异常: {e}"
        
    # 非法索引：断言 warning 被正确发出
    with pytest.warns(UserWarning, match="Index 'non_exist_index' does not exist."):
        col.retrieve("anything", index_name="non_exist_index")

    # 删除索引
    col.delete_index("f2_1_index")
    assert "f2_1_index" not in col.indexes

    rebuild_res = col.rebuild_index("global_index")
    assert rebuild_res is True

    # ==== 持久化保存、恢复测试 ====
    store_path = get_default_data_dir()
    col_name = "demo"
    col.store(store_path)

    del col

    # 直接恢复
    col2 = KVMemoryCollection.load(col_name)

    res = col2.retrieve("Jacky", index_name="global_index")
    assert set(res) == set(['Jacky is not Jack.', 'Hello Jacky.', 'Hello Alice.', 'Jack and Tom say hi.', 'Alice in Wonderland.'])
    meta = col2.metadata_storage.get(col2._get_stable_id("Hello Jacky."))
    assert meta == {"field1": "2", "field2": "9", "field3": "8"}

    idx_meta = col2.indexes["f1_1_index"]
    assert idx_meta.get("metadata_conditions", {}) == {"field1": "1"}
    assert idx_meta.get("metadata_filter_func") is not None
    resx2 = col2.retrieve("Jack", index_name="f1_1_index")
    assert set(resx2) & {"Jack and Tom say hi."} == {"Jack and Tom say hi."}

    # 清理数据
    KVMemoryCollection.clear(col_name)

# file sage/tests/neuromem_test/core_test/collection_test/kv_collection_test.py
# python -m sage.tests.neuromem_test.core_test.collection_test.kv_collection_test

if __name__ == "__main__":
    import os
    from sage.core.neuromem.memory_collection.kv_collection import KVMemoryCollection
    from sage.core.neuromem.memory_collection.base_collection import get_default_data_dir

    def print_test_case(desc, expected, actual):
        status = "通过" if expected == actual or (isinstance(expected, set) and set(expected) == set(actual)) else "不通过"
        print(f"【{desc}】")
        print(f"预期结果：{expected}")
        print(f"实际结果：{actual}")
        print(f"测试情况：{status}\n")

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
    print("数据已保存到磁盘！")
    print("目录为：", os.path.join(store_path, "kv_collection", col_name))

    del col
    print("内存对象已清除。")

    # 直接恢复
    col2 = KVMemoryCollection.load(col_name)
    print("数据已从磁盘恢复！")

    res = col2.retrieve("Jacky", index_name="global_index")
    print_test_case("持久化后检索", ['Jacky is not Jack.', 'Hello Jacky.', 'Hello Alice.', 'Jack and Tom say hi.', 'Alice in Wonderland.'], res)
    meta = col2.metadata_storage.get(col2._get_stable_id("Hello Jacky."))
    print_test_case("持久化后元数据", {"field1": "2", "field2": "9", "field3": "8"}, meta)

    idx_meta = col2.indexes["f1_1_index"]
    print_test_case("f1_1_index恢复metadata_conditions", {"field1": "1"}, idx_meta.get("metadata_conditions", {}))
    print_test_case("f1_1_index恢复filter_func存在", True, idx_meta.get("metadata_filter_func") is not None)
    resx2 = col2.retrieve("Jack", index_name="f1_1_index")
    print_test_case("持久化后f1_1_index检索", {"Jack and Tom say hi."}, set(resx2) & {"Jack and Tom say hi."})

    # 清理数据
    KVMemoryCollection.clear(col_name)
    print("所有数据已删除！")

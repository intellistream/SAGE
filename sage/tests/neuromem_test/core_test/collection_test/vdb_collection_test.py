# file sage/tests/neuromem_test/core_test/collection_test/vdb_collection_test.py
# python -m sage.tests.neuromem_test.core_test.collection_test.vdb_collection_test


if __name__ == "__main__":
    import os
    import time
    from sage.core.neuromem.memory_collection.base_collection import get_default_data_dir
    from sage.core.model.embedding_model.embedding_model import MockTextEmbedder
    from sage.core.neuromem.memory_collection.vdb_collection import VDBMemoryCollection

    def print_test_case(desc, expected, actual):
        status = "通过" if expected == actual or (isinstance(expected, set) and set(expected) == set(actual)) else "不通过"
        print(f"【{desc}】")
        print(f"预期结果：{expected}")
        print(f"实际结果：{actual}")
        print(f"测试情况：{status}\n")

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

    def vdb_persist_test():
        print("\n=== 构建并插入数据 ===")
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

        # 创建索引
        col.create_index("global_index")
        col.create_index("en_index", metadata_filter_func=lambda m: m.get("lang") == "en", description="English only")
        col.create_index("user_index", metadata_filter_func=lambda m: m.get("source") == "user")
        print("索引已创建。")

        # 检索校验
        res = col.retrieve("hello", topk=3, index_name="global_index")
        print_test_case("检索hello", {"hello world"}, set(res) & {"hello world"})

        res = col.retrieve("hello", index_name="en_index")
        print_test_case("en_index检索hello", {"hello world"}, set(res) & {"hello world"})

        res = col.retrieve("你好", index_name="user_index")
        print_test_case("user_index检索你好", {"你好，世界"}, set(res) & {"你好，世界"})

        # --- 持久化保存 ---
        print("\n--- 持久化测试开始 ---")
        store_path = get_default_data_dir()
        col_name = "vdb_demo"
        col.store(store_path)
        print("数据已保存到磁盘！")
        print("目录为：", os.path.join(store_path, "vdb_collection", col_name))
        print("目录下文件有：", os.listdir(os.path.join(store_path, "vdb_collection", col_name)))

        # 清除内存对象
        del col
        print("内存对象已清除。")

        # 恢复对象并回归测试
        default_model2 = MockTextEmbedder(fixed_dim=16)
        col2 = VDBMemoryCollection.load(col_name, embedding_model=default_model2)
        print("数据已从磁盘恢复！")

        # 再检索
        res = col2.retrieve("hello", index_name="global_index")
        print_test_case("恢复后检索hello", {"hello world"}, set(res) & {"hello world"})

        res = col2.retrieve("你好", index_name="user_index")
        print_test_case("恢复后user_index检索你好", {"你好，世界"}, set(res) & {"你好，世界"})

        # 校验metadata一致性
        meta = col2.metadata_storage.get(col2._get_stable_id("hello world"))
        print_test_case("恢复后元数据",
                        True,
                        almost_equal_dict(meta, {"source": "user", "lang": "en", "timestamp": current_time - 3600}))

        # 校验索引条件
        idx_meta = col2.indexes["en_index"]
        print_test_case("en_index恢复description", "English only", idx_meta.get("description", ""))

        # 删除磁盘数据
        VDBMemoryCollection.clear(col_name)
        print("所有数据已删除！")

    vdb_persist_test()


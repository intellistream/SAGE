# file sage/sage_tests/neuromem_test/core_test/manager_test.py
# python -m sage.sage_tests.neuromem_test.core_test.manager_test

from time import sleep


def test_vdb(do_reload=True, do_delete=True):
    from sage.middleware.services.neuromem.memory_manager import MemoryManager
    from sage.utils.embedding_methods.mockembedder import MockTextEmbedder
    import os

    def colored(text, color):
        colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "reset": "\033[0m"}
        return colors.get(color, "") + text + colors["reset"]
        # return text  # 自动化测试不需要彩色输出

    def print_test_case(desc, expected, actual):
        status = "通过" if expected == actual or (isinstance(expected, set) and set(expected) == set(actual)) else "不通过"
        print(f"【{desc}】")
        print(f"预期结果：{expected}")
        print(f"实际结果：{actual}")
        print(f"测试情况：{status}\n")

    # 1. 创建 MemoryManager 和 VDBCollection
    mgr = MemoryManager()
    embedder = MockTextEmbedder(fixed_dim=16)
    col = mgr.create_collection(name="test_vdb", backend_type="VDB", description="测试VDB集合", embedding_model=embedder, dim=16)
    col.add_metadata_field("tag")  # 注册元数据字段tag

    # 2. 插入数据
    col.insert("Alpha", {"tag": "A"})
    col.insert("Beta", {"tag": "B"})
    col.insert("Gamma", {"tag": "A"})

    # 3. 创建索引
    col.create_index("global_index")
    col.create_index("tag_A_index", metadata_filter_func=lambda m: m.get("tag") == "A")

    # 4. 检索测试
    res1 = col.retrieve("Alpha", topk=1, index_name="global_index")
    print_test_case("检索Alpha", ["Alpha"], res1)

    res2 = set(col.retrieve("Alpha", topk=5, index_name="tag_A_index"))  # Alpha 的向量检索，tag为A
    print_test_case("tag_A_index 检索", {'Gamma', 'Alpha', 'Beta'}, res2)

    # 5. 持久化
    mgr.store_collection()
    print("数据已保存到磁盘！")
    data_dir = mgr.data_dir
    print("目录为：", os.path.join(data_dir, "vdb_collection", "test_vdb"))

    # 6. 清空对象
    del mgr, col
    print("内存对象已清除。")

    # 7. 读取持久化数据，自动测试时直接执行
    if do_reload:
        from sage.middleware.services.neuromem.memory_manager import MemoryManager
        embedder2 = MockTextEmbedder(fixed_dim=16)
        mgr2 = MemoryManager()
        col2 = mgr2.connect_collection("test_vdb", embedding_model=embedder2)
        res3 = set(col2.retrieve("Alpha", topk=5, index_name="tag_A_index"))
        print_test_case("恢复后tag_A_index 检索", {'Gamma', 'Alpha', 'Beta'}, res3)
    else:
        print("跳过加载测试。")

    sleep(10)  # 等待一会儿，确保所有操作完成
    # 8. 删除所有数据
    if do_delete:
        from sage.middleware.services.neuromem.memory_collection.vdb_collection import VDBMemoryCollection
        VDBMemoryCollection.clear("test_vdb", data_dir)
        manager_json = os.path.join(data_dir, "manager.json")
        if os.path.exists(manager_json):
            os.remove(manager_json)
        print("所有数据已删除！")
    else:
        print("未执行删除。")

# 作为测试脚本被自动调用
if __name__ == "__main__":
    test_vdb()


# def kvtest():
#     from sage.core.sage.middleware.services.neuromem..memory_manager import MemoryManager
#     import os

#     def colored(text, color):
#         colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "reset": "\033[0m"}
#         return colors.get(color, "") + text + colors["reset"]

#     def print_test_case(desc, expected, actual):
#         status = "通过" if expected == actual or (isinstance(expected, set) and set(expected) == set(actual)) else "不通过"
#         color = "green" if status == "通过" else "red"
#         print(f"【{desc}】")
#         print(f"预期结果：{expected}")
#         print(f"实际结果：{actual}")
#         print(f"测试情况：{colored(status, color)}\n")

#     # 1. 创建 MemoryManager 和 KVCollection
#     mgr = MemoryManager()
#     col = mgr.create_collection(name="test_kv", backend_type="KV", description="测试KV集合")
#     col.add_metadata_field("tag")  # 注册元数据字段tag

#     # 2. 插入数据
#     col.insert("Alpha", {"tag": "A"})
#     col.insert("Beta", {"tag": "B"})
#     col.insert("Gamma", {"tag": "A"})

#     # 3. 创建索引
#     col.create_index("global_index")
#     col.create_index("tag_A_index", metadata_filter_func=lambda m: m.get("tag") == "A")

#     # 4. 检索测试
#     res1 = col.retrieve("Alpha", topk=1, index_name="global_index")
#     print_test_case("检索Alpha", ["Alpha"], res1)

#     res2 = set(col.retrieve("a", topk=5, index_name="tag_A_index"))  # 检索包含'a'的文本，tag为A
#     print_test_case("tag_A_index 检索", {"Alpha", "Gamma"}, res2)

#     # 5. 持久化
#     mgr.store_collection()
#     print(colored("数据已保存到磁盘！", "yellow"))
#     data_dir = mgr.data_dir
#     print("目录为：", os.path.join(data_dir, "kv_collection", "test_kv"))

#     # 6. 清空对象
#     del mgr, col
#     print(colored("内存对象已清除。", "yellow"))

#     # 7. 读取持久化数据
#     user_input = input(colored("输入 yes 加载刚才保存的数据: ", "yellow"))
#     if user_input.strip().lower() == "yes":
#         mgr2 = MemoryManager()  # 会自动加载 manager.json 和 collection
#         col2 = mgr2.get_collection("test_kv")
#         # 检查是否正常恢复
#         res3 = set(col2.retrieve("a", topk=5, index_name="tag_A_index"))
#         print_test_case("恢复后tag_A_index 检索", {"Alpha", "Gamma"}, res3)
#     else:
#         print(colored("跳过加载测试。", "yellow"))

#     # 8. 删除所有数据
#     user_input = input(colored("输入 yes 删除磁盘所有数据: ", "yellow"))
#     if user_input.strip().lower() == "yes":
#         from sage.core.sage.middleware.services.neuromem.memory_collection.kv_collection import KVMemoryCollection
#         KVMemoryCollection.clear("test_kv", data_dir)
#         manager_json = os.path.join(data_dir, "manager.json")
#         if os.path.exists(manager_json):
#             os.remove(manager_json)
#         print(colored("所有数据已删除！", "green"))
#     else:
#         print(colored("未执行删除。", "yellow"))

# kvtest()
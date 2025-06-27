# file sage/core/neuromem/operator_test/vdbcollection_test.py
# python -m sage.core.neuromem.operator_test.vdbcollection_test

import time
from datetime import datetime
from sage.core.neuromem.test.embeddingmodel import MockTextEmbedder
from sage.core.neuromem.memory_collection.base_collection import VDBMemoryCollection


# Initialize VDBMemoryCollection
default_model = MockTextEmbedder(fixed_dim=128)
col = VDBMemoryCollection("vdb_demo", default_model, 128)
col_copy = VDBMemoryCollection("vdb_demo", default_model, 128)
col.add_metadata_field("source")
col.add_metadata_field("lang")
col.add_metadata_field("timestamp")
col.add_metadata_field("topic")
col.add_metadata_field("type")


# Insert operator_test data
current_time = time.time()
texts = [
        ("hello world", {"source": "user", "lang": "en", "timestamp": current_time - 3600}),
        ("你好，世界", {"source": "user", "lang": "zh", "timestamp": current_time - 1800}),
        ("bonjour le monde", {"source": "web", "lang": "fr", "timestamp": current_time}),
]
inserted_ids = [col.insert(text, metadata) for text, metadata in texts]

# Test 1: Create index by language
print("=== 测试1：按语言创建索引 (English and French only) ===")
col.create_index(
        index_name="en_fr_index",
        metadata_filter_func=lambda m: m.get("lang") in {"en", "fr"}
)
results = col.retrieve(
        "operator_test query", topk=10, index_name="en_fr_index",
        metadata_filter_func=lambda m: m.get("lang") in {"en", "fr"}
)
expected_texts = ["hello world", "bonjour le monde"]
print("Expected Texts:", expected_texts)
print("Actual Texts:", results)
print("Test 1 Pass:", set(results) == set(expected_texts))

# Test 2: Create index by timestamp
print("\n=== 测试2：按时间范围创建索引 (Last 45 minutes) ===")
time_threshold = current_time - 2700
col.create_index(
        index_name="recent_index",
        metadata_filter_func=lambda m: m.get("timestamp", 0) > time_threshold
)
results = col.retrieve(
        "operator_test query", topk=10, index_name="recent_index",
        metadata_filter_func=lambda m: m.get("timestamp", 0) > time_threshold
)
expected_texts = ["你好，世界", "bonjour le monde"]
print("Expected Texts:", expected_texts)
print("Actual Texts:", results)
print("Test 2 Pass:", set(results) == set(expected_texts))

# Test 3: Vector search using en_fr_index
print("\n=== 测试3：向量搜索 (Vector Search using retrieve) ===")
query_text = "hello"
results = col.retrieve(query_text, topk=2, index_name="en_fr_index")
expected_top_text = ["hello world"]
for text in results:
        item_id = col._get_stable_id(text)
        metadata = col.metadata_storage.get(item_id)
        timestamp = datetime.fromtimestamp(metadata['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{text} (lang: {metadata['lang']}, timestamp: {timestamp})")
print("Expected Top Text:", expected_top_text)
print("Actual Texts:", results)
print("Test 3 Pass:", results[0] in expected_top_text if results else False)

# Test 4: Combined metadata + vector search (user only)
print("\n=== 测试4：元数据过滤与向量搜索结合 (User source + Vector Search) ===")
results = col.retrieve(
        query_text, topk=1, index_name="en_fr_index",
        metadata_filter_func=lambda m: m.get("source") == "user"
)
expected_top_text = ["hello world"]
for text in results:
        item_id = col._get_stable_id(text)
        metadata = col.metadata_storage.get(item_id)
        timestamp = datetime.fromtimestamp(metadata['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{text} (lang: {metadata['lang']}, timestamp: {timestamp})")
print("Expected Top Text:", expected_top_text)
print("Actual Texts:", results)
print("Test 4 Pass:", results[0] in expected_top_text if results else False)

# Test 5: Recent + Vector Search
print("\n=== 测试5：时间范围过滤与向量搜索 (Last 45 minutes + Vector Search) ===")
results = col.retrieve(
        query_text, topk=2, index_name="recent_index",
        metadata_filter_func=lambda m: m.get("timestamp", 0) > time_threshold
)
expected_top_text = ["你好，世界", "bonjour le monde"]
for text in results:
        item_id = col._get_stable_id(text)
        metadata = col.metadata_storage.get(item_id)
        timestamp = datetime.fromtimestamp(metadata['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{text} (lang: {metadata['lang']}, timestamp: {timestamp})")
print("Expected Top Text:", expected_top_text)
print("Actual Texts:", results)
print("Test 5 Pass:", results[0] in expected_top_text if results else False)

# Test 6: Delete index and ensure it's gone
print("\n=== 测试6：删除索引 (Delete Index Test) ===")
col.delete_index("en_fr_index")
try:
        col.retrieve("hello", index_name="en_fr_index")
        print("Test 6 Fail: Retrieval should have raised an error.")
except ValueError as e:
        print("Caught expected error:", str(e))
        print("Test 6 Pass: Index deletion effective.")

print("\n=== 测试7：重建索引 (Rebuild Index Test) ===")

# 先打印重建前索引中向量数量（假设FaissBackend有ntotal属性）
index_obj = col.indexes["recent_index"]["index"]
old_size = getattr(index_obj, "ntotal", None)
print(f"Index size before rebuild: {old_size}")

# 重建索引
col.rebuild_index("recent_index")

index_obj = col.indexes["recent_index"]["index"]
new_size = getattr(index_obj, "ntotal", None)
print(f"Index size after rebuild: {new_size}")

print("Test 7 Pass:", new_size is not None and new_size > 0)

# 测试重建后是否能正常检索
results = col.retrieve("hello", index_name="recent_index")
print("Results after rebuild:", results)


print("\n=== 测试8：列出索引信息 (List Index Info) ===")

# 创建一个示例索引，带描述
def lang_filter(meta):
        return meta.get("lang") in ("en", "fr")

col.create_index(
        "lang_index",
        metadata_filter_func=lang_filter,
        description="English and French only"
)

# 列出所有索引及其描述
index_info = col.list_index()
for info in index_info:
        print(f"Index Name: {info['name']}, Description: {info['description']}")

expected_names = {"recent_index", "lang_index"}
actual_names = {info["name"] for info in index_info}
print("Test 8 Pass:", expected_names.issubset(actual_names))

print("\n=== 测试9：插入文本时直接加入索引 ===")

col.create_index(
        index_name="user_index",
        metadata_filter_func=lambda m: m.get("source") == "user"
)

# 插入数据并指定立即加入索引
col.insert("hi there", {"source": "user", "lang": "en"}, "user_index")

results = col.retrieve("hi", index_name="user_index")
print("Expected: ['hi there']")
print("Actual:", results)
print("Test 9 Pass:", "hi there" in results)

print("\n=== 测试10：更新文本，删除旧的并加入新索引 ===")

# 更新“hello world”为新文本，并加进 recent_index
col.update("hello world", "hello new world", {"source": "user", "lang": "en", "timestamp": current_time}, "recent_index")

# 检查旧的是否被删除，新内容是否存在
results = col.retrieve("hello", index_name="recent_index")
print("Expected: ['hello new world']")
print("Actual:", results)
print("Test 10 Pass:", "hello new world" in results and "hello world" not in results)

print("\n=== 测试11：删除文本后检索失败 ===")

# 删除刚插入的“hi there”
col.delete("hi there")

# 重新检索看看还在不在
results = col.retrieve("hi", index_name="user_index")
print("Expected: []")
print("Actual:", results)
print("Test 11 Pass:", "hi there" not in results)

print("\n=== 测试12：向量检索不足触发索引重建 ===")

# 假设我们手动删除 recent_index 中某条向量
some_id = col._get_stable_id("bonjour le monde")
col.indexes["recent_index"]["index"].delete(some_id)

# 再次查询，索引应重建
results = col.retrieve("bonjour", topk=2, index_name="recent_index")
print("Results:", results)
print("Test 12 Pass:", "bonjour le monde" in results)

print("\n=== 测试13：插入时指定不存在的索引名 ===")

try:
        col.insert("invalid index operator_test", {"source": "user"}, "non_existing_index")
        print("Test 13 Fail: Expected error for non-existent index.")
except ValueError as e:
        print("Caught expected error:", str(e))
        print("Test 13 Pass: Error raised as expected.")
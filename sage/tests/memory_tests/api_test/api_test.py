import pytest

from memory.api import get_memory  # 如果单独存，可以直接import

# def test_create_memory_basic():
#     config = {}
#     col = get_memory(config)

#     assert col.name == "vdb_test"
#     assert col.dim == 128

#     # 检查插入的元数据能否被正确检索
#     result = col.retrieve("hello world", topk=1, index_name="vdb_index", with_metadata=True)
#     assert isinstance(result, list)
#     assert len(result) == 1
#     metadata = result[0]["metadata"]
#     assert metadata.get("owner") == "ruicheng"
#     assert metadata.get("show_type") == "text"



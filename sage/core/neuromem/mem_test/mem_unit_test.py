# test_memory_api.py
# export HF_ENDPOINT=https://hf-mirror.com
# export PYTHONPATH=/home/zrc/develop_item/sage/SAGE:$PYTHONPATH
# pytest sage/core/neuromem/mem_test/mem_unit_test.py
import pytest
import torch
from sage.api.memory.memory_api import (
    create_table,
    connect,
    init_default_manager,
    get_default_manager,
)

@pytest.fixture(scope="module")
def memory_manager():
    init_default_manager()
    return get_default_manager()

@pytest.fixture
def short_term_memory(memory_manager):
    return create_table("short_term_memory", memory_manager)

@pytest.fixture
def long_term_memory(memory_manager):
    return create_table("long_term_memory", memory_manager)

@pytest.fixture
def dynamic_contextual_memory(memory_manager):
    return create_table("dynamic_contextual_memory", memory_manager)

def test_stm_retrieval(short_term_memory):
    short_term_memory.store("This is STM data")
    results = short_term_memory.retrieve()
    assert results == ["This is STM data"]

def test_ltm_retrieval(long_term_memory):
    long_term_memory.store("This is LTM data")
    results = long_term_memory.retrieve("This is LTM data")
    assert results == ["This is LTM data"]

def test_dcm_retrieval(dynamic_contextual_memory):
    dynamic_contextual_memory.store("This is DCM data")
    results = dynamic_contextual_memory.retrieve("This is DCM data")
    # 这里假设有三个返回值：原始+苹果+香蕉
    assert set(results) == {"This is DCM data", "苹果", "香蕉"}

def test_composite_retrieval(memory_manager, short_term_memory, long_term_memory):
    long_term_memory.store("This is LTM data")  # 添加这一行

    composite = connect(memory_manager, "short_term_memory", "long_term_memory")
    composite.store("This is Composite data.")
    results = composite.retrieve("This is composite data")

    assert "This is Composite data." in results
    assert "This is LTM data" in results


def test_custom_func_retrieval(memory_manager, short_term_memory, long_term_memory):
    composite = connect(memory_manager, "short_term_memory", "long_term_memory")

    def test_write_func(raw_data, embedding, memory):
        embedding = torch.full((128,), 0.5)
        memory.store(raw_data, embedding)

    def test_retrieve_func(embedding, memory):
        embedding = torch.full((128,), 0.5)
        return memory.retrieve(embedding, k=1)

    composite.store("This is a Storage & Retrieval Test.", write_func=test_write_func)
    results = composite.retrieve("This is a Storage & Retrieval Test.", retrieve_func=test_retrieve_func)
    assert results == ["This is a Storage & Retrieval Test."]

def test_composite_flush(memory_manager, short_term_memory, long_term_memory):
    composite = connect(memory_manager, "short_term_memory", "long_term_memory")
    composite.store("test flush data 1")
    composite.store("test flush data 2")
    composite.flush_kv_to_vdb(short_term_memory, long_term_memory)

    assert len(short_term_memory.retrieve("test")) == 0
    assert len(long_term_memory.retrieve("")) >= 2  # 至少刚刚flush的两条

def test_manager_list_and_clean(memory_manager, long_term_memory, dynamic_contextual_memory):
    collections = memory_manager.list_collections()
    collection_names = [c.name for c in collections]
    assert "long_term_memory" in collection_names

    # 清空并确认
    long_term_memory.clean()
    dynamic_contextual_memory.clean()

    # 写入可控测试数据
    long_term_memory.store("LTM test")
    dynamic_contextual_memory.store("DCM test")

    assert long_term_memory.retrieve("LTM") == ["LTM test"]
    assert dynamic_contextual_memory.retrieve("DCM") == ["DCM test", "苹果", "香蕉"]


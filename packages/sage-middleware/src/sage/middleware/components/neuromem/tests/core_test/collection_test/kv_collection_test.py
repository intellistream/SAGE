import pytest
from sage.middleware.components.neuromem.memory_collection.kv_collection import KVMemoryCollection
from sage.middleware.components.neuromem.memory_collection.base_collection import get_default_data_dir

@pytest.fixture
def setup_kv_collection():
    col = KVMemoryCollection(name="demo")

    col.insert("Hello Jack.", {})
    col.insert("Hello Tom.", {})
    col.insert("Hello Alice.", {})
    col.insert("Jack and Tom say hi.", {})
    col.insert("Alice in Wonderland.", {})
    col.insert("Jacky is not Jack.", {})

    col.create_index("global_index")
    return col


def test_kv_retrieve(setup_kv_collection):
    col = setup_kv_collection

    res1 = col.retrieve("Jack", topk=3, index_name="global_index")
    assert set(res1) == {"Hello Jack.", "Jack and Tom say hi.", "Jacky is not Jack."}

    res2 = col.retrieve("Alice", topk=2, index_name="global_index")
    assert set(res2) == {"Hello Alice.", "Alice in Wonderland."}

    res3 = col.retrieve("Tom", topk=2, index_name="global_index")
    assert set(res3) == {"Hello Tom.", "Jack and Tom say hi."}


def test_kv_update_and_delete(setup_kv_collection):
    col = setup_kv_collection

    col.delete("Hello Tom.")
    res4 = col.retrieve("Tom", index_name="global_index")
    assert "Hello Tom." not in res4

    col.update("Hello Jack.", "Hello Jacky.", {}, "global_index")
    res5 = col.retrieve("Jacky", index_name="global_index")

    assert {"Jacky is not Jack.", "Hello Jacky."}.issubset(set(res5))


def test_kv_persistence(setup_kv_collection):
    col = setup_kv_collection
    store_path = get_default_data_dir()
    col_name = "demo"
    col.store(store_path)

    del col

    col2 = KVMemoryCollection.load(col_name)
    res = col2.retrieve("Jacky", index_name="global_index")


    assert "Jacky is not Jack." in res

    KVMemoryCollection.clear(col_name)

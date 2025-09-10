import pytest
from sageflow import Environment, IndexFunction
from sageflow.utils import create_vector_message

def test_brute_force_knn():
    index = IndexFunction()
    index.add_vector([1.0, 2.0])
    results = index.search_kNN([1.0, 2.0], 1)
    assert len(results) == 1

def test_rag_index():
    env = Environment()
    ds = env.create_datastream().from_list([[1.0, 2.0], [3.0, 4.0]])
    index = IndexFunction()
    ds.map(lambda x: create_vector_message(1, x)).sink(index.add_vector).execute()
    search_results = index.search_kNN([1.0, 2.0], k=5)
    assert len(search_results) > 0

@pytest.mark.parametrize("vectors, query, k, expected_len", [
    ([[1.0, 2.0]], [1.0, 2.0], 1, 1),
    ([[1.0, 2.0], [3.0, 4.0]], [1.0, 2.0], 2, 2),
])
def test_index_search(vectors, query, k, expected_len):
    index = IndexFunction()
    for v in vectors:
        index.add_vector(v)
    results = index.search_kNN(query, k)
    assert len(results) == expected_len
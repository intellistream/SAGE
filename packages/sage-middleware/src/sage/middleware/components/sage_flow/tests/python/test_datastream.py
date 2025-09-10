import pytest
from typing import List, Any, Callable
from sageflow import Environment, DataStream
from sageflow.utils import create_text_message

@pytest.mark.parametrize("input_data, expected", [
    ([1, 2, 3], [2, 4, 6]),
    ([], []),
    ([5], [10]),
])
def test_fluent_api(input_data: List[Any], expected: List[Any]):
    env = Environment()
    ds = env.create_datastream().from_list(input_data)
    result = (ds
              .map(lambda x: x * 2)
              .filter(lambda x: x > 0)
              .sink(lambda x: None)
              .execute())
    assert result == expected

@pytest.mark.parametrize("data, map_func, filter_func, expected_len", [
    ([[1], [2], [3]], lambda x: x * 2, lambda x: x > 2, 2),
    ([[0], [0]], lambda x: x, lambda x: x > 0, 0),
])
def test_fluent_chain(data: List[Any], map_func: Callable, filter_func: Callable, expected_len: int):
    env = Environment()
    ds = env.create_datastream().from_list(data)
    result = (ds
              .map(map_func)
              .filter(filter_func)
              .collect())
    assert len(result) == expected_len

def test_datastream_with_messages():
    env = Environment()
    messages = [create_text_message(i, f"text_{i}") for i in range(3)]
    ds = env.create_datastream().from_list(messages)
    result = (ds
              .map(lambda msg: msg)
              .filter(lambda msg: True)
              .sink(print)
              .execute())
    assert len(result) == 3
import pytest
from typing import List, Any, Callable
import numpy as np
from sageflow import Stream

@pytest.fixture
def sample_data() -> List[int]:
    return [1, 2, 3, 4, 5]

@pytest.fixture
def sample_dict_data() -> List[dict]:
    return [{"id": 1, "value": 10}, {"id": 2, "value": 20}, {"id": 3, "value": 30}]

def test_from_list(sample_data):
    """测试 Stream.from_list"""
    stream = Stream.from_list(sample_data)
    result = stream.execute()
    assert result == sample_data
    assert len(result) == len(sample_data)

def test_map(sample_data):
    """测试 Stream.map 链式操作"""
    stream = Stream.from_list(sample_data).map(lambda x: x * 2)
    result = stream.execute()
    expected = [2, 4, 6, 8, 10]
    assert result == expected

def test_filter(sample_data):
    """测试 Stream.filter"""
    stream = Stream.from_list(sample_data).filter(lambda x: x > 3)
    result = stream.execute()
    expected = [4, 5]
    assert result == expected

def test_join(sample_dict_data):
    """测试 Stream.join"""
    left = Stream.from_list(sample_dict_data)
    right = Stream.from_list([{"id": 1, "bonus": 5}, {"id": 3, "bonus": 15}])
    joined = left.join(right, key_func=lambda item: item['id']).map(
        lambda pair: {**pair[0], 'total': pair[0]['value'] + pair[1].get('bonus', 0)} if pair[1] else pair[0]
    )
    result = joined.execute()
    expected = [
        {"id": 1, "value": 10, "total": 15},
        {"id": 2, "value": 20, "total": 20},
        {"id": 3, "value": 30, "total": 45}
    ]
    assert result == expected

def test_aggregate(sample_data):
    """测试 Stream.aggregate"""
    stream = Stream.from_list(sample_data).aggregate(lambda lst: sum(lst))
    result = stream.execute()
    expected = [15]  # sum of 1+2+3+4+5
    assert result == expected

def test_from_numpy():
    """测试 Stream.from_numpy"""
    arr = np.array([1, 2, 3])
    stream = Stream.from_numpy(arr)
    result = stream.execute()
    assert np.array_equal(result, arr)

def test_execute_chain(sample_data):
    """测试完整链式操作和execute"""
    stream = Stream.from_list(sample_data).map(lambda x: x * 2).filter(lambda x: x > 4).aggregate(lambda lst: sum(lst))
    result = stream.execute()
    expected = [20]  # sum of 6+8+10
    assert result == expected

def test_type_hints():
    """测试类型提示 (简单检查)"""
    # Stream 方法应返回 Stream 类型
    data = [1, 2, 3]
    stream: Stream = Stream.from_list(data)
    mapped: Stream = stream.map(lambda x: x)  # type: ignore
    filtered: Stream = mapped.filter(lambda x: True)  # type: ignore
    assert isinstance(stream, Stream)
    assert isinstance(mapped, Stream)
    assert isinstance(filtered, Stream)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
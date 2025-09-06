import pytest
from sageflow import Stream
import numpy as np

def test_end_to_end_pipeline():
    """测试完整管道执行验证"""
    # 准备数据
    data = [{"id": 1, "value": 10}, {"id": 2, "value": 20}, {"id": 3, "value": 30}]
    
    # 创建流
    stream = Stream.from_list(data)
    
    # 链式操作: filter, map, aggregate
    processed_stream = stream.filter(lambda item: item['value'] > 15) \
                             .map(lambda item: {**item, 'doubled': item['value'] * 2}) \
                             .aggregate(lambda lst: sum(item['doubled'] for item in lst))
    
    # 执行
    result = processed_stream.execute()
    
    # 验证
    expected = [100]  # 40 + 60
    assert result == expected

def test_end_to_end_with_numpy():
    """测试包含 NumPy 的端到端管道"""
    arr = np.array([[10, 20], [30, 40], [50, 60]])
    
    stream = Stream.from_numpy(arr)
    
    processed = stream.map(lambda row: np.sum(row)) \
                      .filter(lambda s: s > 50) \
                      .aggregate(lambda lst: sum(lst))
    
    result = processed.execute()
    
    expected = 110  # 50 + 60
    assert result == [expected]

def test_full_pipeline_with_join():
    """测试包含 join 的完整管道"""
    left_data = [{"id": 1, "value": 10}, {"id": 2, "value": 20}]
    right_data = [{"id": 1, "bonus": 5}, {"id": 2, "bonus": 10}]
    
    left = Stream.from_list(left_data)
    right = Stream.from_list(right_data)
    
    joined = left.join(right, key_func=lambda item: item['id']) \
                 .map(lambda pair: {**pair[0], 'total': pair[0]['value'] + pair[1].get('bonus', 0)} if pair[1] else pair[0]) \
                 .aggregate(lambda lst: sum(item['total'] for item in lst))
    
    result = joined.execute()
    
    expected = [45]  # 15 + 30
    assert result == expected

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
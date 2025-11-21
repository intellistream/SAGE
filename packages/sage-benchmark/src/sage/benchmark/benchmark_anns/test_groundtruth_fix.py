"""
测试 groundtruth 计算修复

这个脚本测试关键的修复点：
1. Tag 到 Data Index 的映射
2. Replace 操作
3. Batch Insert Delete 操作
"""
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark_anns.core.groundtruth import GroundtruthTracker


class MockDataset:
    """模拟数据集"""
    def __init__(self, n=100000, dim=128):
        np.random.seed(42)
        self._data = np.random.randn(n, dim).astype('float32')
    
    def get_dataset(self):
        return self._data


def test_basic_mapping():
    """测试基本的 tag 到 data index 映射"""
    print("\n=== Test 1: Basic Mapping ===")
    dataset = MockDataset(n=10000, dim=128)
    tracker = GroundtruthTracker(dataset, metric='euclidean')
    
    # Initial load
    entry = {'operation': 'initial', 'start': 0, 'end': 1000}
    tracker.process_initial(entry)
    
    tags, data = tracker.get_active_data()
    
    print(f"Number of active points: {len(tags)}")
    assert len(tags) == 1000, f"Expected 1000 tags, got {len(tags)}"
    assert len(data) == 1000, f"Expected 1000 data points, got {len(data)}"
    
    # Verify mapping
    for i in range(10):
        assert tracker.tag_to_id[i] == i, f"Tag {i} should map to index {i}"
    
    print("✓ Basic mapping test passed")


def test_replace_operation():
    """测试 replace 操作 - 关键修复点"""
    print("\n=== Test 2: Replace Operation ===")
    dataset = MockDataset(n=100000, dim=128)
    tracker = GroundtruthTracker(dataset, metric='euclidean')
    
    # Initial load
    entry = {'operation': 'initial', 'start': 0, 'end': 1000}
    tracker.process_initial(entry)
    
    print(f"Before replace: tag 0 -> data_index {tracker.tag_to_id[0]}")
    print(f"Before replace: tag 999 -> data_index {tracker.tag_to_id[999]}")
    
    # Replace: tags 0-499 now point to data indices 50000-50499
    replace_entry = {
        'operation': 'replace',
        'tags_start': 0,
        'tags_end': 500,
        'ids_start': 50000
    }
    tracker.process_replace(replace_entry)
    
    print(f"After replace: tag 0 -> data_index {tracker.tag_to_id[0]}")
    print(f"After replace: tag 499 -> data_index {tracker.tag_to_id[499]}")
    print(f"After replace: tag 999 -> data_index {tracker.tag_to_id[999]}")
    
    # Verify mapping changed
    assert tracker.tag_to_id[0] == 50000, f"Tag 0 should now map to 50000, got {tracker.tag_to_id[0]}"
    assert tracker.tag_to_id[499] == 50499, f"Tag 499 should now map to 50499, got {tracker.tag_to_id[499]}"
    assert tracker.tag_to_id[999] == 999, f"Tag 999 should still map to 999, got {tracker.tag_to_id[999]}"
    
    # Get data and verify
    tags, data = tracker.get_active_data()
    assert len(tags) == 1000, f"Should still have 1000 tags, got {len(tags)}"
    
    # Verify data vectors are different for replaced tags
    original_data = dataset.get_dataset()
    tag_0_idx = np.where(tags == 0)[0][0]
    tag_999_idx = np.where(tags == 999)[0][0]
    
    # Tag 0 should have data from index 50000
    assert np.allclose(data[tag_0_idx], original_data[50000]), "Tag 0 data should match index 50000"
    # Tag 999 should still have data from index 999
    assert np.allclose(data[tag_999_idx], original_data[999]), "Tag 999 data should match index 999"
    
    print("✓ Replace operation test passed")


def test_delete_operation():
    """测试删除操作"""
    print("\n=== Test 3: Delete Operation ===")
    dataset = MockDataset(n=10000, dim=128)
    tracker = GroundtruthTracker(dataset, metric='euclidean')
    
    # Initial load
    entry = {'operation': 'initial', 'start': 0, 'end': 1000}
    tracker.process_initial(entry)
    
    print(f"Before delete: {len(tracker.tag_to_id)} tags")
    
    # Delete tags 100-199
    delete_entry = {'operation': 'delete', 'start': 100, 'end': 200}
    tracker.process_delete(delete_entry)
    
    print(f"After delete: {len(tracker.tag_to_id)} tags")
    
    assert len(tracker.tag_to_id) == 900, f"Should have 900 tags after deletion, got {len(tracker.tag_to_id)}"
    assert 50 in tracker.tag_to_id, "Tag 50 should still exist"
    assert 150 not in tracker.tag_to_id, "Tag 150 should be deleted"
    assert 250 in tracker.tag_to_id, "Tag 250 should still exist"
    
    print("✓ Delete operation test passed")


def test_batch_insert_delete():
    """测试 batch_insert_delete 操作 - 关键修复点"""
    print("\n=== Test 4: Batch Insert Delete ===")
    dataset = MockDataset(n=100000, dim=128)
    tracker = GroundtruthTracker(dataset, metric='euclidean')
    
    # Batch insert delete: 10 batches of 1000, delete 10% from each batch
    entry = {
        'operation': 'batch_insert_delete',
        'start': 0,
        'end': 10000,
        'batchSize': 1000,
        'deletion_percentage': 0.1
    }
    
    # Don't compute continuous queries for this test
    tracker.process_batch_insert_delete(
        entry=entry,
        queries=None,
        k=10,
        step=0
    )
    
    print(f"Active tags after batch_insert_delete: {len(tracker.tag_to_id)}")
    
    # Should have 90% of data (10000 * 0.9 = 9000)
    expected_count = int(10000 * 0.9)
    assert len(tracker.tag_to_id) == expected_count, \
        f"Expected {expected_count} tags, got {len(tracker.tag_to_id)}"
    
    # Check that last 10% of each batch is deleted
    for batch_idx in range(10):
        batch_start = batch_idx * 1000
        batch_end = (batch_idx + 1) * 1000
        delete_start = int(batch_end - 1000 * 0.1)
        
        # Check some tags in the retained part
        assert batch_start in tracker.tag_to_id, \
            f"Tag {batch_start} (start of batch {batch_idx}) should exist"
        
        # Check some tags in the deleted part
        assert (batch_end - 1) not in tracker.tag_to_id, \
            f"Tag {batch_end - 1} (end of batch {batch_idx}) should be deleted"
    
    print("✓ Batch insert delete test passed")


def test_groundtruth_computation():
    """测试真值计算"""
    print("\n=== Test 5: Groundtruth Computation ===")
    dataset = MockDataset(n=10000, dim=128)
    tracker = GroundtruthTracker(dataset, metric='euclidean')
    
    # Initial load
    entry = {'operation': 'initial', 'start': 0, 'end': 1000}
    tracker.process_initial(entry)
    
    # Generate some queries
    np.random.seed(43)
    queries = np.random.randn(10, 128).astype('float32')
    
    # Compute groundtruth
    gt = tracker.compute_search_groundtruth(queries, k=10, step=1)
    
    print(f"Query shape: {queries.shape}")
    print(f"GT tags shape: {gt['tags'].shape}")
    print(f"GT distances shape: {gt['distances'].shape}")
    print(f"Active points: {gt['num_active_points']}")
    
    assert gt['tags'].shape == (10, 10), f"Expected (10, 10) tags, got {gt['tags'].shape}"
    assert gt['distances'].shape == (10, 10), f"Expected (10, 10) distances, got {gt['distances'].shape}"
    assert gt['num_active_points'] == 1000, f"Expected 1000 active points, got {gt['num_active_points']}"
    
    # Check that all returned tags are valid (in range 0-999)
    assert np.all(gt['tags'] >= 0) and np.all(gt['tags'] < 1000), \
        "All tags should be in range [0, 1000)"
    
    print("✓ Groundtruth computation test passed")


def test_replace_with_groundtruth():
    """测试 replace 后的真值计算 - 综合测试"""
    print("\n=== Test 6: Replace with Groundtruth (Integration) ===")
    dataset = MockDataset(n=100000, dim=128)
    tracker = GroundtruthTracker(dataset, metric='euclidean')
    
    # Initial load: tags 0-999 point to data 0-999
    tracker.process_initial({'start': 0, 'end': 1000})
    
    # Replace: tags 0-499 now point to data 50000-50499
    tracker.process_replace({
        'tags_start': 0,
        'tags_end': 500,
        'ids_start': 50000
    })
    
    # Generate a query from data index 50000 (should match tag 0 after replace)
    original_data = dataset.get_dataset()
    query = original_data[50000:50001]  # Shape (1, 128)
    
    # Compute groundtruth
    gt = tracker.compute_search_groundtruth(query, k=10, step=1)
    
    print(f"Query matches data index 50000")
    print(f"Top 10 result tags: {gt['tags'][0]}")
    print(f"Top 10 distances: {gt['distances'][0]}")
    
    # The nearest neighbor should be tag 0 (which points to data 50000)
    assert gt['tags'][0, 0] == 0, \
        f"Nearest neighbor should be tag 0, got {gt['tags'][0, 0]}"
    assert gt['distances'][0, 0] < 1e-5, \
        f"Distance to nearest neighbor should be ~0, got {gt['distances'][0, 0]}"
    
    print("✓ Replace with groundtruth test passed")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Testing Groundtruth Computation Fixes")
    print("=" * 60)
    
    try:
        test_basic_mapping()
        test_replace_operation()
        test_delete_operation()
        test_batch_insert_delete()
        test_groundtruth_computation()
        test_replace_with_groundtruth()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

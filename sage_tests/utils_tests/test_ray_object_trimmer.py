"""
测试Ray对象预处理器的效果
验证trim_object_for_ray函数能否正确清理对象以供Ray序列化
"""
import sys
import os
import time
import threading
import pickle
from typing import Any, Dict, List, Optional
from pathlib import Path

# 添加项目根路径
SAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SAGE_ROOT))

from sage_utils.serialization.dill_serializer import (
    trim_object_for_ray,
    RayObjectTrimmer,
    SerializationError
)

# 尝试导入Ray
try:
    import ray
    RAY_AVAILABLE = True
    print("Ray is available for testing")
except ImportError:
    RAY_AVAILABLE = False
    print("Ray not available, will only test object trimming")


class ProblematicClass:
    """包含不可序列化内容的测试类"""
    
    def __init__(self, name: str):
        self.name = name
        self.data = {"key": "value", "number": 42}
        
        # 不可序列化的属性
        self.logger = self._create_mock_logger()
        self.thread = threading.Thread(target=lambda: None)
        self.lock = threading.Lock()
        self.file_handle = open(__file__, 'r')  # 文件句柄
        self.socket_mock = self._create_socket_mock()
        
        # 循环引用
        self.self_ref = self
        
        # 可序列化的属性
        self.config = {
            "setting1": "value1",
            "setting2": 100,
            "nested": {"inner": "data"}
        }
        self.items = [1, 2, 3, "test"]
        
        # 定义序列化排除列表
        self.__state_exclude__ = [
            'logger', 'thread', 'lock', 'file_handle', 'socket_mock', 'self_ref'
        ]
    
    def _create_mock_logger(self):
        """创建模拟日志对象"""
        class MockLogger:
            def info(self, msg): pass
            def error(self, msg): pass
        return MockLogger()
    
    def _create_socket_mock(self):
        """创建模拟socket对象"""
        class MockSocket:
            def __init__(self):
                self.connected = False
        return MockSocket()
    
    def get_safe_data(self):
        """返回可以安全序列化的数据"""
        return {
            "name": self.name,
            "data": self.data,
            "config": self.config,
            "items": self.items
        }
    
    def __del__(self):
        # 清理文件句柄
        try:
            if hasattr(self, 'file_handle') and self.file_handle:
                self.file_handle.close()
        except:
            pass


class NestedProblematicClass:
    """包含嵌套问题的测试类"""
    
    def __init__(self):
        self.name = "nested_test"
        self.problematic_child = ProblematicClass("child")
        self.safe_data = {"nested": "safe"}
        self.thread_list = [threading.Thread(target=lambda: None) for _ in range(3)]


def test_basic_trimming():
    """测试基本的对象trim功能"""
    print("\n=== 测试基本Trim功能 ===")
    
    # 创建有问题的对象
    obj = ProblematicClass("test_object")
    
    print(f"原始对象属性数量: {len(obj.__dict__)}")
    print("原始对象属性:", list(obj.__dict__.keys()))
    
    # 执行trim
    try:
        trimmed_obj = trim_object_for_ray(obj)
        
        print(f"清理后对象属性数量: {len(trimmed_obj.__dict__)}")
        print("清理后对象属性:", list(trimmed_obj.__dict__.keys()))
        
        # 验证清理效果
        assert hasattr(trimmed_obj, 'name'), "name属性应该被保留"
        assert hasattr(trimmed_obj, 'data'), "data属性应该被保留"
        assert hasattr(trimmed_obj, 'config'), "config属性应该被保留"
        assert not hasattr(trimmed_obj, 'logger'), "logger属性应该被移除"
        assert not hasattr(trimmed_obj, 'thread'), "thread属性应该被移除"
        assert not hasattr(trimmed_obj, 'lock'), "lock属性应该被移除"
        
        print("✓ 基本trim测试通过")
        return trimmed_obj
        
    except Exception as e:
        print(f"✗ 基本trim测试失败: {e}")
        raise


def test_custom_include_exclude():
    """测试自定义include/exclude功能"""
    print("\n=== 测试自定义Include/Exclude ===")
    
    obj = ProblematicClass("test_custom")
    
    # 测试exclude
    trimmed_obj = trim_object_for_ray(obj, exclude=['data', 'config'])
    assert hasattr(trimmed_obj, 'name'), "name应该保留"
    assert not hasattr(trimmed_obj, 'data'), "data应该被排除"
    assert not hasattr(trimmed_obj, 'config'), "config应该被排除"
    print("✓ Exclude测试通过")
    
    # 测试include
    trimmed_obj = trim_object_for_ray(obj, include=['name', 'items'])
    assert hasattr(trimmed_obj, 'name'), "name应该包含"
    assert hasattr(trimmed_obj, 'items'), "items应该包含"
    assert not hasattr(trimmed_obj, 'data'), "data不在include中应该被排除"
    print("✓ Include测试通过")


def test_ray_object_trimmer():
    """测试RayObjectTrimmer类的功能"""
    print("\n=== 测试RayObjectTrimmer类 ===")
    
    obj = ProblematicClass("trimmer_test")
    
    # 测试浅层清理
    shallow_cleaned = RayObjectTrimmer.trim_for_remote_call(obj, deep_clean=False)
    print(f"浅层清理后属性: {list(shallow_cleaned.__dict__.keys())}")
    
    # 测试深度清理
    deep_cleaned = RayObjectTrimmer.trim_for_remote_call(obj, deep_clean=True)
    print(f"深度清理后属性: {list(deep_cleaned.__dict__.keys())}")
    
    # 验证清理效果
    assert not hasattr(deep_cleaned, 'logger'), "logger应该被移除"
    assert hasattr(deep_cleaned, 'name'), "name应该保留"
    
    print("✓ RayObjectTrimmer测试通过")


def test_nested_object_trimming():
    """测试嵌套对象的清理"""
    print("\n=== 测试嵌套对象清理 ===")
    
    nested_obj = NestedProblematicClass()
    
    print("原始嵌套对象结构:")
    print(f"  - 顶层属性: {list(nested_obj.__dict__.keys())}")
    if hasattr(nested_obj, 'problematic_child'):
        print(f"  - 子对象属性: {list(nested_obj.problematic_child.__dict__.keys())}")
    
    # 执行嵌套清理
    trimmed_nested = trim_object_for_ray(nested_obj)
    
    print("清理后嵌套对象结构:")
    print(f"  - 顶层属性: {list(trimmed_nested.__dict__.keys())}")
    if hasattr(trimmed_nested, 'problematic_child'):
        print(f"  - 子对象属性: {list(trimmed_nested.problematic_child.__dict__.keys())}")
    
    # 验证嵌套清理
    assert hasattr(trimmed_nested, 'name'), "顶层name应该保留"
    assert hasattr(trimmed_nested, 'safe_data'), "safe_data应该保留"
    assert not hasattr(trimmed_nested, 'thread_list'), "thread_list应该被移除"
    
    # 验证子对象也被清理
    if hasattr(trimmed_nested, 'problematic_child'):
        child = trimmed_nested.problematic_child
        assert hasattr(child, 'name'), "子对象name应该保留"
        assert not hasattr(child, 'logger'), "子对象logger应该被移除"
    
    print("✓ 嵌套对象清理测试通过")


def test_ray_serialization_validation():
    """测试Ray序列化验证功能"""
    print("\n=== 测试Ray序列化验证 ===")
    
    if not RAY_AVAILABLE:
        print("⚠ Ray不可用，跳过序列化验证测试")
        return
    
    obj = ProblematicClass("validation_test")
    
    # 验证原始对象
    print("验证原始对象...")
    original_result = RayObjectTrimmer.validate_ray_serializable(obj)
    print(f"原始对象可序列化: {original_result['is_serializable']}")
    if original_result['issues']:
        print("问题列表:")
        for issue in original_result['issues']:
            print(f"  - {issue}")
    
    # 验证清理后的对象
    print("验证清理后对象...")
    trimmed_obj = trim_object_for_ray(obj)
    trimmed_result = RayObjectTrimmer.validate_ray_serializable(trimmed_obj)
    print(f"清理后对象可序列化: {trimmed_result['is_serializable']}")
    if trimmed_result['issues']:
        print("问题列表:")
        for issue in trimmed_result['issues']:
            print(f"  - {issue}")
    else:
        print(f"序列化大小估计: {trimmed_result['size_estimate']} 字节")
    
    # 验证改进效果
    if not original_result['is_serializable'] and trimmed_result['is_serializable']:
        print("✓ 清理成功解决了序列化问题")
    elif original_result['is_serializable'] and trimmed_result['is_serializable']:
        print("✓ 对象清理后仍然可序列化")
    else:
        print("⚠ 清理可能没有完全解决序列化问题")


def test_ray_remote_call_simulation():
    """模拟Ray远程调用测试"""
    print("\n=== 模拟Ray远程调用测试 ===")
    
    if not RAY_AVAILABLE:
        print("⚠ Ray不可用，跳过远程调用测试")
        return
    
    # 初始化Ray
    if not ray.is_initialized():
        ray.init(address="auto", _temp_dir="/var/lib/ray_shared")
    
    @ray.remote
    class TestActor:
        def process_object(self, obj):
            """处理接收到的对象"""
            return {
                "received_type": type(obj).__name__,
                "attributes": list(obj.__dict__.keys()) if hasattr(obj, '__dict__') else [],
                "name": getattr(obj, 'name', 'unknown'),
                "data": getattr(obj, 'data', None)
            }
    
    # 创建测试对象和Actor
    obj = ProblematicClass("ray_test")
    actor = TestActor.remote()
    
    # 测试原始对象（可能失败）
    print("测试原始对象传输...")
    try:
        original_result = ray.get(actor.process_object.remote(obj))
        print(f"原始对象传输成功: {original_result}")
    except Exception as e:
        print(f"原始对象传输失败: {e}")
    
    # 测试清理后的对象
    print("测试清理后对象传输...")
    try:
        trimmed_obj = trim_object_for_ray(obj)
        trimmed_result = ray.get(actor.process_object.remote(trimmed_obj))
        print(f"清理后对象传输成功: {trimmed_result}")
        print("✓ Ray远程调用测试通过")
    except Exception as e:
        print(f"清理后对象传输失败: {e}")
        print("✗ Ray远程调用测试失败")
    
    # 清理Ray
    try:
        ray.shutdown()
    except:
        pass


def test_performance_comparison():
    """测试性能对比"""
    print("\n=== 性能对比测试 ===")
    
    # 创建大量测试对象
    objects = [ProblematicClass(f"perf_test_{i}") for i in range(100)]
    
    # 测试trim性能
    start_time = time.time()
    trimmed_objects = []
    for obj in objects:
        try:
            trimmed = trim_object_for_ray(obj)
            trimmed_objects.append(trimmed)
        except Exception as e:
            print(f"Trim失败: {e}")
    
    trim_time = time.time() - start_time
    print(f"清理100个对象耗时: {trim_time:.4f}秒")
    print(f"平均每个对象: {trim_time/100:.4f}秒")
    print(f"成功清理对象数量: {len(trimmed_objects)}")
    
    if RAY_AVAILABLE:
        # 测试Ray序列化性能
        import ray.cloudpickle as cloudpickle
        
        start_time = time.time()
        serialized_count = 0
        for obj in trimmed_objects[:10]:  # 只测试前10个
            try:
                cloudpickle.dumps(obj)
                serialized_count += 1
            except:
                pass
        
        serialize_time = time.time() - start_time
        print(f"Ray序列化10个清理对象耗时: {serialize_time:.4f}秒")
        print(f"成功序列化对象数量: {serialized_count}")


def run_all_tests():
    """运行所有测试"""
    print("开始Ray对象预处理器测试...")
    print("=" * 50)
    
    try:
        # 基本测试
        test_basic_trimming()
        test_custom_include_exclude()
        test_ray_object_trimmer()
        test_nested_object_trimming()
        
        # Ray相关测试
        test_ray_serialization_validation()
        test_ray_remote_call_simulation()
        
        # 性能测试
        test_performance_comparison()
        
        print("\n" + "=" * 50)
        print("✓ 所有测试完成！")
        
    except Exception as e:
        print(f"\n✗ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理资源
        import gc
        gc.collect()
        
    return True


if __name__ == "__main__":
    success = run_all_tests()
    
    if success:
        print("\n🎉 所有测试通过！trim_object_for_ray函数工作正常")
    else:
        print("\n❌ 部分测试失败，请检查实现")
        sys.exit(1)

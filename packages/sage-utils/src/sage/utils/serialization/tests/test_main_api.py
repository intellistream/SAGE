"""
测试 sage.utils.serialization 主要API和便捷函数
"""
import pytest
import sys
import os
import tempfile
import threading

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

# 测试主要导入
import sage.utils.serialization as serialization
from sage.utils.serialization import (
    serialize_object,
    deserialize_object,
    save_object_state,
    load_object_from_file,
    load_object_state,
    pack_object,
    unpack_object,
    trim_object_for_ray,
    UniversalSerializer,
    RayObjectTrimmer,
    SerializationError
)


class TestMainAPIImports:
    """测试主要API导入"""
    
    def test_all_imports_available(self):
        """测试所有公共API都可以导入"""
        # 便捷函数
        assert callable(serialize_object)
        assert callable(deserialize_object)
        assert callable(save_object_state)
        assert callable(load_object_from_file)
        assert callable(load_object_state)
        
        # 向后兼容函数
        assert callable(pack_object)
        assert callable(unpack_object)
        
        # Ray相关
        assert callable(trim_object_for_ray)
        
        # 主要类
        assert UniversalSerializer is not None
        assert RayObjectTrimmer is not None
        
        # 异常
        assert issubclass(SerializationError, Exception)
    
    def test_module_has_all_attribute(self):
        """测试模块有 __all__ 属性"""
        assert hasattr(serialization, '__all__')
        assert isinstance(serialization.__all__, list)
        assert len(serialization.__all__) > 0
    
    def test_all_exported_items_exist(self):
        """测试 __all__ 中的所有项目都存在"""
        for item_name in serialization.__all__:
            assert hasattr(serialization, item_name), f"Missing exported item: {item_name}"


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_serialize_deserialize_functions(self):
        """测试序列化/反序列化函数"""
        test_data = {
            'string': 'hello world',
            'number': 42,
            'list': [1, 2, 3],
            'nested': {'key': 'value'}
        }
        
        # 测试序列化
        serialized = serialize_object(test_data)
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
        
        # 测试反序列化
        deserialized = deserialize_object(serialized)
        assert deserialized == test_data
    
    def test_serialize_with_filters(self):
        """测试带过滤器的序列化"""
        class TestClass:
            def __init__(self):
                self.keep = "keep_value"
                self.exclude = "exclude_value"
                self.logger = "should_be_filtered"
        
        obj = TestClass()
        
        # 测试 exclude
        serialized = serialize_object(obj, exclude=['exclude'])
        deserialized = deserialize_object(serialized)
        
        assert hasattr(deserialized, 'keep')
        assert not hasattr(deserialized, 'exclude')
        assert not hasattr(deserialized, 'logger')  # 默认过滤
        
        # 测试 include
        serialized = serialize_object(obj, include=['keep', 'exclude'])
        deserialized = deserialize_object(serialized)
        
        assert hasattr(deserialized, 'keep')
        assert hasattr(deserialized, 'exclude')
        assert not hasattr(deserialized, 'logger')  # 不在 include 中
    
    def test_file_operations(self):
        """测试文件操作函数"""
        test_data = {
            'test': 'file_operations',
            'number': 123
        }
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        try:
            # 测试保存
            save_object_state(test_data, temp_path)
            assert os.path.exists(temp_path)
            
            # 测试加载
            loaded_data = load_object_from_file(temp_path)
            assert loaded_data == test_data
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_object_state_function(self):
        """测试加载对象状态函数"""
        class TestClass:
            def __init__(self):
                self.attr1 = "original1"
                self.attr2 = "original2"
        
        # 创建源对象
        source_obj = TestClass()
        source_obj.attr1 = "modified1"
        source_obj.attr2 = "modified2"
        
        # 创建目标对象
        target_obj = TestClass()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        try:
            # 保存源对象状态
            save_object_state(source_obj, temp_path)
            
            # 加载状态到目标对象
            success = load_object_state(target_obj, temp_path)
            
            assert success is True
            assert target_obj.attr1 == "modified1"
            assert target_obj.attr2 == "modified2"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestBackwardCompatibility:
    """测试向后兼容性"""
    
    def test_pack_unpack_functions(self):
        """测试 pack/unpack 函数（向后兼容）"""
        test_data = {
            'legacy': 'compatibility',
            'version': 'old'
        }
        
        # 测试 pack
        packed = pack_object(test_data)
        assert isinstance(packed, bytes)
        assert len(packed) > 0
        
        # 测试 unpack
        unpacked = unpack_object(packed)
        assert unpacked == test_data
    
    def test_pack_unpack_with_filters(self):
        """测试带过滤器的 pack/unpack"""
        class LegacyClass:
            def __init__(self):
                self.keep = "keep_value"
                self.remove = "remove_value"
        
        obj = LegacyClass()
        
        # 测试带过滤器的 pack
        packed = pack_object(obj, exclude=['remove'])
        unpacked = unpack_object(packed)
        
        assert hasattr(unpacked, 'keep')
        assert not hasattr(unpacked, 'remove')
    
    def test_pack_unpack_equivalence(self):
        """测试 pack/unpack 与 serialize/deserialize 的等价性"""
        test_data = {'test': 'equivalence'}
        
        # 使用新函数
        serialized = serialize_object(test_data)
        deserialized = deserialize_object(serialized)
        
        # 使用旧函数
        packed = pack_object(test_data)
        unpacked = unpack_object(packed)
        
        # 结果应该相同
        assert deserialized == unpacked
        assert deserialized == test_data


class TestRayIntegration:
    """测试 Ray 集成功能"""
    
    def test_trim_object_for_ray_function(self):
        """测试 trim_object_for_ray 函数"""
        class TestTransformation:
            def __init__(self):
                self.name = "test_transform"
                self.config = {'param': 'value'}
                self.logger = "should_be_removed"
                self.env = "also_removed"
                self.thread = threading.Thread(target=lambda: None)
        
        obj = TestTransformation()
        result = trim_object_for_ray(obj)
        
        assert result is not None
        assert hasattr(result, 'name')
        assert hasattr(result, 'config')
        assert not hasattr(result, 'logger')
        assert not hasattr(result, 'env')
        assert not hasattr(result, 'thread')
    
    def test_trim_object_for_ray_with_filters(self):
        """测试带过滤器的 Ray 清理"""
        class TestClass:
            def __init__(self):
                self.keep1 = "keep1"
                self.keep2 = "keep2"
                self.custom_remove = "remove"
        
        obj = TestClass()
        result = trim_object_for_ray(obj, exclude=['custom_remove'])
        
        assert result is not None
        assert hasattr(result, 'keep1')
        assert hasattr(result, 'keep2')
        assert not hasattr(result, 'custom_remove')
    
    def test_ray_object_trimmer_access(self):
        """测试 RayObjectTrimmer 类的访问"""
        # 测试专用清理方法
        class MockTransformation:
            def __init__(self):
                self.name = "test"
                self.logger = "remove"
        
        obj = MockTransformation()
        result = RayObjectTrimmer.trim_transformation_for_ray(obj)
        
        assert result is not None
        assert hasattr(result, 'name')
        assert not hasattr(result, 'logger')


class TestErrorHandling:
    """测试错误处理"""
    
    def test_serialization_error_propagation(self):
        """测试序列化错误的传播"""
        # 这个测试需要mock来模拟错误情况
        from unittest.mock import patch
        
        with patch('sage.utils.serialization.universal_serializer.dill.dumps') as mock_dumps:
            mock_dumps.side_effect = Exception("Mock serialization error")
            
            with pytest.raises(SerializationError):
                serialize_object({'test': 'data'})
    
    def test_file_not_found_error(self):
        """测试文件不存在错误"""
        with pytest.raises(FileNotFoundError):
            load_object_from_file("/nonexistent/path/file.pkl")
    
    def test_graceful_error_handling_in_load_state(self):
        """测试加载状态时的优雅错误处理"""
        class TestClass:
            pass
        
        obj = TestClass()
        # 文件不存在时应该返回 False 而不是抛出异常
        success = load_object_state(obj, "/nonexistent/file.pkl")
        assert success is False


class TestComplexIntegrationScenarios:
    """测试复杂的集成场景"""
    
    def test_full_workflow_serialization(self):
        """测试完整的序列化工作流"""
        # 创建复杂的对象结构
        class WorkflowStep:
            def __init__(self, name, config):
                self.name = name
                self.config = config
                self.logger = f"logger_for_{name}"  # 会被过滤
                self.results = []
        
        class Workflow:
            def __init__(self):
                self.workflow_id = "test_workflow"
                self.steps = [
                    WorkflowStep("step1", {"param1": "value1"}),
                    WorkflowStep("step2", {"param2": "value2"})
                ]
                self.metadata = {
                    "created_by": "test_user",
                    "created_at": "2024-01-01"
                }
                self.runtime_context = "should_be_filtered"
        
        workflow = Workflow()
        
        # 序列化和反序列化
        serialized = serialize_object(workflow)
        deserialized = deserialize_object(serialized)
        
        # 验证结构保持完整
        assert deserialized.workflow_id == "test_workflow"
        assert len(deserialized.steps) == 2
        assert deserialized.steps[0].name == "step1"
        assert deserialized.steps[1].config["param2"] == "value2"
        assert deserialized.metadata["created_by"] == "test_user"
        
        # 验证过滤效果
        assert not hasattr(deserialized, 'runtime_context')
        assert not hasattr(deserialized.steps[0], 'logger')
        assert not hasattr(deserialized.steps[1], 'logger')
    
    def test_ray_integration_workflow(self):
        """测试 Ray 集成工作流"""
        class DataProcessor:
            def __init__(self):
                self.processor_id = "proc_001"
                self.config = {
                    "input_format": "json",
                    "output_format": "parquet",
                    "batch_size": 1000
                }
                self.transformations = [
                    {"type": "filter", "condition": "value > 0"},
                    {"type": "aggregate", "function": "sum"}
                ]
                
                # Ray 不兼容的属性
                self.logger = "logger_instance"
                self.env = "environment_reference"
                self.server_socket = "socket_instance"
        
        processor = DataProcessor()
        
        # 为 Ray 清理对象
        cleaned_processor = trim_object_for_ray(processor)
        
        # 验证清理效果
        assert cleaned_processor.processor_id == "proc_001"
        assert cleaned_processor.config["batch_size"] == 1000
        assert len(cleaned_processor.transformations) == 2
        assert not hasattr(cleaned_processor, 'logger')
        assert not hasattr(cleaned_processor, 'env')
        assert not hasattr(cleaned_processor, 'server_socket')
        
        # 验证清理后的对象可以序列化
        serialized = serialize_object(cleaned_processor)
        deserialized = deserialize_object(serialized)
        
        assert deserialized.processor_id == "proc_001"
        assert deserialized.config["batch_size"] == 1000
    
    def test_state_persistence_workflow(self):
        """测试状态持久化工作流"""
        class ApplicationState:
            def __init__(self):
                self.app_id = "app_001"
                self.config = {"debug": False, "port": 8080}
                self.user_sessions = {
                    "user1": {"last_activity": "2024-01-01"},
                    "user2": {"last_activity": "2024-01-02"}
                }
                self.cache = {}  # 临时数据，不需要持久化
                self.logger = "logger_instance"  # 不需要持久化
            
            # 定义哪些属性不需要持久化
            __state_exclude__ = ['cache', 'logger']
        
        # 创建应用状态
        app_state = ApplicationState()
        app_state.cache["temp_data"] = "temp_value"
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        try:
            # 保存状态
            save_object_state(app_state, temp_path)
            
            # 创建新的应用实例
            new_app_state = ApplicationState()
            new_app_state.app_id = "different_id"  # 这会被覆盖
            
            # 加载状态
            success = load_object_state(new_app_state, temp_path)
            
            assert success is True
            assert new_app_state.app_id == "app_001"  # 被正确恢复
            assert new_app_state.config["port"] == 8080
            assert "user1" in new_app_state.user_sessions
            assert "user2" in new_app_state.user_sessions
            
            # 验证排除的属性没有被加载
            # cache 应该保持为新实例的值（空字典）
            assert new_app_state.cache == {}
            # logger 也应该是新实例的值
            assert new_app_state.logger == "logger_instance"
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__])

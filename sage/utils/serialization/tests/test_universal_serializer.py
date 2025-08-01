"""
测试 sage.utils.serialization.universal_serializer 模块
"""
import pytest
import sys
import os
import tempfile
import threading
from unittest.mock import patch, MagicMock

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from sage.utils.serialization.universal_serializer import UniversalSerializer
from sage.utils.serialization.exceptions import SerializationError


class TestUniversalSerializer:
    """测试 UniversalSerializer 类"""
    
    def test_serialize_basic_object(self):
        """测试序列化基本对象"""
        test_data = {
            'string': 'hello',
            'number': 42,
            'list': [1, 2, 3],
            'boolean': True,
            'none': None
        }
        
        serialized = UniversalSerializer.serialize_object(test_data)
        
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
    
    def test_deserialize_basic_object(self):
        """测试反序列化基本对象"""
        test_data = {
            'string': 'hello',
            'number': 42,
            'list': [1, 2, 3]
        }
        
        serialized = UniversalSerializer.serialize_object(test_data)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert deserialized == test_data
    
    def test_serialize_deserialize_round_trip(self):
        """测试序列化反序列化往返"""
        test_objects = [
            42,
            "string",
            [1, 2, 3],
            {'key': 'value'},
            {'nested': {'deep': 'value'}},
            None,
            True,
            False
        ]
        
        for obj in test_objects:
            serialized = UniversalSerializer.serialize_object(obj)
            deserialized = UniversalSerializer.deserialize_object(serialized)
            assert deserialized == obj
    
    def test_serialize_complex_object(self):
        """测试序列化复杂对象"""
        class ComplexClass:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42
                self.attr3 = [1, 2, 3]
                self.attr4 = {'nested': 'dict'}
        
        obj = ComplexClass()
        serialized = UniversalSerializer.serialize_object(obj)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert isinstance(deserialized, ComplexClass)
        assert deserialized.attr1 == "value1"
        assert deserialized.attr2 == 42
        assert deserialized.attr3 == [1, 2, 3]
        assert deserialized.attr4 == {'nested': 'dict'}
    
    def test_serialize_with_blacklisted_content(self):
        """测试序列化包含黑名单内容的对象"""
        class ObjectWithThread:
            def __init__(self):
                self.safe_data = "safe"
                self.logger = "fake_logger"  # 会被过滤
                self.thread = threading.Thread(target=lambda: None)  # 会被过滤
        
        obj = ObjectWithThread()
        
        # 应该能够序列化（黑名单内容被自动过滤）
        serialized = UniversalSerializer.serialize_object(obj)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert hasattr(deserialized, 'safe_data')
        assert deserialized.safe_data == "safe"
        assert not hasattr(deserialized, 'logger')
        assert not hasattr(deserialized, 'thread')
    
    def test_serialize_with_include_list(self):
        """测试使用 include 列表序列化"""
        class TestClass:
            def __init__(self):
                self.keep1 = "keep1"
                self.keep2 = "keep2"
                self.exclude = "exclude"
        
        obj = TestClass()
        
        # 只保留指定的属性
        serialized = UniversalSerializer.serialize_object(obj, include=['keep1', 'keep2'])
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert hasattr(deserialized, 'keep1')
        assert hasattr(deserialized, 'keep2')
        assert not hasattr(deserialized, 'exclude')
    
    def test_serialize_with_exclude_list(self):
        """测试使用 exclude 列表序列化"""
        class TestClass:
            def __init__(self):
                self.keep1 = "keep1"
                self.keep2 = "keep2"
                self.exclude = "exclude"
        
        obj = TestClass()
        
        # 排除指定的属性
        serialized = UniversalSerializer.serialize_object(obj, exclude=['exclude'])
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert hasattr(deserialized, 'keep1')
        assert hasattr(deserialized, 'keep2')
        assert not hasattr(deserialized, 'exclude')
    
    @patch('sage.utils.serialization.universal_serializer.dill', None)
    def test_serialize_without_dill(self):
        """测试没有 dill 时的行为"""
        with pytest.raises(SerializationError, match="dill is required"):
            UniversalSerializer.serialize_object({'test': 'data'})
    
    @patch('sage.utils.serialization.universal_serializer.dill', None)
    def test_deserialize_without_dill(self):
        """测试没有 dill 时的反序列化行为"""
        with pytest.raises(SerializationError, match="dill is required"):
            UniversalSerializer.deserialize_object(b'fake_data')
    
    @patch('sage.utils.serialization.universal_serializer.dill.dumps')
    def test_serialize_error_handling(self, mock_dumps):
        """测试序列化错误处理"""
        mock_dumps.side_effect = Exception("Serialization failed")
        
        with pytest.raises(SerializationError, match="Object serialization failed"):
            UniversalSerializer.serialize_object({'test': 'data'})
    
    @patch('sage.utils.serialization.universal_serializer.dill.loads')
    def test_deserialize_error_handling(self, mock_loads):
        """测试反序列化错误处理"""
        mock_loads.side_effect = Exception("Deserialization failed")
        
        with pytest.raises(SerializationError, match="Object deserialization failed"):
            UniversalSerializer.deserialize_object(b'fake_data')


class TestUniversalSerializerFileOperations:
    """测试 UniversalSerializer 文件操作"""
    
    def test_save_object_state(self):
        """测试保存对象状态到文件"""
        test_data = {'test': 'data', 'number': 42}
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        try:
            UniversalSerializer.save_object_state(test_data, temp_path)
            
            # 验证文件被创建
            assert os.path.exists(temp_path)
            
            # 验证文件内容
            with open(temp_path, 'rb') as f:
                content = f.read()
                assert len(content) > 0
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_save_object_state_creates_directory(self):
        """测试保存对象时创建目录"""
        test_data = {'test': 'data'}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = os.path.join(temp_dir, 'nested', 'dir', 'file.pkl')
            
            UniversalSerializer.save_object_state(test_data, nested_path)
            
            assert os.path.exists(nested_path)
            assert os.path.isfile(nested_path)
    
    def test_load_object_from_file(self):
        """测试从文件加载对象"""
        test_data = {'test': 'data', 'number': 42}
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        try:
            # 保存对象
            UniversalSerializer.save_object_state(test_data, temp_path)
            
            # 加载对象
            loaded_data = UniversalSerializer.load_object_from_file(temp_path)
            
            assert loaded_data == test_data
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_object_from_nonexistent_file(self):
        """测试从不存在的文件加载对象"""
        with pytest.raises(FileNotFoundError, match="File not found"):
            UniversalSerializer.load_object_from_file("/nonexistent/path/file.pkl")
    
    def test_load_object_state_to_existing_object(self):
        """测试将对象状态加载到现有对象"""
        class TestClass:
            def __init__(self):
                self.attr1 = "original1"
                self.attr2 = "original2"
        
        # 创建原始对象
        original_obj = TestClass()
        original_obj.attr1 = "modified1"
        original_obj.attr2 = "modified2"
        original_obj.attr3 = "new_attr"
        
        # 创建目标对象
        target_obj = TestClass()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        try:
            # 保存原始对象状态
            UniversalSerializer.save_object_state(original_obj, temp_path)
            
            # 加载状态到目标对象
            success = UniversalSerializer.load_object_state(target_obj, temp_path)
            
            assert success is True
            assert target_obj.attr1 == "modified1"
            assert target_obj.attr2 == "modified2"
            assert target_obj.attr3 == "new_attr"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_object_state_type_mismatch(self):
        """测试类型不匹配时的状态加载"""
        class ClassA:
            def __init__(self):
                self.attr = "A"
        
        class ClassB:
            def __init__(self):
                self.attr = "B"
        
        obj_a = ClassA()
        obj_b = ClassB()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        try:
            # 保存 A 类对象
            UniversalSerializer.save_object_state(obj_a, temp_path)
            
            # 尝试加载到 B 类对象（应该失败）
            success = UniversalSerializer.load_object_state(obj_b, temp_path)
            
            assert success is False
            assert obj_b.attr == "B"  # 应该保持原值
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_load_object_state_from_nonexistent_file(self):
        """测试从不存在的文件加载状态"""
        class TestClass:
            pass
        
        obj = TestClass()
        success = UniversalSerializer.load_object_state(obj, "/nonexistent/file.pkl")
        
        assert success is False
    
    def test_load_object_state_with_include_exclude(self):
        """测试使用 include/exclude 配置的状态加载"""
        class TestClass:
            __state_exclude__ = ['exclude_attr']
            
            def __init__(self):
                self.keep_attr = "keep"
                self.exclude_attr = "exclude"
                self.normal_attr = "normal"
        
        # 创建源对象
        source_obj = TestClass()
        source_obj.keep_attr = "modified_keep"
        source_obj.exclude_attr = "modified_exclude"
        source_obj.normal_attr = "modified_normal"
        
        # 创建目标对象
        target_obj = TestClass()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            temp_path = tmp_file.name
        
        try:
            # 保存源对象（exclude_attr 应该被排除）
            UniversalSerializer.save_object_state(source_obj, temp_path)
            
            # 加载到目标对象
            success = UniversalSerializer.load_object_state(target_obj, temp_path)
            
            assert success is True
            assert target_obj.keep_attr == "modified_keep"
            assert target_obj.normal_attr == "modified_normal"
            assert target_obj.exclude_attr == "exclude"  # 应该保持原值
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('sage.utils.serialization.universal_serializer.UniversalSerializer.load_object_from_file')
    def test_load_object_state_error_handling(self, mock_load):
        """测试状态加载错误处理"""
        mock_load.side_effect = Exception("Load failed")
        
        class TestClass:
            pass
        
        obj = TestClass()
        success = UniversalSerializer.load_object_state(obj, "dummy_path")
        
        assert success is False


class TestUniversalSerializerEdgeCases:
    """测试 UniversalSerializer 边界情况"""
    
    def test_serialize_empty_object(self):
        """测试序列化空对象"""
        class EmptyClass:
            pass
        
        obj = EmptyClass()
        serialized = UniversalSerializer.serialize_object(obj)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert isinstance(deserialized, EmptyClass)
    
    def test_serialize_object_with_none_values(self):
        """测试序列化包含 None 值的对象"""
        test_data = {
            'none_value': None,
            'list_with_none': [1, None, 3],
            'dict_with_none': {'key': None}
        }
        
        serialized = UniversalSerializer.serialize_object(test_data)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert deserialized == test_data
    
    def test_serialize_object_with_false_values(self):
        """测试序列化包含 False 值的对象"""
        test_data = {
            'false_value': False,
            'zero_value': 0,
            'empty_string': '',
            'empty_list': [],
            'empty_dict': {}
        }
        
        serialized = UniversalSerializer.serialize_object(test_data)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert deserialized == test_data
    
    def test_large_object_serialization(self):
        """测试大对象序列化"""
        # 创建一个较大的对象
        large_data = {
            'large_list': list(range(10000)),
            'large_dict': {f'key_{i}': f'value_{i}' for i in range(1000)},
            'nested_structure': {
                'level1': {
                    'level2': {
                        'level3': list(range(100))
                    }
                }
            }
        }
        
        serialized = UniversalSerializer.serialize_object(large_data)
        deserialized = UniversalSerializer.deserialize_object(serialized)
        
        assert deserialized == large_data
        assert len(deserialized['large_list']) == 10000
        assert len(deserialized['large_dict']) == 1000


if __name__ == "__main__":
    pytest.main([__file__])

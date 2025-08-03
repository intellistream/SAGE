"""
测试 sage.utils.serialization.ray_trimmer 模块
"""
import pytest
import sys
import os
import threading
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from sage.utils.serialization.ray_trimmer import (
    trim_object_for_ray,
    RayObjectTrimmer
)
from sage.utils.serialization.exceptions import SerializationError
from sage.utils.serialization.config import (
    SKIP_VALUE,
    RAY_TRANSFORMATION_EXCLUDE_ATTRS,
    RAY_OPERATOR_EXCLUDE_ATTRS
)


class TestTrimObjectForRay:
    """测试 trim_object_for_ray 函数"""
    
    def test_trim_basic_object(self):
        """测试清理基本对象"""
        class BasicClass:
            def __init__(self):
                self.safe_data = "safe"
                self.number = 42
                self.list_data = [1, 2, 3]
        
        obj = BasicClass()
        result = trim_object_for_ray(obj)
        
        assert result is not None
        assert hasattr(result, 'safe_data')
        assert hasattr(result, 'number')
        assert hasattr(result, 'list_data')
        assert result.safe_data == "safe"
        assert result.number == 42
        assert result.list_data == [1, 2, 3]
    
    def test_trim_object_with_blacklisted_content(self):
        """测试清理包含黑名单内容的对象"""
        class ObjectWithBlacklisted:
            def __init__(self):
                self.safe_data = "safe"
                self.logger = "fake_logger"  # 会被过滤
                self.thread = threading.Thread(target=lambda: None)  # 会被过滤
                self.number = 42
        
        obj = ObjectWithBlacklisted()
        result = trim_object_for_ray(obj)
        
        assert result is not None
        assert hasattr(result, 'safe_data')
        assert hasattr(result, 'number')
        assert not hasattr(result, 'logger')
        assert not hasattr(result, 'thread')
    
    def test_trim_object_with_custom_exclude(self):
        """测试使用自定义排除列表清理对象"""
        class TestClass:
            def __init__(self):
                self.keep1 = "keep1"
                self.keep2 = "keep2"
                self.custom_exclude = "exclude_me"
                self.logger = "also_exclude"  # 默认排除
        
        obj = TestClass()
        result = trim_object_for_ray(obj, exclude=['custom_exclude'])
        
        assert result is not None
        assert hasattr(result, 'keep1')
        assert hasattr(result, 'keep2')
        assert not hasattr(result, 'custom_exclude')
        assert not hasattr(result, 'logger')  # 仍然被默认排除
    
    def test_trim_object_with_include_list(self):
        """测试使用包含列表清理对象"""
        class TestClass:
            def __init__(self):
                self.keep1 = "keep1"
                self.keep2 = "keep2"
                self.exclude1 = "exclude1"
                self.logger = "normally_excluded"
        
        obj = TestClass()
        result = trim_object_for_ray(obj, include=['keep1', 'logger'])
        
        assert result is not None
        assert hasattr(result, 'keep1')
        assert hasattr(result, 'logger')  # 被 include 覆盖
        assert not hasattr(result, 'keep2')
        assert not hasattr(result, 'exclude1')
    
    def test_trim_object_returns_none_for_skip_value(self):
        """测试清理返回 SKIP_VALUE 的情况"""
        # 创建一个完全由黑名单内容组成的对象
        thread = threading.Thread(target=lambda: None)
        
        # 直接传递黑名单对象
        result = trim_object_for_ray(thread)
        
        assert result is None
    
    @patch('sage.utils.serialization.ray_trimmer.preprocess_for_dill')
    def test_trim_object_error_handling(self, mock_preprocess):
        """测试清理过程中的错误处理"""
        mock_preprocess.side_effect = Exception("Processing failed")
        
        class TestClass:
            def __init__(self):
                self.data = "test"
        
        obj = TestClass()
        
        with pytest.raises(SerializationError, match="Object trimming for Ray failed"):
            trim_object_for_ray(obj)
    
    def test_trim_nested_object(self):
        """测试清理嵌套对象"""
        class NestedClass:
            def __init__(self):
                self.safe_data = "safe"
                self.logger = "should_be_removed"
        
        class ParentClass:
            def __init__(self):
                self.child = NestedClass()
                self.safe_attr = "parent_safe"
                self.server_socket = "should_be_removed"
        
        obj = ParentClass()
        result = trim_object_for_ray(obj)
        
        assert result is not None
        assert hasattr(result, 'child')
        assert hasattr(result, 'safe_attr')
        assert not hasattr(result, 'server_socket')
        
        # 检查嵌套对象也被清理
        assert hasattr(result.child, 'safe_data')
        assert not hasattr(result.child, 'logger')


class TestRayObjectTrimmer:
    """测试 RayObjectTrimmer 类"""
    
    def test_trim_for_remote_call_basic(self):
        """测试基本的远程调用清理"""
        class TestClass:
            def __init__(self):
                self.data = "test_data"
                self.logger = "should_be_removed"
        
        obj = TestClass()
        result = RayObjectTrimmer.trim_for_remote_call(obj)
        
        assert result is not None
        assert hasattr(result, 'data')
        assert not hasattr(result, 'logger')
    
    def test_trim_for_remote_call_shallow(self):
        """测试浅层清理"""
        class TestClass:
            def __init__(self):
                self.safe_data = "safe"
                self.logger = "remove"
                self.thread = threading.Thread(target=lambda: None)
        
        obj = TestClass()
        result = RayObjectTrimmer.trim_for_remote_call(obj, deep_clean=False)
        
        assert result is not None
        assert hasattr(result, 'safe_data')
        # 浅层清理应该移除基本的黑名单属性
        assert not hasattr(result, 'logger')
    
    def test_trim_for_remote_call_deep(self):
        """测试深度清理"""
        class NestedClass:
            def __init__(self):
                self.nested_data = "nested"
                self.logger = "remove"  # 使用标准的黑名单属性名
        
        class TestClass:
            def __init__(self):
                self.safe_data = "safe"
                self.nested = NestedClass()
                self.logger = "remove"
        
        obj = TestClass()
        result = RayObjectTrimmer.trim_for_remote_call(obj, deep_clean=True)
        
        assert result is not None
        assert hasattr(result, 'safe_data')
        assert hasattr(result, 'nested')
        assert not hasattr(result, 'logger')
        
        # 深度清理应该清理嵌套对象
        assert hasattr(result.nested, 'nested_data')
        assert not hasattr(result.nested, 'logger')
    
    def test_trim_for_remote_call_with_custom_filters(self):
        """测试使用自定义过滤器的远程调用清理"""
        class TestClass:
            def __init__(self):
                self.keep1 = "keep1"
                self.keep2 = "keep2"
                self.custom_remove = "remove"
                self.logger = "also_remove"
        
        obj = TestClass()
        result = RayObjectTrimmer.trim_for_remote_call(
            obj, 
            exclude=['custom_remove'],
            deep_clean=False
        )
        
        assert result is not None
        assert hasattr(result, 'keep1')
        assert hasattr(result, 'keep2')
        assert not hasattr(result, 'custom_remove')
        assert not hasattr(result, 'logger')
    
    def test_trim_transformation_for_ray(self):
        """测试 Transformation 对象的专用清理"""
        class MockTransformation:
            def __init__(self):
                self.name = "test_transform"
                self.config = {"param": "value"}
                self.data = [1, 2, 3]
                
                # 这些应该被清理掉
                self.logger = "fake_logger"
                self.env = "environment_ref"
                self.runtime_context = "runtime"
                self._dag_node_factory = "factory"
                self._operator_factory = "factory"
                self._function_factory = "factory"
                self.server_socket = "socket"
                self.server_thread = "thread"
        
        obj = MockTransformation()
        result = RayObjectTrimmer.trim_transformation_for_ray(obj)
        
        assert result is not None
        
        # 应该保留的属性
        assert hasattr(result, 'name')
        assert hasattr(result, 'config')
        assert hasattr(result, 'data')
        
        # 应该被清理的属性
        for attr in RAY_TRANSFORMATION_EXCLUDE_ATTRS:
            if hasattr(obj, attr):
                assert not hasattr(result, attr), f"Attribute {attr} should be excluded"
    
    def test_trim_operator_for_ray(self):
        """测试 Operator 对象的专用清理"""
        class MockOperator:
            def __init__(self):
                self.operator_id = "test_op"
                self.config = {"setting": "value"}
                self.state = "running"
                
                # 这些应该被清理掉
                self.logger = "fake_logger"
                self.runtime_context = "runtime"
                self.emit_context = "emit"
                self.server_socket = "socket"
                self.client_socket = "client_socket"
                self.server_thread = "thread"
                # 注意：__weakref__ 是只读属性，不能直接赋值
        
        obj = MockOperator()
        result = RayObjectTrimmer.trim_operator_for_ray(obj)
        
        assert result is not None
        
        # 应该保留的属性
        assert hasattr(result, 'operator_id')
        assert hasattr(result, 'config')
        assert hasattr(result, 'state')
        
        # 应该被清理的属性
        for attr in RAY_OPERATOR_EXCLUDE_ATTRS:
            if hasattr(obj, attr):
                assert not hasattr(result, attr), f"Attribute {attr} should be excluded"
    
    def test_validate_ray_serializable_success(self):
        """测试 Ray 序列化验证 - 成功情况"""
        # Mock ray 模块
        mock_ray = MagicMock()
        mock_ray.cloudpickle.dumps.return_value = b'serialized_data'
        
        with patch.dict('sys.modules', {'ray': mock_ray}):
            simple_obj = {'key': 'value', 'number': 42}
            result = RayObjectTrimmer.validate_ray_serializable(simple_obj)
            
            assert result['is_serializable'] is True
            assert result['size_estimate'] == len(b'serialized_data')
            assert len(result['issues']) == 0
    
    def test_validate_ray_serializable_failure(self):
        """测试 Ray 序列化验证 - 失败情况"""
        # Mock ray 模块抛出异常
        mock_ray = MagicMock()
        mock_ray.cloudpickle.dumps.side_effect = Exception("Serialization failed")
        
        with patch.dict('sys.modules', {'ray': mock_ray}):
            class ProblematicClass:
                def __init__(self):
                    self.safe_data = "safe"
                    self.thread = threading.Thread(target=lambda: None)
            
            obj = ProblematicClass()
            result = RayObjectTrimmer.validate_ray_serializable(obj)
            
            assert result['is_serializable'] is False
            assert len(result['issues']) > 0
            assert "Ray serialization failed" in result['issues'][0]
            assert result['size_estimate'] == 0
    
    def test_validate_ray_serializable_no_ray(self):
        """测试没有 Ray 时的序列化验证"""
        # 确保 ray 不在 sys.modules 中
        with patch.dict('sys.modules', {}, clear=True):
            # 移除 ray 如果存在
            if 'ray' in sys.modules:
                del sys.modules['ray']
            
            simple_obj = {'test': 'data'}
            result = RayObjectTrimmer.validate_ray_serializable(simple_obj)
            
            assert result['is_serializable'] is False
            assert 'Ray is not installed' in result['issues']
            assert result['size_estimate'] == 0
    
    def test_validate_ray_serializable_with_problematic_attrs(self):
        """测试验证包含问题属性的对象"""
        mock_ray = MagicMock()
        mock_ray.cloudpickle.dumps.side_effect = Exception("Cannot serialize")
        
        with patch.dict('sys.modules', {'ray': mock_ray}):
            class ObjectWithProblems:
                def __init__(self):
                    self.safe_attr = "safe"
                    self.thread = threading.Thread(target=lambda: None)
                    self.logger = "logger_obj"
            
            obj = ObjectWithProblems()
            result = RayObjectTrimmer.validate_ray_serializable(obj)
            
            assert result['is_serializable'] is False
            assert len(result['issues']) > 0
            
            # 应该识别出问题属性
            issues_text = ' '.join(result['issues'])
            assert 'thread' in issues_text or 'Problematic attribute' in issues_text


class TestRayTrimmerIntegration:
    """测试 Ray 清理器的集成功能"""
    
    def test_complex_object_trimming(self):
        """测试复杂对象的清理"""
        class ComplexTransformation:
            def __init__(self):
                # 保留的属性
                self.name = "complex_transform"
                self.config = {
                    'input_format': 'json',
                    'output_format': 'parquet',
                    'batch_size': 1000
                }
                self.operators = [
                    {'type': 'filter', 'condition': 'x > 0'},
                    {'type': 'transform', 'function': 'normalize'}
                ]
                self.metadata = {
                    'created_at': '2024-01-01',
                    'version': '1.0'
                }
                
                # 需要清理的属性
                self.logger = Mock()  # 模拟日志对象
                self.env = Mock()  # 模拟环境对象
                self.runtime_context = Mock()  # 模拟运行时上下文
                self._dag_node_factory = Mock()  # 模拟工厂对象
                self.server_socket = Mock()  # 模拟socket对象
                self.server_thread = threading.Thread(target=lambda: None)
        
        obj = ComplexTransformation()
        result = RayObjectTrimmer.trim_transformation_for_ray(obj)
        
        # 验证保留的属性
        assert result.name == "complex_transform"
        assert result.config['batch_size'] == 1000
        assert len(result.operators) == 2
        assert result.metadata['version'] == '1.0'
        
        # 验证清理的属性
        assert not hasattr(result, 'logger')
        assert not hasattr(result, 'env')
        assert not hasattr(result, 'runtime_context')
        assert not hasattr(result, '_dag_node_factory')
        assert not hasattr(result, 'server_socket')
        assert not hasattr(result, 'server_thread')
    
    def test_nested_complex_trimming(self):
        """测试嵌套复杂对象的清理"""
        class NestedComponent:
            def __init__(self):
                self.component_data = "nested_data"
                self.logger = "nested_logger"
        
        class MainObject:
            def __init__(self):
                self.main_data = "main"
                self.components = [
                    NestedComponent(),
                    NestedComponent()
                ]
                self.component_map = {
                    'comp1': NestedComponent(),
                    'comp2': NestedComponent()
                }
                self.server_thread = threading.Thread(target=lambda: None)
        
        obj = MainObject()
        result = trim_object_for_ray(obj)
        
        # 验证主对象
        assert hasattr(result, 'main_data')
        assert not hasattr(result, 'server_thread')
        
        # 验证嵌套列表中的对象
        assert len(result.components) == 2
        for comp in result.components:
            assert hasattr(comp, 'component_data')
            assert not hasattr(comp, 'logger')
        
        # 验证嵌套字典中的对象
        assert 'comp1' in result.component_map
        assert 'comp2' in result.component_map
        for comp in result.component_map.values():
            assert hasattr(comp, 'component_data')
            assert not hasattr(comp, 'logger')
    
    def test_performance_with_large_object(self):
        """测试大对象的清理性能"""
        class LargeObject:
            def __init__(self):
                # 创建大量安全属性
                for i in range(1000):
                    setattr(self, f'safe_attr_{i}', f'value_{i}')
                
                # 添加一些需要清理的属性
                self.logger = "logger"
                self.server_socket = "socket"
                self.thread = threading.Thread(target=lambda: None)
        
        obj = LargeObject()
        
        # 这应该能够快速完成而不会超时
        result = trim_object_for_ray(obj)
        
        # 验证清理效果
        assert result is not None
        assert not hasattr(result, 'logger')
        assert not hasattr(result, 'server_socket')
        assert not hasattr(result, 'thread')
        
        # 验证大部分安全属性被保留
        safe_attrs = [attr for attr in dir(result) if attr.startswith('safe_attr_')]
        assert len(safe_attrs) == 1000


if __name__ == "__main__":
    pytest.main([__file__])

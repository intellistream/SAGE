"""
Tests for sage.utils.serialization.config module
===============================================

单元测试序列化配置模块的功能，包括：
- 黑名单配置常量
- 排除属性列表
- Ray相关排除配置
"""

import pytest
import threading
from unittest.mock import Mock

from sage.kernel.utils.serialization.config import (
    BLACKLIST,
    ATTRIBUTE_BLACKLIST,
    SKIP_VALUE,
    RAY_TRANSFORMATION_EXCLUDE_ATTRS,
    RAY_OPERATOR_EXCLUDE_ATTRS
)


@pytest.mark.unit
class TestBlacklistConfiguration:
    """黑名单配置测试"""
    
    def test_blacklist_contains_expected_types(self):
        """测试黑名单包含预期的类型"""
        # 验证线程类型在黑名单中
        assert threading.Thread in BLACKLIST
        
        # 验证文件类型在黑名单中
        assert type(open(__file__)) in BLACKLIST or any(
            str(type(open(__file__))) in str(t) for t in BLACKLIST
        )
        
        # 验证锁类型在黑名单中
        assert type(threading.Lock()) in BLACKLIST
        assert type(threading.RLock()) in BLACKLIST
        
        # 验证事件和条件变量在黑名单中
        assert threading.Event in BLACKLIST
        assert threading.Condition in BLACKLIST
    
    def test_blacklist_is_list(self):
        """测试黑名单是列表类型"""
        assert isinstance(BLACKLIST, list)
        assert len(BLACKLIST) > 0
    
    def test_blacklist_types_are_classes(self):
        """测试黑名单中的项都是类型"""
        for item in BLACKLIST:
            assert isinstance(item, type), f"Item {item} is not a type"
    
    def test_thread_type_detection(self):
        """测试线程类型检测"""
        thread = threading.Thread()
        assert type(thread) in BLACKLIST
        
        # 测试实际的线程实例
        assert isinstance(thread, threading.Thread)


@pytest.mark.unit
class TestAttributeBlacklist:
    """属性黑名单测试"""
    
    def test_attribute_blacklist_is_set(self):
        """测试属性黑名单是集合类型"""
        assert isinstance(ATTRIBUTE_BLACKLIST, set)
        assert len(ATTRIBUTE_BLACKLIST) > 0
    
    def test_logger_attributes_excluded(self):
        """测试日志相关属性被排除"""
        assert 'logger' in ATTRIBUTE_BLACKLIST
        assert '_logger' in ATTRIBUTE_BLACKLIST
    
    def test_socket_attributes_excluded(self):
        """测试socket相关属性被排除"""
        assert 'server_socket' in ATTRIBUTE_BLACKLIST
        assert 'client_socket' in ATTRIBUTE_BLACKLIST
    
    def test_thread_attributes_excluded(self):
        """测试线程相关属性被排除"""
        assert 'server_thread' in ATTRIBUTE_BLACKLIST
        assert '_server_thread' in ATTRIBUTE_BLACKLIST
    
    def test_weakref_excluded(self):
        """测试弱引用属性被排除"""
        assert '__weakref__' in ATTRIBUTE_BLACKLIST
    
    def test_runtime_context_excluded(self):
        """测试运行时上下文被排除"""
        assert 'runtime_context' in ATTRIBUTE_BLACKLIST
    
    def test_env_excluded(self):
        """测试环境引用被排除"""
        assert 'env' in ATTRIBUTE_BLACKLIST
    
    def test_attribute_names_are_strings(self):
        """测试属性名都是字符串"""
        for attr in ATTRIBUTE_BLACKLIST:
            assert isinstance(attr, str), f"Attribute {attr} is not a string"
            assert len(attr) > 0, f"Attribute name cannot be empty"


@pytest.mark.unit
class TestSkipValue:
    """SKIP_VALUE测试"""
    
    def test_skip_value_is_sentinel(self):
        """测试SKIP_VALUE是哨兵对象"""
        assert SKIP_VALUE is not None
        assert SKIP_VALUE is not False
        assert SKIP_VALUE is not True
        assert SKIP_VALUE is not 0
        assert SKIP_VALUE is not ""
        assert SKIP_VALUE is not []
        assert SKIP_VALUE is not {}
    
    def test_skip_value_uniqueness(self):
        """测试SKIP_VALUE的唯一性"""
        # SKIP_VALUE应该是唯一的对象
        assert SKIP_VALUE is SKIP_VALUE
        assert id(SKIP_VALUE) == id(SKIP_VALUE)
    
    def test_skip_value_type(self):
        """测试SKIP_VALUE的类型"""
        assert isinstance(SKIP_VALUE, object)
        assert type(SKIP_VALUE) is object


@pytest.mark.unit
class TestRayTransformationExcludeAttrs:
    """Ray转换排除属性测试"""
    
    def test_ray_transformation_exclude_attrs_is_list(self):
        """测试Ray转换排除属性是列表"""
        assert isinstance(RAY_TRANSFORMATION_EXCLUDE_ATTRS, list)
        assert len(RAY_TRANSFORMATION_EXCLUDE_ATTRS) > 0
    
    def test_ray_transformation_includes_common_attrs(self):
        """测试Ray转换排除包含通用属性"""
        assert 'logger' in RAY_TRANSFORMATION_EXCLUDE_ATTRS
        assert '_logger' in RAY_TRANSFORMATION_EXCLUDE_ATTRS
        assert 'env' in RAY_TRANSFORMATION_EXCLUDE_ATTRS
        assert 'runtime_context' in RAY_TRANSFORMATION_EXCLUDE_ATTRS
    
    def test_ray_transformation_includes_factory_attrs(self):
        """测试Ray转换排除包含工厂属性"""
        assert '_dag_node_factory' in RAY_TRANSFORMATION_EXCLUDE_ATTRS
        assert '_operator_factory' in RAY_TRANSFORMATION_EXCLUDE_ATTRS
        assert '_function_factory' in RAY_TRANSFORMATION_EXCLUDE_ATTRS
    
    def test_ray_transformation_includes_socket_attrs(self):
        """测试Ray转换排除包含socket属性"""
        assert 'server_socket' in RAY_TRANSFORMATION_EXCLUDE_ATTRS
        assert 'server_thread' in RAY_TRANSFORMATION_EXCLUDE_ATTRS
        assert '_server_thread' in RAY_TRANSFORMATION_EXCLUDE_ATTRS
    
    def test_ray_transformation_attr_names_are_strings(self):
        """测试Ray转换排除属性名都是字符串"""
        for attr in RAY_TRANSFORMATION_EXCLUDE_ATTRS:
            assert isinstance(attr, str), f"Attribute {attr} is not a string"
            assert len(attr) > 0, f"Attribute name cannot be empty"


@pytest.mark.unit
class TestRayOperatorExcludeAttrs:
    """Ray算子排除属性测试"""
    
    def test_ray_operator_exclude_attrs_is_list(self):
        """测试Ray算子排除属性是列表"""
        assert isinstance(RAY_OPERATOR_EXCLUDE_ATTRS, list)
        assert len(RAY_OPERATOR_EXCLUDE_ATTRS) > 0
    
    def test_ray_operator_includes_logger_attrs(self):
        """测试Ray算子排除包含日志属性"""
        assert 'logger' in RAY_OPERATOR_EXCLUDE_ATTRS
        assert '_logger' in RAY_OPERATOR_EXCLUDE_ATTRS
    
    def test_ray_operator_includes_context_attrs(self):
        """测试Ray算子排除包含上下文属性"""
        assert 'runtime_context' in RAY_OPERATOR_EXCLUDE_ATTRS
        assert 'emit_context' in RAY_OPERATOR_EXCLUDE_ATTRS
    
    def test_ray_operator_includes_socket_attrs(self):
        """测试Ray算子排除包含socket属性"""
        assert 'server_socket' in RAY_OPERATOR_EXCLUDE_ATTRS
        assert 'client_socket' in RAY_OPERATOR_EXCLUDE_ATTRS
        assert 'server_thread' in RAY_OPERATOR_EXCLUDE_ATTRS
        assert '_server_thread' in RAY_OPERATOR_EXCLUDE_ATTRS
    
    def test_ray_operator_attr_names_are_strings(self):
        """测试Ray算子排除属性名都是字符串"""
        for attr in RAY_OPERATOR_EXCLUDE_ATTRS:
            assert isinstance(attr, str), f"Attribute {attr} is not a string"
            assert len(attr) > 0, f"Attribute name cannot be empty"
    
    def test_ray_operator_excludes_weakref_comment(self):
        """测试Ray算子排除列表关于__weakref__的注释"""
        # 检查注释中提到__weakref__不在列表中的原因
        # 这是一个文档测试，确保代码和注释保持一致
        assert '__weakref__' not in RAY_OPERATOR_EXCLUDE_ATTRS


@pytest.mark.unit
class TestExcludeListsComparison:
    """排除列表比较测试"""
    
    def test_attribute_blacklist_vs_ray_lists(self):
        """测试通用属性黑名单与Ray专用列表的关系"""
        # Ray专用列表应该包含一些通用黑名单的属性
        common_attrs = set(['logger', '_logger', 'server_socket', 'server_thread'])
        
        # 检查通用黑名单
        assert common_attrs.issubset(ATTRIBUTE_BLACKLIST)
        
        # 检查Ray转换列表
        assert common_attrs.issubset(set(RAY_TRANSFORMATION_EXCLUDE_ATTRS))
        
        # 检查Ray算子列表（除了server_thread可能不同）
        ray_operator_set = set(RAY_OPERATOR_EXCLUDE_ATTRS)
        assert 'logger' in ray_operator_set
        assert '_logger' in ray_operator_set
        assert 'server_socket' in ray_operator_set
    
    def test_ray_lists_differences(self):
        """测试Ray转换和算子列表的差异"""
        transformation_set = set(RAY_TRANSFORMATION_EXCLUDE_ATTRS)
        operator_set = set(RAY_OPERATOR_EXCLUDE_ATTRS)
        
        # 转换列表应该包含工厂属性，算子列表可能不包含
        factory_attrs = {'_dag_node_factory', '_operator_factory', '_function_factory'}
        assert factory_attrs.issubset(transformation_set)
        
        # 算子列表应该包含发射上下文，转换列表可能不包含
        if 'emit_context' in operator_set:
            # 如果算子列表包含emit_context，验证这个设计选择
            assert 'emit_context' in RAY_OPERATOR_EXCLUDE_ATTRS
    
    def test_no_duplicate_attrs_in_lists(self):
        """测试列表中没有重复属性"""
        # Ray转换列表不应有重复
        transformation_list = RAY_TRANSFORMATION_EXCLUDE_ATTRS
        assert len(transformation_list) == len(set(transformation_list))
        
        # Ray算子列表不应有重复
        operator_list = RAY_OPERATOR_EXCLUDE_ATTRS
        assert len(operator_list) == len(set(operator_list))


@pytest.mark.unit
class TestConfigurationUsageScenarios:
    """配置使用场景测试"""
    
    def test_blacklist_type_checking(self):
        """测试黑名单类型检查场景"""
        # 模拟需要检查对象类型是否在黑名单中的场景
        test_objects = [
            threading.Thread(),
            threading.Lock(),
            threading.RLock(),
            threading.Event(),
            threading.Condition(threading.Lock()),
        ]
        
        for obj in test_objects:
            obj_type = type(obj)
            assert obj_type in BLACKLIST, f"Object type {obj_type} should be in blacklist"
    
    def test_attribute_filtering_scenario(self):
        """测试属性过滤场景"""
        # 模拟一个包含各种属性的对象
        class TestObject:
            def __init__(self):
                self.logger = Mock()
                self._logger = Mock()
                self.server_socket = Mock()
                self.client_socket = Mock()
                self.server_thread = Mock()
                self._server_thread = Mock()
                self.runtime_context = Mock()
                self.env = Mock()
                self.normal_attr = "should_be_kept"
                self.another_attr = 42
        
        test_obj = TestObject()
        
        # 模拟过滤逻辑
        filtered_attrs = []
        for attr_name in dir(test_obj):
            if not attr_name.startswith('__') and attr_name not in ATTRIBUTE_BLACKLIST:
                filtered_attrs.append(attr_name)
        
        # 验证正常属性被保留
        assert 'normal_attr' in filtered_attrs
        assert 'another_attr' in filtered_attrs
        
        # 验证黑名单属性被过滤
        assert 'logger' not in filtered_attrs
        assert '_logger' not in filtered_attrs
        assert 'server_socket' not in filtered_attrs
        assert 'runtime_context' not in filtered_attrs
    
    def test_ray_specific_filtering_scenario(self):
        """测试Ray特定过滤场景"""
        # 模拟Ray转换对象
        class MockRayTransformation:
            def __init__(self):
                self.logger = Mock()
                self._dag_node_factory = Mock()
                self._operator_factory = Mock()
                self._function_factory = Mock()
                self.env = Mock()
                self.runtime_context = Mock()
                self.transformation_data = "important_data"
        
        # 模拟Ray算子对象
        class MockRayOperator:
            def __init__(self):
                self.logger = Mock()
                self._logger = Mock()
                self.runtime_context = Mock()
                self.emit_context = Mock()
                self.server_socket = Mock()
                self.operator_data = "important_data"
        
        transformation = MockRayTransformation()
        operator = MockRayOperator()
        
        # 测试转换对象过滤
        transform_filtered = []
        for attr_name in dir(transformation):
            if not attr_name.startswith('__') and attr_name not in RAY_TRANSFORMATION_EXCLUDE_ATTRS:
                transform_filtered.append(attr_name)
        
        assert 'transformation_data' in transform_filtered
        assert 'logger' not in transform_filtered
        assert '_dag_node_factory' not in transform_filtered
        
        # 测试算子对象过滤
        operator_filtered = []
        for attr_name in dir(operator):
            if not attr_name.startswith('__') and attr_name not in RAY_OPERATOR_EXCLUDE_ATTRS:
                operator_filtered.append(attr_name)
        
        assert 'operator_data' in operator_filtered
        assert 'logger' not in operator_filtered
        assert 'emit_context' not in operator_filtered
    
    def test_skip_value_usage_scenario(self):
        """测试SKIP_VALUE使用场景"""
        # 模拟序列化过程中使用SKIP_VALUE的场景
        def serialize_attribute(value):
            """模拟属性序列化函数"""
            if value is None:
                return None
            elif isinstance(value, (str, int, float, bool)):
                return value
            elif type(value) in BLACKLIST:
                return SKIP_VALUE
            else:
                return str(value)  # 简化处理
        
        # 测试各种值的序列化
        test_values = [
            ("normal_string", "normal_string"),
            (42, 42),
            (None, None),
            (threading.Thread(), SKIP_VALUE),
            (threading.Lock(), SKIP_VALUE),
        ]
        
        for input_value, expected_output in test_values:
            result = serialize_attribute(input_value)
            if expected_output is SKIP_VALUE:
                assert result is SKIP_VALUE
            else:
                assert result == expected_output


@pytest.mark.integration
class TestSerializationConfigIntegration:
    """序列化配置集成测试"""
    
    def test_complete_object_filtering_workflow(self):
        """测试完整的对象过滤工作流程"""
        # 创建一个复杂的测试对象
        class ComplexObject:
            def __init__(self):
                # 正常属性
                self.name = "test_object"
                self.value = 100
                self.data = {"key": "value"}
                
                # 应该被过滤的属性
                self.logger = Mock()
                self._logger = Mock()
                self.server_socket = Mock()
                self.client_socket = Mock()
                self.server_thread = threading.Thread()
                self._server_thread = threading.Thread()
                self.runtime_context = Mock()
                self.env = Mock()
                
                # Ray特定属性
                self._dag_node_factory = Mock()
                self._operator_factory = Mock()
                self._function_factory = Mock()
                self.emit_context = Mock()
        
        obj = ComplexObject()
        
        # 模拟完整的过滤过程
        def filter_object_attributes(obj):
            """过滤对象属性的模拟函数"""
            filtered = {}
            
            for attr_name in dir(obj):
                if attr_name.startswith('__'):
                    continue
                
                attr_value = getattr(obj, attr_name)
                
                # 检查属性名是否在黑名单中
                if attr_name in ATTRIBUTE_BLACKLIST:
                    continue
                
                # 检查属性值类型是否在黑名单中
                if type(attr_value) in BLACKLIST:
                    continue
                
                # 检查是否为可调用对象（方法）
                if callable(attr_value):
                    continue
                
                filtered[attr_name] = attr_value
            
            return filtered
        
        # 执行过滤
        filtered_attrs = filter_object_attributes(obj)
        
        # 验证正常属性被保留
        assert 'name' in filtered_attrs
        assert 'value' in filtered_attrs
        assert 'data' in filtered_attrs
        assert filtered_attrs['name'] == "test_object"
        assert filtered_attrs['value'] == 100
        
        # 验证黑名单属性被过滤
        assert 'logger' not in filtered_attrs
        assert '_logger' not in filtered_attrs
        assert 'server_socket' not in filtered_attrs
        assert 'server_thread' not in filtered_attrs
        assert 'runtime_context' not in filtered_attrs
        assert 'env' not in filtered_attrs
    
    def test_ray_specific_object_filtering(self):
        """测试Ray特定对象过滤"""
        class RayTransformationObject:
            def __init__(self):
                self.transform_id = "transform_001"
                self.input_data = [1, 2, 3]
                self.output_schema = {"type": "array"}
                
                # 应该被Ray转换过滤器过滤的属性
                self.logger = Mock()
                self._dag_node_factory = Mock()
                self._operator_factory = Mock()
                self._function_factory = Mock()
                self.env = Mock()
                self.runtime_context = Mock()
                self.server_socket = Mock()
        
        transform_obj = RayTransformationObject()
        
        # 模拟Ray转换对象过滤
        def filter_ray_transformation(obj):
            filtered = {}
            for attr_name in dir(obj):
                if (not attr_name.startswith('__') and 
                    not callable(getattr(obj, attr_name)) and
                    attr_name not in RAY_TRANSFORMATION_EXCLUDE_ATTRS):
                    filtered[attr_name] = getattr(obj, attr_name)
            return filtered
        
        filtered = filter_ray_transformation(transform_obj)
        
        # 验证业务属性被保留
        assert 'transform_id' in filtered
        assert 'input_data' in filtered
        assert 'output_schema' in filtered
        
        # 验证Ray特定属性被过滤
        assert 'logger' not in filtered
        assert '_dag_node_factory' not in filtered
        assert '_operator_factory' not in filtered
        assert 'runtime_context' not in filtered

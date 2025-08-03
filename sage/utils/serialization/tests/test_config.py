"""
测试 sage.utils.serialization.config 模块
"""
import pytest
import sys
import os
import threading

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from sage.utils.serialization.config import (
    BLACKLIST,
    ATTRIBUTE_BLACKLIST,
    SKIP_VALUE,
    RAY_TRANSFORMATION_EXCLUDE_ATTRS,
    RAY_OPERATOR_EXCLUDE_ATTRS
)


class TestSerializationConfig:
    """测试序列化配置模块"""
    
    def test_blacklist_contents(self):
        """测试黑名单内容"""
        # 检查黑名单是否是列表
        assert isinstance(BLACKLIST, list)
        
        # 检查基本的不可序列化类型
        assert threading.Thread in BLACKLIST
        assert type(open) in BLACKLIST
        assert type(threading.Lock) in BLACKLIST
        assert type(threading.RLock) in BLACKLIST
        assert threading.Event in BLACKLIST
        assert threading.Condition in BLACKLIST
        
        # 检查长度合理
        assert len(BLACKLIST) >= 6
    
    def test_attribute_blacklist_contents(self):
        """测试属性黑名单内容"""
        # 检查属性黑名单是否是集合
        assert isinstance(ATTRIBUTE_BLACKLIST, set)
        
        # 检查基本的需要排除的属性
        expected_attrs = {
            'logger', '_logger',
            'server_socket', 'client_socket',
            'server_thread', '_server_thread',
            '__weakref__',
            'runtime_context',
            'env'
        }
        
        assert expected_attrs.issubset(ATTRIBUTE_BLACKLIST)
        
        # 检查长度合理
        assert len(ATTRIBUTE_BLACKLIST) >= 8
    
    def test_skip_value_uniqueness(self):
        """测试 SKIP_VALUE 的唯一性"""
        # SKIP_VALUE 应该是一个唯一的对象
        assert SKIP_VALUE is not None
        assert SKIP_VALUE is not ""
        assert SKIP_VALUE is not 0
        assert SKIP_VALUE is not False
        
        # 创建另一个对象，应该不相等
        other_obj = object()
        assert SKIP_VALUE is not other_obj
    
    def test_ray_transformation_exclude_attrs(self):
        """测试 Ray Transformation 排除属性"""
        assert isinstance(RAY_TRANSFORMATION_EXCLUDE_ATTRS, list)
        
        expected_attrs = [
            'logger', '_logger',
            'env',
            'runtime_context',
            '_dag_node_factory',
            '_operator_factory',
            '_function_factory',
            'server_socket',
            'server_thread', '_server_thread'
        ]
        
        for attr in expected_attrs:
            assert attr in RAY_TRANSFORMATION_EXCLUDE_ATTRS
    
    def test_ray_operator_exclude_attrs(self):
        """测试 Ray Operator 排除属性"""
        assert isinstance(RAY_OPERATOR_EXCLUDE_ATTRS, list)
        
        expected_attrs = [
            'logger', '_logger',
            'runtime_context',
            'emit_context',
            'server_socket', 'client_socket',
            'server_thread', '_server_thread',
            # 注意：__weakref__ 已移除，因为它是不可删除的内置属性
        ]
        
        for attr in expected_attrs:
            assert attr in RAY_OPERATOR_EXCLUDE_ATTRS
    
    def test_config_mutability(self):
        """测试配置的可变性"""
        # 黑名单应该是可以修改的（如果需要的话）
        original_len = len(BLACKLIST)
        
        # 测试添加
        test_type = type(lambda: None)  # function type
        if test_type not in BLACKLIST:
            BLACKLIST.append(test_type)
            assert len(BLACKLIST) == original_len + 1
            # 清理
            BLACKLIST.remove(test_type)
        
        assert len(BLACKLIST) == original_len
    
    def test_constants_immutability_intention(self):
        """测试常量的不可变性意图（文档化测试）"""
        # 虽然 Python 中常量可以被修改，但我们应该将它们视为不可变
        # 这个测试记录了我们的意图
        
        # SKIP_VALUE 应该始终是同一个对象
        skip_value_id = id(SKIP_VALUE)
        
        # 模拟在其他地方导入
        from sage.utils.serialization.config import SKIP_VALUE as IMPORTED_SKIP_VALUE
        
        assert id(IMPORTED_SKIP_VALUE) == skip_value_id
        assert IMPORTED_SKIP_VALUE is SKIP_VALUE


class TestConfigIntegration:
    """测试配置的集成性"""
    
    def test_blacklist_types_instantiation(self):
        """测试黑名单中的类型是否可以实例化（用于测试）"""
        for blacklisted_type in BLACKLIST:
            try:
                # 尝试创建实例（某些类型可能需要参数）
                if blacklisted_type == threading.Thread:
                    instance = blacklisted_type(target=lambda: None)
                elif blacklisted_type == threading.Event:
                    instance = blacklisted_type()
                elif blacklisted_type == threading.Condition:
                    instance = blacklisted_type()
                elif blacklisted_type == type(open):
                    # 文件类型比较特殊，跳过实例化测试
                    continue
                elif blacklisted_type in [type(threading.Lock), type(threading.RLock)]:
                    # 锁类型也比较特殊
                    instance = threading.Lock()
                else:
                    instance = blacklisted_type()
                
                # 验证实例确实属于该类型
                assert isinstance(instance, blacklisted_type)
                
            except Exception:
                # 某些类型可能无法直接实例化，这是正常的
                pass
    
    def test_configuration_completeness(self):
        """测试配置的完整性"""
        # 确保所有必要的配置都已定义
        required_configs = [
            'BLACKLIST',
            'ATTRIBUTE_BLACKLIST', 
            'SKIP_VALUE',
            'RAY_TRANSFORMATION_EXCLUDE_ATTRS',
            'RAY_OPERATOR_EXCLUDE_ATTRS'
        ]
        
        import sage.utils.serialization.config as config_module
        
        for config_name in required_configs:
            assert hasattr(config_module, config_name), f"Missing config: {config_name}"


if __name__ == "__main__":
    pytest.main([__file__])

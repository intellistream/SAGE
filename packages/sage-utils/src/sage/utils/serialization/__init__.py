"""
Sage序列化工具包

这个包提供了基于dill的通用序列化功能，以及专门为Ray远程调用优化的对象清理功能。

主要模块:
- universal_serializer: 通用序列化器
- ray_trimmer: Ray对象清理器
- preprocessor: 对象预处理器
- config: 配置和常量
- exceptions: 异常定义

便捷函数（向后兼容）:
- serialize_object / deserialize_object
- save_object_state / load_object_state / load_object_from_file
- pack_object / unpack_object (向后兼容)
- trim_object_for_ray

使用示例:
    # 基本序列化
    data = serialize_object(my_object)
    restored_obj = deserialize_object(data)
    
    # 保存/加载状态
    save_object_state(my_object, "state.pkl")
    loaded_obj = load_object_from_file("state.pkl")
    
    # Ray清理
    cleaned_obj = trim_object_for_ray(my_object, exclude=['logger', 'env'])
"""

# 导入所有公共API
from .exceptions import SerializationError
from .universal_serializer import UniversalSerializer
from .ray_trimmer import RayObjectTrimmer, trim_object_for_ray
from .config import (
    BLACKLIST, ATTRIBUTE_BLACKLIST, SKIP_VALUE,
    RAY_TRANSFORMATION_EXCLUDE_ATTRS, RAY_OPERATOR_EXCLUDE_ATTRS
)

# 便捷函数
def serialize_object(obj, include=None, exclude=None):
    """序列化对象的便捷函数"""
    return UniversalSerializer.serialize_object(obj, include, exclude)


def deserialize_object(data):
    """反序列化对象的便捷函数"""
    return UniversalSerializer.deserialize_object(data)


def save_object_state(obj, path, include=None, exclude=None):
    """保存对象状态的便捷函数"""
    return UniversalSerializer.save_object_state(obj, path, include, exclude)


def load_object_from_file(path):
    """从文件加载对象的便捷函数"""
    return UniversalSerializer.load_object_from_file(path)


def load_object_state(obj, path):
    """加载对象状态的便捷函数"""
    return UniversalSerializer.load_object_state(obj, path)


# 向后兼容的函数
def pack_object(obj, include=None, exclude=None):
    """打包对象的便捷函数（向后兼容）"""
    return serialize_object(obj, include, exclude)


def unpack_object(data):
    """解包对象的便捷函数（向后兼容）"""
    return deserialize_object(data)


# 导出所有公共接口
__all__ = [
    # 异常
    'SerializationError',
    
    # 主要类
    'UniversalSerializer',
    'RayObjectTrimmer',
    
    # 便捷函数
    'serialize_object',
    'deserialize_object', 
    'save_object_state',
    'load_object_from_file',
    'load_object_state',
    
    # 向后兼容
    'pack_object',
    'unpack_object',
    
    # Ray相关
    'trim_object_for_ray',
    
    # 配置常量
    'BLACKLIST',
    'ATTRIBUTE_BLACKLIST', 
    'SKIP_VALUE',
    'RAY_TRANSFORMATION_EXCLUDE_ATTRS',
    'RAY_OPERATOR_EXCLUDE_ATTRS',
]
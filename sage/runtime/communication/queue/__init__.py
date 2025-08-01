"""
Sage Runtime Communication Module

统一的通信系统，提供队列描述符和各种通信方式的抽象。

重要说明：
- v2.0+ 版本使用统一的 QueueDescriptor 架构
- queue_stubs 模块已废弃，建议使用迁移工具迁移到新架构
- 提供向后兼容包装器以便平滑迁移
"""

import warnings

from .queue_descriptor import (
    QueueDescriptor,
    resolve_descriptor,
    create_descriptor_from_existing_queue,
    # 便利函数
    get_local_queue,
    attach_to_shm_queue,
    get_ray_actor_queue,
    get_ray_queue,
    get_rpc_queue,
    get_sage_queue,
    # 批量操作
    create_queue_pool,
    serialize_queue_pool,
    deserialize_queue_pool,
)

# 迁移工具
from .migration_guide import (
    QueueMigrationHelper,
    migrate_queue_pool,
    quick_migrate,
    LegacyQueueStubWrapper,
    create_legacy_wrapper,
)

__all__ = [
    # 核心类
    'QueueDescriptor',
    
    # 核心函数
    'resolve_descriptor',
    'create_descriptor_from_existing_queue',
    
    # 便利函数
    'get_local_queue',
    'attach_to_shm_queue',
    'get_ray_actor_queue',
    'get_ray_queue',
    'get_rpc_queue',
    'get_sage_queue',
    
    # 批量操作
    'create_queue_pool',
    'serialize_queue_pool',
    'deserialize_queue_pool',
    
    # 迁移工具
    'QueueMigrationHelper',
    'migrate_queue_pool',
    'quick_migrate',
    'LegacyQueueStubWrapper',
    'create_legacy_wrapper',
]

# 向后兼容性：提供旧的 queue_stubs 导入路径
def _import_deprecated_stubs():
    """处理对已废弃 queue_stubs 模块的导入"""
    warnings.warn(
        "queue_stubs module is deprecated since version 2.0. "
        "Please use QueueDescriptor unified architecture instead. "
        "Use migration_guide tools for smooth migration.",
        DeprecationWarning,
        stacklevel=3
    )
    
    # 返回兼容性包装器
    return type('DeprecatedStubs', (), {
        'SageQueueStub': lambda desc: LegacyQueueStubWrapper(desc),
        'LocalQueueStub': lambda desc: LegacyQueueStubWrapper(desc),
        'SharedMemoryQueueStub': lambda desc: LegacyQueueStubWrapper(desc),
        'RayQueueStub': lambda desc: LegacyQueueStubWrapper(desc),
    })

# 为向后兼容性提供 queue_stubs 导入
try:
    import sys
    sys.modules[f"{__name__}.queue_stubs"] = _import_deprecated_stubs()
except Exception:
    pass  # 忽略导入错误

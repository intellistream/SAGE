"""
SAGE Communication Framework 初始化模块

提供通信框架的统一入口和配置管理
"""

from .message_bus import (
    CommunicationBus, Message, MessageType, CommunicationPattern,
    get_communication_bus, shutdown_communication_bus
)

from .service_base import (
    BaseService, ServiceFunction, FunctionClient, ServiceManager,
    get_service_manager
)

from .migration_adapter import (
    LegacyQueueAdapter, ServiceAdapter, MigrationHelper,
    get_migration_helper, create_queue_adapter, migrate_service
)

__all__ = [
    # Message Bus
    'CommunicationBus',
    'Message',
    'MessageType',
    'CommunicationPattern',
    'get_communication_bus',
    'shutdown_communication_bus',

    # Service Base
    'BaseService',
    'ServiceFunction',
    'FunctionClient',
    'ServiceManager',
    'get_service_manager',

    # Migration Support
    'LegacyQueueAdapter',
    'ServiceAdapter',
    'MigrationHelper',
    'get_migration_helper',
    'create_queue_adapter',
    'migrate_service'
]

# 版本信息
__version__ = "1.0.0"
__author__ = "SAGE Team"

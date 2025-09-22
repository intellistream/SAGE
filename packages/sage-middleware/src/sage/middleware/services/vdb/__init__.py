"""
VDB Service Module
向量数据库服务模块
"""

from .vdb_service import VDBService, create_vdb_service_factory

__all__ = ["VDBService", "create_vdb_service_factory"]

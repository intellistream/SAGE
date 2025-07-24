#!/usr/bin/env python3
"""
测试新的service系统
"""

import logging
from sage_core.environment.base_environment import BaseEnvironment

# 设置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 定义一个简单的服务类
class MockDataService:
    """模拟数据服务"""
    
    def __init__(self, db_url="sqlite://memory", max_connections=10):
        self.db_url = db_url
        self.max_connections = max_connections
        self.connected = False
        logger.info(f"MockDataService initialized with db_url={db_url}, max_connections={max_connections}")
    
    def connect(self):
        """连接数据库"""
        self.connected = True
        logger.info(f"Connected to database: {self.db_url}")
    
    def get_data(self, query):
        """获取数据"""
        if not self.connected:
            self.connect()
        logger.info(f"Executing query: {query}")
        return f"Result for: {query}"
    
    def start_running(self):
        """启动服务"""
        self.connect()
        logger.info("MockDataService started running")
    
    def stop(self):
        """停止服务"""
        self.connected = False
        logger.info("MockDataService stopped")
    
    def cleanup(self):
        """清理资源"""
        self.stop()
        logger.info("MockDataService cleaned up")
    
    def get_statistics(self):
        """获取统计信息"""
        return {
            "service_name": "MockDataService",
            "db_url": self.db_url,
            "max_connections": self.max_connections,
            "connected": self.connected
        }

class MockCacheService:
    """模拟缓存服务"""
    
    def __init__(self, cache_size=1000, ttl=3600):
        self.cache_size = cache_size
        self.ttl = ttl
        self.cache = {}
        logger.info(f"MockCacheService initialized with cache_size={cache_size}, ttl={ttl}")
    
    def get(self, key):
        """获取缓存"""
        return self.cache.get(key)
    
    def set(self, key, value):
        """设置缓存"""
        self.cache[key] = value
        logger.info(f"Cached: {key} = {value}")
    
    def start_running(self):
        """启动服务"""
        logger.info("MockCacheService started running")
    
    def stop(self):
        """停止服务"""
        logger.info("MockCacheService stopped")
    
    def cleanup(self):
        """清理资源"""
        self.cache.clear()
        logger.info("MockCacheService cleaned up")
    
    def get_statistics(self):
        """获取统计信息"""
        return {
            "service_name": "MockCacheService",
            "cache_size": self.cache_size,
            "ttl": self.ttl,
            "items_count": len(self.cache)
        }

def test_service_registration():
    """测试服务注册"""
    logger.info("=== Testing Service Registration ===")
    
    # 创建环境
    env = BaseEnvironment(remote=False)
    
    # 注册服务
    env.register_service(
        "data_service", 
        MockDataService, 
        db_url="postgresql://localhost/test",
        max_connections=20
    )
    
    env.register_service(
        "cache_service",
        MockCacheService,
        cache_size=2000,
        ttl=7200
    )
    
    # 检查是否正确注册
    assert "data_service" in env.service_factories
    assert "cache_service" in env.service_factories
    assert "data_service" in env.service_task_factories
    assert "cache_service" in env.service_task_factories
    
    logger.info(f"Registered service factories: {list(env.service_factories.keys())}")
    logger.info(f"Registered service task factories: {list(env.service_task_factories.keys())}")
    
    # 测试ServiceFactory创建服务实例
    logger.info("\n--- Testing ServiceFactory ---")
    data_service_factory = env.service_factories["data_service"]
    data_service_instance = data_service_factory.create_service()
    
    logger.info(f"Created service instance: {data_service_instance}")
    logger.info(f"Service db_url: {data_service_instance.db_url}")
    logger.info(f"Service max_connections: {data_service_instance.max_connections}")
    
    # 测试ServiceTaskFactory创建服务任务
    logger.info("\n--- Testing ServiceTaskFactory (Local) ---")
    data_service_task_factory = env.service_task_factories["data_service"]
    data_service_task = data_service_task_factory.create_service_task()
    
    logger.info(f"Created service task: {data_service_task}")
    logger.info(f"Service task type: {type(data_service_task)}")
    
    # 测试服务任务操作
    logger.info("\n--- Testing Service Task Operations ---")
    data_service_task.start_running()
    stats = data_service_task.get_statistics()
    logger.info(f"Service statistics: {stats}")
    data_service_task.stop()
    data_service_task.cleanup()
    
    logger.info("=== Service Registration Test Completed Successfully ===\n")

def test_remote_service():
    """测试远程服务（使用Ray）"""
    logger.info("=== Testing Remote Service ===")
    
    try:
        import ray
        
        # 初始化Ray（如果尚未初始化）
        if not ray.is_initialized():
            ray.init()
        
        # 创建远程环境
        env = BaseEnvironment(remote=True)
        
        # 注册远程服务
        env.register_service(
            "remote_data_service",
            MockDataService,
            db_url="postgresql://remote/test",
            max_connections=50
        )
        
        # 创建远程服务任务
        logger.info("\n--- Testing Remote ServiceTaskFactory ---")
        remote_service_task_factory = env.service_task_factories["remote_data_service"]
        remote_service_task = remote_service_task_factory.create_service_task()
        
        logger.info(f"Created remote service task: {remote_service_task}")
        logger.info(f"Remote service task type: {type(remote_service_task)}")
        logger.info(f"Is ActorWrapper: {hasattr(remote_service_task, '_actor')}")
        
        # 测试远程服务任务操作
        logger.info("\n--- Testing Remote Service Task Operations ---")
        
        # 启动服务
        remote_service_task.start_running()
        
        # 获取统计信息（需要等待异步操作）
        import time
        time.sleep(1)  # 等待Ray actor启动
        
        try:
            stats = remote_service_task.get_statistics()
            logger.info(f"Remote service statistics: {stats}")
        except Exception as e:
            logger.warning(f"Failed to get remote service statistics: {e}")
        
        # 清理
        remote_service_task.cleanup()
        
        logger.info("=== Remote Service Test Completed Successfully ===\n")
        
    except ImportError:
        logger.warning("Ray not available, skipping remote service test")
    except Exception as e:
        logger.error(f"Remote service test failed: {e}")

if __name__ == "__main__":
    # 运行测试
    test_service_registration()
    test_remote_service()
    
    logger.info("All tests completed!")

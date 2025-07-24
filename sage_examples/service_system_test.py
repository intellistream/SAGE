"""
服务系统使用示例

这个文件展示了如何使用新的Service系统来创建和管理服务。
"""

from sage_core.api.local_environment import LocalEnvironment


class MockService:
    """
    模拟服务类
    
    用于测试服务系统的基本功能
    """
    
    def __init__(self, service_id: str, config: dict = None):
        self.service_id = service_id
        self.config = config or {}
        self.is_running = False
        self.ctx = None
    
    def start_running(self):
        """启动服务"""
        self.is_running = True
        print(f"Service {self.service_id} started")
    
    def terminate(self):
        """终止服务"""
        self.is_running = False
        print(f"Service {self.service_id} terminated")
    
    def process_data(self, data):
        """处理数据"""
        return f"Service {self.service_id} processed: {data}"


class DatabaseService(MockService):
    """
    数据库服务示例
    """
    
    def __init__(self, db_name: str, host: str = "localhost", port: int = 5432):
        super().__init__(f"db_{db_name}")
        self.db_name = db_name
        self.host = host
        self.port = port
        self.connections = []
    
    def start_running(self):
        super().start_running()
        print(f"Database {self.db_name} connected to {self.host}:{self.port}")
    
    def query(self, sql: str):
        if not self.is_running:
            return "Database not running"
        return f"Query result for: {sql}"


class CacheService(MockService):
    """
    缓存服务示例
    """
    
    def __init__(self, cache_size: int = 1000):
        super().__init__("cache")
        self.cache_size = cache_size
        self.cache = {}
    
    def get(self, key: str):
        return self.cache.get(key, None)
    
    def set(self, key: str, value):
        if len(self.cache) >= self.cache_size:
            # 简单的LRU策略
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value


class ServiceSystemExample:
    """
    服务系统使用示例类
    """
    
    @staticmethod
    def example_usage():
        """
        服务系统使用示例
        """
        print("=== 服务系统使用示例 ===")
        
        try:
            # 1. 创建本地环境
            print("\n1. 创建本地环境:")
            env = LocalEnvironment("service_test_env")
            print(f"环境创建成功: {env}")
            
            # 2. 注册服务
            print("\n2. 注册服务:")
            
            # 注册数据库服务
            env.register_service(
                "database", 
                DatabaseService, 
                "test_db", 
                host="localhost", 
                port=5432
            )
            print("数据库服务注册成功")
            
            # 注册缓存服务
            env.register_service(
                "cache", 
                CacheService, 
                cache_size=500
            )
            print("缓存服务注册成功")
            
            # 注册基础服务
            env.register_service(
                "basic", 
                MockService, 
                "basic_service",
                config={"timeout": 30}
            )
            print("基础服务注册成功")
            
            # 3. 检查注册的服务
            print(f"\n3. 已注册的服务工厂: {len(env.service_factories)}")
            for name in env.service_factories:
                print(f"  - {name}")
            
            print(f"已注册的服务任务工厂: {len(env.service_task_factories)}")
            for name in env.service_task_factories:
                print(f"  - {name}")
            
            # 4. 测试服务创建
            print("\n4. 测试服务工厂:")
            
            # 测试ServiceFactory
            db_factory = env.service_factories["database"]
            print(f"数据库工厂: {db_factory}")
            
            # 创建服务实例
            db_instance = db_factory.create_service()
            print(f"创建的数据库实例: {db_instance}")
            print(f"数据库名: {db_instance.db_name}")
            print(f"数据库主机: {db_instance.host}:{db_instance.port}")
            
            # 测试ServiceTaskFactory
            db_task_factory = env.service_task_factories["database"]
            print(f"数据库任务工厂: {db_task_factory}")
            
            # 创建服务任务
            db_task = db_task_factory.create_service_task()
            print(f"创建的数据库任务: {db_task}")
            
            # 启动服务任务
            db_task.start_running()
            
            # 测试服务功能
            result = db_task.service.query("SELECT * FROM users")
            print(f"查询结果: {result}")
            
            # 终止服务
            db_task.terminate()
            
            print("\n=== 示例完成 ===")
            
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # 运行示例
    ServiceSystemExample.example_usage()

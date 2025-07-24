"""
服务语法糖测试

测试在算子内通过call_service和call_service_async调用服务的功能
"""

from sage_core.function.base_function import BaseFunction
from sage_core.api.local_environment import LocalEnvironment


class CacheService:
    """缓存服务"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.is_running = False
        self.ctx = None
    
    def start_running(self):
        self.is_running = True
        print(f"Cache service started with max_size={self.max_size}")
    
    def terminate(self):
        self.is_running = False
        print("Cache service terminated")
    
    def get(self, key: str):
        """获取缓存值"""
        result = self.cache.get(key, None)
        print(f"Cache GET {key}: {result}")
        return result
    
    def set(self, key: str, value):
        """设置缓存值"""
        if len(self.cache) >= self.max_size:
            # 简单的LRU策略
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value
        print(f"Cache SET {key}: {value}")
        return True
    
    def size(self):
        """获取缓存大小"""
        return len(self.cache)


class DatabaseService:
    """数据库服务"""
    
    def __init__(self, db_name: str = "test_db"):
        self.db_name = db_name
        self.data = {
            "users": [
                {"id": 1, "name": "Alice", "age": 25},
                {"id": 2, "name": "Bob", "age": 30},
                {"id": 3, "name": "Charlie", "age": 35}
            ],
            "products": [
                {"id": 1, "name": "Laptop", "price": 1000},
                {"id": 2, "name": "Mouse", "price": 20},
            ]
        }
        self.is_running = False
        self.ctx = None
    
    def start_running(self):
        self.is_running = True
        print(f"Database service started: {self.db_name}")
    
    def terminate(self):
        self.is_running = False
        print(f"Database service terminated: {self.db_name}")
    
    def query(self, table: str, filter_key: str = None, filter_value = None):
        """查询数据"""
        if not self.is_running:
            return {"error": "Database not running"}
        
        if table not in self.data:
            return {"error": f"Table {table} not found"}
        
        result = self.data[table]
        
        # 简单过滤
        if filter_key and filter_value is not None:
            result = [row for row in result if row.get(filter_key) == filter_value]
        
        print(f"DB Query {table} where {filter_key}={filter_value}: {len(result)} rows")
        return {"data": result, "count": len(result)}
    
    def insert(self, table: str, record: dict):
        """插入数据"""
        if not self.is_running:
            return {"error": "Database not running"}
        
        if table not in self.data:
            self.data[table] = []
        
        # 生成简单ID
        max_id = max([row.get("id", 0) for row in self.data[table]], default=0)
        record["id"] = max_id + 1
        
        self.data[table].append(record)
        print(f"DB Insert into {table}: {record}")
        return {"success": True, "id": record["id"]}


class ProcessFunction(BaseFunction):
    """处理函数，展示如何在算子内调用服务"""
    
    def __init__(self, function_name: str):
        super().__init__()
        self.function_name = function_name
    
    def execute(self, data):
        """执行处理逻辑，同时调用各种服务"""
        self.logger.info(f"Processing data in {self.function_name}: {data}")
        
        result = {
            "input": data,
            "processed_by": self.function_name,
            "services_used": []
        }
        
        try:
            # 1. 同步调用缓存服务
            self.logger.info("Testing cache service...")
            
            # 检查缓存
            cached = self.call_service["cache"].get(f"data_{data.get('id', 'unknown')}")
            if cached:
                self.logger.info(f"Found cached result: {cached}")
                result["from_cache"] = True
                result["cached_data"] = cached
            else:
                self.logger.info("No cached result found")
                result["from_cache"] = False
            
            # 设置缓存
            cache_key = f"processed_{data.get('id', 'unknown')}"
            self.call_service["cache"].set(cache_key, result)
            
            # 获取缓存大小
            cache_size = self.call_service["cache"].size()
            result["cache_size"] = cache_size
            result["services_used"].append("cache")
            
            # 2. 同步调用数据库服务
            self.logger.info("Testing database service...")
            
            # 查询用户数据
            users = self.call_service["database"].query("users")
            result["users_count"] = users.get("count", 0)
            result["services_used"].append("database")
            
            # 根据输入数据查询特定用户
            if "user_id" in data:
                user = self.call_service["database"].query("users", "id", data["user_id"])
                result["specific_user"] = user.get("data", [])
            
            # 插入处理记录
            process_record = {
                "function": self.function_name,
                "input": str(data),
                "timestamp": "2025-07-24 06:15:00"
            }
            
            # 如果没有process_logs表就会自动创建
            insert_result = self.call_service["database"].insert("process_logs", process_record)
            result["log_inserted"] = insert_result.get("success", False)
            
            self.logger.info(f"Processing completed successfully: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error during processing: {e}")
            result["error"] = str(e)
            return result


class AsyncProcessFunction(BaseFunction):
    """异步处理函数，展示异步服务调用"""
    
    def __init__(self, function_name: str):
        super().__init__()
        self.function_name = function_name
    
    def execute(self, data):
        """执行异步处理逻辑"""
        self.logger.info(f"Async processing data in {self.function_name}: {data}")
        
        result = {
            "input": data,
            "processed_by": self.function_name,
            "async_results": []
        }
        
        try:
            # 异步调用多个服务
            self.logger.info("Testing async service calls...")
            
            # 启动异步调用
            cache_future = self.call_service_async["cache"].get(f"async_{data.get('id', 'test')}")
            db_future = self.call_service_async["database"].query("products")
            
            # 等待结果
            self.logger.info("Waiting for async results...")
            
            # 获取缓存结果
            cache_result = cache_future.result() if hasattr(cache_future, 'result') else cache_future
            result["async_cache_result"] = cache_result
            result["async_results"].append("cache")
            
            # 获取数据库结果
            db_result = db_future.result() if hasattr(db_future, 'result') else db_future
            result["async_db_result"] = db_result
            result["async_results"].append("database")
            
            self.logger.info(f"Async processing completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error during async processing: {e}")
            result["error"] = str(e)
            return result


def test_service_syntax():
    """测试服务语法糖功能"""
    print("=== 服务语法糖测试 ===")
    
    try:
        # 1. 创建环境并注册服务
        print("\n1. 创建环境并注册服务:")
        env = LocalEnvironment("service_syntax_test")
        
        # 注册缓存服务
        env.register_service("cache", CacheService, max_size=100)
        print("缓存服务注册完成")
        
        # 注册数据库服务
        env.register_service("database", DatabaseService, db_name="test_service_db")
        print("数据库服务注册完成")
        
        # 2. 启动服务
        print("\n2. 启动服务:")
        services = {}
        for service_name in env.service_task_factories:
            task_factory = env.service_task_factories[service_name]
            service_task = task_factory.create_service_task()
            service_task.start_running()
            services[service_name] = service_task
            print(f"服务 {service_name} 启动完成")
        
        # 3. 创建模拟的运行时上下文
        print("\n3. 创建运行时上下文:")
        
        class MockServiceManager:
            def __init__(self, services):
                self.services = services
            
            def get_sync_proxy(self, service_name: str):
                if service_name in self.services:
                    return self.services[service_name].service
                raise KeyError(f"Service {service_name} not found")
            
            def get_async_proxy(self, service_name: str):
                # 简化版异步代理，实际上还是同步调用
                return self.get_sync_proxy(service_name)
        
        class MockRuntimeContext:
            def __init__(self, name, services):
                self.name = name
                self.service_manager = MockServiceManager(services)
                import logging
                self.logger = logging.getLogger(name)
        
        # 4. 测试同步服务调用
        print("\n4. 测试同步服务调用:")
        
        sync_func = ProcessFunction("sync_processor")
        sync_func.ctx = MockRuntimeContext("sync_processor", services)
        
        test_data = {"id": 123, "name": "test_item", "user_id": 2}
        sync_result = sync_func.execute(test_data)
        
        print(f"同步处理结果:")
        for key, value in sync_result.items():
            print(f"  {key}: {value}")
        
        # 5. 测试异步服务调用
        print("\n5. 测试异步服务调用:")
        
        async_func = AsyncProcessFunction("async_processor")
        async_func.ctx = MockRuntimeContext("async_processor", services)
        
        async_data = {"id": 456, "type": "async_test"}
        async_result = async_func.execute(async_data)
        
        print(f"异步处理结果:")
        for key, value in async_result.items():
            print(f"  {key}: {value}")
        
        # 6. 测试错误处理
        print("\n6. 测试错误处理:")
        
        try:
            # 尝试调用不存在的服务
            sync_func.call_service["nonexistent"].some_method()
        except Exception as e:
            print(f"期望的错误: {e}")
        
        # 7. 关闭服务
        print("\n7. 关闭服务:")
        for service_name, service_task in services.items():
            service_task.terminate()
            print(f"服务 {service_name} 已关闭")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_service_syntax()

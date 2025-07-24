"""
示例服务进程 - 监听mmap队列并处理服务请求
这个文件展示了如何创建一个服务进程来响应算子的服务调用
"""

import time
import json
import threading
from typing import Any, Dict
from sage_utils.mmap_queue.sage_queue import SageQueue
import logging


class BaseService:
    """基础服务类"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"Service.{service_name}")
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format=f'%(asctime)s - {service_name} - %(levelname)s - %(message)s'
        )
        
        # 请求队列 - 监听来自算子的请求
        self.request_queue_name = f"service_request_{service_name}"
        self.request_queue = SageQueue(self.request_queue_name)
        
        # 响应队列缓存 - 缓存不同的响应队列
        self.response_queues: Dict[str, SageQueue] = {}
        
        # 运行标志
        self.running = False
        
        self.logger.info(f"Service {service_name} initialized, listening on queue: {self.request_queue_name}")
    
    def get_response_queue(self, queue_name: str) -> SageQueue:
        """获取或创建响应队列"""
        if queue_name not in self.response_queues:
            self.response_queues[queue_name] = SageQueue(queue_name)
            self.logger.debug(f"Created response queue: {queue_name}")
        
        return self.response_queues[queue_name]
    
    def start(self):
        """启动服务"""
        self.running = True
        self.logger.info(f"Starting service: {self.service_name}")
        
        # 启动请求处理循环
        while self.running:
            try:
                # 从请求队列获取请求（阻塞等待1秒）
                request_data = self.request_queue.get(timeout=1.0)
                
                # 在新线程中处理请求，避免阻塞
                threading.Thread(
                    target=self._process_request,
                    args=(request_data,),
                    daemon=True
                ).start()
                
            except Exception as e:
                if "timed out" not in str(e).lower():
                    self.logger.error(f"Error receiving request: {e}")
    
    def _process_request(self, request_data: Dict[str, Any]):
        """处理单个请求"""
        try:
            request_id = request_data['request_id']
            method_name = request_data['method_name']
            args = request_data.get('args', ())
            kwargs = request_data.get('kwargs', {})
            response_queue_name = request_data['response_queue']
            
            self.logger.info(f"Processing request {request_id}: {method_name}({args}, {kwargs})")
            
            start_time = time.time()
            
            # 调用对应的方法
            try:
                if hasattr(self, method_name):
                    method = getattr(self, method_name)
                    result = method(*args, **kwargs)
                    success = True
                    error = None
                else:
                    result = None
                    success = False
                    error = f"Method '{method_name}' not found in service '{self.service_name}'"
                    
            except Exception as e:
                result = None
                success = False
                error = str(e)
                self.logger.error(f"Error executing {method_name}: {e}")
            
            execution_time = time.time() - start_time
            
            # 构造响应
            response_data = {
                'request_id': request_id,
                'result': result,
                'success': success,
                'error': error,
                'execution_time': execution_time,
                'timestamp': time.time()
            }
            
            # 发送响应
            response_queue = self.get_response_queue(response_queue_name)
            response_queue.put(response_data, timeout=5.0)
            
            self.logger.info(f"Response sent for request {request_id} in {execution_time:.3f}s")
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
    
    def stop(self):
        """停止服务"""
        self.running = False
        self.logger.info(f"Stopping service: {self.service_name}")
        
        # 关闭队列
        try:
            self.request_queue.close()
        except:
            pass
        
        for queue in self.response_queues.values():
            try:
                queue.close()
            except:
                pass
    
    def health_check(self) -> bool:
        """健康检查"""
        return True


class CacheService(BaseService):
    """缓存服务示例"""
    
    def __init__(self):
        super().__init__("cache")
        self.cache: Dict[str, Any] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0
        }
    
    def get(self, key: str) -> Any:
        """获取缓存值"""
        if key in self.cache:
            self.stats["hits"] += 1
            self.logger.debug(f"Cache hit: {key}")
            return self.cache[key]
        else:
            self.stats["misses"] += 1
            self.logger.debug(f"Cache miss: {key}")
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """设置缓存值"""
        self.cache[key] = value
        self.stats["sets"] += 1
        self.logger.debug(f"Cache set: {key}")
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key in self.cache:
            del self.cache[key]
            self.logger.debug(f"Cache delete: {key}")
            return True
        return False
    
    def clear(self) -> bool:
        """清空缓存"""
        self.cache.clear()
        self.logger.info("Cache cleared")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            **self.stats,
            "cache_size": len(self.cache),
            "memory_usage": len(str(self.cache))  # 简单的内存估算
        }


class DatabaseService(BaseService):
    """数据库服务示例"""
    
    def __init__(self):
        super().__init__("database")
        # 模拟数据库数据
        self.users = {
            1: {"id": 1, "name": "Alice", "email": "alice@example.com"},
            2: {"id": 2, "name": "Bob", "email": "bob@example.com"},
            3: {"id": 3, "name": "Charlie", "email": "charlie@example.com"}
        }
    
    def query(self, sql: str) -> list:
        """执行查询（简化版）"""
        time.sleep(0.1)  # 模拟数据库延迟
        
        if "user_info" in sql.lower():
            # 模拟用户查询
            if "id = 1" in sql:
                return [self.users.get(1)]
            elif "id = 2" in sql:
                return [self.users.get(2)]
            else:
                return list(self.users.values())
        
        # 默认返回空结果
        return []
    
    def execute(self, sql: str) -> int:
        """执行更新/插入/删除（简化版）"""
        time.sleep(0.05)  # 模拟写操作延迟
        
        # 模拟返回影响的行数
        return 1
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """获取用户信息"""
        return self.users.get(user_id)
    
    def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """更新用户信息"""
        if user_id in self.users:
            self.users[user_id].update(data)
            return True
        return False


class AuthService(BaseService):
    """认证服务示例"""
    
    def __init__(self):
        super().__init__("auth")
        # 模拟用户会话
        self.sessions = {
            "token123": {"user_id": 1, "permissions": ["read", "write", "process_data"]},
            "token456": {"user_id": 2, "permissions": ["read", "process_data"]},
            "token789": {"user_id": 3, "permissions": ["read"]}
        }
    
    def authenticate(self, token: str) -> Dict[str, Any]:
        """认证令牌"""
        time.sleep(0.02)  # 模拟认证延迟
        
        if token in self.sessions:
            session = self.sessions[token]
            return {
                "valid": True,
                "user_id": session["user_id"],
                "permissions": session["permissions"]
            }
        else:
            return {"valid": False}
    
    def get_permissions(self, user_id: int) -> list:
        """获取用户权限"""
        for session in self.sessions.values():
            if session["user_id"] == user_id:
                return session["permissions"]
        return []
    
    def validate_permission(self, user_id: int, permission: str) -> bool:
        """验证用户权限"""
        permissions = self.get_permissions(user_id)
        return permission in permissions


def run_service(service_class):
    """运行服务的辅助函数"""
    service = service_class()
    try:
        service.start()
    except KeyboardInterrupt:
        print(f"\n💤 Shutting down {service.service_name} service...")
        service.stop()


def run_all_services():
    """在不同进程中运行所有服务"""
    import multiprocessing
    
    services = [CacheService, DatabaseService, AuthService]
    processes = []
    
    print("🚀 Starting all demo services...")
    
    for service_class in services:
        process = multiprocessing.Process(
            target=run_service,
            args=(service_class,),
            name=f"Service-{service_class.__name__}"
        )
        process.start()
        processes.append(process)
        print(f"✓ Started {service_class.__name__}")
    
    print("\n📡 Services are now listening for requests...")
    print("   Cache service: service_request_cache")
    print("   Database service: service_request_database")
    print("   Auth service: service_request_auth")
    print("\nPress Ctrl+C to stop all services\n")
    
    try:
        # 等待所有进程
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        print("\n💤 Shutting down all services...")
        for process in processes:
            process.terminate()
            process.join(timeout=5)
        print("✅ All services stopped.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        service_name = sys.argv[1]
        
        if service_name == "cache":
            run_service(CacheService)
        elif service_name == "database":
            run_service(DatabaseService)
        elif service_name == "auth":
            run_service(AuthService)
        elif service_name == "all":
            run_all_services()
        else:
            print(f"Unknown service: {service_name}")
            print("Available services: cache, database, auth, all")
    else:
        print("Usage: python service_process_example.py <service_name>")
        print("Services: cache, database, auth, all")
        print("\nExample:")
        print("  python service_process_example.py cache    # Run cache service")
        print("  python service_process_example.py all      # Run all services")

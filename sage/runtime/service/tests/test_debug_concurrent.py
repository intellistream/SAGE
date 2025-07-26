"""
调试并发问题：详细追踪代理对象的创建过程
"""

import threading
import time
import sys
import os
from collections import defaultdict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage.core.function.base_function import BaseFunction


class DebugServiceManager:
    """调试版本的ServiceManager，追踪代理对象创建"""
    
    creation_log = []
    creation_lock = threading.Lock()
    
    @classmethod
    def log_creation(cls, proxy_type, service_name, proxy_id, thread_id):
        with cls.creation_lock:
            cls.creation_log.append({
                'proxy_type': proxy_type,
                'service_name': service_name,
                'proxy_id': proxy_id,
                'thread_id': thread_id,
                'timestamp': time.time()
            })


class MockRuntimeContext:
    """模拟运行时上下文"""
    def __init__(self, name="test_context"):
        import logging
        self.logger = logging.getLogger(name)
        self.name = name
        self.env_name = "test_env"
        self._service_manager = None
    
    @property
    def service_manager(self):
        if self._service_manager is None:
            from sage.runtime.service.service_caller import ServiceManager
            self._service_manager = ServiceManager(self)
        return self._service_manager


class DebugTestFunction(BaseFunction):
    """调试版本的测试Function"""
    
    def execute(self, data):
        return data
    
    @property
    def call_service(self):
        """重写call_service以添加调试信息"""
        if self.ctx is None:
            raise RuntimeError("Runtime context not initialized. Cannot access services.")
        
        class DebugServiceProxy:
            def __init__(self, service_manager, function_instance):
                self._service_manager = service_manager
                self._function_instance = function_instance
                
            def __getitem__(self, service_name: str):
                proxy = self._service_manager.get_sync_proxy(service_name)
                
                # 记录创建信息
                DebugServiceManager.log_creation(
                    'sync', 
                    service_name, 
                    id(proxy), 
                    threading.current_thread().ident
                )
                
                return proxy
        
        return DebugServiceProxy(self.ctx.service_manager, self)
    
    @property 
    def call_service_async(self):
        """重写call_service_async以添加调试信息"""
        if self.ctx is None:
            raise RuntimeError("Runtime context not initialized. Cannot access services.")
        
        class DebugAsyncServiceProxy:
            def __init__(self, service_manager, function_instance):
                self._service_manager = service_manager
                self._function_instance = function_instance
                
            def __getitem__(self, service_name: str):
                proxy = self._service_manager.get_async_proxy(service_name)
                
                # 记录创建信息
                DebugServiceManager.log_creation(
                    'async', 
                    service_name, 
                    id(proxy), 
                    threading.current_thread().ident
                )
                
                return proxy
        
        return DebugAsyncServiceProxy(self.ctx.service_manager, self)


def test_debug_concurrent():
    """调试版本的并发测试"""
    print("Running debug concurrent test...")
    
    # 清空日志
    DebugServiceManager.creation_log.clear()
    
    num_threads = 3
    calls_per_thread = 3
    results = []
    results_lock = threading.Lock()
    
    def debug_worker(worker_id):
        """调试工作线程"""
        try:
            print(f"Worker {worker_id} starting...")
            
            # 创建function实例
            func = DebugTestFunction()
            func.ctx = MockRuntimeContext(f"debug_context_{worker_id}")
            
            thread_results = []
            
            for call_id in range(calls_per_thread):
                print(f"Worker {worker_id}, call {call_id}")
                
                # 获取代理对象
                sync_proxy = func.call_service["test_service"]
                async_proxy = func.call_service_async["test_service"]
                
                thread_results.append({
                    'worker_id': worker_id,
                    'call_id': call_id,
                    'sync_proxy_id': id(sync_proxy),
                    'async_proxy_id': id(async_proxy),
                })
                
                time.sleep(0.01)  # 稍长的延迟
            
            with results_lock:
                results.extend(thread_results)
                print(f"Worker {worker_id} completed")
                
        except Exception as e:
            print(f"Worker {worker_id} error: {e}")
            import traceback
            traceback.print_exc()
    
    # 启动线程
    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=debug_worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # 等待完成
    for thread in threads:
        thread.join()
    
    print(f"\n=== Creation Log Analysis ===")
    print(f"Total proxy creations logged: {len(DebugServiceManager.creation_log)}")
    
    # 按类型分析
    by_type = defaultdict(list)
    for log_entry in DebugServiceManager.creation_log:
        by_type[log_entry['proxy_type']].append(log_entry)
    
    for proxy_type, entries in by_type.items():
        proxy_ids = [entry['proxy_id'] for entry in entries]
        unique_ids = set(proxy_ids)
        
        print(f"{proxy_type.upper()} proxies:")
        print(f"  Total created: {len(entries)}")
        print(f"  Unique IDs: {len(unique_ids)}")
        print(f"  Duplicates: {len(entries) - len(unique_ids)}")
        
        if len(unique_ids) != len(entries):
            print(f"  ❌ Duplicate proxy IDs detected!")
            
            # 找出重复的ID
            id_counts = defaultdict(int)
            for proxy_id in proxy_ids:
                id_counts[proxy_id] += 1
            
            duplicates = {pid: count for pid, count in id_counts.items() if count > 1}
            print(f"  Duplicate IDs: {duplicates}")
            
            # 显示重复ID的详细信息
            for dup_id, count in duplicates.items():
                dup_entries = [e for e in entries if e['proxy_id'] == dup_id]
                print(f"    ID {dup_id} (used {count} times):")
                for entry in dup_entries:
                    print(f"      Thread {entry['thread_id']}, Service: {entry['service_name']}")
        else:
            print(f"  ✅ All {proxy_type} proxies are unique")
    
    # 分析结果数据
    print(f"\n=== Results Analysis ===")
    sync_ids_from_results = set(r['sync_proxy_id'] for r in results)
    async_ids_from_results = set(r['async_proxy_id'] for r in results)
    
    print(f"Results collected: {len(results)}")
    print(f"Expected: {num_threads * calls_per_thread}")
    print(f"Unique sync IDs in results: {len(sync_ids_from_results)}")
    print(f"Unique async IDs in results: {len(async_ids_from_results)}")


if __name__ == "__main__":
    test_debug_concurrent()

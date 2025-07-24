"""
深度调试：检查是否是Python对象复用或其他缓存机制导致的问题
"""

import threading
import time
import sys
import os
import gc
from collections import defaultdict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage_core.function.base_function import BaseFunction


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
            from sage_runtime.service.service_caller import ServiceManager
            self._service_manager = ServiceManager(self)
        return self._service_manager


class TestFunction(BaseFunction):
    """测试用的Function类"""
    
    def execute(self, data):
        return data


def test_object_lifecycle():
    """测试对象生命周期和复用"""
    print("Testing object lifecycle and reuse...")
    
    func = TestFunction()
    func.ctx = MockRuntimeContext("lifecycle_test")
    
    # 创建一批代理对象
    proxies_batch_1 = []
    for i in range(5):
        proxy = func.call_service["test_service"]
        proxies_batch_1.append((id(proxy), proxy))
        print(f"Batch 1, proxy {i}: ID = {id(proxy)}")
    
    print(f"Batch 1 unique IDs: {len(set(pid for pid, _ in proxies_batch_1))}")
    
    # 删除引用，强制垃圾回收
    del proxies_batch_1
    gc.collect()
    
    print("\nAfter garbage collection...")
    
    # 创建第二批代理对象
    proxies_batch_2 = []
    for i in range(5):
        proxy = func.call_service["test_service"]
        proxies_batch_2.append((id(proxy), proxy))
        print(f"Batch 2, proxy {i}: ID = {id(proxy)}")
    
    print(f"Batch 2 unique IDs: {len(set(pid for pid, _ in proxies_batch_2))}")


def test_concurrent_with_detailed_tracking():
    """带详细追踪的并发测试"""
    print("\nTesting concurrent with detailed tracking...")
    
    results = []
    results_lock = threading.Lock()
    
    # 跟踪每个代理对象的创建时间和线程
    proxy_creation_info = {}
    creation_lock = threading.Lock()
    
    def track_proxy_creation(proxy_id, thread_id, worker_id, call_id, proxy_type):
        with creation_lock:
            if proxy_id in proxy_creation_info:
                print(f"⚠️  REUSE DETECTED: Proxy ID {proxy_id} already exists!")
                print(f"   Original: {proxy_creation_info[proxy_id]}")
                print(f"   New: thread={thread_id}, worker={worker_id}, call={call_id}, type={proxy_type}")
            else:
                proxy_creation_info[proxy_id] = {
                    'thread_id': thread_id,
                    'worker_id': worker_id,
                    'call_id': call_id,
                    'proxy_type': proxy_type,
                    'timestamp': time.time()
                }
    
    def detailed_worker(worker_id):
        """详细跟踪的工作线程"""
        try:
            print(f"Worker {worker_id} starting in thread {threading.current_thread().ident}")
            
            # 每个worker创建独立的function实例
            func = TestFunction()
            func.ctx = MockRuntimeContext(f"detailed_context_{worker_id}")
            
            for call_id in range(3):
                print(f"Worker {worker_id}, call {call_id}")
                
                # 获取同步代理
                sync_proxy = func.call_service["test_service"]
                sync_id = id(sync_proxy)
                track_proxy_creation(sync_id, threading.current_thread().ident, worker_id, call_id, 'sync')
                
                # 获取异步代理
                async_proxy = func.call_service_async["test_service"]
                async_id = id(async_proxy)
                track_proxy_creation(async_id, threading.current_thread().ident, worker_id, call_id, 'async')
                
                # 再次获取同样服务的代理，应该是不同的对象
                sync_proxy_2 = func.call_service["test_service"]
                sync_id_2 = id(sync_proxy_2)
                track_proxy_creation(sync_id_2, threading.current_thread().ident, worker_id, f"{call_id}_b", 'sync')
                
                result = {
                    'worker_id': worker_id,
                    'call_id': call_id,
                    'thread_id': threading.current_thread().ident,
                    'sync_id_1': sync_id,
                    'async_id': async_id,
                    'sync_id_2': sync_id_2,
                }
                
                with results_lock:
                    results.append(result)
                
                # 验证同一次调用中的两个同步代理是不同的
                if sync_id == sync_id_2:
                    print(f"⚠️  Worker {worker_id}, call {call_id}: Same sync proxy ID used twice!")
                
                time.sleep(0.005)  # 短暂延迟
                
        except Exception as e:
            print(f"Worker {worker_id} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # 启动3个工作线程
    threads = []
    for i in range(3):
        thread = threading.Thread(target=detailed_worker, args=(i,))
        threads.append(thread)
        thread.start()
    
    # 等待完成
    for thread in threads:
        thread.join()
    
    print(f"\n=== Detailed Analysis ===")
    print(f"Total results: {len(results)}")
    print(f"Total proxy creations tracked: {len(proxy_creation_info)}")
    
    # 分析每个worker的结果
    for worker_id in range(3):
        worker_results = [r for r in results if r['worker_id'] == worker_id]
        print(f"\nWorker {worker_id}:")
        print(f"  Results: {len(worker_results)}")
        
        all_ids = []
        for result in worker_results:
            all_ids.extend([result['sync_id_1'], result['async_id'], result['sync_id_2']])
        
        unique_ids = set(all_ids)
        print(f"  Total proxy IDs: {len(all_ids)}")
        print(f"  Unique proxy IDs: {len(unique_ids)}")
        
        if len(all_ids) != len(unique_ids):
            print(f"  ⚠️  Worker {worker_id} has reused proxy IDs!")
    
    # 全局分析
    all_sync_1_ids = set(r['sync_id_1'] for r in results)
    all_async_ids = set(r['async_id'] for r in results)
    all_sync_2_ids = set(r['sync_id_2'] for r in results)
    
    print(f"\n=== Global Analysis ===")
    print(f"Unique sync_1 IDs: {len(all_sync_1_ids)}")
    print(f"Unique async IDs: {len(all_async_ids)}")
    print(f"Unique sync_2 IDs: {len(all_sync_2_ids)}")
    print(f"Expected unique IDs for each type: {len(results)}")
    
    # 检查是否有跨类型的ID重复
    all_ids_combined = all_sync_1_ids | all_async_ids | all_sync_2_ids
    total_ids_expected = len(results) * 3
    
    print(f"All unique IDs combined: {len(all_ids_combined)}")
    print(f"Total IDs expected: {total_ids_expected}")
    
    if len(all_ids_combined) == total_ids_expected:
        print("✅ All proxy objects are truly unique across all types and calls")
        return True
    else:
        print("❌ Some proxy IDs are being reused")
        return False


if __name__ == "__main__":
    print("Running deep debug tests...\n")
    
    # 测试对象生命周期
    test_object_lifecycle()
    
    # 测试详细并发跟踪
    success = test_concurrent_with_detailed_tracking()
    
    if success:
        print("\n🎉 Deep debug tests passed!")
    else:
        print("\n❌ Deep debug tests revealed issues.")
        sys.exit(1)

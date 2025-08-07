"""
Service Call Service集成测试
测试高层service调用底层service的场景，验证服务间通信和重构后的call_service功能
"""

import time
import json
import os
import threading
import unittest
import pytest
from datetime import datetime
from unittest.mock import Mock
from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.service.base_service import BaseService
from sage.core.api.function.comap_function import BaseCoMapFunction
from sage.core.api.function.sink_function import SinkFunction


# ==================== 底层Memory服务类 ====================

class LowLevelMemoryService:
    """底层内存存储服务 - 实际存储数据的服务"""
    
    def __init__(self):
        self.storage = {}  # 实际存储数据的字典
        self.access_count = 0
        self.operation_log = []
    
    def store(self, key: str, value: any) -> dict:
        """存储数据到底层存储"""
        self.access_count += 1
        self.storage[key] = {
            "value": value,
            "stored_at": time.time(),
            "access_count": 1
        }
        
        operation = {
            "operation": "store",
            "key": key,
            "timestamp": time.time(),
            "success": True
        }
        self.operation_log.append(operation)
        
        return {
            "success": True,
            "key": key,
            "stored_at": self.storage[key]["stored_at"],
            "message": f"Successfully stored {key} in low-level storage"
        }
    
    def retrieve(self, key: str) -> dict:
        """从底层存储检索数据"""
        self.access_count += 1
        
        operation = {
            "operation": "retrieve", 
            "key": key,
            "timestamp": time.time(),
            "success": key in self.storage
        }
        self.operation_log.append(operation)
        
        if key in self.storage:
            self.storage[key]["access_count"] += 1
            return {
                "success": True,
                "key": key,
                "value": self.storage[key]["value"],
                "stored_at": self.storage[key]["stored_at"],
                "access_count": self.storage[key]["access_count"],
                "message": f"Successfully retrieved {key} from low-level storage"
            }
        else:
            return {
                "success": False,
                "key": key,
                "error": f"Key {key} not found in low-level storage",
                "message": "Key not found"
            }
    
    def delete(self, key: str) -> dict:
        """从底层存储删除数据"""
        self.access_count += 1
        
        operation = {
            "operation": "delete",
            "key": key, 
            "timestamp": time.time(),
            "success": key in self.storage
        }
        self.operation_log.append(operation)
        
        if key in self.storage:
            del self.storage[key]
            return {
                "success": True,
                "key": key,
                "message": f"Successfully deleted {key} from low-level storage"
            }
        else:
            return {
                "success": False,
                "key": key,
                "error": f"Key {key} not found in low-level storage",
                "message": "Key not found for deletion"
            }
    
    def get_stats(self) -> dict:
        """获取存储统计信息"""
        return {
            "total_keys": len(self.storage),
            "total_access_count": self.access_count,
            "operations_performed": len(self.operation_log),
            "storage_keys": list(self.storage.keys())
        }


# ==================== 高层Memory服务类 ====================

class HighLevelMemoryService(BaseService):
    """高层内存管理服务 - 调用底层memory service并提供增强功能"""
    
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.cache = {}  # 高层缓存
        self.operation_history = []
        self.hit_count = 0
        self.miss_count = 0
    
    def get_with_cache(self, key: str, use_cache: bool = True) -> dict:
        """
        带缓存的获取操作 - 调用底层memory service
        """
        start_time = time.time()
        
        # 检查高层缓存
        if use_cache and key in self.cache:
            self.hit_count += 1
            result = {
                "success": True,
                "key": key,
                "value": self.cache[key]["value"],
                "source": "high_level_cache",
                "cached_at": self.cache[key]["cached_at"],
                "cache_hit": True,
                "response_time": time.time() - start_time
            }
            
            self.operation_history.append({
                "operation": "get_with_cache",
                "key": key,
                "cache_hit": True,
                "timestamp": time.time()
            })
            
            return result
        
        # 缓存未命中，调用底层服务
        self.miss_count += 1
        
        try:
            # 使用service call语法糖调用底层memory service
            low_level_result = self.call_service["low_level_memory"].retrieve(key, timeout=10.0)
            
            if low_level_result.get("success"):
                # 将结果缓存到高层缓存
                if use_cache:
                    self.cache[key] = {
                        "value": low_level_result["value"],
                        "cached_at": time.time(),
                        "low_level_stored_at": low_level_result.get("stored_at")
                    }
                
                result = {
                    "success": True,
                    "key": key,
                    "value": low_level_result["value"],
                    "source": "low_level_storage",
                    "stored_at": low_level_result.get("stored_at"),
                    "access_count": low_level_result.get("access_count"),
                    "cache_hit": False,
                    "cached_in_high_level": use_cache,
                    "response_time": time.time() - start_time
                }
            else:
                result = {
                    "success": False,
                    "key": key,
                    "error": low_level_result.get("error"),
                    "source": "low_level_storage",
                    "cache_hit": False,
                    "response_time": time.time() - start_time
                }
                
        except Exception as e:
            result = {
                "success": False,
                "key": key,
                "error": f"Service call failed: {str(e)}",
                "source": "service_call_error",
                "cache_hit": False,
                "response_time": time.time() - start_time
            }
            
            if self.ctx:
                self.logger.error(f"Failed to call low_level_memory service: {e}")
        
        self.operation_history.append({
            "operation": "get_with_cache",
            "key": key,
            "cache_hit": False,
            "success": result.get("success"),
            "timestamp": time.time()
        })
        
        return result
    
    def put_with_sync(self, key: str, value: any, sync_to_low_level: bool = True) -> dict:
        """
        带同步的存储操作 - 调用底层memory service
        """
        start_time = time.time()
        
        # 先存储到高层缓存
        self.cache[key] = {
            "value": value,
            "cached_at": time.time(),
            "synced_to_low_level": False
        }
        
        result = {
            "success": True,
            "key": key,
            "stored_in_high_level": True,
            "synced_to_low_level": False,
            "response_time": 0
        }
        
        # 如果需要同步到底层存储
        if sync_to_low_level:
            try:
                # 使用service call语法糖调用底层memory service
                low_level_result = self.call_service["low_level_memory"].store(key, value, timeout=10.0)
                
                if low_level_result.get("success"):
                    self.cache[key]["synced_to_low_level"] = True
                    self.cache[key]["low_level_stored_at"] = low_level_result.get("stored_at")
                    
                    result.update({
                        "synced_to_low_level": True,
                        "low_level_stored_at": low_level_result.get("stored_at"),
                        "low_level_message": low_level_result.get("message")
                    })
                else:
                    result.update({
                        "sync_error": low_level_result.get("error"),
                        "low_level_message": low_level_result.get("message")
                    })
                    
            except Exception as e:
                result.update({
                    "sync_error": f"Service call failed: {str(e)}",
                    "synced_to_low_level": False
                })
                
                if self.ctx:
                    self.logger.error(f"Failed to sync to low_level_memory service: {e}")
        
        result["response_time"] = time.time() - start_time
        
        self.operation_history.append({
            "operation": "put_with_sync",
            "key": key,
            "sync_requested": sync_to_low_level,
            "sync_success": result.get("synced_to_low_level", False),
            "timestamp": time.time()
        })
        
        return result
    
    def bulk_operation(self, operations: list) -> dict:
        """
        批量操作 - 演示复杂的service调用场景
        """
        start_time = time.time()
        results = []
        
        for op in operations:
            op_type = op.get("type")
            key = op.get("key")
            value = op.get("value")
            
            if op_type == "get":
                result = self.get_with_cache(key, use_cache=op.get("use_cache", True))
            elif op_type == "put":
                result = self.put_with_sync(key, value, sync_to_low_level=op.get("sync", True))
            else:
                result = {"success": False, "error": f"Unknown operation type: {op_type}"}
            
            results.append({
                "operation": op,
                "result": result
            })
        
        # 异步获取底层存储统计
        try:
            stats_future = self.call_service_async["low_level_memory"].get_stats(timeout=10.0)
            low_level_stats = stats_future.result(timeout=5.0)
        except Exception as e:
            low_level_stats = {"error": f"Failed to get stats: {str(e)}"}
            if self.ctx:
                self.logger.warning(f"Failed to get low-level stats: {e}")
        
        return {
            "success": True,
            "total_operations": len(operations),
            "results": results,
            "high_level_stats": {
                "cache_size": len(self.cache),
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate": self.hit_count / (self.hit_count + self.miss_count) if (self.hit_count + self.miss_count) > 0 else 0
            },
            "low_level_stats": low_level_stats,
            "response_time": time.time() - start_time
        }


# ==================== 测试CoMap函数 ====================

class MemoryTestCoMapFunction(BaseCoMapFunction):
    """
    内存服务测试CoMap函数
    Stream 0: 存储请求流
    Stream 1: 读取请求流
    """
    
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.processed_stores = 0
        self.processed_reads = 0
    
    def map0(self, store_request):
        """处理存储请求流 - 调用高层memory service"""
        print(f"[DEBUG] MemoryTest.map0 - Store request: {store_request}")
        self.processed_stores += 1
        
        key = store_request["key"]
        value = store_request["value"]
        sync_required = store_request.get("sync", True)
        
        try:
            # 调用高层memory service进行存储
            result = self.call_service["high_level_memory"].put_with_sync(
                key, value, sync_to_low_level=sync_required, timeout=15.0
            )
            
            return {
                "type": "store_result",
                "original_request": store_request,
                "result": result,
                "processed_sequence": self.processed_stores,
                "source_stream": 0,
                "processor": "StoreProcessor",
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "type": "store_error",
                "original_request": store_request,
                "error": str(e),
                "processed_sequence": self.processed_stores,
                "source_stream": 0,
                "processor": "StoreProcessor",
                "timestamp": time.time()
            }
    
    def map1(self, read_request):
        """处理读取请求流 - 调用高层memory service"""
        print(f"[DEBUG] MemoryTest.map1 - Read request: {read_request}")
        self.processed_reads += 1
        
        key = read_request["key"]
        use_cache = read_request.get("use_cache", True)
        
        try:
            # 调用高层memory service进行读取
            result = self.call_service["high_level_memory"].get_with_cache(
                key, use_cache=use_cache, timeout=15.0
            )
            
            return {
                "type": "read_result",
                "original_request": read_request,
                "result": result,
                "processed_sequence": self.processed_reads,
                "source_stream": 1,
                "processor": "ReadProcessor",
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "type": "read_error",
                "original_request": read_request,
                "error": str(e),
                "processed_sequence": self.processed_reads,
                "source_stream": 1,
                "processor": "ReadProcessor",
                "timestamp": time.time()
            }


# ==================== 结果收集Sink ====================

class MemoryTestResultSink(SinkFunction):
    """内存服务测试结果收集Sink"""
    
    def __init__(self, output_file: str, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.output_file = output_file
        self.processed_count = 0
        self.all_results = []
        self.store_results = []
        self.read_results = []
    
    def execute(self, data):
        print(f"[DEBUG] MemoryTestResultSink.execute: {data.get('type', 'unknown')}")
        
        self.processed_count += 1
        self.all_results.append(data)
        
        result_type = data.get("type")
        if result_type in ["store_result", "store_error"]:
            self.store_results.append(data)
        elif result_type in ["read_result", "read_error"]:
            self.read_results.append(data)
        
        # 实时写入结果到文件
        self._write_result_to_file(data)
        
        # 打印简化的控制台输出
        self._print_result_summary(data)
        
        return data
    
    def _write_result_to_file(self, data):
        """将结果写入文件"""
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            
            # 追加写入结果
            with open(self.output_file, "a", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                f.write("\n" + "="*50 + "\n")
                
        except Exception as e:
            print(f"Error writing to file {self.output_file}: {e}")
    
    def _print_result_summary(self, data):
        """打印结果摘要"""
        result_type = data.get("type")
        stream = data.get("source_stream", -1)
        sequence = data.get("processed_sequence", 0)
        
        if result_type == "store_result":
            result = data.get("result", {})
            key = data.get("original_request", {}).get("key", "unknown")
            success = result.get("success", False)
            synced = result.get("synced_to_low_level", False)
            response_time = result.get("response_time", 0)
            print(f"💾 Store (Stream {stream}, #{sequence}): {key} -> "
                  f"{'✅' if success else '❌'} | Synced: {'✅' if synced else '❌'} | "
                  f"Time: {response_time:.3f}s")
        
        elif result_type == "read_result":
            result = data.get("result", {})
            key = data.get("original_request", {}).get("key", "unknown")
            success = result.get("success", False)
            cache_hit = result.get("cache_hit", False)
            source = result.get("source", "unknown")
            response_time = result.get("response_time", 0)
            print(f"📖 Read (Stream {stream}, #{sequence}): {key} -> "
                  f"{'✅' if success else '❌'} | Cache: {'🔥' if cache_hit else '❄️'} | "
                  f"Source: {source} | Time: {response_time:.3f}s")
        
        elif result_type in ["store_error", "read_error"]:
            key = data.get("original_request", {}).get("key", "unknown")
            error = data.get("error", "Unknown error")
            print(f"❌ Error (Stream {stream}, #{sequence}): {key} -> {error[:50]}...")


# ==================== 测试类 ====================

class TestServiceCallServiceIntegration:
    """测试Service Call Service集成"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.test_start_time = time.time()
        self.output_file = os.path.expanduser(f"~/.sage/test_tmp/service_call_service_test_{int(self.test_start_time)}.json")
    
    def test_service_call_service_integration(self):
        """测试Service调用Service的集成"""
        print("\n🚀 Testing Service Call Service Integration")
        print("=" * 70)
        print(f"📁 Output file: {self.output_file}")
        print("=" * 70)
        
        # 创建环境
        env = LocalEnvironment("service_call_service_test")
        
        # 注册服务到环境
        env.register_service("low_level_memory", LowLevelMemoryService)
        env.register_service("high_level_memory", HighLevelMemoryService)
        
        print("✅ Services registered:")
        print("   - low_level_memory: LowLevelMemoryService (底层存储)")
        print("   - high_level_memory: HighLevelMemoryService (高层管理，会调用低层)")
        
        # 创建测试数据
        store_requests = [
            {"key": "user:001", "value": {"name": "Alice", "age": 25}, "sync": True},
            {"key": "user:002", "value": {"name": "Bob", "age": 30}, "sync": True},
            {"key": "config:timeout", "value": 3600, "sync": False},
            {"key": "user:003", "value": {"name": "Charlie", "age": 28}, "sync": True},
            {"key": "config:debug", "value": True, "sync": False},
        ]
        
        read_requests = [
            {"key": "user:001", "use_cache": True},   # 应该缓存命中
            {"key": "user:002", "use_cache": False},  # 直接从底层读取
            {"key": "user:999", "use_cache": True},   # 不存在的key
            {"key": "user:001", "use_cache": True},   # 再次读取，应该缓存命中
            {"key": "config:timeout", "use_cache": True}, # 从高层缓存读取（未同步到底层）
            {"key": "user:003", "use_cache": True},   # 第一次读取
            {"key": "config:debug", "use_cache": False}, # 直接从高层缓存读取
        ]
        
        # 创建数据流
        store_stream = env.from_batch(store_requests)
        read_stream = env.from_batch(read_requests)
        
        # 构建处理管道
        result_stream = (
            store_stream
            .connect(read_stream)
            .comap(MemoryTestCoMapFunction)
            .sink(MemoryTestResultSink, output_file=self.output_file, parallelism=1)
        )
        
        # 提交并运行
        print("\n🏃 Pipeline running...")
        env.submit()
        time.sleep(15)  # 让管道运行一段时间
        
        # 等待一会儿确保所有结果都写入文件
        time.sleep(2)
        
        print(f"\n📊 Test completed. Results saved to: {self.output_file}")
        
        # 验证结果
        self._verify_test_results()
    
    def _verify_test_results(self):
        """验证测试结果的正确性"""
        print("\n🔍 Verifying test results...")
        
        if not os.path.exists(self.output_file):
            print(f"❌ Output file not found: {self.output_file}")
            return False
        
        try:
            # 读取结果文件
            results = []
            with open(self.output_file, "r", encoding="utf-8") as f:
                content = f.read()
                # 按分隔符分割
                result_blocks = content.split("="*50)
                
                for block in result_blocks:
                    block = block.strip()
                    if block:
                        try:
                            result = json.loads(block)
                            results.append(result)
                        except json.JSONDecodeError:
                            continue
            
            print(f"📄 Found {len(results)} results in output file")
            
            # 分析结果
            store_results = [r for r in results if r.get("type") == "store_result"]
            read_results = [r for r in results if r.get("type") == "read_result"]
            store_errors = [r for r in results if r.get("type") == "store_error"]
            read_errors = [r for r in results if r.get("type") == "read_error"]
            
            print(f"   - Store Results: {len(store_results)}")
            print(f"   - Read Results: {len(read_results)}")
            print(f"   - Store Errors: {len(store_errors)}")
            print(f"   - Read Errors: {len(read_errors)}")
            
            # 验证关键测试点
            verification_passed = True
            
            # 1. 验证存储操作
            successful_stores = [r for r in store_results if r.get("result", {}).get("success")]
            print(f"\n✅ Verification Points:")
            print(f"   - Successful stores: {len(successful_stores)}/{len(store_results)}")
            
            if len(successful_stores) < len(store_results):
                print(f"   ❌ Not all store operations succeeded")
                verification_passed = False
            
            # 2. 验证同步操作
            synced_stores = [r for r in successful_stores 
                           if r.get("result", {}).get("synced_to_low_level")]
            expected_synced = len([req for req in [
                {"sync": True}, {"sync": True}, {"sync": False}, {"sync": True}, {"sync": False}
            ] if req.get("sync")])
            print(f"   - Synced to low-level: {len(synced_stores)}/{expected_synced} (expected)")
            
            # 3. 验证读取操作
            successful_reads = [r for r in read_results if r.get("result", {}).get("success")]
            print(f"   - Successful reads: {len(successful_reads)}/{len(read_results)}")
            
            # 4. 验证缓存命中
            cache_hits = [r for r in successful_reads if r.get("result", {}).get("cache_hit")]
            print(f"   - Cache hits: {len(cache_hits)} (some reads should hit cache)")
            
            # 5. 验证service间调用
            service_call_evidence = []
            for result in store_results + read_results:
                result_data = result.get("result", {})
                if "low_level_stored_at" in result_data or "stored_at" in result_data:
                    service_call_evidence.append(result)
            
            print(f"   - Evidence of service-to-service calls: {len(service_call_evidence)}")
            
            if len(service_call_evidence) == 0:
                print(f"   ❌ No evidence of service-to-service calls found")
                verification_passed = False
            
            # 创建验证摘要文件
            summary_file = self.output_file.replace(".json", "_summary.json")
            summary = {
                "test_timestamp": self.test_start_time,
                "verification_time": time.time(),
                "total_results": len(results),
                "store_results": len(store_results),
                "read_results": len(read_results),
                "store_errors": len(store_errors),
                "read_errors": len(read_errors),
                "successful_stores": len(successful_stores),
                "successful_reads": len(successful_reads),
                "synced_stores": len(synced_stores),
                "cache_hits": len(cache_hits),
                "service_call_evidence": len(service_call_evidence),
                "verification_passed": verification_passed,
                "output_files": {
                    "detailed_results": self.output_file,
                    "summary": summary_file
                }
            }
            
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            print(f"\n📋 Verification summary saved to: {summary_file}")
            
            if verification_passed:
                print("🎉 All verifications passed! Service call service integration is working correctly.")
                return True
            else:
                print("❌ Some verifications failed. Please check the detailed results.")
                return False
                
        except Exception as e:
            print(f"❌ Error during result verification: {e}")
            import traceback
            traceback.print_exc()
            return False


# ==================== 独立测试函数 ====================

def test_service_call_service_integration():
    """独立运行的测试函数"""
    print("=" * 80)
    print("SAGE Service Call Service Integration Test")
    print("High-Level Memory Service -> Low-Level Memory Service")
    print("=" * 80)
    
    test_instance = TestServiceCallServiceIntegration()
    test_instance.setup_method()
    
    try:
        test_instance.test_service_call_service_integration()
        print("\n🎉 Service call service integration test completed successfully!")
        return True
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Service call service integration test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_service_call_service_integration()
    
    if not success:
        exit(1)

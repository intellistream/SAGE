"""
SAGE服务调用语法糖使用示例
展示如何通过高性能mmap队列与服务进程通信
"""

from sage_core.function.map_function import MapFunction
from sage_core.function.source_function import SourceFunction
from sage_core.function.sink_function import SinkFunction
from sage_core.api.local_environment import LocalEnvironment
from typing import Any, List, Dict
import time
import json


# ==================== 使用服务调用的算子示例 ====================

class DataProcessorFunction(MapFunction):
    """数据处理算子 - 展示同步服务调用"""
    
    def execute(self, data: dict) -> dict:
        # 同步调用缓存服务获取数据
        cached_result = self.call_service["cache"].get(f"processed_{data['id']}")
        
        if cached_result is not None:
            self.logger.info(f"Cache hit for data {data['id']}")
            return cached_result
        
        # 如果缓存未命中，处理数据
        processed_data = {
            "id": data["id"],
            "processed_value": data.get("value", 0) * 2,
            "timestamp": time.time(),
            "processed_by": self.name
        }
        
        # 将结果存入缓存
        self.call_service["cache"].set(f"processed_{data['id']}", processed_data)
        
        self.logger.info(f"Processed and cached data {data['id']}")
        return processed_data


class DataEnricherFunction(MapFunction):
    """数据增强算子 - 展示异步服务调用"""
    
    def execute(self, data: dict) -> dict:
        # 异步调用多个服务
        cache_future = self.call_service_async["cache"].get(f"user_profile_{data['user_id']}")
        db_future = self.call_service_async["database"].query(
            f"SELECT * FROM user_info WHERE id = {data['user_id']}"
        )
        
        # 在等待异步结果时进行本地处理
        enriched_data = {
            **data,
            "enriched_at": time.time(),
            "enricher": self.name
        }
        
        # 获取异步结果
        try:
            # 等待缓存结果（快速服务，超时时间短）
            cached_profile = cache_future.result(timeout=1.0)
            if cached_profile:
                enriched_data["cached_profile"] = cached_profile
                
            # 等待数据库结果（慢服务，超时时间长）
            db_result = db_future.result(timeout=5.0) 
            if db_result:
                enriched_data["user_info"] = db_result[0] if db_result else None
                
        except Exception as e:
            self.logger.warning(f"Failed to get some async service results: {e}")
        
        return enriched_data


class BatchProcessorFunction(MapFunction):
    """批处理算子 - 展示批量和混合调用模式"""
    
    def execute(self, batch_data: List[dict]) -> List[dict]:
        results = []
        
        # 批量异步调用 - 提高并发性
        cache_futures = []
        for item in batch_data:
            future = self.call_service_async["cache"].get(f"batch_item_{item['id']}")
            cache_futures.append((item, future))
        
        # 处理每个项目
        for item, cache_future in cache_futures:
            try:
                # 检查缓存结果
                cached_result = cache_future.result(timeout=0.5)
                if cached_result:
                    results.append(cached_result)
                    continue
                    
            except Exception:
                pass  # 缓存未命中或超时，继续处理
            
            # 本地处理
            processed = {
                **item,
                "batch_processed": True,
                "processed_at": time.time()
            }
            
            # 异步更新缓存（不等待结果）
            try:
                self.call_service_async["cache"].set(f"batch_item_{item['id']}", processed)
            except Exception as e:
                self.logger.warning(f"Failed to cache batch result: {e}")
            
            results.append(processed)
        
        return results


class ServiceStatsCollectorFunction(MapFunction):
    """服务统计收集器 - 展示服务监控"""
    
    def execute(self, data: dict) -> dict:
        # 收集各个服务的健康状态
        service_stats = {}
        
        # 同步检查各个服务的状态
        services_to_check = ["cache", "database", "auth", "notification"]
        
        for service_name in services_to_check:
            try:
                # 假设所有服务都有health_check方法
                start_time = time.time()
                health = self.call_service[service_name].health_check()
                response_time = time.time() - start_time
                
                service_stats[service_name] = {
                    "status": "healthy" if health else "unhealthy",
                    "response_time": response_time,
                    "last_check": time.time()
                }
                
            except Exception as e:
                service_stats[service_name] = {
                    "status": "error",
                    "error": str(e),
                    "last_check": time.time()
                }
        
        # 将统计信息添加到数据中
        return {
            **data,
            "service_stats": service_stats,
            "stats_collected_at": time.time()
        }


class ErrorHandlingFunction(MapFunction):
    """错误处理示例 - 展示服务调用的错误处理和降级策略"""
    
    def execute(self, data: dict) -> dict:
        # 主服务调用（带重试）
        result = self._call_with_retry("primary_service", "process", data, max_retries=3)
        
        if result is None:
            # 主服务失败，使用备用服务
            self.logger.warning("Primary service failed, trying backup service")
            result = self._call_backup_service(data)
        
        return result or self._local_fallback(data)
    
    def _call_with_retry(self, service_name: str, method_name: str, data: dict, max_retries: int = 3):
        """带重试机制的服务调用"""
        for attempt in range(max_retries):
            try:
                service_proxy = self.call_service[service_name]
                method = getattr(service_proxy, method_name)
                return method(data)
                
            except Exception as e:
                self.logger.warning(f"Service call attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    self.logger.error(f"All {max_retries} attempts failed for {service_name}.{method_name}")
        
        return None
    
    def _call_backup_service(self, data: dict):
        """调用备用服务"""
        try:
            return self.call_service["backup_service"].process(data)
        except Exception as e:
            self.logger.error(f"Backup service also failed: {e}")
            return None
    
    def _local_fallback(self, data: dict) -> dict:
        """本地降级处理"""
        self.logger.info("Using local fallback processing")
        return {
            **data,
            "processed_locally": True,
            "fallback_reason": "Service unavailable",
            "processed_at": time.time()
        }


# ==================== 数据源和输出示例 ====================

class TestDataSource(SourceFunction):
    """测试数据源"""
    
    def __init__(self):
        super().__init__()
        self.data_count = 0
    
    def execute(self, ctx) -> List[dict]:
        # 生成测试数据
        test_data = []
        for i in range(5):
            test_data.append({
                "id": self.data_count + i,
                "user_id": (self.data_count + i) % 100,
                "value": (self.data_count + i) * 10,
                "created_at": time.time()
            })
        
        self.data_count += 5
        return test_data


class ResultSinkFunction(SinkFunction):
    """结果输出"""
    
    def execute(self, data: Any):
        if isinstance(data, list):
            for item in data:
                print(f"✓ Processed: {json.dumps(item, indent=2)}")
        else:
            print(f"✓ Result: {json.dumps(data, indent=2)}")
    
    def close(self):
        print("🎯 Processing completed!")


# ==================== 管道构建示例 ====================

def create_service_pipeline():
    """创建使用服务的处理管道"""
    
    # 创建环境（不需要注册服务，直接通过队列通信）
    env = LocalEnvironment("service_demo")
    
    # 构建数据处理管道
    source_stream = env.from_source(TestDataSource)
    
    # 数据处理（使用缓存服务）
    processed_stream = source_stream.map(DataProcessorFunction)
    
    # 数据增强（异步调用多个服务）
    enriched_stream = processed_stream.map(DataEnricherFunction)
    
    # 批处理（混合调用模式）
    batch_stream = enriched_stream.map(BatchProcessorFunction)
    
    # 收集服务统计
    stats_stream = batch_stream.map(ServiceStatsCollectorFunction)
    
    # 错误处理和降级
    final_stream = stats_stream.map(ErrorHandlingFunction)
    
    # 输出结果
    final_stream.sink(ResultSinkFunction)
    
    return env


# ==================== 高级使用模式 ====================

class ConditionalServiceCallFunction(MapFunction):
    """条件性服务调用示例"""
    
    def execute(self, data: dict) -> dict:
        # 根据数据特征决定调用哪个服务
        if data.get("priority") == "high":
            # 高优先级数据使用快速服务
            result = self.call_service["fast_service"].process(data)
        elif data.get("complexity") == "high":
            # 复杂数据使用专门的处理服务
            result = self.call_service["complex_processor"].deep_process(data)
        else:
            # 普通数据使用标准服务
            result = self.call_service["standard_service"].process(data)
        
        return result


class ServiceChainFunction(MapFunction):
    """服务调用链示例"""
    
    def execute(self, data: dict) -> dict:
        # 服务调用链：认证 -> 授权 -> 处理 -> 记录
        
        # 1. 认证
        auth_result = self.call_service["auth"].authenticate(data.get("token"))
        if not auth_result.get("valid"):
            return {"error": "Authentication failed"}
        
        # 2. 授权
        user_id = auth_result["user_id"]
        permissions = self.call_service["auth"].get_permissions(user_id)
        if "process_data" not in permissions:
            return {"error": "Permission denied"}
        
        # 3. 处理数据
        processed = self.call_service["processor"].process(data, user_id=user_id)
        
        # 4. 记录日志（异步，不阻塞主流程）
        self.call_service_async["logger"].log_activity(user_id, "data_processed", processed["id"])
        
        return processed


class ParallelServiceCallFunction(MapFunction):
    """并行服务调用示例"""
    
    def execute(self, data: dict) -> dict:
        # 并行调用多个独立的服务
        futures = {
            "geo": self.call_service_async["geo_service"].geocode(data.get("address")),
            "weather": self.call_service_async["weather_service"].get_weather(data.get("location")),
            "traffic": self.call_service_async["traffic_service"].get_traffic(data.get("route")),
            "events": self.call_service_async["event_service"].get_nearby_events(data.get("coordinates"))
        }
        
        # 收集所有结果
        results = {}
        for service_name, future in futures.items():
            try:
                results[service_name] = future.result(timeout=10.0)
            except Exception as e:
                self.logger.warning(f"Service {service_name} failed: {e}")
                results[service_name] = None
        
        return {
            **data,
            "service_results": results,
            "enriched_at": time.time()
        }


if __name__ == "__main__":
    print("🚀 Starting SAGE Service Demo Pipeline...")
    
    # 创建并运行管道
    env = create_service_pipeline()
    
    print("📊 Pipeline created. Services will be called through mmap queues:")
    print("  - cache: service_request_cache")
    print("  - database: service_request_database") 
    print("  - auth: service_request_auth")
    print("  - notification: service_request_notification")
    print("  - Response queue: service_response_{env_name}_{node_name}")
    
    # 注意：在实际运行前，需要确保对应的服务进程正在运行并监听相应的队列
    # env.submit()

"""
示例：如何在SAGE框架中使用全局服务调用
"""

from sage_core.function.map_function import MapFunction
from sage_core.api.local_environment import LocalEnvironment  # 使用实际存在的环境类
from typing import Any

# ==================== 示例服务类 ====================

class CacheService:
    """示例缓存服务"""
    
    def __init__(self, cache_size: int = 1000):
        self.cache_size = cache_size
        self.cache = {}
        
    def get(self, key: str) -> Any:
        """获取缓存值"""
        return self.cache.get(key)
    
    def set(self, key: str, value: Any) -> bool:
        """设置缓存值"""
        if len(self.cache) >= self.cache_size:
            # 简单的LRU策略：删除第一个
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        
        self.cache[key] = value
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False


class DatabaseService:
    """示例数据库服务"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        # 这里应该是实际的数据库连接
        self.connected = True
        
    def query(self, sql: str) -> list:
        """执行查询"""
        # 模拟查询执行
        return [{"id": 1, "name": "test"}, {"id": 2, "name": "example"}]
    
    def execute(self, sql: str) -> int:
        """执行更新/插入/删除"""
        # 模拟执行
        return 1  # 影响行数


# ==================== 使用服务的算子示例 ====================

class DataProcessorFunction(MapFunction):
    """数据处理函数 - 演示同步服务调用"""
    
    def execute(self, data: dict) -> dict:
        # 同步调用缓存服务
        cached_result = self.ctx.call_service["cache"].get(f"processed_{data['id']}")
        
        if cached_result is not None:
            self.logger.info(f"Cache hit for data {data['id']}")
            return cached_result
        
        # 处理数据
        processed_data = {
            "id": data["id"],
            "processed_value": data.get("value", 0) * 2,
            "timestamp": data.get("timestamp")
        }
        
        # 缓存结果
        self.ctx.call_service["cache"].set(f"processed_{data['id']}", processed_data)
        
        self.logger.info(f"Processed and cached data {data['id']}")
        return processed_data


class DataEnricherFunction(MapFunction):
    """数据增强函数 - 演示异步服务调用"""
    
    def execute(self, data: dict) -> dict:
        # 发起异步数据库查询
        db_future = self.ctx.call_service_async["database"].query(
            f"SELECT * FROM user_info WHERE id = {data['id']}"
        )
        
        # 发起异步缓存查询
        cache_future = self.ctx.call_service_async["cache"].get(f"user_profile_{data['id']}")
        
        # 在等待结果的同时做其他处理
        basic_enriched = {
            **data,
            "enriched_at": "2024-01-01T00:00:00Z",
            "source": "data_enricher"
        }
        
        # 等待异步结果
        try:
            # 等待数据库查询结果（最多等待5秒）
            db_result = db_future.result(timeout=5.0)
            if db_result:
                basic_enriched["user_info"] = db_result[0]
            
            # 检查缓存结果是否已经完成
            if cache_future.done():
                cached_profile = cache_future.result()
                if cached_profile:
                    basic_enriched["cached_profile"] = cached_profile
        
        except Exception as e:
            self.logger.warning(f"Failed to get async service results: {e}")
        
        return basic_enriched


class BatchProcessorFunction(MapFunction):
    """批处理函数 - 演示混合使用同步和异步调用"""
    
    def execute(self, batch_data: list) -> list:
        results = []
        
        # 对于大批量数据，使用异步调用提高并发性
        futures = []
        
        for item in batch_data:
            # 异步获取每个item的缓存
            future = self.ctx.call_service_async["cache"].get(f"batch_item_{item['id']}")
            futures.append((item, future))
        
        # 处理异步结果
        for item, future in futures:
            try:
                cached_result = future.result(timeout=1.0)
                if cached_result:
                    results.append(cached_result)
                    continue
            except Exception:
                pass  # 缓存未命中，继续处理
            
            # 同步处理未缓存的数据
            processed = self._process_item(item)
            
            # 异步缓存结果（不等待完成）
            self.ctx.call_service_async["cache"].set(f"batch_item_{item['id']}", processed)
            
            results.append(processed)
        
        return results
    
    def _process_item(self, item: dict) -> dict:
        """处理单个数据项"""
        return {
            **item,
            "processed": True,
            "batch_processed_at": "2024-01-01T00:00:00Z"
        }


# ==================== 使用示例 ====================

def create_pipeline_with_services():
    """创建带有服务的处理管道"""
    
    # 创建环境
    env = LocalEnvironment("service_example")
    
    # 注册服务
    env.register_service("cache", CacheService, cache_size=10000)
    env.register_service("database", DatabaseService, connection_string="postgresql://localhost/test")
    
    # 构建处理管道
    source_stream = env.from_source(lambda: [
        {"id": 1, "value": 10},
        {"id": 2, "value": 20},
        {"id": 3, "value": 30}
    ])
    
    # 数据处理（使用同步服务调用）
    processed_stream = source_stream.map(DataProcessorFunction)
    
    # 数据增强（使用异步服务调用）
    enriched_stream = processed_stream.map(DataEnricherFunction)
    
    # 批处理（混合使用）
    final_stream = enriched_stream.map(BatchProcessorFunction)
    
    # 输出结果
    final_stream.sink(lambda data: print(f"Final result: {data}"))
    
    return env


# ==================== 高级使用模式 ====================

class AdvancedServiceUsageFunction(MapFunction):
    """高级服务使用模式示例"""
    
    def execute(self, data: dict) -> dict:
        # 1. 并发异步调用多个服务
        cache_future = self.ctx.call_service_async["cache"].get(data["key"])
        db_future = self.ctx.call_service_async["database"].query(f"SELECT * FROM table WHERE id={data['id']}")
        
        # 2. 条件性服务调用
        if data.get("needs_validation"):
            validation_result = self.ctx.call_service["validation_service"].validate(data)
            if not validation_result:
                return {"error": "Validation failed"}
        
        # 3. 服务调用链
        user_id = data["user_id"]
        user_profile = self.ctx.call_service["user_service"].get_profile(user_id)
        
        if user_profile and user_profile.get("premium"):
            # 只对高级用户执行额外处理
            premium_data = self.ctx.call_service["premium_service"].enhance_data(data)
            data.update(premium_data)
        
        # 4. 错误处理和重试
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = self.ctx.call_service["external_api"].call_api(data)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"API call failed after {max_retries} attempts: {e}")
                    result = {"error": "External API unavailable"}
                else:
                    self.logger.warning(f"API call attempt {attempt + 1} failed, retrying...")
        
        # 5. 获取异步结果
        try:
            cached_data = cache_future.result(timeout=2.0)
            db_data = db_future.result(timeout=5.0)
            
            return {
                "original": data,
                "cached": cached_data,
                "db_result": db_data,
                "api_result": result
            }
        except Exception as e:
            self.logger.error(f"Failed to get async results: {e}")
            return {"error": "Async operation failed"}


if __name__ == "__main__":
    # 运行示例
    env = create_pipeline_with_services()
    env.submit()

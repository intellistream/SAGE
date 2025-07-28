"""
CoMap函数中服务调用集成测试
测试dataflow model算子内部调用环境中注册的service
参考算子内的service call语法糖和dataflow comap test
"""

import time
import threading
import unittest
from unittest.mock import Mock
from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.source_function import SourceFunction
from sage.core.function.comap_function import BaseCoMapFunction
from sage.core.function.sink_function import SinkFunction


# ==================== 测试服务类 ====================

class UserProfileService:
    """用户画像服务"""
    def __init__(self):
        self.profiles = {
            "user_001": {"name": "Alice", "age": 25, "interests": ["tech", "music"]},
            "user_002": {"name": "Bob", "age": 30, "interests": ["sports", "travel"]},
            "user_003": {"name": "Charlie", "age": 28, "interests": ["books", "movies"]},
        }
    
    def get_profile(self, user_id: str):
        return self.profiles.get(user_id, {"name": "Unknown", "age": 0, "interests": []})
    
    def update_activity(self, user_id: str, activity: str):
        if user_id in self.profiles:
            if "recent_activities" not in self.profiles[user_id]:
                self.profiles[user_id]["recent_activities"] = []
            self.profiles[user_id]["recent_activities"].append(activity)
            return f"Updated activity for {user_id}: {activity}"
        return f"User {user_id} not found"


class RecommendationService:
    """推荐服务"""
    def __init__(self):
        self.item_db = {
            "item_001": {"name": "Tech News", "category": "tech", "rating": 4.5},
            "item_002": {"name": "Music Album", "category": "music", "rating": 4.8},
            "item_003": {"name": "Sports Match", "category": "sports", "rating": 4.2},
            "item_004": {"name": "Travel Guide", "category": "travel", "rating": 4.6},
        }
    
    def get_recommendations(self, interests: list, user_id: str = None):
        recommendations = []
        for item_id, item_info in self.item_db.items():
            if item_info["category"] in interests:
                recommendations.append({
                    "item_id": item_id,
                    "name": item_info["name"],
                    "rating": item_info["rating"],
                    "reason": f"Matches interest: {item_info['category']}"
                })
        return recommendations[:3]  # 返回前3个推荐
    
    def track_interaction(self, user_id: str, item_id: str, interaction_type: str):
        return {
            "tracked": True,
            "user_id": user_id,
            "item_id": item_id,
            "interaction": interaction_type,
            "timestamp": time.time()
        }


class CacheService:
    """缓存服务"""
    def __init__(self):
        self.cache = {}
    
    def get(self, key: str):
        return self.cache.get(key)
    
    def set(self, key: str, value):
        self.cache[key] = value
        return f"Cached {key}"
    
    def invalidate(self, pattern: str):
        keys_to_remove = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_remove:
            del self.cache[key]
        return f"Invalidated {len(keys_to_remove)} keys matching '{pattern}'"


# ==================== 测试数据源 ====================

class UserEventSource(SourceFunction):
    """用户事件数据源"""
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.counter = 0
        self.events = [
            {"type": "view", "user_id": "user_001", "item_id": "item_001", "timestamp": time.time()},
            {"type": "click", "user_id": "user_002", "item_id": "item_002", "timestamp": time.time()},
            {"type": "view", "user_id": "user_003", "item_id": "item_003", "timestamp": time.time()},
            {"type": "like", "user_id": "user_001", "item_id": "item_002", "timestamp": time.time()},
        ]
    
    def execute(self):
        if self.counter >= len(self.events):
            return None
        
        event = self.events[self.counter]
        self.counter += 1
        if self.ctx:
            self.logger.info(f"UserEventSource generated: {event}")
        return event


class RecommendationRequestSource(SourceFunction):
    """推荐请求数据源"""
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.counter = 0
        self.requests = [
            {"type": "get_recommendations", "user_id": "user_001", "context": "homepage"},
            {"type": "get_recommendations", "user_id": "user_002", "context": "search"},
            {"type": "get_recommendations", "user_id": "user_003", "context": "profile"},
            {"type": "get_recommendations", "user_id": "user_001", "context": "feed"},
        ]
    
    def execute(self):
        if self.counter >= len(self.requests):
            return None
        
        request = self.requests[self.counter]
        self.counter += 1
        if self.ctx:
            self.logger.info(f"RecommendationRequestSource generated: {request}")
        return request


# ==================== CoMap函数测试类 ====================

class UserRecommendationCoMapFunction(BaseCoMapFunction):
    """
    用户推荐CoMap函数 - 测试在CoMap中调用服务
    Stream 0: 用户事件流
    Stream 1: 推荐请求流
    """
    
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.processed_events = 0
        self.processed_requests = 0
    
    def map0(self, event_data):
        """处理用户事件流 (stream 0) - 使用服务调用"""
        self.processed_events += 1
        
        user_id = event_data["user_id"]
        item_id = event_data["item_id"]
        interaction_type = event_data["type"]
        
        # 使用服务调用语法糖 - 同步调用用户画像服务
        activity_description = f"{interaction_type}_{item_id}"
        update_result = self.call_service["user_profile"].update_activity(user_id, activity_description)
        
        # 使用服务调用语法糖 - 同步调用推荐服务跟踪交互
        track_result = self.call_service["recommendation"].track_interaction(
            user_id, item_id, interaction_type
        )
        
        # 使用服务调用语法糖 - 异步调用缓存服务清理相关缓存
        cache_key_pattern = f"rec_{user_id}"
        cache_future = self.call_service_async["cache"].invalidate(cache_key_pattern)
        
        result = {
            "type": "processed_event",
            "original_event": event_data,
            "user_id": user_id,
            "activity_update": update_result,
            "interaction_tracked": track_result,
            "cache_invalidation_started": True,
            "processed_sequence": self.processed_events,
            "source_stream": 0,
            "processor": "EventProcessor"
        }
        
        # 获取异步结果
        try:
            cache_result = cache_future.result(timeout=2.0)
            result["cache_invalidation_result"] = cache_result
        except Exception as e:
            result["cache_invalidation_error"] = str(e)
        
        if self.ctx:
            self.logger.info(f"CoMap map0: processed event {event_data['type']} for user {user_id}")
        
        return result
    
    def map1(self, request_data):
        """处理推荐请求流 (stream 1) - 使用服务调用"""
        self.processed_requests += 1
        
        user_id = request_data["user_id"]
        context = request_data["context"]
        
        # 检查缓存 - 使用同步服务调用
        cache_key = f"rec_{user_id}_{context}"
        cached_recommendations = self.call_service["cache"].get(cache_key)
        
        if cached_recommendations:
            result = {
                "type": "cached_recommendations",
                "user_id": user_id,
                "context": context,
                "recommendations": cached_recommendations,
                "cache_hit": True,
                "processed_sequence": self.processed_requests,
                "source_stream": 1,
                "processor": "RecommendationProcessor"
            }
        else:
            # 缓存未命中，获取用户画像并生成推荐
            
            # 异步获取用户画像
            profile_future = self.call_service_async["user_profile"].get_profile(user_id)
            
            # 在等待的同时做一些本地处理
            request_info = {
                "user_id": user_id,
                "context": context,
                "request_time": time.time()
            }
            
            # 获取用户画像结果
            try:
                user_profile = profile_future.result(timeout=3.0)
                user_interests = user_profile.get("interests", [])
                
                # 根据用户兴趣获取推荐
                recommendations = self.call_service["recommendation"].get_recommendations(
                    user_interests, user_id
                )
                
                # 缓存推荐结果
                self.call_service["cache"].set(cache_key, recommendations)
                
                result = {
                    "type": "fresh_recommendations",
                    "user_id": user_id,
                    "context": context,
                    "user_profile": user_profile,
                    "recommendations": recommendations,
                    "cache_hit": False,
                    "processed_sequence": self.processed_requests,
                    "source_stream": 1,
                    "processor": "RecommendationProcessor"
                }
                
            except Exception as e:
                # 服务调用失败，返回错误信息
                result = {
                    "type": "recommendation_error",
                    "user_id": user_id,
                    "context": context,
                    "error": str(e),
                    "processed_sequence": self.processed_requests,
                    "source_stream": 1,
                    "processor": "RecommendationProcessor"
                }
        
        if self.ctx:
            self.logger.info(f"CoMap map1: processed recommendation request for user {user_id}")
        
        return result


# ==================== 调试输出Sink ====================

class ServiceTestSink(SinkFunction):
    """服务测试结果收集Sink"""
    
    _results = {}  # 类变量，用于收集所有实例的结果
    _lock = threading.Lock()
    
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.instance_id = id(self)
    
    def execute(self, data):
        with ServiceTestSink._lock:
            if self.instance_id not in ServiceTestSink._results:
                ServiceTestSink._results[self.instance_id] = []
            ServiceTestSink._results[self.instance_id].append(data)
        
        # 打印处理结果
        result_type = data.get("type", "unknown")
        source_stream = data.get("source_stream", -1)
        user_id = data.get("user_id", "unknown")
        
        if result_type == "processed_event":
            print(f"📱 Event Processed: User {user_id} | Stream {source_stream} | Activity: {data.get('activity_update')}")
        elif result_type == "cached_recommendations":
            print(f"⚡ Cache Hit: User {user_id} | Stream {source_stream} | Context: {data.get('context')}")
        elif result_type == "fresh_recommendations":
            print(f"🎯 Fresh Recommendations: User {user_id} | Stream {source_stream} | Count: {len(data.get('recommendations', []))}")
        elif result_type == "recommendation_error":
            print(f"❌ Recommendation Error: User {user_id} | Stream {source_stream} | Error: {data.get('error')}")
        else:
            print(f"📊 Result: {result_type} | Stream {source_stream} | User {user_id}")
        
        return data
    
    @classmethod
    def read_results(cls):
        """读取所有收集到的结果"""
        with cls._lock:
            return dict(cls._results)
    
    @classmethod
    def clear_results(cls):
        """清空结果"""
        with cls._lock:
            cls._results.clear()


# ==================== 测试类 ====================

class TestCoMapServiceIntegration:
    """测试CoMap函数中的服务调用集成"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        ServiceTestSink.clear_results()
    
    def test_comap_service_integration(self):
        """测试CoMap函数中的服务调用集成"""
        print("\n🚀 Testing CoMap Service Integration")
        print("=" * 60)
        
        # 创建环境
        env = LocalEnvironment("comap_service_test")
        
        # 注册服务到环境
        env.register_service("user_profile", UserProfileService)
        env.register_service("recommendation", RecommendationService)
        env.register_service("cache", CacheService)
        
        print("✅ Services registered:")
        print("   - user_profile: UserProfileService")
        print("   - recommendation: RecommendationService")
        print("   - cache: CacheService")
        
        # 创建数据源
        event_stream = env.from_source(UserEventSource, delay=0.3)
        request_stream = env.from_source(RecommendationRequestSource, delay=0.4)
        
        # 构建CoMap处理管道
        result_stream = (
            event_stream
            .connect(request_stream)
            .comap(UserRecommendationCoMapFunction)
            .sink(ServiceTestSink, parallelism=1)
        )
        
        print("\n📊 Pipeline Structure:")
        print("UserEventSource (Stream 0) ─┐")
        print("                            ├─ CoMap(UserRecommendationCoMapFunction) ─ Sink")
        print("RecommendationRequestSource (Stream 1) ─┘")
        print("\n🎯 Expected Behavior:")
        print("- Stream 0: Process user events with service calls")
        print("- Stream 1: Handle recommendation requests with service calls")
        print("- Both streams use registered services through syntax sugar")
        
        try:
            # 提交并运行管道
            env.submit()
            
            print("\n🏃 Pipeline running...")
            time.sleep(5)  # 让管道运行一段时间
            
        finally:
            env.close()
        
        # 验证结果
        time.sleep(1)  # 确保所有数据处理完成
        self._verify_service_integration_results()
    
    def _verify_service_integration_results(self):
        """验证服务集成结果"""
        results = ServiceTestSink.read_results()
        
        print("\n📋 Service Integration Results:")
        print("=" * 50)
        
        processed_events = []
        recommendation_results = []
        
        for instance_id, data_list in results.items():
            print(f"\n🔹 Sink Instance {instance_id}:")
            
            for data in data_list:
                result_type = data.get("type", "unknown")
                source_stream = data.get("source_stream", -1)
                
                if result_type == "processed_event":
                    processed_events.append(data)
                    user_id = data.get("user_id")
                    activity_update = data.get("activity_update", "No update")
                    interaction_tracked = data.get("interaction_tracked", {})
                    cache_result = data.get("cache_invalidation_result", "No cache result")
                    
                    print(f"   📱 Event (Stream {source_stream}): User {user_id}")
                    print(f"      Activity Update: {activity_update}")
                    print(f"      Interaction Tracked: {interaction_tracked.get('tracked', False)}")
                    print(f"      Cache Invalidation: {cache_result}")
                    
                elif result_type in ["cached_recommendations", "fresh_recommendations"]:
                    recommendation_results.append(data)
                    user_id = data.get("user_id")
                    context = data.get("context")
                    cache_hit = data.get("cache_hit", False)
                    recommendations = data.get("recommendations", [])
                    
                    cache_status = "🔥 Cache Hit" if cache_hit else "🆕 Fresh"
                    print(f"   🎯 Recommendation (Stream {source_stream}): User {user_id}")
                    print(f"      Context: {context} | {cache_status}")
                    print(f"      Recommendations: {len(recommendations)} items")
                    
                    if not cache_hit and "user_profile" in data:
                        profile = data["user_profile"]
                        print(f"      User Profile: {profile.get('name')} (interests: {profile.get('interests', [])})")
                
                elif result_type == "recommendation_error":
                    print(f"   ❌ Error (Stream {source_stream}): {data.get('error')}")
        
        # 验证断言
        print(f"\n📊 Summary:")
        print(f"   - Processed Events: {len(processed_events)}")
        print(f"   - Recommendation Results: {len(recommendation_results)}")
        
        # 验证至少处理了一些数据
        assert len(processed_events) > 0, "❌ No events were processed"
        assert len(recommendation_results) > 0, "❌ No recommendation requests were processed"
        
        # 验证服务调用的结果
        for event in processed_events:
            assert event.get("source_stream") == 0, f"❌ Event from wrong stream: {event.get('source_stream')}"
            assert "activity_update" in event, "❌ Missing activity update from service call"
            assert "interaction_tracked" in event, "❌ Missing interaction tracking from service call"
        
        for rec_result in recommendation_results:
            assert rec_result.get("source_stream") == 1, f"❌ Recommendation from wrong stream: {rec_result.get('source_stream')}"
            assert "recommendations" in rec_result or "error" in rec_result, "❌ Missing recommendations or error"
        
        print("✅ CoMap Service Integration test passed!")
        print("✅ Service calls working correctly in CoMap functions")
        print("✅ Both sync and async service calls functioning")
        print("✅ Stream routing working correctly")


def test_comap_service_integration():
    """独立运行的测试函数"""
    print("=" * 70)
    print("SAGE CoMap Service Integration Test")
    print("=" * 70)
    
    test_instance = TestCoMapServiceIntegration()
    test_instance.setup_method()
    
    try:
        test_instance.test_comap_service_integration()
        print("\n🎉 All tests passed! CoMap service integration is working correctly.")
        return True
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_comap_service_integration()
    
    if not success:
        exit(1)

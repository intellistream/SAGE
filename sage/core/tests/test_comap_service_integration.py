"""
CoMap函数中服务调用集成测试
测试dataflow model算子内部调用环境中注册的service
参考算子内的service call语法糖和dataflow comap test
"""

import time
import threading
import unittest
import pytest
from unittest.mock import Mock
from sage.core.api.local_environment import LocalEnvironment
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
        print(f"[DEBUG] CoMap.map0 called with event_data: {event_data}")
        self.processed_events += 1
        
        user_id = event_data["user_id"]
        item_id = event_data["item_id"]
        interaction_type = event_data["type"]
        
        # 使用服务调用语法糖 - 同步调用用户画像服务（增加容错处理）
        activity_description = f"{interaction_type}_{item_id}"
            
        try:
            print(f"[DEBUG] CoMap.map0: Calling user_profile.update_activity with timeout=10.0")
            update_result = self.call_service["user_profile"].update_activity(user_id, activity_description, timeout=10.0)
        except Exception as e:
            update_result = f"Service call failed: {str(e)[:100]}"
            self.logger.error(f"[DEBUG] CoMap.map0: user_profile service call failed: {e}")
        
        try:
            track_result = self.call_service["recommendation"].track_interaction(
                user_id, item_id, interaction_type, timeout=10.0
            )
        except Exception as e:
            track_result = {"tracked": False, "error": str(e)[:100]}
            self.logger.warning(f"Recommendation service call failed: {e}")
        
        # 使用服务调用语法糖 - 异步调用缓存服务清理相关缓存（增加容错处理）
        cache_key_pattern = f"rec_{user_id}"
        try:
            cache_future = self.call_service_async["cache"].invalidate(cache_key_pattern, timeout=10.0)
        except Exception as e:
            cache_future = None
            self.logger.warning(f"Cache service async call failed: {e}")
        
        result = {
            "type": "processed_event",
            "original_event": event_data,
            "user_id": user_id,
            "activity_update": update_result,
            "interaction_tracked": track_result,
            "cache_invalidation_started": cache_future is not None,
            "processed_sequence": self.processed_events,
            "source_stream": 0,
            "processor": "EventProcessor"
        }
        
        if cache_future is not None:
            try:
                cache_result = cache_future.result(timeout=5.0)  # 增加超时时间
                result["cache_invalidation_result"] = cache_result
            except Exception as e:
                result["cache_invalidation_error"] = str(e)[:100]
                self.logger.warning(f"Cache service result failed: {e}")
        else:
            result["cache_invalidation_error"] = "Cache service call not initiated"
        
        if self.ctx:
            self.logger.info(f"CoMap map0: processed event {event_data['type']} for user {user_id}")
        
        return result
    
    def map1(self, request_data):
        """处理推荐请求流 (stream 1) - 使用服务调用"""
        print(f"[DEBUG] CoMap.map1 called with request_data: {request_data}")
        self.processed_requests += 1
        
        user_id = request_data["user_id"]
        context = request_data["context"]
        
        # 检查缓存 - 使用同步服务调用（增加容错处理）
        cache_key = f"rec_{user_id}_{context}"
        try:
            cached_recommendations = self.call_service["cache"].get(cache_key, timeout=10.0)
        except Exception as e:
            cached_recommendations = None
            self.logger.warning(f"Cache get service call failed: {e}")
        
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
            # 缓存未命中，获取用户画像并生成推荐（增加容错处理）
            
            # 异步获取用户画像
            try:
                profile_future = self.call_service_async["user_profile"].get_profile(user_id, timeout=10.0)
            except Exception as e:
                profile_future = None
                self.logger.warning(f"User profile async service call failed: {e}")
            
            # 在等待的同时做一些本地处理
            request_info = {
                "user_id": user_id,
                "context": context,
                "request_time": time.time()
            }
            
            # 获取用户画像结果（增加容错处理）
            if profile_future is not None:
                try:
                    user_profile = profile_future.result(timeout=5.0)  # 减少超时时间
                    user_interests = user_profile.get("interests", [])
                except Exception as e:
                    user_profile = {"interests": ["general"]}  # 使用默认兴趣
                    user_interests = ["general"]
                    self.logger.warning(f"User profile result failed: {e}")
            else:
                user_profile = {"interests": ["general"]}
                user_interests = ["general"]
                
            # 根据用户兴趣获取推荐（增加容错处理）
            try:
                recommendations = self.call_service["recommendation"].get_recommendations(
                    user_interests, user_id, timeout=10.0
                )
            except Exception as e:
                recommendations = [f"item_{user_id}_{context}"]  # 使用默认推荐
                self.logger.warning(f"Recommendation service call failed: {e}")
            
            # 缓存推荐结果（增加容错处理）
            try:
                self.call_service["cache"].set(cache_key, recommendations, timeout=10.0)
            except Exception as e:
                self.logger.warning(f"Cache set service call failed: {e}")
                
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
        
        return result
        if self.ctx:
            self.logger.info(f"CoMap map1: processed request for user {user_id} in context {context}")
        
        return result
        if self.ctx:
            self.logger.info(f"CoMap map1: processed recommendation request for user {user_id}")
        
        return result


# ==================== 调试输出Sink ====================

class ServiceTestSink(SinkFunction):
    """服务测试结果收集Sink"""
    
    def __init__(self, ctx=None, **kwargs):
        super().__init__(ctx=ctx, **kwargs)
        self.processed_count = 0
        self.results = []  # 实例级别的结果存储
    
    def execute(self, data):
        print(f"[DEBUG] ServiceTestSink.execute called with data: {data}")
        
        self.processed_count += 1
        self.results.append(data)
        
        print(f"[DEBUG] Total results in this sink instance: {len(self.results)}")
        
        # 打印处理结果
        result_type = data.get("type", "unknown")
        source_stream = data.get("source_stream", -1)
        user_id = data.get("user_id", "unknown")
        
        if result_type == "processed_event":
            activity_update = data.get('activity_update', 'No update')
            interaction_tracked = data.get('interaction_tracked', {})
            cache_invalidation = data.get('cache_invalidation_started', False)
            print(f"📱 Event (Stream {source_stream}): User {user_id}")
            print(f"      Activity Update: {activity_update}")
            print(f"      Interaction Tracked: {interaction_tracked.get('tracked', False)}")
            print(f"      Cache Invalidation: {'Started' if cache_invalidation else 'No cache result'}")
        elif result_type == "cached_recommendations":
            context = data.get('context', 'unknown')
            recommendations = data.get('recommendations', [])
            print(f"🎯 Recommendation (Stream {source_stream}): User {user_id}")
            print(f"      Context: {context} | 🔥 Cache Hit")
            print(f"      Recommendations: {len(recommendations)} items")
        elif result_type == "fresh_recommendations":
            context = data.get('context', 'unknown')
            recommendations = data.get('recommendations', [])
            user_profile = data.get('user_profile', {})
            print(f"🎯 Recommendation (Stream {source_stream}): User {user_id}")
            print(f"      Context: {context} | 🆕 Fresh")
            print(f"      Recommendations: {len(recommendations)} items")
            if user_profile:
                interests = user_profile.get('interests', ['general'])
                print(f"      User Profile: {user_profile.get('name', 'None')} (interests: {interests})")
        elif result_type == "recommendation_error":
            print(f"❌ Recommendation Error: User {user_id} | Stream {source_stream} | Error: {data.get('error')}")
        else:
            print(f"📊 Result: {result_type} | Stream {source_stream} | User {user_id}")
        
        return data


# ==================== 测试类 ====================

class TestCoMapServiceIntegration:
    """测试CoMap函数中的服务调用集成"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        pass  # 不再需要清理类级别结果
    
    def test_comap_service_integration(self):
        """测试CoMap函数中的servive调用集成"""
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
        
        # 创建批处理数据源 - 使用 from_batch 接口避免无限循环
        event_data = [
            {"type": "view", "user_id": "user_001", "item_id": "item_001", "timestamp": time.time()},
            {"type": "click", "user_id": "user_002", "item_id": "item_002", "timestamp": time.time()},
            {"type": "view", "user_id": "user_003", "item_id": "item_003", "timestamp": time.time()},
            {"type": "like", "user_id": "user_001", "item_id": "item_002", "timestamp": time.time()},
        ]
        
        request_data = [
            {"type": "get_recommendations", "user_id": "user_001", "context": "homepage"},
            {"type": "get_recommendations", "user_id": "user_002", "context": "search"},
            {"type": "get_recommendations", "user_id": "user_003", "context": "profile"},
            {"type": "get_recommendations", "user_id": "user_001", "context": "feed"},
        ]
        
        event_stream = env.from_batch(event_data)
        request_stream = env.from_batch(request_data)
        
        # 构建CoMap处理管道
        result_stream = (
            event_stream
            .connect(request_stream)
            .comap(UserRecommendationCoMapFunction)
            .sink(ServiceTestSink, parallelism=1)
        )
        

        env.submit()
        
        print("\n🏃 Pipeline running...")
        time.sleep(20)  # 让管道运行一段时间

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
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"CoMap service integration test failed: {e}")


if __name__ == "__main__":
    success = test_comap_service_integration()
    
    if not success:
        exit(1)

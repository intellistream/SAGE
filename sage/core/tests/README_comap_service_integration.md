# CoMap服务集成测试

## 概述

这个测试验证了在SAGE框架中，CoMap函数是否能够正确地调用环境中注册的服务。它模拟了一个真实的用户推荐系统场景，展示了如何在dataflow model算子内部使用service call语法糖。

## 测试场景

测试创建了一个双流CoMap处理场景：

### 数据流设计
```
UserEventSource (Stream 0) ─┐
                            ├─ CoMap(UserRecommendationCoMapFunction) ─ Sink
RecommendationRequestSource (Stream 1) ─┘
```

### 注册的服务
1. **UserProfileService** - 用户画像服务
   - `get_profile(user_id)` - 获取用户资料
   - `update_activity(user_id, activity)` - 更新用户活动

2. **RecommendationService** - 推荐服务  
   - `get_recommendations(interests, user_id)` - 获取推荐内容
   - `track_interaction(user_id, item_id, type)` - 跟踪用户交互

3. **CacheService** - 缓存服务
   - `get(key)` - 获取缓存
   - `set(key, value)` - 设置缓存
   - `invalidate(pattern)` - 清理缓存

## CoMap函数实现

### Stream 0 处理 (用户事件)
```python
def map0(self, event_data):
    # 同步服务调用 - 更新用户活动
    update_result = self.call_service["user_profile"].update_activity(user_id, activity)
    
    # 同步服务调用 - 跟踪交互
    track_result = self.call_service["recommendation"].track_interaction(user_id, item_id, type)
    
    # 异步服务调用 - 清理缓存
    cache_future = self.call_service_async["cache"].invalidate(cache_pattern)
    cache_result = cache_future.result(timeout=2.0)
```

### Stream 1 处理 (推荐请求)
```python
def map1(self, request_data):
    # 同步调用 - 检查缓存
    cached_recs = self.call_service["cache"].get(cache_key)
    
    if not cached_recs:
        # 异步调用 - 获取用户画像
        profile_future = self.call_service_async["user_profile"].get_profile(user_id)
        user_profile = profile_future.result(timeout=3.0)
        
        # 同步调用 - 生成推荐
        recommendations = self.call_service["recommendation"].get_recommendations(interests, user_id)
        
        # 同步调用 - 缓存结果
        self.call_service["cache"].set(cache_key, recommendations)
```

## 验证的功能

✅ **环境服务注册** - `env.register_service()` 正确注册服务  
✅ **CoMap流路由** - Stream 0和Stream 1正确路由到对应的map方法  
✅ **同步服务调用** - `self.call_service["service_name"].method()` 语法糖工作正常  
✅ **异步服务调用** - `self.call_service_async["service_name"].method().result()` 语法糖工作正常  
✅ **服务实例隔离** - 每个服务独立工作，状态不互相影响  
✅ **错误处理** - 服务调用超时和异常正确处理  

## 运行测试

```bash
cd /home/tjy/SAGE
python sage_tests/core_tests/test_comap_service_integration.py
```

## 测试输出示例

```
🚀 Testing CoMap Service Integration
✅ Services registered:
   - user_profile: UserProfileService
   - recommendation: RecommendationService  
   - cache: CacheService

📱 Event Processed: User user_001 | Stream 0 | Activity: Updated activity for user_001: view_item_001
🎯 Fresh Recommendations: User user_001 | Stream 1 | Count: 2

📊 Summary:
   - Processed Events: 4
   - Recommendation Results: 4
✅ CoMap Service Integration test passed!
```

## 技术要点

1. **语法糖一致性**: CoMap函数中的服务调用语法与普通Map函数完全一致 
2. **流隔离**: 不同输入流的数据通过不同的map方法处理，服务调用独立进行
3. **混合调用模式**: 同时展示了同步和异步服务调用的使用场景
4. **真实业务场景**: 模拟了推荐系统中常见的用户行为处理和推荐生成流程

这个测试完整验证了SAGE框架中CoMap函数的服务调用能力，确保了dataflow model在复杂业务场景下的可用性。

"""
现实工作流服务测试

展示在真实数据处理工作流中如何使用服务系统
"""

from sage_core.function.base_function import BaseFunction
from sage_core.api.local_environment import LocalEnvironment
import json
import time
import random


class FeatureStoreService:
    """特征存储服务"""
    
    def __init__(self):
        self.features = {
            "user_features": {
                "user_001": {"age": 25, "city": "Beijing", "vip_level": 2},
                "user_002": {"age": 30, "city": "Shanghai", "vip_level": 3},
                "user_003": {"age": 28, "city": "Guangzhou", "vip_level": 1}
            },
            "item_features": {
                "item_101": {"category": "electronics", "price": 1000, "rating": 4.5},
                "item_102": {"category": "books", "price": 50, "rating": 4.8},
                "item_103": {"category": "clothing", "price": 200, "rating": 4.2}
            }
        }
        self.is_running = False
        self.ctx = None
    
    def start_running(self):
        self.is_running = True
        print("Feature store service started")
    
    def terminate(self):
        self.is_running = False
        print("Feature store service terminated")
    
    def get_user_features(self, user_id: str):
        """获取用户特征"""
        features = self.features["user_features"].get(user_id, {})
        print(f"Retrieved user features for {user_id}: {features}")
        return features
    
    def get_item_features(self, item_id: str):
        """获取物品特征"""
        features = self.features["item_features"].get(item_id, {})
        print(f"Retrieved item features for {item_id}: {features}")
        return features
    
    def batch_get_features(self, entity_type: str, entity_ids: list):
        """批量获取特征"""
        feature_table = self.features.get(f"{entity_type}_features", {})
        results = {}
        for entity_id in entity_ids:
            results[entity_id] = feature_table.get(entity_id, {})
        print(f"Batch retrieved {len(results)} {entity_type} features")
        return results


class ModelService:
    """模型服务"""
    
    def __init__(self, model_name: str = "recommendation_model_v1"):
        self.model_name = model_name
        self.is_running = False
        self.ctx = None
        self.prediction_count = 0
    
    def start_running(self):
        self.is_running = True
        print(f"Model service started: {self.model_name}")
    
    def terminate(self):
        self.is_running = False
        print(f"Model service terminated: {self.model_name}")
    
    def predict(self, features: dict):
        """单个预测"""
        if not self.is_running:
            return {"error": "Model service not running"}
        
        self.prediction_count += 1
        
        # 模拟预测逻辑
        score = random.uniform(0.1, 0.9)
        result = {
            "score": round(score, 3),
            "prediction_id": f"pred_{self.prediction_count}",
            "model": self.model_name,
            "features_used": list(features.keys())
        }
        
        print(f"Model prediction {self.prediction_count}: score={result['score']}")
        return result
    
    def batch_predict(self, features_list: list):
        """批量预测"""
        if not self.is_running:
            return {"error": "Model service not running"}
        
        results = []
        for features in features_list:
            prediction = self.predict(features)
            results.append(prediction)
        
        print(f"Batch prediction completed: {len(results)} predictions")
        return results
    
    def get_model_info(self):
        """获取模型信息"""
        return {
            "name": self.model_name,
            "version": "1.0",
            "prediction_count": self.prediction_count,
            "status": "running" if self.is_running else "stopped"
        }


class RecommendationFunction(BaseFunction):
    """推荐算子，展示复杂的服务编排"""
    
    def __init__(self, recommender_id: str):
        super().__init__()
        self.recommender_id = recommender_id
    
    def execute(self, request):
        """执行推荐流程"""
        self.logger.info(f"Recommendation request: {request}")
        
        result = {
            "request_id": request.get("request_id", "unknown"),
            "user_id": request.get("user_id"),
            "recommender_id": self.recommender_id,
            "recommendations": [],
            "metadata": {}
        }
        
        try:
            # Step 1: 获取用户特征
            user_id = request.get("user_id")
            if not user_id:
                raise ValueError("User ID is required")
            
            user_features = self.call_service["feature_store"].get_user_features(user_id)
            if not user_features:
                self.call_service["log"].error(f"No features found for user {user_id}")
                raise ValueError(f"User {user_id} not found")
            
            result["metadata"]["user_features"] = user_features
            
            # Step 2: 获取候选物品
            candidate_items = request.get("candidate_items", ["item_101", "item_102", "item_103"])
            item_features = self.call_service["feature_store"].batch_get_features("item", candidate_items)
            result["metadata"]["candidate_count"] = len(candidate_items)
            
            # Step 3: 特征工程
            feature_vectors = self._create_feature_vectors(user_features, item_features)
            result["metadata"]["feature_vectors_created"] = len(feature_vectors)
            
            # Step 4: 模型预测
            predictions = self.call_service["model"].batch_predict(feature_vectors)
            
            # Step 5: 后处理和排序
            recommendations = self._post_process_predictions(candidate_items, predictions, user_features)
            result["recommendations"] = recommendations
            
            # Step 6: 缓存结果
            cache_key = f"rec_{user_id}_{hash(str(candidate_items))}"
            self.call_service["cache"].set(cache_key, recommendations)
            
            # Step 7: 记录分析数据
            self.call_service["analytics"].track_event("recommendation_generated", {
                "user_id": user_id,
                "candidate_count": len(candidate_items),
                "recommendation_count": len(recommendations),
                "recommender_id": self.recommender_id
            })
            
            self.call_service["analytics"].increment_metric("total_recommendations")
            
            # Step 8: 记录日志
            self.call_service["log"].info("Recommendation completed successfully", {
                "user_id": user_id,
                "recommendation_count": len(recommendations),
                "top_score": recommendations[0]["score"] if recommendations else 0
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Recommendation failed: {e}"
            self.logger.error(error_msg)
            
            self.call_service["log"].error(error_msg, {
                "user_id": request.get("user_id"),
                "recommender_id": self.recommender_id
            })
            
            result["error"] = str(e)
            return result
    
    def _create_feature_vectors(self, user_features, item_features):
        """创建特征向量"""
        feature_vectors = []
        
        for item_id, item_attrs in item_features.items():
            # 合并用户和物品特征
            vector = {
                **user_features,
                **item_attrs,
                "user_item_interaction": self._calculate_interaction_features(user_features, item_attrs)
            }
            feature_vectors.append(vector)
        
        return feature_vectors
    
    def _calculate_interaction_features(self, user_features, item_features):
        """计算交互特征"""
        # 简单的交互特征计算
        interaction_score = 0.0
        
        # VIP用户对高价物品的偏好
        if user_features.get("vip_level", 0) >= 2 and item_features.get("price", 0) > 500:
            interaction_score += 0.2
        
        # 年龄与电子产品的关联
        if user_features.get("age", 0) < 30 and item_features.get("category") == "electronics":
            interaction_score += 0.1
        
        return round(interaction_score, 3)
    
    def _post_process_predictions(self, candidate_items, predictions, user_features):
        """后处理预测结果"""
        recommendations = []
        
        for i, (item_id, prediction) in enumerate(zip(candidate_items, predictions)):
            rec = {
                "item_id": item_id,
                "score": prediction["score"],
                "rank": i + 1,
                "prediction_id": prediction["prediction_id"],
                "reasons": self._generate_reasons(user_features, prediction)
            }
            recommendations.append(rec)
        
        # 按分数排序
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        # 重新分配排名
        for i, rec in enumerate(recommendations):
            rec["rank"] = i + 1
        
        return recommendations
    
    def _generate_reasons(self, user_features, prediction):
        """生成推荐理由"""
        reasons = []
        
        if prediction["score"] > 0.7:
            reasons.append("High compatibility score")
        
        if user_features.get("vip_level", 0) >= 2:
            reasons.append("VIP member exclusive")
        
        city = user_features.get("city", "")
        if city in ["Beijing", "Shanghai"]:
            reasons.append(f"Popular in {city}")
        
        return reasons


def test_realistic_workflow():
    """测试现实工作流场景"""
    print("=== 现实工作流服务测试 ===")
    
    try:
        # 1. 创建环境并注册所有服务
        print("\n1. 创建环境并注册服务:")
        env = LocalEnvironment("workflow_test")
        
        # 注册业务服务
        env.register_service("feature_store", FeatureStoreService)
        env.register_service("model", ModelService, model_name="rec_model_v2")
        env.register_service("cache", CacheService, max_size=1000)
        env.register_service("log", LogService, log_level="INFO")
        env.register_service("analytics", AnalyticsService)
        
        print("所有业务服务注册完成")
        
        # 2. 启动所有服务
        print("\n2. 启动服务:")
        services = {}
        for service_name in env.service_task_factories:
            task_factory = env.service_task_factories[service_name]
            service_task = task_factory.create_service_task()
            service_task.start_running()
            services[service_name] = service_task
            print(f"服务 {service_name} 启动完成")
        
        # 3. 创建运行时上下文
        print("\n3. 创建业务处理器:")
        
        class MockServiceManager:
            def __init__(self, services):
                self.services = services
            
            def get_sync_proxy(self, service_name: str):
                if service_name in self.services:
                    return self.services[service_name].service
                raise KeyError(f"Service {service_name} not found")
            
            def get_async_proxy(self, service_name: str):
                return self.get_sync_proxy(service_name)
        
        class MockRuntimeContext:
            def __init__(self, name, services):
                self.name = name
                self.service_manager = MockServiceManager(services)
                import logging
                self.logger = logging.getLogger(name)
        
        # 4. 测试推荐工作流
        print("\n4. 测试推荐工作流:")
        
        rec_function = RecommendationFunction("recommender_alpha")
        rec_function.ctx = MockRuntimeContext("recommendation_processor", services)
        
        # 测试请求1
        request1 = {
            "request_id": "req_001",
            "user_id": "user_001",
            "candidate_items": ["item_101", "item_102", "item_103"]
        }
        
        result1 = rec_function.execute(request1)
        print(f"\n推荐结果1:")
        print(f"用户: {result1['user_id']}")
        print(f"推荐数量: {len(result1['recommendations'])}")
        
        for rec in result1['recommendations'][:2]:  # 显示前2个推荐
            print(f"  - {rec['item_id']}: score={rec['score']}, rank={rec['rank']}")
            print(f"    原因: {', '.join(rec['reasons'])}")
        
        # 测试请求2 - 不同用户
        print("\n5. 测试不同用户的推荐:")
        
        request2 = {
            "request_id": "req_002", 
            "user_id": "user_002",
            "candidate_items": ["item_101", "item_102"]
        }
        
        result2 = rec_function.execute(request2)
        print(f"\n推荐结果2:")
        print(f"用户: {result2['user_id']}")
        print(f"推荐数量: {len(result2['recommendations'])}")
        
        for rec in result2['recommendations']:
            print(f"  - {rec['item_id']}: score={rec['score']}, rank={rec['rank']}")
        
        # 6. 查看服务状态和指标
        print("\n6. 查看服务状态:")
        
        # 模型服务状态
        model_info = rec_function.call_service["model"].get_model_info()
        print(f"模型信息: {model_info}")
        
        # 分析指标
        metrics = rec_function.call_service["analytics"].get_metrics()
        print(f"分析指标: {metrics}")
        
        events = rec_function.call_service["analytics"].get_events()
        print(f"事件数量: {len(events)}")
        
        # 缓存状态
        cache_size = rec_function.call_service["cache"].size()
        print(f"缓存大小: {cache_size}")
        
        # 日志统计
        logs = rec_function.call_service["log"].get_logs()
        print(f"日志条数: {len(logs)}")
        
        # 7. 测试错误处理
        print("\n7. 测试错误处理:")
        
        invalid_request = {
            "request_id": "req_003",
            "user_id": "user_999",  # 不存在的用户
            "candidate_items": ["item_101"]
        }
        
        result3 = rec_function.execute(invalid_request)
        if "error" in result3:
            print(f"错误处理正常: {result3['error']}")
        
        # 8. 关闭所有服务
        print("\n8. 关闭服务:")
        for service_name, service_task in services.items():
            service_task.terminate()
            print(f"服务 {service_name} 已关闭")
        
        print("\n=== 现实工作流测试完成 ===")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


# 重用之前的服务类
class CacheService:
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
        result = self.cache.get(key, None)
        return result
    
    def set(self, key: str, value):
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value
        return True
    
    def size(self):
        return len(self.cache)


class LogService:
    def __init__(self, log_level: str = "INFO"):
        self.log_level = log_level
        self.logs = []
        self.is_running = False
        self.ctx = None
    
    def start_running(self):
        self.is_running = True
        print(f"Log service started with level {self.log_level}")
    
    def terminate(self):
        self.is_running = False
        print("Log service terminated")
    
    def log(self, level: str, message: str, context: dict = None):
        if not self.is_running:
            return False
        
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "message": message,
            "context": context or {}
        }
        self.logs.append(log_entry)
        print(f"[{log_entry['timestamp']}] {level}: {message}")
        return True
    
    def info(self, message: str, context: dict = None):
        return self.log("INFO", message, context)
    
    def error(self, message: str, context: dict = None):
        return self.log("ERROR", message, context)
    
    def get_logs(self):
        return self.logs.copy()


class AnalyticsService:
    def __init__(self):
        self.metrics = {}
        self.events = []
        self.is_running = False
        self.ctx = None
    
    def start_running(self):
        self.is_running = True
        print("Analytics service started")
    
    def terminate(self):
        self.is_running = False
        print("Analytics service terminated")
    
    def track_event(self, event_name: str, properties: dict = None):
        if not self.is_running:
            return False
        
        event = {
            "name": event_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "properties": properties or {}
        }
        self.events.append(event)
        print(f"Tracked event: {event_name}")
        return True
    
    def increment_metric(self, metric_name: str, value: int = 1):
        if not self.is_running:
            return False
        
        if metric_name not in self.metrics:
            self.metrics[metric_name] = 0
        self.metrics[metric_name] += value
        return True
    
    def get_metrics(self):
        return self.metrics.copy()
    
    def get_events(self):
        return self.events.copy()


if __name__ == "__main__":
    test_realistic_workflow()

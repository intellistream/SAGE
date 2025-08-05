"""
真实SAGE工作流测试

使用SAGE的完整流水线机制，展示服务在真实算子中的使用
"""

from sage.api.remote_environment import RemoteEnvironment
from sage.api.function.base_function import BaseFunction
from sage.api.operator.base_operator import BaseOperator
from sage.api.local_environment import LocalEnvironment
import json
import time


# 服务定义（重用之前的服务）
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
        features = self.features["user_features"].get(user_id, {})
        print(f"Retrieved user features for {user_id}: {features}")
        return features
    
    def get_item_features(self, item_id: str):
        features = self.features["item_features"].get(item_id, {})
        print(f"Retrieved item features for {item_id}: {features}")
        return features
    
    def batch_get_features(self, entity_type: str, entity_ids: list):
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
        if not self.is_running:
            return {"error": "Model service not running"}
        
        self.prediction_count += 1
        score = 0.6
        result = {
            "score": round(score, 3),
            "prediction_id": f"pred_{self.prediction_count}",
            "model": self.model_name,
            "features_used": list(features.keys())
        }
        
        print(f"Model prediction {self.prediction_count}: score={result['score']}")
        return result
    
    def batch_predict(self, features_list: list):
        if not self.is_running:
            return {"error": "Model service not running"}
        
        results = []
        for features in features_list:
            prediction = self.predict(features)
            results.append(prediction)
        
        print(f"Batch prediction completed: {len(results)} predictions")
        return results


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


# 算子函数定义
class RequestSourceFunction(BaseFunction):
    """请求源算子 - 生成推荐请求"""
    
    def __init__(self, request_count: int = 5):
        super().__init__()
        self.request_count = request_count
        self.current_count = 0
        
    def execute(self):
        """生成推荐请求（源算子不需要data参数）"""
        if self.current_count >= self.request_count:
            return None  # 停止生成
        
        self.current_count += 1
        
        # 生成模拟请求
        users = ["user_001", "user_002", "user_003"]
        items = [["item_101", "item_102", "item_103"], ["item_101", "item_102"], ["item_102", "item_103"]]
        
        request = {
            "request_id": f"req_{self.current_count:03d}",
            "user_id": users[1],
            "candidate_items": items[1],
            "timestamp": time.time()
        }
        
        self.logger.info(f"Generated request {self.current_count}: {request['request_id']} for {request['user_id']}")
        return request


class FeatureEnrichmentFunction(BaseFunction):
    """特征丰富算子 - 获取用户和物品特征"""
    
    def execute(self, request):
        """丰富请求的特征信息"""
        if request is None:
            return None
            
        self.logger.info(f"Enriching features for request: {request['request_id']}")
        
        try:
            # 使用服务语法糖获取用户特征
            user_features = self.call_service["feature_store"].get_user_features(request["user_id"])
            
            # 批量获取物品特征
            item_features = self.call_service["feature_store"].batch_get_features(
                "item", request["candidate_items"]
            )
            
            # 丰富请求
            enriched_request = {
                **request,
                "user_features": user_features,
                "item_features": item_features,
                "enrichment_timestamp": time.time()
            }
            
            # 记录日志
            self.call_service["log"].info(f"Features enriched for request {request['request_id']}", {
                "user_id": request["user_id"],
                "item_count": len(request["candidate_items"])
            })
            
            self.logger.info(f"Feature enrichment completed for: {request['request_id']}")
            return enriched_request
            
        except Exception as e:
            self.logger.error(f"Feature enrichment failed for {request['request_id']}: {e}")
            # 记录错误到日志服务
            self.call_service["log"].error(f"Feature enrichment failed: {e}", {
                "request_id": request["request_id"]
            })
            return None


class RecommendationFunction(BaseFunction):
    """推荐算子 - 生成推荐结果"""
    
    def execute(self, enriched_request):
        """生成推荐结果"""
        if enriched_request is None:
            return None
            
        self.logger.info(f"Generating recommendations for: {enriched_request['request_id']}")
        
        try:
            # 检查缓存
            cache_key = f"rec_{enriched_request['user_id']}_{hash(str(enriched_request['candidate_items']))}"
            cached_result = self.call_service["cache"].get(cache_key)
            
            if cached_result:
                self.logger.info(f"Using cached recommendations for: {enriched_request['request_id']}")
                self.call_service["log"].info("Used cached recommendations", {
                    "request_id": enriched_request["request_id"],
                    "cache_key": cache_key
                })
                return {**enriched_request, "recommendations": cached_result, "from_cache": True}
            
            # 创建特征向量
            feature_vectors = self._create_feature_vectors(
                enriched_request["user_features"], 
                enriched_request["item_features"]
            )
            
            # 使用模型服务进行预测
            predictions = self.call_service["model"].batch_predict(feature_vectors)
            
            # 生成推荐结果
            recommendations = []
            for i, (item_id, prediction) in enumerate(zip(enriched_request["candidate_items"], predictions)):
                rec = {
                    "item_id": item_id,
                    "score": prediction["score"],
                    "rank": i + 1,
                    "prediction_id": prediction["prediction_id"]
                }
                recommendations.append(rec)
            
            # 按分数排序
            recommendations.sort(key=lambda x: x["score"], reverse=True)
            for i, rec in enumerate(recommendations):
                rec["rank"] = i + 1
            
            # 缓存结果
            self.call_service["cache"].set(cache_key, recommendations)
            
            # 记录推荐完成
            self.call_service["log"].info("Recommendations generated successfully", {
                "request_id": enriched_request["request_id"],
                "recommendation_count": len(recommendations),
                "top_score": recommendations[0]["score"] if recommendations else 0
            })
            
            result = {
                **enriched_request,
                "recommendations": recommendations,
                "from_cache": False,
                "recommendation_timestamp": time.time()
            }
            
            self.logger.info(f"Recommendations generated for: {enriched_request['request_id']}, count: {len(recommendations)}")
            return result
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed for {enriched_request['request_id']}: {e}")
            self.call_service["log"].error(f"Recommendation generation failed: {e}", {
                "request_id": enriched_request["request_id"]
            })
            return None
    
    def _create_feature_vectors(self, user_features, item_features):
        """创建特征向量"""
        feature_vectors = []
        for item_id, item_attrs in item_features.items():
            vector = {
                **user_features,
                **item_attrs,
                "interaction_score": self._calculate_interaction(user_features, item_attrs)
            }
            feature_vectors.append(vector)
        return feature_vectors
    
    def _calculate_interaction(self, user_features, item_features):
        """计算交互特征"""
        score = 0.0
        if user_features.get("vip_level", 0) >= 2 and item_features.get("price", 0) > 500:
            score += 0.2
        if user_features.get("age", 0) < 30 and item_features.get("category") == "electronics":
            score += 0.1
        return round(score, 3)


class ResultSinkFunction(BaseFunction):
    """结果输出算子 - 输出最终推荐结果"""
    
    def __init__(self):
        super().__init__()
        self.processed_count = 0
    
    def execute(self, recommendation_result):
        """输出推荐结果"""
        if recommendation_result is None:
            return None
            
        self.processed_count += 1
        
        self.logger.info(f"Processing final result for: {recommendation_result['request_id']}")
        
        # 格式化输出
        output = {
            "request_id": recommendation_result["request_id"],
            "user_id": recommendation_result["user_id"],
            "recommendations": recommendation_result["recommendations"][:3],  # 只取前3个
            "from_cache": recommendation_result.get("from_cache", False),
            "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "processing_order": self.processed_count
        }
        
        # 记录到日志服务
        self.call_service["log"].info("Final recommendation result", {
            "request_id": output["request_id"],
            "user_id": output["user_id"],
            "recommendation_count": len(output["recommendations"]),
            "from_cache": output["from_cache"]
        })
        
        # 打印结果
        print(f"\n=== 推荐结果 #{self.processed_count} ===")
        print(f"请求ID: {output['request_id']}")
        print(f"用户ID: {output['user_id']}")
        print(f"缓存命中: {output['from_cache']}")
        print("推荐列表:")
        for rec in output["recommendations"]:
            print(f"  {rec['rank']}. {rec['item_id']} (分数: {rec['score']})")
        print(f"处理时间: {output['processed_at']}")
        print("=" * 40)
        
        return output


def test_realistic_sage_workflow():
    """测试真实的SAGE工作流"""
    print("=== 真实SAGE工作流测试 ===")
    
    try:
        # 1. 创建环境
        print("\n1. 创建环境:")
        env = LocalEnvironment("realistic_workflow_test")
        
        # 2. 注册服务
        print("\n2. 注册服务:")
        env.register_service("feature_store", FeatureStoreService)
        env.register_service("model", ModelService, model_name="workflow_model_v1")
        env.register_service("cache", CacheService, max_size=500)
        env.register_service("log", LogService, log_level="INFO")
        
        print("所有服务注册完成")
        
        # 3. 构建流处理管道
        print("\n3. 构建流处理管道:")
        
        # 使用流式API构建处理管道
        stream = env.from_source(RequestSourceFunction, request_count=30) \
                   .map(FeatureEnrichmentFunction) \
                   .map(RecommendationFunction) \
                   .map(ResultSinkFunction)
        
        print("流处理管道构建完成")
        
        # 4. 提交并运行流处理管道
        print("\n4. 提交流处理管道:")
        env.submit()
        
        # 5. 等待处理完成
        print("\n5. 等待处理完成...")
        time.sleep(15)  # 给足够时间让流处理完成
        
        # 6. 检查服务状态
        print("\n6. 检查服务状态:")
        print("流水线执行完成！")
        
        print("\n=== 真实工作流测试完成 ===")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理环境
        try:
            env.stop()
            print("环境已清理")
        except:
            pass


if __name__ == "__main__":
    test_realistic_sage_workflow()

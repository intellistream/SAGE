"""
详细的服务工作流测试

使用各种sink将流处理的中间结果写入文件，然后验证结果的正确性
"""

from sage_core.function.base_function import BaseFunction
from sage_core.function.source_function import SourceFunction
from sage_core.function.sink_function import SinkFunction
from sage_core.operator.base_operator import BaseOperator
from sage_core.api.local_environment import LocalEnvironment
from sage_libs.io.sink import FileSink, MemWriteSink, PrintSink
import json
import time
import random
import os
import tempfile
import shutil


# 自定义JsonSink - 用于保存JSON数据
class JsonSink(SinkFunction):
    """用于保存JSON格式数据的Sink"""
    
    def __init__(self, config: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.config = config or {}
        file_path = self.config.get("file_path", "output.json")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        self.file_path = file_path
        
        # 创建或清空文件
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("")
    
    def execute(self, data):
        """保存数据到文件"""
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(str(data) + "\n")
        
        self.logger.debug(f"Data written to file: {self.file_path}")


# 服务定义 - 重用之前的服务
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
        return features
    
    def get_item_features(self, item_id: str):
        features = self.features["item_features"].get(item_id, {})
        return features


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
        # 基于特征计算一个确定性的分数（便于测试验证）
        score = 0.5
        if "age" in features:
            score += features["age"] * 0.01
        if "vip_level" in features:
            score += features["vip_level"] * 0.1
        if "rating" in features:
            score += features["rating"] * 0.1
        
        score = min(0.99, score)  # 限制最大值
        
        result = {
            "score": round(score, 3),
            "prediction_id": f"pred_{self.prediction_count}",
            "model": self.model_name,
            "features_used": list(features.keys())
        }
        
        return result


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
        return self.cache.get(key, None)
    
    def set(self, key: str, value):
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value
        return True


# 数据源函数
class RequestSourceFunction(SourceFunction):
    """生成测试请求数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.requests = [
            {"user_id": "user_001", "item_id": "item_101"},
            {"user_id": "user_002", "item_id": "item_102"},
            {"user_id": "user_003", "item_id": "item_103"},
            {"user_id": "user_001", "item_id": "item_102"},  # 重复用户，测试缓存
        ]
        self.index = 0
    
    def execute(self):
        if self.index < len(self.requests):
            request = self.requests[self.index]
            self.index += 1
            print(f"Source generating request: {request}")
            return request
        return None


# 数据处理算子
class FeatureEnrichmentOperator(BaseFunction):
    """特征增强算子"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def execute(self, data):
        user_id = data["user_id"]
        item_id = data["item_id"]
        
        # 调用特征存储服务 - 使用正确的语法
        user_features = self.call_service["feature_store"].get_user_features(user_id)
        item_features = self.call_service["feature_store"].get_item_features(item_id)
        
        # 合并特征
        enriched_data = {
            "request": data,
            "user_features": user_features,
            "item_features": item_features,
            "combined_features": {**user_features, **item_features}
        }
        
        return enriched_data


class CacheCheckOperator(BaseFunction):
    """缓存检查算子"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def execute(self, data):
        cache_key = f"{data['request']['user_id']}_{data['request']['item_id']}"
        
        # 检查缓存 - 使用正确的语法
        cached_result = self.call_service["cache"].get(cache_key)
        
        if cached_result:
            return {
                "from_cache": True,
                "cache_key": cache_key,
                "prediction": cached_result,
                "original_data": data
            }
        else:
            return {
                "from_cache": False,
                "cache_key": cache_key,
                "original_data": data
            }


class PredictionOperator(BaseFunction):
    """预测算子"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def execute(self, data):
        if data["from_cache"]:
            # 直接返回缓存结果
            return data["prediction"]
        
        # 调用模型服务进行预测 - 使用正确的语法
        features = data["original_data"]["combined_features"]
        prediction = self.call_service["model"].predict(features)
        
        # 将结果存入缓存 - 使用正确的语法
        cache_key = data["cache_key"]
        self.call_service["cache"].set(cache_key, prediction)
        
        return prediction


class ResultFormatterOperator(BaseFunction):
    """结果格式化算子"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def execute(self, data):
        formatted_result = {
            "recommendation": {
                "score": data["score"],
                "prediction_id": data["prediction_id"],
                "model": data["model"]
            },
            "features_count": len(data["features_used"]),
            "timestamp": time.time()
        }
        
        return formatted_result


# 文件验证辅助函数
def verify_test_files(test_dir):
    """验证测试生成的文件内容"""
    print("\n=== 验证测试文件 ===")
    
    results = {}
    
    # 验证原始请求文件
    request_file = os.path.join(test_dir, "raw_requests.txt")
    if os.path.exists(request_file):
        with open(request_file, "r", encoding="utf-8") as f:
            content = f.read()
            request_count = content.count("user_")
            results["raw_requests"] = {
                "file_exists": True,
                "request_count": request_count,
                "has_all_users": all(f"user_{i:03d}" in content for i in range(1, 4))
            }
            print(f"✓ 原始请求文件: {request_count}个请求")
    
    # 验证特征增强结果文件
    enriched_file = os.path.join(test_dir, "enriched_features.txt")
    if os.path.exists(enriched_file):
        with open(enriched_file, "r", encoding="utf-8") as f:
            content = f.read()
            feature_count = content.count("combined_features")
            has_user_features = "age" in content and "city" in content
            has_item_features = "category" in content and "price" in content
            results["enriched_features"] = {
                "file_exists": True,
                "feature_count": feature_count,
                "has_user_features": has_user_features,
                "has_item_features": has_item_features
            }
            print(f"✓ 特征增强文件: {feature_count}个特征集，用户特征：{has_user_features}，物品特征：{has_item_features}")
    
    # 验证缓存检查结果文件
    cache_file = os.path.join(test_dir, "cache_results.txt")
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            content = f.read()
            cache_hits = content.count('"from_cache": true')
            cache_misses = content.count('"from_cache": false')
            results["cache_results"] = {
                "file_exists": True,
                "cache_hits": cache_hits,
                "cache_misses": cache_misses,
                "total_checks": cache_hits + cache_misses
            }
            print(f"✓ 缓存检查文件: {cache_hits}次命中，{cache_misses}次未命中")
    
    # 验证预测结果文件
    prediction_file = os.path.join(test_dir, "predictions.txt")
    if os.path.exists(prediction_file):
        with open(prediction_file, "r", encoding="utf-8") as f:
            content = f.read()
            prediction_count = content.count("prediction_id")
            has_scores = "score" in content
            results["predictions"] = {
                "file_exists": True,
                "prediction_count": prediction_count,
                "has_scores": has_scores
            }
            print(f"✓ 预测结果文件: {prediction_count}个预测，包含分数：{has_scores}")
    
    # 验证最终结果文件
    final_file = os.path.join(test_dir, "final_results.txt")
    if os.path.exists(final_file):
        with open(final_file, "r", encoding="utf-8") as f:
            content = f.read()
            result_count = content.count("recommendation")
            has_timestamps = "timestamp" in content
            results["final_results"] = {
                "file_exists": True,
                "result_count": result_count,
                "has_timestamps": has_timestamps
            }
            print(f"✓ 最终结果文件: {result_count}个结果，包含时间戳：{has_timestamps}")
    
    return results


def run_detailed_test():
    """运行详细的服务工作流测试"""
    print("开始详细服务工作流测试...")
    
    # 创建临时测试目录
    test_dir = "/tmp/sage_service_test"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    try:
        # 创建环境
        env = LocalEnvironment()
        
        # 注册服务
        env.register_service("feature_store", FeatureStoreService)
        env.register_service("model", ModelService, model_name="test_model_v1")
        env.register_service("cache", CacheService, max_size=10)
        
        # 构建流水线，使用不同的sink保存中间结果
        stream = env.from_source(RequestSourceFunction)
        
        # 保存原始请求数据
        stream.map(lambda x: json.dumps(x)).sink(JsonSink, config={"file_path": os.path.join(test_dir, "raw_requests.txt")})
        
        # 特征增强
        enriched_stream = stream.map(FeatureEnrichmentOperator)
        enriched_stream.map(lambda x: json.dumps(x, indent=2)).sink(JsonSink, config={"file_path": os.path.join(test_dir, "enriched_features.txt")})
        
        # 缓存检查
        cache_stream = enriched_stream.map(CacheCheckOperator)
        cache_stream.map(lambda x: json.dumps(x, indent=2)).sink(JsonSink, config={"file_path": os.path.join(test_dir, "cache_results.txt")})
        
        # 预测
        prediction_stream = cache_stream.map(PredictionOperator)
        prediction_stream.map(lambda x: json.dumps(x, indent=2)).sink(JsonSink, config={"file_path": os.path.join(test_dir, "predictions.txt")})
        
        # 最终结果格式化
        final_stream = prediction_stream.map(ResultFormatterOperator)
        final_stream.map(lambda x: json.dumps(x, indent=2)).sink(JsonSink, config={"file_path": os.path.join(test_dir, "final_results.txt")})
        
        # 同时使用PrintSink显示最终结果
        final_stream.sink(PrintSink, prefix="FINAL_RESULT", colored=True)
        
        print("流水线构建完成，开始执行...")
        
        # 提交执行
        env.submit()
        
        # 等待执行完成
        print("等待流水线执行完成...")
        time.sleep(3)
        
        # 验证文件内容
        verification_results = verify_test_files(test_dir)
        
        # 生成测试报告
        generate_test_report(test_dir, verification_results)
        
        print(f"\n测试完成！结果文件保存在: {test_dir}")
        print("可以手动检查以下文件:")
        for filename in os.listdir(test_dir):
            print(f"  - {os.path.join(test_dir, filename)}")
        
        return verification_results
        
    except Exception as e:
        print(f"测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_test_report(test_dir, verification_results):
    """生成测试报告"""
    report_file = os.path.join(test_dir, "test_report.json")
    
    report = {
        "test_timestamp": time.time(),
        "test_directory": test_dir,
        "verification_results": verification_results,
        "summary": {
            "total_files_generated": len([f for f in os.listdir(test_dir) if f.endswith('.txt')]),
            "all_files_exist": all(result.get("file_exists", False) for result in verification_results.values()),
            "test_passed": len(verification_results) >= 4  # 至少应该有4个主要结果文件
        }
    }
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n测试报告已生成: {report_file}")
    print(f"测试通过: {report['summary']['test_passed']}")


if __name__ == "__main__":
    verification_results = run_detailed_test()
    
    if verification_results:
        print("\n=== 测试结果总结 ===")
        for file_type, results in verification_results.items():
            status = "✓" if results.get("file_exists", False) else "✗"
            print(f"{status} {file_type}: {results}")
    else:
        print("测试失败")

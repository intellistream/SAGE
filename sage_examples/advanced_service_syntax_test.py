"""
高级服务语法糖测试

测试更复杂的服务调用场景，包括链式调用、条件调用等
"""

from sage_core.function.base_function import BaseFunction
from sage_core.api.local_environment import LocalEnvironment
import json
import time


class ConfigService:
    """配置服务"""
    
    def __init__(self):
        self.config = {
            "processing": {
                "batch_size": 100,
                "timeout": 30,
                "retry_count": 3
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "max_connections": 10
            },
            "features": {
                "caching_enabled": True,
                "logging_enabled": True,
                "analytics_enabled": False
            }
        }
        self.is_running = False
        self.ctx = None
    
    def start_running(self):
        self.is_running = True
        print("Config service started")
    
    def terminate(self):
        self.is_running = False
        print("Config service terminated")
    
    def get(self, key: str, default=None):
        """获取配置值，支持点号分隔的嵌套键"""
        try:
            keys = key.split('.')
            value = self.config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value):
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        return True
    
    def get_all(self):
        """获取所有配置"""
        return self.config.copy()


class LogService:
    """日志服务"""
    
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
        """记录日志"""
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
    
    def debug(self, message: str, context: dict = None):
        return self.log("DEBUG", message, context)
    
    def get_logs(self, level_filter: str = None):
        """获取日志，可按级别过滤"""
        if level_filter:
            return [log for log in self.logs if log["level"] == level_filter]
        return self.logs.copy()


class AnalyticsService:
    """分析服务"""
    
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
        """跟踪事件"""
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
        """增加指标计数"""
        if not self.is_running:
            return False
        
        if metric_name not in self.metrics:
            self.metrics[metric_name] = 0
        self.metrics[metric_name] += value
        print(f"Metric {metric_name}: {self.metrics[metric_name]}")
        return True
    
    def get_metrics(self):
        """获取所有指标"""
        return self.metrics.copy()
    
    def get_events(self, event_filter: str = None):
        """获取事件，可按名称过滤"""
        if event_filter:
            return [event for event in self.events if event["name"] == event_filter]
        return self.events.copy()


class CacheService:
    """缓存服务（重用之前的实现）"""
    
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
        print(f"Cache GET {key}: {result}")
        return result
    
    def set(self, key: str, value):
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value
        print(f"Cache SET {key}: {value}")
        return True
    
    def size(self):
        return len(self.cache)


class SmartProcessFunction(BaseFunction):
    """智能处理函数，展示复杂的服务调用场景"""
    
    def __init__(self, processor_id: str):
        super().__init__()
        self.processor_id = processor_id
    
    def execute(self, data):
        """执行智能处理逻辑"""
        self.logger.info(f"Smart processing started by {self.processor_id}")
        
        result = {
            "processor_id": self.processor_id,
            "input": data,
            "steps": [],
            "metrics": {}
        }
        
        try:
            # 1. 获取配置并记录日志
            config = self._load_configuration()
            result["config"] = config
            result["steps"].append("configuration_loaded")
            
            # 2. 条件性地启用功能
            if config.get("caching_enabled", False):
                self._handle_caching(data, result)
                result["steps"].append("caching_handled")
            
            if config.get("logging_enabled", False):
                self._log_processing_steps(data, result)
                result["steps"].append("logging_enabled")
            
            if config.get("analytics_enabled", False):
                self._track_analytics(data, result)
                result["steps"].append("analytics_tracked")
            
            # 3. 执行核心处理逻辑
            processed_data = self._core_processing(data, config)
            result["processed_data"] = processed_data
            result["steps"].append("core_processing_completed")
            
            # 4. 记录处理指标
            self._record_metrics(result)
            result["steps"].append("metrics_recorded")
            
            self.logger.info(f"Smart processing completed successfully")
            return result
            
        except Exception as e:
            error_msg = f"Error in smart processing: {e}"
            self.logger.error(error_msg)
            
            # 记录错误到日志服务
            try:
                self.call_service["log"].error(error_msg, {
                    "processor_id": self.processor_id,
                    "input": str(data)
                })
            except:
                pass
            
            result["error"] = str(e)
            return result
    
    def _load_configuration(self):
        """加载配置"""
        try:
            # 获取处理相关配置
            processing_config = self.call_service["config"].get("processing", {})
            features_config = self.call_service["config"].get("features", {})
            
            # 合并配置
            config = {**processing_config, **features_config}
            
            self.call_service["log"].info("Configuration loaded successfully", {
                "processor_id": self.processor_id,
                "config_keys": list(config.keys())
            })
            
            return config
            
        except Exception as e:
            self.logger.warning(f"Failed to load configuration: {e}")
            return {}
    
    def _handle_caching(self, data, result):
        """处理缓存逻辑"""
        cache_key = f"smart_process_{self.processor_id}_{data.get('id', 'unknown')}"
        
        # 检查缓存
        cached_result = self.call_service["cache"].get(cache_key)
        if cached_result:
            result["from_cache"] = True
            result["cached_data"] = cached_result
            self.call_service["log"].info("Used cached result", {
                "cache_key": cache_key
            })
        else:
            result["from_cache"] = False
            self.call_service["log"].debug("No cached result found", {
                "cache_key": cache_key
            })
    
    def _log_processing_steps(self, data, result):
        """记录处理步骤"""
        self.call_service["log"].info("Processing started", {
            "processor_id": self.processor_id,
            "data_type": type(data).__name__,
            "data_size": len(str(data))
        })
    
    def _track_analytics(self, data, result):
        """跟踪分析数据"""
        # 跟踪处理事件
        self.call_service["analytics"].track_event("processing_started", {
            "processor_id": self.processor_id,
            "data_type": type(data).__name__
        })
        
        # 增加处理计数
        self.call_service["analytics"].increment_metric("total_processed")
        self.call_service["analytics"].increment_metric(f"processor_{self.processor_id}_count")
    
    def _core_processing(self, data, config):
        """核心处理逻辑"""
        batch_size = config.get("batch_size", 50)
        timeout = config.get("timeout", 10)
        
        processed = {
            "original": data,
            "batch_size": batch_size,
            "timeout": timeout,
            "processing_time": time.time(),
            "enhanced": True
        }
        
        # 模拟一些处理逻辑
        if isinstance(data, dict) and "items" in data:
            processed["item_count"] = len(data["items"])
            processed["batches"] = (len(data["items"]) + batch_size - 1) // batch_size
        
        return processed
    
    def _record_metrics(self, result):
        """记录处理指标"""
        try:
            metrics = {
                "steps_completed": len(result["steps"]),
                "has_error": "error" in result,
                "from_cache": result.get("from_cache", False)
            }
            
            result["metrics"] = metrics
            
            # 记录到分析服务
            if self.call_service["config"].get("features.analytics_enabled", False):
                for metric_name, value in metrics.items():
                    if isinstance(value, bool):
                        value = 1 if value else 0
                    if isinstance(value, int):
                        self.call_service["analytics"].increment_metric(
                            f"processing_{metric_name}", value
                        )
        
        except Exception as e:
            self.logger.warning(f"Failed to record metrics: {e}")


def test_advanced_service_syntax():
    """测试高级服务语法糖功能"""
    print("=== 高级服务语法糖测试 ===")
    
    try:
        # 1. 创建环境并注册所有服务
        print("\n1. 创建环境并注册服务:")
        env = LocalEnvironment("advanced_service_test")
        
        # 注册各种服务
        env.register_service("config", ConfigService)
        env.register_service("log", LogService, log_level="DEBUG")
        env.register_service("analytics", AnalyticsService)
        env.register_service("cache", CacheService, max_size=200)
        
        print("所有服务注册完成")
        
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
        print("\n3. 创建运行时上下文:")
        
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
        
        # 4. 测试智能处理函数
        print("\n4. 测试智能处理函数:")
        
        smart_func = SmartProcessFunction("processor_001")
        smart_func.ctx = MockRuntimeContext("smart_processor", services)
        
        # 测试数据
        test_data = {
            "id": "task_789",
            "type": "batch_processing",
            "items": [f"item_{i}" for i in range(25)],
            "priority": "high"
        }
        
        # 执行处理
        result = smart_func.execute(test_data)
        
        print("\n智能处理结果:")
        print(f"处理器ID: {result['processor_id']}")
        print(f"完成步骤: {result['steps']}")
        print(f"处理指标: {result.get('metrics', {})}")
        print(f"从缓存获取: {result.get('from_cache', False)}")
        
        if 'processed_data' in result:
            processed = result['processed_data']
            print(f"处理后数据:")
            print(f"  - 项目数量: {processed.get('item_count', 'N/A')}")
            print(f"  - 批次数量: {processed.get('batches', 'N/A')}")
            print(f"  - 批次大小: {processed.get('batch_size', 'N/A')}")
        
        # 5. 测试服务状态查询
        print("\n5. 查询服务状态:")
        
        # 查询日志
        logs = smart_func.call_service["log"].get_logs()
        print(f"总日志条数: {len(logs)}")
        
        # 查询分析数据
        metrics = smart_func.call_service["analytics"].get_metrics()
        print(f"分析指标: {metrics}")
        
        events = smart_func.call_service["analytics"].get_events()
        print(f"跟踪事件数: {len(events)}")
        
        # 查询配置
        all_config = smart_func.call_service["config"].get_all()
        print(f"配置项数: {len(all_config)}")
        
        # 6. 测试配置修改
        print("\n6. 测试动态配置修改:")
        
        # 启用分析功能
        smart_func.call_service["config"].set("features.analytics_enabled", True)
        print("已启用分析功能")
        
        # 再次处理以测试分析功能
        test_data2 = {
            "id": "task_790",
            "type": "analytics_test",
            "items": [f"item_{i}" for i in range(10)]
        }
        
        result2 = smart_func.execute(test_data2)
        print(f"第二次处理完成，步骤: {result2['steps']}")
        
        # 查看更新后的指标
        updated_metrics = smart_func.call_service["analytics"].get_metrics()
        print(f"更新后的指标: {updated_metrics}")
        
        # 7. 关闭所有服务
        print("\n7. 关闭服务:")
        for service_name, service_task in services.items():
            service_task.terminate()
            print(f"服务 {service_name} 已关闭")
        
        print("\n=== 高级测试完成 ===")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_advanced_service_syntax()

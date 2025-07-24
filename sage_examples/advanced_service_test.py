"""
高级服务系统测试

展示更复杂的服务使用场景，包括：
1. 数据处理管道服务
2. 缓存服务与数据库服务的协作
3. 监控和统计服务
4. 多服务协同工作
"""

import time
import random
import json
from typing import List, Dict, Any
from sage_core.api.local_environment import LocalEnvironment


class DataProcessorService:
    """
    数据处理服务
    模拟数据清洗、转换和验证功能
    """
    
    def __init__(self, batch_size: int = 100, workers: int = 4):
        self.batch_size = batch_size
        self.workers = workers
        self.is_running = False
        self.processed_count = 0
        self.error_count = 0
        self.ctx = None
        
        # 模拟处理规则
        self.processing_rules = {
            'normalize_text': lambda x: x.strip().lower() if isinstance(x, str) else x,
            'validate_email': lambda x: '@' in x if isinstance(x, str) else False,
            'extract_numbers': lambda x: [int(i) for i in x.split() if i.isdigit()] if isinstance(x, str) else []
        }
    
    def start_running(self):
        self.is_running = True
        print(f"Data processor started with {self.workers} workers, batch size {self.batch_size}")
    
    def terminate(self):
        self.is_running = False
        print(f"Data processor terminated. Processed: {self.processed_count}, Errors: {self.error_count}")
    
    def process_batch(self, data_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理一批数据"""
        if not self.is_running:
            raise RuntimeError("Data processor is not running")
        
        processed_batch = []
        for item in data_batch:
            try:
                processed_item = self._process_single_item(item)
                processed_batch.append(processed_item)
                self.processed_count += 1
            except Exception as e:
                self.error_count += 1
                print(f"Error processing item {item}: {e}")
        
        # 模拟处理时间
        time.sleep(0.1)
        return processed_batch
    
    def _process_single_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个数据项"""
        processed = item.copy()
        
        # 应用处理规则
        for field, value in item.items():
            if field == 'text' and value:
                processed[field] = self.processing_rules['normalize_text'](value)
            elif field == 'email' and value:
                processed['email_valid'] = self.processing_rules['validate_email'](value)
            elif field == 'numbers' and value:
                processed['extracted_numbers'] = self.processing_rules['extract_numbers'](value)
        
        processed['processed_timestamp'] = time.time()
        return processed
    
    def get_statistics(self) -> Dict[str, Any]:
        return {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'success_rate': self.processed_count / (self.processed_count + self.error_count) if (self.processed_count + self.error_count) > 0 else 0
        }


class SmartCacheService:
    """
    智能缓存服务
    支持TTL、LRU策略和命中率统计
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.is_running = False
        self.cache = {}
        self.access_times = {}
        self.ttl_times = {}
        self.hit_count = 0
        self.miss_count = 0
        self.ctx = None
    
    def start_running(self):
        self.is_running = True
        print(f"Smart cache started: max_size={self.max_size}, default_ttl={self.default_ttl}s")
    
    def terminate(self):
        self.is_running = False
        print(f"Smart cache terminated. Hit rate: {self.get_hit_rate():.2%}")
    
    def get(self, key: str) -> Any:
        """获取缓存值"""
        if not self.is_running:
            return None
        
        current_time = time.time()
        
        # 检查是否存在且未过期
        if key in self.cache and current_time < self.ttl_times.get(key, 0):
            self.access_times[key] = current_time
            self.hit_count += 1
            return self.cache[key]
        else:
            # 清理过期项
            if key in self.cache:
                self._remove_key(key)
            self.miss_count += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """设置缓存值"""
        if not self.is_running:
            return False
        
        # 如果缓存已满，使用LRU策略移除最久未访问的项
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict_lru()
        
        current_time = time.time()
        ttl = ttl or self.default_ttl
        
        self.cache[key] = value
        self.access_times[key] = current_time
        self.ttl_times[key] = current_time + ttl
        
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        if key in self.cache:
            self._remove_key(key)
            return True
        return False
    
    def _remove_key(self, key: str):
        """移除指定key"""
        self.cache.pop(key, None)
        self.access_times.pop(key, None)
        self.ttl_times.pop(key, None)
    
    def _evict_lru(self):
        """移除最久未访问的项"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self._remove_key(lru_key)
        print(f"Evicted LRU key: {lru_key}")
    
    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0
    
    def get_statistics(self) -> Dict[str, Any]:
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': self.get_hit_rate(),
            'utilization': len(self.cache) / self.max_size
        }


class MonitoringService:
    """
    监控服务
    收集和报告系统指标
    """
    
    def __init__(self, collection_interval: int = 10, max_metrics: int = 10000):
        self.collection_interval = collection_interval
        self.max_metrics = max_metrics
        self.is_running = False
        self.metrics_data = []
        self.alert_rules = {}
        self.ctx = None
    
    def start_running(self):
        self.is_running = True
        print(f"Monitoring service started: interval={self.collection_interval}s")
    
    def terminate(self):
        self.is_running = False
        print(f"Monitoring service terminated. Collected {len(self.metrics_data)} metrics")
    
    def collect_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """收集指标"""
        if not self.is_running:
            return
        
        metric = {
            'name': name,
            'value': value,
            'timestamp': time.time(),
            'tags': tags or {}
        }
        
        self.metrics_data.append(metric)
        
        # 保持最大指标数量
        if len(self.metrics_data) > self.max_metrics:
            self.metrics_data = self.metrics_data[-self.max_metrics:]
        
        # 检查告警规则
        self._check_alerts(metric)
    
    def add_alert_rule(self, name: str, metric_name: str, threshold: float, operator: str = '>'):
        """添加告警规则"""
        self.alert_rules[name] = {
            'metric_name': metric_name,
            'threshold': threshold,
            'operator': operator
        }
        print(f"Added alert rule: {name} ({metric_name} {operator} {threshold})")
    
    def _check_alerts(self, metric: Dict[str, Any]):
        """检查告警"""
        for alert_name, rule in self.alert_rules.items():
            if metric['name'] == rule['metric_name']:
                value = metric['value']
                threshold = rule['threshold']
                operator = rule['operator']
                
                triggered = False
                if operator == '>' and value > threshold:
                    triggered = True
                elif operator == '<' and value < threshold:
                    triggered = True
                elif operator == '==' and value == threshold:
                    triggered = True
                
                if triggered:
                    print(f"🚨 ALERT: {alert_name} - {metric['name']}={value} {operator} {threshold}")
    
    def get_metric_summary(self, metric_name: str, window_minutes: int = 10) -> Dict[str, Any]:
        """获取指标摘要"""
        current_time = time.time()
        window_start = current_time - (window_minutes * 60)
        
        relevant_metrics = [
            m for m in self.metrics_data 
            if m['name'] == metric_name and m['timestamp'] >= window_start
        ]
        
        if not relevant_metrics:
            return {'count': 0}
        
        values = [m['value'] for m in relevant_metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1] if values else None
        }


def test_data_processing_pipeline():
    """测试数据处理管道"""
    print("=== 数据处理管道测试 ===")
    
    # 创建环境
    env = LocalEnvironment("data_pipeline_env")
    
    # 注册服务
    env.register_service("data_processor", DataProcessorService, batch_size=50, workers=2)
    env.register_service("cache", SmartCacheService, max_size=500, default_ttl=120)
    env.register_service("monitor", MonitoringService, collection_interval=5)
    
    # 创建服务任务
    services = {}
    for service_name in env.service_task_factories:
        task_factory = env.service_task_factories[service_name]
        service_task = task_factory.create_service_task()
        services[service_name] = service_task
    
    try:
        # 启动所有服务
        print("\n启动服务...")
        for service_name, service_task in services.items():
            service_task.start_running()
        
        # 获取服务实例
        processor = services["data_processor"].service
        cache = services["cache"].service
        monitor = services["monitor"].service
        
        # 设置监控告警
        monitor.add_alert_rule("high_error_rate", "error_rate", 0.1, '>')
        monitor.add_alert_rule("low_cache_hit", "cache_hit_rate", 0.5, '<')
        
        # 生成测试数据
        print("\n生成测试数据...")
        test_data = []
        for i in range(200):
            item = {
                'id': i,
                'text': f"  Hello World {i}  ".upper() if i % 3 == 0 else f"test data {i}",
                'email': f"user{i}@test.com" if i % 5 != 0 else "invalid-email",
                'numbers': f"{random.randint(1, 100)} {random.randint(200, 300)} text {random.randint(400, 500)}"
            }
            test_data.append(item)
        
        # 分批处理数据
        print("\n开始数据处理...")
        batch_size = 25
        processed_total = 0
        
        for i in range(0, len(test_data), batch_size):
            batch = test_data[i:i + batch_size]
            
            # 检查缓存
            cache_key = f"batch_{i // batch_size}"
            cached_result = cache.get(cache_key)
            
            if cached_result:
                print(f"使用缓存结果: batch {i // batch_size}")
                processed_batch = cached_result
            else:
                # 处理数据
                processed_batch = processor.process_batch(batch)
                # 存入缓存
                cache.set(cache_key, processed_batch, ttl=60)
                print(f"处理完成: batch {i // batch_size}, 处理了 {len(processed_batch)} 项")
            
            processed_total += len(processed_batch)
            
            # 收集监控指标
            processor_stats = processor.get_statistics()
            cache_stats = cache.get_statistics()
            
            monitor.collect_metric("processed_items", processed_total)
            monitor.collect_metric("error_rate", processor_stats['error_count'] / max(processor_stats['processed_count'], 1))
            monitor.collect_metric("cache_hit_rate", cache_stats['hit_rate'])
            monitor.collect_metric("cache_utilization", cache_stats['utilization'])
            
            # 模拟一些随机延迟
            time.sleep(0.1)
        
        # 显示最终统计
        print(f"\n=== 处理完成 ===")
        print(f"总处理项目: {processed_total}")
        
        print(f"\n数据处理器统计:")
        processor_stats = processor.get_statistics()
        for key, value in processor_stats.items():
            print(f"  {key}: {value}")
        
        print(f"\n缓存统计:")
        cache_stats = cache.get_statistics()
        for key, value in cache_stats.items():
            print(f"  {key}: {value}")
        
        print(f"\n监控摘要:")
        for metric_name in ["processed_items", "error_rate", "cache_hit_rate"]:
            summary = monitor.get_metric_summary(metric_name, window_minutes=5)
            print(f"  {metric_name}: {summary}")
    
    finally:
        # 清理服务
        print(f"\n清理服务...")
        for service_name, service_task in services.items():
            service_task.terminate()


def test_collaborative_services():
    """测试服务协作场景"""
    print("\n=== 服务协作测试 ===")
    
    # 创建环境
    env = LocalEnvironment("collaborative_env")
    
    # 注册服务
    env.register_service("cache", SmartCacheService, max_size=100, default_ttl=30)
    env.register_service("monitor", MonitoringService, collection_interval=1)
    
    # 创建服务
    services = {}
    for service_name in env.service_task_factories:
        task_factory = env.service_task_factories[service_name]
        service_task = task_factory.create_service_task()
        services[service_name] = service_task
    
    try:
        # 启动服务
        for service_task in services.values():
            service_task.start_running()
        
        cache = services["cache"].service
        monitor = services["monitor"].service
        
        # 模拟应用工作负载
        print("模拟应用工作负载...")
        
        # 设置缓存数据
        for i in range(50):
            key = f"key_{i}"
            value = {"data": f"value_{i}", "created": time.time()}
            cache.set(key, value, ttl=random.randint(10, 60))
        
        # 模拟访问模式
        for round_num in range(5):
            print(f"\n访问轮次 {round_num + 1}")
            
            hit_count = 0
            miss_count = 0
            
            # 随机访问缓存
            for _ in range(30):
                key = f"key_{random.randint(0, 70)}"  # 有些key不存在
                result = cache.get(key)
                
                if result:
                    hit_count += 1
                else:
                    miss_count += 1
                    # 模拟从数据库加载并缓存
                    if random.random() < 0.7:  # 70%概率能从"数据库"找到
                        new_value = {"data": f"loaded_{key}", "loaded_at": time.time()}
                        cache.set(key, new_value)
            
            # 收集指标
            cache_stats = cache.get_statistics()
            monitor.collect_metric("round_hits", hit_count, {"round": str(round_num)})
            monitor.collect_metric("round_misses", miss_count, {"round": str(round_num)})
            monitor.collect_metric("cache_size", cache_stats['size'])
            monitor.collect_metric("overall_hit_rate", cache_stats['hit_rate'])
            
            print(f"  本轮命中: {hit_count}, 未命中: {miss_count}")
            print(f"  缓存大小: {cache_stats['size']}, 整体命中率: {cache_stats['hit_rate']:.2%}")
            
            time.sleep(1)
        
        # 显示监控摘要
        print(f"\n=== 监控摘要 ===")
        for metric in ["round_hits", "round_misses", "overall_hit_rate"]:
            summary = monitor.get_metric_summary(metric, window_minutes=1)
            print(f"{metric}: {summary}")
    
    finally:
        # 清理
        for service_task in services.values():
            service_task.terminate()


if __name__ == "__main__":
    # 运行测试
    test_data_processing_pipeline()
    test_collaborative_services()
    print("\n🎉 所有高级服务测试完成！")

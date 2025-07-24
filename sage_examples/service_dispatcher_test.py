"""
服务系统与Dispatcher集成测试

这个文件展示了如何使用Dispatcher来管理服务的完整生命周期。
"""

import time
from sage_core.api.local_environment import LocalEnvironment


class LoggingService:
    """
    日志服务示例
    """
    
    def __init__(self, log_level: str = "INFO"):
        self.log_level = log_level
        self.is_running = False
        self.logs = []
        self.ctx = None
    
    def start_running(self):
        """启动服务"""
        self.is_running = True
        self.log("Service started")
    
    def terminate(self):
        """终止服务"""
        self.log("Service terminating")
        self.is_running = False
    
    def log(self, message: str):
        """记录日志"""
        if self.is_running:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {self.log_level}: {message}"
            self.logs.append(log_entry)
            print(log_entry)
    
    def get_logs(self):
        """获取所有日志"""
        return self.logs.copy()


class MetricsService:
    """
    指标服务示例
    """
    
    def __init__(self, collection_interval: int = 60):
        self.collection_interval = collection_interval
        self.is_running = False
        self.metrics = {}
        self.ctx = None
    
    def start_running(self):
        """启动服务"""
        self.is_running = True
        print(f"Metrics service started with {self.collection_interval}s interval")
    
    def terminate(self):
        """终止服务"""
        print("Metrics service terminating")
        self.is_running = False
    
    def record_metric(self, name: str, value: float):
        """记录指标"""
        if self.is_running:
            self.metrics[name] = value
            print(f"Recorded metric {name}: {value}")
    
    def get_metrics(self):
        """获取所有指标"""
        return self.metrics.copy()


def test_service_system_integration():
    """
    测试服务系统的完整集成（不使用Dispatcher）
    """
    print("=== 服务系统完整集成测试 ===")
    
    try:
        # 1. 创建环境并注册服务
        print("\n1. 创建环境并注册服务:")
        env = LocalEnvironment("integration_test_env")
        
        # 注册日志服务
        env.register_service(
            "logging", 
            LoggingService,
            log_level="DEBUG"
        )
        
        # 注册指标服务
        env.register_service(
            "metrics", 
            MetricsService,
            collection_interval=30
        )
        
        print(f"已注册服务: {list(env.service_factories.keys())}")
        
        # 2. 创建服务任务
        print("\n2. 创建服务任务:")
        
        services = {}
        for service_name in env.service_task_factories:
            task_factory = env.service_task_factories[service_name]
            service_task = task_factory.create_service_task()
            services[service_name] = service_task
            print(f"创建服务任务: {service_name}")
        
        # 3. 启动服务
        print("\n3. 启动服务:")
        for service_name, service_task in services.items():
            service_task.start_running()
            print(f"启动服务: {service_name}")
        
        # 4. 测试服务功能
        print("\n4. 测试服务功能:")
        
        # 获取服务实例
        logging_service = services["logging"].service
        metrics_service = services["metrics"].service
        
        # 测试日志服务
        logging_service.log("Test log message 1")
        logging_service.log("Test log message 2")
        print(f"日志条数: {len(logging_service.get_logs())}")
        
        # 测试指标服务
        metrics_service.record_metric("cpu_usage", 75.5)
        metrics_service.record_metric("memory_usage", 60.2)
        print(f"指标数量: {len(metrics_service.get_metrics())}")
        
        # 5. 检查服务状态
        print("\n5. 检查服务状态:")
        for service_name, service_task in services.items():
            print(f"服务 {service_name}: running={service_task.is_running}")
        
        # 6. 关闭服务
        print("\n6. 关闭服务:")
        for service_name, service_task in services.items():
            service_task.terminate()
            print(f"关闭服务: {service_name}")
        
        print("\n=== 集成测试完成 ===")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行集成测试
    test_service_system_integration()

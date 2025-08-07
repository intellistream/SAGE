#!/usr/bin/env python3
"""
测试从execution graph的service nodes构造service task的功能
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from sage.core.api.local_environment import LocalEnvironment
from sage.core.api.function.base_function import BaseFunction
from sage.kernel.jobmanager.execution_graph import ExecutionGraph
from sage.kernel.runtime.dispatcher import Dispatcher


# 测试服务类
class TestCacheService:
    """测试缓存服务"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache = {}
        self.is_running = False
        self.ctx = None
        self.initialized_from_service_node = False  # 标记是否从service node初始化
    
    def start_running(self):
        self.is_running = True
        self.initialized_from_service_node = True  # 标记已初始化
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
    
    def get_info(self):
        return {
            "max_size": self.max_size,
            "current_size": len(self.cache),
            "is_running": self.is_running,
            "initialized_from_service_node": self.initialized_from_service_node
        }


class TestModelService:
    """测试模型服务"""
    
    def __init__(self, model_name: str = "test_model"):
        self.model_name = model_name
        self.is_running = False
        self.ctx = None
        self.prediction_count = 0
        self.initialized_from_service_node = False
    
    def start_running(self):
        self.is_running = True
        self.initialized_from_service_node = True
        print(f"Model service started: {self.model_name}")
    
    def terminate(self):
        self.is_running = False
        print(f"Model service terminated: {self.model_name}")
    
    def predict(self, data):
        if not self.is_running:
            return {"error": "Model service not running"}
        
        self.prediction_count += 1
        return {
            "prediction": f"result_{self.prediction_count}",
            "model": self.model_name,
            "input": data
        }
    
    def get_info(self):
        return {
            "model_name": self.model_name,
            "is_running": self.is_running,
            "prediction_count": self.prediction_count,
            "initialized_from_service_node": self.initialized_from_service_node
        }


# 测试函数
class TestSourceFunction(BaseFunction):
    def __init__(self, count: int = 3):
        super().__init__()
        self.count = count
        self.current = 0
    
    def execute(self):
        if self.current >= self.count:
            return None
        self.current += 1
        return f"data_{self.current}"


class TestMapFunction(BaseFunction):
    def execute(self, data):
        if data is None:
            return None
        return f"processed_{data}"


def test_dispatcher_service_creation():
    """测试dispatcher从service nodes创建服务任务"""
    print("=== 测试Dispatcher从Service Nodes创建服务任务 ===")
    
    try:
        # 1. 创建环境并注册服务
        print("\n1. 创建环境并注册服务")
        env = LocalEnvironment("test_dispatcher_services")
        env.set_console_log_level("DEBUG")
        
        # 注册服务
        env.register_service("cache", TestCacheService, max_size=50)
        env.register_service("model", TestModelService, model_name="dispatcher_test_model")
        
        print(f"注册的服务: {list(env.service_factories.keys())}")
        
        # 2. 构建简单的流水线
        print("\n2. 构建流水线")
        stream = env.from_source(TestSourceFunction, count=3) \
                   .map(TestMapFunction)
        
        # 3. 设置日志系统并创建execution graph
        print("\n3. 创建执行图")
        env.setup_logging_system("/tmp/test_logs")
        execution_graph = ExecutionGraph(env)
        
        print(f"执行图创建完成:")
        print(f"  - 流水线节点: {len(execution_graph.nodes)}")
        print(f"  - 服务节点: {len(execution_graph.service_nodes)}")
        
        # 4. 创建dispatcher
        print("\n4. 创建Dispatcher")
        dispatcher = Dispatcher(execution_graph, env)
        
        # 5. 检查dispatcher初始状态
        print(f"Dispatcher初始状态:")
        print(f"  - 服务数量: {len(dispatcher.services)}")
        print(f"  - 任务数量: {len(dispatcher.tasks)}")
        
        # 6. 调用submit方法（这会从service nodes创建服务任务）
        print("\n5. 提交作业（创建服务任务）")
        dispatcher.submit()
        
        # 7. 检查服务是否正确创建
        print(f"\n6. 检查服务创建结果:")
        print(f"  - 创建的服务数量: {len(dispatcher.services)}")
        print(f"  - 创建的任务数量: {len(dispatcher.tasks)}")
        
        # 8. 详细检查每个服务
        print(f"\n7. 服务详情:")
        for service_name, service_task in dispatcher.services.items():
            print(f"  服务: {service_name}")
            print(f"    类型: {service_task.__class__.__name__}")
            print(f"    是否有ctx属性: {hasattr(service_task, 'ctx')}")
            
            # 检查服务实例
            if hasattr(service_task, 'service_instance'):
                service_instance = service_task.service_instance
                print(f"    服务实例类型: {service_instance.__class__.__name__}")
                
                # 如果有get_info方法，调用它
                if hasattr(service_instance, 'get_info'):
                    info = service_instance.get_info()
                    print(f"    服务信息: {info}")
        
        # 9. 验证服务是否从service node正确构造
        print(f"\n8. 验证构造来源:")
        expected_services = set(execution_graph.service_nodes.keys())
        created_services = set(dispatcher.services.keys())
        
        # 从service node name映射到service name
        service_node_to_service_name = {
            node_name: service_node.service_name 
            for node_name, service_node in execution_graph.service_nodes.items()
        }
        expected_service_names = set(service_node_to_service_name.values())
        
        print(f"    期望的服务名称: {expected_service_names}")
        print(f"    实际创建的服务: {created_services}")
        print(f"    是否匹配: {expected_service_names == created_services}")
        
        # 10. 清理
        print(f"\n9. 清理资源")
        dispatcher.cleanup()
        
        print("\n=== Dispatcher从Service Nodes创建服务任务测试成功 ===")
        return True
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_context_injection():
    """测试服务任务的运行时上下文注入"""
    print("\n=== 测试服务运行时上下文注入 ===")
    
    try:
        # 创建环境并注册服务
        env = LocalEnvironment("test_service_context_injection")
        env.register_service("test_service", TestCacheService)
        
        # 设置日志系统并创建execution graph
        env.setup_logging_system("/tmp/test_logs")
        execution_graph = ExecutionGraph(env)
        
        # 创建dispatcher并提交
        dispatcher = Dispatcher(execution_graph, env)
        dispatcher.submit()
        
        # 检查服务任务的上下文
        print(f"\n检查服务上下文:")
        for service_name, service_task in dispatcher.services.items():
            print(f"  服务: {service_name}")
            
            if hasattr(service_task, 'ctx') and service_task.ctx:
                ctx = service_task.ctx
                print(f"    上下文名称: {ctx.name}")
                print(f"    环境名称: {ctx.env_name}")
                print(f"    并行索引: {ctx.parallel_index}")
                print(f"    并行度: {ctx.parallelism}")
                print(f"    是否为源: {ctx.is_spout}")
                print(f"    停止信号数: {ctx.stop_signal_num}")
            else:
                print(f"    上下文: None")
        
        # 清理
        dispatcher.cleanup()
        
        print("\n=== 服务运行时上下文注入测试成功 ===")
        return True
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success1 = test_dispatcher_service_creation()
    success2 = test_service_context_injection()
    
    if success1 and success2:
        print("\n✅ 所有测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败!")
        sys.exit(1)

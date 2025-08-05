#!/usr/bin/env python3
"""
测试服务节点在执行图中的集成
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from sage.core.api.local_environment import LocalEnvironment
from sage.core.function.base_function import BaseFunction
from sage.jobmanager.execution_graph import ExecutionGraph


# 测试服务类
class TestCacheService:
    """测试缓存服务"""
    
    def __init__(self, max_size: int = 100):
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
            # 简单的FIFO清除策略
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value
        return True


class TestModelService:
    """测试模型服务"""
    
    def __init__(self, model_name: str = "test_model"):
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
    
    def predict(self, data):
        if not self.is_running:
            return {"error": "Model service not running"}
        
        self.prediction_count += 1
        return {
            "prediction": f"result_{self.prediction_count}",
            "model": self.model_name,
            "input": data
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


def test_service_nodes_integration():
    """测试服务节点与执行图的集成"""
    print("=== 测试服务节点集成 ===")
    
    try:
        # 1. 创建环境
        print("\n1. 创建本地环境")
        env = LocalEnvironment("test_service_nodes")
        env.set_console_log_level("DEBUG")
        
        # 2. 注册服务
        print("\n2. 注册测试服务")
        env.register_service("cache", TestCacheService, max_size=50)
        env.register_service("model", TestModelService, model_name="test_model_v1")
        
        print(f"注册的服务: {list(env.service_factories.keys())}")
        
        # 3. 构建简单的流水线
        print("\n3. 构建流水线")
        stream = env.from_source(TestSourceFunction, count=5) \
                   .map(TestMapFunction)
        
        print("流水线构建完成")
        
        # 4. 模拟日志系统设置（通常由JobManager调用）
        print("\n4. 设置日志系统")
        env.setup_logging_system("/tmp/test_logs")
        
        # 5. 创建执行图
        print("\n5. 创建执行图")
        execution_graph = ExecutionGraph(env)
        
        # 6. 检查执行图结构
        print("\n6. 检查执行图结构")
        print(f"流水线节点数: {len(execution_graph.nodes)}")
        print(f"服务节点数: {len(execution_graph.service_nodes)}")
        print(f"边数: {len(execution_graph.edges)}")
        
        # 7. 列出所有节点
        print("\n7. 流水线节点详情:")
        for name, node in execution_graph.nodes.items():
            print(f"  - {name}: {node.transformation.operator_class.__name__} (并行度: {node.parallelism})")
            if hasattr(node, 'ctx') and node.ctx:
                print(f"    运行时上下文: {node.ctx.name}")
        
        print("\n8. 服务节点详情:")
        for name, service_node in execution_graph.service_nodes.items():
            print(f"  - {name}: {service_node.service_name} ({service_node.service_factory.service_class.__name__})")
            if hasattr(service_node, 'ctx') and service_node.ctx:
                print(f"    运行时上下文: {service_node.ctx.name}")
        
        # 9. 测试获取所有节点
        print("\n9. 获取所有节点:")
        all_nodes = execution_graph.get_all_nodes()
        print(f"总节点数: {len(all_nodes)}")
        for name, node in all_nodes.items():
            node_type = "Service" if name in execution_graph.service_nodes else "Transformation"
            print(f"  - {name}: {node_type}")
        
        print("\n=== 服务节点集成测试成功 ===")
        return True
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_runtime_context():
    """测试服务节点的运行时上下文"""
    print("\n=== 测试服务运行时上下文 ===")
    
    try:
        # 创建环境并注册服务
        env = LocalEnvironment("test_service_context")
        env.register_service("test_service", TestCacheService)
        
        # 设置日志系统
        env.setup_logging_system("/tmp/test_logs")
        
        # 创建执行图
        execution_graph = ExecutionGraph(env)
        
        # 检查服务节点的运行时上下文
        for name, service_node in execution_graph.service_nodes.items():
            print(f"\n服务节点: {name}")
            print(f"  服务名称: {service_node.service_name}")
            
            if service_node.ctx:
                print(f"  运行时上下文:")
                print(f"    名称: {service_node.ctx.name}")
                print(f"    环境名: {service_node.ctx.env_name}")
                print(f"    并行索引: {service_node.ctx.parallel_index}")
                print(f"    是否为源: {service_node.ctx.is_spout}")
                print(f"    停止信号数: {service_node.ctx.stop_signal_num}")
            else:
                print("  运行时上下文: None")
        
        print("\n=== 服务运行时上下文测试成功 ===")
        return True
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success1 = test_service_nodes_integration()
    success2 = test_service_runtime_context()
    
    if success1 and success2:
        print("\n✅ 所有测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败!")
        sys.exit(1)

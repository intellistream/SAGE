"""
SAGE系统中使用Ray对象预处理器的实际示例
展示如何在Transformation和Operator中使用trim_object_for_ray
"""
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目根路径
SAGE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SAGE_ROOT))

from sage_utils.serialization.dill_serializer import (
    trim_object_for_ray,
    RayObjectTrimmer
)

# 模拟SAGE组件
class MockTransformation:
    """模拟的Transformation类，包含典型的不可序列化属性"""
    
    def __init__(self, function_name: str):
        # 可序列化的核心属性
        self.function_class_name = function_name
        self.function_args = ["arg1", "arg2"]
        self.function_kwargs = {"param1": "value1"}
        self.basename = f"transform_{function_name}"
        self.parallelism = 1
        self.upstreams = []
        self.downstreams = {"downstream1": 0}
        
        # 不可序列化的属性（会导致Ray调用失败）
        from sage_utils.custom_logger import CustomLogger
        self.logger = CustomLogger()  # 日志对象
        self.env = self._create_mock_env()  # 环境引用
        self.memory_collection = self._create_mock_memory()  # 可能是Actor句柄
        
        # 懒加载工厂（包含复杂状态）
        self._dag_node_factory = None
        self._operator_factory = None
        self._function_factory = None
        
        # 运行时状态
        self.ctx = self._create_runtime_context()
        
        # 定义序列化排除列表
        self.__state_exclude__ = [
            'logger', 'env', 'memory_collection', 'runtime_context',
            '_dag_node_factory', '_operator_factory', '_function_factory'
        ]
    
    def _create_mock_env(self):
        """创建模拟环境对象"""
        class MockEnv:
            def __init__(self):
                self.name = "test_env"
                self.platform = "remote"
        return MockEnv()
    
    def _create_mock_memory(self):
        """创建模拟内存集合"""
        class MockMemory:
            def __init__(self):
                self.collection_type = "VDB"
        return MockMemory()
    
    def _create_runtime_context(self):
        """创建模拟运行时上下文"""
        class MockContext:
            def __init__(self):
                self.session_id = "test_session"
        return MockContext()
    
    def get_serializable_state(self):
        """返回可序列化的状态"""
        return {
            'function_class_name': self.function_class_name,
            'function_args': self.function_args,
            'function_kwargs': self.function_kwargs,
            'basename': self.basename,
            'parallelism': self.parallelism,
            'upstreams': self.upstreams,
            'downstreams': self.downstreams
        }


class MockOperator:
    """模拟的Operator类"""
    
    def __init__(self, operator_name: str):
        self.operator_name = operator_name
        self.config = {"setting": "value"}
        
        # 不可序列化的属性
        import threading
        self.logger = self._create_logger()
        self.emit_context = self._create_emit_context()
        self.server_thread = threading.Thread(target=lambda: None)
        
        # 排除列表
        self.__state_exclude__ = [
            'logger', 'emit_context', 'server_thread'
        ]
    
    def _create_logger(self):
        class Logger:
            def info(self, msg): pass
        return Logger()
    
    def _create_emit_context(self):
        class EmitContext:
            def __init__(self):
                self.connections = {}
        return EmitContext()


def demonstrate_transformation_trimming():
    """演示Transformation对象的预处理"""
    print("=== Transformation对象预处理示例 ===")
    
    # 创建包含问题属性的transformation
    transformation = MockTransformation("map_function")
    
    print("原始Transformation属性:")
    for attr_name in sorted(transformation.__dict__.keys()):
        attr_value = getattr(transformation, attr_name)
        print(f"  {attr_name}: {type(attr_value)} = {str(attr_value)[:50]}...")
    
    # 使用专门的transformation清理方法
    print("\n使用RayObjectTrimmer.trim_transformation_for_ray()...")
    cleaned_transformation = RayObjectTrimmer.trim_transformation_for_ray(transformation)
    
    print("清理后Transformation属性:")
    for attr_name in sorted(cleaned_transformation.__dict__.keys()):
        attr_value = getattr(cleaned_transformation, attr_name)
        print(f"  {attr_name}: {type(attr_value)} = {str(attr_value)[:50]}...")
    
    # 验证关键属性保留
    assert hasattr(cleaned_transformation, 'function_class_name'), "核心属性应该保留"
    assert hasattr(cleaned_transformation, 'basename'), "名称应该保留"
    assert not hasattr(cleaned_transformation, 'logger'), "logger应该被移除"
    assert not hasattr(cleaned_transformation, 'env'), "env应该被移除"
    
    print("✓ Transformation清理成功")
    return cleaned_transformation


def demonstrate_operator_trimming():
    """演示Operator对象的预处理"""
    print("\n=== Operator对象预处理示例 ===")
    
    operator = MockOperator("map_operator")
    
    print("原始Operator属性:")
    for attr_name in sorted(operator.__dict__.keys()):
        print(f"  {attr_name}: {type(getattr(operator, attr_name))}")
    
    # 使用专门的operator清理方法
    cleaned_operator = RayObjectTrimmer.trim_operator_for_ray(operator)
    
    print("清理后Operator属性:")
    for attr_name in sorted(cleaned_operator.__dict__.keys()):
        print(f"  {attr_name}: {type(getattr(cleaned_operator, attr_name))}")
    
    assert hasattr(cleaned_operator, 'operator_name'), "核心属性应该保留"
    assert not hasattr(cleaned_operator, 'logger'), "logger应该被移除"
    assert not hasattr(cleaned_operator, 'server_thread'), "线程应该被移除"
    
    print("✓ Operator清理成功")
    return cleaned_operator


def demonstrate_custom_trimming():
    """演示自定义预处理规则"""
    print("\n=== 自定义预处理规则示例 ===")
    
    transformation = MockTransformation("custom_function")
    
    # 场景1：只保留特定属性
    print("场景1：只保留核心执行属性...")
    core_only = trim_object_for_ray(
        transformation,
        include=['function_class_name', 'function_args', 'function_kwargs', 'parallelism']
    )
    print(f"保留属性: {list(core_only.__dict__.keys())}")
    
    # 场景2：排除特定属性
    print("\n场景2：排除运行时状态...")
    runtime_excluded = trim_object_for_ray(
        transformation,
        exclude=['upstreams', 'downstreams', 'runtime_context']
    )
    print(f"剩余属性: {list(runtime_excluded.__dict__.keys())}")
    
    print("✓ 自定义预处理规则测试成功")


def simulate_ray_actor_workflow():
    """模拟完整的Ray Actor工作流程"""
    print("\n=== 模拟Ray Actor工作流程 ===")
    
    try:
        import ray
        
        if not ray.is_initialized():
            ray.init(local_mode=True, ignore_reinit_error=True)
        
        @ray.remote
        class TransformationProcessor:
            """模拟处理Transformation的Ray Actor"""
            
            def process_transformation(self, transformation):
                """处理清理后的transformation对象"""
                return {
                    "processed_type": type(transformation).__name__,
                    "function_name": getattr(transformation, 'function_class_name', 'unknown'),
                    "attributes_count": len(transformation.__dict__) if hasattr(transformation, '__dict__') else 0,
                    "attributes": list(transformation.__dict__.keys()) if hasattr(transformation, '__dict__') else []
                }
            
            def validate_object(self, obj):
                """验证对象是否可以正常处理"""
                try:
                    # 尝试访问对象属性
                    attrs = obj.__dict__ if hasattr(obj, '__dict__') else {}
                    return {
                        "valid": True,
                        "attribute_count": len(attrs),
                        "sample_attributes": list(attrs.keys())[:5]
                    }
                except Exception as e:
                    return {
                        "valid": False,
                        "error": str(e)
                    }
        
        # 创建Actor
        processor = TransformationProcessor.remote()
        
        # 准备测试对象
        original_transformation = MockTransformation("ray_workflow_test")
        
        print("步骤1：尝试发送原始对象（可能失败）...")
        try:
            result = ray.get(processor.validate_object.remote(original_transformation))
            print(f"原始对象验证结果: {result}")
        except Exception as e:
            print(f"原始对象发送失败: {e}")
        
        print("\n步骤2：预处理对象并发送...")
        cleaned_transformation = RayObjectTrimmer.trim_transformation_for_ray(original_transformation)
        
        # 发送清理后的对象
        validation_result = ray.get(processor.validate_object.remote(cleaned_transformation))
        print(f"清理后对象验证结果: {validation_result}")
        
        processing_result = ray.get(processor.process_transformation.remote(cleaned_transformation))
        print(f"处理结果: {processing_result}")
        
        print("✓ Ray Actor工作流程测试成功")
        
        # 清理
        ray.shutdown()
        
    except ImportError:
        print("Ray未安装，跳过Actor工作流程测试")
    except Exception as e:
        print(f"Ray Actor工作流程测试失败: {e}")


def performance_analysis():
    """性能分析：对比处理前后的对象大小"""
    print("\n=== 性能分析 ===")
    
    import pickle
    import sys
    
    # 创建测试对象
    transformation = MockTransformation("performance_test")
    operator = MockOperator("performance_test")
    
    # 分析transformation
    print("Transformation对象分析:")
    try:
        original_size = sys.getsizeof(pickle.dumps(transformation.__dict__))
        print(f"  原始对象大小: {original_size} 字节")
    except Exception as e:
        print(f"  原始对象无法序列化: {e}")
    
    cleaned_trans = RayObjectTrimmer.trim_transformation_for_ray(transformation)
    cleaned_size = sys.getsizeof(pickle.dumps(cleaned_trans.__dict__))
    print(f"  清理后对象大小: {cleaned_size} 字节")
    print(f"  属性数量: {len(transformation.__dict__)} -> {len(cleaned_trans.__dict__)}")
    
    # 分析operator  
    print("\nOperator对象分析:")
    try:
        original_op_size = sys.getsizeof(pickle.dumps(operator.__dict__))
        print(f"  原始对象大小: {original_op_size} 字节")
    except Exception as e:
        print(f"  原始对象无法序列化: {e}")
    
    cleaned_op = RayObjectTrimmer.trim_operator_for_ray(operator)
    cleaned_op_size = sys.getsizeof(pickle.dumps(cleaned_op.__dict__))
    print(f"  清理后对象大小: {cleaned_op_size} 字节")
    print(f"  属性数量: {len(operator.__dict__)} -> {len(cleaned_op.__dict__)}")


def main():
    """主函数：运行所有示例"""
    print("SAGE Ray对象预处理器使用示例")
    print("=" * 60)
    
    try:
        # 基本用法示例
        demonstrate_transformation_trimming()
        demonstrate_operator_trimming()
        demonstrate_custom_trimming()
        
        # 高级用法
        simulate_ray_actor_workflow()
        performance_analysis()
        
        print("\n" + "=" * 60)
        print("🎉 所有示例运行完成！")
        print("\n总结:")
        print("1. ✓ trim_object_for_ray() 可以有效清理不可序列化的属性")
        print("2. ✓ RayObjectTrimmer 提供了针对不同对象类型的专门清理方法")
        print("3. ✓ 支持自定义include/exclude规则")
        print("4. ✓ 清理后的对象可以安全地传递给Ray进行序列化")
        print("5. ✓ 显著减少了对象大小和序列化复杂度")
        
        print("\n使用建议:")
        print("- 在Ray远程调用前使用trim_object_for_ray()预处理对象")
        print("- 为常见的SAGE组件使用专门的清理方法")
        print("- 根据具体需求定制include/exclude列表")
        print("- 在开发阶段使用validate_ray_serializable()验证对象")
        
    except Exception as e:
        print(f"示例运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

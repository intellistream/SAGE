"""
测试反馈边功能的简单例子
"""

from sage_core.api.env import LocalEnvironment
from sage_core.function.base_function import BaseFunction
from sage_core.function.comap_function import BaseCoMapFunction


class ExampleSource(BaseFunction):
    def call(self, data):
        return f"source: {data}"


class ProcessFunction(BaseFunction):
    def call(self, data):
        return f"processed: {data}"


class CombineFunction(BaseCoMapFunction):
    def map0(self, data):
        """处理第一个输入流的数据"""
        return f"stream0: {data}"
    
    def map1(self, data):
        """处理第二个输入流的数据（来自future stream）"""
        return f"stream1_feedback: {data}"


class FilterFunction(BaseFunction):
    def call(self, data):
        return "important" in str(data)


def test_feedback_edge():
    """测试反馈边功能"""
    
    # 1. 创建环境
    env = LocalEnvironment("test_feedback")
    
    # 2. 声明future stream
    future_stream = env.from_future("feedback_loop")
    print(f"Created future stream: {future_stream.transformation}")
    print(f"Pipeline before fill: {len(env._pipeline)} transformations")
    print(f"Has unfilled futures: {env.has_unfilled_futures()}")
    
    # 3. 构建pipeline，使用future stream
    source_stream = env.from_source(ExampleSource)
    combined_stream = source_stream.connect(future_stream).comap(CombineFunction)
    
    # 4. 进一步处理
    processed_stream = combined_stream.map(ProcessFunction)
    filtered_stream = processed_stream.filter(FilterFunction)
    
    print(f"Pipeline after construction: {len(env._pipeline)} transformations")
    
    # 5. 测试编译前的验证
    try:
        env.validate_pipeline_for_compilation()
        print("✗ Should not pass validation with unfilled futures")
    except RuntimeError as e:
        print(f"✓ Correctly failed validation: {e}")
    
    # 6. 填充future stream，创建反馈边
    try:
        filtered_stream.fill_future(future_stream)
        print("✓ Successfully created feedback edge")
        print(f"Future stream status: {future_stream.transformation}")
        print(f"Pipeline after fill: {len(env._pipeline)} transformations")
        print(f"Filled futures: {list(env.get_filled_futures().keys())}")
        print(f"Has unfilled futures: {env.has_unfilled_futures()}")
        
        # 7. 测试编译前的验证（现在应该通过）
        try:
            env.validate_pipeline_for_compilation()
            print("✓ Pipeline validation passed after filling")
        except RuntimeError as e:
            print(f"✗ Validation should pass after filling: {e}")
        
        # 8. 验证不能重复填充
        try:
            filtered_stream.fill_future(future_stream)
            print("✗ Should not allow double filling")
        except RuntimeError as e:
            print(f"✓ Correctly prevented double filling: {e}")
            
    except Exception as e:
        print(f"✗ Failed to create feedback edge: {e}")


def test_compiler_safety():
    """测试compiler的安全检查"""
    print("\n--- Testing Compiler Safety ---")
    
    # 创建一个有未填充future的环境
    env = LocalEnvironment("test_compiler_safety")
    future_stream = env.from_future("unfilled_future")
    source_stream = env.from_source(ExampleSource)
    
    # 尝试编译，应该失败
    try:
        from sage_runtime.compiler import Compiler
        compiler = Compiler(env)
        print("✗ Compiler should reject unfilled futures")
    except RuntimeError as e:
        print(f"✓ Compiler correctly rejected unfilled future: {e}")
    except Exception as e:
        print(f"? Unexpected error: {e}")


if __name__ == "__main__":
    test_feedback_edge()
    test_compiler_safety()

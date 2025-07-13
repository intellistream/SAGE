"""
测试反馈边功能的简单例子
"""

from sage_core.api.env import LocalEnvironment
from sage_core.function.base_function import BaseFunction


class ExampleSource(BaseFunction):
    def call(self, data):
        return f"source: {data}"


class ProcessFunction(BaseFunction):
    def call(self, data):
        return f"processed: {data}"


class CombineFunction(BaseFunction):
    def call(self, data1, data2):
        return f"combined: {data1} + {data2}"


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
    
    # 3. 构建pipeline，使用future stream
    source_stream = env.from_source(ExampleSource)
    combined_stream = source_stream.connect(future_stream).comap(CombineFunction)
    
    # 4. 进一步处理
    processed_stream = combined_stream.map(ProcessFunction)
    filtered_stream = processed_stream.filter(FilterFunction)
    
    # 5. 填充future stream，创建反馈边
    try:
        filtered_stream.fill_future(future_stream)
        print("✓ Successfully created feedback edge")
        print(f"Future stream status: {future_stream.transformation}")
        print(f"Filled futures: {env._filled_futures}")
        
        # 验证不能重复填充
        try:
            filtered_stream.fill_future(future_stream)
            print("✗ Should not allow double filling")
        except RuntimeError as e:
            print(f"✓ Correctly prevented double filling: {e}")
            
    except Exception as e:
        print(f"✗ Failed to create feedback edge: {e}")


if __name__ == "__main__":
    test_feedback_edge()

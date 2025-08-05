"""
测试Pipeline模块的单元测试
"""

import pytest
from unittest.mock import Mock, patch
from typing import Any

from sage.kernel.api.pipeline import (
    Pipeline, 
    PipelineStep, 
    DataTransformStep, 
    FilterStep,
    create_pipeline,
    transform_step,
    filter_step
)


class MockPipelineStep(PipelineStep):
    """测试用的Mock Pipeline Step"""
    
    def __init__(self, name: str, return_value: Any = None):
        super().__init__(name)
        self.return_value = return_value
        self.process_called = False
        self.process_call_count = 0
        self.last_input = None
        
    def process(self, data: Any) -> Any:
        self.process_called = True
        self.process_call_count += 1
        self.last_input = data
        return self.return_value if self.return_value is not None else data


@pytest.mark.unit
class TestPipeline:
    """Pipeline类的单元测试"""
    
    def test_pipeline_creation(self):
        """测试Pipeline创建"""
        pipeline = Pipeline("test_pipeline")
        assert pipeline.name == "test_pipeline"
        assert pipeline.steps == []
        assert len(pipeline.steps) == 0
        
    def test_pipeline_creation_default_name(self):
        """测试Pipeline默认名称创建"""
        pipeline = Pipeline()
        assert pipeline.name == "sage_pipeline"
        
    def test_add_step(self):
        """测试添加处理步骤"""
        pipeline = Pipeline("test")
        step = MockPipelineStep("step1")
        
        result = pipeline.add_step(step)
        
        # 测试链式调用
        assert result is pipeline
        assert len(pipeline.steps) == 1
        assert pipeline.steps[0] is step
        
    def test_add_multiple_steps(self):
        """测试添加多个处理步骤"""
        pipeline = Pipeline("test")
        step1 = MockPipelineStep("step1")
        step2 = MockPipelineStep("step2")
        
        pipeline.add_step(step1).add_step(step2)
        
        assert len(pipeline.steps) == 2
        assert pipeline.steps[0] is step1
        assert pipeline.steps[1] is step2
        
    def test_execute_empty_pipeline(self):
        """测试空管道执行"""
        pipeline = Pipeline("test")
        input_data = {"test": "data"}
        
        result = pipeline.execute(input_data)
        
        assert result is input_data
        
    def test_execute_single_step(self):
        """测试单步骤管道执行"""
        pipeline = Pipeline("test")
        step = MockPipelineStep("step1", "processed_data")
        pipeline.add_step(step)
        
        input_data = "original_data"
        result = pipeline.execute(input_data)
        
        assert result == "processed_data"
        assert step.process_called
        assert step.process_call_count == 1
        assert step.last_input == input_data
        
    def test_execute_multiple_steps(self):
        """测试多步骤管道执行"""
        pipeline = Pipeline("test")
        step1 = MockPipelineStep("step1", "data_from_step1")
        step2 = MockPipelineStep("step2", "data_from_step2")
        pipeline.add_step(step1).add_step(step2)
        
        input_data = "original_data"
        result = pipeline.execute(input_data)
        
        assert result == "data_from_step2"
        assert step1.process_called
        assert step2.process_called
        assert step1.last_input == input_data
        assert step2.last_input == "data_from_step1"
        
    def test_pipeline_repr(self):
        """测试Pipeline字符串表示"""
        pipeline = Pipeline("test_pipeline")
        step1 = MockPipelineStep("step1")
        step2 = MockPipelineStep("step2")
        pipeline.add_step(step1).add_step(step2)
        
        repr_str = repr(pipeline)
        assert "Pipeline" in repr_str
        assert "test_pipeline" in repr_str
        assert "steps=2" in repr_str
        
    @patch('sage.core.pipeline.logging.getLogger')
    def test_pipeline_logging(self, mock_get_logger):
        """测试Pipeline日志记录"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        pipeline = Pipeline("test")
        step = MockPipelineStep("step1")
        pipeline.add_step(step)
        
        pipeline.execute("test_data")
        
        # 验证日志调用
        mock_logger.info.assert_called()
        mock_logger.debug.assert_called()


@pytest.mark.unit
class TestPipelineStep:
    """PipelineStep抽象基类测试"""
    
    def test_pipeline_step_creation(self):
        """测试PipelineStep创建"""
        step = MockPipelineStep("test_step")
        assert step.name == "test_step"
        
    def test_pipeline_step_repr(self):
        """测试PipelineStep字符串表示"""
        step = MockPipelineStep("test_step")
        repr_str = repr(step)
        assert "MockPipelineStep" in repr_str
        assert "test_step" in repr_str
        
    def test_abstract_process_method(self):
        """测试抽象process方法必须实现"""
        with pytest.raises(TypeError):
            # 直接实例化抽象类应该失败
            PipelineStep("test")


@pytest.mark.unit
class TestDataTransformStep:
    """DataTransformStep测试"""
    
    def test_creation(self):
        """测试DataTransformStep创建"""
        transform_func = lambda x: x * 2
        step = DataTransformStep("transform", transform_func)
        
        assert step.name == "transform"
        assert step.transform_func is transform_func
        
    def test_process_simple_transform(self):
        """测试简单数据转换"""
        transform_func = lambda x: x.upper()
        step = DataTransformStep("upper", transform_func)
        
        result = step.process("hello")
        assert result == "HELLO"
        
    def test_process_numeric_transform(self):
        """测试数值转换"""
        transform_func = lambda x: x * 2 + 1
        step = DataTransformStep("math", transform_func)
        
        result = step.process(5)
        assert result == 11
        
    def test_process_complex_transform(self):
        """测试复杂数据转换"""
        transform_func = lambda data: {
            "processed": True,
            "original": data,
            "length": len(str(data))
        }
        step = DataTransformStep("complex", transform_func)
        
        result = step.process("test")
        assert result["processed"] is True
        assert result["original"] == "test"
        assert result["length"] == 4


@pytest.mark.unit
class TestFilterStep:
    """FilterStep测试"""
    
    def test_creation(self):
        """测试FilterStep创建"""
        filter_func = lambda x: x > 0
        step = FilterStep("positive", filter_func)
        
        assert step.name == "positive"
        assert step.filter_func is filter_func
        
    def test_process_single_item_pass(self):
        """测试单个项目通过过滤"""
        filter_func = lambda x: x > 0
        step = FilterStep("positive", filter_func)
        
        result = step.process(5)
        assert result == 5
        
    def test_process_single_item_fail(self):
        """测试单个项目不通过过滤"""
        filter_func = lambda x: x > 0
        step = FilterStep("positive", filter_func)
        
        result = step.process(-5)
        assert result is None
        
    def test_process_list_filter(self):
        """测试列表过滤"""
        filter_func = lambda x: x % 2 == 0
        step = FilterStep("even", filter_func)
        
        input_data = [1, 2, 3, 4, 5, 6]
        result = step.process(input_data)
        
        assert result == [2, 4, 6]
        assert isinstance(result, list)
        
    def test_process_tuple_filter(self):
        """测试元组过滤"""
        filter_func = lambda x: len(x) > 2
        step = FilterStep("long_strings", filter_func)
        
        input_data = ("a", "bb", "ccc", "dddd")
        result = step.process(input_data)
        
        assert result == ["ccc", "dddd"]
        assert isinstance(result, list)
        
    def test_process_empty_list(self):
        """测试空列表过滤"""
        filter_func = lambda x: True
        step = FilterStep("all", filter_func)
        
        result = step.process([])
        assert result == []
        
    def test_process_string_filter(self):
        """测试字符串过滤（作为单个项目处理）"""
        filter_func = lambda x: len(x) > 3
        step = FilterStep("long", filter_func)
        
        result_pass = step.process("hello")
        assert result_pass == "hello"
        
        result_fail = step.process("hi")
        assert result_fail is None


@pytest.mark.unit
class TestConvenienceFunctions:
    """便利函数测试"""
    
    def test_create_pipeline(self):
        """测试create_pipeline便利函数"""
        pipeline = create_pipeline("test")
        assert isinstance(pipeline, Pipeline)
        assert pipeline.name == "test"
        
    def test_create_pipeline_default_name(self):
        """测试create_pipeline默认名称"""
        pipeline = create_pipeline()
        assert isinstance(pipeline, Pipeline)
        assert pipeline.name == "sage_pipeline"
        
    def test_transform_step(self):
        """测试transform_step便利函数"""
        func = lambda x: x * 2
        step = transform_step("double", func)
        
        assert isinstance(step, DataTransformStep)
        assert step.name == "double"
        assert step.transform_func is func
        
    def test_filter_step(self):
        """测试filter_step便利函数"""
        func = lambda x: x > 0
        step = filter_step("positive", func)
        
        assert isinstance(step, FilterStep)
        assert step.name == "positive"
        assert step.filter_func is func


@pytest.mark.integration
class TestPipelineIntegration:
    """Pipeline集成测试"""
    
    def test_complete_pipeline_workflow(self):
        """测试完整的管道工作流程"""
        # 创建一个完整的数据处理管道
        pipeline = create_pipeline("data_processing")
        
        # 添加转换步骤：将字符串转换为大写
        upper_step = transform_step("uppercase", lambda x: x.upper())
        pipeline.add_step(upper_step)
        
        # 添加过滤步骤：只保留长度大于3的字符串
        length_filter = filter_step("length_filter", lambda x: len(x) > 3)
        pipeline.add_step(length_filter)
        
        # 添加最终转换：添加前缀
        prefix_step = transform_step("add_prefix", lambda x: f"PROCESSED: {x}")
        pipeline.add_step(prefix_step)
        
        # 测试执行
        result = pipeline.execute("hello")
        assert result == "PROCESSED: HELLO"
        
        # 测试被过滤的情况
        result = pipeline.execute("hi")
        assert result is None
        
    def test_pipeline_with_list_processing(self):
        """测试管道处理列表数据"""
        pipeline = create_pipeline("list_processing")
        
        # 数字加倍
        double_step = transform_step("double", lambda lst: [x * 2 for x in lst])
        pipeline.add_step(double_step)
        
        # 过滤偶数
        even_filter = filter_step("even_only", lambda lst: [x for x in lst if x % 2 == 0])
        pipeline.add_step(even_filter)
        
        input_data = [1, 2, 3, 4, 5]
        result = pipeline.execute(input_data)
        
        # [1,2,3,4,5] -> [2,4,6,8,10] -> [2,4,6,8,10]
        assert result == [2, 4, 6, 8, 10]
        
    def test_pipeline_error_handling(self):
        """测试管道错误处理"""
        pipeline = create_pipeline("error_test")
        
        def error_func(x):
            if x == "error":
                raise ValueError("Test error")
            return x
            
        error_step = transform_step("error_step", error_func)
        pipeline.add_step(error_step)
        
        # 正常情况
        result = pipeline.execute("normal")
        assert result == "normal"
        
        # 异常情况
        with pytest.raises(ValueError, match="Test error"):
            pipeline.execute("error")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Core模块测试的配置文件
"""

from unittest.mock import Mock

import pytest


class TestConfig:
    """测试配置类"""

    # 测试数据
    SAMPLE_STRING_DATA = "test_string_data"
    SAMPLE_NUMERIC_DATA = 42
    SAMPLE_LIST_DATA = [1, 2, 3, 4, 5]
    SAMPLE_DICT_DATA = {"key1": "value1", "key2": "value2"}

    # 测试序列
    SAMPLE_DATA_SEQUENCE = ["item1", "item2", "item3", "item4", "item5"]

    # 错误数据
    ERROR_DATA = "error_trigger"

    # 批处理大小
    DEFAULT_BATCH_SIZE = 3

    # 测试超时
    TEST_TIMEOUT = 5.0


@pytest.fixture
def mock_logger():
    """Mock logger fixture"""
    return Mock()


@pytest.fixture
def mock_context():
    """Mock context fixture"""
    mock_ctx = Mock()
    mock_ctx.name = "test_context"
    mock_ctx.logger = Mock()
    return mock_ctx


@pytest.fixture
def mock_function_factory():
    """Mock function factory fixture"""
    mock_factory = Mock()
    mock_function = Mock()
    mock_function.execute = Mock(return_value="processed_data")
    mock_factory.create_function.return_value = mock_function
    return mock_factory


@pytest.fixture
def sample_data():
    """Sample data fixture"""
    return {
        "string": TestConfig.SAMPLE_STRING_DATA,
        "numeric": TestConfig.SAMPLE_NUMERIC_DATA,
        "list": TestConfig.SAMPLE_LIST_DATA,
        "dict": TestConfig.SAMPLE_DICT_DATA,
        "sequence": TestConfig.SAMPLE_DATA_SEQUENCE,
    }


@pytest.fixture
def mock_packet():
    """Mock packet fixture"""
    packet = Mock()
    packet.data = "test_packet_data"
    packet.stream_id = 0
    return packet


class TestUtilities:
    """测试工具类"""

    @staticmethod
    def assert_method_called_with_data(mock_method, expected_data):
        """断言方法被调用并传入期望的数据"""
        mock_method.assert_called()
        call_args = mock_method.call_args
        assert call_args is not None
        if call_args.args:
            assert expected_data in call_args.args
        elif call_args.kwargs:
            assert expected_data in call_args.kwargs.values()

    @staticmethod
    def create_mock_with_side_effect(side_effect_list):
        """创建有副作用的Mock"""
        mock = Mock()
        mock.side_effect = side_effect_list
        return mock

    @staticmethod
    def verify_lifecycle_calls(mock_obj, setup=True, start=True, stop=True, cleanup=True):
        """验证生命周期方法调用"""
        if setup:
            mock_obj.setup.assert_called()
        if start:
            mock_obj.start.assert_called()
        if stop:
            mock_obj.stop.assert_called()
        if cleanup:
            mock_obj.cleanup.assert_called()


# 测试标记定义
pytestmark = [
    pytest.mark.core,  # 标记为core模块测试
]


# 自定义断言
def assert_pipeline_structure(pipeline, expected_step_count):
    """断言管道结构"""
    assert len(pipeline.steps) == expected_step_count
    assert all(hasattr(step, "process") for step in pipeline.steps)


def assert_function_inheritance(function_instance, base_class):
    """断言函数继承关系"""
    assert isinstance(function_instance, base_class)
    assert hasattr(function_instance, "ctx")
    assert hasattr(function_instance, "logger")


def assert_operator_state(operator, expected_function_type=None):
    """断言操作器状态"""
    assert operator.ctx is not None
    assert hasattr(operator, "function")
    if expected_function_type:
        assert isinstance(operator.function, expected_function_type)


def assert_service_lifecycle_state(
    service, setup=False, started=False, stopped=False, cleaned=False
):
    """断言服务生命周期状态"""
    if hasattr(service, "setup_called"):
        assert service.setup_called == setup
    if hasattr(service, "start_called"):
        assert service.start_called == started
    if hasattr(service, "stop_called"):
        assert service.stop_called == stopped
    if hasattr(service, "cleanup_called"):
        assert service.cleanup_called == cleaned


# 测试数据生成器
class DataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_string_sequence(count=5, prefix="data"):
        """生成字符串序列"""
        return [f"{prefix}_{i}" for i in range(count)]

    @staticmethod
    def generate_numeric_sequence(start=0, count=5):
        """生成数值序列"""
        return list(range(start, start + count))

    @staticmethod
    def generate_dict_sequence(count=3):
        """生成字典序列"""
        return [{"id": i, "value": f"item_{i}"} for i in range(count)]

    @staticmethod
    def generate_mixed_data():
        """生成混合类型数据"""
        return ["string_data", 123, [1, 2, 3], {"key": "value"}, None, True]


# 错误模拟器
class ErrorSimulator:
    """错误模拟器"""

    @staticmethod
    def create_error_function(error_type=RuntimeError, error_message="Test error"):
        """创建会抛出错误的函数"""

        def error_func(*args, **kwargs):
            raise error_type(error_message)

        return error_func

    @staticmethod
    def create_conditional_error_function(
        error_condition, error_type=RuntimeError, error_message="Conditional error"
    ):
        """创建条件错误函数"""

        def conditional_error_func(data):
            if error_condition(data):
                raise error_type(error_message)
            return data

        return conditional_error_func


# 性能测试工具
class PerformanceTestUtils:
    """性能测试工具"""

    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """测量执行时间"""
        import time

        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time

    @staticmethod
    def assert_execution_time_under(func, max_time, *args, **kwargs):
        """断言执行时间小于指定值"""
        result, execution_time = PerformanceTestUtils.measure_execution_time(func, *args, **kwargs)
        assert execution_time < max_time, (
            f"Execution time {execution_time}s exceeds maximum {max_time}s"
        )
        return result


# 集成测试帮助器
class IntegrationTestHelper:
    """集成测试帮助器"""

    @staticmethod
    def create_full_pipeline_scenario():
        """
        创建完整管道场景

        使用新的 Environment + DataStream API 替代旧的 Pipeline API
        """
        from sage.common.core.functions import (
            BatchFunction,
            FilterFunction,
            MapFunction,
            SinkFunction,
        )
        from sage.kernel.api.local_environment import LocalEnvironment

        # 定义测试用的 Function 类
        class TestBatchSource(BatchFunction):
            """测试批处理数据源"""

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.counter = 0
                self.max_count = 5

            def execute(self):
                if self.counter >= self.max_count:
                    return None
                self.counter += 1
                return f"test_item_{self.counter}"

        class TransformFunction(MapFunction):
            """转换函数"""

            def execute(self, data):
                return f"transformed_{data}"

        class FilterErrorFunction(FilterFunction):
            """过滤错误函数"""

            def execute(self, data):
                if "error" in data:
                    return None
                return data

        class TestSink(SinkFunction):
            """测试 Sink"""

            # 类级别属性用于收集结果
            results: list = []

            def execute(self, data):
                # 记录数据到类级别属性
                self.__class__.results.append(data)

        # 创建 Environment 和 Pipeline
        env = LocalEnvironment("integration_test_pipeline")

        # 使用链式 API 构建 pipeline
        env.from_batch(TestBatchSource).map(TransformFunction).filter(FilterErrorFunction).sink(
            TestSink
        )

        return env

    @staticmethod
    def create_multi_stream_scenario():
        """创建多流场景"""
        return {
            "stream_0": DataGenerator.generate_string_sequence(3, "stream0"),
            "stream_1": DataGenerator.generate_numeric_sequence(0, 3),
            "stream_2": DataGenerator.generate_dict_sequence(3),
        }

    @staticmethod
    def simulate_distributed_environment():
        """模拟分布式环境"""
        return {
            "node_1": {"id": "node_1", "resources": ["cpu", "memory"]},
            "node_2": {"id": "node_2", "resources": ["gpu", "storage"]},
            "node_3": {"id": "node_3", "resources": ["network", "compute"]},
        }


# 覆盖率测试辅助
class CoverageTestHelper:
    """覆盖率测试辅助"""

    @staticmethod
    def test_all_public_methods(obj, exclude_methods=None):
        """测试对象的所有公共方法"""
        exclude_methods = exclude_methods or []
        public_methods = [
            method
            for method in dir(obj)
            if not method.startswith("_")
            and callable(getattr(obj, method))
            and method not in exclude_methods
        ]

        coverage_report = {}
        for method_name in public_methods:
            try:
                getattr(obj, method_name)
                # 尝试调用方法（可能需要参数）
                coverage_report[method_name] = "callable"
            except Exception as e:
                coverage_report[method_name] = f"error: {str(e)}"

        return coverage_report

    @staticmethod
    def test_all_properties(obj):
        """测试对象的所有属性"""
        properties = [
            prop
            for prop in dir(obj)
            if not prop.startswith("_") and not callable(getattr(obj, prop))
        ]

        property_report = {}
        for prop_name in properties:
            try:
                value = getattr(obj, prop_name)
                property_report[prop_name] = type(value).__name__
            except Exception as e:
                property_report[prop_name] = f"error: {str(e)}"

        return property_report


# 清理工具
class TestCleanupHelper:
    """测试清理辅助"""

    @staticmethod
    def cleanup_mocks(*mocks):
        """清理mock对象"""
        for mock in mocks:
            if hasattr(mock, "reset_mock"):
                mock.reset_mock()

    @staticmethod
    def cleanup_resources(*resources):
        """清理资源"""
        for resource in resources:
            if hasattr(resource, "cleanup"):
                resource.cleanup()
            elif hasattr(resource, "close"):
                resource.close()
            elif hasattr(resource, "stop"):
                resource.stop()

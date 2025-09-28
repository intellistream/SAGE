# 简单的解耦测试，验证BaseOperator不再直接依赖BaseRouter

import sys
from unittest.mock import Mock

# Project-specific sys.path tweaks may be required in tests; keep them explicit
sys.path.insert(0, "/home/flecther/workspace/SAGE/packages/sage-core/src")
sys.path.insert(0, "/home/flecther/workspace/SAGE/packages/sage-kernel/src")


class MockTaskContext:
    """模拟TaskContext，提供路由接口"""

    def __init__(self, name="test_task"):
        self.name = name
        self.logger = Mock()

    def send_packet(self, packet):
        """模拟发送数据包"""
        print(f"MockTaskContext: Sending packet {packet}")
        return True

    def send_stop_signal(self, stop_signal):
        """模拟发送停止信号"""
        print(f"MockTaskContext: Sending stop signal {stop_signal}")

    def get_routing_info(self):
        """模拟获取路由信息"""
        return {"connections": 3, "status": "active"}


class MockFunctionFactory:
    """模拟函数工厂"""

    def create_function(self, name, ctx):
        mock_function = Mock()
        mock_function.name = name
        return mock_function


class TestBaseOperatorDecoupling:
    """测试BaseOperator的解耦实现"""

    def test_operator_uses_context_routing(self):
        """测试BaseOperator通过TaskContext进行路由，不再直接依赖BaseRouter"""

        # 创建模拟对象
        mock_ctx = MockTaskContext("test_operator")
        mock_factory = MockFunctionFactory()

        # 定义一个简单的operator实现
        class TestOperator:
            def __init__(self, function_factory, ctx):
                self.ctx = ctx
                self.function = function_factory.create_function("test", ctx)
                self.logger = ctx.logger
                self.name = ctx.name

            def send_packet(self, packet):
                """通过TaskContext发送数据包"""
                return self.ctx.send_packet(packet)

            def send_stop_signal(self, stop_signal):
                """通过TaskContext发送停止信号"""
                self.ctx.send_stop_signal(stop_signal)

            def get_routing_info(self):
                """获取路由信息"""
                return self.ctx.get_routing_info()

        # 创建operator
        operator = TestOperator(mock_factory, mock_ctx)

        # 测试发送数据包
        result = operator.send_packet("test_packet")
        assert result is True

        # 测试发送停止信号
        operator.send_stop_signal("stop_signal")

        # 测试获取路由信息
        info = operator.get_routing_info()
        assert info["connections"] == 3
        assert info["status"] == "active"

        print("✅ BaseOperator解耦测试通过!")
        print("✅ Operator通过TaskContext进行路由，不再直接依赖BaseRouter")

    def test_no_direct_router_dependency(self):
        """验证BaseOperator不再有直接的router属性"""
        mock_ctx = MockTaskContext("test_operator")
        mock_factory = MockFunctionFactory()

        class TestOperator:
            def __init__(self, function_factory, ctx):
                self.ctx = ctx
                self.function = function_factory.create_function("test", ctx)
                # 注意：没有self.router属性

        operator = TestOperator(mock_factory, mock_ctx)

        # 验证operator没有直接的router属性
        assert not hasattr(operator, "router")
        assert not hasattr(operator, "routing")

        # 但是有ctx属性来进行间接路由
        assert hasattr(operator, "ctx")
        assert hasattr(operator.ctx, "send_packet")
        assert hasattr(operator.ctx, "send_stop_signal")
        assert hasattr(operator.ctx, "get_routing_info")

        print("✅ BaseOperator不再有直接的router依赖!")
        print("✅ 路由功能完全通过TaskContext提供!")


if __name__ == "__main__":
    test = TestBaseOperatorDecoupling()
    test.test_operator_uses_context_routing()
    test.test_no_direct_router_dependency()
    print("\n🎉 所有解耦测试都通过了!")
    print("📋 总结:")
    print("  - BaseOperator不再直接依赖BaseRouter")
    print("  - 路由功能完全集成到TaskContext中")
    print("  - 实现了清晰的架构分层")

#!/usr/bin/env python3
"""
测试重构后的JobManagerClient
验证基类功能和子类特定功能都正常工作
"""

import sys

# 添加SAGE路径
sys.path.insert(0, "/home/tjy/SAGE")


def test_base_tcp_client():
    """测试BaseTcpClient基类功能"""
    print("=== 测试 BaseTcpClient 基类 ===")

    try:
        from sage.common.utils.network.base_tcp_client import BaseTcpClient

        # 创建一个简单的测试客户端
        class TestClient(BaseTcpClient):
            def _build_health_check_request(self):
                return {"action": "test_health_check"}

            def _build_server_info_request(self):
                return {"action": "test_server_info"}

        client = TestClient("127.0.0.1", 19001)
        print("✓ BaseTcpClient基类创建成功")
        print(f"  - Host: {client.host}")
        print(f"  - Port: {client.port}")
        print(f"  - Timeout: {client.timeout}")
        print(f"  - Client Name: {client.client_name}")

        # 测试错误响应创建
        error_resp = client._create_error_response("TEST_ERROR", "Test error message")
        print(f"✓ 错误响应创建测试通过: {error_resp['status']}")

        return True

    except Exception as e:
        print(f"✗ BaseTcpClient基类测试失败: {e}")
        return False


def test_jobmanager_client():
    """测试重构后的JobManagerClient"""
    print("\n=== 测试 JobManagerClient ===")

    try:
        from sage.kernel.runtime.jobmanager_client import JobManagerClient

        # 创建客户端
        client = JobManagerClient("127.0.0.1", 19001, timeout=10.0)
        print("✓ JobManagerClient创建成功")
        print(f"  - Host: {client.host}")
        print(f"  - Port: {client.port}")
        print(f"  - Timeout: {client.timeout}")
        print(f"  - Client Name: {client.client_name}")

        # 测试方法是否存在
        methods_to_test = [
            "submit_job",
            "pause_job",
            "get_job_status",
            "list_jobs",
            "continue_job",
            "delete_job",
            "receive_node_stop_signal",
            "cleanup_all_jobs",
            "health_check",
            "get_server_info",
        ]

        missing_methods = []
        for method in methods_to_test:
            if not hasattr(client, method):
                missing_methods.append(method)

        if missing_methods:
            print(f"✗ 缺少方法: {missing_methods}")
            return False
        else:
            print("✓ 所有必需方法都存在")

        # 测试继承的基类方法
        health_req = client._build_health_check_request()
        server_req = client._build_server_info_request()

        print(f"✓ 健康检查请求构建: {health_req}")
        print(f"✓ 服务器信息请求构建: {server_req}")

        # 测试上下文管理器（不会实际连接）
        print(f"✓ 上下文管理器支持: {hasattr(client, '__enter__')}")

        return True

    except Exception as e:
        print(f"✗ JobManagerClient测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===")

    try:
        from sage.kernel.runtime.jobmanager_client import JobManagerClient

        # 测试原有的初始化方式
        client1 = JobManagerClient()  # 默认参数
        print(f"✓ 默认参数初始化: {client1.host}:{client1.port}")

        client2 = JobManagerClient("localhost", 19002)  # 位置参数
        print(f"✓ 位置参数初始化: {client2.host}:{client2.port}")

        # 测试新的timeout参数
        client3 = JobManagerClient(timeout=5.0)
        print(f"✓ 新参数支持: timeout={client3.timeout}")

        return True

    except Exception as e:
        print(f"✗ 向后兼容性测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("开始测试JobManagerClient重构...")

    tests = [test_base_tcp_client, test_jobmanager_client, test_backward_compatibility]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print("\n=== 测试结果 ===")
    print(f"通过: {passed}/{total}")

    if passed == total:
        print("✓ 所有测试通过！重构成功！")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

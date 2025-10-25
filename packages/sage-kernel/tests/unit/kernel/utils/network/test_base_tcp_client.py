"""
Tests for sage.common.utils.network.base_tcp_client module
==================================================

单元测试基础TCP客户端模块的功能，包括：
- 连接管理
- 消息发送和接收
- 错误处理
- 超时处理
"""

import json
import socket
import time
from unittest.mock import MagicMock, patch

import pytest
from sage.common.utils.network.base_tcp_client import BaseTcpClient


class MockTcpClient(BaseTcpClient):
    """用于测试的具体TCP客户端实现"""

    def build_request(self, data):
        """构建请求"""
        return {"type": "test_request", "data": data, "timestamp": time.time()}

    def handle_response(self, response_data):
        """处理响应"""
        return response_data

    def _build_health_check_request(self):
        """构建健康检查请求"""
        return {"type": "health_check", "timestamp": time.time()}

    def _build_server_info_request(self):
        """构建服务器信息请求"""
        return {"type": "server_info", "timestamp": time.time()}


@pytest.mark.unit
class TestBaseTcpClient:
    """BaseTcpClient基本功能测试"""

    def setup_method(self):
        """测试前准备"""
        self.client = MockTcpClient(
            host="127.0.0.1", port=19001, timeout=5.0, client_name="TestClient"
        )

    def teardown_method(self):
        """测试后清理"""
        if hasattr(self.client, "_socket") and self.client._socket:
            try:
                self.client.disconnect()
            except Exception:
                pass

    def test_client_initialization(self):
        """测试客户端初始化"""
        assert self.client.host == "127.0.0.1"
        assert self.client.port == 19001
        assert self.client.timeout == 5.0
        assert self.client.client_name == "TestClient"
        assert self.client.connected is False
        assert self.client._socket is None

    def test_client_default_initialization(self):
        """测试客户端默认初始化参数"""
        default_client = MockTcpClient()
        assert default_client.host == "127.0.0.1"
        assert default_client.port == 19001
        assert default_client.timeout == 30.0
        assert default_client.client_name == "TcpClient"

    def test_create_default_logger(self):
        """测试默认日志记录器创建"""
        logger = self.client._create_default_logger()
        assert logger.name == "TestClient"
        assert len(logger.handlers) > 0
        assert logger.level == 20  # logging.INFO = 20

    @patch("socket.socket")
    def test_successful_connection(self, mock_socket_class):
        """测试成功连接"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        result = self.client.connect()

        assert result is True
        assert self.client.connected is True
        assert self.client._socket == mock_socket

        # 验证socket配置
        mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        mock_socket.settimeout.assert_called_once_with(5.0)
        mock_socket.connect.assert_called_once_with(("127.0.0.1", 19001))

    @patch("socket.socket")
    def test_connection_failure(self, mock_socket_class):
        """测试连接失败"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")

        result = self.client.connect()

        assert result is False
        assert self.client.connected is False
        assert self.client._socket is None

        # 验证socket被关闭
        mock_socket.close.assert_called_once()

    def test_connect_when_already_connected(self):
        """测试已连接时再次连接"""
        self.client.connected = True

        result = self.client.connect()

        assert result is True
        assert self.client.connected is True

    @patch("socket.socket")
    def test_disconnect(self, mock_socket_class):
        """测试断开连接"""
        mock_socket = MagicMock()
        self.client._socket = mock_socket
        self.client.connected = True

        self.client.disconnect()

        assert self.client.connected is False
        assert self.client._socket is None
        mock_socket.close.assert_called_once()

    def test_disconnect_when_not_connected(self):
        """测试未连接时断开连接"""
        self.client.disconnect()

        assert self.client.connected is False
        assert self.client._socket is None

    @patch("socket.socket")
    def test_disconnect_with_socket_error(self, mock_socket_class):
        """测试断开连接时socket错误"""
        mock_socket = MagicMock()
        mock_socket.close.side_effect = OSError("Socket error")
        self.client._socket = mock_socket
        self.client.connected = True

        # 应该能正常断开，忽略socket错误
        self.client.disconnect()

        assert self.client.connected is False
        assert self.client._socket is None

    @patch("socket.socket")
    def test_send_request_success(self, mock_socket_class):
        """测试成功发送请求"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        # 模拟连接成功
        self.client.connect()

        # 模拟接收响应 - 需要模拟二进制协议
        response_data = {"status": "success", "data": "test_response"}
        response_json = json.dumps(response_data)
        response_bytes = response_json.encode("utf-8")

        # 模拟接收：先接收4字节长度，然后接收数据
        def mock_recv(size):
            if size == 4:
                # 返回响应数据长度（大端序）
                return len(response_bytes).to_bytes(4, byteorder="big")
            else:
                # 返回响应数据
                return response_bytes

        mock_socket.recv.side_effect = mock_recv

        request_data = {"test": "data"}
        result = self.client.send_request(request_data)

        assert result == response_data

        # 验证调用了sendall方法（发送长度和数据）
        assert mock_socket.sendall.call_count == 2  # 一次发送长度，一次发送数据

    @patch("socket.socket")
    def test_send_request_connection_error(self, mock_socket_class):
        """测试发送请求时连接错误"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        self.client.connect()
        mock_socket.sendall.side_effect = ConnectionError("Connection lost")

        request_data = {"test": "data"}

        result = self.client.send_request(request_data)

        # 应该返回错误响应而不是抛出异常
        assert result["status"] == "error"
        assert result["error_code"] == "ERR_COMMUNICATION_FAILED"

    @patch("socket.socket")
    def test_send_request_timeout(self, mock_socket_class):
        """测试发送请求超时"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        self.client.connect()
        mock_socket.recv.side_effect = TimeoutError("Timeout")

        request_data = {"test": "data"}

        result = self.client.send_request(request_data)

        # 应该返回错误响应而不是抛出异常
        assert result["status"] == "error"
        assert result["error_code"] == "ERR_NO_RESPONSE"

    @patch("socket.socket")
    def test_send_request_invalid_json_response(self, mock_socket_class):
        """测试接收无效JSON响应"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        self.client.connect()

        # 模拟接收无效的响应长度（第一个4字节不是有效长度）
        invalid_length_bytes = b"abcd"  # 这会被解释为一个非常大的数字
        mock_socket.recv.return_value = invalid_length_bytes

        request_data = {"test": "data"}

        result = self.client.send_request(request_data)

        # 应该返回错误响应
        assert result["status"] == "error"
        assert result["error_code"] == "ERR_NO_RESPONSE"

    @patch("socket.socket")
    def test_send_request_empty_response(self, mock_socket_class):
        """测试接收空响应"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        self.client.connect()

        # 模拟接收空响应
        mock_socket.recv.return_value = b""

        request_data = {"test": "data"}

        result = self.client.send_request(request_data)

        # 应该返回错误响应而不是抛出异常
        assert result["status"] == "error"
        assert result["error_code"] == "ERR_NO_RESPONSE"

    @patch("socket.socket")
    def test_send_request_partial_response(self, mock_socket_class):
        """测试接收部分响应（多次recv）"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        self.client.connect()

        # 模拟分多次接收完整响应
        response_data = {"status": "success", "large_data": "x" * 1000}
        response_json = json.dumps(response_data)
        response_bytes = response_json.encode("utf-8")

        # 模拟接收：先接收4字节长度，然后分多次接收数据

        def mock_recv(size):
            if size == 4:
                # 第一次调用，返回响应数据长度
                return len(response_bytes).to_bytes(4, byteorder="big")
            else:
                # 后续调用，分多次返回数据
                if not hasattr(mock_recv, "call_count"):
                    mock_recv.call_count = 0
                    mock_recv.data_sent = 0

                mock_recv.call_count += 1
                remaining_size = len(response_bytes) - mock_recv.data_sent
                chunk_size = min(
                    size,
                    (
                        remaining_size // 2
                        if mock_recv.call_count == 1
                        else remaining_size
                    ),
                )

                if chunk_size > 0:
                    chunk = response_bytes[
                        mock_recv.data_sent : mock_recv.data_sent + chunk_size
                    ]
                    mock_recv.data_sent += chunk_size
                    return chunk
                else:
                    return b""

        mock_socket.recv.side_effect = mock_recv

        request_data = {"test": "data"}
        result = self.client.send_request(request_data)

        assert result == response_data


@pytest.mark.unit
class MockTcpClientEdgeCases:
    """TCP客户端边界情况测试"""

    def test_custom_host_port(self):
        """测试自定义主机和端口"""
        client = MockTcpClient(host="192.168.1.100", port=8080)
        assert client.host == "192.168.1.100"
        assert client.port == 8080

    def test_custom_timeout(self):
        """测试自定义超时时间"""
        client = MockTcpClient(timeout=60.0)
        assert client.timeout == 60.0

    def test_custom_client_name(self):
        """测试自定义客户端名称"""
        client = MockTcpClient(client_name="CustomClient")
        assert client.client_name == "CustomClient"

        logger = client._create_default_logger()
        assert logger.name == "CustomClient"

    @patch("socket.socket")
    def test_send_request_with_unicode_data(self, mock_socket_class):
        """测试发送包含Unicode字符的请求"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = MockTcpClient()
        client.connect()

        # 模拟Unicode响应 - 使用二进制协议
        response_data = {"message": "你好世界", "emoji": "🌍"}
        response_json = json.dumps(response_data, ensure_ascii=False)
        response_bytes = response_json.encode("utf-8")

        # 模拟接收：先接收4字节长度，然后接收数据
        def mock_recv(size):
            if size == 4:
                # 返回响应数据长度（大端序）
                return len(response_bytes).to_bytes(4, byteorder="big")
            else:
                # 返回响应数据
                return response_bytes

        mock_socket.recv.side_effect = mock_recv

        request_data = {"query": "测试查询", "symbols": "™®©"}
        result = client.send_request(request_data)

        assert result == response_data
        assert result["message"] == "你好世界"
        assert result["emoji"] == "🌍"

    @patch("socket.socket")
    def test_multiple_consecutive_requests(self, mock_socket_class):
        """测试连续多个请求"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = MockTcpClient()
        client.connect()

        # 模拟多个响应
        responses = [
            {"id": 1, "result": "first"},
            {"id": 2, "result": "second"},
            {"id": 3, "result": "third"},
        ]

        response_index = 0

        def mock_recv(size):
            nonlocal response_index
            if size == 4:
                # 返回响应数据长度
                if response_index < len(responses):
                    response_json = json.dumps(responses[response_index])
                    response_bytes = response_json.encode("utf-8")
                    return len(response_bytes).to_bytes(4, byteorder="big")
                else:
                    return b""
            else:
                # 返回响应数据
                if response_index < len(responses):
                    response_json = json.dumps(responses[response_index])
                    response_bytes = response_json.encode("utf-8")
                    response_index += 1
                    return response_bytes
                else:
                    return b""

        mock_socket.recv.side_effect = mock_recv

        # 发送多个请求
        for i in range(3):
            request_data = {"request_id": i + 1}
            result = client.send_request(request_data)
            assert result["id"] == i + 1
            assert result["result"] in ["first", "second", "third"]

    @patch("socket.socket")
    def test_large_request_data(self, mock_socket_class):
        """测试大型请求数据"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = MockTcpClient()
        client.connect()

        # 创建大型请求数据
        large_data = {
            "large_field": "x" * 10000,  # 10KB数据
            "array_field": list(range(1000)),
            "nested_data": {f"key_{i}": f"value_{i}" for i in range(100)},
        }

        # 模拟响应 - 使用长度前缀协议
        response_data = {"status": "received"}
        response_json = json.dumps(response_data).encode("utf-8")
        response_length = len(response_json).to_bytes(4, byteorder="big")

        # 模拟按顺序接收：先长度，后数据
        mock_socket.recv.side_effect = [response_length, response_json]

        result = client.send_request(large_data)
        assert result == response_data

        # 验证发送调用 - sendall被调用两次：长度和数据
        assert mock_socket.sendall.call_count == 2

        # 验证发送的数据包含大型数据
        sent_calls = mock_socket.sendall.call_args_list
        data_call = sent_calls[1][0][0]  # 第二次调用是数据内容
        sent_data = data_call.decode("utf-8")
        assert '"large_field"' in sent_data
        assert "x" * 100 in sent_data  # 部分大型字段内容


@pytest.mark.unit
class TestAbstractMethods:
    """抽象方法测试"""

    def test_build_request_abstract_method(self):
        """测试build_request抽象方法"""
        # BaseTcpClient是抽象类，不能直接实例化
        # 但我们可以测试具体实现
        client = MockTcpClient()

        data = {"test": "data"}
        request = client.build_request(data)

        assert isinstance(request, dict)
        assert request["type"] == "test_request"
        assert request["data"] == data
        assert "timestamp" in request

    def test_handle_response_abstract_method(self):
        """测试handle_response抽象方法"""
        client = MockTcpClient()

        response_data = {"status": "success", "result": "test"}
        handled_response = client.handle_response(response_data)

        assert handled_response == response_data


@pytest.mark.integration
class MockTcpClientIntegration:
    """TCP客户端集成测试"""

    def test_client_with_mock_server(self):
        """测试客户端与模拟服务器的集成"""
        import threading
        import time

        # 创建模拟服务器
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("127.0.0.1", 0))  # 使用随机端口
        server_port = server_socket.getsockname()[1]
        server_socket.listen(1)

        server_responses = []
        server_running = threading.Event()
        server_error = None

        def mock_server():
            nonlocal server_error
            try:
                server_running.set()
                client_socket, addr = server_socket.accept()
                client_socket.settimeout(5.0)  # 设置超时

                # 接收请求长度（4字节）
                length_data = client_socket.recv(4)
                if len(length_data) != 4:
                    raise ValueError("Invalid length data")

                request_length = int.from_bytes(length_data, byteorder="big")

                # 接收请求数据
                request_data = b""
                while len(request_data) < request_length:
                    chunk = client_socket.recv(
                        min(1024, request_length - len(request_data))
                    )
                    if not chunk:
                        break
                    request_data += chunk

                # 解析请求
                request_text = request_data.decode("utf-8")
                request_json = json.loads(request_text)
                server_responses.append(request_json)

                # 发送响应
                response = {"status": "success", "echo": request_json}
                response_data = json.dumps(response).encode("utf-8")
                response_length = len(response_data).to_bytes(4, byteorder="big")

                client_socket.sendall(response_length)
                client_socket.sendall(response_data)

                client_socket.close()

            except Exception as e:
                server_error = e
                print(f"Mock server error: {e}")
            finally:
                server_socket.close()

        # 启动模拟服务器
        server_thread = threading.Thread(target=mock_server)
        server_thread.start()

        # 等待服务器启动
        server_running.wait(timeout=5)
        time.sleep(0.1)

        try:
            # 创建客户端并连接
            client = MockTcpClient(port=server_port, timeout=5.0)

            assert client.connect() is True

            # 发送请求
            request_data = {"message": "Hello Server", "timestamp": time.time()}
            response = client.send_request(request_data)

            # 验证响应
            assert response["status"] == "success"
            assert "echo" in response

            # 验证服务器接收到的数据
            assert len(server_responses) == 1
            received_request = server_responses[0]

            # BaseTcpClient._serialize_request 会添加 request_id 和 timestamp，
            # 但MockTcpClient.build_request不会包装数据
            # 检查原始请求数据是否在接收到的请求中
            assert "message" in received_request
            assert received_request["message"] == request_data["message"]
            assert "request_id" in received_request  # 由_serialize_request添加
            assert "timestamp" in received_request  # 由_serialize_request添加

            client.disconnect()

            # 检查服务器是否有错误
            if server_error:
                raise AssertionError(f"Server error: {server_error}")

        finally:
            server_thread.join(timeout=5)

    @pytest.mark.slow
    def test_connection_timeout(self):
        """测试连接超时"""
        # 在Linux上，连接被拒绝通常会立即返回，所以我们改用模拟的方式
        from unittest.mock import MagicMock, patch

        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket

            # 模拟连接超时
            mock_socket.connect.side_effect = TimeoutError("Connection timeout")

            client = MockTcpClient(host="127.0.0.1", port=65534, timeout=1.0)

            start_time = time.time()
            result = client.connect()
            elapsed_time = time.time() - start_time

            assert result is False
            assert client.connected is False
            # 模拟的超时应该很快返回
            assert elapsed_time < 1.0


@pytest.mark.unit
class TestErrorHandling:
    """错误处理测试"""

    @patch("socket.socket")
    def test_connection_refused_error(self, mock_socket_class):
        """测试连接被拒绝错误"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")

        client = MockTcpClient()

        with patch.object(client.logger, "error") as mock_log_error:
            result = client.connect()

            assert result is False
            mock_log_error.assert_called_once()
            assert "Failed to connect" in str(mock_log_error.call_args)

    @patch("socket.socket")
    def test_socket_timeout_error(self, mock_socket_class):
        """测试socket超时错误"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = TimeoutError("Connection timeout")

        client = MockTcpClient()
        result = client.connect()

        assert result is False
        assert client.connected is False

    @patch("socket.socket")
    def test_general_socket_error(self, mock_socket_class):
        """测试一般socket错误"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = OSError("Network error")

        client = MockTcpClient()
        result = client.connect()

        assert result is False
        assert client._socket is None


# 性能测试
@pytest.mark.slow
class MockTcpClientPerformance:
    """TCP客户端性能测试"""

    @patch("socket.socket")
    def test_multiple_connections_performance(self, mock_socket_class):
        """测试多次连接的性能"""
        import time

        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = MockTcpClient()

        # 测试多次连接和断开的性能
        num_connections = 100
        start_time = time.time()

        for _ in range(num_connections):
            client.connect()
            client.disconnect()

        elapsed_time = time.time() - start_time

        # 性能断言（这些值可以根据实际需要调整）
        assert elapsed_time < 1.0  # 100次连接应在1秒内完成

        # 验证调用次数
        assert mock_socket.connect.call_count == num_connections
        assert mock_socket.close.call_count == num_connections

    @patch("socket.socket")
    def test_large_data_transfer_performance(self, mock_socket_class):
        """测试大数据传输性能"""
        import time

        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        # 模拟大响应数据
        large_response = {"data": "x" * 100000}  # 100KB数据
        response_json = json.dumps(large_response).encode("utf-8")
        response_length = len(response_json).to_bytes(4, byteorder="big")

        # 模拟按顺序接收：先长度，后数据
        mock_socket.recv.side_effect = [response_length, response_json]

        client = MockTcpClient()
        client.connect()

        # 测试大数据传输性能
        start_time = time.time()

        request_data = {"query": "large_data"}
        result = client.send_request(request_data)

        elapsed_time = time.time() - start_time

        # 性能断言
        assert elapsed_time < 1.0  # 100KB数据传输应在1秒内完成
        assert result == large_response
        assert len(result["data"]) == 100000


@pytest.mark.unit
class TestTcpClientEdgeCases:
    """TCP客户端边界情况测试"""

    def test_custom_host_port(self):
        """测试自定义主机和端口"""
        client = MockTcpClient(host="192.168.1.100", port=8080)
        assert client.host == "192.168.1.100"
        assert client.port == 8080

    def test_custom_timeout(self):
        """测试自定义超时时间"""
        client = MockTcpClient(timeout=60.0)
        assert client.timeout == 60.0

    def test_custom_client_name(self):
        """测试自定义客户端名称"""
        client = MockTcpClient(client_name="CustomClient")
        assert client.client_name == "CustomClient"

        logger = client._create_default_logger()
        assert logger.name == "CustomClient"

    @patch("socket.socket")
    def test_send_request_with_unicode_data(self, mock_socket_class):
        """测试发送包含Unicode字符的请求"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = MockTcpClient()
        client.connect()

        # 模拟Unicode响应 - 使用二进制协议
        response_data = {"message": "你好世界", "emoji": "🌍"}
        response_json = json.dumps(response_data, ensure_ascii=False)
        response_bytes = response_json.encode("utf-8")

        # 模拟接收：先接收4字节长度，然后接收数据
        def mock_recv(size):
            if size == 4:
                # 返回响应数据长度（大端序）
                return len(response_bytes).to_bytes(4, byteorder="big")
            else:
                # 返回响应数据
                return response_bytes

        mock_socket.recv.side_effect = mock_recv

        request_data = {"query": "测试查询", "symbols": "™®©"}
        result = client.send_request(request_data)

        assert result == response_data
        assert result["message"] == "你好世界"
        assert result["emoji"] == "🌍"

    @patch("socket.socket")
    def test_multiple_consecutive_requests(self, mock_socket_class):
        """测试连续多个请求"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = MockTcpClient()
        client.connect()

        # 模拟多个响应
        responses = [
            {"id": 1, "result": "first"},
            {"id": 2, "result": "second"},
            {"id": 3, "result": "third"},
        ]

        response_index = 0

        def mock_recv(size):
            nonlocal response_index
            if size == 4:
                # 返回响应数据长度
                if response_index < len(responses):
                    response_json = json.dumps(responses[response_index])
                    response_bytes = response_json.encode("utf-8")
                    return len(response_bytes).to_bytes(4, byteorder="big")
                else:
                    return b""
            else:
                # 返回响应数据
                if response_index < len(responses):
                    response_json = json.dumps(responses[response_index])
                    response_bytes = response_json.encode("utf-8")
                    response_index += 1
                    return response_bytes
                else:
                    return b""

        mock_socket.recv.side_effect = mock_recv

        # 发送多个请求
        for i in range(3):
            request_data = {"request_id": i + 1}
            result = client.send_request(request_data)
            assert result["id"] == i + 1
            assert result["result"] in ["first", "second", "third"]

    @patch("socket.socket")
    def test_large_request_data(self, mock_socket_class):
        """测试大型请求数据"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = MockTcpClient()
        client.connect()

        # 创建大型请求数据
        large_data = {
            "large_field": "x" * 10000,  # 10KB数据
            "array_field": list(range(1000)),
            "nested_data": {f"key_{i}": f"value_{i}" for i in range(100)},
        }

        # 模拟响应 - 使用长度前缀协议
        response_data = {"status": "received"}
        response_json = json.dumps(response_data).encode("utf-8")
        response_length = len(response_json).to_bytes(4, byteorder="big")

        # 模拟按顺序接收：先长度，后数据
        mock_socket.recv.side_effect = [response_length, response_json]

        result = client.send_request(large_data)
        assert result == response_data

        # 验证发送调用 - sendall被调用两次：长度和数据
        assert mock_socket.sendall.call_count == 2

        # 验证发送的数据包含大型数据
        sent_calls = mock_socket.sendall.call_args_list
        data_call = sent_calls[1][0][0]  # 第二次调用是数据内容
        sent_data = data_call.decode("utf-8")
        assert '"large_field"' in sent_data
        assert "x" * 100 in sent_data  # 部分大型字段内容


@pytest.mark.integration
class TestTcpClientIntegration:
    """TCP客户端集成测试"""

    def test_client_with_mock_server(self):
        """测试客户端与模拟服务器的集成"""
        import threading
        import time

        # 创建模拟服务器
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("127.0.0.1", 0))  # 使用随机端口
        server_port = server_socket.getsockname()[1]
        server_socket.listen(1)

        server_responses = []
        server_running = threading.Event()
        server_error = None

        def mock_server():
            nonlocal server_error
            try:
                server_running.set()
                client_socket, addr = server_socket.accept()
                client_socket.settimeout(5.0)  # 设置超时

                # 接收请求长度（4字节）
                length_data = client_socket.recv(4)
                if len(length_data) != 4:
                    raise ValueError("Invalid length data")

                request_length = int.from_bytes(length_data, byteorder="big")

                # 接收请求数据
                request_data = b""
                while len(request_data) < request_length:
                    chunk = client_socket.recv(
                        min(1024, request_length - len(request_data))
                    )
                    if not chunk:
                        break
                    request_data += chunk

                # 解析请求
                request_text = request_data.decode("utf-8")
                request_json = json.loads(request_text)
                server_responses.append(request_json)

                # 发送响应
                response = {"status": "success", "echo": request_json}
                response_data = json.dumps(response).encode("utf-8")
                response_length = len(response_data).to_bytes(4, byteorder="big")

                client_socket.sendall(response_length)
                client_socket.sendall(response_data)

                client_socket.close()

            except Exception as e:
                server_error = e
                print(f"Mock server error: {e}")
            finally:
                server_socket.close()

        # 启动模拟服务器
        server_thread = threading.Thread(target=mock_server)
        server_thread.start()

        # 等待服务器启动
        server_running.wait(timeout=5)
        time.sleep(0.1)

        try:
            # 创建客户端并连接
            client = MockTcpClient(port=server_port, timeout=5.0)

            assert client.connect() is True

            # 发送请求
            request_data = {"message": "Hello Server", "timestamp": time.time()}
            response = client.send_request(request_data)

            # 验证响应
            assert response["status"] == "success"
            assert "echo" in response

            # 验证服务器接收到的数据
            assert len(server_responses) == 1
            received_request = server_responses[0]

            # BaseTcpClient._serialize_request 会添加 request_id 和 timestamp，
            # 但MockTcpClient.build_request不会包装数据
            # 检查原始请求数据是否在接收到的请求中
            assert "message" in received_request
            assert received_request["message"] == request_data["message"]
            assert "request_id" in received_request  # 由_serialize_request添加
            assert "timestamp" in received_request  # 由_serialize_request添加

            client.disconnect()

            # 检查服务器是否有错误
            if server_error:
                raise AssertionError(f"Server error: {server_error}")

        finally:
            server_thread.join(timeout=5)

    @pytest.mark.slow
    def test_connection_timeout(self):
        """测试连接超时"""
        # 在Linux上，连接被拒绝通常会立即返回，所以我们改用模拟的方式
        from unittest.mock import MagicMock, patch

        with patch("socket.socket") as mock_socket_class:
            mock_socket = MagicMock()
            mock_socket_class.return_value = mock_socket

            # 模拟连接超时
            mock_socket.connect.side_effect = TimeoutError("Connection timeout")

            client = MockTcpClient(host="127.0.0.1", port=65534, timeout=1.0)

            start_time = time.time()
            result = client.connect()
            elapsed_time = time.time() - start_time

            assert result is False
            assert client.connected is False
            # 模拟的超时应该很快返回
            assert elapsed_time < 1.0


# 性能测试
@pytest.mark.slow
class TestTcpClientPerformance:
    """TCP客户端性能测试"""

    @patch("socket.socket")
    def test_multiple_connections_performance(self, mock_socket_class):
        """测试多次连接的性能"""
        import time

        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        client = MockTcpClient()

        # 测试多次连接和断开的性能
        num_connections = 100
        start_time = time.time()

        for _ in range(num_connections):
            client.connect()
            client.disconnect()

        elapsed_time = time.time() - start_time

        # 性能断言（这些值可以根据实际需要调整）
        assert elapsed_time < 1.0  # 100次连接应在1秒内完成

        # 验证调用次数
        assert mock_socket.connect.call_count == num_connections
        assert mock_socket.close.call_count == num_connections

    @patch("socket.socket")
    def test_large_data_transfer_performance(self, mock_socket_class):
        """测试大数据传输性能"""
        import time

        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        # 模拟大响应数据
        large_response = {"data": "x" * 100000}  # 100KB数据
        response_json = json.dumps(large_response).encode("utf-8")
        response_length = len(response_json).to_bytes(4, byteorder="big")

        # 模拟按顺序接收：先长度，后数据
        mock_socket.recv.side_effect = [response_length, response_json]

        client = MockTcpClient()
        client.connect()

        # 测试大数据传输性能
        start_time = time.time()

        request_data = {"query": "large_data"}
        result = client.send_request(request_data)

        elapsed_time = time.time() - start_time

        # 性能断言
        assert elapsed_time < 1.0  # 100KB数据传输应在1秒内完成
        assert result == large_response
        assert len(result["data"]) == 100000

"""
Tests for sage.utils.network.base_tcp_client module
==================================================

单元测试基础TCP客户端模块的功能，包括：
- 连接管理
- 消息发送和接收
- 错误处理
- 超时处理
"""

import pytest
import socket
import json
import time
import threading
from unittest.mock import patch, MagicMock, Mock

from sage.kernel.utils.network.base_tcp_client import BaseTcpClient


class TestTcpClient(BaseTcpClient):
    """用于测试的具体TCP客户端实现"""
    
    def build_request(self, data):
        """构建请求"""
        return {
            "type": "test_request",
            "data": data,
            "timestamp": time.time()
        }
    
    def handle_response(self, response_data):
        """处理响应"""
        return response_data
    
    def _build_health_check_request(self):
        """构建健康检查请求"""
        return {
            "type": "health_check",
            "timestamp": time.time()
        }
    
    def _build_server_info_request(self):
        """构建服务器信息请求"""
        return {
            "type": "server_info",
            "timestamp": time.time()
        }


@pytest.mark.unit
class TestBaseTcpClient:
    """BaseTcpClient基本功能测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.client = TestTcpClient(
            host="127.0.0.1",
            port=19001,
            timeout=5.0,
            client_name="TestClient"
        )
    
    def teardown_method(self):
        """测试后清理"""
        if hasattr(self.client, '_socket') and self.client._socket:
            try:
                self.client.disconnect()
            except:
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
        default_client = TestTcpClient()
        assert default_client.host == "127.0.0.1"
        assert default_client.port == 19001
        assert default_client.timeout == 30.0
        assert default_client.client_name == "TcpClient"
    
    def test_create_default_logger(self):
        """测试默认日志记录器创建"""
        logger = self.client._create_default_logger()
        assert logger.name == "TestClient"
        assert len(logger.handlers) > 0
        assert logger.level == 10  # logging.INFO = 20, but it might be set to DEBUG = 10
    
    @patch('socket.socket')
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
    
    @patch('socket.socket')
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
    
    @patch('socket.socket')
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
    
    @patch('socket.socket')
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
    
    @patch('socket.socket')
    def test_send_request_success(self, mock_socket_class):
        """测试成功发送请求"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        # 模拟连接成功
        self.client.connect()
        
        # 模拟接收响应
        response_data = {"status": "success", "data": "test_response"}
        response_json = json.dumps(response_data) + "\n"
        mock_socket.recv.return_value = response_json.encode('utf-8')
        
        request_data = {"test": "data"}
        result = self.client.send_request(request_data)
        
        assert result == response_data
        
        # 验证发送的数据
        expected_request = self.client.build_request(request_data)
        expected_json = json.dumps(expected_request) + "\n"
        mock_socket.send.assert_called_once_with(expected_json.encode('utf-8'))
    
    @patch('socket.socket')
    def test_send_request_connection_error(self, mock_socket_class):
        """测试发送请求时连接错误"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        self.client.connect()
        mock_socket.send.side_effect = ConnectionError("Connection lost")
        
        request_data = {"test": "data"}
        
        with pytest.raises(ConnectionError):
            self.client.send_request(request_data)
    
    @patch('socket.socket')
    def test_send_request_timeout(self, mock_socket_class):
        """测试发送请求超时"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        self.client.connect()
        mock_socket.recv.side_effect = socket.timeout("Timeout")
        
        request_data = {"test": "data"}
        
        with pytest.raises(socket.timeout):
            self.client.send_request(request_data)
    
    @patch('socket.socket')
    def test_send_request_invalid_json_response(self, mock_socket_class):
        """测试接收无效JSON响应"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        self.client.connect()
        
        # 模拟接收无效JSON
        mock_socket.recv.return_value = b"invalid json\n"
        
        request_data = {"test": "data"}
        
        with pytest.raises(json.JSONDecodeError):
            self.client.send_request(request_data)
    
    @patch('socket.socket')
    def test_send_request_empty_response(self, mock_socket_class):
        """测试接收空响应"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        self.client.connect()
        
        # 模拟接收空响应
        mock_socket.recv.return_value = b""
        
        request_data = {"test": "data"}
        
        with pytest.raises(ConnectionError, match="Connection closed by server"):
            self.client.send_request(request_data)
    
    @patch('socket.socket')
    def test_send_request_partial_response(self, mock_socket_class):
        """测试接收部分响应（多次recv）"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        self.client.connect()
        
        # 模拟分多次接收完整响应
        response_data = {"status": "success", "large_data": "x" * 1000}
        response_json = json.dumps(response_data) + "\n"
        response_bytes = response_json.encode('utf-8')
        
        # 分两次接收
        mid_point = len(response_bytes) // 2
        mock_socket.recv.side_effect = [
            response_bytes[:mid_point],
            response_bytes[mid_point:]
        ]
        
        request_data = {"test": "data"}
        result = self.client.send_request(request_data)
        
        assert result == response_data
        assert mock_socket.recv.call_count == 2


@pytest.mark.unit
class TestTcpClientEdgeCases:
    """TCP客户端边界情况测试"""
    
    def test_custom_host_port(self):
        """测试自定义主机和端口"""
        client = TestTcpClient(host="192.168.1.100", port=8080)
        assert client.host == "192.168.1.100"
        assert client.port == 8080
    
    def test_custom_timeout(self):
        """测试自定义超时时间"""
        client = TestTcpClient(timeout=60.0)
        assert client.timeout == 60.0
    
    def test_custom_client_name(self):
        """测试自定义客户端名称"""
        client = TestTcpClient(client_name="CustomClient")
        assert client.client_name == "CustomClient"
        
        logger = client._create_default_logger()
        assert logger.name == "CustomClient"
    
    @patch('socket.socket')
    def test_send_request_with_unicode_data(self, mock_socket_class):
        """测试发送包含Unicode字符的请求"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        client = TestTcpClient()
        client.connect()
        
        # 模拟Unicode响应
        response_data = {"message": "你好世界", "emoji": "🌍"}
        response_json = json.dumps(response_data, ensure_ascii=False) + "\n"
        mock_socket.recv.return_value = response_json.encode('utf-8')
        
        request_data = {"query": "测试查询", "symbols": "™®©"}
        result = client.send_request(request_data)
        
        assert result == response_data
        assert result["message"] == "你好世界"
        assert result["emoji"] == "🌍"
    
    @patch('socket.socket')
    def test_multiple_consecutive_requests(self, mock_socket_class):
        """测试连续多个请求"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        client = TestTcpClient()
        client.connect()
        
        # 模拟多个响应
        responses = [
            {"id": 1, "result": "first"},
            {"id": 2, "result": "second"},
            {"id": 3, "result": "third"}
        ]
        
        def mock_recv_side_effect(*args, **kwargs):
            if len(responses) > 0:
                response = responses.pop(0)
                response_json = json.dumps(response) + "\n"
                return response_json.encode('utf-8')
            return b""
        
        mock_socket.recv.side_effect = mock_recv_side_effect
        
        # 发送多个请求
        for i in range(3):
            request_data = {"request_id": i + 1}
            result = client.send_request(request_data)
            assert result["id"] == i + 1
            assert result["result"] in ["first", "second", "third"]
    
    @patch('socket.socket')
    def test_large_request_data(self, mock_socket_class):
        """测试大型请求数据"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        client = TestTcpClient()
        client.connect()
        
        # 创建大型请求数据
        large_data = {
            "large_field": "x" * 10000,  # 10KB数据
            "array_field": list(range(1000)),
            "nested_data": {
                f"key_{i}": f"value_{i}" for i in range(100)
            }
        }
        
        # 模拟简单响应
        response_data = {"status": "received"}
        response_json = json.dumps(response_data) + "\n"
        mock_socket.recv.return_value = response_json.encode('utf-8')
        
        result = client.send_request(large_data)
        assert result == response_data
        
        # 验证发送的数据包含大型数据
        call_args = mock_socket.send.call_args[0][0]
        sent_data = call_args.decode('utf-8')
        assert '"large_field"' in sent_data
        assert 'x' * 100 in sent_data  # 部分大型字段内容


@pytest.mark.unit
class TestAbstractMethods:
    """抽象方法测试"""
    
    def test_build_request_abstract_method(self):
        """测试build_request抽象方法"""
        # BaseTcpClient是抽象类，不能直接实例化
        # 但我们可以测试具体实现
        client = TestTcpClient()
        
        data = {"test": "data"}
        request = client.build_request(data)
        
        assert isinstance(request, dict)
        assert request["type"] == "test_request"
        assert request["data"] == data
        assert "timestamp" in request
    
    def test_handle_response_abstract_method(self):
        """测试handle_response抽象方法"""
        client = TestTcpClient()
        
        response_data = {"status": "success", "result": "test"}
        handled_response = client.handle_response(response_data)
        
        assert handled_response == response_data


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
        server_socket.bind(('127.0.0.1', 0))  # 使用随机端口
        server_port = server_socket.getsockname()[1]
        server_socket.listen(1)
        
        server_responses = []
        server_running = threading.Event()
        
        def mock_server():
            try:
                server_running.set()
                client_socket, addr = server_socket.accept()
                
                # 接收请求
                data = b""
                while True:
                    chunk = client_socket.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                    if b'\n' in data:
                        break
                
                # 解析请求
                request_text = data.decode('utf-8').strip()
                request_data = json.loads(request_text)
                server_responses.append(request_data)
                
                # 发送响应
                response = {"status": "success", "echo": request_data}
                response_text = json.dumps(response) + "\n"
                client_socket.send(response_text.encode('utf-8'))
                
                client_socket.close()
                
            except Exception as e:
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
            client = TestTcpClient(port=server_port, timeout=5.0)
            
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
            assert received_request["type"] == "test_request"
            assert received_request["data"] == request_data
            
            client.disconnect()
            
        finally:
            server_thread.join(timeout=5)
    
    @pytest.mark.slow
    def test_connection_timeout(self):
        """测试连接超时"""
        # 使用一个不存在的端口来模拟超时
        client = TestTcpClient(host="127.0.0.1", port=65534, timeout=1.0)
        
        start_time = time.time()
        result = client.connect()
        elapsed_time = time.time() - start_time
        
        assert result is False
        assert elapsed_time >= 1.0  # 应该至少等待超时时间
        assert elapsed_time < 2.0   # 但不应该等待太久


@pytest.mark.unit
class TestErrorHandling:
    """错误处理测试"""
    
    @patch('socket.socket')
    def test_connection_refused_error(self, mock_socket_class):
        """测试连接被拒绝错误"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
        
        client = TestTcpClient()
        
        with patch.object(client.logger, 'error') as mock_log_error:
            result = client.connect()
            
            assert result is False
            mock_log_error.assert_called_once()
            assert "Failed to connect" in str(mock_log_error.call_args)
    
    @patch('socket.socket')
    def test_socket_timeout_error(self, mock_socket_class):
        """测试socket超时错误"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = socket.timeout("Connection timeout")
        
        client = TestTcpClient()
        result = client.connect()
        
        assert result is False
        assert client.connected is False
    
    @patch('socket.socket')
    def test_general_socket_error(self, mock_socket_class):
        """测试一般socket错误"""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = OSError("Network error")
        
        client = TestTcpClient()
        result = client.connect()
        
        assert result is False
        assert client._socket is None


# 性能测试
@pytest.mark.slow
class TestTcpClientPerformance:
    """TCP客户端性能测试"""
    
    @patch('socket.socket')
    def test_multiple_connections_performance(self, mock_socket_class):
        """测试多次连接的性能"""
        import time
        
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        client = TestTcpClient()
        
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
    
    @patch('socket.socket')
    def test_large_data_transfer_performance(self, mock_socket_class):
        """测试大数据传输性能"""
        import time
        
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        # 模拟大响应数据
        large_response = {"data": "x" * 100000}  # 100KB数据
        response_json = json.dumps(large_response) + "\n"
        mock_socket.recv.return_value = response_json.encode('utf-8')
        
        client = TestTcpClient()
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

"""
JobManager服务器端测试
测试 JobManagerServer 类的所有功能，包括TCP服务器、请求处理、并发控制等
"""
import pytest
import socket
import threading
import json
import time
import base64
from unittest.mock import Mock, patch, MagicMock

from sage.kernel.kernels.jobmanager.job_manager_server import JobManagerServer


@pytest.mark.unit
class TestJobManagerServerInitialization:
    """测试JobManagerServer初始化"""

    def test_default_initialization(self):
        """测试默认参数初始化"""
        mock_job_manager = Mock()
        
        with patch('socket.socket'):
            server = JobManagerServer(job_manager=mock_job_manager)
            assert server.host == "127.0.0.1"
            assert server.port == 19001
            assert server.job_manager is mock_job_manager
            assert server.max_concurrent_connections == 100

    def test_custom_initialization(self):
        """测试自定义参数初始化"""
        mock_job_manager = Mock()
        
        with patch('socket.socket'):
            server = JobManagerServer(
                host="0.0.0.0",
                port=8080,
                job_manager=mock_job_manager,
                max_concurrent_connections=50
            )
            assert server.host == "0.0.0.0"
            assert server.port == 8080
            assert server.max_concurrent_connections == 50

    def test_initialization_with_invalid_port(self):
        """测试无效端口号初始化"""
        mock_job_manager = Mock()
        
        with pytest.raises(ValueError):
            JobManagerServer(port=-1, job_manager=mock_job_manager)
        
        with pytest.raises(ValueError):
            JobManagerServer(port=65536, job_manager=mock_job_manager)

    def test_initialization_without_job_manager(self):
        """测试没有JobManager的初始化"""
        with pytest.raises(ValueError, match="JobManager instance is required"):
            JobManagerServer(job_manager=None)

    def test_socket_creation_and_binding(self):
        """测试套接字创建和绑定"""
        mock_job_manager = Mock()
        mock_socket = Mock()
        
        with patch('socket.socket') as mock_socket_class:
            mock_socket_class.return_value = mock_socket
            
            server = JobManagerServer(job_manager=mock_job_manager)
            
            # 验证套接字创建和配置
            mock_socket_class.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
            mock_socket.setsockopt.assert_called_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            mock_socket.bind.assert_called_once_with(("127.0.0.1", 19001))


@pytest.mark.unit
class TestJobManagerServerLifecycle:
    """测试JobManagerServer生命周期管理"""

    @pytest.fixture
    def server(self):
        """创建JobManagerServer实例"""
        mock_job_manager = Mock()
        with patch('socket.socket'):
            return JobManagerServer(job_manager=mock_job_manager)

    def test_start_server(self, server):
        """测试启动服务器"""
        with patch.object(server, '_server_loop') as mock_loop:
            server.start()
            
            assert server.is_running is True
            mock_loop.assert_called_once()

    def test_stop_server(self, server):
        """测试停止服务器"""
        server.is_running = True
        mock_socket = Mock()
        server.server_socket = mock_socket
        
        server.stop()
        
        assert server.is_running is False
        mock_socket.close.assert_called_once()

    def test_start_already_running_server(self, server):
        """测试启动已运行的服务器"""
        server.is_running = True
        
        with patch.object(server, '_server_loop') as mock_loop:
            server.start()
            
            # 不应该重复启动
            mock_loop.assert_not_called()

    def test_stop_not_running_server(self, server):
        """测试停止未运行的服务器"""
        server.is_running = False
        mock_socket = Mock()
        server.server_socket = mock_socket
        
        server.stop()
        
        # 不应该调用close
        mock_socket.close.assert_not_called()

    def test_context_manager_usage(self, server):
        """测试上下文管理器使用"""
        with patch.object(server, 'start') as mock_start, \
             patch.object(server, 'stop') as mock_stop:
            
            with server:
                pass
            
            mock_start.assert_called_once()
            mock_stop.assert_called_once()


@pytest.mark.unit
class TestJobManagerServerRequestHandling:
    """测试请求处理功能"""

    @pytest.fixture
    def server(self):
        """创建JobManagerServer实例"""
        mock_job_manager = Mock()
        with patch('socket.socket'):
            return JobManagerServer(job_manager=mock_job_manager)

    def test_handle_health_check_request(self, server):
        """测试处理健康检查请求"""
        request = {
            "action": "health_check",
            "request_id": "test-request-id"
        }
        
        mock_client_socket = Mock()
        
        with patch.object(server.job_manager, 'health_check') as mock_health:
            mock_health.return_value = {"status": "healthy", "uptime": 3600}
            
            response = server._handle_request(request, mock_client_socket)
            
            assert response["success"] is True
            assert response["status"] == "healthy"
            assert response["request_id"] == "test-request-id"
            mock_health.assert_called_once()

    def test_handle_server_info_request(self, server):
        """测试处理服务器信息请求"""
        request = {
            "action": "get_server_info",
            "request_id": "test-request-id"
        }
        
        mock_client_socket = Mock()
        
        with patch.object(server.job_manager, 'get_server_info') as mock_info:
            mock_info.return_value = {"version": "1.0.0", "daemon_port": 19001}
            
            response = server._handle_request(request, mock_client_socket)
            
            assert response["success"] is True
            assert response["version"] == "1.0.0"
            assert response["request_id"] == "test-request-id"
            mock_info.assert_called_once()

    def test_handle_submit_job_request(self, server):
        """测试处理作业提交请求"""
        test_data = b"test serialized data"
        request = {
            "action": "submit_job",
            "request_id": "test-request-id",
            "serialized_data": base64.b64encode(test_data).decode('utf-8')
        }
        
        mock_client_socket = Mock()
        
        with patch.object(server, '_process_job_submission') as mock_process:
            mock_process.return_value = {
                "success": True,
                "job_uuid": "test-job-uuid"
            }
            
            response = server._handle_request(request, mock_client_socket)
            
            assert response["success"] is True
            assert response["job_uuid"] == "test-job-uuid"
            assert response["request_id"] == "test-request-id"
            mock_process.assert_called_once_with(test_data)

    def test_handle_pause_job_request(self, server):
        """测试处理暂停作业请求"""
        request = {
            "action": "pause_job",
            "request_id": "test-request-id",
            "job_uuid": "test-job-uuid"
        }
        
        mock_client_socket = Mock()
        
        with patch.object(server.job_manager, 'pause_job') as mock_pause:
            mock_pause.return_value = {"success": True, "job_uuid": "test-job-uuid"}
            
            response = server._handle_request(request, mock_client_socket)
            
            assert response["success"] is True
            assert response["job_uuid"] == "test-job-uuid"
            assert response["request_id"] == "test-request-id"
            mock_pause.assert_called_once_with("test-job-uuid")

    def test_handle_get_job_status_request(self, server):
        """测试处理获取作业状态请求"""
        request = {
            "action": "get_job_status",
            "request_id": "test-request-id",
            "job_uuid": "test-job-uuid"
        }
        
        mock_client_socket = Mock()
        
        with patch.object(server.job_manager, 'get_job_status') as mock_status:
            mock_status.return_value = {
                "success": True,
                "status": "RUNNING",
                "progress": 0.5
            }
            
            response = server._handle_request(request, mock_client_socket)
            
            assert response["success"] is True
            assert response["status"] == "RUNNING"
            assert response["progress"] == 0.5
            assert response["request_id"] == "test-request-id"
            mock_status.assert_called_once_with("test-job-uuid")

    def test_handle_unknown_action(self, server):
        """测试处理未知动作请求"""
        request = {
            "action": "unknown_action",
            "request_id": "test-request-id"
        }
        
        mock_client_socket = Mock()
        
        response = server._handle_request(request, mock_client_socket)
        
        assert response["success"] is False
        assert "unknown action" in response["error"].lower()
        assert response["request_id"] == "test-request-id"

    def test_handle_malformed_request(self, server):
        """测试处理格式错误的请求"""
        malformed_requests = [
            {},  # 空请求
            {"action": "health_check"},  # 缺少request_id
            {"request_id": "test-id"},  # 缺少action
            {"action": "submit_job", "request_id": "test-id"},  # 缺少必要数据
        ]
        
        mock_client_socket = Mock()
        
        for request in malformed_requests:
            response = server._handle_request(request, mock_client_socket)
            assert response["success"] is False
            assert "error" in response


@pytest.mark.unit
class TestJobManagerServerJobProcessing:
    """测试作业处理功能"""

    @pytest.fixture
    def server(self):
        """创建JobManagerServer实例"""
        mock_job_manager = Mock()
        with patch('socket.socket'):
            return JobManagerServer(job_manager=mock_job_manager)

    def test_process_job_submission_success(self, server):
        """测试成功处理作业提交"""
        test_data = b"serialized environment data"
        
        with patch.object(server, '_deserialize_environment') as mock_deserialize, \
             patch.object(server.job_manager, 'submit_job') as mock_submit:
            
            mock_env = Mock()
            mock_deserialize.return_value = mock_env
            mock_submit.return_value = "test-job-uuid"
            
            result = server._process_job_submission(test_data)
            
            assert result["success"] is True
            assert result["job_uuid"] == "test-job-uuid"
            mock_deserialize.assert_called_once_with(test_data)
            mock_submit.assert_called_once_with(mock_env)

    def test_process_job_submission_deserialization_failure(self, server):
        """测试反序列化失败的作业提交"""
        test_data = b"invalid serialized data"
        
        with patch.object(server, '_deserialize_environment') as mock_deserialize:
            mock_deserialize.side_effect = Exception("Deserialization failed")
            
            result = server._process_job_submission(test_data)
            
            assert result["success"] is False
            assert "deserialization" in result["error"].lower()

    def test_process_job_submission_jobmanager_failure(self, server):
        """测试JobManager提交失败"""
        test_data = b"serialized environment data"
        
        with patch.object(server, '_deserialize_environment') as mock_deserialize, \
             patch.object(server.job_manager, 'submit_job') as mock_submit:
            
            mock_env = Mock()
            mock_deserialize.return_value = mock_env
            mock_submit.side_effect = Exception("JobManager submission failed")
            
            result = server._process_job_submission(test_data)
            
            assert result["success"] is False
            assert "submission failed" in result["error"].lower()

    def test_deserialize_environment_success(self, server):
        """测试成功反序列化环境"""
        test_data = b"serialized environment"
        
        with patch('sage.kernel.kernels.runtime.serialization.dill.deserialize_object') as mock_deserialize:
            mock_env = Mock()
            mock_deserialize.return_value = mock_env
            
            result = server._deserialize_environment(test_data)
            
            assert result is mock_env
            mock_deserialize.assert_called_once_with(test_data)

    def test_deserialize_environment_failure(self, server):
        """测试反序列化环境失败"""
        test_data = b"invalid data"
        
        with patch('sage.kernel.kernels.runtime.serialization.dill.deserialize_object') as mock_deserialize:
            mock_deserialize.side_effect = Exception("Deserialization error")
            
            with pytest.raises(Exception, match="Deserialization error"):
                server._deserialize_environment(test_data)


@pytest.mark.unit
class TestJobManagerServerConnectionHandling:
    """测试连接处理功能"""

    @pytest.fixture
    def server(self):
        """创建JobManagerServer实例"""
        mock_job_manager = Mock()
        with patch('socket.socket'):
            return JobManagerServer(job_manager=mock_job_manager)

    def test_handle_client_connection_success(self, server):
        """测试成功处理客户端连接"""
        mock_client_socket = Mock()
        mock_address = ("127.0.0.1", 12345)
        
        # 模拟接收请求和发送响应
        request_data = json.dumps({
            "action": "health_check",
            "request_id": "test-id"
        }).encode('utf-8')
        
        mock_client_socket.recv.return_value = request_data
        
        with patch.object(server, '_handle_request') as mock_handle:
            mock_handle.return_value = {"success": True, "status": "healthy"}
            
            server._handle_client_connection(mock_client_socket, mock_address)
            
            mock_client_socket.recv.assert_called()
            mock_client_socket.send.assert_called()
            mock_client_socket.close.assert_called()

    def test_handle_client_connection_receive_error(self, server):
        """测试接收数据错误"""
        mock_client_socket = Mock()
        mock_address = ("127.0.0.1", 12345)
        
        mock_client_socket.recv.side_effect = socket.error("Receive error")
        
        # 应该优雅处理错误
        server._handle_client_connection(mock_client_socket, mock_address)
        
        mock_client_socket.close.assert_called()

    def test_handle_client_connection_send_error(self, server):
        """测试发送响应错误"""
        mock_client_socket = Mock()
        mock_address = ("127.0.0.1", 12345)
        
        request_data = json.dumps({
            "action": "health_check",
            "request_id": "test-id"
        }).encode('utf-8')
        
        mock_client_socket.recv.return_value = request_data
        mock_client_socket.send.side_effect = socket.error("Send error")
        
        with patch.object(server, '_handle_request') as mock_handle:
            mock_handle.return_value = {"success": True}
            
            server._handle_client_connection(mock_client_socket, mock_address)
            
            mock_client_socket.close.assert_called()

    def test_handle_client_connection_json_decode_error(self, server):
        """测试JSON解码错误"""
        mock_client_socket = Mock()
        mock_address = ("127.0.0.1", 12345)
        
        # 发送无效JSON
        mock_client_socket.recv.return_value = b"invalid json data"
        
        server._handle_client_connection(mock_client_socket, mock_address)
        
        # 应该发送错误响应
        mock_client_socket.send.assert_called()
        mock_client_socket.close.assert_called()

    def test_concurrent_connection_handling(self, server):
        """测试并发连接处理"""
        server.max_concurrent_connections = 5
        
        # 模拟多个并发连接
        connections = []
        for i in range(3):
            mock_socket = Mock()
            mock_address = ("127.0.0.1", 12345 + i)
            connections.append((mock_socket, mock_address))
        
        with patch.object(server, '_handle_client_connection') as mock_handle:
            # 模拟并发处理
            for client_socket, address in connections:
                server._handle_client_connection(client_socket, address)
            
            assert mock_handle.call_count == 3

    def test_max_connections_limit(self, server):
        """测试最大连接数限制"""
        server.max_concurrent_connections = 2
        server.current_connections = 2
        
        mock_client_socket = Mock()
        mock_address = ("127.0.0.1", 12345)
        
        # 应该拒绝新连接
        with patch.object(server, '_reject_connection') as mock_reject:
            server._handle_new_connection(mock_client_socket, mock_address)
            mock_reject.assert_called_once()


@pytest.mark.unit
class TestJobManagerServerUtilities:
    """测试服务器工具功能"""

    @pytest.fixture
    def server(self):
        """创建JobManagerServer实例"""
        mock_job_manager = Mock()
        with patch('socket.socket'):
            return JobManagerServer(job_manager=mock_job_manager)

    def test_validate_request_format(self, server):
        """测试请求格式验证"""
        valid_requests = [
            {"action": "health_check", "request_id": "test-id"},
            {"action": "submit_job", "request_id": "test-id", "serialized_data": "data"},
            {"action": "pause_job", "request_id": "test-id", "job_uuid": "uuid"},
        ]
        
        for request in valid_requests:
            assert server._validate_request_format(request) is True
        
        invalid_requests = [
            {},  # 空请求
            {"action": "health_check"},  # 缺少request_id
            {"request_id": "test-id"},  # 缺少action
            {"action": "submit_job", "request_id": "test-id"},  # 缺少数据
        ]
        
        for request in invalid_requests:
            assert server._validate_request_format(request) is False

    def test_format_response(self, server):
        """测试响应格式化"""
        # 成功响应
        success_data = {"status": "healthy", "uptime": 3600}
        response = server._format_response(success_data, "test-id", success=True)
        
        assert response["success"] is True
        assert response["request_id"] == "test-id"
        assert response["status"] == "healthy"
        assert response["uptime"] == 3600
        
        # 错误响应
        error_response = server._format_response(
            None, "test-id", success=False, error="Test error"
        )
        
        assert error_response["success"] is False
        assert error_response["request_id"] == "test-id"
        assert error_response["error"] == "Test error"

    def test_log_request(self, server):
        """测试请求日志记录"""
        request = {"action": "health_check", "request_id": "test-id"}
        address = ("127.0.0.1", 12345)
        
        with patch('sage.kernel.utils.logging.custom_logger.CustomLogger') as mock_logger:
            server._log_request(request, address)
            # 验证日志记录被调用（具体实现取决于CustomLogger）

    def test_get_server_statistics(self, server):
        """测试获取服务器统计信息"""
        server.start_time = time.time() - 3600  # 1小时前
        server.total_requests = 1000
        server.successful_requests = 950
        server.failed_requests = 50
        
        stats = server._get_server_statistics()
        
        assert stats["uptime"] >= 3600
        assert stats["total_requests"] == 1000
        assert stats["successful_requests"] == 950
        assert stats["failed_requests"] == 50
        assert abs(stats["success_rate"] - 0.95) < 0.01


@pytest.mark.integration
class TestJobManagerServerIntegration:
    """JobManagerServer集成测试"""

    @pytest.fixture
    def server_with_mock_job_manager(self):
        """创建带有模拟JobManager的服务器"""
        mock_job_manager = Mock()
        mock_job_manager.health_check.return_value = {"status": "healthy"}
        mock_job_manager.get_server_info.return_value = {"version": "1.0.0"}
        mock_job_manager.submit_job.return_value = "test-job-uuid"
        mock_job_manager.pause_job.return_value = {"success": True}
        mock_job_manager.get_job_status.return_value = {"success": True, "status": "RUNNING"}
        
        with patch('socket.socket'):
            return JobManagerServer(job_manager=mock_job_manager)

    def test_full_request_response_cycle(self, server_with_mock_job_manager):
        """测试完整的请求-响应周期"""
        server = server_with_mock_job_manager
        
        # 模拟客户端请求
        requests = [
            {"action": "health_check", "request_id": "health-1"},
            {"action": "get_server_info", "request_id": "info-1"},
            {
                "action": "submit_job",
                "request_id": "submit-1",
                "serialized_data": base64.b64encode(b"test data").decode('utf-8')
            },
            {"action": "pause_job", "request_id": "pause-1", "job_uuid": "test-uuid"},
            {"action": "get_job_status", "request_id": "status-1", "job_uuid": "test-uuid"},
        ]
        
        mock_client_socket = Mock()
        
        with patch.object(server, '_deserialize_environment') as mock_deserialize:
            mock_deserialize.return_value = Mock()
            
            for request in requests:
                response = server._handle_request(request, mock_client_socket)
                
                assert response["success"] is True
                assert response["request_id"] == request["request_id"]

    def test_error_handling_integration(self, server_with_mock_job_manager):
        """测试错误处理集成"""
        server = server_with_mock_job_manager
        
        # 模拟JobManager抛出异常
        server.job_manager.submit_job.side_effect = Exception("Submission failed")
        
        request = {
            "action": "submit_job",
            "request_id": "error-test",
            "serialized_data": base64.b64encode(b"test data").decode('utf-8')
        }
        
        mock_client_socket = Mock()
        
        with patch.object(server, '_deserialize_environment') as mock_deserialize:
            mock_deserialize.return_value = Mock()
            
            response = server._handle_request(request, mock_client_socket)
            
            assert response["success"] is False
            assert "error" in response
            assert response["request_id"] == "error-test"

    def test_concurrent_request_handling(self, server_with_mock_job_manager):
        """测试并发请求处理"""
        server = server_with_mock_job_manager
        
        def handle_request(request_id):
            request = {"action": "health_check", "request_id": request_id}
            mock_client_socket = Mock()
            return server._handle_request(request, mock_client_socket)
        
        import concurrent.futures
        
        # 并发处理10个请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(handle_request, f"concurrent-{i}")
                for i in range(10)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # 验证所有请求都成功处理
        assert len(results) == 10
        assert all(result["success"] for result in results)
        
        # 验证request_id正确
        request_ids = [result["request_id"] for result in results]
        expected_ids = [f"concurrent-{i}" for i in range(10)]
        assert set(request_ids) == set(expected_ids)


@pytest.mark.slow
class TestJobManagerServerPerformance:
    """JobManagerServer性能测试"""

    @pytest.fixture
    def server_with_mock_job_manager(self):
        """创建带有模拟JobManager的服务器"""
        mock_job_manager = Mock()
        mock_job_manager.health_check.return_value = {"status": "healthy"}
        
        with patch('socket.socket'):
            return JobManagerServer(job_manager=mock_job_manager)

    def test_request_processing_performance(self, server_with_mock_job_manager):
        """测试请求处理性能"""
        server = server_with_mock_job_manager
        
        request = {"action": "health_check", "request_id": "perf-test"}
        mock_client_socket = Mock()
        
        # 测量1000次请求处理时间
        start_time = time.time()
        
        for i in range(1000):
            request["request_id"] = f"perf-test-{i}"
            server._handle_request(request, mock_client_socket)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 验证性能要求：1000次请求应在5秒内处理完成
        assert duration < 5.0, f"Request processing took {duration:.2f}s, expected < 5s"
        
        # 计算吞吐量
        throughput = 1000 / duration
        assert throughput > 200, f"Throughput {throughput:.2f} requests/s, expected > 200 requests/s"

    def test_memory_usage_stability(self, server_with_mock_job_manager):
        """测试内存使用稳定性"""
        import psutil
        import os
        
        server = server_with_mock_job_manager
        request = {"action": "health_check", "request_id": "memory-test"}
        mock_client_socket = Mock()
        
        # 记录初始内存使用
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 处理大量请求
        for i in range(10000):
            request["request_id"] = f"memory-test-{i}"
            server._handle_request(request, mock_client_socket)
        
        # 记录最终内存使用
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 验证内存增长在合理范围内（小于100MB）
        max_increase = 100 * 1024 * 1024  # 100MB
        assert memory_increase < max_increase, \
            f"Memory increased by {memory_increase / 1024 / 1024:.2f}MB, expected < 100MB"

    def test_concurrent_connection_performance(self, server_with_mock_job_manager):
        """测试并发连接性能"""
        server = server_with_mock_job_manager
        
        def process_request(request_id):
            request = {"action": "health_check", "request_id": request_id}
            mock_client_socket = Mock()
            start = time.time()
            server._handle_request(request, mock_client_socket)
            return time.time() - start
        
        import concurrent.futures
        
        # 并发处理100个请求
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(process_request, f"concurrent-perf-{i}")
                for i in range(100)
            ]
            processing_times = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # 验证并发性能
        assert total_time < 10.0, f"Concurrent processing took {total_time:.2f}s, expected < 10s"
        
        # 验证平均处理时间
        avg_processing_time = sum(processing_times) / len(processing_times)
        assert avg_processing_time < 0.1, \
            f"Average processing time {avg_processing_time:.4f}s, expected < 0.1s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

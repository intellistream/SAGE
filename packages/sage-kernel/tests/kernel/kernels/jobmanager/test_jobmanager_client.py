"""
JobManager客户端测试
测试 JobManagerClient 类的所有功能，包括连接管理、请求发送、响应处理等
"""
import pytest
import socket
import json
import base64
import uuid
import time
from unittest.mock import Mock, patch, MagicMock

from sage.kernel.kernels.jobmanager.jobmanager_client import JobManagerClient


@pytest.mark.unit
class TestJobManagerClientInitialization:
    """测试JobManagerClient初始化"""

    def test_default_initialization(self):
        """测试默认参数初始化"""
        client = JobManagerClient()
        assert client.host == "127.0.0.1"
        assert client.port == 19001
        assert client.timeout == 30.0
        assert client.client_name == "JobManagerClient"

    def test_custom_initialization(self):
        """测试自定义参数初始化"""
        client = JobManagerClient(
            host="192.168.1.100",
            port=8080,
            timeout=60.0
        )
        assert client.host == "192.168.1.100"
        assert client.port == 8080
        assert client.timeout == 60.0

    def test_initialization_with_invalid_port(self):
        """测试无效端口号"""
        # 测试端口范围
        with pytest.raises(ValueError):
            JobManagerClient(port=-1)
        
        with pytest.raises(ValueError):
            JobManagerClient(port=65536)

    def test_initialization_with_invalid_timeout(self):
        """测试无效超时时间"""
        with pytest.raises(ValueError):
            JobManagerClient(timeout=-1)
        
        with pytest.raises(ValueError):
            JobManagerClient(timeout=0)


@pytest.mark.unit
class TestJobManagerClientRequestBuilding:
    """测试请求构建功能"""

    @pytest.fixture
    def client(self):
        """创建JobManagerClient实例"""
        return JobManagerClient()

    def test_build_health_check_request(self, client):
        """测试构建健康检查请求"""
        request = client._build_health_check_request()
        
        assert request["action"] == "health_check"
        assert "request_id" in request
        assert uuid.UUID(request["request_id"])  # 验证是有效的UUID

    def test_build_server_info_request(self, client):
        """测试构建服务器信息请求"""
        request = client._build_server_info_request()
        
        assert request["action"] == "get_server_info"
        assert "request_id" in request
        assert uuid.UUID(request["request_id"])

    def test_build_submit_job_request(self, client):
        """测试构建作业提交请求"""
        test_data = b"test serialized data"
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = {"success": True, "job_uuid": "test-uuid"}
            
            result = client.submit_job(test_data)
            
            # 验证调用参数
            call_args = mock_send.call_args[0][0]
            assert call_args["action"] == "submit_job"
            assert "request_id" in call_args
            assert call_args["serialized_data"] == base64.b64encode(test_data).decode('utf-8')

    def test_build_pause_job_request(self, client):
        """测试构建暂停作业请求"""
        job_uuid = "test-job-uuid"
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = {"success": True}
            
            result = client.pause_job(job_uuid)
            
            call_args = mock_send.call_args[0][0]
            assert call_args["action"] == "pause_job"
            assert call_args["job_uuid"] == job_uuid
            assert "request_id" in call_args

    def test_build_get_job_status_request(self, client):
        """测试构建获取作业状态请求"""
        job_uuid = "test-job-uuid"
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = {"success": True, "status": "RUNNING"}
            
            result = client.get_job_status(job_uuid)
            
            call_args = mock_send.call_args[0][0]
            assert call_args["action"] == "get_job_status"
            assert call_args["job_uuid"] == job_uuid
            assert "request_id" in call_args


@pytest.mark.unit
class TestJobManagerClientJobOperations:
    """测试作业操作功能"""

    @pytest.fixture
    def client(self):
        """创建JobManagerClient实例"""
        return JobManagerClient()

    def test_submit_job_success(self, client):
        """测试成功提交作业"""
        test_data = b"test job data"
        expected_response = {
            "success": True,
            "job_uuid": "test-uuid-123",
            "message": "Job submitted successfully"
        }
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = expected_response
            
            result = client.submit_job(test_data)
            
            assert result == expected_response
            mock_send.assert_called_once()

    def test_submit_job_with_empty_data(self, client):
        """测试提交空数据"""
        with pytest.raises(ValueError, match="Serialized data cannot be empty"):
            client.submit_job(b"")

    def test_submit_job_with_none_data(self, client):
        """测试提交None数据"""
        with pytest.raises(ValueError, match="Serialized data cannot be None"):
            client.submit_job(None)

    def test_submit_job_server_error(self, client):
        """测试服务器错误响应"""
        test_data = b"test data"
        error_response = {
            "success": False,
            "error": "Server internal error",
            "message": "Failed to process job submission"
        }
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = error_response
            
            result = client.submit_job(test_data)
            
            assert result == error_response
            assert result["success"] is False

    def test_pause_job_success(self, client):
        """测试成功暂停作业"""
        job_uuid = "test-job-uuid"
        expected_response = {
            "success": True,
            "job_uuid": job_uuid,
            "message": "Job paused successfully"
        }
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = expected_response
            
            result = client.pause_job(job_uuid)
            
            assert result == expected_response

    def test_pause_job_invalid_uuid(self, client):
        """测试暂停无效UUID的作业"""
        with pytest.raises(ValueError, match="Job UUID cannot be empty"):
            client.pause_job("")
        
        with pytest.raises(ValueError, match="Job UUID cannot be None"):
            client.pause_job(None)

    def test_get_job_status_success(self, client):
        """测试成功获取作业状态"""
        job_uuid = "test-job-uuid"
        expected_response = {
            "success": True,
            "job_uuid": job_uuid,
            "status": "RUNNING",
            "progress": 0.75,
            "start_time": "2023-01-01T10:00:00Z"
        }
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = expected_response
            
            result = client.get_job_status(job_uuid)
            
            assert result == expected_response
            assert result["status"] == "RUNNING"
            assert result["progress"] == 0.75

    def test_get_job_status_not_found(self, client):
        """测试获取不存在作业的状态"""
        job_uuid = "nonexistent-job"
        error_response = {
            "success": False,
            "error": "Job not found",
            "message": f"Job {job_uuid} does not exist"
        }
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = error_response
            
            result = client.get_job_status(job_uuid)
            
            assert result == error_response
            assert result["success"] is False


@pytest.mark.unit
class TestJobManagerClientHealthAndInfo:
    """测试健康检查和信息查询功能"""

    @pytest.fixture
    def client(self):
        """创建JobManagerClient实例"""
        return JobManagerClient()

    def test_health_check_success(self, client):
        """测试成功的健康检查"""
        expected_response = {
            "success": True,
            "status": "healthy",
            "uptime": 3600,
            "jobs_count": 5
        }
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = expected_response
            
            result = client.health_check()
            
            assert result == expected_response
            assert result["status"] == "healthy"

    def test_health_check_unhealthy(self, client):
        """测试不健康状态的响应"""
        unhealthy_response = {
            "success": False,
            "status": "unhealthy",
            "error": "High memory usage",
            "memory_usage": 0.95
        }
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = unhealthy_response
            
            result = client.health_check()
            
            assert result == unhealthy_response
            assert result["status"] == "unhealthy"

    def test_get_server_info_success(self, client):
        """测试成功获取服务器信息"""
        expected_response = {
            "success": True,
            "version": "1.0.0",
            "daemon_host": "127.0.0.1",
            "daemon_port": 19001,
            "enable_daemon": True,
            "start_time": "2023-01-01T09:00:00Z"
        }
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = expected_response
            
            result = client.get_server_info()
            
            assert result == expected_response
            assert result["version"] == "1.0.0"
            assert result["daemon_port"] == 19001


@pytest.mark.unit
class TestJobManagerClientConnectionHandling:
    """测试连接处理功能"""

    @pytest.fixture
    def client(self):
        """创建JobManagerClient实例"""
        return JobManagerClient()

    def test_connection_timeout(self, client):
        """测试连接超时处理"""
        with patch.object(client, '_create_socket') as mock_create_socket:
            mock_socket = Mock()
            mock_socket.connect.side_effect = socket.timeout("Connection timeout")
            mock_create_socket.return_value = mock_socket
            
            with pytest.raises(ConnectionError, match="Connection timeout"):
                client.submit_job(b"test data")

    def test_connection_refused(self, client):
        """测试连接被拒绝"""
        with patch.object(client, '_create_socket') as mock_create_socket:
            mock_socket = Mock()
            mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
            mock_create_socket.return_value = mock_socket
            
            with pytest.raises(ConnectionError, match="Connection refused"):
                client.submit_job(b"test data")

    def test_socket_error_handling(self, client):
        """测试套接字错误处理"""
        with patch.object(client, '_create_socket') as mock_create_socket:
            mock_socket = Mock()
            mock_socket.send.side_effect = socket.error("Socket error")
            mock_create_socket.return_value = mock_socket
            
            with pytest.raises(ConnectionError, match="Socket error"):
                client.submit_job(b"test data")

    def test_invalid_response_format(self, client):
        """测试无效响应格式处理"""
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = "invalid json response"
            
            with pytest.raises(ValueError, match="Invalid response format"):
                client.submit_job(b"test data")

    def test_network_interruption_retry(self, client):
        """测试网络中断重试机制"""
        with patch.object(client, 'send_request') as mock_send:
            # 第一次调用失败，第二次成功
            mock_send.side_effect = [
                ConnectionError("Network interrupted"),
                {"success": True, "job_uuid": "retry-uuid"}
            ]
            
            # 客户端应该实现重试机制
            with patch.object(client, '_retry_request') as mock_retry:
                mock_retry.return_value = {"success": True, "job_uuid": "retry-uuid"}
                
                result = client.submit_job(b"test data")
                
                assert result["success"] is True
                assert result["job_uuid"] == "retry-uuid"


@pytest.mark.integration
class TestJobManagerClientIntegration:
    """JobManagerClient集成测试"""

    @pytest.fixture
    def client(self):
        """创建JobManagerClient实例"""
        return JobManagerClient()

    def test_full_job_workflow_simulation(self, client):
        """测试完整的作业工作流程模拟"""
        job_uuid = "integration-test-uuid"
        
        # 模拟响应序列
        responses = [
            # 1. 提交作业
            {"success": True, "job_uuid": job_uuid},
            # 2. 查询状态 - 运行中
            {"success": True, "status": "RUNNING", "progress": 0.3},
            # 3. 查询状态 - 完成
            {"success": True, "status": "COMPLETED", "progress": 1.0},
            # 4. 暂停作业（已完成）
            {"success": False, "error": "Cannot pause completed job"}
        ]
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.side_effect = responses
            
            # 1. 提交作业
            submit_result = client.submit_job(b"integration test data")
            assert submit_result["success"] is True
            assert submit_result["job_uuid"] == job_uuid
            
            # 2. 查询运行状态
            status_result = client.get_job_status(job_uuid)
            assert status_result["status"] == "RUNNING"
            assert status_result["progress"] == 0.3
            
            # 3. 查询完成状态
            final_status = client.get_job_status(job_uuid)
            assert final_status["status"] == "COMPLETED"
            assert final_status["progress"] == 1.0
            
            # 4. 尝试暂停已完成的作业
            pause_result = client.pause_job(job_uuid)
            assert pause_result["success"] is False

    def test_batch_operations(self, client):
        """测试批量操作"""
        job_uuids = [f"batch-job-{i}" for i in range(5)]
        
        with patch.object(client, 'send_request') as mock_send:
            # 模拟批量提交响应
            submit_responses = [
                {"success": True, "job_uuid": uuid} for uuid in job_uuids
            ]
            # 模拟批量状态查询响应
            status_responses = [
                {"success": True, "status": "RUNNING", "job_uuid": uuid} 
                for uuid in job_uuids
            ]
            
            mock_send.side_effect = submit_responses + status_responses
            
            # 批量提交作业
            submitted_uuids = []
            for i in range(5):
                result = client.submit_job(f"batch job {i}".encode())
                assert result["success"] is True
                submitted_uuids.append(result["job_uuid"])
            
            assert submitted_uuids == job_uuids
            
            # 批量查询状态
            statuses = []
            for uuid in job_uuids:
                status = client.get_job_status(uuid)
                assert status["success"] is True
                statuses.append(status["status"])
            
            assert all(status == "RUNNING" for status in statuses)

    def test_error_recovery_workflow(self, client):
        """测试错误恢复工作流程"""
        with patch.object(client, 'send_request') as mock_send:
            responses = [
                # 首次提交失败
                {"success": False, "error": "Server busy"},
                # 重试提交成功
                {"success": True, "job_uuid": "recovery-uuid"},
                # 状态查询成功
                {"success": True, "status": "RUNNING"}
            ]
            mock_send.side_effect = responses
            
            # 第一次提交失败
            first_result = client.submit_job(b"test data")
            assert first_result["success"] is False
            
            # 重试提交成功
            retry_result = client.submit_job(b"test data")
            assert retry_result["success"] is True
            job_uuid = retry_result["job_uuid"]
            
            # 查询状态确认作业运行
            status_result = client.get_job_status(job_uuid)
            assert status_result["status"] == "RUNNING"


@pytest.mark.slow
class TestJobManagerClientPerformance:
    """JobManagerClient性能测试"""

    @pytest.fixture
    def client(self):
        """创建JobManagerClient实例"""
        return JobManagerClient()

    def test_request_latency(self, client):
        """测试请求延迟"""
        import time
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = {"success": True, "status": "healthy"}
            
            # 测量100次健康检查的平均延迟
            start_time = time.time()
            
            for _ in range(100):
                client.health_check()
            
            end_time = time.time()
            avg_latency = (end_time - start_time) / 100
            
            # 验证平均延迟小于10ms（模拟场景）
            assert avg_latency < 0.01, f"Average latency {avg_latency:.4f}s, expected < 0.01s"

    def test_concurrent_requests(self, client):
        """测试并发请求处理"""
        import concurrent.futures
        import time
        
        def make_request(i):
            with patch.object(client, 'send_request') as mock_send:
                mock_send.return_value = {"success": True, "job_uuid": f"concurrent-{i}"}
                return client.submit_job(f"concurrent job {i}".encode())
        
        # 并发发送50个请求
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        duration = end_time - start_time
        
        # 验证所有请求都成功
        assert len(results) == 50
        assert all(result["success"] for result in results)
        
        # 验证并发性能
        assert duration < 5.0, f"Concurrent requests took {duration:.2f}s, expected < 5s"

    def test_large_payload_handling(self, client):
        """测试大负载处理"""
        # 创建1MB的测试数据
        large_data = b"x" * (1024 * 1024)
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = {"success": True, "job_uuid": "large-payload-uuid"}
            
            start_time = time.time()
            result = client.submit_job(large_data)
            end_time = time.time()
            
            assert result["success"] is True
            duration = end_time - start_time
            
            # 验证大负载处理在合理时间内完成
            assert duration < 2.0, f"Large payload handling took {duration:.2f}s, expected < 2s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

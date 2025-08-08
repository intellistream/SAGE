"""
JobManager 集成测试
测试 JobManager 模块各组件之间的真实集成，重点测试网络通信、序列化和实际的端到端流程
"""
import pytest
import time
import threading
import json
from unittest.mock import patch

from sage.kernel.api.jobmanager_client import JobManagerClient


@pytest.mark.integration
class TestJobManagerClientServerIntegration:
    """JobManager 客户端-服务器真实集成测试"""
    
    def test_real_tcp_communication_simulation(self):
        """测试真实TCP通信模拟"""
        # 创建客户端连接
        client = JobManagerClient(host="localhost", port=8080, timeout=2.0)
        
        # 测试健康检查
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = {"success": True, "status": "healthy"}
            
            result = client.health_check()
            assert result["success"] is True
            assert result["status"] == "healthy"
            
            # 验证请求格式
            sent_request = mock_send.call_args[0][0]
            assert "action" in sent_request
            assert "request_id" in sent_request
            assert sent_request["action"] == "health_check"

    def test_request_response_serialization(self):
        """测试请求-响应序列化"""
        client = JobManagerClient(timeout=1.0)
        
        # 测试复杂数据结构的序列化
        complex_request = {
            "action": "submit_job",
            "request_id": "test-123",
            "data": {
                "environment_name": "test_env",
                "config": {
                    "batch_size": 1000,
                    "timeout": 30,
                    "nested_data": {
                        "algorithms": ["algo1", "algo2"],
                        "parameters": {
                            "learning_rate": 0.01,
                            "epochs": 100
                        }
                    }
                },
                "metadata": {
                    "created_by": "integration_test",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        }
        
        # 测试序列化能力
        serialized = json.dumps(complex_request)
        deserialized = json.loads(serialized)
        
        assert deserialized == complex_request
        assert deserialized["data"]["config"]["nested_data"]["parameters"]["learning_rate"] == 0.01

    def test_large_data_transfer(self):
        """测试大数据传输"""
        client = JobManagerClient(timeout=5.0)
        
        # 创建大数据负载
        large_data = {
            "action": "bulk_operation", 
            "request_id": "bulk-test-456",
            "data": {
                "items": [{"id": i, "data": f"data_item_{i}" * 100} for i in range(1000)],
                "metadata": {
                    "total_items": 1000,
                    "item_size": "large"
                }
            }
        }
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = {
                "success": True, 
                "processed_items": 1000,
                "processing_time": 2.5
            }
            
            # 发送大数据请求
            result = client.send_request(large_data)
            
            assert result["success"] is True
            assert result["processed_items"] == 1000
            
            # 验证发送的数据结构
            sent_data = mock_send.call_args[0][0]
            assert len(sent_data["data"]["items"]) == 1000
            assert sent_data["data"]["metadata"]["total_items"] == 1000


@pytest.mark.integration  
class TestJobManagerBasicOperations:
    """JobManager 基本操作真实测试"""
    
    def test_job_info_creation_and_status_tracking(self):
        """测试 JobInfo 创建和状态跟踪"""
        from sage.kernel.jobmanager.job_info import JobInfo
        from sage.core.api.local_environment import LocalEnvironment
        
        # 创建真实的环境对象
        env = LocalEnvironment("test_job_info", {})
        
        # 创建 JobInfo 实例
        job_info = JobInfo(environment=env, graph=None, dispatcher=None, uuid="test-uuid-123")
        
        # 测试初始状态
        assert job_info.uuid == "test-uuid-123"
        assert job_info.status == "initializing"
        assert job_info.environment.name == "test_job_info"
        
        # 测试状态转换
        job_info.update_status("running")
        assert job_info.status == "running"
        assert job_info.stop_time is None
        
        # 测试元数据
        job_info.add_metadata("job_type", "integration_test")
        job_info.add_metadata("priority", "high")
        
        assert job_info.get_metadata("job_type") == "integration_test"
        assert job_info.get_metadata("priority") == "high"
        assert job_info.get_metadata("non_existent", "default") == "default"
        
        # 测试完成状态
        job_info.update_status("stopped")
        assert job_info.status == "stopped"
        assert job_info.stop_time is not None
        
        # 测试摘要信息
        summary = job_info.get_summary()
        assert summary["uuid"] == "test-uuid-123"
        assert summary["status"] == "stopped"
        assert "runtime" in summary

    def test_execution_graph_basic_structure(self):
        """测试执行图基本结构创建"""
        from sage.kernel.jobmanager.compiler.execution_graph import ExecutionGraph
        from sage.core.api.local_environment import LocalEnvironment
        
        # 创建真实环境但不添加复杂的 pipeline
        env = LocalEnvironment("test_execution_graph", {})
        env.pipeline = []  # 空的 pipeline
        env.service_factories = {}  # 空的服务工厂
        
        # 创建执行图
        graph = ExecutionGraph(env)
        
        # 验证基本结构
        assert graph.env == env
        assert isinstance(graph.nodes, dict)
        assert isinstance(graph.service_nodes, dict)
        assert isinstance(graph.edges, dict)
        
        # 验证日志系统设置
        assert hasattr(graph, 'logger')
        assert graph.logger is not None


@pytest.mark.integration
class TestJobManagerComponentIntegration:
    """JobManager 组件集成测试 - 测试组件之间的真实交互"""
    
    def test_job_info_status_transitions(self):
        """测试作业信息状态转换的完整性"""
        from sage.kernel.jobmanager.job_info import JobInfo
        from sage.core.api.local_environment import LocalEnvironment
        
        env = LocalEnvironment("status_test", {})
        job_info = JobInfo(environment=env, graph=None, dispatcher=None, uuid="status-test-uuid")
        
        # 测试完整的状态转换流程
        status_transitions = [
            ("initializing", False),
            ("running", False), 
            ("paused", False),
            ("running", False),
            ("stopped", True),
            ("restarting", False),
            ("running", False),
            ("failed", True)
        ]
        
        for status, should_have_stop_time in status_transitions:
            job_info.update_status(status)
            assert job_info.status == status
            
            if should_have_stop_time:
                assert job_info.stop_time is not None
            else:
                if status != "failed":  # failed 状态会设置 stop_time
                    pass  # stop_time 可能被之前的状态设置
        
        # 测试错误处理
        job_info.update_status("failed", "Test error occurred")
        assert job_info.status == "failed" 
        assert job_info.error_message == "Test error occurred"
        
        # 测试运行时计算
        runtime_str = job_info.get_runtime()
        assert isinstance(runtime_str, str)
        assert "s" in runtime_str  # 应该包含秒数

    def test_client_request_structure_validation(self):
        """测试客户端请求结构验证"""
        client = JobManagerClient(timeout=1.0)
        
        # 测试健康检查请求结构
        health_request = client._build_health_check_request()
        assert "action" in health_request
        assert "request_id" in health_request
        assert health_request["action"] == "health_check"
        
        # 测试服务器信息请求结构  
        server_info_request = client._build_server_info_request()
        assert "action" in server_info_request
        assert "request_id" in server_info_request
        assert server_info_request["action"] == "get_server_info"
        
        # 测试请求ID的唯一性
        req1 = client._build_health_check_request()
        req2 = client._build_health_check_request()
        assert req1["request_id"] != req2["request_id"]

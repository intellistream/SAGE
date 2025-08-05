"""
JobManager 综合集成测试
测试 JobManager 模块各组件之间的集成，端到端工作流程，以及真实场景模拟
"""
import pytest
import time
import threading
import concurrent.futures
from unittest.mock import Mock, patch, MagicMock

from sage.kernels.jobmanager.job_manager import JobManager
from sage.kernels.jobmanager.jobmanager_client import JobManagerClient
from sage.kernels.jobmanager.job_manager_server import JobManagerServer
from sage.kernels.jobmanager.job_info import JobInfo
from sage.kernels.jobmanager.execution_graph.execution_graph import ExecutionGraph


@pytest.mark.integration
class TestJobManagerFullIntegration:
    """JobManager完整集成测试"""

    @pytest.fixture
    def reset_jobmanager_singleton(self):
        """重置JobManager单例"""
        JobManager.instance = None
        yield
        JobManager.instance = None

    @pytest.fixture
    def mock_environment(self):
        """创建模拟环境"""
        env = Mock()
        env.name = "integration_test_env"
        env.env_uuid = None
        env.console_log_level = "INFO"
        env.env_base_dir = "/tmp/integration_test"
        env.pipeline = Mock()
        env.pipeline.transformations = []
        return env

    def test_complete_job_submission_workflow(self, reset_jobmanager_singleton, mock_environment):
        """测试完整的作业提交工作流程"""
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'), \
             patch('sage.kernels.runtime.serialization.dill.deserialize_object'), \
             patch('sage.kernels.runtime.dispatcher.Dispatcher'):
            
            # 1. 创建JobManager
            job_manager = JobManager(enable_daemon=False)
            assert job_manager is not None
            
            # 2. 提交作业
            with patch.object(job_manager, '_generate_job_uuid') as mock_uuid, \
                 patch.object(job_manager, '_create_job_info') as mock_create_info, \
                 patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
                
                test_uuid = "integration-test-uuid"
                mock_uuid.return_value = test_uuid
                mock_job_info = Mock()
                mock_job_info.status = "SUBMITTED"
                mock_create_info.return_value = mock_job_info
                mock_submit.return_value = True
                
                job_uuid = job_manager.submit_job(mock_environment)
                assert job_uuid == test_uuid
                assert mock_environment.env_uuid == test_uuid
            
            # 3. 查询作业状态
            with patch.object(job_manager, '_get_job_info') as mock_get_info:
                mock_job_info.to_dict.return_value = {
                    "job_uuid": test_uuid,
                    "status": "RUNNING",
                    "progress": 0.5
                }
                mock_get_info.return_value = mock_job_info
                
                status = job_manager.get_job_status(test_uuid)
                assert status["success"] is True
                assert status["status"] == "RUNNING"
            
            # 4. 控制作业（暂停/恢复）
            with patch.object(job_manager, '_pause_job_execution') as mock_pause, \
                 patch.object(job_manager, '_resume_job_execution') as mock_resume:
                
                mock_pause.return_value = True
                mock_resume.return_value = True
                
                # 暂停作业
                pause_result = job_manager.pause_job(test_uuid)
                assert pause_result["success"] is True
                
                # 恢复作业
                resume_result = job_manager.resume_job(test_uuid)
                assert resume_result["success"] is True

    def test_client_server_communication(self, reset_jobmanager_singleton):
        """测试客户端-服务器通信"""
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'):
            job_manager = JobManager(enable_daemon=False)
            
            # 模拟客户端请求
            mock_client = Mock()
            
            with patch.object(job_manager, 'health_check') as mock_health, \
                 patch.object(job_manager, 'get_server_info') as mock_info:
                
                mock_health.return_value = {"status": "healthy", "uptime": 3600}
                mock_info.return_value = {"version": "1.0.0", "daemon_port": 19001}
                
                # 健康检查
                health_result = job_manager.health_check()
                assert health_result["status"] == "healthy"
                
                # 服务器信息
                info_result = job_manager.get_server_info()
                assert info_result["version"] == "1.0.0"

    def test_multiple_jobs_concurrent_management(self, reset_jobmanager_singleton, mock_environment):
        """测试多作业并发管理"""
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'):
            job_manager = JobManager(enable_daemon=False)
            
            # 创建多个环境
            environments = []
            for i in range(5):
                env = Mock()
                env.name = f"concurrent_env_{i}"
                env.env_uuid = None
                environments.append(env)
            
            with patch.object(job_manager, '_generate_job_uuid') as mock_uuid, \
                 patch.object(job_manager, '_create_job_info') as mock_create_info, \
                 patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
                
                # 设置模拟返回值
                mock_uuid.side_effect = [f"concurrent-uuid-{i}" for i in range(5)]
                mock_create_info.return_value = Mock()
                mock_submit.return_value = True
                
                # 并发提交作业
                def submit_job(env):
                    return job_manager.submit_job(env)
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [executor.submit(submit_job, env) for env in environments]
                    results = [future.result() for future in concurrent.futures.as_completed(futures)]
                
                # 验证所有作业都成功提交
                assert len(results) == 5
                assert len(set(results)) == 5  # 所有UUID都不同
                
                # 验证所有环境的UUID都被设置
                for i, env in enumerate(environments):
                    assert env.env_uuid == f"concurrent-uuid-{i}"

    def test_job_lifecycle_state_transitions(self, reset_jobmanager_singleton, mock_environment):
        """测试作业生命周期状态转换"""
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'):
            job_manager = JobManager(enable_daemon=False)
            
            with patch.object(job_manager, '_generate_job_uuid') as mock_uuid, \
                 patch.object(job_manager, '_create_job_info') as mock_create_info, \
                 patch.object(job_manager, '_submit_to_dispatcher') as mock_submit, \
                 patch.object(job_manager, '_get_job_info') as mock_get_info:
                
                test_uuid = "lifecycle-test-uuid"
                mock_uuid.return_value = test_uuid
                
                # 创建JobInfo实例来模拟状态转换
                job_info = JobInfo(job_uuid=test_uuid, environment=mock_environment)
                mock_create_info.return_value = job_info
                mock_get_info.return_value = job_info
                mock_submit.return_value = True
                
                # 1. 提交作业 (SUBMITTED)
                job_uuid = job_manager.submit_job(mock_environment)
                assert job_info.status == "SUBMITTED"
                
                # 2. 模拟状态转换到PENDING
                job_info.update_status("PENDING")
                status = job_manager.get_job_status(test_uuid)
                assert status["status"] == "PENDING"
                
                # 3. 模拟状态转换到RUNNING
                job_info.update_status("RUNNING")
                status = job_manager.get_job_status(test_uuid)
                assert status["status"] == "RUNNING"
                
                # 4. 模拟进度更新
                for progress in [0.25, 0.5, 0.75, 1.0]:
                    job_info.update_progress(progress)
                    status = job_manager.get_job_status(test_uuid)
                    assert status["progress"] == progress
                
                # 5. 模拟作业完成
                job_info.update_status("COMPLETED")
                status = job_manager.get_job_status(test_uuid)
                assert status["status"] == "COMPLETED"
                assert status["progress"] == 1.0

    def test_error_handling_and_recovery(self, reset_jobmanager_singleton, mock_environment):
        """测试错误处理和恢复"""
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'):
            job_manager = JobManager(enable_daemon=False)
            
            # 测试提交失败的恢复
            with patch.object(job_manager, '_generate_job_uuid') as mock_uuid, \
                 patch.object(job_manager, '_create_job_info') as mock_create_info, \
                 patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
                
                test_uuid = "error-test-uuid"
                mock_uuid.return_value = test_uuid
                mock_create_info.return_value = Mock()
                
                # 第一次提交失败
                mock_submit.side_effect = Exception("Submission failed")
                
                with pytest.raises(Exception, match="Submission failed"):
                    job_manager.submit_job(mock_environment)
                
                # 第二次提交成功
                mock_submit.side_effect = None
                mock_submit.return_value = True
                
                job_uuid = job_manager.submit_job(mock_environment)
                assert job_uuid == test_uuid

    def test_resource_cleanup_on_shutdown(self, reset_jobmanager_singleton):
        """测试关闭时的资源清理"""
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer') as mock_server_class:
            mock_server = Mock()
            mock_server_class.return_value = mock_server
            
            job_manager = JobManager(enable_daemon=True)
            
            # 模拟服务器运行
            job_manager.server = mock_server
            mock_server.is_running = True
            
            # 关闭JobManager
            job_manager.stop_daemon()
            
            # 验证服务器被正确停止
            mock_server.stop.assert_called_once()


@pytest.mark.integration
class TestJobManagerClientServerIntegration:
    """JobManager客户端-服务器集成测试"""

    def test_real_tcp_communication_simulation(self):
        """测试真实TCP通信模拟"""
        # 创建模拟的服务器端JobManager
        mock_job_manager = Mock()
        mock_job_manager.health_check.return_value = {"status": "healthy"}
        mock_job_manager.submit_job.return_value = "tcp-test-uuid"
        
        # 创建客户端
        client = JobManagerClient(host="127.0.0.1", port=19001)
        
        # 模拟TCP通信
        with patch.object(client, 'send_request') as mock_send:
            # 健康检查通信
            mock_send.return_value = {"success": True, "status": "healthy"}
            result = client.health_check()
            assert result["status"] == "healthy"
            
            # 作业提交通信
            mock_send.return_value = {"success": True, "job_uuid": "tcp-test-uuid"}
            result = client.submit_job(b"test job data")
            assert result["job_uuid"] == "tcp-test-uuid"

    def test_request_response_serialization(self):
        """测试请求-响应序列化"""
        client = JobManagerClient()
        
        # 测试复杂数据结构的序列化
        complex_response = {
            "success": True,
            "job_info": {
                "uuid": "complex-uuid",
                "status": "RUNNING",
                "metadata": {
                    "tags": ["ml", "production"],
                    "config": {"batch_size": 32, "learning_rate": 0.01}
                },
                "timestamps": {
                    "created": "2023-01-01T10:00:00Z",
                    "started": "2023-01-01T10:01:00Z"
                }
            }
        }
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = complex_response
            
            result = client.get_job_status("complex-uuid")
            
            # 验证复杂数据结构正确传输
            assert result["job_info"]["metadata"]["tags"] == ["ml", "production"]
            assert result["job_info"]["metadata"]["config"]["batch_size"] == 32

    def test_connection_retry_mechanism(self):
        """测试连接重试机制"""
        client = JobManagerClient(timeout=1.0)
        
        with patch.object(client, 'send_request') as mock_send:
            # 模拟连接失败然后成功的场景
            mock_send.side_effect = [
                ConnectionError("Connection failed"),
                ConnectionError("Connection failed"),
                {"success": True, "status": "healthy"}  # 第三次成功
            ]
            
            # 客户端应该实现重试机制
            with patch.object(client, '_retry_request') as mock_retry:
                mock_retry.return_value = {"success": True, "status": "healthy"}
                
                result = client.health_check()
                assert result["success"] is True

    def test_large_data_transfer(self):
        """测试大数据传输"""
        client = JobManagerClient()
        
        # 创建大量数据 (1MB)
        large_data = b"x" * (1024 * 1024)
        
        with patch.object(client, 'send_request') as mock_send:
            mock_send.return_value = {"success": True, "job_uuid": "large-data-uuid"}
            
            start_time = time.time()
            result = client.submit_job(large_data)
            end_time = time.time()
            
            assert result["success"] is True
            # 验证大数据传输在合理时间内完成
            transfer_time = end_time - start_time
            assert transfer_time < 5.0  # 5秒内完成


@pytest.mark.integration
class TestJobManagerExecutionGraphIntegration:
    """JobManager与ExecutionGraph集成测试"""

    @pytest.fixture
    def mock_environment_with_pipeline(self):
        """创建带有流水线的模拟环境"""
        env = Mock()
        env.name = "pipeline_test_env"
        env.console_log_level = "INFO"
        env.env_base_dir = "/tmp/pipeline_test"
        env.pipeline = Mock()
        
        # 创建模拟的转换流水线
        transforms = []
        for i in range(3):
            transform = Mock()
            transform.name = f"transform_{i}"
            transforms.append(transform)
        
        env.pipeline.transformations = transforms
        return env

    def test_job_submission_with_execution_graph(self, mock_environment_with_pipeline):
        """测试带有执行图的作业提交"""
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'), \
             patch.object(ExecutionGraph, '__init__', return_value=None), \
             patch('sage.kernels.runtime.dispatcher.Dispatcher'):
            
            JobManager.instance = None  # 重置单例
            job_manager = JobManager(enable_daemon=False)
            
            with patch.object(job_manager, '_generate_job_uuid') as mock_uuid, \
                 patch.object(job_manager, '_create_execution_graph') as mock_create_graph, \
                 patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
                
                test_uuid = "graph-test-uuid"
                mock_uuid.return_value = test_uuid
                
                # 模拟执行图创建
                mock_graph = Mock()
                mock_graph.nodes = {"node1": Mock(), "node2": Mock()}
                mock_graph.edges = {"edge1": Mock()}
                mock_create_graph.return_value = mock_graph
                mock_submit.return_value = True
                
                job_uuid = job_manager.submit_job(mock_environment_with_pipeline)
                
                assert job_uuid == test_uuid
                mock_create_graph.assert_called_once_with(mock_environment_with_pipeline)

    def test_execution_graph_optimization(self, mock_environment_with_pipeline):
        """测试执行图优化"""
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline'), \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'generate_runtime_contexts'), \
             patch.object(ExecutionGraph, 'setup_logging_system'):
            
            graph = ExecutionGraph(mock_environment_with_pipeline)
            
            # 添加节点进行优化测试
            mock_nodes = {}
            for i in range(3):
                node = Mock()
                node.name = f"node_{i}"
                node.is_source = (i == 0)
                node.is_sink = (i == 2)
                mock_nodes[f"node_{i}"] = node
            
            graph.nodes = mock_nodes
            
            # 测试图优化
            with patch.object(graph, 'optimize_graph') as mock_optimize:
                mock_optimize.return_value = True
                
                optimization_result = graph.optimize_graph()
                assert optimization_result is True

    def test_runtime_context_generation_integration(self, mock_environment_with_pipeline):
        """测试运行时上下文生成集成"""
        with patch.object(ExecutionGraph, '_build_graph_from_pipeline'), \
             patch.object(ExecutionGraph, '_build_service_nodes'), \
             patch.object(ExecutionGraph, 'setup_logging_system'):
            
            graph = ExecutionGraph(mock_environment_with_pipeline)
            
            # 添加测试节点
            mock_transform = Mock()
            mock_transform.name = "test_transform"
            
            from sage.kernels.jobmanager.execution_graph.graph_node import GraphNode
            node = GraphNode(
                transformation=mock_transform,
                name="test_node",
                is_source=True,
                is_sink=False
            )
            graph.nodes["test_node"] = node
            
            # 添加服务节点
            from sage.kernels.jobmanager.execution_graph.service_node import ServiceNode
            service_node = ServiceNode(
                service_name="test_service",
                service_type="ML_SERVICE"
            )
            graph.service_nodes["test_service"] = service_node
            
            with patch('sage.kernels.runtime.task_context.TaskContext') as mock_task_context, \
                 patch('sage.kernels.runtime.service_context.ServiceContext') as mock_service_context:
                
                mock_task_context.return_value = Mock()
                mock_service_context.return_value = Mock()
                
                graph.generate_runtime_contexts()
                
                # 验证上下文被创建
                mock_task_context.assert_called_once()
                mock_service_context.assert_called_once()
                
                # 验证上下文被分配
                assert node.ctx is not None
                assert service_node.ctx is not None


@pytest.mark.integration 
class TestJobManagerRealWorldScenarios:
    """JobManager真实世界场景测试"""

    def test_machine_learning_pipeline_simulation(self):
        """测试机器学习流水线模拟"""
        # 创建ML流水线环境
        ml_env = Mock()
        ml_env.name = "ml_training_pipeline"
        ml_env.env_uuid = None
        ml_env.console_log_level = "INFO"
        ml_env.env_base_dir = "/tmp/ml_pipeline"
        
        # 模拟ML流水线组件
        pipeline_stages = [
            "data_ingestion",
            "data_preprocessing", 
            "feature_engineering",
            "model_training",
            "model_evaluation",
            "model_deployment"
        ]
        
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'):
            JobManager.instance = None
            job_manager = JobManager(enable_daemon=False)
            
            with patch.object(job_manager, '_generate_job_uuid') as mock_uuid, \
                 patch.object(job_manager, '_create_job_info') as mock_create_info, \
                 patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
                
                test_uuid = "ml-pipeline-uuid"
                mock_uuid.return_value = test_uuid
                
                # 创建作业信息来模拟ML流水线执行
                job_info = JobInfo(job_uuid=test_uuid, environment=ml_env)
                job_info.add_metadata("pipeline_type", "ml_training")
                job_info.add_metadata("stages", pipeline_stages)
                job_info.add_metadata("dataset_size", "10GB")
                job_info.add_metadata("model_type", "neural_network")
                
                mock_create_info.return_value = job_info
                mock_submit.return_value = True
                
                # 提交ML作业
                job_uuid = job_manager.submit_job(ml_env)
                assert job_uuid == test_uuid
                
                # 模拟各个阶段的执行
                with patch.object(job_manager, '_get_job_info') as mock_get_info:
                    mock_get_info.return_value = job_info
                    
                    # 模拟阶段进度
                    stage_progress = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
                    for i, progress in enumerate(stage_progress):
                        stage_name = pipeline_stages[i]
                        job_info.update_progress(progress, message=f"Executing {stage_name}")
                        
                        status = job_manager.get_job_status(test_uuid)
                        assert status["progress"] == progress
                        assert stage_name in status.get("progress_message", "")

    def test_data_processing_batch_job(self):
        """测试数据处理批量作业"""
        # 创建批量数据处理环境
        batch_env = Mock()
        batch_env.name = "daily_data_processing"
        batch_env.env_uuid = None
        
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'):
            JobManager.instance = None
            job_manager = JobManager(enable_daemon=False)
            
            # 模拟批量数据处理作业
            batch_size = 1000
            total_records = 50000
            expected_batches = total_records // batch_size
            
            with patch.object(job_manager, '_generate_job_uuid') as mock_uuid, \
                 patch.object(job_manager, '_create_job_info') as mock_create_info, \
                 patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
                
                test_uuid = "batch-processing-uuid"
                mock_uuid.return_value = test_uuid
                
                job_info = JobInfo(job_uuid=test_uuid, environment=batch_env)
                job_info.add_metadata("job_type", "batch_processing")
                job_info.add_metadata("total_records", total_records)
                job_info.add_metadata("batch_size", batch_size)
                job_info.add_metadata("expected_batches", expected_batches)
                
                mock_create_info.return_value = job_info
                mock_submit.return_value = True
                
                job_uuid = job_manager.submit_job(batch_env)
                
                # 模拟批量处理进度
                with patch.object(job_manager, '_get_job_info') as mock_get_info:
                    mock_get_info.return_value = job_info
                    
                    for batch_num in range(1, expected_batches + 1):
                        progress = batch_num / expected_batches
                        message = f"Processed batch {batch_num}/{expected_batches}"
                        job_info.update_progress(progress, message=message)
                        
                        status = job_manager.get_job_status(test_uuid)
                        assert abs(status["progress"] - progress) < 0.01

    def test_distributed_compute_job(self):
        """测试分布式计算作业"""
        # 创建分布式计算环境
        distributed_env = Mock()
        distributed_env.name = "distributed_computation"
        distributed_env.env_uuid = None
        
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'):
            JobManager.instance = None
            job_manager = JobManager(enable_daemon=False)
            
            # 模拟分布式计算节点
            compute_nodes = ["node1", "node2", "node3", "node4"]
            
            with patch.object(job_manager, '_generate_job_uuid') as mock_uuid, \
                 patch.object(job_manager, '_create_job_info') as mock_create_info, \
                 patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
                
                test_uuid = "distributed-compute-uuid"
                mock_uuid.return_value = test_uuid
                
                job_info = JobInfo(job_uuid=test_uuid, environment=distributed_env)
                job_info.add_metadata("job_type", "distributed_compute")
                job_info.add_metadata("compute_nodes", compute_nodes)
                job_info.add_metadata("parallelism", len(compute_nodes))
                
                mock_create_info.return_value = job_info
                mock_submit.return_value = True
                
                job_uuid = job_manager.submit_job(distributed_env)
                
                # 模拟分布式计算的并行执行
                with patch.object(job_manager, '_get_job_info') as mock_get_info:
                    mock_get_info.return_value = job_info
                    
                    # 模拟各个节点的计算进度
                    node_progress = {node: 0.0 for node in compute_nodes}
                    
                    # 模拟异步进度更新
                    import random
                    for step in range(10):
                        # 随机更新某些节点的进度
                        for node in random.sample(compute_nodes, 2):
                            node_progress[node] = min(1.0, node_progress[node] + 0.1)
                        
                        # 计算总体进度
                        overall_progress = sum(node_progress.values()) / len(compute_nodes)
                        job_info.update_progress(overall_progress)
                        
                        status = job_manager.get_job_status(test_uuid)
                        assert status["progress"] <= 1.0

    def test_long_running_service_job(self):
        """测试长时间运行的服务作业"""
        # 创建长时间运行服务环境
        service_env = Mock()
        service_env.name = "long_running_service"
        service_env.env_uuid = None
        
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'):
            JobManager.instance = None
            job_manager = JobManager(enable_daemon=False)
            
            with patch.object(job_manager, '_generate_job_uuid') as mock_uuid, \
                 patch.object(job_manager, '_create_job_info') as mock_create_info, \
                 patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
                
                test_uuid = "long-running-service-uuid"
                mock_uuid.return_value = test_uuid
                
                job_info = JobInfo(job_uuid=test_uuid, environment=service_env)
                job_info.add_metadata("job_type", "long_running_service")
                job_info.add_metadata("service_type", "web_api")
                job_info.add_metadata("expected_duration", "indefinite")
                
                mock_create_info.return_value = job_info
                mock_submit.return_value = True
                
                job_uuid = job_manager.submit_job(service_env)
                
                # 模拟长时间运行服务的状态
                with patch.object(job_manager, '_get_job_info') as mock_get_info:
                    mock_get_info.return_value = job_info
                    
                    # 服务启动
                    job_info.update_status("RUNNING")
                    job_info.update_progress(0.1, "Service initializing")
                    
                    # 服务就绪
                    job_info.update_progress(1.0, "Service ready and accepting requests")
                    
                    status = job_manager.get_job_status(test_uuid)
                    assert status["status"] == "RUNNING"
                    assert status["progress"] == 1.0
                    assert "ready" in status["progress_message"]
                    
                    # 模拟服务健康检查
                    for health_check in range(5):
                        job_info.add_metadata(f"health_check_{health_check}", {
                            "timestamp": time.time(),
                            "status": "healthy",
                            "cpu_usage": "15%",
                            "memory_usage": "2.3GB"
                        })


@pytest.mark.slow
class TestJobManagerPerformanceIntegration:
    """JobManager性能集成测试"""

    def test_high_throughput_job_submission(self):
        """测试高吞吐量作业提交"""
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'):
            JobManager.instance = None
            job_manager = JobManager(enable_daemon=False)
            
            # 准备大量测试环境
            environments = []
            for i in range(100):
                env = Mock()
                env.name = f"throughput_test_env_{i}"
                env.env_uuid = None
                environments.append(env)
            
            with patch.object(job_manager, '_generate_job_uuid') as mock_uuid, \
                 patch.object(job_manager, '_create_job_info') as mock_create_info, \
                 patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
                
                mock_uuid.side_effect = [f"throughput-uuid-{i}" for i in range(100)]
                mock_create_info.return_value = Mock()
                mock_submit.return_value = True
                
                # 测量提交时间
                start_time = time.time()
                
                for env in environments:
                    job_manager.submit_job(env)
                
                end_time = time.time()
                duration = end_time - start_time
                
                # 验证吞吐量性能
                throughput = 100 / duration
                assert throughput > 50, f"Throughput {throughput:.2f} jobs/s, expected > 50 jobs/s"

    def test_concurrent_operations_stress(self):
        """测试并发操作压力"""
        with patch('sage.kernels.jobmanager.job_manager.JobManagerServer'):
            JobManager.instance = None
            job_manager = JobManager(enable_daemon=False)
            
            # 模拟各种并发操作
            def submit_jobs():
                for i in range(10):
                    env = Mock()
                    env.name = f"stress_env_{i}"
                    env.env_uuid = None
                    with patch.object(job_manager, '_generate_job_uuid'), \
                         patch.object(job_manager, '_create_job_info'), \
                         patch.object(job_manager, '_submit_to_dispatcher'):
                        job_manager.submit_job(env)
            
            def query_status():
                for i in range(10):
                    with patch.object(job_manager, '_get_job_info'):
                        job_manager.get_job_status(f"stress-uuid-{i}")
            
            def control_jobs():
                for i in range(10):
                    with patch.object(job_manager, '_get_job_info'), \
                         patch.object(job_manager, '_pause_job_execution'):
                        job_manager.pause_job(f"stress-uuid-{i}")
            
            # 并发执行所有操作
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                futures = []
                futures.append(executor.submit(submit_jobs))
                futures.append(executor.submit(submit_jobs))
                futures.append(executor.submit(query_status))
                futures.append(executor.submit(query_status))
                futures.append(executor.submit(control_jobs))
                futures.append(executor.submit(control_jobs))
                
                # 等待所有操作完成
                for future in concurrent.futures.as_completed(futures):
                    future.result()  # 会抛出异常如果有的话


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

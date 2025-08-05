"""
JobManager 核心组件测试
测试 JobManager 类的所有核心功能，包括单例模式、作业管理、状态维护等
"""
import pytest
import threading
import time
import uuid
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from sage.kernel.kernels.jobmanager.job_manager import JobManager
from sage.kernel.kernels.jobmanager.job_info import JobInfo


@pytest.fixture
def reset_jobmanager_singleton():
    """重置JobManager单例，确保测试隔离"""
    JobManager.instance = None
    yield
    JobManager.instance = None


@pytest.mark.unit
class TestJobManagerSingleton:
    """测试JobManager单例模式"""

    def test_singleton_instance_creation(self, reset_jobmanager_singleton):
        """测试单例实例创建"""
        # 创建第一个实例
        jm1 = JobManager(enable_daemon=False)
        assert jm1 is not None
        
        # 创建第二个实例，应该返回同一个对象
        jm2 = JobManager(enable_daemon=False)
        assert jm1 is jm2
        assert id(jm1) == id(jm2)

    def test_singleton_thread_safety(self, reset_jobmanager_singleton):
        """测试单例模式的线程安全性"""
        instances = []
        
        def create_instance():
            jm = JobManager(enable_daemon=False)
            instances.append(jm)
        
        # 创建多个线程同时创建实例
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)
            
        # 启动所有线程
        for thread in threads:
            thread.start()
            
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有实例都是同一个对象
        assert len(instances) == 10
        for instance in instances:
            assert instance is instances[0]

    def test_singleton_initialization_once(self, reset_jobmanager_singleton):
        """测试单例只初始化一次"""
        with patch.object(JobManager, '__init__', wraps=JobManager.__init__) as mock_init:
            # 创建多个实例
            jm1 = JobManager(enable_daemon=False)
            jm2 = JobManager(enable_daemon=False)
            jm3 = JobManager(enable_daemon=False)
            
            # __init__应该只被调用一次
            assert mock_init.call_count == 1


@pytest.mark.unit
class TestJobManagerInitialization:
    """测试JobManager初始化"""

    def test_default_initialization(self, reset_jobmanager_singleton):
        """测试默认参数初始化"""
        with patch('sage.kernel.kernels.jobmanager.job_manager.JobManagerServer'):
            jm = JobManager()
            assert jm.enable_daemon is True
            assert jm.daemon_host == "127.0.0.1"
            assert jm.daemon_port == 19001

    def test_custom_initialization(self, reset_jobmanager_singleton):
        """测试自定义参数初始化"""
        with patch('sage.kernel.kernels.jobmanager.job_manager.JobManagerServer'):
            jm = JobManager(
                enable_daemon=False,
                daemon_host="0.0.0.0",
                daemon_port=8080
            )
            assert jm.enable_daemon is False
            assert jm.daemon_host == "0.0.0.0"
            assert jm.daemon_port == 8080

    def test_daemon_server_creation(self, reset_jobmanager_singleton):
        """测试守护进程服务器创建"""
        with patch('sage.kernel.kernels.jobmanager.job_manager.JobManagerServer') as mock_server:
            jm = JobManager(enable_daemon=True)
            mock_server.assert_called_once_with(
                host="127.0.0.1",
                port=19001,
                job_manager=jm
            )

    def test_no_daemon_server_creation(self, reset_jobmanager_singleton):
        """测试禁用守护进程时不创建服务器"""
        with patch('sage.kernel.kernels.jobmanager.job_manager.JobManagerServer') as mock_server:
            jm = JobManager(enable_daemon=False)
            mock_server.assert_not_called()


@pytest.mark.unit
class TestJobManagerJobSubmission:
    """测试作业提交功能"""

    @pytest.fixture
    def job_manager(self, reset_jobmanager_singleton):
        """创建JobManager实例"""
        with patch('sage.kernel.kernels.jobmanager.job_manager.JobManagerServer'):
            return JobManager(enable_daemon=False)

    def test_submit_job_basic(self, job_manager):
        """测试基本作业提交"""
        # 模拟环境对象
        mock_env = Mock()
        mock_env.name = "test_env"
        mock_env.env_uuid = None
        
        with patch.object(job_manager, '_generate_job_uuid') as mock_gen_uuid, \
             patch.object(job_manager, '_create_job_info') as mock_create_info, \
             patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
            
            # 设置模拟返回值
            test_uuid = "test-uuid-123"
            mock_gen_uuid.return_value = test_uuid
            mock_create_info.return_value = Mock()
            mock_submit.return_value = True
            
            # 执行作业提交
            result_uuid = job_manager.submit_job(mock_env)
            
            # 验证结果
            assert result_uuid == test_uuid
            assert mock_env.env_uuid == test_uuid
            mock_gen_uuid.assert_called_once()
            mock_create_info.assert_called_once_with(mock_env, test_uuid)
            mock_submit.assert_called_once()

    def test_submit_job_with_existing_uuid(self, job_manager):
        """测试提交已有UUID的作业"""
        mock_env = Mock()
        mock_env.name = "test_env"
        mock_env.env_uuid = "existing-uuid"
        
        with patch.object(job_manager, '_generate_job_uuid') as mock_gen_uuid:
            result_uuid = job_manager.submit_job(mock_env)
            
            # 不应该生成新的UUID
            mock_gen_uuid.assert_not_called()
            assert result_uuid == "existing-uuid"

    def test_submit_job_failure_handling(self, job_manager):
        """测试作业提交失败处理"""
        mock_env = Mock()
        mock_env.name = "test_env"
        mock_env.env_uuid = None
        
        with patch.object(job_manager, '_generate_job_uuid') as mock_gen_uuid, \
             patch.object(job_manager, '_create_job_info') as mock_create_info, \
             patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
            
            # 模拟提交失败
            mock_gen_uuid.return_value = "test-uuid"
            mock_create_info.return_value = Mock()
            mock_submit.side_effect = Exception("Submission failed")
            
            # 验证异常被正确抛出
            with pytest.raises(Exception, match="Submission failed"):
                job_manager.submit_job(mock_env)

    def test_batch_job_submission(self, job_manager):
        """测试批量作业提交"""
        # 创建多个模拟环境
        envs = []
        for i in range(5):
            env = Mock()
            env.name = f"test_env_{i}"
            env.env_uuid = None
            envs.append(env)
        
        with patch.object(job_manager, 'submit_job') as mock_submit:
            mock_submit.side_effect = [f"uuid-{i}" for i in range(5)]
            
            # 批量提交作业
            uuids = []
            for env in envs:
                uuid = job_manager.submit_job(env)
                uuids.append(uuid)
            
            # 验证所有作业都被提交
            assert len(uuids) == 5
            assert mock_submit.call_count == 5
            for i, uuid in enumerate(uuids):
                assert uuid == f"uuid-{i}"


@pytest.mark.unit
class TestJobManagerJobControl:
    """测试作业控制功能"""

    @pytest.fixture
    def job_manager(self, reset_jobmanager_singleton):
        """创建JobManager实例"""
        with patch('sage.kernel.kernels.jobmanager.job_manager.JobManagerServer'):
            return JobManager(enable_daemon=False)

    def test_pause_job_success(self, job_manager):
        """测试成功暂停作业"""
        job_uuid = "test-job-uuid"
        
        with patch.object(job_manager, '_get_job_info') as mock_get_info, \
             patch.object(job_manager, '_pause_job_execution') as mock_pause:
            
            # 模拟作业信息
            mock_job_info = Mock()
            mock_job_info.status = "RUNNING"
            mock_get_info.return_value = mock_job_info
            mock_pause.return_value = True
            
            # 执行暂停
            result = job_manager.pause_job(job_uuid)
            
            # 验证结果
            assert result["success"] is True
            assert result["job_uuid"] == job_uuid
            mock_get_info.assert_called_once_with(job_uuid)
            mock_pause.assert_called_once_with(job_uuid)

    def test_pause_nonexistent_job(self, job_manager):
        """测试暂停不存在的作业"""
        job_uuid = "nonexistent-job"
        
        with patch.object(job_manager, '_get_job_info') as mock_get_info:
            mock_get_info.return_value = None
            
            result = job_manager.pause_job(job_uuid)
            
            assert result["success"] is False
            assert "not found" in result["message"].lower()

    def test_pause_already_paused_job(self, job_manager):
        """测试暂停已暂停的作业"""
        job_uuid = "paused-job"
        
        with patch.object(job_manager, '_get_job_info') as mock_get_info:
            mock_job_info = Mock()
            mock_job_info.status = "PAUSED"
            mock_get_info.return_value = mock_job_info
            
            result = job_manager.pause_job(job_uuid)
            
            assert result["success"] is False
            assert "already paused" in result["message"].lower()

    def test_resume_job_success(self, job_manager):
        """测试成功恢复作业"""
        job_uuid = "test-job-uuid"
        
        with patch.object(job_manager, '_get_job_info') as mock_get_info, \
             patch.object(job_manager, '_resume_job_execution') as mock_resume:
            
            mock_job_info = Mock()
            mock_job_info.status = "PAUSED"
            mock_get_info.return_value = mock_job_info
            mock_resume.return_value = True
            
            result = job_manager.resume_job(job_uuid)
            
            assert result["success"] is True
            mock_resume.assert_called_once_with(job_uuid)

    def test_cancel_job_success(self, job_manager):
        """测试成功取消作业"""
        job_uuid = "test-job-uuid"
        
        with patch.object(job_manager, '_get_job_info') as mock_get_info, \
             patch.object(job_manager, '_cancel_job_execution') as mock_cancel:
            
            mock_job_info = Mock()
            mock_job_info.status = "RUNNING"
            mock_get_info.return_value = mock_job_info
            mock_cancel.return_value = True
            
            result = job_manager.cancel_job(job_uuid)
            
            assert result["success"] is True
            mock_cancel.assert_called_once_with(job_uuid)


@pytest.mark.unit
class TestJobManagerJobStatus:
    """测试作业状态查询功能"""

    @pytest.fixture
    def job_manager(self, reset_jobmanager_singleton):
        """创建JobManager实例"""
        with patch('sage.kernel.kernels.jobmanager.job_manager.JobManagerServer'):
            return JobManager(enable_daemon=False)

    def test_get_job_status_existing(self, job_manager):
        """测试获取存在作业的状态"""
        job_uuid = "test-job-uuid"
        
        with patch.object(job_manager, '_get_job_info') as mock_get_info:
            mock_job_info = Mock()
            mock_job_info.to_dict.return_value = {
                "job_uuid": job_uuid,
                "status": "RUNNING",
                "progress": 0.5
            }
            mock_get_info.return_value = mock_job_info
            
            result = job_manager.get_job_status(job_uuid)
            
            assert result["success"] is True
            assert result["job_uuid"] == job_uuid
            assert result["status"] == "RUNNING"
            assert result["progress"] == 0.5

    def test_get_job_status_nonexistent(self, job_manager):
        """测试获取不存在作业的状态"""
        job_uuid = "nonexistent-job"
        
        with patch.object(job_manager, '_get_job_info') as mock_get_info:
            mock_get_info.return_value = None
            
            result = job_manager.get_job_status(job_uuid)
            
            assert result["success"] is False
            assert "not found" in result["message"].lower()

    def test_list_all_jobs(self, job_manager):
        """测试列出所有作业"""
        with patch.object(job_manager, '_get_all_job_infos') as mock_get_all:
            mock_jobs = [
                Mock(to_dict=Mock(return_value={"job_uuid": "job1", "status": "RUNNING"})),
                Mock(to_dict=Mock(return_value={"job_uuid": "job2", "status": "COMPLETED"})),
                Mock(to_dict=Mock(return_value={"job_uuid": "job3", "status": "FAILED"})),
            ]
            mock_get_all.return_value = mock_jobs
            
            result = job_manager.list_jobs()
            
            assert result["success"] is True
            assert len(result["jobs"]) == 3
            assert result["jobs"][0]["job_uuid"] == "job1"
            assert result["jobs"][1]["job_uuid"] == "job2"
            assert result["jobs"][2]["job_uuid"] == "job3"

    def test_list_jobs_by_status(self, job_manager):
        """测试按状态筛选作业"""
        with patch.object(job_manager, '_get_all_job_infos') as mock_get_all:
            mock_jobs = [
                Mock(to_dict=Mock(return_value={"job_uuid": "job1", "status": "RUNNING"})),
                Mock(to_dict=Mock(return_value={"job_uuid": "job2", "status": "COMPLETED"})),
                Mock(to_dict=Mock(return_value={"job_uuid": "job3", "status": "RUNNING"})),
            ]
            mock_get_all.return_value = mock_jobs
            
            result = job_manager.list_jobs(status_filter="RUNNING")
            
            assert result["success"] is True
            assert len(result["jobs"]) == 2
            for job in result["jobs"]:
                assert job["status"] == "RUNNING"


@pytest.mark.unit
class TestJobManagerLifecycle:
    """测试JobManager生命周期管理"""

    @pytest.fixture
    def job_manager(self, reset_jobmanager_singleton):
        """创建JobManager实例"""
        with patch('sage.kernel.kernels.jobmanager.job_manager.JobManagerServer'):
            return JobManager(enable_daemon=False)

    def test_start_daemon_server(self, job_manager):
        """测试启动守护进程服务器"""
        mock_server = Mock()
        job_manager.server = mock_server
        
        job_manager.start_daemon()
        
        mock_server.start.assert_called_once()

    def test_stop_daemon_server(self, job_manager):
        """测试停止守护进程服务器"""
        mock_server = Mock()
        job_manager.server = mock_server
        
        job_manager.stop_daemon()
        
        mock_server.stop.assert_called_once()

    def test_health_check(self, job_manager):
        """测试健康检查"""
        result = job_manager.health_check()
        
        assert result["status"] == "healthy"
        assert "uptime" in result
        assert "jobs_count" in result

    def test_get_server_info(self, job_manager):
        """测试获取服务器信息"""
        result = job_manager.get_server_info()
        
        assert "version" in result
        assert "daemon_host" in result
        assert "daemon_port" in result
        assert "enable_daemon" in result


@pytest.mark.integration
class TestJobManagerIntegration:
    """JobManager集成测试"""

    @pytest.fixture
    def job_manager(self, reset_jobmanager_singleton):
        """创建JobManager实例"""
        with patch('sage.kernel.kernels.jobmanager.job_manager.JobManagerServer'):
            return JobManager(enable_daemon=False)

    def test_full_job_lifecycle(self, job_manager):
        """测试完整的作业生命周期"""
        # 模拟环境
        mock_env = Mock()
        mock_env.name = "integration_test"
        mock_env.env_uuid = None
        
        with patch.object(job_manager, '_generate_job_uuid') as mock_gen_uuid, \
             patch.object(job_manager, '_create_job_info') as mock_create_info, \
             patch.object(job_manager, '_submit_to_dispatcher') as mock_submit, \
             patch.object(job_manager, '_get_job_info') as mock_get_info, \
             patch.object(job_manager, '_pause_job_execution') as mock_pause, \
             patch.object(job_manager, '_resume_job_execution') as mock_resume, \
             patch.object(job_manager, '_cancel_job_execution') as mock_cancel:
            
            # 设置模拟返回值
            test_uuid = "integration-test-uuid"
            mock_gen_uuid.return_value = test_uuid
            mock_job_info = Mock()
            mock_job_info.status = "RUNNING"
            mock_job_info.to_dict.return_value = {"job_uuid": test_uuid, "status": "RUNNING"}
            mock_create_info.return_value = mock_job_info
            mock_get_info.return_value = mock_job_info
            mock_submit.return_value = True
            mock_pause.return_value = True
            mock_resume.return_value = True
            mock_cancel.return_value = True
            
            # 1. 提交作业
            job_uuid = job_manager.submit_job(mock_env)
            assert job_uuid == test_uuid
            
            # 2. 查询状态
            status = job_manager.get_job_status(job_uuid)
            assert status["success"] is True
            assert status["status"] == "RUNNING"
            
            # 3. 暂停作业
            pause_result = job_manager.pause_job(job_uuid)
            assert pause_result["success"] is True
            
            # 4. 恢复作业
            resume_result = job_manager.resume_job(job_uuid)
            assert resume_result["success"] is True
            
            # 5. 取消作业
            cancel_result = job_manager.cancel_job(job_uuid)
            assert cancel_result["success"] is True

    def test_concurrent_job_submission(self, job_manager):
        """测试并发作业提交"""
        import concurrent.futures
        
        def submit_job(i):
            mock_env = Mock()
            mock_env.name = f"concurrent_job_{i}"
            mock_env.env_uuid = None
            return job_manager.submit_job(mock_env)
        
        with patch.object(job_manager, '_generate_job_uuid') as mock_gen_uuid, \
             patch.object(job_manager, '_create_job_info') as mock_create_info, \
             patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
            
            # 设置模拟返回值
            mock_gen_uuid.side_effect = [f"concurrent-uuid-{i}" for i in range(10)]
            mock_create_info.return_value = Mock()
            mock_submit.return_value = True
            
            # 并发提交10个作业
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(submit_job, i) for i in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            # 验证所有作业都成功提交
            assert len(results) == 10
            assert len(set(results)) == 10  # 所有UUID都不同


@pytest.mark.slow
class TestJobManagerPerformance:
    """JobManager性能测试"""

    @pytest.fixture
    def job_manager(self, reset_jobmanager_singleton):
        """创建JobManager实例"""
        with patch('sage.kernel.kernels.jobmanager.job_manager.JobManagerServer'):
            return JobManager(enable_daemon=False)

    def test_job_submission_performance(self, job_manager):
        """测试作业提交性能"""
        with patch.object(job_manager, '_generate_job_uuid') as mock_gen_uuid, \
             patch.object(job_manager, '_create_job_info') as mock_create_info, \
             patch.object(job_manager, '_submit_to_dispatcher') as mock_submit:
            
            mock_gen_uuid.side_effect = [f"perf-uuid-{i}" for i in range(1000)]
            mock_create_info.return_value = Mock()
            mock_submit.return_value = True
            
            # 测量1000个作业提交的时间
            start_time = time.time()
            
            for i in range(1000):
                mock_env = Mock()
                mock_env.name = f"perf_job_{i}"
                mock_env.env_uuid = None
                job_manager.submit_job(mock_env)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 验证性能要求：1000个作业提交应在10秒内完成
            assert duration < 10.0, f"Job submission took {duration:.2f}s, expected < 10s"
            
            # 计算吞吐量
            throughput = 1000 / duration
            assert throughput > 100, f"Throughput {throughput:.2f} jobs/s, expected > 100 jobs/s"

    def test_status_query_performance(self, job_manager):
        """测试状态查询性能"""
        job_uuid = "performance-test-job"
        
        with patch.object(job_manager, '_get_job_info') as mock_get_info:
            mock_job_info = Mock()
            mock_job_info.to_dict.return_value = {"job_uuid": job_uuid, "status": "RUNNING"}
            mock_get_info.return_value = mock_job_info
            
            # 测量1000次状态查询的时间
            start_time = time.time()
            
            for _ in range(1000):
                job_manager.get_job_status(job_uuid)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 验证性能要求：1000次查询应在5秒内完成
            assert duration < 5.0, f"Status queries took {duration:.2f}s, expected < 5s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

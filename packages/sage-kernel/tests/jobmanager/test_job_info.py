"""
JobInfo 作业信息管理测试
测试 JobInfo 类的所有功能，包括作业元数据管理、状态追踪、序列化等
"""
import pytest
import json
import time
from datetime import datetime
from unittest.mock import Mock, patch

from sage.jobmanager.job_info import JobInfo


@pytest.mark.unit
class TestJobInfoInitialization:
    """测试JobInfo初始化"""

    def test_basic_initialization(self):
        """测试基本初始化"""
        job_uuid = "test-job-uuid"
        environment = Mock()
        environment.name = "test_env"
        
        job_info = JobInfo(job_uuid=job_uuid, environment=environment)
        
        assert job_info.job_uuid == job_uuid
        assert job_info.environment is environment
        assert job_info.status == "SUBMITTED"
        assert job_info.progress == 0.0
        assert job_info.created_at is not None
        assert job_info.started_at is None
        assert job_info.completed_at is None

    def test_initialization_with_custom_status(self):
        """测试使用自定义状态初始化"""
        job_uuid = "test-job-uuid"
        environment = Mock()
        
        job_info = JobInfo(
            job_uuid=job_uuid,
            environment=environment,
            status="PENDING",
            progress=0.25
        )
        
        assert job_info.status == "PENDING"
        assert job_info.progress == 0.25

    def test_initialization_with_timestamps(self):
        """测试使用时间戳初始化"""
        job_uuid = "test-job-uuid"
        environment = Mock()
        created_time = datetime.now()
        started_time = datetime.now()
        
        job_info = JobInfo(
            job_uuid=job_uuid,
            environment=environment,
            created_at=created_time,
            started_at=started_time
        )
        
        assert job_info.created_at == created_time
        assert job_info.started_at == started_time

    def test_initialization_validation(self):
        """测试初始化参数验证"""
        environment = Mock()
        
        # 测试空UUID
        with pytest.raises(ValueError, match="Job UUID cannot be empty"):
            JobInfo(job_uuid="", environment=environment)
        
        # 测试None UUID
        with pytest.raises(ValueError, match="Job UUID cannot be None"):
            JobInfo(job_uuid=None, environment=environment)
        
        # 测试None环境
        with pytest.raises(ValueError, match="Environment cannot be None"):
            JobInfo(job_uuid="test-uuid", environment=None)

    def test_initialization_with_metadata(self):
        """测试使用元数据初始化"""
        job_uuid = "test-job-uuid"
        environment = Mock()
        metadata = {
            "priority": "high",
            "tags": ["ml", "training"],
            "owner": "user123"
        }
        
        job_info = JobInfo(
            job_uuid=job_uuid,
            environment=environment,
            metadata=metadata
        )
        
        assert job_info.metadata == metadata
        assert job_info.metadata["priority"] == "high"
        assert job_info.metadata["tags"] == ["ml", "training"]


@pytest.mark.unit
class TestJobInfoStatusManagement:
    """测试作业状态管理"""

    @pytest.fixture
    def job_info(self):
        """创建JobInfo实例"""
        environment = Mock()
        environment.name = "test_env"
        return JobInfo(job_uuid="test-uuid", environment=environment)

    def test_status_transitions(self, job_info):
        """测试状态转换"""
        # 初始状态
        assert job_info.status == "SUBMITTED"
        
        # 转换到PENDING
        job_info.update_status("PENDING")
        assert job_info.status == "PENDING"
        
        # 转换到RUNNING
        job_info.update_status("RUNNING")
        assert job_info.status == "RUNNING"
        assert job_info.started_at is not None
        
        # 转换到COMPLETED
        job_info.update_status("COMPLETED")
        assert job_info.status == "COMPLETED"
        assert job_info.completed_at is not None

    def test_invalid_status_transitions(self, job_info):
        """测试无效状态转换"""
        # 从SUBMITTED直接到COMPLETED（跳过RUNNING）
        with pytest.raises(ValueError, match="Invalid status transition"):
            job_info.update_status("COMPLETED")
        
        # 设置为RUNNING后再回到SUBMITTED
        job_info.update_status("RUNNING")
        with pytest.raises(ValueError, match="Invalid status transition"):
            job_info.update_status("SUBMITTED")

    def test_valid_status_values(self, job_info):
        """测试有效状态值"""
        valid_statuses = [
            "SUBMITTED", "PENDING", "RUNNING", 
            "COMPLETED", "FAILED", "CANCELLED", "PAUSED"
        ]
        
        for status in valid_statuses:
            # 重置到初始状态
            job_info.status = "SUBMITTED"
            job_info.started_at = None
            job_info.completed_at = None
            
            if status in ["RUNNING", "PAUSED"]:
                job_info.update_status("PENDING")
                job_info.update_status(status)
            elif status in ["COMPLETED", "FAILED", "CANCELLED"]:
                job_info.update_status("PENDING")
                job_info.update_status("RUNNING")
                job_info.update_status(status)
            else:
                job_info.update_status(status)
            
            assert job_info.status == status

    def test_invalid_status_values(self, job_info):
        """测试无效状态值"""
        invalid_statuses = ["INVALID", "", None, 123, []]
        
        for status in invalid_statuses:
            with pytest.raises(ValueError, match="Invalid status"):
                job_info.update_status(status)

    def test_status_history_tracking(self, job_info):
        """测试状态历史跟踪"""
        # 执行状态转换
        job_info.update_status("PENDING")
        job_info.update_status("RUNNING")
        job_info.update_status("COMPLETED")
        
        # 验证状态历史
        history = job_info.get_status_history()
        assert len(history) == 4  # 包括初始SUBMITTED状态
        assert history[0]["status"] == "SUBMITTED"
        assert history[1]["status"] == "PENDING"
        assert history[2]["status"] == "RUNNING"
        assert history[3]["status"] == "COMPLETED"
        
        # 验证时间戳
        for record in history:
            assert "timestamp" in record
            assert isinstance(record["timestamp"], datetime)

    def test_is_terminal_status(self, job_info):
        """测试终端状态判断"""
        # 非终端状态
        non_terminal_statuses = ["SUBMITTED", "PENDING", "RUNNING", "PAUSED"]
        for status in non_terminal_statuses:
            job_info.status = status
            assert not job_info.is_terminal_status()
        
        # 终端状态
        terminal_statuses = ["COMPLETED", "FAILED", "CANCELLED"]
        for status in terminal_statuses:
            job_info.status = status
            assert job_info.is_terminal_status()

    def test_is_active_status(self, job_info):
        """测试活跃状态判断"""
        # 活跃状态
        active_statuses = ["SUBMITTED", "PENDING", "RUNNING"]
        for status in active_statuses:
            job_info.status = status
            assert job_info.is_active_status()
        
        # 非活跃状态
        inactive_statuses = ["COMPLETED", "FAILED", "CANCELLED", "PAUSED"]
        for status in inactive_statuses:
            job_info.status = status
            assert not job_info.is_active_status()


@pytest.mark.unit
class TestJobInfoProgressTracking:
    """测试进度跟踪功能"""

    @pytest.fixture
    def job_info(self):
        """创建JobInfo实例"""
        environment = Mock()
        return JobInfo(job_uuid="test-uuid", environment=environment)

    def test_progress_update(self, job_info):
        """测试进度更新"""
        # 初始进度
        assert job_info.progress == 0.0
        
        # 更新进度
        job_info.update_progress(0.25)
        assert job_info.progress == 0.25
        
        job_info.update_progress(0.75)
        assert job_info.progress == 0.75
        
        job_info.update_progress(1.0)
        assert job_info.progress == 1.0

    def test_progress_validation(self, job_info):
        """测试进度验证"""
        # 负值
        with pytest.raises(ValueError, match="Progress must be between 0 and 1"):
            job_info.update_progress(-0.1)
        
        # 大于1的值
        with pytest.raises(ValueError, match="Progress must be between 0 and 1"):
            job_info.update_progress(1.1)
        
        # 非数值
        with pytest.raises(ValueError, match="Progress must be a number"):
            job_info.update_progress("50%")

    def test_progress_monotonicity(self, job_info):
        """测试进度单调性"""
        job_info.update_progress(0.5)
        
        # 进度不能倒退
        with pytest.raises(ValueError, match="Progress cannot go backwards"):
            job_info.update_progress(0.3)
        
        # 相同进度应该被允许
        job_info.update_progress(0.5)
        assert job_info.progress == 0.5

    def test_progress_completion_auto_status(self, job_info):
        """测试进度完成时自动状态更新"""
        job_info.update_status("RUNNING")
        
        # 当进度达到1.0时，应该自动更新状态为COMPLETED
        job_info.update_progress(1.0, auto_complete=True)
        assert job_info.progress == 1.0
        assert job_info.status == "COMPLETED"

    def test_progress_with_custom_message(self, job_info):
        """测试带自定义消息的进度更新"""
        message = "Processing data batch 1/4"
        job_info.update_progress(0.25, message=message)
        
        assert job_info.progress == 0.25
        assert job_info.progress_message == message

    def test_estimated_remaining_time(self, job_info):
        """测试预估剩余时间"""
        # 设置开始时间
        job_info.update_status("RUNNING")
        start_time = time.time()
        job_info.started_at = datetime.fromtimestamp(start_time)
        
        # 模拟进度
        time.sleep(0.1)  # 等待一小段时间
        job_info.update_progress(0.5)
        
        # 计算预估剩余时间
        estimated_time = job_info.get_estimated_remaining_time()
        assert estimated_time > 0
        assert estimated_time < 1.0  # 应该在合理范围内


@pytest.mark.unit
class TestJobInfoMetadataManagement:
    """测试元数据管理功能"""

    @pytest.fixture
    def job_info(self):
        """创建JobInfo实例"""
        environment = Mock()
        return JobInfo(job_uuid="test-uuid", environment=environment)

    def test_metadata_initialization(self, job_info):
        """测试元数据初始化"""
        assert job_info.metadata == {}

    def test_add_metadata(self, job_info):
        """测试添加元数据"""
        job_info.add_metadata("priority", "high")
        assert job_info.metadata["priority"] == "high"
        
        job_info.add_metadata("tags", ["ml", "training"])
        assert job_info.metadata["tags"] == ["ml", "training"]

    def test_update_metadata(self, job_info):
        """测试更新元数据"""
        job_info.add_metadata("priority", "low")
        job_info.update_metadata("priority", "high")
        assert job_info.metadata["priority"] == "high"

    def test_remove_metadata(self, job_info):
        """测试删除元数据"""
        job_info.add_metadata("temp_field", "temp_value")
        assert "temp_field" in job_info.metadata
        
        job_info.remove_metadata("temp_field")
        assert "temp_field" not in job_info.metadata

    def test_get_metadata(self, job_info):
        """测试获取元数据"""
        job_info.add_metadata("owner", "user123")
        
        assert job_info.get_metadata("owner") == "user123"
        assert job_info.get_metadata("nonexistent") is None
        assert job_info.get_metadata("nonexistent", "default") == "default"

    def test_bulk_metadata_operations(self, job_info):
        """测试批量元数据操作"""
        metadata_batch = {
            "priority": "high",
            "owner": "user123",
            "department": "engineering",
            "cost_center": "AI-ML"
        }
        
        job_info.update_metadata_batch(metadata_batch)
        
        for key, value in metadata_batch.items():
            assert job_info.metadata[key] == value

    def test_metadata_serialization(self, job_info):
        """测试元数据序列化"""
        complex_metadata = {
            "config": {"learning_rate": 0.01, "batch_size": 32},
            "tags": ["ml", "training", "production"],
            "created_by": "user123",
            "timestamps": {
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            }
        }
        
        job_info.metadata = complex_metadata
        
        # 测试转换为字典
        job_dict = job_info.to_dict()
        assert job_dict["metadata"] == complex_metadata


@pytest.mark.unit
class TestJobInfoSerialization:
    """测试序列化功能"""

    @pytest.fixture
    def job_info(self):
        """创建JobInfo实例"""
        environment = Mock()
        environment.name = "test_env"
        environment.description = "Test environment"
        
        job_info = JobInfo(job_uuid="test-uuid", environment=environment)
        job_info.update_status("RUNNING")
        job_info.update_progress(0.5)
        job_info.add_metadata("priority", "high")
        job_info.add_metadata("tags", ["ml", "training"])
        
        return job_info

    def test_to_dict_basic(self, job_info):
        """测试基本字典转换"""
        job_dict = job_info.to_dict()
        
        assert job_dict["job_uuid"] == "test-uuid"
        assert job_dict["status"] == "RUNNING"
        assert job_dict["progress"] == 0.5
        assert job_dict["metadata"]["priority"] == "high"
        assert "created_at" in job_dict
        assert "started_at" in job_dict

    def test_to_dict_include_environment(self, job_info):
        """测试包含环境信息的字典转换"""
        job_dict = job_info.to_dict(include_environment=True)
        
        assert "environment" in job_dict
        assert job_dict["environment"]["name"] == "test_env"

    def test_to_dict_exclude_environment(self, job_info):
        """测试排除环境信息的字典转换"""
        job_dict = job_info.to_dict(include_environment=False)
        
        assert "environment" not in job_dict

    def test_to_json(self, job_info):
        """测试JSON序列化"""
        json_str = job_info.to_json()
        
        # 验证是有效的JSON
        parsed = json.loads(json_str)
        assert parsed["job_uuid"] == "test-uuid"
        assert parsed["status"] == "RUNNING"
        assert parsed["progress"] == 0.5

    def test_from_dict(self):
        """测试从字典创建JobInfo"""
        environment = Mock()
        environment.name = "test_env"
        
        job_dict = {
            "job_uuid": "restored-uuid",
            "status": "RUNNING",
            "progress": 0.75,
            "metadata": {"priority": "high"},
            "created_at": datetime.now().isoformat(),
            "started_at": datetime.now().isoformat()
        }
        
        job_info = JobInfo.from_dict(job_dict, environment=environment)
        
        assert job_info.job_uuid == "restored-uuid"
        assert job_info.status == "RUNNING"
        assert job_info.progress == 0.75
        assert job_info.metadata["priority"] == "high"

    def test_from_json(self):
        """测试从JSON创建JobInfo"""
        environment = Mock()
        environment.name = "test_env"
        
        job_dict = {
            "job_uuid": "json-uuid",
            "status": "COMPLETED",
            "progress": 1.0,
            "metadata": {"tags": ["ml", "production"]}
        }
        
        json_str = json.dumps(job_dict)
        job_info = JobInfo.from_json(json_str, environment=environment)
        
        assert job_info.job_uuid == "json-uuid"
        assert job_info.status == "COMPLETED"
        assert job_info.progress == 1.0
        assert job_info.metadata["tags"] == ["ml", "production"]

    def test_serialization_roundtrip(self, job_info):
        """测试序列化往返"""
        # 转换为字典
        job_dict = job_info.to_dict(include_environment=False)
        
        # 从字典重建
        restored_job = JobInfo.from_dict(job_dict, environment=job_info.environment)
        
        # 验证所有关键字段
        assert restored_job.job_uuid == job_info.job_uuid
        assert restored_job.status == job_info.status
        assert restored_job.progress == job_info.progress
        assert restored_job.metadata == job_info.metadata

    def test_datetime_serialization(self, job_info):
        """测试日期时间序列化"""
        job_dict = job_info.to_dict()
        
        # 验证日期时间被正确序列化为ISO格式字符串
        assert isinstance(job_dict["created_at"], str)
        if job_dict["started_at"]:
            assert isinstance(job_dict["started_at"], str)
        
        # 验证可以解析为有效日期时间
        datetime.fromisoformat(job_dict["created_at"])
        if job_dict["started_at"]:
            datetime.fromisoformat(job_dict["started_at"])


@pytest.mark.unit
class TestJobInfoUtilities:
    """测试工具函数"""

    @pytest.fixture
    def job_info(self):
        """创建JobInfo实例"""
        environment = Mock()
        environment.name = "test_env"
        return JobInfo(job_uuid="test-uuid", environment=environment)

    def test_get_runtime_duration(self, job_info):
        """测试获取运行时长"""
        # 未开始的作业
        assert job_info.get_runtime_duration() is None
        
        # 已开始的作业
        job_info.update_status("RUNNING")
        time.sleep(0.1)
        
        runtime = job_info.get_runtime_duration()
        assert runtime > 0
        assert runtime < 1.0  # 应该在合理范围内

    def test_get_total_duration(self, job_info):
        """测试获取总时长"""
        # 未完成的作业
        job_info.update_status("RUNNING")
        assert job_info.get_total_duration() is None
        
        # 已完成的作业
        job_info.update_status("COMPLETED")
        
        total_duration = job_info.get_total_duration()
        assert total_duration > 0

    def test_get_environment_info(self, job_info):
        """测试获取环境信息"""
        job_info.environment.name = "production_env"
        job_info.environment.version = "1.2.3"
        
        env_info = job_info.get_environment_info()
        assert env_info["name"] == "production_env"
        assert env_info["version"] == "1.2.3"

    def test_is_timeout(self, job_info):
        """测试超时检查"""
        timeout_seconds = 1
        
        # 设置作业开始时间为过去
        job_info.update_status("RUNNING")
        job_info.started_at = datetime.fromtimestamp(time.time() - 2)
        
        assert job_info.is_timeout(timeout_seconds) is True
        assert job_info.is_timeout(10) is False

    def test_calculate_efficiency(self, job_info):
        """测试计算效率"""
        # 模拟已完成的作业
        job_info.update_status("RUNNING")
        job_info.started_at = datetime.fromtimestamp(time.time() - 100)
        job_info.update_status("COMPLETED")
        job_info.completed_at = datetime.fromtimestamp(time.time())
        
        # 设置预期运行时间
        expected_runtime = 50  # 秒
        efficiency = job_info.calculate_efficiency(expected_runtime)
        
        assert 0 < efficiency <= 1.0

    def test_get_summary(self, job_info):
        """测试获取摘要信息"""
        job_info.update_status("RUNNING")
        job_info.update_progress(0.75)
        job_info.add_metadata("priority", "high")
        
        summary = job_info.get_summary()
        
        assert summary["job_uuid"] == "test-uuid"
        assert summary["status"] == "RUNNING"
        assert summary["progress"] == 0.75
        assert summary["environment_name"] == "test_env"
        assert "runtime" in summary


@pytest.mark.integration
class TestJobInfoIntegration:
    """JobInfo集成测试"""

    def test_complete_job_lifecycle(self):
        """测试完整的作业生命周期"""
        environment = Mock()
        environment.name = "integration_test_env"
        
        # 创建作业
        job_info = JobInfo(job_uuid="lifecycle-test", environment=environment)
        assert job_info.status == "SUBMITTED"
        
        # 添加元数据
        job_info.add_metadata("owner", "integration_test")
        job_info.add_metadata("priority", "high")
        
        # 状态转换：SUBMITTED -> PENDING -> RUNNING
        job_info.update_status("PENDING")
        job_info.update_status("RUNNING")
        
        # 进度更新
        for progress in [0.25, 0.5, 0.75, 1.0]:
            job_info.update_progress(progress)
            time.sleep(0.01)  # 模拟处理时间
        
        # 完成作业
        job_info.update_status("COMPLETED")
        
        # 验证最终状态
        assert job_info.status == "COMPLETED"
        assert job_info.progress == 1.0
        assert job_info.is_terminal_status()
        assert not job_info.is_active_status()
        
        # 验证时间戳
        assert job_info.created_at is not None
        assert job_info.started_at is not None
        assert job_info.completed_at is not None
        
        # 验证持续时间计算
        total_duration = job_info.get_total_duration()
        assert total_duration > 0

    def test_error_handling_integration(self):
        """测试错误处理集成"""
        environment = Mock()
        job_info = JobInfo(job_uuid="error-test", environment=environment)
        
        # 正常流程开始
        job_info.update_status("RUNNING")
        job_info.update_progress(0.3)
        
        # 遇到错误
        error_info = {
            "error_type": "ProcessingError",
            "error_message": "Data validation failed",
            "error_timestamp": datetime.now().isoformat()
        }
        job_info.add_metadata("error_info", error_info)
        job_info.update_status("FAILED")
        
        # 验证错误状态
        assert job_info.status == "FAILED"
        assert job_info.is_terminal_status()
        assert job_info.metadata["error_info"]["error_type"] == "ProcessingError"

    def test_persistence_simulation(self):
        """测试持久化模拟"""
        environment = Mock()
        environment.name = "persistence_test"
        
        # 创建原始作业
        original_job = JobInfo(job_uuid="persistence-test", environment=environment)
        original_job.update_status("RUNNING")
        original_job.update_progress(0.6)
        original_job.add_metadata("checkpoint", "step_100")
        
        # 序列化
        job_data = original_job.to_dict(include_environment=False)
        
        # 模拟从持久化存储恢复
        restored_job = JobInfo.from_dict(job_data, environment=environment)
        
        # 验证恢复的作业
        assert restored_job.job_uuid == original_job.job_uuid
        assert restored_job.status == original_job.status
        assert restored_job.progress == original_job.progress
        assert restored_job.metadata == original_job.metadata
        
        # 继续处理恢复的作业
        restored_job.update_progress(0.8)
        restored_job.update_metadata("checkpoint", "step_150")
        restored_job.update_status("COMPLETED")
        
        assert restored_job.status == "COMPLETED"
        assert restored_job.progress == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

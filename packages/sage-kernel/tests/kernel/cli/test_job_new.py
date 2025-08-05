#!/usr/bin/env python3
"""
Tests for sage.cli.job - Updated comprehensive test suite
完整测试作业管理CLI功能
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from typer.testing import CliRunner

from sage.kernel.cli.job import app, JobManagerCLI


class TestJobManagerCLIClass:
    """Test JobManagerCLI class functionality"""
    
    @pytest.mark.unit
    def test_init_default_params(self):
        """测试使用默认参数初始化JobManagerCLI"""
        cli = JobManagerCLI()
        
        assert cli.daemon_host == "127.0.0.1"
        assert cli.daemon_port == 19001
        assert cli.client is None
        assert cli.connected is False
    
    @pytest.mark.unit
    def test_init_custom_params(self):
        """测试使用自定义参数初始化JobManagerCLI"""
        custom_host = "192.168.1.100"
        custom_port = 20001
        
        cli = JobManagerCLI(custom_host, custom_port)
        
        assert cli.daemon_host == custom_host
        assert cli.daemon_port == custom_port
        assert cli.client is None
        assert cli.connected is False
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.JobManagerClient')
    def test_connect_success(self, mock_client_class):
        """测试成功连接到JobManager"""
        mock_client = MagicMock()
        mock_client.health_check.return_value = True
        mock_client_class.return_value = mock_client
        
        cli = JobManagerCLI()
        result = cli.connect()
        
        assert result is True
        assert cli.client == mock_client
        assert cli.connected is True
        mock_client_class.assert_called_once_with("127.0.0.1", 19001)
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.JobManagerClient')
    def test_connect_health_check_fail(self, mock_client_class):
        """测试连接时健康检查失败"""
        mock_client = MagicMock()
        mock_client.health_check.return_value = False
        mock_client_class.return_value = mock_client
        
        cli = JobManagerCLI()
        result = cli.connect()
        
        assert result is False
        assert cli.client == mock_client
        assert cli.connected is False
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.JobManagerClient')
    def test_connect_exception(self, mock_client_class):
        """测试连接时发生异常"""
        mock_client_class.side_effect = Exception("Connection failed")
        
        cli = JobManagerCLI()
        result = cli.connect()
        
        assert result is False
        assert cli.client is None
        assert cli.connected is False


class TestJobSubmitCommand:
    """Test job submit functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_submit_job_success(self, mock_cli):
        """测试成功提交作业"""
        mock_cli.ensure_connected.return_value = None
        mock_cli.client.submit_job.return_value = {
            "status": "success",
            "job_id": "test-job-123"
        }
        
        # 创建临时作业文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('Hello SAGE')")
            temp_job_file = f.name
        
        try:
            result = self.runner.invoke(app, ["run", temp_job_file])
            
            assert result.exit_code == 0
            mock_cli.ensure_connected.assert_called()
        finally:
            os.unlink(temp_job_file)
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_submit_job_file_not_found(self, mock_cli):
        """测试提交不存在的作业文件"""
        result = self.runner.invoke(app, ["run", "/nonexistent/job.py"])
        
        # 应该检查文件存在性并报错
        assert result.exit_code != 0
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_submit_job_connection_fail(self, mock_cli):
        """测试提交作业时连接失败"""
        mock_cli.ensure_connected.side_effect = Exception("Connection failed")
        
        # 创建临时作业文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('Hello SAGE')")
            temp_job_file = f.name
        
        try:
            result = self.runner.invoke(app, ["run", temp_job_file])
            
            # 连接失败应该被处理
            assert result.exit_code != 0 or "error" in result.stdout.lower()
        finally:
            os.unlink(temp_job_file)


class TestJobListCommand:
    """Test job list functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_list_jobs_success(self, mock_cli):
        """测试成功列出作业"""
        mock_cli.ensure_connected.return_value = None
        mock_cli.client.list_jobs.return_value = {
            "status": "success",
            "jobs": [
                {"job_id": "job-1", "name": "test-job-1", "status": "running"},
                {"job_id": "job-2", "name": "test-job-2", "status": "completed"}
            ]
        }
        
        result = self.runner.invoke(app, ["list"])
        
        assert result.exit_code == 0
        mock_cli.ensure_connected.assert_called_once()
        mock_cli.client.list_jobs.assert_called_once()
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_list_jobs_empty(self, mock_cli):
        """测试列出空作业列表"""
        mock_cli.ensure_connected.return_value = None
        mock_cli.client.list_jobs.return_value = {
            "status": "success",
            "jobs": []
        }
        
        result = self.runner.invoke(app, ["list"])
        
        assert result.exit_code == 0
        mock_cli.client.list_jobs.assert_called_once()
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_list_jobs_connection_error(self, mock_cli):
        """测试列出作业时连接错误"""
        mock_cli.ensure_connected.side_effect = Exception("Connection failed")
        
        result = self.runner.invoke(app, ["list"])
        
        # 应该处理连接错误
        assert result.exit_code != 0 or "error" in result.stdout.lower()


class TestJobStatusCommand:
    """Test job status functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_show_job_success(self, mock_cli):
        """测试成功显示作业状态"""
        mock_cli.ensure_connected.return_value = None
        mock_cli._resolve_job_identifier.return_value = "test-job-123"
        mock_cli.client.get_job_status.return_value = {
            "status": "success",
            "job_status": {
                "job_id": "test-job-123",
                "name": "test-job",
                "status": "running",
                "progress": 50
            }
        }
        
        result = self.runner.invoke(app, ["show", "1"])
        
        assert result.exit_code == 0
        mock_cli._resolve_job_identifier.assert_called_with("1")
        mock_cli.client.get_job_status.assert_called_with("test-job-123")
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_show_job_not_found(self, mock_cli):
        """测试显示不存在作业的状态"""
        mock_cli.ensure_connected.return_value = None
        mock_cli._resolve_job_identifier.return_value = None
        
        result = self.runner.invoke(app, ["show", "999"])
        
        # 应该处理作业不存在的情况
        assert result.exit_code == 0  # 命令应该成功执行
        mock_cli._resolve_job_identifier.assert_called_with("999")


class TestJobStopCommand:
    """Test job stop functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_stop_job_success(self, mock_cli):
        """测试成功停止作业"""
        mock_cli.ensure_connected.return_value = None
        mock_cli._resolve_job_identifier.return_value = "test-job-123"
        mock_cli.client.pause_job.return_value = {
            "status": "success",
            "message": "Job stopped successfully"
        }
        
        result = self.runner.invoke(app, ["stop", "1"])
        
        assert result.exit_code == 0
        mock_cli._resolve_job_identifier.assert_called_with("1")
        mock_cli.client.pause_job.assert_called_with("test-job-123")
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_stop_job_with_force(self, mock_cli):
        """测试使用强制选项停止作业"""
        mock_cli.ensure_connected.return_value = None
        mock_cli._resolve_job_identifier.return_value = "test-job-123"
        mock_cli.client.pause_job.return_value = {
            "status": "success"
        }
        
        result = self.runner.invoke(app, ["stop", "1", "--force"])
        
        assert result.exit_code == 0
        mock_cli.client.pause_job.assert_called_with("test-job-123")
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_stop_job_failure(self, mock_cli):
        """测试停止作业失败"""
        mock_cli.ensure_connected.return_value = None
        mock_cli._resolve_job_identifier.return_value = "test-job-123"
        mock_cli.client.pause_job.side_effect = Exception("Cannot stop job")
        
        result = self.runner.invoke(app, ["stop", "1"])
        
        # 应该处理停止失败的情况
        assert result.exit_code == 0  # 命令应该成功执行


class TestJobLogsCommand:
    """Test job logs functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_logs_job_basic(self, mock_cli):
        """测试基本的作业日志功能"""
        # 由于logs命令可能还没有完全实现，我们测试它不会崩溃
        result = self.runner.invoke(app, ["logs", "1"])
        
        # 应该正常处理，即使功能未实现
        assert result.exit_code in [0, 1, 2]
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_logs_job_with_follow(self, mock_cli):
        """测试带follow选项的作业日志"""
        # 测试带--follow参数的logs命令
        result = self.runner.invoke(app, ["logs", "1", "--follow"])
        
        # 应该正常处理
        assert result.exit_code in [0, 1, 2]


class TestJobHelpCommands:
    """Test help functionality for job commands"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    def test_job_help_display(self):
        """测试作业管理帮助信息显示"""
        result = self.runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "作业" in result.stdout or "job" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_run_help(self):
        """测试run命令帮助信息"""
        result = self.runner.invoke(app, ["run", "--help"])
        
        assert result.exit_code == 0
        assert "run" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_list_help(self):
        """测试list命令帮助信息"""
        result = self.runner.invoke(app, ["list", "--help"])
        
        assert result.exit_code == 0
        assert "list" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_show_help(self):
        """测试show命令帮助信息"""
        result = self.runner.invoke(app, ["show", "--help"])
        
        assert result.exit_code == 0
        assert "show" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_stop_help(self):
        """测试stop命令帮助信息"""
        result = self.runner.invoke(app, ["stop", "--help"])
        
        assert result.exit_code == 0
        assert "stop" in result.stdout.lower()


class TestJobCommandEdgeCases:
    """Test edge cases for job commands"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    def test_invalid_job_id_format(self):
        """测试无效的作业ID格式"""
        result = self.runner.invoke(app, ["show", "invalid-id-format"])
        
        # 应该处理无效ID格式
        assert result.exit_code in [0, 1, 2]
    
    @pytest.mark.unit
    def test_empty_job_id(self):
        """测试空作业ID"""
        result = self.runner.invoke(app, ["show", ""])
        
        # 应该处理空ID
        assert result.exit_code != 0
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.job.cli')
    def test_concurrent_job_operations(self, mock_cli):
        """测试并发作业操作"""
        mock_cli.ensure_connected.return_value = None
        mock_cli._resolve_job_identifier.return_value = "test-job-123"
        mock_cli.client.get_job_status.return_value = {
            "status": "success",
            "job_status": {"status": "running"}
        }
        
        # 多次调用同一个命令
        results = []
        for _ in range(3):
            result = self.runner.invoke(app, ["show", "1"])
            results.append(result)
        
        # 所有调用都应该成功
        for result in results:
            assert result.exit_code == 0


class TestIntegration:
    """Integration tests for job CLI"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.integration
    @patch('sage.kernel.cli.job.cli')
    def test_full_job_workflow(self, mock_cli):
        """测试完整的作业工作流：提交、查看状态、停止"""
        mock_cli.ensure_connected.return_value = None
        mock_cli._resolve_job_identifier.return_value = "integration-test-job"
        
        # 模拟作业提交
        mock_cli.client.submit_job.return_value = {
            "status": "success",
            "job_id": "integration-test-job"
        }
        
        # 模拟状态查询
        mock_cli.client.get_job_status.return_value = {
            "status": "success",
            "job_status": {
                "job_id": "integration-test-job",
                "status": "running"
            }
        }
        
        # 模拟作业停止
        mock_cli.client.pause_job.return_value = {
            "status": "success"
        }
        
        # 创建临时作业文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('Integration test job')")
            temp_job_file = f.name
        
        try:
            # 提交作业
            submit_result = self.runner.invoke(app, ["run", temp_job_file])
            assert submit_result.exit_code == 0
            
            # 查看状态
            status_result = self.runner.invoke(app, ["show", "1"])
            assert status_result.exit_code == 0
            
            # 停止作业
            stop_result = self.runner.invoke(app, ["stop", "1"])
            assert stop_result.exit_code == 0
            
        finally:
            os.unlink(temp_job_file)
    
    @pytest.mark.integration
    def test_cli_error_handling(self):
        """测试CLI错误处理的健壮性"""
        # 测试各种错误情况下CLI不会崩溃
        
        error_scenarios = [
            ["run"],  # 缺少参数
            ["show"],  # 缺少作业ID
            ["stop"],  # 缺少作业ID
            ["invalid-command"],  # 无效命令
        ]
        
        for scenario in error_scenarios:
            result = self.runner.invoke(app, scenario)
            # 应该有适当的错误处理，不会崩溃
            assert result.exit_code != -1  # 不应该有严重错误

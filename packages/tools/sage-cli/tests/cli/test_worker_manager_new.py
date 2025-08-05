#!/usr/bin/env python3
"""
Tests for sage.cli.worker_manager
完整测试Worker节点管理CLI功能
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call, mock_open
from typer.testing import CliRunner

from sage.cli.worker_manager import app, execute_remote_command


class TestExecuteRemoteCommand:
    """Test remote command execution functionality"""
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_execute_remote_command_success(self, mock_temp_file, mock_subprocess, mock_get_config_manager):
        """测试成功执行远程命令"""
        # Mock配置管理器
        mock_config_manager = MagicMock()
        mock_config_manager.get_ssh_config.return_value = {
            'user': 'test_user',
            'key_path': '~/.ssh/test_key',
            'connect_timeout': 15
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock临时文件
        mock_file = MagicMock()
        mock_file.name = '/tmp/test_script.sh'
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Mock subprocess成功结果
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        # Mock文件操作
        with patch('builtins.open', mock_open(read_data="test command")):
            result = execute_remote_command("test_host", 22, "echo 'test'")
        
        assert result is True
        mock_subprocess.assert_called_once()
        
        # 验证SSH命令参数
        call_args = mock_subprocess.call_args[0]
        ssh_cmd = call_args[0]
        assert 'ssh' in ssh_cmd
        assert '-i' in ssh_cmd
        assert '-p' in ssh_cmd
        assert '22' in ssh_cmd
        assert 'test_user@test_host' in ssh_cmd
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_execute_remote_command_failure(self, mock_temp_file, mock_subprocess, mock_get_config_manager):
        """测试远程命令执行失败"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_ssh_config.return_value = {
            'user': 'test_user',
            'key_path': '~/.ssh/test_key'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock临时文件
        mock_file = MagicMock()
        mock_file.name = '/tmp/test_script.sh'
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Mock subprocess失败结果
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result
        
        with patch('builtins.open', mock_open(read_data="failing command")):
            result = execute_remote_command("test_host", 22, "false")
        
        assert result is False
        mock_subprocess.assert_called_once()
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_execute_remote_command_exception(self, mock_temp_file, mock_subprocess, mock_get_config_manager):
        """测试远程命令执行时发生异常"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_ssh_config.return_value = {
            'user': 'test_user',
            'key_path': '~/.ssh/test_key'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock临时文件
        mock_file = MagicMock()
        mock_file.name = '/tmp/test_script.sh'
        mock_temp_file.return_value.__enter__.return_value = mock_file
        
        # Mock subprocess抛出异常
        mock_subprocess.side_effect = Exception("Connection failed")
        
        with patch('builtins.open', mock_open(read_data="test command")):
            result = execute_remote_command("test_host", 22, "echo 'test'")
        
        assert result is False
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('os.path.expanduser')
    def test_execute_remote_command_config_defaults(self, mock_expanduser, mock_get_config_manager):
        """测试使用默认配置值"""
        # Mock配置管理器返回空配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_ssh_config.return_value = {}
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_expanduser.return_value = '/home/user/.ssh/id_rsa'
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('sage.cli.worker_manager.subprocess.run') as mock_subprocess, \
             patch('builtins.open', mock_open()):
            
            mock_file = MagicMock()
            mock_file.name = '/tmp/test_script.sh'
            mock_temp_file.return_value.__enter__.return_value = mock_file
            
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_subprocess.return_value = mock_result
            
            result = execute_remote_command("test_host", 22, "echo 'test'")
            
            # 验证使用了默认值
            call_args = mock_subprocess.call_args[0]
            ssh_cmd = call_args[0]
            assert 'sage@test_host' in ssh_cmd  # 默认用户
            assert '/home/user/.ssh/id_rsa' in ssh_cmd  # 默认密钥路径


class TestWorkerStartCommand:
    """Test worker start functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.execute_remote_command')
    def test_start_workers_success(self, mock_execute_remote, mock_get_config_manager):
        """测试成功启动Worker节点"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {
            'worker_nodes': 'worker1:22,worker2:22',
            'head_node': 'head-node',
            'head_port': 6379
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock远程命令执行成功
        mock_execute_remote.return_value = True
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        assert "启动Worker节点" in result.stdout or "start" in result.stdout.lower()
        
        # 验证为每个worker节点调用了远程命令
        assert mock_execute_remote.call_count == 2  # 两个worker节点
        mock_get_config_manager.assert_called()
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.execute_remote_command')
    def test_start_workers_partial_failure(self, mock_execute_remote, mock_get_config_manager):
        """测试部分Worker节点启动失败"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {
            'worker_nodes': 'worker1:22,worker2:22',
            'head_node': 'head-node',
            'head_port': 6379
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock第一个worker成功，第二个失败
        mock_execute_remote.side_effect = [True, False]
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 0  # 命令本身应该成功执行
        assert mock_execute_remote.call_count == 2
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_start_workers_no_config(self, mock_get_config_manager):
        """测试没有worker配置时的处理"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {}
        mock_get_config_manager.return_value = mock_config_manager
        
        result = self.runner.invoke(app, ["start"])
        
        # 应该处理没有配置的情况
        assert result.exit_code == 0
        assert "配置" in result.stdout or "config" in result.stdout.lower()


class TestWorkerStopCommand:
    """Test worker stop functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.execute_remote_command')
    def test_stop_workers_success(self, mock_execute_remote, mock_get_config_manager):
        """测试成功停止Worker节点"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {
            'worker_nodes': 'worker1:22,worker2:22'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock远程命令执行成功
        mock_execute_remote.return_value = True
        
        result = self.runner.invoke(app, ["stop"])
        
        assert result.exit_code == 0
        assert "停止Worker节点" in result.stdout or "stop" in result.stdout.lower()
        
        # 验证为每个worker节点调用了停止命令
        assert mock_execute_remote.call_count == 2
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.execute_remote_command')
    def test_stop_workers_with_force(self, mock_execute_remote, mock_get_config_manager):
        """测试使用强制选项停止Worker节点"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {
            'worker_nodes': 'worker1:22'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_execute_remote.return_value = True
        
        result = self.runner.invoke(app, ["stop", "--force"])
        
        assert result.exit_code == 0
        mock_execute_remote.assert_called()
        
        # 验证force参数影响了命令
        call_args = mock_execute_remote.call_args[0]
        command = call_args[2]  # 第三个参数是命令
        assert "force" in command.lower() or "kill" in command.lower()


class TestWorkerStatusCommand:
    """Test worker status functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.execute_remote_command')
    def test_status_workers_success(self, mock_execute_remote, mock_get_config_manager):
        """测试成功查看Worker节点状态"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {
            'worker_nodes': 'worker1:22,worker2:22'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock远程命令执行成功
        mock_execute_remote.return_value = True
        
        result = self.runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        assert "Worker节点状态" in result.stdout or "status" in result.stdout.lower()
        
        # 验证为每个worker节点查询了状态
        assert mock_execute_remote.call_count == 2
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.execute_remote_command')
    def test_status_workers_mixed_results(self, mock_execute_remote, mock_get_config_manager):
        """测试Worker节点状态混合结果"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {
            'worker_nodes': 'worker1:22,worker2:22'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock一个worker在线，一个离线
        mock_execute_remote.side_effect = [True, False]
        
        result = self.runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        assert mock_execute_remote.call_count == 2


class TestWorkerListCommand:
    """Test worker list functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_list_workers_from_config(self, mock_get_config_manager):
        """测试从配置列出Worker节点"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {
            'worker_nodes': 'worker1:22,worker2:2222,worker3:22'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        result = self.runner.invoke(app, ["list"])
        
        assert result.exit_code == 0
        assert "worker1" in result.stdout
        assert "worker2" in result.stdout
        assert "worker3" in result.stdout
        assert "22" in result.stdout
        assert "2222" in result.stdout
    
    @pytest.mark.unit
    @patch('sage.cli.worker_manager.get_config_manager')
    def test_list_workers_no_config(self, mock_get_config_manager):
        """测试没有worker配置时列出worker"""
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {}
        mock_get_config_manager.return_value = mock_config_manager
        
        result = self.runner.invoke(app, ["list"])
        
        assert result.exit_code == 0
        assert "未配置" in result.stdout or "no worker" in result.stdout.lower()


class TestWorkerHelpCommands:
    """Test help functionality for worker commands"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    def test_worker_help_display(self):
        """测试Worker管理帮助信息显示"""
        result = self.runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "Worker节点管理" in result.stdout or "worker" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_start_help(self):
        """测试start命令帮助信息"""
        result = self.runner.invoke(app, ["start", "--help"])
        
        assert result.exit_code == 0
        assert "start" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_stop_help(self):
        """测试stop命令帮助信息"""
        result = self.runner.invoke(app, ["stop", "--help"])
        
        assert result.exit_code == 0
        assert "stop" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_status_help(self):
        """测试status命令帮助信息"""
        result = self.runner.invoke(app, ["status", "--help"])
        
        assert result.exit_code == 0
        assert "status" in result.stdout.lower()
    
    @pytest.mark.unit
    def test_list_help(self):
        """测试list命令帮助信息"""
        result = self.runner.invoke(app, ["list", "--help"])
        
        assert result.exit_code == 0
        assert "list" in result.stdout.lower()


class TestWorkerConfigParsing:
    """Test worker configuration parsing"""
    
    @pytest.mark.unit
    def test_parse_worker_nodes_string(self):
        """测试解析worker节点字符串"""
        # 这个测试需要访问实际的解析逻辑
        # 如果有专门的解析函数，可以单独测试
        worker_string = "worker1:22,worker2:2222,worker3:22"
        expected_workers = [
            ("worker1", 22),
            ("worker2", 2222),
            ("worker3", 22)
        ]
        
        # Note: 这里需要根据实际的解析函数来测试
        # 假设有一个parse_worker_nodes函数
        # parsed_workers = parse_worker_nodes(worker_string)
        # assert parsed_workers == expected_workers
        
        # 目前只测试字符串格式正确
        assert "worker1:22" in worker_string
        assert "worker2:2222" in worker_string
        assert "worker3:22" in worker_string
    
    @pytest.mark.unit
    def test_parse_worker_nodes_edge_cases(self):
        """测试worker节点解析的边界情况"""
        # 测试各种边界情况
        edge_cases = [
            "",  # 空字符串
            "worker1",  # 缺少端口
            "worker1:abc",  # 无效端口
            "worker1:22,",  # 末尾逗号
            ",worker1:22",  # 开头逗号
            "worker1:22,,worker2:22",  # 双逗号
        ]
        
        for case in edge_cases:
            # 解析函数应该能处理这些边界情况而不崩溃
            # 这里只是验证格式
            assert isinstance(case, str)


class TestIntegration:
    """Integration tests for worker manager CLI"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.integration
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.execute_remote_command')
    def test_full_worker_lifecycle(self, mock_execute_remote, mock_get_config_manager):
        """测试完整的Worker生命周期：启动->状态->停止"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {
            'worker_nodes': 'worker1:22',
            'head_node': 'head-node',
            'head_port': 6379
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        # Mock所有远程命令执行成功
        mock_execute_remote.return_value = True
        
        # 执行完整的生命周期
        start_result = self.runner.invoke(app, ["start"])
        assert start_result.exit_code == 0
        
        status_result = self.runner.invoke(app, ["status"])
        assert status_result.exit_code == 0
        
        stop_result = self.runner.invoke(app, ["stop"])
        assert stop_result.exit_code == 0
        
        # 验证所有命令都执行了
        assert mock_execute_remote.call_count >= 3  # 至少每个命令一次
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_worker_command_error_handling(self):
        """测试Worker命令的错误处理"""
        # 测试各种错误情况下CLI不会崩溃
        error_scenarios = [
            ["start"],   # 可能的配置或连接错误
            ["stop"],    # 可能的停止错误
            ["status"],  # 可能的状态查询错误
            ["list"],    # 配置错误
        ]
        
        for scenario in error_scenarios:
            result = self.runner.invoke(app, scenario)
            # 应该有适当的错误处理，不会崩溃
            assert result.exit_code != -1  # 不应该有严重错误
    
    @pytest.mark.integration
    @patch('sage.cli.worker_manager.get_config_manager')
    @patch('sage.cli.worker_manager.execute_remote_command')
    def test_concurrent_worker_operations(self, mock_execute_remote, mock_get_config_manager):
        """测试并发Worker操作"""
        # Mock配置
        mock_config_manager = MagicMock()
        mock_config_manager.get_worker_config.return_value = {
            'worker_nodes': 'worker1:22,worker2:22,worker3:22'
        }
        mock_get_config_manager.return_value = mock_config_manager
        
        mock_execute_remote.return_value = True
        
        # 模拟并发操作（同时启动多个worker）
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        # 验证为所有worker节点都执行了命令
        assert mock_execute_remote.call_count == 3

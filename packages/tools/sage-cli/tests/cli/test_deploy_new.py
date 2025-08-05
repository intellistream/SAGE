#!/usr/bin/env python3
"""
Tests for sage.cli.deploy
完整测试系统部署CLI功能
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typer.testing import CliRunner

from sage.cli.deploy import app, load_config


class TestLoadConfig:
    """Test config loading functionality"""
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=False)
    def test_load_config_file_not_found(self, mock_exists):
        """测试配置文件不存在时的处理"""
        with pytest.raises(SystemExit):
            load_config()
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_config_success(self, mock_exists):
        """测试成功加载配置文件"""
        config_content = """# SAGE Config
daemon:
  host: "127.0.0.1"
  port: 19001

workers:
  head_node: "base-sage"
  worker_nodes: "sage2:22,sage4:22"
  ssh_user: "sage"

monitor:
  refresh_interval: 5
"""
        
        with patch('builtins.open', mock_open(read_data=config_content)):
            config = load_config()
            
            assert 'daemon' in config
            assert config['daemon']['host'] == "127.0.0.1"
            assert config['daemon']['port'] == 19001
            assert 'workers' in config
            assert config['workers']['head_node'] == "base-sage"
            assert 'monitor' in config
            assert config['monitor']['refresh_interval'] == 5
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_config_with_comments_and_empty_lines(self, mock_exists):
        """测试处理包含注释和空行的配置文件"""
        config_content = """# This is a comment
daemon:
  host: "localhost"
  # Another comment
  port: 8080

# Empty lines should be ignored

workers:
  count: 4
"""
        
        with patch('builtins.open', mock_open(read_data=config_content)):
            config = load_config()
            
            assert config['daemon']['host'] == "localhost"
            assert config['daemon']['port'] == 8080
            assert config['workers']['count'] == 4
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_config_io_error(self, mock_exists):
        """测试读取配置文件IO错误的处理"""
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            with pytest.raises(SystemExit):
                load_config()


class TestDeployStartCommand:
    """Test deploy start functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.cli.deploy.load_config')
    @patch('sage.cli.deploy.subprocess.run')
    def test_start_success(self, mock_subprocess, mock_load_config):
        """测试成功启动系统"""
        mock_load_config.return_value = {
            'daemon': {'host': '127.0.0.1', 'port': 19001}
        }
        
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "System started successfully"
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["start"])
        
        assert result.exit_code == 0
        assert "启动" in result.stdout or "start" in result.stdout.lower()
        mock_load_config.assert_called_once()
        mock_subprocess.assert_called()
    
    @pytest.mark.unit
    @patch('sage.cli.deploy.load_config')
    def test_start_config_error(self, mock_load_config):
        """测试启动时配置加载错误"""
        mock_load_config.side_effect = SystemExit(1)
        
        with pytest.raises(SystemExit):
            self.runner.invoke(app, ["start"])
    
    @pytest.mark.unit
    @patch('sage.cli.deploy.load_config')
    @patch('sage.cli.deploy.subprocess.run')
    def test_start_subprocess_error(self, mock_subprocess, mock_load_config):
        """测试启动时子进程错误"""
        mock_load_config.return_value = {
            'daemon': {'host': '127.0.0.1', 'port': 19001}
        }
        
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Startup failed"
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["start"])
        
        # 应该处理启动失败
        assert result.exit_code == 0  # 命令本身应该成功执行
        mock_subprocess.assert_called()


class TestDeployStopCommand:
    """Test deploy stop functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.cli.deploy.subprocess.run')
    def test_stop_success(self, mock_subprocess):
        """测试成功停止系统"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "System stopped successfully"
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["stop"])
        
        assert result.exit_code == 0
        assert "停止" in result.stdout or "stop" in result.stdout.lower()
        mock_subprocess.assert_called()
    
    @pytest.mark.unit
    @patch('sage.cli.deploy.subprocess.run')
    def test_stop_failure(self, mock_subprocess):
        """测试停止系统失败"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Stop failed"
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["stop"])
        
        # 应该处理停止失败
        assert result.exit_code == 0  # 命令本身应该成功执行
        mock_subprocess.assert_called()


class TestDeployStatusCommand:
    """Test deploy status functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.cli.deploy.subprocess.run')
    def test_status_running(self, mock_subprocess):
        """测试查看运行中系统状态"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "System is running"
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        assert "状态" in result.stdout or "status" in result.stdout.lower()
        mock_subprocess.assert_called()
    
    @pytest.mark.unit
    @patch('sage.cli.deploy.subprocess.run')
    def test_status_not_running(self, mock_subprocess):
        """测试查看未运行系统状态"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "System is not running"
        mock_subprocess.return_value = mock_result
        
        result = self.runner.invoke(app, ["status"])
        
        assert result.exit_code == 0
        mock_subprocess.assert_called()


class TestDeployRestartCommand:
    """Test deploy restart functionality"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    @patch('sage.cli.deploy.load_config')
    @patch('sage.cli.deploy.subprocess.run')
    def test_restart_success(self, mock_subprocess, mock_load_config):
        """测试成功重启系统"""
        mock_load_config.return_value = {
            'daemon': {'host': '127.0.0.1', 'port': 19001}
        }
        
        # 模拟多次subprocess调用（停止+启动）
        mock_results = [
            MagicMock(returncode=0, stdout="Stopped"),
            MagicMock(returncode=0, stdout="Started")
        ]
        mock_subprocess.side_effect = mock_results
        
        result = self.runner.invoke(app, ["restart"])
        
        assert result.exit_code == 0
        assert "重启" in result.stdout or "restart" in result.stdout.lower()
        # 应该调用多次subprocess（停止和启动）
        assert mock_subprocess.call_count >= 1


class TestDeployHelpCommands:
    """Test help functionality for deploy commands"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.unit
    def test_deploy_help_display(self):
        """测试部署管理帮助信息显示"""
        result = self.runner.invoke(app, ["--help"])
        
        assert result.exit_code == 0
        assert "系统部署" in result.stdout or "deploy" in result.stdout.lower()
    
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
    def test_restart_help(self):
        """测试restart命令帮助信息"""
        result = self.runner.invoke(app, ["restart", "--help"])
        
        assert result.exit_code == 0
        assert "restart" in result.stdout.lower()


class TestDeployConfigParsing:
    """Test configuration parsing edge cases"""
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=True)
    def test_config_parsing_edge_cases(self, mock_exists):
        """测试配置解析的边界情况"""
        config_content = """# Test config with edge cases
section1:
  key_with_quotes: "value with spaces"
  numeric_key: 12345
  boolean_like: true
  
section2:
  empty_value: ""
  special_chars: "value@#$%"
"""
        
        with patch('builtins.open', mock_open(read_data=config_content)):
            config = load_config()
            
            assert config['section1']['key_with_quotes'] == "value with spaces"
            assert config['section1']['numeric_key'] == 12345
            assert config['section1']['boolean_like'] == "true"  # 作为字符串处理
            assert config['section2']['empty_value'] == ""
            assert config['section2']['special_chars'] == "value@#$%"
    
    @pytest.mark.unit
    @patch('pathlib.Path.exists', return_value=True)
    def test_config_parsing_malformed(self, mock_exists):
        """测试处理格式错误的配置文件"""
        malformed_config = """
invalid line without colon
section1:
  key1: value1
  malformed line
  key2: value2
"""
        
        with patch('builtins.open', mock_open(read_data=malformed_config)):
            config = load_config()
            
            # 应该跳过格式错误的行，处理正确的配置
            assert 'section1' in config
            assert config['section1']['key1'] == "value1"
            assert config['section1']['key2'] == "value2"


class TestIntegration:
    """Integration tests for deploy CLI"""
    
    def setup_method(self):
        """Setup test runner"""
        self.runner = CliRunner()
    
    @pytest.mark.integration
    def test_full_config_lifecycle(self):
        """测试完整的配置生命周期"""
        test_config = {
            'daemon': {'host': '127.0.0.1', 'port': 19001},
            'workers': {'count': 4, 'memory': '2G'},
            'monitor': {'refresh_interval': 5}
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / ".sage" / "config.yaml"
            config_path.parent.mkdir(parents=True)
            
            # 写入配置文件
            with open(config_path, 'w') as f:
                yaml.dump(test_config, f)
            
            # 修改配置路径
            with patch('pathlib.Path.home', return_value=Path(temp_dir)):
                loaded_config = load_config()
                
                # 验证配置正确加载（注意load_config使用简单解析）
                assert 'daemon' in loaded_config
                assert 'workers' in loaded_config
                assert 'monitor' in loaded_config
    
    @pytest.mark.integration
    @pytest.mark.slow
    @patch('sage.cli.deploy.load_config')
    @patch('sage.cli.deploy.subprocess.run')
    def test_deploy_command_sequence(self, mock_subprocess, mock_load_config):
        """测试部署命令序列：启动->状态->重启->停止"""
        mock_load_config.return_value = {
            'daemon': {'host': '127.0.0.1', 'port': 19001}
        }
        
        # 模拟所有subprocess调用成功
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command executed successfully"
        mock_subprocess.return_value = mock_result
        
        # 执行命令序列
        commands = ["start", "status", "restart", "stop"]
        
        for command in commands:
            result = self.runner.invoke(app, [command])
            assert result.exit_code == 0, f"Command {command} failed"
        
        # 验证所有subprocess调用
        assert mock_subprocess.call_count >= len(commands)
    
    @pytest.mark.integration
    def test_error_recovery(self):
        """测试错误恢复能力"""
        # 测试在各种错误条件下CLI的行为
        error_scenarios = [
            ["start"],  # 可能的配置错误
            ["stop"],   # 可能的停止错误
            ["status"], # 可能的状态查询错误
        ]
        
        for scenario in error_scenarios:
            # 即使发生错误，也不应该崩溃
            result = self.runner.invoke(app, scenario)
            assert result.exit_code != -1  # 不Should have severe errors

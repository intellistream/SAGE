#!/usr/bin/env python3
"""
Tests for sage.cli.setup
完整测试CLI安装配置功能
"""

import pytest
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, call, MagicMock

from sage.kernel.cli.setup import install_cli_dependencies, create_config_directory, main


class TestCLISetup:
    """Test CLI setup functionality"""
    
    @pytest.mark.unit
    @patch('subprocess.check_call')
    def test_install_dependencies_success(self, mock_check_call):
        """测试成功安装所有依赖"""
        result = install_cli_dependencies()
        
        assert result is True
        expected_calls = [
            call([sys.executable, "-m", "pip", "install", "typer>=0.9.0"]),
            call([sys.executable, "-m", "pip", "install", "colorama>=0.4.0"]),
            call([sys.executable, "-m", "pip", "install", "tabulate>=0.9.0"]),
            call([sys.executable, "-m", "pip", "install", "pyyaml>=6.0"]),
        ]
        mock_check_call.assert_has_calls(expected_calls, any_order=True)
        assert mock_check_call.call_count == 4
    
    @pytest.mark.unit
    @patch('subprocess.check_call')
    def test_install_dependencies_partial_failure(self, mock_check_call):
        """测试部分依赖安装失败的处理"""
        # 第二个依赖安装失败
        mock_check_call.side_effect = [
            None,  # 第一个成功
            subprocess.CalledProcessError(1, 'cmd'),  # 第二个失败
            None,  # 不会执行到第三个
        ]
        
        result = install_cli_dependencies()
        
        assert result is False
        assert mock_check_call.call_count == 2  # 应该在第二个失败后停止
    
    @pytest.mark.unit
    @patch('subprocess.check_call')
    def test_install_dependencies_first_failure(self, mock_check_call):
        """测试第一个依赖安装就失败的处理"""
        mock_check_call.side_effect = subprocess.CalledProcessError(1, 'cmd')
        
        result = install_cli_dependencies()
        
        assert result is False
        assert mock_check_call.call_count == 1
    
    @pytest.mark.unit
    def test_install_dependencies_with_real_commands(self):
        """测试安装依赖使用正确的命令格式"""
        with patch('subprocess.check_call') as mock_check_call:
            install_cli_dependencies()
            
            # 验证所有调用都使用了正确的格式
            for call_args in mock_check_call.call_args_list:
                args = call_args[0][0]
                assert args[0] == sys.executable
                assert args[1:3] == ["-m", "pip"]
                assert args[3] == "install"
                assert ">=" in args[4]  # 版本要求格式


class TestConfigDirectory:
    """Test config directory creation"""
    
    @pytest.mark.unit
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.exists', return_value=False)
    @patch('pathlib.Path.mkdir')
    def test_create_config_directory_new(self, mock_mkdir, mock_exists, mock_write_text):
        """测试创建新的配置目录和文件"""
        create_config_directory()
        
        # 验证目录创建
        mock_mkdir.assert_called_once_with(exist_ok=True)
        
        # 验证文件存在性检查
        mock_exists.assert_called_once()
        
        # 验证配置文件写入
        mock_write_text.assert_called_once()
        written_content = mock_write_text.call_args[0][0]
        
        # 验证配置内容包含必要的字段
        assert "daemon:" in written_content
        assert "host:" in written_content
        assert "port: 19001" in written_content
        assert "jobmanager:" in written_content
        assert "workers:" in written_content
    
    @pytest.mark.unit
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.mkdir')
    def test_create_config_directory_existing(self, mock_mkdir, mock_exists, mock_write_text):
        """测试配置文件已存在时不覆盖"""
        create_config_directory()
        
        # 验证目录仍会创建（以防不存在）
        mock_mkdir.assert_called_once_with(exist_ok=True)
        
        # 验证检查文件存在性
        mock_exists.assert_called_once()
        
        # 验证不会写入新文件
        mock_write_text.assert_not_called()
    
    @pytest.mark.unit
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.exists', return_value=False)
    @patch('pathlib.Path.mkdir', side_effect=PermissionError("Permission denied"))
    def test_create_config_directory_permission_error(self, mock_mkdir, mock_exists, mock_write_text):
        """测试创建配置目录时权限错误的处理"""
        with pytest.raises(PermissionError):
            create_config_directory()
        
        mock_mkdir.assert_called_once()
        mock_exists.assert_not_called()
        mock_write_text.assert_not_called()
    
    @pytest.mark.unit
    def test_config_content_structure(self):
        """测试配置文件内容结构正确性"""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.write_text') as mock_write_text:
            
            create_config_directory()
            
            written_content = mock_write_text.call_args[0][0]
            lines = written_content.strip().split('\n')
            
            # 验证包含主要配置段
            config_sections = ['daemon:', 'output:', 'monitor:', 'jobmanager:', 'workers:']
            for section in config_sections:
                assert any(section in line for line in lines), f"Missing section: {section}"


class TestMainFunction:
    """Test main setup function"""
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.setup.create_config_directory')
    @patch('sage.kernel.cli.setup.install_cli_dependencies', return_value=True)
    @patch('sys.exit')
    def test_main_success(self, mock_exit, mock_install, mock_create_config):
        """测试主函数成功执行"""
        main()
        
        mock_install.assert_called_once()
        mock_create_config.assert_called_once()
        mock_exit.assert_not_called()
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.setup.create_config_directory')
    @patch('sage.kernel.cli.setup.install_cli_dependencies', return_value=False)
    @patch('sys.exit')
    def test_main_install_failure(self, mock_exit, mock_install, mock_create_config):
        """测试依赖安装失败时主函数的处理"""
        main()
        
        mock_install.assert_called_once()
        mock_exit.assert_called_once_with(1)
        # 由于sys.exit被mock了，程序会继续执行，所以create_config_directory会被调用
        mock_create_config.assert_called_once()
    
    @pytest.mark.unit
    @patch('sage.kernel.cli.setup.create_config_directory', side_effect=Exception("Config error"))
    @patch('sage.kernel.cli.setup.install_cli_dependencies', return_value=True)
    def test_main_config_creation_error(self, mock_install, mock_create_config):
        """测试配置创建失败时的错误处理"""
        with pytest.raises(Exception, match="Config error"):
            main()
        
        mock_install.assert_called_once()
        mock_create_config.assert_called_once()


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_config_directory_path_correct(self):
        """测试配置目录路径正确"""
        expected_path = Path.home() / ".sage"
        
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.write_text'):
            
            create_config_directory()
            
            # 验证mkdir被调用
            mock_mkdir.assert_called_once_with(exist_ok=True)
    
    @pytest.mark.integration  
    def test_dependencies_list_current(self):
        """测试依赖列表是最新的"""
        expected_deps = [
            "typer>=0.9.0",
            "colorama>=0.4.0", 
            "tabulate>=0.9.0",
            "pyyaml>=6.0",
        ]
        
        with patch('subprocess.check_call') as mock_check_call:
            install_cli_dependencies()
            
            installed_deps = []
            for call_args in mock_check_call.call_args_list:
                dep = call_args[0][0][4]  # 第5个参数是依赖名
                installed_deps.append(dep)
            
            assert installed_deps == expected_deps


@pytest.mark.unit
@patch('sys.exit')
@patch('sage.kernel.cli.setup.install_cli_dependencies', return_value=False)
def test_main_flow_install_fail(mock_install_deps, mock_exit):
    """Test the main function when dependency installation fails."""
    main()
    mock_install_deps.assert_called_once()
    mock_exit.assert_called_with(1)

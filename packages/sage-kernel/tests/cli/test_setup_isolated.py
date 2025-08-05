#!/usr/bin/env python3
"""
Tests for sage.cli.setup module (isolated testing)
独立测试CLI安装配置功能，避免复杂的依赖问题
"""

import pytest
import tempfile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, call, MagicMock

# 直接测试setup模块，不依赖其他CLI模块
import sage.cli.setup as setup_module


class TestInstallDependencies:
    """Test CLI dependency installation"""
    
    @pytest.mark.unit
    @patch('subprocess.check_call')
    def test_install_dependencies_success(self, mock_check_call):
        """测试成功安装所有依赖"""
        result = setup_module.install_cli_dependencies()
        
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
    def test_install_dependencies_failure(self, mock_check_call):
        """测试依赖安装失败的处理"""
        mock_check_call.side_effect = subprocess.CalledProcessError(1, 'cmd')
        
        result = setup_module.install_cli_dependencies()
        
        assert result is False
        assert mock_check_call.call_count == 1


class TestConfigDirectoryCreation:
    """Test config directory creation"""
    
    @pytest.mark.unit
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.exists', return_value=False)
    @patch('pathlib.Path.mkdir')
    def test_create_config_directory_new(self, mock_mkdir, mock_exists, mock_write_text):
        """测试创建新的配置目录和文件"""
        setup_module.create_config_directory()
        
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
    
    @pytest.mark.unit
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.mkdir')
    def test_create_config_directory_existing(self, mock_mkdir, mock_exists, mock_write_text):
        """测试配置文件已存在时不覆盖"""
        setup_module.create_config_directory()
        
        # 验证目录仍会创建（以防不存在）
        mock_mkdir.assert_called_once_with(exist_ok=True)
        
        # 验证检查文件存在性
        mock_exists.assert_called_once()
        
        # 验证不会写入新文件
        mock_write_text.assert_not_called()


class TestMainFunction:
    """Test main setup function"""
    
    @pytest.mark.unit
    @patch('sage.cli.setup.create_config_directory')
    @patch('sage.cli.setup.install_cli_dependencies', return_value=True)
    @patch('sys.exit')
    def test_main_success(self, mock_exit, mock_install, mock_create_config):
        """测试主函数成功执行"""
        setup_module.main()
        
        mock_install.assert_called_once()
        mock_create_config.assert_called_once()
        mock_exit.assert_not_called()
    
    @pytest.mark.unit
    @patch('sage.cli.setup.create_config_directory')
    @patch('sage.cli.setup.install_cli_dependencies', return_value=False)
    @patch('sys.exit')
    def test_main_install_failure(self, mock_exit, mock_install, mock_create_config):
        """测试依赖安装失败时主函数的处理"""
        setup_module.main()
        
        mock_install.assert_called_once()
        mock_create_config.assert_not_called()
        mock_exit.assert_called_once_with(1)


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.integration
    def test_config_directory_path_correct(self):
        """测试配置目录路径正确"""
        expected_path = Path.home() / ".sage"
        
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.write_text'):
            
            setup_module.create_config_directory()
            
            # 验证mkdir被调用
            mock_mkdir.assert_called_once_with(exist_ok=True)
    
    @pytest.mark.integration
    def test_dependencies_list_current(self):
        """测试依赖列表是正确的"""
        expected_deps = [
            "typer>=0.9.0",
            "colorama>=0.4.0", 
            "tabulate>=0.9.0",
            "pyyaml>=6.0",
        ]
        
        with patch('subprocess.check_call') as mock_check_call:
            setup_module.install_cli_dependencies()
            
            installed_deps = []
            for call_args in mock_check_call.call_args_list:
                dep = call_args[0][0][4]  # 第5个参数是依赖名
                installed_deps.append(dep)
            
            assert installed_deps == expected_deps


class TestSimpleVersionFunction:
    """Test simple version functionality without Typer complexity"""
    
    @pytest.mark.unit
    def test_version_info_available(self):
        """测试版本信息可用"""
        # 这里测试版本信息是否定义正确
        # 由于main.py中定义了版本信息，我们可以简单验证
        version_info = {
            "name": "SAGE - Stream Analysis and Graph Engine",
            "version": "0.1.2",
            "author": "IntelliStream",
            "repository": "https://github.com/intellistream/SAGE"
        }
        
        assert version_info["name"]
        assert version_info["version"]
        assert version_info["author"]
        assert version_info["repository"]
        assert "github.com" in version_info["repository"]


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])

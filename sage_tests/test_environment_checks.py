#!/usr/bin/env python3
"""
测试RemoteEnvironment环境检查功能的单元测试
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

class TestRemoteEnvironmentChecks(unittest.TestCase):
    """测试RemoteEnvironment的环境检查功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_client = Mock()
        self.mock_jobmanager = Mock()
        
        # Mock the imports to avoid dependency issues in testing
        with patch.dict('sys.modules', {
            'sage_core.jobmanager_client': Mock(),
            'sage_utils.actor_wrapper': Mock(),
        }):
            from sage_core.api.remote_environment import RemoteEnvironment
            self.RemoteEnvironment = RemoteEnvironment
    
    def test_get_local_environment_info(self):
        """测试获取本地环境信息"""
        with patch('sage_core.api.remote_environment.sys') as mock_sys, \
             patch('sage_core.api.remote_environment.os') as mock_os, \
             patch('sage_core.api.remote_environment.subprocess') as mock_subprocess:
            
            # Setup mocks
            mock_sys.version = "3.11.5 (main, Sep 11 2023)"
            mock_sys.executable = "/usr/bin/python3.11"
            mock_sys.platform = "linux"
            mock_sys.path = ["/usr/lib", "/usr/local/lib"]
            mock_os.environ.get.side_effect = lambda key, default=None: {
                "VIRTUAL_ENV": "/opt/venv",
                "CONDA_DEFAULT_ENV": None
            }.get(key, default)
            mock_os.getcwd.return_value = "/home/user/project"
            
            # Mock subprocess for pip list
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = '[{"name": "ray", "version": "2.37.0"}]'
            mock_subprocess.run.return_value = mock_result
            
            # Create environment and test
            env = self.RemoteEnvironment("test")
            with patch.object(env, 'client', self.mock_client):
                env_info = env._get_local_environment_info()
            
            # Assertions
            self.assertEqual(env_info["python_version"], "3.11.5 (main, Sep 11 2023)")
            self.assertEqual(env_info["python_executable"], "/usr/bin/python3.11")
            self.assertEqual(env_info["platform"], "linux")
            self.assertEqual(env_info["virtual_env"], "/opt/venv")
            self.assertEqual(env_info["working_directory"], "/home/user/project")
            self.assertIn("ray", env_info["installed_packages"])
    
    def test_validate_environment_compatibility_warnings(self):
        """测试环境兼容性验证 - 警告情况"""
        local_env = {
            "python_version": "3.11.5 (main, Sep 11 2023)",
            "ray_version": "2.37.0",
            "dill_version": "0.3.8",
            "virtual_env": "/opt/venv1"
        }
        
        remote_env = {
            "python_version": "3.11.4 (main, Aug 15 2023)",
            "ray_version": "2.36.0", 
            "dill_version": "0.3.8",
            "virtual_env": "/opt/venv2"
        }
        
        env = self.RemoteEnvironment("test")
        with patch.object(env, 'client', self.mock_client):
            with patch.object(env, '_get_local_environment_info', return_value=local_env), \
                 patch.object(env, '_get_remote_environment_info', return_value=remote_env):
                
                result = env._validate_environment_compatibility()
                
                # Should have warnings but still be compatible
                self.assertTrue(result["compatible"])
                self.assertGreater(len(result["warnings"]), 0)
                
                # Check specific warnings
                warnings_text = " ".join(result["warnings"])
                self.assertIn("Python version mismatch", warnings_text)
                self.assertIn("ray_version mismatch", warnings_text)
                self.assertIn("Virtual environment mismatch", warnings_text)
    
    def test_suggest_compatible_python(self):
        """测试Python兼容性建议"""
        local_env = {"python_version": "3.10.5"}
        remote_env = {"python_version": "3.11.5 (main, Sep 11 2023)"}
        
        env = self.RemoteEnvironment("test")
        
        with patch('sage_core.api.remote_environment.subprocess') as mock_subprocess:
            # Mock successful python3.11 found
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Python 3.11.4"
            mock_subprocess.run.return_value = mock_result
            
            with patch.object(env, 'client', self.mock_client):
                suggested = env._suggest_compatible_python(local_env, remote_env)
                
                self.assertEqual(suggested, "python3.11")
    
    def test_environment_alignment_attempt(self):
        """测试环境对齐尝试"""
        compatibility_result = {
            "compatible": False,
            "warnings": ["Python version mismatch"],
            "errors": [],
            "local_env": {"python_executable": "/usr/bin/python3.10"},
            "remote_env": {"python_executable": "/usr/bin/python3.11"}
        }
        
        env = self.RemoteEnvironment("test")
        
        with patch.object(env, 'client', self.mock_client), \
             patch.object(env, '_suggest_compatible_python', return_value="python3.11"), \
             patch.object(env, '_try_restart_with_python', return_value=True):
            
            result = env._attempt_environment_alignment(compatibility_result)
            self.assertTrue(result)
    
    def test_check_environment_compatibility_api(self):
        """测试环境兼容性检查API"""
        env = self.RemoteEnvironment("test")
        
        mock_compatibility = {
            "compatible": True,
            "warnings": [],
            "errors": [],
            "local_env": {"python_version": "3.11.5"},
            "remote_env": {"python_version": "3.11.5"}
        }
        
        with patch.object(env, 'client', self.mock_client), \
             patch.object(env, '_validate_environment_compatibility', return_value=mock_compatibility):
            
            # Test simple check
            result = env.check_environment_compatibility(detailed=False)
            self.assertEqual(result["compatible"], True)
            self.assertNotIn("local_env", result)
            
            # Test detailed check
            result = env.check_environment_compatibility(detailed=True)
            self.assertEqual(result["compatible"], True)
            self.assertIn("local_env", result)
    
    def test_align_environment_api(self):
        """测试环境对齐API"""
        env = self.RemoteEnvironment("test")
        
        compatible_result = {
            "compatible": True,
            "warnings": [],
            "errors": []
        }
        
        with patch.object(env, 'client', self.mock_client), \
             patch.object(env, '_validate_environment_compatibility', return_value=compatible_result):
            
            # Test already compatible
            result = env.align_environment(force=False)
            self.assertEqual(result["status"], "success")
            self.assertFalse(result["alignment_performed"])
            
            # Test forced alignment
            with patch.object(env, '_attempt_environment_alignment', return_value=True):
                result = env.align_environment(force=True)
                self.assertEqual(result["status"], "success")
                self.assertTrue(result["alignment_performed"])


class TestJobManagerClientExtensions(unittest.TestCase):
    """测试JobManagerClient的扩展功能"""
    
    def setUp(self):
        """设置测试环境"""
        with patch.dict('sys.modules', {
            'ray': Mock(),
            'ray.actor': Mock(),
            'sage_jobmanager.remote_job_manager': Mock(),
            'sage_utils.actor_wrapper': Mock(),
            'sage_utils.ray_init_helper': Mock(),
        }):
            from sage_core.jobmanager_client import JobManagerClient
            self.JobManagerClient = JobManagerClient
    
    def test_get_environment_info(self):
        """测试获取环境信息"""
        client = self.JobManagerClient()
        
        mock_response = {
            "status": "success",
            "environment_info": {
                "python_version": "3.11.5",
                "platform": "linux"
            }
        }
        
        with patch.object(client, '_send_request', return_value=mock_response):
            env_info = client.get_environment_info()
            
            self.assertEqual(env_info["python_version"], "3.11.5")
            self.assertEqual(env_info["platform"], "linux")


def run_tests():
    """运行所有测试"""
    print("运行RemoteEnvironment环境检查功能测试...")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试用例
    suite.addTests(loader.loadTestsFromTestCase(TestRemoteEnvironmentChecks))
    suite.addTests(loader.loadTestsFromTestCase(TestJobManagerClientExtensions))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回结果
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

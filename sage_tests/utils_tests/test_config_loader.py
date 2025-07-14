
import unittest
from pathlib import Path
import os
import yaml
import tempfile
import shutil
from unittest.mock import patch
from sage_utils.config_loader import load_config

class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        """在测试前设置临时目录和文件"""
        self.tmpdir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.tmpdir.name)
        self.test_file = self.test_dir / "test_config.yaml"
        self.test_file.write_text(yaml.dump({"key": "value"}))

        self.env_var = "SAGE_CONFIG"
        self.original_env = os.getenv(self.env_var)

    def tearDown(self):
        """清理测试环境"""
        self.tmpdir.cleanup()
        if self.original_env is not None:
            os.environ[self.env_var] = self.original_env
        else:
            os.environ.pop(self.env_var, None)

    def test_load_config_explicit_path(self):
        """测试显式路径加载配置"""
        config = load_config(path=self.test_file)
        self.assertEqual(config, {"key": "value"})

    def test_load_config_env_var(self):
        """测试环境变量加载配置"""
        os.environ[self.env_var] = str(self.test_file)
        config = load_config()
        self.assertEqual(config, {"key": "value"})

    # def test_load_config_user_level(self):
    #     """测试用户级配置加载（使用 mock）"""
    #     fake_user_dir = self.test_dir / "user_config"
    #     fake_user_dir.mkdir(parents=True, exist_ok=True)
    #     user_file = fake_user_dir / "config.yaml"
    #     user_file.write_text(yaml.dump({"user_key": "user_value"}))

    #     # with patch("sage_utils.config_loader.user_config_dir", return_value=str(fake_user_dir)):
    #     #     config = load_config()
    #     #     self.assertEqual(config, {"user_key": "user_value"})

    def test_load_config_project_default(self):
        """测试项目默认路径加载（使用 mock 项目结构）"""
        # 模拟项目结构：project_root/config/config.yaml
        project_root = self.test_dir / "fake_project"
        config_dir = project_root / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        project_file = config_dir / "config.yaml"
        project_file.write_text(yaml.dump({"project_key": "project_value"}))

        # 创建一个调用者伪造文件
        caller_path = project_root / "dummy.py"
        caller_path.touch()

        # patch inspect 调用栈模拟调用者文件路径
        with patch("inspect.currentframe") as mock_frame:
            mock_frame.return_value.f_back = type("MockFrame", (), {
                "f_globals": {"__file__": str(caller_path)}
            })()
            config = load_config()
            self.assertEqual(config, {"project_key": "project_value"})

if __name__ == "__main__":
    unittest.main()

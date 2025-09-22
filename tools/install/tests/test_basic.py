"""
SAGE安装模块基础测试
验证模块化安装系统的基本功能
"""

import sys
import unittest
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))


class TestBasicImports(unittest.TestCase):
    """测试基础模块导入"""
    
    def test_core_module_imports(self):
        """测试核心模块导入"""
        try:
            from core import EnvironmentManager, PackageInstaller, DependencyChecker, SubmoduleManager
            self.assertTrue(True, "核心模块导入成功")
        except ImportError as e:
            self.fail(f"核心模块导入失败: {e}")
    
    def test_utils_module_imports(self):
        """测试工具模块导入"""
        try:
            from utils import ProgressTracker, UserInterface, Validator
            self.assertTrue(True, "工具模块导入成功")
        except ImportError as e:
            self.fail(f"工具模块导入失败: {e}")
    
    def test_config_module_imports(self):
        """测试配置模块导入"""
        try:
            from config import get_profile, list_profiles
            self.assertTrue(True, "配置模块导入成功")
        except ImportError as e:
            self.fail(f"配置模块导入失败: {e}")


class TestInstallationProfiles(unittest.TestCase):
    """测试安装配置文件"""
    
    def setUp(self):
        from config import get_profile, list_profiles
        self.get_profile = get_profile
        self.list_profiles = list_profiles
    
    def test_list_profiles(self):
        """测试列出配置文件"""
        profiles = self.list_profiles()
        self.assertIsInstance(profiles, list)
        self.assertGreater(len(profiles), 0)
        
        # 检查基本配置文件是否存在
        expected_profiles = ["quick", "standard", "development", "minimal"]
        for profile in expected_profiles:
            self.assertIn(profile, profiles, f"缺少配置文件: {profile}")
    
    def test_get_profile(self):
        """测试获取配置文件"""
        # 测试有效配置文件
        profile = self.get_profile("standard")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "标准安装")
        self.assertIsInstance(profile.packages, list)
        self.assertGreater(len(profile.packages), 0)
        
        # 测试无效配置文件
        invalid_profile = self.get_profile("nonexistent")
        self.assertIsNone(invalid_profile)


class TestProgressTracker(unittest.TestCase):
    """测试进度跟踪器"""
    
    def test_progress_tracker_creation(self):
        """测试进度跟踪器创建"""
        from utils import ProgressTracker
        
        progress = ProgressTracker(total_steps=5, show_spinner=False)
        self.assertEqual(progress.total_steps, 5)
        self.assertEqual(progress.current_step, 0)
        self.assertFalse(progress.show_spinner)
    
    def test_add_step(self):
        """测试添加步骤"""
        from utils import ProgressTracker
        
        progress = ProgressTracker(show_spinner=False)
        progress.add_step("test_step", "测试步骤")
        
        self.assertEqual(len(progress.steps), 1)
        self.assertEqual(progress.steps[0].name, "test_step")
        self.assertEqual(progress.steps[0].description, "测试步骤")
        self.assertEqual(progress.steps[0].status, "pending")


class TestUserInterface(unittest.TestCase):
    """测试用户界面"""
    
    def test_quiet_mode(self):
        """测试静默模式"""
        from utils import UserInterface
        
        ui = UserInterface(quiet_mode=True)
        self.assertTrue(ui.quiet_mode)
        
        # 静默模式下不应该有输出
        ui.show_welcome("测试")  # 不应该有输出
        ui.show_info("测试信息")  # 不应该有输出


class TestDependencyChecker(unittest.TestCase):
    """测试依赖检查器"""
    
    def test_dependency_checker_creation(self):
        """测试依赖检查器创建"""
        from core import DependencyChecker
        
        checker = DependencyChecker(".")
        self.assertIsNotNone(checker.project_root)
        self.assertIsNotNone(checker.system_info)
    
    def test_python_version_check(self):
        """测试Python版本检查"""
        from core import DependencyChecker
        
        checker = DependencyChecker(".")
        is_valid, message = checker.check_python_version()
        
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(message, str)
        self.assertIn("Python", message)


def run_tests():
    """运行所有测试"""
    print("🧪 运行SAGE安装模块测试...")
    print("=" * 50)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    test_classes = [
        TestBasicImports,
        TestInstallationProfiles,
        TestProgressTracker,
        TestUserInterface,
        TestDependencyChecker
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 显示结果
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ 所有测试通过！模块化安装系统基本功能正常。")
        return True
    else:
        print(f"❌ 测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

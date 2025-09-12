#!/usr/bin/env python3
"""
SAGE Issues Manager Python Scripts Test Runner
简单的测试运行器，用于验证Python脚本的基础功能
"""

import sys
import os
import importlib.util
import traceback
from typing import List, Dict, Any

# 添加当前目录到path，以便导入其他模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestRunner:
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def test_import(self, module_name: str, module_path: str) -> bool:
        """测试模块是否可以正常导入"""
        try:
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None:
                self.results['errors'].append(f"❌ {module_name}: 无法创建模块规范")
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"✅ {module_name}: 导入成功")
            self.results['passed'] += 1
            return True
        except Exception as e:
            self.results['errors'].append(f"❌ {module_name}: 导入失败 - {str(e)}")
            self.results['failed'] += 1
            return False
    
    def test_config_loading(self) -> bool:
        """测试配置文件加载"""
        try:
            import config
            
            # 检查基本配置项（检查类属性）
            config_obj = config.Config()
            required_attrs = ['GITHUB_REPO', 'GITHUB_OWNER']
            missing_attrs = []
            
            for attr in required_attrs:
                if not hasattr(config_obj, attr):
                    missing_attrs.append(attr)
            
            if missing_attrs:
                self.results['errors'].append(f"❌ config.py: 缺少配置项 {missing_attrs}")
                self.results['failed'] += 1
                return False
            
            print("✅ config.py: 配置加载成功")
            self.results['passed'] += 1
            return True
        except Exception as e:
            self.results['errors'].append(f"❌ config.py: 配置加载失败 - {str(e)}")
            self.results['failed'] += 1
            return False
    
    def test_helper_functions(self) -> bool:
        """测试helper函数的基础功能"""
        try:
            # 测试配置类的基本功能
            import config
            config_obj = config.Config()
            
            # 尝试获取基本配置
            if hasattr(config_obj, 'GITHUB_REPO') and config_obj.GITHUB_REPO:
                print("✅ config: 基础配置功能正常")
                self.results['passed'] += 1
                return True
            else:
                self.results['errors'].append("❌ config: 无法获取基础配置")
                self.results['failed'] += 1
                return False
        except Exception as e:
            self.results['errors'].append(f"❌ config: 测试失败 - {str(e)}")
            self.results['failed'] += 1
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🧪 开始运行Python脚本测试...")
        print("=" * 50)
        
        # 获取所有Python文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        python_files = []
        
        for file in os.listdir(script_dir):
            if file.endswith('.py') and file != 'test_runner.py' and not file.startswith('test_'):
                python_files.append(file)
        
        # 测试导入
        print("\n📦 测试模块导入...")
        for file in python_files:
            module_name = file[:-3]  # 去掉.py后缀
            module_path = os.path.join(script_dir, file)
            self.test_import(module_name, module_path)
        
        # 测试配置
        print("\n⚙️ 测试配置功能...")
        self.test_config_loading()
        
        # 测试helper函数
        print("\n🔧 测试helper函数...")
        self.test_helper_functions()
        
        # 汇总结果
        print("\n" + "=" * 50)
        print(f"🎯 测试汇总:")
        print(f"   ✅ 通过: {self.results['passed']}")
        print(f"   ❌ 失败: {self.results['failed']}")
        
        if self.results['errors']:
            print(f"\n❌ 错误详情:")
            for error in self.results['errors']:
                print(f"   {error}")
        
        return self.results

def main():
    """主函数"""
    runner = TestRunner()
    results = runner.run_all_tests()
    
    # 返回适当的退出码
    return 0 if results['failed'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

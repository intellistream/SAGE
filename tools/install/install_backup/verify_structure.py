#!/usr/bin/env python3
"""
简单的模块化安装系统验证脚本
"""

import sys
from pathlib import Path

# 添加当前目录到Python路径
install_dir = Path(__file__).parent
sys.path.insert(0, str(install_dir))

def test_module_structure():
    """测试模块结构"""
    print("🔍 检查模块结构...")
    
    required_dirs = ["core", "utils", "config", "tests"]
    missing_dirs = []
    
    for dir_name in required_dirs:
        dir_path = install_dir / dir_name
        if not dir_path.exists():
            missing_dirs.append(dir_name)
        else:
            print(f"  ✅ {dir_name}/ 目录存在")
    
    if missing_dirs:
        print(f"  ❌ 缺少目录: {', '.join(missing_dirs)}")
        return False
    
    return True

def test_core_files():
    """测试核心文件"""
    print("\n🔍 检查核心文件...")
    
    core_files = [
        "core/__init__.py",
        "core/environment_manager.py", 
        "core/package_installer.py",
        "core/dependency_checker.py",
        "core/submodule_manager.py"
    ]
    
    missing_files = []
    for file_path in core_files:
        full_path = install_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path} 存在")
    
    if missing_files:
        print(f"  ❌ 缺少文件: {', '.join(missing_files)}")
        return False
    
    return True

def test_utils_files():
    """测试工具文件"""
    print("\n🔍 检查工具文件...")
    
    utils_files = [
        "utils/__init__.py",
        "utils/progress_tracker.py",
        "utils/user_interface.py", 
        "utils/validator.py"
    ]
    
    missing_files = []
    for file_path in utils_files:
        full_path = install_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path} 存在")
    
    if missing_files:
        print(f"  ❌ 缺少文件: {', '.join(missing_files)}")
        return False
    
    return True

def test_config_files():
    """测试配置文件"""
    print("\n🔍 检查配置文件...")
    
    config_files = [
        "config/__init__.py",
        "config/defaults.py",
        "config/profiles.py"
    ]
    
    missing_files = []
    for file_path in config_files:
        full_path = install_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"  ✅ {file_path} 存在")
    
    if missing_files:
        print(f"  ❌ 缺少文件: {', '.join(missing_files)}")
        return False
    
    return True

def test_main_installer():
    """测试主安装器"""
    print("\n🔍 检查主安装器...")
    
    installer_path = install_dir / "install.py"
    if installer_path.exists():
        print("  ✅ install.py 存在")
        
        # 检查文件大小（应该是一个合理的脚本）
        file_size = installer_path.stat().st_size
        if file_size > 1000:  # 至少1KB
            print(f"  ✅ install.py 文件大小合理 ({file_size} bytes)")
            return True
        else:
            print(f"  ⚠️ install.py 文件可能过小 ({file_size} bytes)")
            return False
    else:
        print("  ❌ install.py 不存在")
        return False

def test_basic_syntax():
    """测试基本语法"""
    print("\n🔍 检查Python语法...")
    
    python_files = [
        "install.py",
        "core/environment_manager.py",
        "core/package_installer.py", 
        "core/dependency_checker.py",
        "core/submodule_manager.py",
        "utils/progress_tracker.py",
        "utils/user_interface.py",
        "utils/validator.py",
        "config/defaults.py",
        "config/profiles.py"
    ]
    
    syntax_errors = []
    
    for file_path in python_files:
        full_path = install_dir / file_path
        if full_path.exists():
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 简单的语法检查
                compile(content, str(full_path), 'exec')
                print(f"  ✅ {file_path} 语法正确")
                
            except SyntaxError as e:
                syntax_errors.append(f"{file_path}: {e}")
                print(f"  ❌ {file_path} 语法错误: {e}")
            except Exception as e:
                print(f"  ⚠️ {file_path} 检查时出错: {e}")
    
    return len(syntax_errors) == 0

def test_readme():
    """测试README文件"""
    print("\n🔍 检查README文件...")
    
    readme_path = install_dir / "README.md"
    if readme_path.exists():
        file_size = readme_path.stat().st_size
        if file_size > 500:  # 至少500字节
            print(f"  ✅ README.md 存在且内容充实 ({file_size} bytes)")
            return True
        else:
            print(f"  ⚠️ README.md 可能内容不足 ({file_size} bytes)")
            return False
    else:
        print("  ❌ README.md 不存在")
        return False

def main():
    """主函数"""
    print("🎯 SAGE模块化安装系统验证")
    print("=" * 50)
    
    tests = [
        ("模块结构", test_module_structure),
        ("核心文件", test_core_files),
        ("工具文件", test_utils_files), 
        ("配置文件", test_config_files),
        ("主安装器", test_main_installer),
        ("语法检查", test_basic_syntax),
        ("README文档", test_readme)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ❌ {test_name} 测试出错: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有验证通过！模块化安装系统结构正确。")
        print("\n💡 下一步:")
        print("  1. 运行: python3 install.py --list-profiles")
        print("  2. 测试: python3 install.py --help")
        print("  3. 体验: python3 install.py --profile quick --dry-run")
        return True
    else:
        print("⚠️ 发现问题，请检查上述错误。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

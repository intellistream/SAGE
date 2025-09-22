#!/usr/bin/env python3
"""
测试套件安装验证脚本
Validation script for the SAGE mmap_queue test suite

使用: python validate_test_setup.py
"""

import os
import sys
import importlib.util
from pathlib import Path

def main():
    """验证测试套件安装的完整性"""
    print("🔍 验证 SAGE mmap_queue 测试套件...")
    print("=" * 50)
    
    # 获取测试目录路径
    test_dir = Path(__file__).parent
    root_dir = test_dir.parent
    
    print(f"📁 测试目录: {test_dir}")
    print(f"📁 根目录: {root_dir}")
    
    # 检查必需文件
    required_files = [
        "__init__.py",
        "README.md", 
        "run_all_tests.py",
        "generate_test_report.py",
        "test_basic_functionality.py",
        "test_ray_integration.py",
        "test_quick_validation.py",
        "test_comprehensive.py",
        "test_multiprocess_concurrent.py", 
        "test_performance_benchmark.py",
        "test_safety.py"
    ]
    
    missing_files = []
    for file in required_files:
        file_path = test_dir / file
        if file_path.exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - 缺失")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️  发现 {len(missing_files)} 个缺失文件!")
        return False
    
    print("\n🔧 检查核心模块导入...")
    
    # 检查核心模块是否可导入
    sys.path.insert(0, str(root_dir))
    
    try:
        from sage.extensions.sage_queue import SageQueue
        print("✅ SageQueue 导入成功")
    except ImportError as e:
        print(f"❌ SageQueue 导入失败: {e}")
        return False
    
    # 检查测试模块是否可导入
    test_modules = [
        "test_quick_validation",
        "test_basic_functionality", 
        "test_safety"
    ]
    
    failed_imports = []
    for module in test_modules:
        try:
            spec = importlib.util.spec_from_file_location(
                module, test_dir / f"{module}.py"
            )
            if spec and spec.loader:
                test_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(test_module)
                print(f"✅ {module} 导入成功")
            else:
                raise ImportError(f"无法加载模块规格")
        except Exception as e:
            print(f"❌ {module} 导入失败: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n⚠️  {len(failed_imports)} 个测试模块导入失败!")
        return False
    
    print("\n🎯 运行快速验证测试...")
    
    # 运行最基本的测试
    try:
        # 创建小队列进行基本测试
        queue = SageQueue("validation_test")
        
        # 基本写入读取测试
        test_data = b"Hello, SAGE!"
        queue.put(test_data)
        retrieved = queue.get()
        
        if retrieved == test_data:
            print("✅ 基本读写功能正常")
        else:
            print("❌ 基本读写功能异常")
            return False
            
        # 清理
        queue.close()
        
    except Exception as e:
        print(f"❌ 基本功能测试失败: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 测试套件验证完成!")
    print("\n📖 使用方法:")
    print("   - 快速测试: python run_all_tests.py --quick")
    print("   - 完整测试: python run_all_tests.py")
    print("   - 生成报告: python generate_test_report.py")
    print("   - 查看文档: cat README.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

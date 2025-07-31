#!/usr/bin/env python3
"""
测试 release_build.py 的构建功能
"""

import os
import sys
import subprocess

def test_build_discovery():
    """测试自动发现功能"""
    print("=== 测试自动发现功能 ===")
    
    # 添加当前目录到 Python 路径
    sys.path.insert(0, '.')
    
    try:
        from release_build import build_sage_ext_modules, build_sage_ext_libraries
        import glob
        
        # 检查绑定文件
        binding_files = glob.glob('sage_ext/**/*bindings*.cpp', recursive=True)
        print(f"发现的绑定文件: {len(binding_files)}")
        for f in binding_files:
            print(f"  - {f}")
        
        # 检查构建脚本
        build_scripts = []
        for root, dirs, files in os.walk('sage_ext'):
            if 'build.sh' in files and root != 'sage_ext':
                build_scripts.append(os.path.join(root, 'build.sh'))
        
        print(f"\n发现的构建脚本: {len(build_scripts)}")
        for script in build_scripts:
            print(f"  - {script}")
        
        print("\n✓ 自动发现功能正常")
        return True
        
    except Exception as e:
        print(f"✗ 自动发现功能失败: {e}")
        return False

def test_build_process():
    """测试构建过程"""
    print("\n=== 测试构建过程 ===")
    
    try:
        # 只测试构建发现，不实际执行构建
        sys.path.insert(0, '.')
        from release_build import build_sage_ext_modules
        
        print("调用 build_sage_ext_modules()...")
        modules = build_sage_ext_modules()
        
        print(f"✓ 成功返回 {len(modules)} 个扩展模块")
        for i, module in enumerate(modules):
            if hasattr(module, 'name'):
                print(f"  {i+1}. {module.name}")
        
        return True
        
    except Exception as e:
        print(f"✗ 构建过程失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("SAGE Release Build 测试")
    print("=" * 50)
    
    # 检查当前目录
    if not os.path.exists('sage_ext'):
        print("✗ sage_ext 目录不存在")
        return 1
    
    if not os.path.exists('release_build.py'):
        print("✗ release_build.py 文件不存在")
        return 1
    
    # 运行测试
    tests = [
        test_build_discovery,
        test_build_process,
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n测试结果: {passed}/{len(tests)} 通过")
    
    if passed == len(tests):
        print("🎉 所有测试通过!")
        return 0
    else:
        print("❌ 有测试失败")
        return 1

if __name__ == '__main__':
    exit(main())

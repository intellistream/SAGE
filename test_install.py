#!/usr/bin/env python3
"""
测试SAGE安装是否正确
"""

import sys
import os

def test_sage_install():
    """测试SAGE是否正确安装到site-packages"""
    print("🔍 测试SAGE安装...")
    
    try:
        import sage
        print(f"✅ SAGE 已安装")
        print(f"📍 SAGE 位置: {sage.__file__}")
        
        # 检查是否安装在site-packages
        if 'site-packages' in sage.__file__:
            print("✅ SAGE 已正确安装到site-packages")
        elif '/packages/' in sage.__file__:
            print("⚠️  SAGE 仍然指向开发目录（editable install）")
            return False
        else:
            print(f"❓ SAGE 安装在: {os.path.dirname(sage.__file__)}")
        
        # 尝试获取版本
        try:
            version = sage.__version__
            print(f"📋 SAGE 版本: {version}")
        except AttributeError:
            print("⚠️  无法获取版本信息")
        
        return True
        
    except ImportError as e:
        print(f"❌ 无法导入SAGE: {e}")
        return False

def test_submodules():
    """测试SAGE子模块"""
    print("\n🔍 测试SAGE子模块...")
    
    modules_to_test = [
        'sage.kernel',
        'sage.middleware', 
        'sage.lib',
        'sage.plugins',
        'sage.cli'
    ]
    
    success_count = 0
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module}")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module}: {e}")
    
    print(f"\n📊 子模块测试结果: {success_count}/{len(modules_to_test)} 成功")
    return success_count == len(modules_to_test)

if __name__ == "__main__":
    print("=" * 50)
    print("SAGE 安装测试")
    print("=" * 50)
    
    # 显示Python环境信息
    print(f"🐍 Python 可执行文件: {sys.executable}")
    print(f"📦 Site packages: {[p for p in sys.path if 'site-packages' in p]}")
    print()
    
    # 测试主模块
    main_ok = test_sage_install()
    
    # 测试子模块
    sub_ok = test_submodules()
    
    print("\n" + "=" * 50)
    if main_ok and sub_ok:
        print("🎉 所有测试通过！SAGE已正确安装")
        sys.exit(0)
    else:
        print("❌ 某些测试失败")
        sys.exit(1)

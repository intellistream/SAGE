#!/usr/bin/env python3
"""
测试SAGE安装是否正确
支持验证不同的安装方法
"""

import sys
import os
import subprocess

def test_sage_install():
    """测试SAGE是否正确安装"""
    print("🔍 测试SAGE安装...")
    
    try:
        import sage
        print(f"✅ SAGE 已安装")
        print(f"📍 SAGE 位置: {sage.__file__}")
        
        # 检查安装类型
        if 'site-packages' in sage.__file__:
            print("✅ SAGE 已正确安装到 site-packages（生产模式）")
            install_type = "production"
        elif '/packages/' in sage.__file__ and sage.__file__.endswith('.py'):
            print("✅ SAGE 以开发模式安装（editable install）")
            install_type = "development"
        elif '.egg-link' in sage.__file__ or '/src/' in sage.__file__:
            print("✅ SAGE 以开发模式安装（editable install）")
            install_type = "development"
        else:
            print(f"❓ SAGE 安装在: {os.path.dirname(sage.__file__)}")
            install_type = "unknown"
        
        # 尝试获取版本
        try:
            version = sage.__version__
            print(f"📋 SAGE 版本: {version}")
        except AttributeError:
            print("⚠️  无法获取版本信息")
        
        return True, install_type
        
    except ImportError as e:
        print(f"❌ 无法导入SAGE: {e}")
        return False, "none"

def test_submodules():
    """测试SAGE子模块"""
    print("\n🔍 测试SAGE子模块...")
    
    modules_to_test = [
        ('sage.kernel', '核心模块'),
        ('sage.middleware', '中间件模块'), 
        ('sage.lib', '库模块'),
        ('sage.plugins', '插件模块'),
    ]
    
    success_count = 0
    for module, name in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module} ({name})")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module} ({name}): {e}")
    
    # 测试可选模块
    optional_modules = [
        ('sage.cli', 'CLI工具'),
        ('sage_dev_toolkit', '开发工具包'),
    ]
    
    optional_count = 0
    for module, name in optional_modules:
        try:
            __import__(module)
            print(f"✅ {module} ({name}) - 可选")
            optional_count += 1
        except ImportError:
            print(f"⚠️  {module} ({name}) - 未安装（可选）")
    
    print(f"\n📊 子模块测试结果: {success_count}/{len(modules_to_test)} 核心模块成功")
    print(f"📊 可选模块: {optional_count}/{len(optional_modules)} 可选模块可用")
    
    return success_count == len(modules_to_test)

def test_pip_list():
    """检查pip list中的SAGE包"""
    print("\n🔍 检查已安装的SAGE相关包...")
    
    try:
        result = subprocess.run(['pip', 'list'], capture_output=True, text=True)
        sage_packages = [line for line in result.stdout.split('\n') if 'sage' in line.lower()]
        
        if sage_packages:
            print("📦 已安装的SAGE相关包:")
            for pkg in sage_packages:
                print(f"   {pkg}")
        else:
            print("⚠️  pip list中未找到SAGE包")
            
    except Exception as e:
        print(f"❌ 无法运行pip list: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("SAGE 安装测试")
    print("=" * 50)
    
    # 显示Python环境信息
    print(f"🐍 Python 可执行文件: {sys.executable}")
    print(f"📦 Site packages: {[p for p in sys.path if 'site-packages' in p]}")
    print()
    
    # 测试主模块
    main_ok, install_type = test_sage_install()
    
    # 测试子模块
    sub_ok = test_submodules()
    
    # 检查pip list
    test_pip_list()
    
    print("\n" + "=" * 50)
    print("📋 安装总结")
    print("=" * 50)
    
    if main_ok:
        print(f"✅ SAGE 主模块: 已安装 ({install_type} 模式)")
    else:
        print("❌ SAGE 主模块: 未安装")
        
    if sub_ok:
        print("✅ SAGE 子模块: 全部可用")
    else:
        print("⚠️  SAGE 子模块: 部分缺失")
    
    print("\n💡 安装建议:")
    if install_type == "production":
        print("   当前为生产模式安装，适合最终用户")
    elif install_type == "development":
        print("   当前为开发模式安装，代码修改会即时生效")
    else:
        print("   建议重新安装SAGE")
        print("   开发者使用: make dev-install")
        print("   用户使用: make install-smart")
    
    if main_ok and sub_ok:
        print("\n🎉 所有测试通过！SAGE安装正常")
        sys.exit(0)
    else:
        print("\n❌ 某些测试失败，请检查安装")
        sys.exit(1)

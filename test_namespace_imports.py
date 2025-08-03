#!/usr/bin/env python3
"""
测试命名空间包导入功能
验证所有sage子包都能正确导入
"""

def test_imports():
    """测试所有sage包的导入"""
    print("🧪 测试SAGE命名空间包导入...")
    
    # 测试基础utils包导入
    try:
        from sage.utils import config, logger
        print("✅ sage.utils 导入成功")
    except ImportError as e:
        print(f"❌ sage.utils 导入失败: {e}")
    
    # 测试core包导入
    try:
        from sage.core import pipeline, models
        print("✅ sage.core 导入成功")
    except ImportError as e:
        print(f"❌ sage.core 导入失败: {e}")
    
    # 测试extensions包导入
    try:
        from sage.extensions import plugins
        print("✅ sage.extensions 导入成功")
    except ImportError as e:
        print(f"❌ sage.extensions 导入失败: {e}")
    
    # 测试lib包导入
    try:
        from sage.lib import data, vectorstore
        print("✅ sage.lib 导入成功")
    except ImportError as e:
        print(f"❌ sage.lib 导入失败: {e}")
    
    # 测试plugins包导入
    try:
        from sage.plugins import base
        print("✅ sage.plugins 导入成功")
    except ImportError as e:
        print(f"❌ sage.plugins 导入失败: {e}")
    
    # 测试service包导入
    try:
        from sage.service import api, server
        print("✅ sage.service 导入成功")
    except ImportError as e:
        print(f"❌ sage.service 导入失败: {e}")
    
    # 测试cli包导入
    try:
        from sage.cli import main
        print("✅ sage.cli 导入成功")
    except ImportError as e:
        print(f"❌ sage.cli 导入失败: {e}")

def test_cross_package_imports():
    """测试跨包导入"""
    print("\n🔗 测试跨包导入...")
    
    try:
        # CLI应该能导入core和utils
        from sage.cli.main import app
        from sage.core.pipeline import Pipeline
        from sage.utils.config import Config
        print("✅ 跨包导入成功 - CLI可以使用core和utils")
    except ImportError as e:
        print(f"❌ 跨包导入失败: {e}")

def test_namespace_functionality():
    """测试命名空间包的基本功能"""
    print("\n📦 测试命名空间包功能...")
    
    import sage
    print(f"sage package path: {sage.__path__}")
    
    # 列出所有可用的子包
    import pkgutil
    subpackages = []
    for importer, modname, ispkg in pkgutil.iter_modules(sage.__path__, sage.__name__ + "."):
        if ispkg:
            subpackages.append(modname)
    
    print(f"发现的子包: {subpackages}")
    expected_packages = [
        'sage.utils', 'sage.core', 'sage.extensions', 
        'sage.lib', 'sage.plugins', 'sage.service', 'sage.cli'
    ]
    
    for pkg in expected_packages:
        if pkg in subpackages:
            print(f"✅ {pkg} 已正确注册")
        else:
            print(f"❌ {pkg} 未找到")

if __name__ == "__main__":
    test_imports()
    test_cross_package_imports()
    test_namespace_functionality()
    print("\n🎉 测试完成！")

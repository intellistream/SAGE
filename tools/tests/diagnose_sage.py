#!/usr/bin/env python3
"""
SAGE 安装诊断脚本
检查 sage namespace package 的安装状态和模块可用性
"""

import sys
import importlib
from pathlib import Path
import os
import pkgutil

def check_sage_installation():
    """检查 SAGE 安装状态"""
    print("🔍 SAGE 安装诊断")
    print("=" * 50)
    
    # 1. 检查基础 sage 包
    try:
        import sage
        print(f"✅ sage 包导入成功")
        print(f"   路径: {sage.__file__}")
        print(f"   版本: {getattr(sage, '__version__', 'Unknown')}")
        if hasattr(sage, '__path__'):
            print(f"   命名空间路径: {sage.__path__}")
    except ImportError as e:
        print(f"❌ sage 包导入失败: {e}")
        return False
    
    # 2. 检查 sage.kernel
    print("\n📦 检查 sage.kernel:")
    try:
        import sage.kernel
        print(f"✅ sage.kernel 导入成功")
        print(f"   路径: {getattr(sage.kernel, '__file__', 'namespace package')}")
        if hasattr(sage.kernel, '__path__'):
            print(f"   命名空间路径: {sage.kernel.__path__}")
            
            # 检查 sage.kernel 目录中的文件
            print("   📁 sage.kernel 目录内容:")
            for path in sage.kernel.__path__:
                if os.path.exists(path):
                    print(f"     {path}:")
                    try:
                        files = os.listdir(path)
                        for f in sorted(files):
                            print(f"       - {f}")
                    except PermissionError:
                        print(f"       权限不足，无法列出内容")
        
        # 尝试导入 JobManagerClient
        try:
            from sage.kernel import JobManagerClient
            print(f"✅ JobManagerClient 导入成功: {JobManagerClient}")
        except ImportError as e:
            print(f"❌ JobManagerClient 导入失败: {e}")
            
            # 列出 sage.kernel 中可用的属性
            print(f"   sage.kernel 中可用的属性: {dir(sage.kernel)}")
            
            # 尝试查找所有可导入的模块
            print("   🔍 在 sage.kernel 中搜索可用模块:")
            try:
                import pkgutil
                for importer, modname, ispkg in pkgutil.iter_modules(sage.kernel.__path__, sage.kernel.__name__ + "."):
                    print(f"     - {modname} {'(包)' if ispkg else '(模块)'}")
            except Exception as e:
                print(f"     搜索模块失败: {e}")
            
    except ImportError as e:
        print(f"❌ sage.kernel 导入失败: {e}")
    
    # 3. 检查 sage.utils
    print("\n📦 检查 sage.utils:")
    try:
        import sage.utils
        print(f"✅ sage.utils 导入成功")
        if hasattr(sage.utils, '__path__'):
            print(f"   命名空间路径: {sage.utils.__path__}")
            
            # 检查是否有 logging.custom_logger
            try:
                from sage.utils.logging.custom_logger import CustomLogger
                print(f"✅ CustomLogger 导入成功")
            except ImportError as e:
                print(f"❌ CustomLogger 导入失败: {e}")
                
    except ImportError as e:
        print(f"❌ sage.utils 导入失败: {e}")
    
    # 4. 检查 sage.middleware  
    print("\n📦 检查 sage.middleware:")
    try:
        import sage.middleware
        print(f"✅ sage.middleware 导入成功")
        if hasattr(sage.middleware, '__path__'):
            print(f"   命名空间路径: {sage.middleware.__path__}")
    except ImportError as e:
        print(f"❌ sage.middleware 导入失败: {e}")
    
    # 5. 检查已安装的包
    print("\n📋 检查已安装的相关包:")
    import subprocess
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list"], 
                               capture_output=True, text=True, check=True)
        lines = result.stdout.split('\n')
        sage_packages = [line for line in lines if 'sage' in line.lower() or 'intellistream' in line.lower()]
        
        for package in sage_packages:
            if package.strip():
                print(f"   {package}")
                
    except subprocess.CalledProcessError as e:
        print(f"❌ 无法获取包列表: {e}")
    
    # 6. 检查闭源包的详细信息
    print("\n🔍 检查闭源包详细信息:")
    closed_packages = [
        'intellistream-sage-kernel',
        'intellistream-sage-utils', 
        'intellistream-sage-middleware'
    ]
    
    for pkg_name in closed_packages:
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "show", pkg_name], 
                                   capture_output=True, text=True, check=True)
            print(f"📦 {pkg_name}:")
            lines = result.stdout.split('\n')
            for line in lines:
                if line.startswith(('Version:', 'Location:', 'Files:')):
                    print(f"   {line}")
        except subprocess.CalledProcessError:
            print(f"❌ 无法获取 {pkg_name} 信息")
    
    # 7. 检查 Python 路径
    print(f"\n🐍 Python 路径信息:")
    print(f"   Python 版本: {sys.version}")
    print(f"   Python 路径: {sys.executable}")
    print(f"   模块搜索路径:")
    for path in sys.path[:5]:  # 只显示前5个路径
        print(f"     {path}")
    
    return True

if __name__ == "__main__":
    check_sage_installation()

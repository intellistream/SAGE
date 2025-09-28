#!/usr/bin/env python3
"""
诊断 SAGE Flow 导入问题的脚本
用于在 CI 环境中调试模块发现问题
"""

import importlib.util
import os
import sys
from pathlib import Path


def check_path_exists(path_str):
    """检查路径是否存在"""
    path = Path(path_str)
    exists = path.exists()
    print(f"{'✅' if exists else '❌'} {path_str}: {'存在' if exists else '不存在'}")
    if exists and path.is_dir():
        try:
            contents = list(path.iterdir())
            print(f"    内容: {[f.name for f in contents[:5]]}")
            if len(contents) > 5:
                print(f"    ... 和其他 {len(contents) - 5} 个文件")
        except:
            print("    无法列出内容")
    return exists


def check_module_import(module_name):
    """检查模块是否可以导入"""
    try:
        module = importlib.import_module(module_name)
        print(f"✅ {module_name}: 导入成功")
        if hasattr(module, "__file__"):
            print(f"    位置: {module.__file__}")
        return True
    except Exception as e:
        print(f"❌ {module_name}: 导入失败 - {e}")
        return False


def check_file_import(file_path):
    """检查文件是否可以直接导入"""
    try:
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"✅ 文件 {file_path}: 可以直接导入")
            return True
    except Exception as e:
        print(f"❌ 文件 {file_path}: 直接导入失败 - {e}")
    return False


def main():
    print("🔍 SAGE Flow 导入诊断")
    print("=" * 50)

    print(f"\n📁 当前工作目录: {os.getcwd()}")
    print(f"🐍 Python 版本: {sys.version}")
    print(f"🐍 Python 可执行文件: {sys.executable}")

    print(f"\n📂 Python 路径:")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")

    print(f"\n🔍 检查关键路径:")
    base_path = "packages/sage-middleware/src/sage/middleware/components/sage_flow"
    paths_to_check = [
        base_path,
        f"{base_path}/python",
        f"{base_path}/python/__init__.py",
        f"{base_path}/python/sage_flow.py",
        f"{base_path}/python/_sage_flow.cpython-311-x86_64-linux-gnu.so",
        f"{base_path}/python/micro_service",
        f"{base_path}/python/micro_service/__init__.py",
        f"{base_path}/python/micro_service/sage_flow_service.py",
    ]

    for path in paths_to_check:
        check_path_exists(path)

    print(f"\n🧩 检查模块导入:")
    modules_to_check = [
        "sage",
        "sage.middleware",
        "sage.middleware.components",
        "sage.middleware.components.sage_flow",
        "sage.middleware.components.sage_flow.python",
        "sage.middleware.components.sage_flow.python._sage_flow",
        "sage.middleware.components.sage_flow.python.sage_flow",
        "sage.middleware.components.sage_flow.python.micro_service",
        "sage.middleware.components.sage_flow.python.micro_service.sage_flow_service",
    ]

    success_count = 0
    for module in modules_to_check:
        if check_module_import(module):
            success_count += 1

    print(f"\n📊 导入结果: {success_count}/{len(modules_to_check)} 成功")

    print(f"\n🔧 尝试特定导入测试:")
    test_imports = [
        "from sage.middleware.components.sage_flow.python.sage_flow import SimpleStreamSource, StreamEnvironment",
        "from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import SageFlowService",
    ]

    for test_import in test_imports:
        print(f"\n测试: {test_import}")
        try:
            exec(test_import)
            print("✅ 成功")
        except Exception as e:
            print(f"❌ 失败: {e}")
            import traceback

            print("详细错误:")
            traceback.print_exc()

    print(f"\n🎯 extensions_compat 状态:")
    try:
        from sage.middleware.components.extensions_compat import \
            check_extensions_availability

        status = check_extensions_availability()
        print(f"扩展状态: {status}")
    except Exception as e:
        print(f"无法检查扩展状态: {e}")


if __name__ == "__main__":
    main()

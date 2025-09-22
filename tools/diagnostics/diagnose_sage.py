#!/usr/bin/env python3
"""
import logging
SAGE 安装诊断脚本
检查 sage namespace package 的安装状态和模块可用性
"""

import importlib
import os
import pkgutil
import sys
from pathlib import Path


def check_sage_installation():
    """检查 SAGE 安装状态"""
    logging.info("🔍 SAGE 安装诊断")
    logging.info("=" * 50)

    # 1. 检查基础 sage 包
    try:
        import sage

        logging.info(f"✅ sage 包导入成功")
        logging.info(f"   路径: {sage.__file__}")
        logging.info(f"   版本: {getattr(sage, '__version__', 'Unknown')}")
        if hasattr(sage, "__path__"):
            logging.info(f"   命名空间路径: {sage.__path__}")
    except ImportError as e:
        logging.info(f"❌ sage 包导入失败: {e}")
        return False

    # 2. 检查 sage.kernel
    logging.info("\n📦 检查 sage.kernel:")
    try:
        import sage.kernel

        logging.info(f"✅ sage.kernel 导入成功")
        logging.info(
            f"   路径: {getattr(sage.kernel, '__file__', 'namespace package')}"
        )
        if hasattr(sage.kernel, "__path__"):
            logging.info(f"   命名空间路径: {sage.kernel.__path__}")

            # 检查 sage.kernel 目录中的文件
            logging.info("   📁 sage.kernel 目录内容:")
            for path in sage.kernel.__path__:
                if os.path.exists(path):
                    logging.info(f"     {path}:")
                    try:
                        files = os.listdir(path)
                        for f in sorted(files):
                            logging.info(f"       - {f}")
                    except PermissionError:
                        logging.info(f"       权限不足，无法列出内容")

        # 尝试导入 JobManagerClient
        try:
            from sage.kernel.jobmanager.jobmanager_client import \
                JobManagerClient

            logging.info(f"✅ JobManagerClient 导入成功: {JobManagerClient}")
        except ImportError as e:
            logging.info(f"❌ JobManagerClient 导入失败: {e}")

            # 列出 sage.kernel 中可用的属性
            logging.info(f"   sage.kernel 中可用的属性: {dir(sage.kernel)}")

            # 尝试查找所有可导入的模块
            logging.info("   🔍 在 sage.kernel 中搜索可用模块:")
            try:
                import pkgutil

                for importer, modname, ispkg in pkgutil.iter_modules(
                    sage.kernel.__path__, sage.kernel.__name__ + "."
                ):
                    logging.info(f"     - {modname} {'(包)' if ispkg else '(模块)'}")
            except Exception as e:
                logging.info(f"     搜索模块失败: {e}")

    except ImportError as e:
        logging.info(f"❌ sage.kernel 导入失败: {e}")

    # 3. 检查 sage.utils
    logging.info("\n📦 检查 sage.utils:")
    try:
        import sage.utils

        logging.info(f"✅ sage.utils 导入成功")
        if hasattr(sage.utils, "__path__"):
            logging.info(f"   命名空间路径: {sage.utils.__path__}")

            # 检查是否有 logging.custom_logger
            try:
                from sage.utils.logging.custom_logger import CustomLogger

                logging.info(f"✅ CustomLogger 导入成功")
            except ImportError as e:
                logging.info(f"❌ CustomLogger 导入失败: {e}")

    except ImportError as e:
        logging.info(f"❌ sage.utils 导入失败: {e}")

    # 4. 检查 sage.middleware
    logging.info("\n📦 检查 sage.middleware:")
    try:
        import sage.middleware

        logging.info(f"✅ sage.middleware 导入成功")
        if hasattr(sage.middleware, "__path__"):
            logging.info(f"   命名空间路径: {sage.middleware.__path__}")
    except ImportError as e:
        logging.info(f"❌ sage.middleware 导入失败: {e}")

    # 5. 检查已安装的包
    logging.info("\n📋 检查已安装的相关包:")
    import subprocess

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.split("\n")
        sage_packages = [
            line
            for line in lines
            if "sage" in line.lower() or "intellistream" in line.lower()
        ]

        for package in sage_packages:
            if package.strip():
                logging.info(f"   {package}")

    except subprocess.CalledProcessError as e:
        logging.info(f"❌ 无法获取包列表: {e}")

    # 6. 检查闭源包的详细信息
    logging.info("\n🔍 检查闭源包详细信息:")
    closed_packages = [
        "intellistream-sage-kernel",
        "intellistream-sage-utils",
        "intellistream-sage-middleware",
    ]

    for pkg_name in closed_packages:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", pkg_name],
                capture_output=True,
                text=True,
                check=True,
            )
            logging.info(f"📦 {pkg_name}:")
            lines = result.stdout.split("\n")
            for line in lines:
                if line.startswith(("Version:", "Location:", "Files:")):
                    logging.info(f"   {line}")
        except subprocess.CalledProcessError:
            logging.info(f"❌ 无法获取 {pkg_name} 信息")

    # 7. 检查 Python 路径
    logging.info(f"\n🐍 Python 路径信息:")
    logging.info(f"   Python 版本: {sys.version}")
    logging.info(f"   Python 路径: {sys.executable}")
    logging.info(f"   模块搜索路径:")
    for path in sys.path[:5]:  # 只显示前5个路径
        logging.info(f"     {path}")

    return True


if __name__ == "__main__":
    check_sage_installation()

#!/usr/bin/env python3
"""
SAGE Meta Package Setup Script
提供安装后的用户友好提示
"""

import sys
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop


class PostInstallCommand(install):
    """安装后执行的命令"""
    def run(self):
        install.run(self)
        self._post_install()
    
    def _post_install(self):
        _show_installation_guide()


class PostDevelopCommand(develop):
    """开发安装后执行的命令"""
    def run(self):
        develop.run(self)
        self._post_install()
    
    def _post_install(self):
        _show_installation_guide()


def _show_installation_guide():
    """显示安装指南"""
    print("\n" + "="*60)
    print("🎉 SAGE 安装完成！")
    print("="*60)
    
    print("\n📦 当前已安装:")
    print("  • isage (meta package) - 核心包管理")
    print("  • isage-kernel - 数据处理内核")
    print("  • isage-middleware - 中间件服务")
    print("  • isage-apps - 应用示例")
    
    print("\n🔧 可选功能包 (推荐安装):")
    print("  • CLI 工具:")
    print("    pip install isage-common[basic]")
    print("  • 开发工具:")
    print("    pip install isage-common[dev]")
    print("  • Web 前端:")
    print("    pip install isage-common[frontend]")
    print("  • 完整功能:")
    print("    pip install isage-common[full]")
    
    print("\n🚀 快速开始:")
    print("  • 查看帮助: python -c \"import sage; help(sage)\"")
    print("  • 运行示例: python -c \"from sage.apps.examples import hello_world\"")
    
    print("\n📚 更多信息:")
    print("  • 文档: https://intellistream.github.io/SAGE-Pub/")
    print("  • GitHub: https://github.com/intellistream/SAGE")
    
    print("\n💡 提示: 根据使用需求选择安装对应的功能包")
    print("="*60 + "\n")


# 使用 pyproject.toml 作为主要配置，这里只处理 post-install hooks
setup(
    cmdclass={
        'install': PostInstallCommand,
        'develop': PostDevelopCommand,
    },
)

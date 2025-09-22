#!/usr/bin/env python3
"""
import logging
SAGE Meta Package Setup Script
提供安装后的用户友好提示
"""

import logging

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install


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
    logging.info("\n" + "=" * 60)
    logging.info("🎉 SAGE 安装完成！")
    logging.info("=" * 60)

    logging.info("\n📦 当前已安装:")
    logging.info("  • isage (meta package) - 核心包管理")
    logging.info("  • isage-kernel - 数据处理内核")
    logging.info("  • isage-middleware - 中间件服务")
    logging.info("  • isage-libs - 应用示例")

    logging.info("\n🔧 可选功能包 (推荐安装):")
    logging.info("  • CLI 工具:")
    logging.info("    pip install isage-common[basic]")
    logging.info("  • 开发工具:")
    logging.info("    pip install isage-tools")
    logging.info("  • Web 前端:")
    logging.info("    pip install isage-tools")
    logging.info("  • 完整功能:")
    logging.info("    pip install isage-common[full]")

    logging.info("\n🚀 快速开始:")
    logging.info('  • 查看帮助: python -c "import sage; help(sage)"')
    logging.info('  • 运行示例: python -c "from sage.apps.examples import hello_world"')

    logging.info("\n📚 更多信息:")
    logging.info("  • 文档: https://intellistream.github.io/SAGE-Pub/")
    logging.info("  • GitHub: https://github.com/intellistream/SAGE")

    logging.info("\n💡 提示: 根据使用需求选择安装对应的功能包")
    logging.info("=" * 60 + "\n")


# 使用 pyproject.toml 作为主要配置，这里只处理 post-install hooks
setup(
    cmdclass={
        "install": PostInstallCommand,
        "develop": PostDevelopCommand,
    },
)

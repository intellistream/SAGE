#!/usr/bin/env python3
"""
SAGE Meta Package Setup Script
提供安装后的用户友好提示
"""

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
    print("\n" + "=" * 60)
    print("🎉 SAGE 核心安装完成！")
    print("=" * 60)

    print("\n📦 当前已安装 (核心组件):")
    print("  • isage-common - L1 基础工具和公共模块")
    print("  • isage-kernel - L3 核心运行时和任务执行引擎")
    print("  • isage-libs - L3 算法库和 Agent 框架")
    print("  • isage-middleware - L4 RAG/LLM operators")

    print("\n🔧 推荐安装选项:")
    print("  • 标准开发环境 (含科学计算库):")
    print("    pip install isage[standard]")
    print("  • 完整功能 (含示例和测试工具) [需要其他包发布]:")
    print("    pip install isage[full]")
    print("  • 框架开发 (修改 SAGE 源代码) [需要其他包发布]:")
    print("    pip install isage[dev]")

    print("\n⚠️  注意:")
    print("  某些功能包尚未发布到 PyPI，完整功能需要从源码安装：")
    print("  git clone https://github.com/intellistream/SAGE.git")
    print("  cd SAGE && pip install -e packages/sage[dev]")

    print("\n🚀 快速开始:")
    print('  • 查看版本: python -c "import sage; print(sage.__version__)"')
    print('  • 导入核心模块: python -c "from sage import kernel, libs"')

    print("\n📚 更多信息:")
    print("  • 文档: https://intellistream.github.io/SAGE-Pub/")
    print("  • GitHub: https://github.com/intellistream/SAGE")

    print("\n💡 提示: 当前版本仅包含核心功能，CLI/Web UI 等将在后续发布")
    print("=" * 60 + "\n")


# 使用 pyproject.toml 作为主要配置，这里只处理 post-install hooks
setup(
    cmdclass={
        "install": PostInstallCommand,
        "develop": PostDevelopCommand,
    },
)

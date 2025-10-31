"""
SAGE 开发工具 CLI - 重定向到统一CLI结构

这个文件现在重定向到新的统一CLI结构。
请使用: sage-dev <command> 而不是直接调用这个模块。
"""

import warnings


def _warn_deprecated():
    """显示弃用警告"""
    warnings.warn(
        "sage.tools.dev.cli 已迁移到 sage.tools.cli.commands.dev。"
        "请使用 'sage-dev <command>' 命令。",
        DeprecationWarning,
        stacklevel=3,
    )


try:
    from sage.tools.cli.commands.dev import app as dev_app

    _warn_deprecated()
    # 为了向后兼容，导出dev app
    cli = dev_app
except ImportError:
    # 如果统一CLI还没有安装，提供基本的错误信息
    import sys

    def cli():
        print("错误: 统一CLI结构未找到。请确保SAGE已正确安装。")
        print("使用命令: sage-dev <command>")
        sys.exit(1)


if __name__ == "__main__":
    cli()

"""SAGE 开发工具 CLI 入口。"""

from sage.tools.cli.commands.dev import app as cli

app = cli

__all__ = ["cli", "app"]


if __name__ == "__main__":
    cli()

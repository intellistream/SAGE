#!/usr/bin/env python3
"""
SAGE C++ Extensions Test Command
===============================

测试 SAGE C++ 扩展的安装和功能
"""

from pathlib import Path

import typer

app = typer.Typer(name="test", help="🧪 测试 C++ 扩展")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    🧪 SAGE C++ 扩展测试工具

    专门用于测试 C++ 扩展的安装和功能
    """
    if ctx.invoked_subcommand is None:
        # 如果没有子命令，显示帮助信息
        typer.echo("🧪 SAGE C++ 扩展测试")
        typer.echo("=" * 40)
        typer.echo()
        typer.echo("可用命令:")
        typer.echo("  cpp-extensions  - 快速测试 C++ 扩展安装和导入")
        typer.echo()
        typer.echo("完整测试套件:")
        typer.echo("  sage-dev test   - 运行完整的测试套件 (包括 C++ 扩展和示例)")
        typer.echo("  sage-dev examples test - 运行所有示例程序")
        typer.echo()
        typer.echo("使用 'sage test COMMAND --help' 查看具体命令的帮助")


@app.command(name="cpp-extensions")
def cpp_extensions():
    """测试 C++ 扩展的安装和导入"""
    typer.echo("🧪 SAGE C++ 扩展测试")
    typer.echo("=" * 40)

    success_count = 0
    total_tests = 4

    # 测试列表
    tests = [
        (
            "sage_db 扩展",
            "from sage.middleware.components.sage_db.python.sage_db import SageDB",
        ),
        (
            "sage_flow 扩展",
            "from sage.middleware.components.sage_flow.python.sage_flow import StreamEnvironment",
        ),
        (
            "sage_db micro_service",
            "from sage.middleware.components.sage_db.python.micro_service.sage_db_service import SageDBService",
        ),
        (
            "sage_flow micro_service",
            "from sage.middleware.components.sage_flow.python.micro_service.sage_flow_service import SageFlowService",
        ),
    ]

    for test_name, import_statement in tests:
        if check_extension_import(test_name, import_statement):
            success_count += 1

    typer.echo()
    typer.echo(f"📊 测试结果: {success_count}/{total_tests}")

    if success_count == total_tests:
        typer.echo("🎉 所有扩展测试通过！")
        return True
    else:
        typer.echo("⚠️  部分扩展测试失败")
        return False


def check_extension_import(test_name: str, import_statement: str) -> bool:
    """测试模块导入（辅助函数，不是 pytest 测试）"""
    typer.echo(f"🔍 测试 {test_name}...")

    try:
        exec(import_statement)
        typer.echo(f"✅ {test_name} 导入成功")
        return True
    except ImportError as e:
        typer.echo(f"❌ {test_name} 导入失败: {e}")
        return False
    except Exception as e:
        typer.echo(f"⚠️  {test_name} 导入异常: {e}")
        return False


def find_sage_root() -> Path | None:
    """查找 SAGE 项目根目录"""
    current = Path.cwd()

    # 向上查找包含 package.json 的目录
    for parent in [current] + list(current.parents):
        if (parent / "package.json").exists():
            return parent
        if (parent / "packages" / "sage-tools").exists():
            return parent

    return None


if __name__ == "__main__":
    app()

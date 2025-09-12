#!/usr/bin/env python3
"""
SAGE CLI Doctor Command
诊断SAGE安装和配置
"""

import typer

app = typer.Typer(name="doctor", help="🔍 系统诊断")


@app.command()
def check():
    """诊断SAGE安装和配置"""
    print("🔍 SAGE 系统诊断")
    print("=" * 40)

    # 检查Python版本
    import sys

    print(f"Python版本: {sys.version.split()[0]}")

    # 检查SAGE安装
    try:
        import sage.common
        print(f"✅ SAGE安装: v{sage.common.__version__}")
    except ImportError as e:
        print(f"❌ SAGE未安装: {e}")

    # 检查扩展 - 只检查实际存在的模块
    extensions = [
        ("sage_db", "sage.middleware.components.sage_db")
    ]
    
    for ext_name, ext_path in extensions:
        try:
            __import__(ext_path)
            print(f"✅ {ext_name}")
        except ImportError:
            print(f"⚠️ {ext_name} 不可用")

    # 检查Ray
    try:
        import ray
        print(f"✅ Ray: v{ray.__version__}")
    except ImportError:
        print("❌ Ray未安装")

    print("\n💡 如需安装扩展，运行: sage extensions install")


# 为了向后兼容，也提供一个直接的doctor命令
@app.callback(invoke_without_command=True)
def doctor_callback(ctx: typer.Context):
    """诊断SAGE安装和配置"""
    if ctx.invoked_subcommand is None:
        check()

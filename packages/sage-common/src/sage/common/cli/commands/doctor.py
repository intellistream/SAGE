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
        import sage
        print(f"✅ SAGE安装: v{sage.__version__}")
    except ImportError:
        print("❌ SAGE未安装")
    
    # 检查扩展
    extensions = ["sage_ext", "sage_ext.sage_queue", "sage_ext.sage_db"]
    for ext in extensions:
        try:
            __import__(ext)
            print(f"✅ {ext}")
        except ImportError:
            print(f"⚠️ {ext} 不可用")
    
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

"""
SAGE Framework Monorepo Workspace

这是 SAGE Framework 的 Monorepo 工作空间根包。
安装此包会自动安装所有 SAGE 子包。

子包包括：
- sage-kernel: 统一内核层
- sage-middleware: 中间件层  
- sage-userspace: 用户空间层
- sage-cli: CLI工具
- sage-frontend: 前端工具
- sage-dev-toolkit: 开发工具包
"""

__version__ = "1.0.0"
__author__ = "IntelliStream Team"
__email__ = "sage@intellistream.cc"

# 导入主要的 sage 包（如果可用）
try:
    import sage
    from sage import __version__ as sage_version
    print(f"SAGE Framework v{sage_version} 已加载")
except ImportError:
    print("SAGE 核心包未安装，请运行: pip install -e packages/sage-kernel")

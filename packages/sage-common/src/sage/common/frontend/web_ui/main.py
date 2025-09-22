"""
SAGE Frontend Server Main Entry Point

This module provides the main entry point for the SAGE Frontend server.
"""


def _load_version():
    """加载版本信息"""
    try:
        # 尝试从本地包的版本文件加载
        from sage.common._version import __version__
        return {
            'version': __version__,
            'python_requires': '>=3.10',
            'python_supported': ['3.10', '3.11', '3.12']
        }
    except ImportError:
        # 如果本地版本文件不存在，尝试从项目根目录加载（开发环境）
        try:
            from pathlib import Path
            current_file = Path(__file__).resolve()
            root_dir = current_file.parent.parent.parent.parent.parent.parent.parent  # 向上7层到项目根目录
            version_file = root_dir / "_version.py"
            
            if version_file.exists():
                version_globals = {}
                with open(version_file, 'r', encoding='utf-8') as f:
                    exec(f.read(), version_globals)
                return {
                    'version': version_globals.get('__version__', '0.1.4'),
                    'python_requires': version_globals.get('__python_requires__', '>=3.10'),
                    'python_supported': version_globals.get('__python_supported_versions__', ['3.10', '3.11', '3.12'])
                }
        except Exception:
            pass
    
    # 最后的默认值
    return {
        'version': '0.1.4',
        'python_requires': '>=3.10',
        'python_supported': ['3.10', '3.11', '3.12']
    }


def main():
    """Main entry point for sage-frontend server"""

    # 简单的参数解析来支持 --help 和 version 命令
    import argparse

    parser = argparse.ArgumentParser(description="SAGE Web UI")
    parser.add_argument('command', nargs='?', help='Command to run (version, start)')
    parser.add_argument(
        '--version', action='store_true', help='Show version information'
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to (default: 8080)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    # 处理版本命令
    if args.command == 'version' or args.version:
        info = _load_version()
        print("🌐 SAGE Web UI")
        print(f"Version: {info['version']}")
        print(f"Author: {info['author']}")
        print(f"Repository: {info['repository']}")
        return 0

    # 处理help命令
    if args.command == 'help' or not args.command:
        parser.print_help()
        print("\nAvailable commands:")
        print("  version    Show version information")
        print("  start      Start the frontend server")
        print("\nExample usage:")
        print("  python -m sage.common.frontend.web_ui.main start")
        print("  python -m sage.common.frontend.web_ui.main start --host 0.0.0.0 --port 8080")
        print("  python -m sage.common.frontend.web_ui.main start --reload")
        return 0

    # 处理start命令
    if args.command == "start":
        try:
            from .app import start_server
            print(f"🚀 启动 SAGE Web UI...")
            start_server(host=args.host, port=args.port, reload=args.reload)
            return 0
        except ImportError as e:
            print(f"❌ Failed to import server application: {e}")
            print("💡 Make sure all dependencies are installed: pip install -e .[dev]")
            return 1
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return 1

    # 其他命令暂时不支持
    print("Available commands: version, help, start")
    return 1


if __name__ == "__main__":
    exit(main())

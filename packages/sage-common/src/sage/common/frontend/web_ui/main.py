"""
SAGE Frontend Server Main Entry Point

This module provides the main entry point for the SAGE Frontend server.
"""


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
        print("🌐 SAGE Web UI")
        print("Version: 0.1.0")
        print("Author: IntelliStream Team")
        print("Repository: https://github.com/intellistream/SAGE")
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

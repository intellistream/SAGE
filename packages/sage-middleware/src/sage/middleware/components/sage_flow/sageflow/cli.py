"""
SAGE Flow 命令行接口

提供SAGE Flow的命令行工具和实用命令。
"""

import argparse
import sys
from typing import List, Optional

from .utils import get_version_info, print_system_info, check_dependencies
from . import __version__


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="sage-flow",
        description="SAGE Flow - High-Performance Stream Processing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"SAGE Flow {__version__}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # info 命令
    info_parser = subparsers.add_parser(
        "info",
        help="Show system and dependency information"
    )
    info_parser.add_argument(
        "--format", "-f",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    # check 命令
    check_parser = subparsers.add_parser(
        "check",
        help="Check dependencies and extensions"
    )
    
    # benchmark 命令
    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Run performance benchmarks"
    )
    benchmark_parser.add_argument(
        "--suite", "-s",
        choices=["basic", "full", "custom"],
        default="basic",
        help="Benchmark suite to run"
    )
    
    return parser


def cmd_info(args: argparse.Namespace) -> int:
    """处理info命令"""
    if args.format == "json":
        import json
        info = get_version_info()
        print(json.dumps(info, indent=2))
    else:
        print_system_info()
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """处理check命令"""
    print("Checking SAGE Flow dependencies...")
    print("=" * 40)
    
    dependencies = check_dependencies()
    all_good = True
    
    for package, available in dependencies.items():
        status = "✓ OK" if available else "✗ MISSING"
        print(f"{package:25} {status}")
        if not available:
            all_good = False
    
    print()
    if all_good:
        print("✓ All dependencies are available!")
        return 0
    else:
        print("✗ Some dependencies are missing. Please install them.")
        return 1


def cmd_benchmark(args: argparse.Namespace) -> int:
    """处理benchmark命令"""
    try:
        from .utils import require_extensions
        require_extensions()
    except Exception as e:
        print(f"Error: Cannot run benchmarks - {e}")
        return 1
    
    print(f"Running {args.suite} benchmark suite...")
    print("=" * 40)
    
    # 这里可以添加实际的基准测试代码
    print("Benchmark functionality not yet implemented.")
    print("This will be added in future versions.")
    
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """主入口函数"""
    parser = create_parser()
    args = parser.parse_args(argv)
    
    if args.command is None:
        parser.print_help()
        return 0
    
    # 路由到相应的命令处理函数
    if args.command == "info":
        return cmd_info(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "benchmark":
        return cmd_benchmark(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
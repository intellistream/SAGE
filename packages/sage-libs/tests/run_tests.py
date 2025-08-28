#!/usr/bin/env python3
"""
SAGE Apps 测试运行脚本
提供灵活的测试运行选项和报告生成

使用示例:
    python run_tests.py --rag              # 运行所有RAG测试
    python run_tests.py --chunk --verbose  # 运行chunk测试并显示详细输出
    python run_tests.py --unit --coverage  # 运行单元测试并生成覆盖率报告
    python run_tests.py --lib --html-coverage  # 运行lib测试并生成HTML覆盖率报告
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def get_project_root():
    """获取项目根目录"""
    return Path(__file__).parent


def run_command(cmd, description=""):
    """运行命令并处理错误"""
    if description:
        print(f"\n{'='*60}")
        print(f"执行: {description}")
        print(f"命令: {' '.join(cmd)}")
        print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="SAGE Apps 测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --rag                    运行所有RAG模块测试
  %(prog)s --chunk --verbose        运行chunk测试并显示详细输出
  %(prog)s --unit --coverage        运行单元测试并生成覆盖率报告
  %(prog)s --lib --html-coverage    运行lib测试并生成HTML覆盖率报告
  %(prog)s --generator --failfast   运行generator测试，遇到失败立即停止
        """
    )
    
    # 测试类型选项
    parser.add_argument("--unit", action="store_true", help="只运行单元测试")
    parser.add_argument("--integration", action="store_true", help="只运行集成测试")
    parser.add_argument("--slow", action="store_true", help="包含耗时测试")
    parser.add_argument("--external", action="store_true", help="包含外部依赖测试")
    
    # 测试范围选项
    parser.add_argument("--lib", action="store_true", help="只测试lib模块")
    parser.add_argument("--userspace", action="store_true", help="只测试userspace模块")
    
    # 具体模块选项
    parser.add_argument("--agents", action="store_true", help="只测试agents模块")
    parser.add_argument("--rag", action="store_true", help="只测试rag模块")
    parser.add_argument("--io", action="store_true", help="只测试io模块")
    parser.add_argument("--tools", action="store_true", help="只测试tools模块")
    
    # RAG子模块选项
    parser.add_argument("--chunk", action="store_true", help="只测试chunk模块")
    parser.add_argument("--evaluate", action="store_true", help="只测试evaluate模块")
    parser.add_argument("--generator", action="store_true", help="只测试generator模块")
    parser.add_argument("--promptor", action="store_true", help="只测试promptor模块")
    parser.add_argument("--retriever", action="store_true", help="只测试retriever模块")
    parser.add_argument("--reranker", action="store_true", help="只测试reranker模块")
    parser.add_argument("--pipeline", action="store_true", help="只测试pipeline模块")
    parser.add_argument("--longrefiner", action="store_true", help="只测试longrefiner模块")
    
    # 输出选项
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--html-coverage", action="store_true", help="生成HTML覆盖率报告")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--quiet", "-q", action="store_true", help="安静模式")
    
    # 其他选项
    parser.add_argument("--parallel", "-n", type=int, help="并行运行测试的进程数")
    parser.add_argument("--failfast", "-x", action="store_true", help="遇到第一个失败就停止")
    parser.add_argument("--lf", action="store_true", help="只运行上次失败的测试")
    parser.add_argument("--collect-only", action="store_true", help="只收集测试，不运行")
    
    args = parser.parse_args()
    
    # 构建pytest命令
    cmd = ["python", "-m", "pytest"]
    
    # 设置测试路径
    test_paths = []
    if args.lib:
        test_paths.append("lib/")
    elif args.userspace:
        test_paths.append("userspace/")
    elif args.agents:
        test_paths.append("lib/agents/")
    elif args.rag:
        test_paths.append("lib/rag/")
    elif args.io:
        test_paths.append("lib/io/")
    elif args.tools:
        test_paths.append("lib/tools/")
    # RAG子模块
    elif args.chunk:
        test_paths.append("lib/rag/test_chunk.py")
    elif args.evaluate:
        test_paths.append("lib/rag/test_evaluate.py")
    elif args.generator:
        test_paths.append("lib/rag/test_generator.py")
    elif args.promptor:
        test_paths.append("lib/rag/test_promptor.py")
    elif args.retriever:
        test_paths.append("lib/rag/test_retriever.py")
    elif args.reranker:
        test_paths.append("lib/rag/test_reranker.py")
    elif args.pipeline:
        test_paths.append("lib/rag/test_pipeline.py")
    elif args.longrefiner:
        test_paths.append("lib/rag/test_longrefiner_adapter.py")
    else:
        # 默认运行所有测试
        test_paths.append(".")
    
    cmd.extend(test_paths)
    
    # 添加标记过滤
    markers = []
    if args.unit and not args.integration:
        markers.append("unit")
    elif args.integration and not args.unit:
        markers.append("integration")
    
    if not args.slow:
        markers.append("not slow")
    
    if not args.external:
        markers.append("not external")
    
    if markers:
        cmd.extend(["-m", " and ".join(markers)])
    
    # 添加覆盖率选项
    if args.coverage or args.html_coverage:
        cmd.extend([
            "--cov=sage.libs",
            "--cov=sage.userspace",
            "--cov-report=term-missing"
        ])
        
        if args.html_coverage:
            cmd.append("--cov-report=html")
    
    # 添加输出选项
    if args.verbose:
        cmd.append("-v")
    elif args.quiet:
        cmd.append("-q")
    
    # 添加其他选项
    if args.parallel:
        cmd.extend(["-n", str(args.parallel)])
    
    if args.failfast:
        cmd.append("-x")
    
    if args.lf:
        cmd.append("--lf")
    
    if args.collect_only:
        cmd.append("--collect-only")
    
    # 运行测试
    print("SAGE Userspace 测试运行器")
    print("=" * 50)
    
    success = run_command(cmd, "运行测试")
    
    if success:
        print("\n✅ 测试运行完成")
        
        if args.html_coverage:
            print("📊 HTML覆盖率报告已生成: htmlcov/index.html")
    else:
        print("\n❌ 测试运行失败")
        sys.exit(1)


if __name__ == "__main__":
    main()

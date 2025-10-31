#!/usr/bin/env python3
"""
Medical Diagnosis System Example

This script demonstrates how to use the Medical Diagnosis application from sage-apps.
It provides AI-assisted medical imaging analysis using a multi-agent system.

Requirements:
    pip install -e packages/sage-apps[medical]

Usage:
    python examples/apps/run_medical_diagnosis.py
    python examples/apps/run_medical_diagnosis.py --case-id case_0001
    python examples/apps/run_medical_diagnosis.py --interactive

Test Configuration:
    @test_category: apps
    @test_speed: slow
    @test_requires: [medical, data]
    @test_skip_ci: true
    @test:skip - Requires medical dataset to be downloaded
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

try:
    from sage.apps.medical_diagnosis.run_diagnosis import main as diagnosis_main
except ImportError as e:
    print(f"Error importing sage.apps.medical_diagnosis: {e}")
    print("\nPlease install sage-apps with medical dependencies:")
    print("  pip install -e packages/sage-apps[medical]")
    sys.exit(1)


def check_and_setup_data(data_dir: str, auto_setup: bool = False) -> bool:
    """检查数据是否存在，如果不存在则提示用户自动设置"""
    data_path = Path(data_dir)
    processed_dir = data_path / "processed"

    # 检查数据是否存在
    if processed_dir.exists() and (processed_dir / "train_index.json").exists():
        return True

    print(f"\n{'=' * 60}")
    print("数据集未找到")
    print("=" * 60)
    print(f"期望的数据目录: {data_dir}")
    print("")

    # 查找 setup_data.sh 脚本
    setup_script = data_path.parent / "setup_data.sh"

    if not setup_script.exists():
        # 尝试其他可能的位置
        setup_script = (
            project_root
            / "packages/sage-apps/src/sage/apps/medical_diagnosis/setup_data.sh"
        )

    if not setup_script.exists():
        print("❌ 数据设置脚本未找到")
        print("")
        print("期望结构:")
        print("  {data_dir}/processed/images/")
        print("  {data_dir}/processed/train_index.json")
        print("  {data_dir}/processed/test_index.json")
        return False

    print(f"找到数据设置脚本: {setup_script}")
    print("")
    print("🤖 自动下载并准备数据集...")
    print("提示: 如果不想自动下载，请使用 Ctrl+C 取消")
    print("")
    print("开始自动设置数据集...")
    print("=" * 60)

    try:
        # 运行 setup_data.sh
        subprocess.run(
            ["bash", str(setup_script)],
            cwd=str(setup_script.parent),
            check=True,
            text=True,
        )

        print("=" * 60)
        print("✅ 数据集设置完成！")
        print("")
        return True

    except subprocess.CalledProcessError:
        print("=" * 60)
        print("❌ 数据集设置失败")
        print("")
        print("您可以手动运行以下命令来设置数据:")
        print(f"  bash {setup_script}")
        print("")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False


def main():
    """Run the medical diagnosis system."""
    parser = argparse.ArgumentParser(
        description="SAGE Medical Diagnosis System - AI-assisted medical imaging analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default demo case
  python %(prog)s

  # Analyze a specific case
  python %(prog)s --case-id case_0001

  # Interactive mode
  python %(prog)s --interactive

  # Use custom data directory
  python %(prog)s --data-dir path/to/medical/data

Features:
  - Multi-agent diagnostic workflow
  - Medical image analysis
  - Knowledge base integration
  - Diagnostic report generation
  - Interactive consultation mode
        """,
    )

    parser.add_argument(
        "--case-id", type=str, help="Specific case ID to analyze (e.g., case_0001)"
    )

    parser.add_argument(
        "--data-dir",
        type=str,
        default="packages/sage-apps/src/sage/apps/medical_diagnosis/data",
        help="Path to medical diagnosis data directory",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive consultation mode",
    )

    parser.add_argument(
        "--output", type=str, help="Output directory for diagnostic reports"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "--auto-setup",
        action="store_true",
        help="Automatically download and setup data without prompting",
    )

    args = parser.parse_args()

    # Check and setup data if needed
    if not check_and_setup_data(args.data_dir, auto_setup=args.auto_setup):
        print("\n⚠️  警告: 数据集未就绪")
        print("系统将尝试使用模拟数据运行...")
        print("")

    print("=" * 60)
    print("SAGE Medical Diagnosis System")
    print("=" * 60)
    print(f"Data Directory: {args.data_dir}")
    if args.case_id:
        print(f"Case ID: {args.case_id}")
    if args.interactive:
        print("Mode: Interactive")
    else:
        print("Mode: Automated Analysis")
    if args.output:
        print(f"Output: {args.output}")
    print("=" * 60)
    print()

    # Call the medical diagnosis main function
    try:
        diagnosis_main()
    except Exception as e:
        print(f"Error running medical diagnosis system: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

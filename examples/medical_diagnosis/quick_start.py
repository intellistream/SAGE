#!/usr/bin/env python3
"""
医疗诊断应用 - 快速入门示例

这是一个5分钟快速演示，展示如何使用医疗诊断应用的基本功能。

完整应用代码位于:
    packages/sage-libs/src/sage/libs/applications/medical_diagnosis/

在线文档:
    https://github.com/intellistream/SAGE/tree/main/packages/sage-libs/src/sage/libs/applications/medical_diagnosis

安装:
    pip install sage-libs[medical]

用法:
    python examples/medical_diagnosis/quick_start.py
"""

import sys
from pathlib import Path

# 添加项目路径以便导入
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "packages" / "sage-libs" / "src"))

from sage.libs.applications.medical_diagnosis import DiagnosticAgent


def quick_demo():
    """5分钟快速演示"""

    print("=" * 80)
    print("🏥 医疗诊断应用 - 快速演示")
    print("=" * 80)
    print()
    print("注意: 这是一个演示示例，使用模拟数据展示系统功能。")
    print("完整功能需要下载真实数据集。")
    print()

    # 初始化诊断Agent
    print("📋 步骤 1: 初始化诊断系统...")
    agent = DiagnosticAgent()
    print("✅ 系统初始化完成")
    print()

    # 模拟诊断请求
    print("📋 步骤 2: 执行诊断分析...")

    # 使用模拟数据（不需要真实图像文件）
    result = agent.diagnose(
        image_path="demo_mri.jpg",  # 模拟路径，系统会自动使用mock数据
        patient_info={
            "patient_id": "DEMO_001",
            "age": 45,
            "gender": "male",
            "symptoms": "腰痛伴下肢放射痛",
        },
        verbose=True,
    )

    print()
    print("=" * 80)
    print("📊 诊断完成")
    print("=" * 80)
    print()
    print(f"✅ 诊断结果: {', '.join(result.diagnoses)}")
    print(f"✅ 置信度: {result.confidence:.1%}")
    print(f"✅ 发现数量: {len(result.findings)} 处")
    print(f"✅ 相似病例: {len(result.similar_cases)} 个")
    print()

    print("=" * 80)
    print("🚀 下一步")
    print("=" * 80)
    print()
    print("1️⃣  查看完整应用代码:")
    print("    packages/sage-libs/src/sage/libs/applications/medical_diagnosis/")
    print()
    print("2️⃣  准备真实数据集:")
    print("    cd packages/sage-libs/src/sage/libs/applications/medical_diagnosis/")
    print("    ./setup_data.sh")
    print()
    print("3️⃣  运行完整测试:")
    print("    python -m sage.libs.applications.medical_diagnosis.test_diagnosis")
    print()
    print("4️⃣  交互式诊断:")
    print(
        "    python -m sage.libs.applications.medical_diagnosis.run_diagnosis --interactive"
    )
    print()
    print("=" * 80)


def show_features():
    """展示主要功能特性"""
    print()
    print("=" * 80)
    print("📚 医疗诊断应用主要功能")
    print("=" * 80)
    print()
    print("🔹 多Agent协作:")
    print("   • DiagnosticAgent - 主协调Agent")
    print("   • ImageAnalyzer - MRI影像分析")
    print("   • ReportGenerator - 诊断报告生成")
    print()
    print("🔹 智能诊断流程:")
    print("   • 影像特征提取 (椎体、椎间盘识别)")
    print("   • 病变检测 (退行性变、突出等)")
    print("   • 知识库检索 (相似病例、医学知识)")
    print("   • 报告生成 (结构化诊断报告)")
    print()
    print("🔹 支持的数据:")
    print("   • 数据集: UniDataPro/lumbar-spine-mri")
    print("   • 腰椎MRI影像 (T2加权矢状位)")
    print("   • 医疗诊断报告")
    print("   • 疾病标注")
    print()
    print("🔹 使用模式:")
    print("   • 单病例诊断")
    print("   • 批量诊断")
    print("   • 交互式会话")
    print()
    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="医疗诊断应用快速演示",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--show-features", action="store_true", help="显示功能特性而不运行演示"
    )

    args = parser.parse_args()

    if args.show_features:
        show_features()
    else:
        try:
            quick_demo()
        except Exception as e:
            print(f"\n❌ 演示运行出错: {e}")
            print("\n提示: 确保已安装依赖:")
            print("    pip install sage-libs")
            import traceback

            traceback.print_exc()

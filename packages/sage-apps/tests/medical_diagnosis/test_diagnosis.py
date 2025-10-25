#!/usr/bin/env python3
"""
医疗诊断系统简单测试
使用预处理好的数据测试诊断流程（不需要真实的SAGE服务）
"""

import json
import random
from pathlib import Path

# 获取医疗诊断目录路径（用于访问数据和配置文件）
medical_diagnosis_dir = (
    Path(__file__).parent.parent.parent / "src" / "sage" / "apps" / "medical_diagnosis"
)

# 导入医疗诊断模块
from sage.apps.medical_diagnosis.agents.diagnostic_agent import DiagnosticAgent


def test_single_case():
    """测试单个病例诊断"""
    import pytest

    print("=" * 80)
    print("🧪 医疗诊断系统测试 - 单病例模式")
    print("=" * 80)

    # 加载测试数据
    data_dir = medical_diagnosis_dir / "data" / "processed"
    test_index_path = data_dir / "test_index.json"

    if not test_index_path.exists():
        pytest.skip(
            f"Test data not available at {test_index_path}. Run scripts/prepare_data.py first to generate test data."
        )

    with open(test_index_path, encoding="utf-8") as f:
        test_cases = json.load(f)

    # 随机选择一个测试病例
    case = random.choice(test_cases)

    print("\n📋 测试病例信息:")
    print(f"   - 病例ID: {case['case_id']}")
    print(f"   - 患者ID: {case['patient_id']}")
    print(f"   - 年龄: {case['age']}岁")
    print(f"   - 性别: {case['gender']}")
    print(f"   - 真实疾病: {case['disease']}")
    print(f"   - 严重程度: {case['severity']}")

    # 构建完整路径
    image_path = data_dir / case["image_path"]

    print(f"\n📸 MRI影像: {image_path}")
    print(f"   (文件存在: {image_path.exists()})")

    # 准备患者信息
    patient_info = {
        "patient_id": case["patient_id"],
        "age": case["age"],
        "gender": case["gender"],
        "symptoms": "腰痛伴下肢放射痛" if case["severity"] != "无" else "体检发现",
    }

    # 初始化诊断系统
    print("\n🔧 初始化诊断系统...")

    config_path = medical_diagnosis_dir / "config" / "agent_config.yaml"

    try:
        # 创建诊断Agent
        agent = DiagnosticAgent(config_path=str(config_path))
        print("   ✓ DiagnosticAgent 初始化成功")

        # 执行诊断
        print("\n🔍 开始诊断...")
        result = agent.diagnose(image_path=str(image_path), patient_info=patient_info)

        # 显示结果
        print("\n" + "=" * 80)
        print("📊 诊断结果摘要")
        print("=" * 80)

        print(f"\n病例ID: {case['patient_id']}")
        print(f"诊断时间: {result.timestamp}")
        print("\n影像分析:")
        print(f"  - 质量评分: {result.quality_score:.2f}")
        print(f"  - 检测到的病变: {len(result.findings)} 处")

        print("\n主要发现:")
        for finding in result.findings[:3]:
            print(f"  - {finding}")

        print("\n诊断结论:")
        for i, diagnosis in enumerate(result.diagnoses, 1):
            print(f"  {i}. {diagnosis}")

        print(f"\n  置信度: {result.confidence:.2%}")

        print(f"\n相似病例参考: {len(result.similar_cases)} 个")

        print("\n📄 完整诊断报告:")
        print("-" * 80)
        print(result.report)
        print("-" * 80)

        # 对比真实标签
        print(f"\n✅ 真实疾病: {case['disease']}")
        print(f"   诊断结果中是否包含: {'是' if case['disease'] in result.report else '否'}")

    except Exception as e:
        print(f"❌ 诊断过程出错: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)


def test_batch_mode():
    """测试批量诊断模式"""
    import pytest

    print("=" * 80)
    print("🧪 医疗诊断系统测试 - 批量模式")
    print("=" * 80)

    # 加载测试数据
    data_dir = medical_diagnosis_dir / "data" / "processed"
    test_index_path = data_dir / "test_index.json"

    if not test_index_path.exists():
        pytest.skip(
            f"Test data not available at {test_index_path}. Run scripts/prepare_data.py first to generate test data."
        )

    with open(test_index_path, encoding="utf-8") as f:
        test_cases = json.load(f)

    # 选择前5个病例
    cases_to_test = test_cases[:5]

    print(f"\n📋 准备批量诊断 {len(cases_to_test)} 个病例...")

    # 准备批量病例
    batch_cases = []
    for case in cases_to_test:
        image_path = data_dir / case["image_path"]
        patient_info = {
            "patient_id": case["patient_id"],
            "age": case["age"],
            "gender": case["gender"],
            "symptoms": "腰痛" if case["severity"] != "无" else "体检",
        }
        batch_cases.append(
            {
                "image_path": str(image_path),
                "patient_info": patient_info,
            }
        )

    # 初始化Agent
    config_path = medical_diagnosis_dir / "config" / "agent_config.yaml"
    agent = DiagnosticAgent(config_path=str(config_path))

    # 批量诊断
    print("\n🔍 开始批量诊断...")
    output_dir = medical_diagnosis_dir / "data" / "test_results"

    results = agent.batch_diagnose(cases=batch_cases, output_dir=str(output_dir))

    # 显示结果摘要
    print("\n" + "=" * 80)
    print("📊 批量诊断结果摘要")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(f"\n{i}. 病例 {cases_to_test[i-1]['case_id']}")
        print(f"   诊断: {', '.join(result.diagnoses)}")
        print(f"   置信度: {result.confidence:.2%}")
        print(f"   发现: {len(result.findings)} 处")

    print(f"\n✅ 批量诊断完成，结果已保存到: {output_dir}")
    print("=" * 80)


def main():
    """主函数"""

    import argparse

    parser = argparse.ArgumentParser(description="医疗诊断系统测试")
    parser.add_argument(
        "--mode",
        type=str,
        default="single",
        choices=["single", "batch"],
        help="测试模式: single(单病例) 或 batch(批量)",
    )

    args = parser.parse_args()

    if args.mode == "single":
        test_single_case()
    elif args.mode == "batch":
        test_batch_mode()


if __name__ == "__main__":
    main()

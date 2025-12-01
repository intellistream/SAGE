#!/usr/bin/env python3
"""
演示医学知识库的知识加载功能
Demonstrate the knowledge loading functionality of the MedicalKnowledgeBase
"""

import json
import sys
from pathlib import Path

# Add the source directory to the path
src_dir = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from sage.apps.medical_diagnosis.tools.knowledge_base import MedicalKnowledgeBase


def create_sample_data():
    """创建示例数据文件用于演示"""
    print("=" * 80)
    print("创建示例数据文件...")
    print("=" * 80)

    # 创建临时数据目录
    data_dir = Path(__file__).parent / "test_data"
    data_dir.mkdir(exist_ok=True)

    # 创建报告目录
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(exist_ok=True)

    # 创建示例报告
    sample_reports = [
        {
            "filename": "case_0001_report.txt",
            "content": """患者信息:
  年龄: 48岁
  性别: 男
  主诉: 腰痛伴左下肢放射痛

影像描述:
  腰椎MRI T2加权矢状位: L4/L5椎间盘向后突出，压迫硬膜囊。相应节段椎管变窄，神经根可能受压。

主要发现:
  - 病变节段: L4/L5
  - 病变类型: 椎间盘突出
  - 严重程度: 中度

诊断结论:
  L4/L5椎间盘突出症，程度中度。

治疗建议:
  建议卧床休息2-3周，牵引治疗。口服非甾体抗炎药及神经营养药物。保守治疗无效时考虑手术治疗。

注: 本报告仅供参考，请结合临床症状和其他检查结果综合判断。
""",
        },
        {
            "filename": "case_0002_report.txt",
            "content": """患者信息:
  年龄: 60岁
  性别: 男
  主诉: 慢性腰痛

影像描述:
  腰椎MRI T2加权矢状位: L3/L4, L4/L5, L5/S1多节段退行性变。椎管尚通畅，未见明显神经根受压。

主要发现:
  - 病变节段: 多节段
  - 病变类型: 多节段退行性变
  - 严重程度: 中度

诊断结论:
  腰椎退行性变，L3/L4、L4/L5椎间盘突出，程度中度。

治疗建议:
  适当休息，避免久坐久站。可进行腰背肌锻炼，如游泳、普拉提等。必要时物理治疗。

注: 本报告仅供参考，请结合临床症状和其他检查结果综合判断。
""",
        },
    ]

    for report in sample_reports:
        report_path = reports_dir / report["filename"]
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report["content"])
        print(f"  ✓ 创建报告: {report['filename']}")

    # 创建统计文件
    stats = {
        "total_samples": 100,
        "train_samples": 80,
        "test_samples": 20,
        "disease_distribution": {
            "正常": 10,
            "轻度退行性变": 20,
            "椎间盘突出": 25,
            "多节段退行性变": 15,
            "椎管狭窄": 12,
            "椎间盘脱出": 8,
            "骨质增生": 10,
        },
    }

    stats_path = data_dir / "stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print("  ✓ 创建统计文件: stats.json")

    # 创建病例数据库
    cases = [
        {
            "case_id": "case_0001",
            "patient_id": "P0001",
            "age": 48,
            "gender": "男",
            "disease": "椎间盘突出",
            "severity": "中度",
            "image_path": "images/case_0001.jpg",
            "report_path": "reports/case_0001_report.txt",
        },
        {
            "case_id": "case_0002",
            "patient_id": "P0002",
            "age": 60,
            "gender": "男",
            "disease": "多节段退行性变",
            "severity": "中度",
            "image_path": "images/case_0002.jpg",
            "report_path": "reports/case_0002_report.txt",
        },
    ]

    all_cases_path = data_dir / "all_cases.json"
    with open(all_cases_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)
    print("  ✓ 创建病例数据库: all_cases.json")

    print(f"\n✓ 示例数据创建完成，保存在: {data_dir.absolute()}")
    print()

    return str(data_dir)


def test_knowledge_loading():
    """测试知识加载功能"""
    print("=" * 80)
    print("测试医学知识库 - 不使用数据集")
    print("=" * 80)
    print()

    # 测试1：不使用数据集
    print("1️⃣  测试基本初始化（仅使用默认知识）")
    print("-" * 80)
    config = {}
    kb = MedicalKnowledgeBase(config)

    print("\n📊 知识库统计:")
    print(f"  - 知识条目总数: {len(kb.knowledge_base)}")
    print(f"  - 病例数据库大小: {len(kb.case_database)}")

    print("\n📚 默认知识主题:")
    for i, knowledge in enumerate(kb.knowledge_base[:5], 1):
        topic = knowledge.get("topic", "Unknown")
        source = knowledge.get("source", "default")
        print(f"  {i}. {topic} (来源: {source})")

    print("\n" + "=" * 80)
    print()

    # 测试2：使用示例数据
    print("2️⃣  测试从数据集加载知识")
    print("-" * 80)

    # 创建示例数据
    data_path = create_sample_data()

    config_with_data = {"data_path": data_path}
    kb_with_data = MedicalKnowledgeBase(config_with_data)

    print("\n📊 知识库统计（使用数据集）:")
    print(f"  - 知识条目总数: {len(kb_with_data.knowledge_base)}")
    print(f"  - 病例数据库大小: {len(kb_with_data.case_database)}")

    print("\n📚 知识主题:")
    for i, knowledge in enumerate(kb_with_data.knowledge_base, 1):
        topic = knowledge.get("topic", "Unknown")
        source = knowledge.get("source", "default")
        case_count = knowledge.get("case_count", "N/A")
        if case_count != "N/A":
            print(f"  {i}. {topic} (来源: {source}, 病例数: {case_count})")
        else:
            print(f"  {i}. {topic} (来源: {source})")

    print("\n" + "=" * 80)
    print()

    # 测试3：知识检索
    print("3️⃣  测试知识检索功能")
    print("-" * 80)

    queries = ["腰椎间盘突出", "退行性变", "椎管狭窄"]

    for query in queries:
        results = kb_with_data.retrieve_knowledge(query, top_k=2)
        print(f"\n🔍 查询: '{query}'")
        print(f"   找到 {len(results)} 条相关知识:")
        for i, result in enumerate(results, 1):
            topic = result.get("topic", "Unknown")
            print(f"   {i}. {topic}")

    print("\n" + "=" * 80)
    print()

    # 测试4：相似病例检索
    print("4️⃣  测试相似病例检索")
    print("-" * 80)

    queries_cases = ["椎间盘突出", "退行性变", "腰痛"]

    for query in queries_cases:
        results = kb_with_data.retrieve_similar_cases(query, {}, top_k=3)
        print(f"\n🔍 查询: '{query}'")
        print(f"   找到 {len(results)} 个相似病例:")
        for i, case in enumerate(results, 1):
            case_id = case.get("case_id", "Unknown")
            diagnosis = case.get("diagnosis", "Unknown")
            score = case.get("similarity_score", 0.0)
            print(f"   {i}. {case_id}: {diagnosis} (相似度: {score:.2f})")

    print("\n" + "=" * 80)
    print()

    # 清理测试数据
    print("🧹 清理测试数据...")
    import shutil

    test_data_dir = Path(__file__).parent / "test_data"
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)
        print("  ✓ 测试数据已删除")

    print("\n" + "=" * 80)
    print("✅ 测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    test_knowledge_loading()

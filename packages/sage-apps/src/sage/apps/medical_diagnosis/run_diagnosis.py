#!/usr/bin/env python3
"""
腰椎MRI医疗诊断Agent - 主运行脚本

功能:
1. 单个病例诊断
2. 批量病例处理
3. 交互式诊断会话
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from sage.apps.medical_diagnosis.agents import DiagnosticAgent


def check_and_setup_data(auto_setup: bool = False):
    """检查数据是否存在，如果不存在则自动下载和准备"""
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent
    data_dir = current_dir / "data" / "processed"
    setup_script = current_dir / "setup_data.sh"
    
    # 检查数据是否存在
    if data_dir.exists() and (data_dir / "train_index.json").exists():
        print(f"✓ 数据集已就绪: {data_dir}")
        return True
    
    print(f"⚠️  数据集未找到: {data_dir}")
    print(f"")
    
    # 检查 setup_data.sh 是否存在
    if not setup_script.exists():
        print(f"❌ 数据设置脚本未找到: {setup_script}")
        print(f"")
        print(f"请手动准备数据或检查安装是否完整")
        return False
    
    # 自动下载数据
    print(f"数据集设置脚本: {setup_script}")
    print(f"")
    print("🤖 自动下载并准备数据集...")
    print(f"提示: 如果不想自动下载，请使用 Ctrl+C 取消")
    print(f"")
    print(f"开始自动设置数据集...")
    print(f"=" * 70)
    
    try:
        # 运行 setup_data.sh
        result = subprocess.run(
            ["bash", str(setup_script)],
            cwd=str(current_dir),
            check=True,
            text=True,
            capture_output=False
        )
        
        print(f"=" * 70)
        print(f"✅ 数据集设置完成！")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"=" * 70)
        print(f"❌ 数据集设置失败")
        print(f"")
        print(f"您可以手动运行以下命令来设置数据:")
        print(f"  bash {setup_script}")
        print(f"")
        print(f"或者查看错误日志以获取更多信息")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="腰椎MRI医疗诊断Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 诊断单个病例
  python run_diagnosis.py --image data/medical/test/case_001.jpg --age 45 --gender male --symptoms "腰痛伴左腿麻木"
  
  # 批量处理
  python run_diagnosis.py --batch data/medical/batch_cases/ --output output/diagnoses/
  
  # 交互式模式
  python run_diagnosis.py --interactive
        """,
    )

    # 单个病例诊断参数
    parser.add_argument("--image", "-i", type=str, help="MRI影像路径")

    parser.add_argument("--age", type=int, help="患者年龄")

    parser.add_argument(
        "--gender", type=str, choices=["male", "female"], help="患者性别 (male/female)"
    )

    parser.add_argument("--symptoms", type=str, help="患者症状描述")

    # 批量处理参数
    parser.add_argument("--batch", type=str, help="批量处理目录")

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="output/diagnoses/",
        help="输出目录 (默认: output/diagnoses/)",
    )

    # 其他参数
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="examples/medical_diagnosis/config/agent_config.yaml",
        help="配置文件路径",
    )

    parser.add_argument("--interactive", action="store_true", help="交互式模式")

    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    
    parser.add_argument("--auto-setup", action="store_true", help="自动下载并设置数据（无需确认）")

    return parser.parse_args()


def diagnose_single_case(
    agent: DiagnosticAgent,
    image_path: str,
    patient_info: Optional[Dict[str, Any]] = None,
    verbose: bool = True,
):
    """诊断单个病例"""
    print(f"\n{'='*70}")
    print(f"🏥 腰椎MRI诊断系统")
    print(f"{'='*70}\n")

    # 执行诊断
    result = agent.diagnose(
        image_path=image_path, patient_info=patient_info, verbose=verbose
    )

    print(f"\n{'='*70}")
    print(f"✅ 诊断完成")
    print(f"{'='*70}")
    # DiagnosisReport 使用 diagnoses (复数) 而不是 diagnosis
    if hasattr(result, 'diagnoses') and result.diagnoses:
        print(f"诊断: {', '.join(result.diagnoses)}")
    print(f"置信度: {result.confidence:.2%}")

    return result


def batch_diagnose(agent: DiagnosticAgent, batch_dir: str, output_dir: str):
    """批量诊断"""
    batch_path = Path(batch_dir)

    if not batch_path.exists():
        print(f"❌ 错误: 批量处理目录不存在: {batch_dir}")
        return

    # 查找所有图像文件
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.dcm"]:
        image_files.extend(batch_path.glob(ext))

    if not image_files:
        print(f"❌ 错误: 未找到图像文件")
        return

    print(f"\n🏥 批量诊断模式")
    print(f"{'='*70}")
    print(f"📂 输入目录: {batch_dir}")
    print(f"📁 输出目录: {output_dir}")
    print(f"📊 病例数量: {len(image_files)}")
    print(f"{'='*70}\n")

    # 构建病例列表
    cases = [
        {"image_path": str(img), "patient_info": {"case_id": img.stem}}
        for img in image_files
    ]

    # 批量处理
    results = agent.batch_diagnose(cases=cases, output_dir=output_dir)

    print(f"\n📊 批量诊断统计:")
    print(f"   总病例数: {len(results)}")

    # 统计诊断结果
    diagnoses_count = {}
    for result in results:
        diag = result.diagnosis
        diagnoses_count[diag] = diagnoses_count.get(diag, 0) + 1

    print(f"\n   诊断分布:")
    for diag, count in sorted(diagnoses_count.items(), key=lambda x: -x[1]):
        print(f"   - {diag}: {count} 例")


def interactive_mode(agent: DiagnosticAgent):
    """交互式诊断模式"""
    print(f"\n{'='*70}")
    print(f"🏥 腰椎MRI诊断系统 - 交互式模式")
    print(f"{'='*70}")
    print(f"\n输入 'exit' 或 'quit' 退出\n")

    while True:
        print(f"\n{'─'*70}")

        # 输入影像路径
        image_path = input("📄 请输入MRI影像路径: ").strip()

        if image_path.lower() in ["exit", "quit"]:
            print("\n👋 再见！")
            break

        if not image_path:
            print("❌ 路径不能为空")
            continue

        # 输入患者信息
        print("\n👤 患者信息（可选，直接回车跳过）:")

        age_input = input("   年龄: ").strip()
        age = int(age_input) if age_input.isdigit() else None

        gender_input = input("   性别 (male/female): ").strip().lower()
        gender = gender_input if gender_input in ["male", "female"] else None

        symptoms = input("   症状: ").strip()

        # 构建患者信息
        patient_info = {}
        if age:
            patient_info["age"] = age
        if gender:
            patient_info["gender"] = gender
        if symptoms:
            patient_info["symptoms"] = symptoms

        # 执行诊断
        try:
            result = agent.diagnose(
                image_path=image_path,
                patient_info=patient_info if patient_info else None,
                verbose=True,
            )
        except Exception as e:
            print(f"\n❌ 诊断失败: {e}")
            continue

        # 询问是否继续
        continue_input = input("\n是否继续诊断下一个病例? (y/n): ").strip().lower()
        if continue_input != "y":
            print("\n👋 再见！")
            break


def main():
    """主函数"""
    args = parse_args()

    # 检查并设置数据（如果需要）
    print(f"\n{'='*70}")
    print(f"📦 检查数据集状态...")
    print(f"{'='*70}\n")
    
    if not check_and_setup_data(auto_setup=args.auto_setup):
        print(f"\n⚠️  警告: 数据集未就绪")
        print(f"系统将使用模拟数据运行演示模式")
        print(f"")
    
    # 初始化Agent
    print(f"\n🚀 初始化诊断Agent...")
    print(f"{'='*70}")

    config_path = args.config if Path(args.config).exists() else None
    agent = DiagnosticAgent(config_path=config_path)

    print(f"{'='*70}\n")

    # 根据参数执行不同模式
    if args.interactive:
        # 交互式模式
        interactive_mode(agent)

    elif args.batch:
        # 批量处理模式
        batch_diagnose(agent=agent, batch_dir=args.batch, output_dir=args.output)

    elif args.image:
        # 单个病例诊断
        patient_info = {}
        if args.age:
            patient_info["age"] = args.age
        if args.gender:
            patient_info["gender"] = args.gender
        if args.symptoms:
            patient_info["symptoms"] = args.symptoms

        diagnose_single_case(
            agent=agent,
            image_path=args.image,
            patient_info=patient_info if patient_info else None,
            verbose=args.verbose,
        )

    else:
        # 演示模式（使用模拟数据）
        print(f"\n💡 演示模式（使用模拟数据）\n")
        print(f"提示: 使用 --help 查看完整使用说明\n")

        # 创建一个演示病例
        demo_image = "data/medical/demo/mri_case.jpg"
        demo_patient = {
            "age": 45,
            "gender": "male",
            "symptoms": "下背部疼痛，左腿麻木，持续2周",
        }

        diagnose_single_case(
            agent=agent, image_path=demo_image, patient_info=demo_patient, verbose=True
        )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
数据集探索脚本
用于查看腰椎MRI数据集的样本和统计信息
"""

import os
import sys
from pathlib import Path
from collections import Counter

import numpy as np
from PIL import Image
from datasets import load_from_disk

# 设置项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def explore_dataset():
    """探索数据集"""
    
    dataset_path = project_root / "data" / "medical" / "lumbar-spine-mri" / "cache"
    
    if not dataset_path.exists():
        print(f"❌ 数据集不存在: {dataset_path}")
        print("请先运行 scripts/download_lumbar_dataset.py 下载数据集")
        return
    
    print("=" * 80)
    print("📊 腰椎MRI数据集探索")
    print("=" * 80)
    
    # 加载数据集
    print(f"\n📂 从 {dataset_path} 加载数据集...")
    dataset = load_from_disk(str(dataset_path))
    
    # 基本信息
    print(f"\n📋 数据集基本信息:")
    print(f"   - 样本总数: {len(dataset)}")
    print(f"   - 字段: {dataset.column_names}")
    print(f"   - Features: {dataset.features}")
    
    # 标签分布
    labels = [sample['label'] for sample in dataset]
    label_counts = Counter(labels)
    
    print(f"\n🏷️  标签分布:")
    for label, count in sorted(label_counts.items()):
        percentage = count / len(dataset) * 100
        print(f"   - Label {label}: {count} samples ({percentage:.1f}%)")
    
    # 图像统计
    print(f"\n🖼️  图像统计 (前10个样本):")
    image_sizes = []
    
    for i in range(min(10, len(dataset))):
        sample = dataset[i]
        img = sample['image']
        
        if isinstance(img, Image.Image):
            width, height = img.size
            mode = img.mode
            image_sizes.append((width, height))
            
            if i < 5:  # 只打印前5个
                print(f"   - 样本 {i}: {width}x{height}, mode={mode}, label={sample['label']}")
    
    if image_sizes:
        widths = [w for w, h in image_sizes]
        heights = [h for w, h in image_sizes]
        
        print(f"\n📐 图像尺寸范围:")
        print(f"   - 宽度: {min(widths)} ~ {max(widths)} (平均: {np.mean(widths):.0f})")
        print(f"   - 高度: {min(heights)} ~ {max(heights)} (平均: {np.mean(heights):.0f})")
    
    # 保存一些样本
    output_dir = project_root / "examples" / "medical_diagnosis" / "data" / "samples"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n💾 保存样本图像到: {output_dir}")
    
    # 每个标签保存一个样本
    saved_labels = set()
    saved_count = 0
    
    for i, sample in enumerate(dataset):
        label = sample['label']
        
        if label not in saved_labels:
            img = sample['image']
            if isinstance(img, Image.Image):
                output_path = output_dir / f"sample_label{label}_{i}.jpg"
                img.save(output_path)
                print(f"   ✓ 保存 label={label} 样本: {output_path.name}")
                saved_labels.add(label)
                saved_count += 1
                
                if saved_count >= 5:  # 最多保存5个样本
                    break
    
    # 创建简单的统计报告
    report_path = output_dir / "dataset_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("腰椎MRI数据集统计报告\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"数据集路径: {dataset_path}\n")
        f.write(f"样本总数: {len(dataset)}\n")
        f.write(f"字段: {', '.join(dataset.column_names)}\n\n")
        
        f.write("标签分布:\n")
        for label, count in sorted(label_counts.items()):
            percentage = count / len(dataset) * 100
            f.write(f"  Label {label}: {count} ({percentage:.1f}%)\n")
        
        if image_sizes:
            f.write(f"\n图像尺寸范围:\n")
            f.write(f"  宽度: {min(widths)} ~ {max(widths)} (平均: {np.mean(widths):.0f})\n")
            f.write(f"  高度: {min(heights)} ~ {max(heights)} (平均: {np.mean(heights):.0f})\n")
    
    print(f"\n📊 统计报告已保存: {report_path}")
    
    print("\n" + "=" * 80)
    print("✅ 数据集探索完成!")
    print("=" * 80)


if __name__ == "__main__":
    explore_dataset()

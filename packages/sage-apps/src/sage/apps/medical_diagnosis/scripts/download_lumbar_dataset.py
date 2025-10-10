#!/usr/bin/env python3
"""下载腰椎MRI数据集"""

import os
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import snapshot_download


def download_lumbar_spine_dataset():
    """下载 UniDataPro/lumbar-spine-mri 数据集"""

    dataset_name = "UniDataPro/lumbar-spine-mri"
    output_dir = Path("data/medical/lumbar-spine-mri")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📥 开始下载数据集: {dataset_name}")
    print(f"📂 保存路径: {output_dir.absolute()}")

    try:
        # 方式1: 使用 datasets 库加载
        print("\n🔄 方式1: 使用 datasets 库加载...")
        dataset = load_dataset(dataset_name, split="train")

        print(f"✅ 数据集加载成功!")
        print(f"📊 样本数量: {len(dataset)}")
        print(f"📋 字段: {dataset.column_names}")

        # 保存数据集信息
        info_file = output_dir / "dataset_info.txt"
        with open(info_file, "w", encoding="utf-8") as f:
            f.write(f"Dataset: {dataset_name}\n")
            f.write(f"Samples: {len(dataset)}\n")
            f.write(f"Columns: {dataset.column_names}\n")
            f.write(f"\nFirst sample:\n")
            if len(dataset) > 0:
                for key, value in dataset[0].items():
                    f.write(f"  {key}: {type(value).__name__}\n")

        print(f"\n💾 数据集信息已保存到: {info_file}")

        # 保存数据集到本地
        cache_dir = output_dir / "cache"
        dataset.save_to_disk(str(cache_dir))
        print(f"💾 数据集已缓存到: {cache_dir}")

        return dataset

    except Exception as e:
        print(f"❌ 下载失败: {e}")
        print("\n🔄 尝试方式2: 直接下载仓库...")

        try:
            snapshot_download(
                repo_id=dataset_name,
                repo_type="dataset",
                local_dir=str(output_dir / "raw"),
                local_dir_use_symlinks=False,
            )
            print(f"✅ 数据集仓库下载成功: {output_dir / 'raw'}")
        except Exception as e2:
            print(f"❌ 方式2也失败: {e2}")
            raise


if __name__ == "__main__":
    download_lumbar_spine_dataset()

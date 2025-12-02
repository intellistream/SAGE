"""
数据集下载配置

存储所有数据集的下载链接和参数
"""

# Google Drive 文件夹 URL 配置
DATASET_URLS = {
    "sift-small": "https://drive.google.com/drive/folders/1XbvrSjlP-oUZ5cixVpfSTn0zE-Cim0NK?usp=sharing",
    "sift": "https://drive.google.com/drive/folders/1PngXRH9jnN86T8RNiU-QyGqOillfQE_p?usp=sharing",
    "openimages": "https://drive.google.com/drive/folders/1ZkWOrja-0A6C9yh3ysFoCP6w5u7oWjQx?usp=sharing",
    "sun": "https://drive.google.com/drive/folders/1gNK1n-do-7d5N-Z1tuAoXe5Xq3I8fZIH?usp=sharing",
    "coco": "https://drive.google.com/drive/folders/1Hp6SI8YOFPdWbmC1a4_-1dZWxZH3CHMS?usp=sharing",
    "glove": "https://drive.google.com/drive/folders/1m06VVmXmklHr7QZzdz6w8EtYmuRGIl9s?usp=sharing",
    "msong": "https://drive.google.com/drive/folders/1TnLNJNVqyFrEzKGfQVdvUC8Al-tmjVg0?usp=sharing",
}


def download_dataset(dataset_name: str, basedir: str) -> bool:
    """
    下载数据集

    Args:
        dataset_name: 数据集名称
        basedir: 目标目录

    Returns:
        是否下载成功
    """
    if dataset_name not in DATASET_URLS:
        print(f"✗ No download URL configured for '{dataset_name}'")
        print(f"  Please download manually and place in: {basedir}")
        return False

    try:
        import gdown

        print(f"Downloading {dataset_name} to {basedir}...")
        folder_url = DATASET_URLS[dataset_name]
        gdown.download_folder(folder_url, output=basedir, quiet=False)
        print("✓ Download completed!")
        return True
    except ImportError:
        print("✗ gdown not installed. Install it with: pip install gdown")
        return False
    except Exception as e:
        print(f"✗ Download failed: {e}")
        print(f"  Manual download URL: {DATASET_URLS[dataset_name]}")
        return False

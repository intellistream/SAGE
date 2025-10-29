# @test:skip           - 跳过测试

import os

import requests
from tqdm import tqdm


def download_from_huggingface(
    repo_id,
    filename,
    save_dir=None,
    use_mirror=True,
    mirror_url="https://hf-mirror.com",
    repo_type="dataset",
):
    """
    从 Hugging Face 下载文件，支持使用镜像站点

    Args:
        repo_id: Hugging Face 仓库 ID，格式为 "username/repo-name"
        filename: 要下载的文件名
        save_dir: 保存目录，默认为当前脚本所在目录
        use_mirror: 是否使用镜像站点
        mirror_url: 镜像站点 URL，默认为 hf-mirror.com
        repo_type: 仓库类型，可选 "model" 或 "dataset"，默认为 "dataset"
    """
    if save_dir is None:
        save_dir = os.path.dirname(__file__)

    # 构建下载 URL
    base_url = mirror_url if use_mirror else "https://huggingface.co"

    # 根据仓库类型构建不同的 URL
    if repo_type == "dataset":
        download_url = f"{base_url}/datasets/{repo_id}/resolve/main/{filename}"
    else:
        download_url = f"{base_url}/{repo_id}/resolve/main/{filename}"

    print(f"正在从 {'镜像站点' if use_mirror else 'Hugging Face'} 下载...")
    print(f"URL: {download_url}")

    try:
        # 发送请求
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()

        # 获取文件总大小
        total = int(response.headers.get("content-length", 0))

        # 保存文件路径
        file_path = os.path.join(save_dir, filename)

        # 下载并显示进度条
        with (
            open(file_path, "wb") as f,
            tqdm(
                desc=filename,
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
            ) as bar,
        ):
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))

        print(f"\n✓ 下载完成: {file_path}")
        return file_path

    except requests.exceptions.RequestException as e:
        print(f"\n✗ 下载失败: {e}")
        if use_mirror:
            print("\n提示: 镜像站点下载失败，你可以尝试:")
            print("  1. 检查网络连接")
            print("  2. 使用其他镜像站点（修改 mirror_url 参数）")
            print("  3. 设置 use_mirror=False 直接从 Hugging Face 下载")
        raise


if __name__ == "__main__":
    # 从 Hugging Face 下载数据集（支持镜像）
    print("=" * 60)
    print("Locomo 数据集下载工具")
    print("=" * 60)
    print("\n使用 Hugging Face 镜像下载数据集...")

    try:
        repo_id = "KimmoZZZ/locomo"
        filename = "locomo10.json"

        download_from_huggingface(
            repo_id=repo_id,
            filename=filename,
            use_mirror=True,  # 使用镜像
            mirror_url="https://hf-mirror.com",  # 默认镜像站点
            repo_type="dataset",  # 数据集类型
        )
    except Exception as e:
        print(f"\n错误: {e}")
        print("\n如果下载失败，请按以下步骤操作:")
        print("1. 检查网络连接")
        print("2. 尝试使用其他镜像站点")
        print("3. 确认数据集仓库 ID 是否正确")

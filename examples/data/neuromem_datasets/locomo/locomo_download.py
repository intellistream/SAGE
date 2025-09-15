# @test:skip           - 跳过测试

import re

import requests
from tqdm import tqdm


def download_gdrive_file(url):
    # 1. 提取 file id
    file_id = re.search(r"/d/([a-zA-Z0-9_-]+)", url).group(1)
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    # 2. 获取响应
    response = requests.get(download_url, stream=True)
    # 3. 自动获取文件名
    cd = response.headers.get("content-disposition")
    if cd:
        fname = re.search(r'filename="(.+)"', cd).group(1)
    else:
        fname = f"{file_id}.download"
    # 4. 获取文件总大小
    total = int(response.headers.get("content-length", 0))

    # 5. 保存文件并显示进度条
    with open(fname, "wb") as f, tqdm(
        desc=fname,
        total=total,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for chunk in response.iter_content(1024):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))
    print(f"\n下载完成: {fname}")


if __name__ == "__main__":
    url = "https://drive.google.com/file/d/1e5URAGLjui-K6fKboio3ZVapxo9znu0s/view?usp=sharing"
    download_gdrive_file(url)

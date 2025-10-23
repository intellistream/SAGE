import os
from pathlib import Path

import requests

# 输出路径
TARGET = Path("docs_src/about.md")

# 仓库信息
REPO = "intellistream/SAGE"
BRANCH = "main"
FILE_PATH = "README.md"

# 支持两种环境变量名
token = os.environ.get("SAGE_REPO_TOKEN") or os.environ.get("GITHUB_TOKEN")

if not token:
    print("❌ 未检测到 GitHub Token。请设置 SAGE_REPO_TOKEN 或 GITHUB_TOKEN")
    exit(1)

# GitHub API 请求 URL
url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}?ref={BRANCH}"

headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3.raw"}

print(f"📡 正在从 {url} 拉取 README.md ...")

resp = requests.get(url, headers=headers)

if resp.status_code == 200:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(resp.text, encoding="utf-8")
    print(f"✅ 同步成功：内容写入 {TARGET}")
else:
    print(f"❌ 拉取失败：HTTP {resp.status_code}")
    print(resp.text)

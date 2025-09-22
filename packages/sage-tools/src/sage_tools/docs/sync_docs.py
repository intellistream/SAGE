#!/usr/bin/env python3
"""
SAGE 文档同步脚本
用于将内部文档同步到公开文档仓库
"""

import os
import subprocess
import sys
from datetime import datetime

def run_command(cmd, cwd=None, check=True, capture_output=False):
    """运行命令并检查返回值"""
    result = subprocess.run(cmd, cwd=cwd, check=check, capture_output=capture_output)
    return result

# 脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
# 由于现在在 packages/sage-tools/src/sage_tools/docs/，根目录是 ../../../..
repo_root = os.path.join(script_dir, '..', '..', '..', '..', '..')

# 路径定义
SAGE_KERNEL_DOCS = os.path.join(repo_root, 'packages/sage-kernel/docs')
SAGE_MIDDLEWARE_DOCS = os.path.join(repo_root, 'packages/sage-middleware/docs')
SAGE_TOOLS_DOCS = os.path.join(repo_root, 'packages/sage-tools/docs')
PUBLIC_DOCS = os.path.join(repo_root, 'docs-public/docs_src')

print("🔄 开始同步 SAGE 文档...")

# 检查目录是否存在
if not os.path.exists(SAGE_KERNEL_DOCS):
    print(f"❌ 错误: sage-kernel 文档目录不存在: {SAGE_KERNEL_DOCS}")
    sys.exit(1)

if not os.path.exists(PUBLIC_DOCS):
    print(f"❌ 错误: 公开文档目录不存在: {PUBLIC_DOCS}")
    sys.exit(1)

# 同步 Kernel 文档
print("📘 同步 SAGE Kernel 文档...")
run_command([
    'rsync', '-av', '--delete',
    '--exclude=.git*',
    '--exclude=__pycache__',
    '--exclude=*.pyc',
    f'{SAGE_KERNEL_DOCS}/', f'{PUBLIC_DOCS}/kernel/'
])

# 同步 Middleware 文档 (如果存在)
if os.path.exists(SAGE_MIDDLEWARE_DOCS):
    print("🔧 同步 SAGE Middleware 文档...")
    run_command([
        'rsync', '-av', '--delete',
        '--exclude=.git*',
        '--exclude=__pycache__',
        '--exclude=*.pyc',
        f'{SAGE_MIDDLEWARE_DOCS}/', f'{PUBLIC_DOCS}/middleware/'
    ])
else:
    print("⚠️  Middleware 文档目录不存在，跳过同步")

# 同步 Tools 文档 (如果存在)
if os.path.exists(SAGE_TOOLS_DOCS):
    print("🛠️  同步 SAGE Tools 文档...")
    run_command([
        'rsync', '-av', '--delete',
        '--exclude=.git*',
        '--exclude=__pycache__',
        '--exclude=*.pyc',
        f'{SAGE_TOOLS_DOCS}/', f'{PUBLIC_DOCS}/tools/'
    ])
else:
    print("⚠️  Tools 文档目录不存在，跳过同步")

# 进入公开文档目录
public_docs_dir = os.path.join(repo_root, 'docs-public')
os.chdir(public_docs_dir)

# 检查是否有更改
diff_result = run_command(['git', 'diff', '--quiet'], capture_output=True, check=False)
staged_result = run_command(['git', 'diff', '--staged', '--quiet'], capture_output=True, check=False)

if diff_result.returncode == 0 and staged_result.returncode == 0:
    print("✅ 没有检测到文档更改")
    sys.exit(0)

print("📝 检测到文档更改，准备提交...")

# 显示更改
run_command(['git', 'status', '--short'])

# 询问是否提交
response = input("🤔 是否要提交这些更改到公开文档仓库? (y/N): ").strip()
if response.lower() in ['y', 'yes']:
    # 添加所有更改
    run_command(['git', 'add', '-A'])
    
    # 生成提交信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_msg = f"""docs: 同步内部文档更新 ({timestamp})

- 自动同步来自主仓库的文档更改
- 更新时间: {timestamp}
- 同步脚本: packages/sage-tools/src/sage_tools/docs/sync_docs.py"""
    
    # 提交更改
    with open('.git/COMMIT_EDITMSG', 'w') as f:
        f.write(commit_msg)
    run_command(['git', 'commit'])
    
    print("✅ 文档更改已提交到本地仓库")
    
    # 询问是否推送
    response = input("🚀 是否要推送到远程仓库? (y/N): ").strip()
    if response.lower() in ['y', 'yes']:
        run_command(['git', 'push', 'origin', 'main'])
        print("🎉 文档已成功推送到远程仓库！")
        print("📖 查看更新后的文档: https://intellistream.github.io/SAGE-Pub/")
    else:
        print("📋 文档已提交到本地，使用 'git push origin main' 手动推送")
else:
    print("❌ 取消提交，文档更改保留在工作区")

print("🏁 文档同步完成！")
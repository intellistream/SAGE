#!/bin/bash
set -e

# SAGE 子模块自动同步脚本
# 减少子模块冲突，规范更新流程

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "🔄 SAGE 子模块同步管理器"
echo "================================"

# 检查当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" != "main-dev" && "$CURRENT_BRANCH" != "main" ]]; then
    echo "⚠️  警告: 当前不在主分支 ($CURRENT_BRANCH)"
    echo "   子模块更新建议在主分支进行"
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 函数：检查子模块状态
check_submodule_status() {
    local submodule_path="$1"
    local submodule_name="$(basename "$submodule_path")"
    
    echo "📋 检查 $submodule_name 状态..."
    
    cd "$submodule_path"
    
    # 检查是否有未提交的更改
    if ! git diff --quiet || ! git diff --quiet --cached; then
        echo "❌ $submodule_name 有未提交的更改"
        git status --short
        cd - > /dev/null
        return 1
    fi
    
    # 获取当前commit和远程最新commit  
    local current_commit=$(git rev-parse HEAD)
    local remote_commit=$(git rev-parse origin/stable 2>/dev/null || git rev-parse origin/main)
    local branch_name=$(git rev-parse --abbrev-ref HEAD)
    
    echo "   当前分支: $branch_name"
    echo "   当前: $current_commit"
    echo "   远程: $remote_commit"
    
    if [[ "$current_commit" != "$remote_commit" ]]; then
        echo "⚠️  $submodule_name 与远程不同步"
        cd - > /dev/null
        return 2
    fi
    
    cd - > /dev/null
    echo "✅ $submodule_name 状态正常"
    return 0
}

# 函数：安全更新子模块
safe_update_submodule() {
    local submodule_path="$1"
    local submodule_name="$(basename "$submodule_path")"
    
    echo "🔄 更新 $submodule_name..."
    
    cd "$submodule_path"
    
    # 拉取最新更改
    git fetch origin
    
    # 确定要使用的分支（优先stable，fallback到main）
    local target_branch="stable"
    if ! git rev-parse --verify origin/stable >/dev/null 2>&1; then
        target_branch="main"
        echo "⚠️  $submodule_name 没有stable分支，使用main分支"
    fi
    
    # 检查是否有新的commits
    local current_commit=$(git rev-parse HEAD)
    local latest_commit=$(git rev-parse "origin/$target_branch")
    
    if [[ "$current_commit" == "$latest_commit" ]]; then
        echo "✅ $submodule_name 已是最新版本"
        cd - > /dev/null
        return 0
    fi
    
    echo "📦 发现新提交:"
    git log --oneline "$current_commit..$latest_commit"
    
    # 询问是否更新
    read -p "是否更新 $submodule_name 到 $target_branch 分支? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ "$target_branch" == "stable" ]]; then
            git checkout stable 2>/dev/null || git checkout -b stable origin/stable
        fi
        git merge "origin/$target_branch" --ff-only
        echo "✅ $submodule_name 更新完成"
        cd - > /dev/null
        return 0
    else
        echo "⏭️  跳过 $submodule_name 更新"
        cd - > /dev/null
        return 1
    fi
}

# 主逻辑
case "${1:-status}" in
    "status")
        echo "🔍 检查所有子模块状态..."
        git submodule status
        echo ""
        
        for submodule in packages/sage-middleware/src/sage/middleware/components/sage_*; do
            if [[ -d "$submodule/.git" ]]; then
                check_submodule_status "$submodule"
                echo ""
            fi
        done
        ;;
        
    "update")
        echo "🔄 安全更新子模块..."
        
        # 检查是否有未提交的主仓库更改
        if ! git diff --quiet || ! git diff --quiet --cached; then
            echo "❌ 主仓库有未提交的更改，请先提交"
            git status --short
            exit 1
        fi
        
        # 更新每个子模块
        updated_modules=()
        for submodule in packages/sage-middleware/src/sage/middleware/components/sage_*; do
            if [[ -d "$submodule/.git" ]]; then
                if safe_update_submodule "$submodule"; then
                    updated_modules+=("$(basename "$submodule")")
                fi
            fi
        done
        
        # 如果有更新，提交到主仓库
        if [[ ${#updated_modules[@]} -gt 0 ]]; then
            echo ""
            echo "📝 提交子模块更新到主仓库..."
            git add -A
            
            # 生成提交信息
            commit_msg="update: 子模块定期同步更新"
            if [[ ${#updated_modules[@]} -eq 1 ]]; then
                commit_msg="update: 同步 ${updated_modules[0]} 子模块"
            else
                commit_msg="update: 同步子模块 ($(IFS=', '; echo "${updated_modules[*]}"))"
            fi
            
            git commit -m "$commit_msg

自动同步的子模块更新，减少PR冲突
更新的组件: $(IFS=', '; echo "${updated_modules[*]}")

通过 submodule_sync.sh 脚本管理"
            
            echo "✅ 子模块更新已提交"
        else
            echo "ℹ️  没有子模块需要更新"
        fi
        ;;
        
    "lock")
        echo "🔒 锁定当前子模块版本..."
        # 生成版本锁定文件
        python3 -c "
import json
import subprocess
import os
from datetime import datetime

config = {
    'description': 'SAGE子模块版本锁定配置',
    'submodules': {},
    'lock_time': datetime.now().isoformat(),
    'locked_by': subprocess.getoutput('git config user.name')
}

submodules = [
    'packages/sage-middleware/src/sage/middleware/components/sage_db',
    'packages/sage-middleware/src/sage/middleware/components/sage_flow'
]

for submodule_path in submodules:
    if os.path.exists(submodule_path + '/.git'):
        os.chdir(submodule_path)
        name = os.path.basename(submodule_path)
        commit = subprocess.getoutput('git rev-parse HEAD')
        remote_url = subprocess.getoutput('git remote get-url origin')
        
        config['submodules'][name] = {
            'repository': remote_url,
            'commit': commit,
            'path': submodule_path
        }
        os.chdir('../../../../../..')

with open('submodule-lock.json', 'w') as f:
    json.dump(config, f, indent=2)
    
print('✅ 版本锁定文件已生成: submodule-lock.json')
"
        ;;
        
    "help")
        echo "用法: $0 [命令]"
        echo ""
        echo "命令:"
        echo "  status   显示所有子模块状态 (默认)"
        echo "  update   安全更新子模块"
        echo "  lock     锁定当前子模块版本"
        echo "  help     显示此帮助信息"
        echo ""
        echo "这个脚本帮助减少子模块冲突问题："
        echo "- 检查状态避免意外更新"
        echo "- 交互式确认更新"
        echo "- 生成规范的提交信息"
        echo "- 支持版本锁定"
        ;;
        
    *)
        echo "❌ 未知命令: $1"
        echo "运行 '$0 help' 查看可用命令"
        exit 1
        ;;
esac
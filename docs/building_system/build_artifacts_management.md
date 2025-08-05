# SAGE 构建产物统一管理指南

## 概述

SAGE开发工具包现在提供了统一管理pip install产生的中间产物的功能，包括：

- `*.egg-info` 目录
- `dist/` 目录  
- `__pycache__/` 目录
- `build/` 目录
- 覆盖率文件（`.coverage`, `coverage.xml`, `htmlcov/`）
- 测试缓存（`.pytest_cache/`）
- 临时文件和日志

## 核心功能

### 1. 扫描构建产物

```bash
# 扫描所有构建产物
sage-dev clean --dry-run

# 详细扫描结果
sage-dev clean --dry-run --verbose
```

### 2. 选择性清理

```bash
# 清理特定类型的产物
sage-dev clean --categories pycache,temp

# 清理所有构建产物
sage-dev clean --categories all

# 只清理超过7天的文件
sage-dev clean --categories all --older-than-days 7
```

### 3. 安全预览

```bash
# 预览将要删除的内容（不实际删除）
sage-dev clean --dry-run --categories all

# 强制清理（不询问确认）
sage-dev clean --categories all --force
```

### 4. 生成自动化脚本

```bash
# 生成shell清理脚本
sage-dev clean --create-script

# 脚本位置：scripts/cleanup_build_artifacts.sh
bash scripts/cleanup_build_artifacts.sh
```

### 5. 更新Git忽略规则

```bash
# 自动更新.gitignore以忽略构建产物
sage-dev clean --update-gitignore
```

## 使用场景

### 日常开发
```bash
# 清理Python缓存和临时文件
sage-dev clean --categories pycache,temp
```

### 每周维护
```bash
# 清理一周前的构建产物
sage-dev clean --categories all --older-than-days 7 --dry-run
sage-dev clean --categories all --older-than-days 7
```

### 发布前清理
```bash
# 完全清理所有构建产物
sage-dev clean --categories all --force
```

### CI/CD集成
```bash
# 在CI中清理构建产物
sage-dev clean --categories all --force --verbose
```

## 可清理的产物类别

| 类别 | 描述 | 包含的模式 |
|------|------|-----------|
| `egg_info` | pip安装信息 | `*.egg-info`, `*egg-info` |
| `dist` | 分发包目录 | `dist/` |
| `build` | 构建目录 | `build/` |
| `pycache` | Python缓存 | `__pycache__/` |
| `coverage` | 覆盖率文件 | `.coverage`, `coverage.xml`, `htmlcov/` |
| `pytest` | 测试缓存 | `.pytest_cache/` |
| `mypy` | 类型检查缓存 | `.mypy_cache/` |
| `temp` | 临时文件 | `*.tmp`, `*.temp`, `.tmp/` |
| `logs` | 日志文件 | `*.log`, `logs/` |

## 保护机制

系统会自动保护以下目录，不会被意外清理：
- `.git/` - Git仓库
- `.venv/`, `venv/`, `env/` - 虚拟环境
- `.idea/` - IDE配置
- `.vscode/` - VS Code配置
- `node_modules/` - Node.js依赖
- `.sage/` - SAGE配置目录

## 自动化建议

### 1. 使用 SAGE 工具链命令
```bash
# 日常开发清理
sage-dev clean --categories pycache,temp

# 深度清理
sage-dev clean --categories all --force

# 发布前清理
sage-dev clean --categories all --force
sage-dev clean --update-gitignore
```

### 2. Git钩子集成
创建 `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# 提交前清理临时文件
sage-dev clean --categories temp --force
```

### 3. 定期维护脚本
创建 `scripts/weekly_maintenance.sh`:
```bash
#!/bin/bash
# 每周维护脚本
echo "🧹 Weekly maintenance cleanup..."
sage-dev clean --categories all --older-than-days 7 --force
echo "✅ Cleanup completed!"
```

### 4. VS Code 任务集成
在 `.vscode/tasks.json` 中添加：
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "SAGE: Clean Dev Artifacts",
            "type": "shell",
            "command": "sage-dev",
            "args": ["clean", "--categories", "pycache,temp"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "SAGE: Deep Clean",
            "type": "shell", 
            "command": "sage-dev",
            "args": ["clean", "--categories", "all", "--force"],
            "group": "build"
        }
    ]
}
```

## 高级用法

### 1. 批量项目清理
```bash
# 对于多个SAGE项目
for project in /path/to/sage-project-*; do
    cd "$project"
    sage-dev clean --categories all --older-than-days 30 --force
done
```

### 2. 监控清理效果
```bash
# 清理前后的空间对比
du -sh /home/shuhao/SAGE before_cleanup.txt
sage-dev clean --categories all --force
du -sh /home/shuhao/SAGE after_cleanup.txt
```

### 3. 自定义清理策略
```bash
# 开发阶段：只清理缓存
sage-dev clean --categories pycache,temp --older-than-days 1

# 测试阶段：清理测试产物
sage-dev clean --categories pycache,pytest,coverage --older-than-days 3

# 发布阶段：完全清理
sage-dev clean --categories all --force
```

## 故障排除

### 权限问题
```bash
# 如果遇到权限问题，检查文件权限
ls -la packages/*/dist/
sudo chown -R $USER:$USER packages/
```

### 清理失败
```bash
# 使用详细模式查看错误
sage-dev clean --categories all --verbose --dry-run

# 逐个类别清理
sage-dev clean --categories pycache
sage-dev clean --categories dist
sage-dev clean --categories egg_info
```

### 恢复误删文件
如果意外删除重要文件：
```bash
# 从Git恢复
git checkout HEAD -- path/to/deleted/file

# 重新构建包
pip install -e packages/sage-kernel/
```

## 最佳实践

1. **始终先预览**: 使用 `--dry-run` 确认要删除的内容
2. **分类清理**: 根据需要选择特定类别，不要总是使用 `all`
3. **定期维护**: 建立定期清理的习惯
4. **保留重要产物**: 发布前备份重要的dist文件
5. **更新忽略规则**: 使用 `--update-gitignore` 保持.gitignore最新

## 示例工作流

### 开发者日常工作流
```bash
# 早晨开始工作 - 清理昨天的临时文件
sage-dev clean --categories pycache,temp

# 开发过程中...

# 测试后清理测试产物
sage-dev clean --categories pytest,coverage --older-than-days 1

# 结束工作前清理
sage-dev clean --categories temp --force
```

### 项目维护工作流
```bash
# 每周维护 - 先预览再执行
sage-dev clean --categories all --older-than-days 7 --dry-run
sage-dev clean --categories all --older-than-days 7

# 月度深度清理
sage-dev clean --categories all --force
sage-dev clean --update-gitignore

# 生成自动化清理脚本（可选）
sage-dev clean --create-script
```

### 团队协作建议
```bash
# 新成员入门时
sage-dev clean --update-gitignore  # 确保.gitignore是最新的

# 发布前的标准流程
sage-dev clean --categories all --dry-run  # 预览要清理的内容
sage-dev clean --categories all --force    # 执行清理
sage-dev test --mode all                   # 确保清理后测试通过

# CI/CD 集成
sage-dev clean --categories all --force --verbose
```

通过这个统一的管理系统，你可以有效地控制SAGE项目中的所有构建产物，保持项目目录的整洁，并避免不必要的磁盘空间占用。

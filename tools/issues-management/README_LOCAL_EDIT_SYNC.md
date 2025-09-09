# 新架构下的Issues本地修改和同步指南

## 概述

在新的"单一数据源 + 视图分离"架构下，所有的issues数据都存储在`data/`目录下的JSON文件中。这是唯一的真实数据源，其他目录（如`issues/`、`metadata/`、`summaries/`）都是从这个数据源自动生成的视图。

## 本地修改流程

### 1. 数据位置
- **数据源**: `data/issue_XXX.json` - 这是唯一可以手动修改的文件
- **视图**: `issues/`、`metadata/`、`summaries/` - 这些是自动生成的，不要手动修改

### 2. JSON数据结构
```json
{
  "metadata": {
    "number": 92,
    "title": "问题标题",
    "state": "open",
    "labels": ["bug", "enhancement"],
    "assignees": ["username"],
    "milestone": {
      "title": "v1.0",
      "number": 1
    },
    "projects": [
      {
        "number": 14,
        "title": "SAGE-Apps",
        "team": "sage-apps"
      }
    ],
    // ... 其他GitHub metadata
  },
  "content": {
    "body": "问题描述内容...",
    "comments": []
  },
  "tracking": {
    "downloaded_at": "2025-09-09T22:28:08.079640",
    "last_synced": "2025-09-09T22:28:08.079642",
    "update_history": []
  }
}
```

### 3. 可修改的字段
在本地修改时，你可以安全地修改以下字段：
- `metadata.title` - 问题标题
- `metadata.labels` - 标签列表
- `metadata.assignees` - 分配给的用户列表
- `metadata.milestone` - 里程碑信息
- `content.body` - 问题描述内容

⚠️ **不要修改**: `metadata.number`、`metadata.state`、`tracking` 等字段

## 同步到云端

### 1. 预览更改
```bash
cd tools/issues-management
python3 _scripts/sync_issues.py --preview
```

### 2. 应用所有更改
```bash
python3 _scripts/sync_issues.py --apply-all --confirm
```

### 3. 仅应用基本属性更改
```bash
python3 _scripts/sync_issues.py --apply-basic --confirm
```

### 4. 仅应用项目板更改
```bash
python3 _scripts/sync_issues.py --apply-projects --confirm
```

## 重新生成视图

同步脚本会在成功同步后自动重新生成视图。如果你只是本地修改了数据（没有同步到云端），可以手动重新生成视图：

```bash
cd tools/issues-management
python3 _scripts/issue_data_manager.py generate-views
```

## 完整工作流程示例

1. **修改本地数据**:
   ```bash
   # 编辑 data/issue_123.json
   vim output/issues-workspace/data/issue_123.json
   ```

2. **预览更改**:
   ```bash
   cd tools/issues-management
   python3 _scripts/sync_issues.py --preview
   ```

3. **同步到GitHub**:
   ```bash
   python3 _scripts/sync_issues.py --apply-all --confirm
   ```

4. **验证结果**:
   - 本地JSON数据已更新为GitHub的最新状态
   - 视图已重新生成
   - GitHub上的issue已更新

## 注意事项

1. **单一数据源**: 只修改`data/`目录下的JSON文件，不要修改其他视图文件
2. **备份**: 重要修改前建议备份相关的JSON文件
3. **格式**: 确保修改后的JSON格式正确
4. **权限**: 确保有足够的GitHub权限来修改issues
5. **冲突**: 如果GitHub上的issue在你修改后也被更新了，sync脚本会用GitHub的最新数据覆盖你的修改

## 故障排除

### 同步失败
- 检查GitHub token权限
- 检查网络连接
- 查看错误日志

### 视图不一致
```bash
# 强制重新生成所有视图
python3 _scripts/issue_data_manager.py generate-views --force
```

### 数据损坏
```bash
# 重新下载所有数据
./issues_manager.sh download
```

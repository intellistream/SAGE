# Issues Archive - GitHub Issues 归档

这个目录包含从GitHub下载的SAGE项目issues，用于离线查看和分析。

## 📁 目录结构

```
issues_workspace/
├── issues/               # 所有issues (Markdown格式，按状态前缀命名)
│   ├── open_123_bug_fix.md
│   ├── closed_456_feature.md
│   └── ...
├── by_label/             # 按标签分类 (引用文件)
│   ├── bug/
│   ├── enhancement/
│   └── ...
├── metadata/             # 简化的JSON元数据
└── issues_summary.md     # 统计报告
```

## 🔍 使用说明

### 查看Issues
```bash
# 查看所有issues
ls issues/

# 查看开放的issues
ls issues/open_*

# 查看已关闭的issues  
ls issues/closed_*

# 查看总结报告
cat issues_summary.md
```

### 按分类查看
```bash
# 查看bug相关的issues
ls by_label/bug/

# 查看功能请求
ls by_label/enhancement/

# 查看文档相关
ls by_label/documentation/
```

### 搜索Issues
```bash
# 在所有issues中搜索关键词
grep -r "关键词" issues/

# 搜索开放的issues
grep -r "关键词" issues/open_*
```

## 🔄 更新数据

要更新issues数据，请使用：
```bash
# 重新下载最新的issues
../scripts/download_issues.py --repo intellistream/SAGE --output .
```

## 📝 创建新Issue

项目已配置了完整的GitHub Issue模板，请直接在GitHub上创建：
- 访问: https://github.com/intellistream/SAGE/issues/new/choose
- 选择合适的模板类型

## 💡 提示

这个归档主要用于：
1. **离线查看** - 无网络时查看issues
2. **数据分析** - 分析issue模式和趋势  
3. **搜索查找** - 快速搜索相关问题
4. **备份存档** - 保留历史记录

文件命名规则：`{状态}_{编号}_{标题}.md`
- 开放的issue: `open_123_bug_title.md`
- 已关闭的issue: `closed_456_feature_title.md`

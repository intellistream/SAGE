# SAGE Issues 管理工具 - 简化版

这是重新设计的SAGE Issues管理工具，专注于核心的三大功能，界面更加清爽简洁。

## 🎯 核心功能

### 1. 📥 下载远端Issues
- 下载所有Issues
- 下载开放的Issues  
- 下载已关闭的Issues

### 2. 🤖 AI智能整理Issues
- AI分析重复Issues
- AI优化标签分类
- AI评估优先级
- AI综合分析报告

### 3. 📤 上传Issues到远端
- 同步所有修改
- 同步标签更新
- 同步状态更新
- 预览待同步更改

## 🚀 快速开始

### 启动主界面
```bash
./issues_manager.sh
```

### 直接使用脚本
```bash
# 下载Issues
python3 _scripts/download_issues.py --state=all

# AI分析
python3 _scripts/ai_analyzer.py --mode=comprehensive

# 同步更改
python3 _scripts/sync_issues.py --preview
```

## 📁 目录结构

```
issues-management/
├── issues_manager.sh           # 主入口脚本
├── _scripts/                   # 核心功能脚本
│   ├── download_issues.py      # 下载Issues
│   ├── ai_analyzer.py          # AI分析
│   ├── sync_issues.py          # 同步Issues
│   └── helpers/                # 辅助工具和GitHub操作脚本
├── issues_workspace/           # Issues数据存储
├── analysis_output/            # AI分析报告
└── sync_logs/                  # 同步日志
```

## ✨ 主要改进

1. **简化菜单结构**: 只保留三个核心功能在一级菜单
2. **清晰的功能分层**: 每个功能有合理的二级菜单
3. **隐藏实现细节**: 用户不需要看到的脚本放在`_scripts`目录
4. **辅助工具分离**: 原有脚本保存在`helpers`目录，作为辅助工具
5. **模块化设计**: 每个核心功能独立为一个Python脚本

## 🔧 配置

确保以下环境变量已设置:
```bash
export GITHUB_TOKEN="your_github_token"
export OPENAI_API_KEY="your_openai_key"  # 可选
export ANTHROPIC_API_KEY="your_claude_key"  # 可选
```

## 📊 工作流程

1. **下载**: 从GitHub获取最新的Issues数据
2. **分析**: 使用AI工具分析和整理Issues
3. **上传**: 将优化后的结果同步回GitHub

每一步都有详细的进度提示和确认机制，确保操作的安全性和可控性。
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

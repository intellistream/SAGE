# SAGE Issues 管理工具

一个功能完整的GitHub Issues管理工具，提供下载、分析、管理和同步功能，支持AI智能分析和团队协作管理。

## 🎯 核心功能

### 1. 📥 下载远端Issues
- 下载所有Issues（支持状态过滤）
- 下载开放的Issues  
- 下载已关闭的Issues
- 自动按标签分类存储
- 支持增量更新

### 2. 📋 Issues管理
- 📊 查看Issues统计信息
- 🏷️ 标签管理
- 👥 团队分析报告
- ✨ 创建新Issue
- 📋 项目管理功能
- 🔍 搜索和过滤

### 3. 🤖 AI智能整理Issues
- AI分析重复Issues（深度语义理解）
- AI优化标签分类（智能分类推荐）
- AI评估优先级（多因素评估）
- AI综合分析报告（全面管理建议）
- 支持多种AI引擎（OpenAI、Claude、交互式）

### 4. 📤 上传Issues到远端
- 同步所有修改到GitHub
- 同步标签更新
- 同步状态更新
- 预览待同步更改
- 详细同步日志

## 🚀 快速开始

### 启动主界面
```bash
./issues_manager.sh
```

### 命令行直接使用
```bash
# 下载Issues
python3 _scripts/download_issues.py --state=all

# Issues管理
python3 _scripts/issues_manager.py --statistics

# AI分析
python3 _scripts/ai_analyzer.py --mode=comprehensive

# 同步更改
python3 _scripts/sync_issues.py --preview
```

## 📁 项目结构

```
issues-management/
├── issues_manager.sh           # 主入口脚本（交互式界面）
├── _scripts/                   # 核心功能脚本
│   ├── download_issues.py      # Issues下载功能
│   ├── issues_manager.py       # Issues管理功能
│   ├── ai_analyzer.py          # AI智能分析
│   ├── sync_issues.py          # 同步到GitHub
│   └── helpers/                # 辅助工具和GitHub操作
│       ├── _github_operations.py      # GitHub API操作
│       ├── team_issues_manager.py     # 团队Issues管理
│       ├── get_team_members.py        # 团队成员信息
│       ├── generate_team_analysis.py  # 团队分析报告
│       ├── 1_create_github_issue.py   # 创建GitHub Issue
│       ├── 2_download_issues.py       # Issues下载实现
│       ├── 5_sync_issues_to_github.py # Issues同步实现
│       └── 6_move_issues_to_project.py # Issues项目移动
├── issues_workspace/           # Issues数据存储
├── output/                     # AI分析报告和统计结果
└── README.md                   # 本文档
```

## ✨ 主要特性

### 🧠 AI驱动的智能分析
- **深度语义理解**: 不依赖简单的文本匹配，使用AI理解Issues的真实含义
- **多模型支持**: 支持OpenAI GPT-4、Claude API、交互式Claude分析
- **智能分类**: 基于内容自动推荐合适的标签和优先级
- **重复检测**: 智能识别语义相似的重复Issues

### 🔧 完整的管理功能
- **统计分析**: 详细的Issues数据统计和可视化
- **团队管理**: 基于团队配置的分析和分配管理
- **项目集成**: 与GitHub Projects无缝集成
- **搜索过滤**: 强大的搜索和过滤功能

### 🔄 同步和集成
- **双向同步**: 支持从GitHub下载和向GitHub同步
- **增量更新**: 智能的增量下载和同步
- **预览模式**: 同步前可预览所有更改
- **详细日志**: 完整的操作日志记录

### 🎨 用户体验
- **交互式界面**: 清晰的菜单结构和操作提示
- **模块化设计**: 功能独立，易于维护和扩展
- **容错处理**: 完善的错误处理和用户提示

## 🔧 环境配置

### 必需配置
```bash
# GitHub访问令牌（必需）
export GITHUB_TOKEN="your_github_token"
```

### 可选配置（AI功能）
```bash
# OpenAI API密钥（用于GPT-4分析）
export OPENAI_API_KEY="your_openai_key"

# Anthropic API密钥（用于Claude分析）
export ANTHROPIC_API_KEY="your_claude_key"
```

### 获取GitHub Token
1. 访问 [GitHub Personal Access Tokens](https://github.com/settings/tokens)
2. 创建新token，需要以下权限：
   - `repo` (访问仓库)
   - `read:org` (读取组织信息)
   - `read:user` (读取用户信息)

### 本地Token存储
也可以将token存储在文件中：
```bash
echo "your_github_token" > /home/shuhao/SAGE/.github_token
```

## 📊 使用流程

### 标准工作流程
1. **📥 下载Issues**: 从GitHub获取最新的Issues数据
   ```bash
   ./issues_manager.sh -> 1. 下载远端Issues -> 1. 下载所有Issues
   ```

2. **📋 管理分析**: 查看统计信息，进行基础管理
   ```bash
   ./issues_manager.sh -> 2. Issues管理 -> 1. 查看Issues统计
   ```

3. **🤖 AI分析**: 使用AI进行智能分析和优化
   ```bash
   ./issues_manager.sh -> 3. AI智能整理Issues -> 4. AI综合分析报告
   ```

4. **📤 同步更新**: 将优化后的结果同步回GitHub
   ```bash
   ./issues_manager.sh -> 4. 上传Issues到远端 -> 4. 预览待同步更改
   ```

### 高级功能
- **团队分析**: 基于团队配置生成分析报告
- **标签优化**: AI推荐最优的标签分类
- **重复检测**: 智能识别重复或相似的Issues
- **优先级评估**: 多因素评估Issues优先级

## 🔍 搜索和过滤

### 本地搜索
```bash
# 搜索包含关键词的Issues
grep -r "关键词" issues_workspace/

# 搜索特定状态的Issues
find issues_workspace/ -name "open_*.md" | xargs grep "关键词"
find issues_workspace/ -name "closed_*.md" | xargs grep "关键词"

# 搜索特定标签的Issues
grep -r "label:bug" issues_workspace/
```

### 工具内搜索
使用工具的搜索功能：
```bash
./issues_manager.sh -> 2. Issues管理 -> 6. 搜索和过滤
```

## 📝 创建新Issue

### 通过工具创建
```bash
./issues_manager.sh -> 2. Issues管理 -> 4. 创建新Issue
```

### 直接在GitHub创建
访问: [https://github.com/intellistream/SAGE/issues/new/choose](https://github.com/intellistream/SAGE/issues/new/choose)
选择合适的Issue模板类型

## 📈 数据分析和报告

### 统计报告
- Issues总数和状态分布
- 标签使用情况统计
- 分配和完成情况
- 时间趋势分析

### AI分析报告
- 重复Issues检测报告
- 标签优化建议
- 优先级评估结果
- 团队工作负载分析

### 报告存储
所有报告保存在 `output/` 目录：
- `statistics_YYYYMMDD_HHMMSS.md` - 统计报告
- `ai_analysis_YYYYMMDD_HHMMSS.md` - AI分析报告
- `team_analysis_YYYYMMDD_HHMMSS.md` - 团队分析报告

## 🛠️ 开发和扩展

### 添加新功能
1. 在 `_scripts/` 目录添加新的Python脚本
2. 在 `issues_manager.sh` 中添加相应的菜单选项
3. 在 `_scripts/helpers/` 中添加辅助功能

### 自定义AI分析
编辑 `_scripts/ai_analyzer.py` 中的分析逻辑，支持：
- 自定义分析规则
- 新的AI模型集成
- 特定领域的分析逻辑

## 🔧 故障排除

### 常见问题
1. **GitHub API限制**: 确保设置了有效的GitHub Token
2. **AI功能不可用**: 检查是否设置了相应的API密钥
3. **权限错误**: 确保对SAGE仓库有足够的访问权限

### 调试模式
```bash
# 启用详细输出
python3 _scripts/download_issues.py --verbose
python3 _scripts/ai_analyzer.py --debug
```

## 💡 使用提示

### 最佳实践
1. **定期同步**: 建议每周下载一次最新的Issues
2. **AI分析**: 在重要决策前运行综合AI分析
3. **预览更改**: 同步前始终预览更改内容
4. **备份数据**: 重要操作前备份 `issues_workspace/` 目录

### 数据管理
- **离线查看**: 下载的Issues可在无网络时查看
- **历史记录**: 保留完整的Issues历史版本
- **数据分析**: 支持对Issues数据进行深度分析
- **搜索查找**: 快速搜索和定位相关问题

### 文件命名规则
- 开放的Issue: `open_{编号}_{标题}.md`
- 已关闭的Issue: `closed_{编号}_{标题}.md`
- 按标签分类存储在相应子目录中

## 📋 开发状态

### 已完成功能 ✅
- ✅ Issues下载和同步
- ✅ AI智能分析（多模型支持）
- ✅ 统计报告生成
- ✅ 团队分析功能
- ✅ 创建新Issue
- ✅ 预览和同步功能
- ✅ 交互式主界面

### 开发中功能 🚧
- 🚧 标签管理界面（建议使用AI分析功能）
- 🚧 高级搜索过滤（建议使用VS Code搜索）

### 计划功能 📋
- 📋 Issues模板管理
- 📋 自动化工作流
- 📋 更多AI分析模式
- 📋 数据可视化图表

## 🤝 贡献指南

欢迎贡献代码和建议！请：
1. Fork 本项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 📄 许可证

本项目遵循SAGE项目的许可证。详见项目根目录的LICENSE文件。

---

🎯 **快速开始**: 运行 `./issues_manager.sh` 开始使用！

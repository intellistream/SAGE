# SAGE Issues 管理工具集

本目录包含完整的GitHub Issues管理和分析解决方案。

## 🚀 快速开始

```bash
# 进入issues_workspace目录
cd issues_workspace

# 运行主管理工具
./scripts/issues_manager.sh
```

## 📁 文件结构

```
issues_workspace/
├── scripts/                          # 用户接口
│   ├── issues_manager.sh              # 🎯 主管理工具 (唯一入口)
│   ├── _scripts/                      # 实现脚本(隐藏)
│   │   ├── download_issues.py         # 📥 下载GitHub Issues
│   │   ├── improved_issue_analyzer.py # 🔍 重复Issues分析
│   │   ├── smart_issue_analyzer.py    # 🤖 智能Issues分析
│   │   ├── manage_github_issues.py    # ⚙️ GitHub Issues管理
│   │   └── correct_issues.py          # 🔧 错误修正工具
│   └── README.md                      # 📖 本文档
├── issues/                            # Issues存储目录
│   ├── open_*.md                      # 开放Issues
│   ├── closed_*.md                    # 关闭Issues
│   └── *_enhanced/                    # AI分析结果
└── analysis_reports/                  # 分析报告
```

## 🛠️ 核心功能

### 1. 📥 Issues下载
- 自动下载所有GitHub Issues
- 支持增量更新
- 本地Markdown格式存储

### 2. 🔍 重复检测
- 95%+准确率的重复检测
- 智能相似度分析
- 手动验证机制

### 3. 🤖 智能分析
支持三种分析模式：
- **OpenAI GPT-4**: 需要API密钥
- **Claude API**: 需要API密钥  
- **Claude助手交互**: 🔥推荐，免费且高质量

### 4. ⚙️ 批量管理
- 批量关闭/重开Issues
- 批量添加标签
- 批量分配责任人

### 5. 🔧 错误修正
- 撤销错误操作
- 重开错误关闭的Issues
- 操作历史追踪

## 💡 使用建议

### 首次使用流程
1. 运行 `./scripts/issues_manager.sh`
2. 选择 "1. 📥 下载GitHub Issues"
3. 选择 "2. 🔍 分析重复Issues"
4. 选择 "3. 🤖 智能Issues分析" (推荐Claude助手交互模式)

### 智能分析模式对比

| 模式 | 成本 | 质量 | 交互性 | 推荐度 |
|------|------|------|--------|--------|
| OpenAI GPT-4 | 💰 | ⭐⭐⭐⭐ | ❌ | ⭐⭐⭐ |
| Claude API | 💰 | ⭐⭐⭐⭐⭐ | ❌ | ⭐⭐⭐⭐ |
| Claude助手交互 | 🆓 | ⭐⭐⭐⭐⭐ | ✅ | ⭐⭐⭐⭐⭐ |

## 🔧 环境配置

### 必需环境
```bash
# Python环境
conda activate sage
pip install requests anthropic  # 如需API调用

# GitHub Token (必需)
export GITHUB_TOKEN="your_github_token"
```

### 可选API密钥
```bash
# OpenAI (可选)
export OPENAI_API_KEY="your_openai_key"

# Claude (可选)  
export ANTHROPIC_API_KEY="your_claude_key"
```

## 📊 统计信息

使用主管理工具可查看实时统计：
- 开放/关闭Issues数量
- 已分析Issues数量
- 最近更新情况

## 🎯 高级功能

### 直接脚本调用(高级用户)
```bash
# 批量关闭重复issues
python3 scripts/_scripts/manage_github_issues.py --close-duplicates

# 批量添加标签
python3 scripts/_scripts/manage_github_issues.py --add-labels enhancement

# 智能分析特定范围
python3 scripts/_scripts/smart_issue_analyzer.py --start 1 --count 10
```

### 自定义分析
Claude助手交互模式支持：
- 实时调整分析重点
- 针对性问题解答
- 个性化建议生成

## 🚨 注意事项

1. **GitHub Token权限**: 确保token有read/write权限
2. **API使用**: API调用会产生费用，建议使用免费的Claude助手交互模式
3. **数据备份**: 重要操作前建议备份issues目录
4. **网络环境**: 需要稳定的网络连接

## 🤝 贡献指南

欢迎提交改进建议和bug报告到SAGE项目的GitHub Issues。

## 📞 支持

如有问题，请：
1. 查看本README文档
2. 运行主工具的帮助功能
3. 在SAGE项目提交Issue

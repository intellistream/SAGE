# SAGE Issues管理工具集 - 实现脚本

本目录包含issues管理工具集的所有实现脚本，采用统一的AI驱动架构。

## 🎯 架构设计

### 核心原则
- **AI优先**: 完全摒弃rule-based硬编码，使用AI深度分析
- **统一管理**: 整合所有功能到统一的meta脚本中
- **简化接口**: 主菜单的每个选项对应一个脚本文件
- **清晰命名**: 使用数字前缀确保脚本顺序和功能映射

## 📁 脚本列表

### 1_download_issues.py
- **功能**: 从GitHub API下载issues数据
- **输入**: GitHub token, 仓库信息
- **输出**: issues/ 目录下的markdown文件
- **特点**: 支持增量更新，按标签分类

### 2_ai_unified_manager.py
- **功能**: 统一的AI智能issues管理系统
- **包含功能**:
  - 🔍 AI重复检测分析 (深度语义理解)
  - 🏷️ AI标签优化分析 (智能分类推荐)
  - 📊 AI优先级评估 (多因素评估)
  - 🔧 AI错误修正 (智能识别和修复)
  - 🧠 AI综合管理 (全面管理建议)
  - 📈 AI分析报告 (专业报告生成)
- **AI模式**: OpenAI GPT-4, Claude API, 交互式Claude
- **输出**: output/ 目录下的AI分析报告

### 3_github_operations.py
- **功能**: GitHub issues批量操作工具
- **操作类型**: 合并、关闭、标签更新、分配管理
- **输入**: GitHub token, 操作配置
- **输出**: 操作报告和GitHub API调用结果

### 4_show_statistics.py
- **功能**: issues数据统计和可视化
- **统计内容**: 
  - 基础数量统计
  - 标签分布分析
  - 分配情况统计
  - 时间趋势分析
  - 质量指标评估
- **输出**: 控制台显示 + 详细统计报告

## 🤖 AI驱动特性

### 与传统rule-based的区别

**传统方式 (已淘汰)**:
```python
# 硬编码的相似度阈值
if title_similarity > 0.9 and desc_similarity > 0.8:
    mark_as_duplicate()
```

**AI驱动方式 (当前)**:
```python
# 深度语义理解
ai_analysis = call_ai_with_context(issues_data, project_context)
decisions = parse_intelligent_recommendations(ai_analysis)
```

### AI分析能力
- **语义理解**: 理解issues的真实含义，不局限于字面匹配
- **上下文感知**: 结合SAGE项目特点进行分析
- **多因素评估**: 综合考虑影响范围、紧急程度、实施复杂度等
- **学习适应**: 基于项目特点和历史数据提供个性化建议

## 🔧 使用方式

### 从主菜单使用 (推荐)
```bash
cd /path/to/SAGE/issues_workspace
./manage_issues.sh
```

### 直接调用脚本
```bash
cd /path/to/SAGE/issues_workspace
python3 scripts/_scripts/1_download_issues.py
python3 scripts/_scripts/2_ai_unified_manager.py
python3 scripts/_scripts/3_github_operations.py
python3 scripts/_scripts/4_show_statistics.py
```

## 📊 输出目录

### issues/
- 下载的GitHub issues原始数据
- 按开放/关闭状态分类
- 按标签组织的子目录

### output/
- 所有AI分析报告统一输出目录
- 文件命名格式: `ai_{type}_{timestamp}.md`
- 自动gitignore，不提交到版本控制

## 🔑 环境变量

```bash
# 必需 (用于GitHub API)
export GITHUB_TOKEN="your_github_token"

# 可选 (用于AI分析)
export OPENAI_API_KEY="your_openai_key"
export ANTHROPIC_API_KEY="your_claude_key"
```

## 🚀 未来扩展

当前架构支持轻松扩展新功能：
1. 添加新的AI分析类型到统一管理器
2. 集成更多AI模型和API
3. 扩展GitHub操作类型
4. 增加更多统计维度

## 📋 维护说明

- 每个脚本都是独立的，可以单独运行和测试
- 统一的错误处理和日志记录
- 清晰的输入输出接口
- 完整的文档和注释

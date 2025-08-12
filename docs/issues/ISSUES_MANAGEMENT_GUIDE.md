# SAGE Issues 管理工具使用指南

## 🎯 概述

SAGE项目的Issues管理工具集，用于自动化处理GitHub Issues的下载、分析、整理和标签优化。

## 📁 工具结构

```
scripts/
├── download_issues.py       # GitHub Issues下载工具
├── manage_issues.sh         # 交互式Issues管理脚本  
├── analyze_issues.py        # Issues分析工具
└── manage_github_issues.py  # GitHub API Issues管理工具

issues_workspace/
├── issues/                  # 下载的issues文件存储
├── issues_analysis_report.md    # 分析报告
├── processing_report.md     # 处理报告
└── cleanup_issues.py        # 自动生成的清理脚本
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 设置GitHub Token
export GITHUB_TOKEN="your_github_token_here"

# 确保在SAGE项目根目录
cd /path/to/SAGE
```

### 2. 下载Issues

```bash
# 交互式管理界面
./scripts/manage_issues.sh

# 或直接下载
python3 scripts/download_issues.py
```

### 3. 分析Issues

```bash
# 分析开放issues，识别重复和建议标签
python3 scripts/analyze_issues.py
```

### 4. 管理Issues

```bash
# 完整的issues管理（标签优化 + 重复处理）
python3 scripts/manage_github_issues.py

# 分步骤执行
python3 scripts/manage_github_issues.py labels      # 只创建标签
python3 scripts/manage_github_issues.py duplicates  # 只处理重复
python3 scripts/manage_github_issues.py update-labels # 只更新标签
```

## 📊 处理结果统计

### 最近处理结果 (2025-08-10)

- **开放Issues**: 120个 → 105个（合并重复后）
- **重复Issues**: 发现13组，合并15个重复issues
- **标签系统**: 创建30个标准化标签
- **标签更新**: 21个issues获得正确分类

### 重复Issues合并详情

| 主Issue | 合并的重复Issues | 合并原因 |
|---------|------------------|----------|
| #357 | #359 | 相同的logging integration |
| #347 | #351 | 相同的batch execution |
| #348 | #349 | 相同的streaming/job execution |
| #356 | #358 | 相同的document parsing logic |
| #352 | #354, #360 | 相同的implementation tasks |
| #291 | #297, #293 | 相同的SAGE系统设计主题 |
| #288 | #296 | 相同的refinement tasks |
| #312 | #344 | 相同的accumulator支持 |
| #361 | #362 | 相同的serialization/deserialization |
| #188 | #189 | 相同的存储实现 |
| #314 | #346 | 相同的stateful function概念 |
| #311 | #343 | 相同的job listeners支持 |
| #315 | #365 | 相同的memory manager需求 |

## 🏷️ 标签体系

### 类型标签
- `bug`: Bug报告 🔴
- `feature`: 新功能 🔵  
- `enhancement`: 功能增强 🟡
- `documentation`: 文档相关 🔵
- `refactor`: 代码重构 🟣
- `task`: 一般任务 🟡
- `algorithm`: 算法相关 🟣
- `dataset`: 数据集相关 🟢

### 优先级标签
- `priority:high`: 高优先级 🔴
- `priority:medium`: 中优先级 🟡
- `priority:low`: 低优先级 🟢

### 组件标签  
- `component:core`: 核心组件
- `component:cli`: CLI组件
- `component:frontend`: 前端组件
- `component:docs`: 文档组件
- `component:testing`: 测试组件

### 功能标签
- `rag`: RAG相关
- `memory`: 内存相关
- `retrieval`: 检索相关
- `distributed`: 分布式系统
- `engine`: 引擎相关
- `job`: 作业相关
- `api`: API相关
- `config`: 配置相关

## 🔧 工具详细说明

### download_issues.py
**功能**: 从GitHub API下载所有issues并组织存储
**特性**: 
- 支持私有仓库（Token认证）
- 分页处理大量issues
- 文件名安全处理
- 按状态分类存储

### analyze_issues.py  
**功能**: 分析开放issues，识别重复内容和优化标签
**算法**: 
- 文本相似度计算（70%阈值）
- 关键词提取和分类
- 自动类型识别
- 标签建议生成

### manage_github_issues.py
**功能**: 通过GitHub API批量管理issues
**操作**:
- 创建/更新标准化标签
- 合并重复issues并添加说明
- 批量更新issues标签
- 生成处理报告

## 📈 效果评估

### 提升项目管理效率
1. **减少重复讨论**: 15个重复issues合并，避免分散注意力
2. **标准化分类**: 30个标准标签，便于快速定位和分工
3. **优先级明确**: 高/中/低优先级，便于开发计划安排
4. **组件清晰**: 按模块分类，便于责任分工

### 开发团队协作优化
1. **查找效率**: 通过标签快速筛选相关issues
2. **工作分配**: 基于组件标签分配给对应团队成员
3. **进度跟踪**: 优先级标签帮助制定开发里程碑
4. **知识管理**: 合并相似issues，集中讨论和解决方案

## 🔄 定期维护

### 推荐频率
- **每周**: 下载新issues并分析
- **每月**: 运行完整的重复检查和标签优化
- **季度**: 评估标签体系并调整

### 维护脚本
```bash
# 周度维护
./scripts/manage_issues.sh
python3 scripts/analyze_issues.py

# 月度维护  
python3 scripts/manage_github_issues.py

# 生成报告
python3 scripts/manage_github_issues.py report
```

## 🔗 相关链接

- [SAGE GitHub Issues](https://github.com/intellistream/SAGE/issues)
- [GitHub API 文档](https://docs.github.com/en/rest/issues)
- [标签最佳实践](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels)

## 🤝 贡献指南

1. 使用标准化标签创建新issues
2. 创建issues前检查是否已有相似内容
3. 定期运行分析工具维护issues质量
4. 反馈标签体系改进建议

---

*最后更新: 2025-08-10*  
*维护者: SAGE开发团队*

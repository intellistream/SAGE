# _scripts 目录

这个目录包含Issues管理工具的核心实现脚本。用户通常不需要直接调用这些脚本，而是通过主入口 `issues_manager.sh` 来使用。

## 核心脚本

### download_issues.py
下载GitHub Issues的核心实现
- 支持按状态过滤（open/closed/all）
- 自动生成Markdown格式的Issues文件
- 按标签自动分类
- 生成统计摘要

### ai_analyzer.py  
AI智能分析Issues的核心实现
- 重复Issues检测
- 标签优化建议
- 优先级评估
- 综合分析报告

### sync_issues.py
同步Issues到远端的核心实现
- 检测本地和远端的差异
- 批量同步更新
- 同步日志记录
- 预览功能

## helpers 目录

包含原有的所有辅助工具和GitHub操作脚本，这些工具为核心功能提供支持。如果需要使用原有的功能，可以直接调用helpers目录中的脚本。

## 使用方式

建议通过主入口脚本使用：
```bash
# 推荐方式
./issues_manager.sh

# 直接调用（高级用户）
python3 _scripts/download_issues.py --help
python3 _scripts/ai_analyzer.py --help  
python3 _scripts/sync_issues.py --help
```

# Batch Issue Management Scripts

这个目录包含用于批量管理SAGE项目GitHub Issues的脚本。

## 主要脚本

### 1. `batch_update_milestone_v01.py`
批量设置milestone为v0.1的脚本
- **功能**: 将2025年8月15日前创建的issues的milestone设置为v0.1
- **范围**: 包括open和closed状态的issues
- **使用**: `python batch_update_milestone_v01.py`

### 2. `batch_set_parent_issues.py`
批量设置parent issues的脚本
- **功能**: 基于团队分工设置parent-child关系
- **规则**: 
  - sage-kernel团队 → parent issue #609
  - sage-apps团队 → parent issue #611  
  - sage-middleware团队 → parent issue #610
  - intellistream/documentation → parent issue #612
- **使用**: `python batch_set_parent_issues.py`

### 3. `batch_set_project_dependencies.py`
GitHub Projects组织脚本
- **功能**: 将issues添加到对应的团队Projects中
- **支持**: 使用GraphQL API操作GitHub Projects V2
- **使用**: `python batch_set_project_dependencies.py`

## 团队映射

```
sage-kernel: CubeLander, Yang-YJY, peilin9990, iliujunn, LIXINYI33
sage-apps: zslchase, FirmamentumX, LaughKing, Jerry01020, yamatanooroch, kms12425-ctrl, LuckyWindovo, cybber695, Li-changwu, huanghaonan1231
sage-middleware: ZeroJustMe, leixy2004, hongrugao, wrp-wrp, Kwan-Yiu, Pygone, KimmoZAG, MingqiWang-coder
intellistream: ShuhaoZhangTony
github-actions: github-actions[bot]
```

## 执行记录

- ✅ **2025-09-10**: 成功处理267个issues的milestone设置为v0.1
- ✅ **2025-09-10**: 成功设置267个issues的基于团队的parent关系
- ✅ **2025-09-10**: 成功将43个新issues添加到GitHub Projects

## 注意事项

1. 所有脚本都需要GitHub token配置
2. 脚本会自动更新本地缓存数据
3. GitHub的native issue relationships功能无法通过公共API自动化设置（详见INVESTIGATION_REPORT.md）

## 相关文档

- `INVESTIGATION_REPORT.md` - GitHub Issue关系功能的详细调查报告
- `_scripts/config.py` - 配置和团队映射
- `_scripts/issue_data_manager.py` - 数据管理器

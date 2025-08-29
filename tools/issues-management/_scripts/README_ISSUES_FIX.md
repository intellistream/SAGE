# Issues错误分配修复系统

## 概述

这套工具用于检测和修复GitHub项目板中错误分配的issues。当issues被分配到不符合作者团队归属的项目时，这些工具可以自动识别并修复这些错误。

## 问题背景

SAGE项目使用三个GitHub项目板来管理不同团队的issues：
- **项目 #12** (sage-kernel): 核心引擎和内核开发
- **项目 #13** (sage-middleware): 中间件和服务层开发  
- **项目 #14** (sage-apps): 应用层开发和集成

但是由于历史原因和人工操作错误，许多issues被分配到了错误的项目板。

## 工具说明

### 1. `fix_misplaced_issues.py` - 错误检测和计划生成

**功能:**
- 扫描所有项目板，检测错误分配的issues
- 基于作者的团队归属判断正确的项目分配
- 生成详细的修复计划文件

**使用方法:**
```bash
python3 fix_misplaced_issues.py
```

**输出:**
- `output/issues_fix_plan_<timestamp>.json` - 修复计划文件
- 控制台统计报告

### 2. `execute_fix_plan.py` - 修复执行

**功能:**
- 根据修复计划执行实际的issues移动
- 支持dry-run模式预览操作
- 自动处理GitHub API的添加和删除操作
- 完整的错误处理和状态报告

**使用方法:**
```bash
# Dry-run模式 (推荐先运行)
python3 execute_fix_plan.py <fix_plan_file.json>

# 实际执行修复
python3 execute_fix_plan.py <fix_plan_file.json> --live
```

**输出:**
- `output/fix_execution_result_<timestamp>.json` - 执行结果文件
- 控制台进度报告

## 工作流程

### 1. 检测错误分配
```bash
cd /home/shuhao/SAGE/tools/issues-management/_scripts
python3 fix_misplaced_issues.py
```

### 2. 预览修复操作
```bash
python3 execute_fix_plan.py ../output/issues_fix_plan_<timestamp>.json
```

### 3. 执行实际修复
```bash
python3 execute_fix_plan.py ../output/issues_fix_plan_<timestamp>.json --live
```

### 4. 验证修复结果
```bash
# 重新扫描确认没有剩余的错误分配
python3 fix_misplaced_issues.py
```

## 团队配置

团队分配规则基于以下配置文件：
- `../meta-data/team_members.json` - 团队成员映射
- `../boards_metadata.json` - 团队到项目的映射

**团队映射:**
- `sage-kernel` → 项目 #12
- `sage-middleware` → 项目 #13  
- `sage-apps` → 项目 #14

## 安全特性

1. **Dry-run模式**: 默认预览模式，不会实际修改数据
2. **确认提示**: 实际执行前需要用户确认
3. **详细日志**: 完整记录所有操作和结果
4. **错误处理**: 单个失败不会影响其他issues的处理
5. **API限制**: 内置延迟避免GitHub API限制

## 成功案例

在2025年8月30日的修复中，系统成功处理了50个错误分配的issues：
- 项目#12: 23个issues移出
- 项目#13: 15个issues移出  
- 项目#14: 12个issues移出

修复了包括Yang-YJY、MingqiWang-coder、CubeLander、KimmoZAG等多位开发者的错误分配issues。

## 注意事项

1. **GitHub Token**: 确保`.github_token`文件存在且有效
2. **API权限**: Token需要有仓库和项目管理权限
3. **网络**: 操作需要稳定的网络连接
4. **备份**: 虽然操作可逆，但建议先在测试环境验证

## 故障排除

### 常见错误
- `Bad credentials`: 检查GitHub token
- `NOT_FOUND`: 确认issue存在且有权限访问
- `Rate limiting`: 增加API调用间隔

### 日志文件
所有操作结果保存在`output/`目录下，可用于问题排查。

## 维护

定期运行检测脚本以确保没有新的错误分配：
```bash
# 建议每周运行一次
python3 fix_misplaced_issues.py
```

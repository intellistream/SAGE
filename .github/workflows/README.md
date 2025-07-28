# GitHub Actions Workflows - 禁用说明

## 🚫 已禁用的测试工作流 (Disabled Test Workflows)

为了节省费用，以下测试工作流已被禁用，不会在PR或push时自动触发：

### 禁用的工作流列表：

1. **`pr-smart-testing.yml`** - PR智能测试
   - 原触发条件：PR到 main/develop/v*.*.* 分支
   - 现状态：仅支持手动触发 (`workflow_dispatch`)

2. **`lighter_test.yml`** - 轻量级运行时测试
   - 原触发条件：push到main分支 + PR到main分支
   - 现状态：仅支持手动触发 (`workflow_dispatch`)

3. **`pr-intelligent-testing.yml`** - PR智能测试
   - 原触发条件：PR到 main/develop/v*.*.* 分支
   - 现状态：仅支持手动触发 (`workflow_dispatch`)

4. **`smart-test.yml`** - AI智能测试
   - 原触发条件：PR到 main/develop 分支
   - 现状态：仅支持手动触发 (`workflow_dispatch`)

5. **`todo-to-issue-pr.yml`** - TODO转Issue工具
   - 原触发条件：PR触发 + 手动触发
   - 现状态：仅支持手动触发 (`workflow_dispatch`)

### 仍然活跃的工作流：

- **无** - 所有工作流都已禁用自动触发

## 🔧 如何手动运行测试

如需运行测试，您可以：

1. **通过GitHub界面手动触发**：
   - 进入 Actions 选项卡
   - 选择相应的工作流
   - 点击 "Run workflow" 按钮

2. **通过GitHub CLI手动触发**：
   ```bash
   gh workflow run "pr-smart-testing.yml"
   gh workflow run "lighter_test.yml"
   gh workflow run "pr-intelligent-testing.yml"
   gh workflow run "smart-test.yml"
   gh workflow run "todo-to-issue-pr.yml"
   ```

3. **重新启用自动触发**：
   如需重新启用自动测试，可以编辑相应的工作流文件，取消注释 `on:` 部分的触发条件。

## 📝 修改记录

- **修改日期**: 2025-07-27
- **修改原因**: 避免自动触发测试以节省费用
- **修改方式**: 将自动触发改为手动触发，添加禁用说明
- **影响范围**: 所有测试相关的GitHub Actions工作流

## ⚠️ 注意事项

- 工作流仍然存在并可以正常运行，只是不会自动触发
- 所有测试逻辑和功能保持不变
- 如需恢复自动触发，只需取消注释相应的触发条件即可
- 建议在重要发布前手动运行相关测试以确保代码质量

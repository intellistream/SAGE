# 🚀 SAGE 代码提交快速参考

## 基本流程（5分钟上手）

```bash
# 1. 准备工作
git checkout main-dev
git pull origin main-dev

# 2. 创建分支（选择合适的前缀）
git checkout -b fix/your-issue-name
git checkout -b feat/your-feature-name

# 3. 修改代码
# 编辑你的文件...

# 4. 测试验证
./quickstart.sh --minimal                    # 测试安装脚本
bash tools/tests/test_issues_manager.sh --quick  # 测试issues manager
bash -n your_script.sh                      # Shell脚本语法检查

# 5. 提交代码
git add 文件名
git commit -m "类型(范围): 简短描述

详细说明...

修改文件:
- 文件1
- 文件2"

# 6. 推送分支
git push -u origin 分支名

# 7. 创建PR
# 访问GitHub提供的链接创建Pull Request
```

## 分支命名规范

| 类型 | 示例 | 说明 |
|------|------|------|
| `fix/` | `fix/ci-cache-permissions` | 修复问题 |
| `feat/` | `feat/vllm-integration` | 新功能 |
| `test/` | `test/suite-improvements` | 测试相关 |
| `docs/` | `docs/contributing-guide` | 文档更新 |
| `refactor/` | `refactor/jobmanager` | 代码重构 |

## 提交信息模板

```
类型(范围): 简短描述

🔧 主要修复/功能:
- 修复了什么问题
- 添加了什么功能
- 改进了什么地方

💡 技术细节:
- 具体的技术实现
- 重要的设计决策

🎯 解决的问题:
- 解决了哪些具体问题
- 改善了什么用户体验

📝 修改文件:
- 文件1
- 文件2
```

## 常用Git命令

```bash
# 查看状态
git status
git diff

# 分支操作
git branch -a                    # 查看所有分支
git checkout main-dev            # 切换分支
git checkout -b new-branch       # 创建并切换

# 提交操作
git add .                        # 添加所有修改
git add 文件名                   # 添加指定文件
git commit -m "提交信息"         # 提交
git push -u origin 分支名        # 推送新分支

# 同步操作
git pull origin main-dev         # 拉取最新代码
git rebase main-dev              # 变基到主分支
```

## 测试检查清单

- [ ] Shell脚本语法：`bash -n script.sh`
- [ ] Python语法：`python -m py_compile script.py`
- [ ] 安装测试：`./quickstart.sh --minimal`
- [ ] 单元测试：`bash tools/tests/optimized_test_runner.sh`
- [ ] Issues测试：`bash tools/tests/test_issues_manager.sh --quick`

## 提交前自检

- [ ] 代码功能正确
- [ ] 测试全部通过
- [ ] 提交信息清晰
- [ ] 文件权限正确
- [ ] 没有敏感信息
- [ ] 遵循代码规范

## 紧急修复流程

```bash
# 1. 快速创建hotfix分支
git checkout main-dev
git pull
git checkout -b fix/urgent-issue

# 2. 快速修复
# 修改文件...

# 3. 快速测试
bash -n modified_script.sh
./quickstart.sh --minimal

# 4. 快速提交
git add .
git commit -m "fix: 紧急修复XXX问题"
git push -u origin fix/urgent-issue

# 5. 立即创建PR并标记为urgent
```

## 获得帮助

- 📖 详细指南：[CONTRIBUTING.md](./CONTRIBUTING.md)
- 🐛 报告问题：[GitHub Issues](https://github.com/intellistream/SAGE/issues)
- 💬 讨论交流：项目维护者

---
💡 **记住：测试先行，提交规范，协作愉快！**

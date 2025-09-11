# SAGE 贡献指南

## 📋 目录
- [新人代码提交流程](#新人代码提交流程)
- [分支管理规范](#分支管理规范)
- [提交信息规范](#提交信息规范)
- [代码质量要求](#代码质量要求)
- [测试要求](#测试要求)
- [常见问题解决](#常见问题解决)

## 🚀 新人代码提交流程

### 第一步：准备工作环境

```bash
# 1. 克隆仓库
git clone https://github.com/intellistream/SAGE.git
cd SAGE

# 2. 切换到主开发分支
git checkout main-dev
git pull origin main-dev

# 3. 安装开发环境
./quickstart.sh --dev
```

### 第二步：创建功能分支

```bash
# 根据功能类型创建分支，使用以下命名规范：
# - fix/xxx: 修复问题
# - feat/xxx: 新功能
# - refactor/xxx: 重构
# - docs/xxx: 文档更新
# - test/xxx: 测试相关

# 示例：修复CI缓存问题
git checkout -b fix/ci-cache-permissions

# 示例：添加新功能
git checkout -b feat/vllm-integration

# 示例：修复测试问题
git checkout -b fix/test-suite-improvements
```

### 第三步：进行开发

```bash
# 1. 编辑代码文件
# 使用你喜欢的编辑器修改代码

# 2. 实时检查修改状态
git status

# 3. 查看具体修改内容
git diff
```

### 第四步：测试验证

```bash
# 1. 运行相关测试
# 对于quickstart修复
./quickstart.sh --minimal

# 对于测试脚本修复
bash tools/tests/test_issues_manager.sh --quick
bash tools/tests/optimized_test_runner.sh

# 2. 检查代码质量
# 如果修改了Python代码
python -m py_compile modified_file.py

# 如果修改了Shell脚本
bash -n modified_script.sh
```

### 第五步：提交代码

```bash
# 1. 添加修改的文件到暂存区
git add 文件名1 文件名2
# 或者添加所有修改
git add .

# 2. 提交代码（使用规范的提交信息）
git commit -m "fix(ci): 修复GitHub Actions缓存权限问题

🔧 主要修复:
- 修复'/var/cache/apt'权限拒绝错误
- 将缓存路径改为用户可写目录
- 优化系统依赖安装流程

💡 技术细节:
- 移除对/var/cache/apt的缓存依赖(需要root权限)
- 使用~/.cache/pip和/tmp/apt-cache作为缓存路径
- 简化apt更新逻辑，使用-qq减少输出

🎯 解决的问题:
- CI post job cleanup失败
- 缓存保存权限拒绝错误

📝 修改文件:
- .github/workflows/dev-ci.yml"
```

### 第六步：推送分支

```bash
# 推送新分支到远程仓库
git push -u origin 分支名

# 示例
git push -u origin fix/ci-cache-permissions
```

### 第七步：创建Pull Request

1. 访问GitHub提供的PR链接（推送后会显示）
2. 填写PR描述，包括：
   - 问题描述
   - 解决方案
   - 测试结果
   - 影响范围

## 🌲 分支管理规范

### 主要分支
- `main-dev`: 主开发分支，所有功能分支从这里分出
- `main`: 稳定发布分支
- `feature/xxx`: 大型功能开发分支

### 功能分支命名规范
```
fix/问题描述          # 修复问题
feat/功能名称         # 新功能
refactor/重构内容     # 代码重构
docs/文档内容         # 文档更新
test/测试内容         # 测试相关
style/样式调整        # 代码格式化
perf/性能优化         # 性能优化
```

### 示例分支名
```
fix/ci-cache-permissions
fix/test-suite-improvements
fix/quickstart-ci-issues
feat/vllm-quickstart-integration
feat/new-memory-manager
refactor/jobmanager-architecture
docs/contributing-guide
test/unit-test-improvements
```

## 💬 提交信息规范

### 基本格式
```
<类型>(范围): 简短描述

详细描述（可选）
- 具体修改内容
- 技术细节
- 解决的问题

修改文件:
- 文件1
- 文件2
```

### 类型说明
- `fix`: 修复问题
- `feat`: 新功能
- `refactor`: 重构
- `docs`: 文档
- `test`: 测试
- `style`: 格式化
- `perf`: 性能优化
- `ci`: CI/CD相关

### 范围说明
- `quickstart`: 安装脚本
- `ci`: CI/CD系统
- `tests`: 测试系统
- `core`: 核心功能
- `libs`: 库文件
- `docs`: 文档

### 提交信息示例

#### 修复问题
```
fix(ci): 修复GitHub Actions缓存权限问题

🔧 主要修复:
- 修复'/var/cache/apt'权限拒绝错误
- 将缓存路径改为用户可写目录

📝 修改文件:
- .github/workflows/dev-ci.yml
```

#### 新功能
```
feat(vllm): 添加VLLM快速启动支持

✨ 新功能:
- 集成VLLM到quickstart脚本
- 添加自动环境检测
- 支持GPU加速配置

📝 修改文件:
- quickstart.sh
- tools/install/vllm_installer.sh
```

#### 测试修复
```
fix(tests): 修复测试套件中的卡住和超时问题

🔧 主要修复:
- 修复test_issues_manager.sh中的'未知测试模式'错误
- 解决测试脚本卡住问题，添加超时处理
- 优化sage-kernel包的pytest超时配置

📝 修改文件:
- tools/tests/test_issues_manager.sh
- tools/tests/optimized_test_runner.sh
```

## 🧪 测试要求

### 提交前必须测试

1. **语法检查**
   ```bash
   # Shell脚本
   bash -n script.sh
   
   # Python脚本
   python -m py_compile script.py
   ```

2. **功能测试**
   ```bash
   # 安装脚本测试
   ./quickstart.sh --minimal
   
   # 单元测试
   bash tools/tests/optimized_test_runner.sh
   
   # Issues manager测试
   bash tools/tests/test_issues_manager.sh --quick
   ```

3. **集成测试**
   ```bash
   # 完整安装测试
   ./quickstart.sh --dev
   
   # 验证安装
   python -c "import sage; print(sage.__version__)"
   ```

## 🔧 代码质量要求

### Shell脚本
- 使用`set -e`进行错误检查
- 添加必要的注释
- 使用函数封装逻辑
- 处理边界情况和错误

### Python代码
- 遵循PEP 8规范
- 添加类型注解
- 编写单元测试
- 添加适当的文档字符串

### 通用要求
- 代码可读性强
- 添加必要注释
- 处理异常情况
- 避免硬编码

## 🆘 常见问题解决

### 1. 分支落后于主分支
```bash
git checkout main-dev
git pull origin main-dev
git checkout your-branch
git rebase main-dev
```

### 2. 提交信息写错了
```bash
# 修改最后一次提交信息
git commit --amend -m "新的提交信息"
```

### 3. 想要撤销某些修改
```bash
# 撤销工作区修改
git checkout -- 文件名

# 撤销暂存区修改
git reset HEAD 文件名
```

### 4. 测试失败怎么办
```bash
# 查看详细错误
bash -x test_script.sh

# 检查权限
ls -la 文件名

# 查看日志
cat logs/install.log
```

### 5. CI构建失败
- 查看GitHub Actions日志
- 本地复现CI环境测试
- 检查文件权限问题
- 验证依赖是否正确安装

## 📚 参考资源

- [Git官方文档](https://git-scm.com/doc)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [SAGE开发文档](./README.md)

## 🤝 获得帮助

如果遇到问题，可以：
1. 查看这个贡献指南
2. 搜索已有的Issues
3. 创建新的Issue描述问题
4. 联系项目维护者

---

**记住：好的代码提交不仅是功能正确，更要让其他开发者容易理解和维护！** 🚀

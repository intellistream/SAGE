# Pre-commit 自动修复工具使用指南

**Date**: 2025-10-24
**Author**: SAGE Team
**Summary**: 详细指南，帮助开发者理解和处理 pre-commit hooks 自动格式化带来的类型错误问题

## 问题背景

当你提交代码时，pre-commit hooks 会自动运行多个工具（black、isort、ruff、mypy）。这些工具会：
- ✅ **自动格式化代码**（这是好事）
- ⚠️ **可能暴露新的类型错误**（这会让人困惑）

### 典型现象

```bash
# 你只修复了 file_a.py
git add file_a.py
git commit -m "fix: 修复类型错误"

# pre-commit 运行后：
# - black 自动格式化了 file_b.py, file_c.py
# - isort 修改了它们的 import 语句
# - mypy 发现 file_b.py 有新的类型错误！

# 你会想：我明明没改 file_b.py，为什么它有错误了？
```

## 原因分析

### 为什么会产生新错误？

1. **类型注解格式化**
   ```python
   # 原始代码（使用字符串注解，mypy 检查不严格）
   def func(param: "Optional[str]" = None):
       self.field: "str" = param

   # black/isort 自动修改后（移除字符串，mypy 检查更严格）
   def func(param: str | None = None):
       self.field: str = param  # ❌ 错误！str 不能是 None
   ```

2. **Import 重新排序暴露问题**
   ```python
   # 原始代码（循环导入被隐藏）
   from typing import TYPE_CHECKING
   from module_a import ClassA  # 可能有循环导入

   # isort 重新排序后
   from module_a import ClassA  # 循环导入暴露！
   from typing import TYPE_CHECKING
   ```

3. **格式化改变了语义**
   ```python
   # 原始代码
   result = function(
       arg1, arg2,
       arg3  # 可能少了逗号
   )

   # black 格式化后
   result = function(arg1, arg2, arg3)  # 现在参数顺序错误变明显了
   ```

## 正确的修复流程

### 方法一：分步修复（推荐给学生）

```bash
# 1. 先提交你的核心修复（跳过所有检查）
SKIP=mypy,black,isort,ruff,detect-secrets git commit -m "fix: 核心类型错误修复"

# 2. 手动运行格式化工具，看它们会改什么
python -m black packages/
python -m isort packages/

# 3. 查看被自动修改的文件
git status

# 4. 对这些文件运行 mypy，看是否有新错误
git status --short | awk '{print $2}' | xargs python -m mypy --ignore-missing-imports

# 5. 如果有新错误，逐个修复
# 6. 再次提交（这次可以让 pre-commit 运行）
git add .
git commit -m "fix: 修复自动格式化后的类型错误"
```

### 方法二：批量处理（推荐给经验丰富者）

```bash
# 1. 先对所有代码运行格式化（一次性暴露所有问题）
python -m black packages/
python -m isort packages/
git add .
git commit -m "style: 统一代码格式"

# 2. 然后专注修复类型错误
python -m mypy packages/ --ignore-missing-imports > /tmp/mypy_errors.txt

# 3. 按类别修复错误
# 4. 提交时就不会再有格式化变动了
```

### 方法三：临时禁用自动修复（调试时使用）

```bash
# 完全跳过 pre-commit
git commit --no-verify -m "WIP: 调试中"

# 或者只跳过特定工具
SKIP=black,isort git commit -m "fix: 只检查类型"
```

## 理解关键点

### 🔑 自动工具不会无限循环

- **格式化是幂等的**：black 运行一次后，再次运行不会有变化
- **错误总数会收敛**：修复错误 → 暴露新错误 → 修复新错误 → 最终稳定
- **不会越修越多**：新暴露的错误是**本来就存在的**，只是被隐藏了

### 📈 错误收敛过程示例

```
迭代 0: 340 个原始错误
迭代 1: 修复 50 个 → 剩余 290 个 → 格式化暴露 10 个新的 → 总计 300 个
迭代 2: 修复 60 个（包括新的10个）→ 剩余 240 个 → 格式化暴露 5 个 → 总计 245 个
迭代 3: 修复 45 个 → 剩余 200 个 → 格式化不再有变化 → 总计 200 个
迭代 4: 修复 100 个 → 剩余 100 个 → 稳定
迭代 5: 修复 100 个 → 完成！✅
```

**关键**：每次迭代，真实的错误总数在**持续减少**。

## 如何避免困惑

### ✅ 推荐做法

1. **先格式化，再修复**
   ```bash
   # 第一步：让所有代码格式统一
   ./manage.sh dev quality  # 运行所有格式化工具

   # 第二步：现在开始修复类型错误
   python -m mypy packages/ > errors.txt
   ```

2. **理解自动修改的范围**
   ```bash
   # 提交前先看看哪些文件会被修改
   git add <your-files>
   pre-commit run --files <your-files>
   git status  # 查看新增的修改
   ```

3. **分批提交**
   - 格式化的提交单独做
   - 类型修复的提交单独做
   - 不要混在一起

### ❌ 避免做法

1. **不要盲目 `type: ignore`**
   ```python
   # 错误做法：看到错误就忽略
   self.field: str = None  # type: ignore

   # 正确做法：理解并修复
   self.field: str | None = None
   ```

2. **不要频繁跳过检查**
   ```bash
   # 不要每次都这样
   git commit --no-verify

   # 偶尔调试可以，但要记得回来修复
   ```

3. **不要一次修改太多文件**
   - 每次提交控制在 3-5 个相关文件
   - 更容易定位问题

## 调试技巧

### 当你看到"意外的"类型错误时

```bash
# 1. 查看这个文件是否被自动修改了
git diff <file>

# 2. 查看修改前后的类型注解变化
git diff <file> | grep -A 2 -B 2 "def\|class\|:"

# 3. 理解为什么自动工具做了这个修改
# - black: PEP 8 代码风格
# - isort: PEP 8 import 排序
# - ruff: 现代 Python 最佳实践（如 Union[X,Y] → X|Y）

# 4. 修复类型不一致
# 通常是：参数可以是 None，但字段/返回值不能是 None
```

### 使用工具帮助理解

```bash
# 查看某个文件的所有类型错误
python -m mypy <file> --show-error-codes --show-column-numbers

# 只看特定类型的错误
python -m mypy <file> 2>&1 | grep "\[assignment\]"

# 对比修改前后的错误数量
git stash
python -m mypy <file> 2>&1 | wc -l  # 修改前
git stash pop
python -m mypy <file> 2>&1 | wc -l  # 修改后
```

## 学生常见问题 FAQ

### Q1: 我只改了一个文件，为什么 pre-commit 修改了 10 个文件？

**A**: Pre-commit 配置了 `--all-files` 或者依赖关系导致。查看 `.pre-commit-config.yaml` 中每个 hook 的范围。

### Q2: 格式化后错误变多了，是不是工具有 bug？

**A**: 不是 bug！是工具帮你**暴露了隐藏的问题**。格式化前代码就有问题，只是语法糖或字符串注解隐藏了。

### Q3: 我应该先修复类型错误还是先格式化？

**A**: **先格式化**！用 `./manage.sh dev quality` 一次性格式化所有代码，然后再专注修复类型错误。

### Q4: 能不能禁用自动格式化？

**A**: 可以，但**不推荐**。格式化保证代码风格统一，对团队协作很重要。正确做法是：
1. 一开始就格式化好所有代码
2. 然后配置编辑器自动格式化（保存时）
3. 这样提交时就不会有大的变动

### Q5: 循环修复会不会永远修不完？

**A**: **不会**！原因：
- 格式化是幂等的（第二次运行不会再改）
- 每次修复都在减少真实的错误数量
- 最多 3-4 轮迭代就会稳定

## 工具配置建议

### VS Code 配置（推荐）

```json
{
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "python.sortImports.provider": "isort",
  "python.linting.mypyEnabled": true,
  "python.linting.mypyArgs": [
    "--ignore-missing-imports",
    "--show-error-codes"
  ]
}
```

这样每次保存文件时：
- black 自动格式化 ✅
- isort 自动排序 import ✅
- mypy 实时显示类型错误 ✅
- 提交时不会有意外！✅

### Pre-commit 配置理解

```yaml
# 示例 .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black
        # 会自动格式化你修改的文件

  - repo: https://github.com/pycqa/isort
    hooks:
      - id: isort
        # 会自动排序 import

  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
        # 检查类型错误，如果有错误会阻止提交
```

## 总结

### 🎯 核心理念

1. **自动工具是朋友，不是敌人**
   - 它们帮你发现隐藏的问题
   - 它们强制执行最佳实践

2. **理解工具行为**
   - black: 格式化代码风格
   - isort: 排序和分组 imports
   - mypy: 类型检查
   - ruff: 现代化 Python 语法

3. **正确的工作流**
   ```
   格式化（一次性） → 修复类型错误 → 保持格式化（编辑器自动）
   ```

4. **错误总数会收敛**
   - 不会无限循环
   - 每次迭代都在进步
   - 3-5 轮就能完成

### 📚 延伸阅读

- [Black 文档](https://black.readthedocs.io/)
- [isort 文档](https://pycqa.github.io/isort/)
- [Mypy 文档](https://mypy.readthedocs.io/)
- [Pre-commit 文档](https://pre-commit.com/)
- [PEP 8 风格指南](https://peps.python.org/pep-0008/)
- [Python 类型提示指南](https://docs.python.org/3/library/typing.html)

---

**记住**：当你看到"意外"的类型错误时，不要慌张，这是工具在帮你发现代码中隐藏的问题！🎉

# Pre-commit 自动修复 - 快速参考

**Date**: 2025-10-24
**Author**: SAGE Team  
**Summary**: 快速参考卡片，提供三种解决方案应对 pre-commit 自动格式化问题

## 🚨 当你看到"意外"的类型错误时

### 不要慌张！这是正常的！

```
你的修改:
  fix_file_a.py  ✅ 修复了 3 个错误

Pre-commit 自动做了:
  file_b.py  📝 自动格式化
  file_c.py  📝 自动格式化
  file_d.py  📝 自动格式化

结果:
  file_b.py  ❌ 暴露了 2 个新错误
  file_c.py  ❌ 暴露了 1 个新错误
```

**原因**: 格式化工具暴露了**本来就存在**的隐藏问题！

## ✅ 三步解决方案

### 方法一：分步提交（推荐新手）

```bash
# 1. 先提交核心修复（跳过自动检查）
SKIP=mypy,black,isort,ruff git commit -m "fix: 核心修复"

# 2. 手动格式化，看会改什么
python -m black .
python -m isort .

# 3. 查看新产生的错误
git status --short | awk '{print $2}' | xargs python -m mypy --ignore-missing-imports

# 4. 修复新错误，再次提交
git add .
git commit -m "fix: 格式化后的类型修复"
```

### 方法二：使用辅助脚本（最简单）

```bash
# 检查当前状态
./tools/maintenance/fix-types-helper.sh check-status

# 查看新增了哪些错误
./tools/maintenance/fix-types-helper.sh show-new-errors

# 安全提交（会一步步提示）
./tools/maintenance/fix-types-helper.sh safe-commit "fix: 修复类型错误"
```

### 方法三：先格式化再修复（推荐老手）

```bash
# 第一次：格式化所有代码
./tools/maintenance/fix-types-helper.sh format-first
git add .
git commit -m "style: 统一代码格式"

# 之后：专注修复类型错误
python -m mypy packages/ > errors.txt
# 修复错误...
git commit -m "fix: 类型错误修复"
```

## 🎯 核心原则

### ✅ 会收敛，不会无限循环

```
迭代 1: 340 错误 → 修复 50 → 剩 290 → 格式化暴露 10 → 总 300
迭代 2: 300 错误 → 修复 60 → 剩 240 → 格式化暴露 5  → 总 245
迭代 3: 245 错误 → 修复 45 → 剩 200 → 格式化稳定   → 总 200
迭代 4: 200 错误 → 修复 100 → 剩 100 → 完成 ✅
```

**关键**: 真实错误数在**持续减少**！

### ⚠️ 常见陷阱

```python
# ❌ 陷阱 1: 盲目使用 type: ignore
self.field: str = None  # type: ignore  # 错误！

# ✅ 正确: 理解并修复
self.field: str | None = None  # 正确！

# ❌ 陷阱 2: 局部类型注解不完整
def func(param: str | None = None):
    self.field: str = param  # 错误！field 不能是 None

# ✅ 正确: 保持类型一致
def func(param: str | None = None):
    self.field: str | None = param  # 正确！
```

## 🔧 常用命令

```bash
# 查看自动修改了哪些文件
git status --short

# 查看某个文件的修改详情
git diff <file>

# 解释为什么文件被修改
./tools/maintenance/fix-types-helper.sh explain-diff <file>

# 撤销自动修改（小心使用）
git reset --hard HEAD

# 只检查修改的文件
git status --short | awk '{print $2}' | xargs python -m mypy --ignore-missing-imports

# 跳过特定检查
SKIP=mypy git commit -m "..."
SKIP=black,isort git commit -m "..."
```

## 📚 自动工具说明

| 工具 | 作用 | 可能的"副作用" |
|------|------|---------------|
| **black** | 统一代码格式 | 可能改变缩进、空行、括号位置 |
| **isort** | 排序 imports | 可能改变 import 顺序、单行/多行格式 |
| **ruff** | 现代化语法 | `Union[X,Y]` → `X\|Y`, `Optional[X]` → `X\|None` |
| **mypy** | 类型检查 | 不修改代码，但检查更严格 |

## 🎓 理解关键点

1. **格式化是幂等的**: 运行一次后，再次运行不会再改
2. **新错误不是新产生的**: 它们本来就存在，只是被隐藏了
3. **总数会收敛**: 3-5 轮迭代就会稳定
4. **工具是朋友**: 它们在帮你发现隐藏的 bug！

## 💡 配置建议

### VS Code 设置（保存时自动格式化）

```json
{
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

这样每次保存就自动格式化，提交时就不会有意外！

## 🆘 遇到问题？

1. **错误越改越多?**
   - 运行 `./tools/maintenance/fix-types-helper.sh show-new-errors` 分析
   - 新错误是被暴露的，不是新产生的

2. **不知道从哪里开始?**
   - 运行 `./tools/maintenance/fix-types-helper.sh format-first` 一次性格式化
   - 然后专注修复类型错误

3. **提交被阻止?**
   - 查看 pre-commit 输出，了解是哪个工具报错
   - 修复错误，或临时跳过: `SKIP=mypy git commit`

4. **想撤销自动修改?**
   - `git reset --hard HEAD` (⚠️ 会丢失所有未提交的修改)
   - 或 `git checkout -- <file>` (只撤销特定文件)

---

**记住**: 自动工具是你的朋友！它们在帮你写出更好、更安全的代码！🎉

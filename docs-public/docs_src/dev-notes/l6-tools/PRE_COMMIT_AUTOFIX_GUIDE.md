# Pre-commit 自动修复与类型检查指南

**Date**: 2025-11-25 \
**Author**: SAGE Development Team \
**Summary**: 合并《Pre-commit 自动修复工具使用指南》与《快速参考》，提供背景解释、实操流程与速查表，帮助贡献者在自动格式化触发类型错误时快速收敛。

______________________________________________________________________

## 1. 发生了什么？

当 `pre-commit` 运行 `black`、`isort`、`ruff`、`mypy` 时，可能出现：

```
你只修改了 file_a.py ✅

pre-commit 自动改动了：
  file_b.py 📝
  file_c.py 📝

结果：
  file_b.py ❌ 暴露 2 个类型错误
  file_c.py ❌ 暴露 1 个类型错误
```

**原因**：格式化或 import 排序让原本被隐藏的类型不一致暴露出来（例如 `Optional[str]` 被 `black` 展开成 `str | None`
之后，赋值语句突然违反类型约束）。

______________________________________________________________________

## 2. 收敛原则

1. **格式化是幂等的**：`black` / `isort` 再运行一次不会继续改动。
1. **新错误并非新引入**：它们原本就存在，只是以前未被静态检查捕获。
1. **错误数量会递减**：
   - 迭代 1：340 → 修复 50 → 格式化暴露 10 → 300
   - 迭代 2：300 → 修复 60 → 暴露 5 → 245
   - 迭代 3：245 → 修复 45 → 暴露 0 → 200
   - … 最终 0

______________________________________________________________________

## 3. 三种推荐流程

### 3.1 分步提交（适合新手）

```bash
# Step 1: 先提交核心修复，跳过自动检查（仅限 WIP）
SKIP=mypy,black,isort,ruff git commit -m "fix: 核心修复"

# Step 2: 手动格式化并查看改动
python -m black .
python -m isort .
git status

# Step 3: 只对被动改动的文件运行 mypy
git status --short | awk '{print $2}' | \
  xargs python -m mypy --ignore-missing-imports

# Step 4: 修复新错误后重新提交
git add .
git commit -m "fix: 格式化后的类型修复"
```

### 3.2 辅助脚本（最简单）

```bash
./tools/maintenance/fix-types-helper.sh check-status
./tools/maintenance/fix-types-helper.sh show-new-errors
./tools/maintenance/fix-types-helper.sh safe-commit "fix: 修复类型错误"
```

脚本会：

- 运行格式化 → 显示新增错误 → 指导逐步提交。

### 3.3 先格式再修复（适合熟练者）

```bash
./tools/maintenance/fix-types-helper.sh format-first
python -m mypy packages/ > /tmp/mypy_errors.txt
# 逐个修复并提交干净的类型补丁
```

______________________________________________________________________

## 4. 快速命令参考

| 任务                 | 命令                                                          |
| -------------------- | ------------------------------------------------------------- |
| 查看被自动修改的文件 | `git status --short`                                          |
| 解释 diff            | `./tools/maintenance/fix-types-helper.sh explain-diff <file>` |
| 只对修改文件跑 mypy  | \`git status --short                                          |
| 暂时跳过特定 hook    | `SKIP=mypy git commit -m "..."`                               |
| 完全跳过（仅限 WIP） | `git commit --no-verify -m "..."`                             |

### 常见陷阱

```python
# ❌ 盲目的 type: ignore
self.name: str = None  # type: ignore

# ✅ 真实修复
self.name: str | None = None
```

```python
# ❌ 字符串注解在格式化后暴露问题
value: "Optional[str]" = None

# ✅ 与实现保持一致
value: str | None = None
```

______________________________________________________________________

## 5. VS Code / 编辑器配置建议

```json
{
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "python.linting.mypyEnabled": true,
  "python.linting.mypyArgs": [
    "--ignore-missing-imports",
    "--show-error-codes"
  ]
}
```

- 保存即格式化，提交前不会再出现大块 diff。
- VS Code 中实时显示 mypy 错误，减少提交前的惊喜。

______________________________________________________________________

## 6. FAQ

| 问题                         | 解答                                                              |
| ---------------------------- | ----------------------------------------------------------------- |
| **为什么我没改的文件报错？** | 因为自动格式化让隐藏的问题显形，它们原本就存在。                  |
| **会不会一直循环？**         | 不会，格式化幂等，错误数量严格下降。                              |
| **能否禁用自动格式化？**     | 可以，但不推荐；正确做法是一次性统一格式，然后靠编辑器保持一致。  |
| **如何撤销自动改动？**       | `git checkout -- <file>` 或 `git reset --hard HEAD`（谨慎使用）。 |

______________________________________________________________________

## 7. Workflow 建议

1. `./manage.sh dev quality` 先统一格式 → 再集中修复类型。
1. 使用 `sage-dev quality fix` / `sage-dev quality check` 替换零散的脚本。
1. `pre-commit install` 后首次运行时间可能较长（会安装工具）。
1. 真正需要跳过 hook 时，一定在提交信息说明原因，后续补齐。

______________________________________________________________________

## 8. 后续改进

- `fix-types-helper.sh` 计划增加 `--files-from-mypy` 参数，直接定位 `mypy` 输出中的文件。
- 为 `sage-dev quality` 添加 `--changed-only` 选项，专门检查当前 diff。
- 继续补充 FAQ 中的典型报错案例，供新贡献者参考。

# 🧹 SAGE 自动清理功能说明

## 概述

SAGE 项目现在提供了多种自动清理功能，帮助你保持项目整洁、节省磁盘空间、避免因缓存问题导致的奇怪错误。

## 功能列表

### 1. 安装前自动清理 (quickstart.sh)

**默认启用**：从现在开始，`quickstart.sh` 在运行时会**自动清理**缓存和临时文件。

**跳过清理：**

如果您想跳过清理（例如快速测试），可以使用 `--no-clean` 选项：

```bash
# 跳过清理，直接安装
./quickstart.sh --dev --no-clean

# 或使用其他别名
./quickstart.sh --dev --skip-clean
```

**强制清理（明确指定）：**

```bash
# 明确指定要清理（虽然默认就会清理）
./quickstart.sh --dev --clean
```

**清理内容：**

- ✅ 所有 `__pycache__` 目录
- ✅ 所有 `.pyc` 和 `.pyo` 文件
- ✅ 所有 `.egg-info` 目录
- ✅ `build/` 和 `dist/` 目录
- ✅ 空目录（排除 `.git` 和 `.sage`）

**推荐使用场景：**

- 🔄 版本升级时（默认自动清理）
- 🔄 重新安装时（默认自动清理）
- 🐛 遇到奇怪的导入或缓存问题时（默认自动清理）
- 💾 磁盘空间不足时（默认自动清理）
- ⚡ 快速测试时使用 `--no-clean` 跳过清理

### 2. 手动清理命令 (manage.sh)

项目提供了两个清理命令：

```bash
# 快速清理（推荐日常使用）
./manage.sh clean

# 深度清理（包括日志文件）
./manage.sh clean-deep
```

**快速清理内容：**

- Python 缓存（`__pycache__`, `.pyc`, `.pyo`）
- 代码质量工具缓存（`.mypy_cache`, `.ruff_cache`, `.pytest_cache`）
- 构建产物（`build/`, `dist/`, `*.egg-info`）
- 空目录
- 显示清理统计信息

**深度清理额外内容：**

- 日志文件（`.sage/logs/`）
- 更彻底的递归清理

### 3. Git Hooks 自动提醒

每次切换分支时（通过 `git checkout`），系统会自动检查距离上次清理的时间。

**提醒规则：**

- ⏰ 每 30 天提醒一次
- 💡 提示运行清理命令
- 📝 记录在 `.sage/.last_cleanup_reminder`

**示例输出：**

```
💡 提示：已经一段时间没有清理缓存了，建议运行：
   ./manage.sh clean         # 快速清理缓存和空目录
   ./manage.sh clean-deep    # 深度清理（包括日志）
```

## 使用场景对照表

| 场景         | 推荐命令                           | 说明              |
| ------------ | ---------------------------------- | ----------------- |
| 首次安装     | `./quickstart.sh --dev`            | 默认自动清理      |
| 版本升级     | `./quickstart.sh --dev`            | 默认自动清理      |
| 快速测试     | `./quickstart.sh --dev --no-clean` | 跳过清理加速      |
| 日常开发     | `./manage.sh clean`                | 定期清理缓存      |
| 遇到奇怪问题 | `./quickstart.sh --dev`            | 默认自动清理      |
| 释放磁盘空间 | `./manage.sh clean-deep`           | 深度清理          |
| CI/CD 环境   | `./quickstart.sh --yes`            | 默认清理+自动确认 |

## 技术实现

### 文件结构

```
tools/
  maintenance/
    helpers/
      pre_install_cleanup.sh      # 安装前清理脚本
      quick_cleanup.sh            # 快速清理脚本（manage.sh clean）
    git-hooks/
      post-checkout               # Git hook 清理提醒
  install/
    download_tools/
      argument_parser.sh          # 参数解析（--clean 选项）
```

### 空文件夹处理

Git 不会跟踪空文件夹，所以像 `tools/git-hooks` 这样的空文件夹只存在于本地。清理脚本会自动删除这些空文件夹，但会排除：

- `.git/*` - Git 内部目录
- `docs-public` - 子模块
- `.sage/*` - SAGE 运行时目录

### 自定义清理

如果需要自定义清理行为，可以直接编辑：

- `tools/maintenance/helpers/pre_install_cleanup.sh` - 安装前清理逻辑
- `tools/maintenance/helpers/quick_cleanup.sh` - 日常清理逻辑

## 常见问题

### Q: 清理会删除我的代码吗？

**A:** 不会。清理只删除：

- Python 生成的缓存文件（`.pyc`, `__pycache__`）
- 构建工具生成的临时文件
- 空目录
- 你的源代码文件（`.py`）完全安全

### Q: 清理后需要重新安装吗？

**A:**

- 使用 `./manage.sh clean` - **不需要重新安装**，只是清理缓存
- 使用 `./quickstart.sh` - **会自动清理并安装**（默认行为）
- 使用 `./quickstart.sh --no-clean` - **跳过清理直接安装**

### Q: 能否禁用 Git hooks 的清理提醒？

**A:** 可以，删除或修改 `.git/hooks/post-checkout` 文件即可。

### Q: 清理会影响性能吗？

**A:**

- 首次导入可能稍慢（需要重新生成 `.pyc` 文件）
- 后续运行速度正常
- 通常清理带来的好处（避免缓存问题）大于这点性能影响

## 统计示例

典型的清理结果：

```bash
$ ./manage.sh clean
🧹 清理 SAGE 项目缓存和临时文件...
✅ 删除了 386 个 __pycache__ 目录
✅ 删除了 13 个 .ruff_cache 目录
✅ 删除了 12 个 .pytest_cache 目录
✅ 删除了 12 个 .egg-info 目录
✅ 删除了 1283 个空目录

🎉 清理完成！总共清理了 1707 个文件/目录
```

## 最佳实践

1. **默认清理**: `quickstart.sh` 现在默认会清理缓存，无需额外参数
1. **定期清理**: 建议每月运行一次 `./manage.sh clean`
1. **升级前清理**: 升级 SAGE 版本前，直接运行 `./quickstart.sh --dev`（默认清理）
1. **快速测试**: 如需快速安装测试，使用 `./quickstart.sh --dev --no-clean`
1. **CI 环境**: 使用 `./quickstart.sh --yes`（默认清理+自动确认）
1. **磁盘空间紧张**: 使用 `./manage.sh clean-deep` 释放更多空间

## 参考

- [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md) - 问题排查指南
- [INSTALLATION_VALIDATION.md](../../INSTALLATION_VALIDATION.md) - 安装验证
- [cleanup-automation.md](cleanup-automation.md) - 清理自动化（本文档）

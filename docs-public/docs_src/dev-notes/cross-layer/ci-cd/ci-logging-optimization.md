# CI 环境下的日志优化

## 问题描述

在 CI 环境（如 GitHub Actions）下，安装依赖包时会产生大量的 spinner 动画输出：

```text
⠏ 安装依赖包... lazy-loader
⠋ 安装依赖包... lazy-loader
⠙ 安装依赖包... lazy-loader
... (重复多次)
```

这些动画在交互式终端中显示为旋转动画，但在 CI 日志中会展开成多行，浪费日志空间且无实际意义。

## 解决方案

通过检测 CI 环境变量（`CI`, `GITHUB_ACTIONS`, `CONTINUOUS_INTEGRATION`），自动切换输出模式：

### 交互环境（默认）

- 显示旋转 spinner 动画
- 显示实时更新的进度条（覆盖式）
- 提供更好的视觉反馈

### CI 环境

- **`log_pip_install_with_progress`**: 仅在包名变化时输出一行 `Installing: <package-name>`
- **`start_spinner`**: 输出一行静态消息，不旋转
- **`show_spinner`**: 不输出任何内容
- **`show_progress_bar`**: 仅在 10% 的倍数时输出（0%, 10%, 20%, ... 100%）

## 影响的文件

1. `tools/install/display_tools/logging.sh`

   - `log_pip_install_with_progress()`: 主要的 pip 安装进度函数
   - `start_spinner()`: 启动 spinner 动画
   - `stop_spinner()`: 停止 spinner 动画

1. `tools/install/display_tools/progress_bar.sh`

   - `show_progress_bar()`: 显示进度条
   - `show_spinner()`: 显示旋转动画
   - `stop_spinner()`: 停止动画

## 测试

运行测试脚本查看不同环境下的输出效果：

```bash
# 测试交互环境和 CI 环境
./tools/install/test_ci_logging.sh
```

## 预期效果

### CI 日志示例（修复后）

```text
Installing: lazy-loader
Installing: numpy
Installing: scipy
安装进度: 0% (0/10)
安装进度: 10% (1/10)
安装进度: 20% (2/10)
...
```

### 交互环境（不变）

依然保持原有的动画效果和用户体验。

## 技术细节

### CI 环境检测

```bash
if [[ "${CI:-false}" == "true" ]] ||
   [[ "${GITHUB_ACTIONS:-false}" == "true" ]] ||
   [[ "${CONTINUOUS_INTEGRATION:-false}" == "true" ]]; then
    is_ci=true
fi
```

### 日志去重

在 CI 模式下，使用 `last_logged_pkg` 变量避免重复打印相同的包名：

```bash
if [ -n "$current_pkg" ] && [ "$current_pkg" != "$last_logged_pkg" ]; then
    echo "  Installing: $current_pkg" >&2
    last_logged_pkg="$current_pkg"
fi
```

## 相关 Issue

解决了 CI 环境下安装依赖时产生的大量无意义日志输出问题（如 lazy-loader spinner 问题）。

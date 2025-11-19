# SAGE 安装工具测试套件

本目录包含 SAGE 环境隔离、自动虚拟环境创建、安装跟踪和清理功能的测试套件。

## 📋 测试清单

### 单元测试

1. **环境配置测试** (`test_environment_config.sh`)

   - 虚拟环境检测（Conda、Python venv、系统环境）
   - 自动虚拟环境创建
   - 环境隔离检查
   - CI 环境处理

1. **清理工具测试** (`test_cleanup_tools.sh`)

   - 安装信息跟踪
   - 包列表记录
   - 卸载脚本功能
   - 完整跟踪和清理流程

### 集成测试

3. **端到端集成测试** (`test_e2e_integration.sh`)
   - 完整的安装→跟踪→清理工作流
   - 多种环境配置测试
   - Makefile 集成验证
   - 文档一致性检查

## 🚀 快速开始

### 运行所有单元测试

```bash
# 从 SAGE 根目录运行
cd /path/to/SAGE

# 测试环境配置
bash tools/install/tests/test_environment_config.sh

# 测试清理工具
bash tools/install/tests/test_cleanup_tools.sh
```

### 运行端到端测试

```bash
# 运行完整的集成测试（包括自动虚拟环境创建、安装跟踪、清理）
bash tools/install/tests/test_e2e_integration.sh
```

### 运行所有测试

```bash
# 一次性运行所有测试
for test in tools/install/tests/test_*.sh; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "运行: $(basename $test)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    bash "$test"
    echo ""
done
```

## 📊 测试覆盖范围

### 环境配置模块

| 功能             | 测试用例    | 状态 |
| ---------------- | ----------- | ---- |
| 检测 Conda 环境  | ✅ 3 个测试 | 通过 |
| 检测 Python venv | ✅ 3 个测试 | 通过 |
| 检测系统环境     | ✅ 2 个测试 | 通过 |
| 自动创建虚拟环境 | ✅ 3 个测试 | 通过 |
| CI 环境跳过检查  | ✅ 2 个测试 | 通过 |

**总计**: 13 个测试用例，100% 通过率

### 清理工具模块

| 功能         | 测试用例    | 状态 |
| ------------ | ----------- | ---- |
| 记录安装信息 | ✅ 4 个测试 | 通过 |
| show 命令    | ✅ 1 个测试 | 通过 |
| 卸载帮助选项 | ✅ 1 个测试 | 通过 |
| --yes 标志   | ✅ 1 个测试 | 通过 |
| 完整工作流   | ✅ 2 个测试 | 通过 |

**总计**: 9 个测试用例，100% 通过率

### 端到端集成测试

| 测试步骤         | 描述                       | 状态 |
| ---------------- | -------------------------- | ---- |
| 1. 环境设置      | 创建隔离测试环境           | ✅   |
| 2. 自动虚拟环境  | 测试 auto-venv 创建和激活  | ✅   |
| 3. 安装跟踪      | 测试 pre/post-install 记录 | ✅   |
| 4. 环境检测      | 验证环境类型识别           | ✅   |
| 5. 策略配置      | 测试 SAGE_VENV_POLICY      | ✅   |
| 6. 清理功能      | 测试卸载脚本               | ✅   |
| 7. Makefile 集成 | 验证 make 目标             | ✅   |
| 8. 文档验证      | 检查文档一致性             | ✅   |

**总计**: 8 个集成步骤，全部通过

## 🔧 测试配置

### 环境变量

测试支持以下环境变量：

- `SAGE_VENV_POLICY`: 虚拟环境策略（`warning`、`error`、`ignore`）
- `CI`: 设置为 `true` 以模拟 CI 环境
- `SAGE_CONDA_INSTALL`: 设置为 `true` 以模拟 Conda 安装模式

### 测试隔离

所有测试都在临时目录中运行，确保：

- ✅ 不会修改实际的 SAGE 安装
- ✅ 测试之间相互独立
- ✅ 自动清理测试环境

## 📝 测试输出示例

### 成功输出

```
╔════════════════════════════════════════════════╗
║                                                ║
║   🧪 环境配置模块单元测试                      ║
║                                                ║
╚════════════════════════════════════════════════╝

测试组: detect_virtual_environment - Conda 环境
✅ PASS: 检测到 Conda 环境
✅ PASS: 环境类型为 conda
✅ PASS: 环境名称正确

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
测试总结
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总测试数: 13
通过: 13
失败: 0
通过率: 100%

✅ 所有测试通过！
```

## 🤖 CI/CD 集成

这些测试已集成到 GitHub Actions 工作流中（`.github/workflows/test-env-cleanup.yml`）：

### CI 工作流包括

1. **单元测试** - 在 Ubuntu 22.04 和 latest 上运行
1. **自动虚拟环境测试** - 跨 Python 3.10, 3.11, 3.12 的矩阵测试
1. **安装跟踪测试** - 验证记录功能
1. **端到端集成测试** - 完整工作流验证
1. **文档示例测试** - 确保文档示例可运行

### 触发条件

工作流在以下情况下运行：

- 推送到 `main` 或 `main-dev` 分支
- 对相关文件的 Pull Request
- 手动触发 (workflow_dispatch)

### 相关文件路径

```
tools/install/environment_config.sh
tools/cleanup/**
.github/workflows/test-env-cleanup.yml
docs/dev-notes/l0-infra/cleanup-automation.md
```

## 🛠️ 添加新测试

### 单元测试结构

```bash
#!/bin/bash
# 测试名称和描述

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAGE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# 导入颜色定义
source "$SAGE_ROOT/tools/install/display_tools/colors.sh"

# 测试计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
test_my_feature() {
    echo -e "${BLUE}测试组: 功能描述${NC}"

    # 执行测试
    # ...

    assert_equals "$actual" "$expected" "测试名称"
}

# 主程序
main() {
    echo "╔════════════════════════════════════════════════╗"
    echo "║         🧪 我的测试套件                        ║"
    echo "╚════════════════════════════════════════════════╝"

    test_my_feature

    print_test_summary
}

main "$@"
```

### 断言函数

测试框架提供以下断言函数：

- `assert_equals VALUE EXPECTED NAME` - 检查值相等
- `assert_contains TEXT PATTERN NAME` - 检查文本包含模式
- `assert_file_exists FILE NAME` - 检查文件存在
- `assert_file_contains FILE PATTERN NAME` - 检查文件包含内容
- `assert_success NAME` - 检查上一个命令成功
- `assert_failure NAME` - 检查上一个命令失败

## 📚 相关文档

- [清理自动化文档](../../../docs/dev-notes/l0-infra/cleanup-automation.md)
- [开发者文档](../../../DEVELOPER.md)
- [贡献指南](../../../CONTRIBUTING.md)

## ❓ 常见问题

### Q: 测试失败了怎么办？

A: 检查测试输出中的失败消息。测试在隔离环境中运行，所以不会影响实际安装。

### Q: 如何在不同的 Python 版本下测试？

A: 修改系统的默认 Python 版本，或在 CI 矩阵中指定版本。

### Q: 测试会修改我的 SAGE 安装吗？

A: 不会。所有测试都在 `/tmp` 下的临时目录中运行，并在完成后自动清理。

### Q: 如何调试失败的测试？

A:

1. 在测试脚本顶部添加 `set -x` 启用调试输出
1. 移除测试结束时的清理步骤以检查测试目录
1. 单独运行失败的测试函数

## 🔍 故障排除

### 权限问题

```bash
chmod +x tools/install/tests/*.sh
```

### 找不到颜色定义

确保 `tools/install/display_tools/colors.sh` 存在。

### 临时目录空间不足

测试使用 `/tmp` 目录。如果空间不足，可以设置：

```bash
export TMPDIR=/path/to/larger/tmp
```

______________________________________________________________________

**维护者**: SAGE 开发团队\
**最后更新**: 2025-11-15\
**版本**: 1.0.0

# SAGE 安装工具测试

本目录包含安装器环境检查、安装跟踪与清理脚本的测试说明。测试目标是保证 SAGE 在当前仓库约束下继续遵守以下规则：

- 不创建新的 `venv` 或 `.venv`
- 兼容当前非 venv Python 环境工作流
- 安装跟踪与清理脚本行为可验证

## 测试文件

- `test_environment_config.sh`: 环境检测、虚拟环境拒绝策略、CI 特殊路径
- `test_cleanup_tools.sh`: 安装跟踪、show/info 命令、清理脚本行为
- `test_e2e_integration.sh`: 端到端安装、跟踪、清理流程
- `run_all_tests.sh`: 顺序执行全部测试套件并输出汇总

## 运行方式

从仓库根目录运行：

```bash
# 单个测试套件
bash tools/install/tests/test_environment_config.sh
bash tools/install/tests/test_cleanup_tools.sh
bash tools/install/tests/test_e2e_integration.sh

# 一次性运行全部测试
bash tools/install/tests/run_all_tests.sh
```

## 测试覆盖主题

- Conda、系统 Python 与受限环境检测
- Python venv 拒绝策略
- `SAGE_VENV_POLICY` 行为分支
- 安装前后跟踪文件记录
- 清理脚本的非交互行为
- 文档和脚本路径的一致性检查

## 相关环境变量

- `SAGE_VENV_POLICY`: 控制系统环境下的虚拟环境策略（如 `warning`、`error`、`ignore`）
- `CI`: 模拟 CI 运行路径
- `SAGE_CONDA_INSTALL`: 模拟 Conda 安装模式

## CI 集成

这些测试当前由 GitHub Actions 工作流
[`.github/workflows/util-cleanup.yml`](../../../.github/workflows/util-cleanup.yml) 执行。

工作流覆盖：

- 单元测试脚本执行
- 安装跟踪与清理脚本验证
- 端到端安装与清理流程
- 关键环境检测逻辑存在性检查

主分支策略遵循仓库 main-only 规则，因此文档和工作流说明都应以 `main` 为准，不应再引用 `main-dev`。

## 相关文件

- `tools/install/installers/environment_config.sh`
- `tools/install/cleanup/track_install.sh`
- `tools/install/cleanup/uninstall_sage.sh`
- `.github/workflows/util-cleanup.yml`
- `quickstart.sh`

## 故障排查

```bash
# 脚本执行权限
chmod +x tools/install/tests/*.sh

# 查看完整测试汇总
bash tools/install/tests/run_all_tests.sh
```

若测试失败，请附上失败命令与相关输出片段，并优先检查被测脚本路径是否仍与本 README 中列出的文件一致。

# 🔧 SAGE 故障排除指南 (Troubleshooting Guide)

> 遇到安装、环境或示例运行问题时，请从这里开始。本指南整合了 `README.md`、安装脚本和环境医生的关键信息，帮助你快速定位并解决常见故障。

## ⚡️ 快速索引（Quick Index）

| 症状 / 报错                                                         | 优先动作                                                                                             |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| 安装脚本 `quickstart.sh` 报错                                       | [运行诊断工具](#-%E5%BF%AB%E9%80%9F%E8%AF%8A%E6%96%AD%E5%B7%A5%E5%85%B7kit)                          |
| "Python version"、"dependency conflict"、`numpy`/`torch` 版本不兼容 | [常见安装问题](#-%E5%B8%B8%E8%A7%81%E5%AE%89%E8%A3%85%E9%97%AE%E9%A2%98-common-install-issues)       |
| vLLM / CUDA / C++ 扩展编译失败                                      | [安装问题 · GPU/C++](#-%E5%B8%B8%E8%A7%81%E5%AE%89%E8%A3%85%E9%97%AE%E9%A2%98-common-install-issues) |
| `ModuleNotFoundError`、示例运行失败                                 | [示例 & CLI 运行](#-%E7%A4%BA%E4%BE%8B--cli-%E8%BF%90%E8%A1%8C%E9%97%AE%E9%A2%98)                    |
| Submodule 处于 detached HEAD、代码不同步                            | [Submodule & 仓库状态](#-submodule--%E4%BB%93%E5%BA%93%E7%8A%B6%E6%80%81)                            |
| API Key / `.env` 配置缺失                                           | [环境变量 & API Key](#-%E7%8E%AF%E5%A2%83%E5%8F%98%E9%87%8F--api-key-%E7%BC%BA%E5%A4%B1)             |
| 仍无法解决                                                          | [收集日志并求助](#-%E6%8F%90%E4%BA%A4-issue-%E5%89%8D%E7%9A%84%E6%B8%85%E5%8D%95)                    |

______________________________________________________________________

## 🩺 快速诊断工具（Kit）

更详细的安装验证流程请参考 [docs/INSTALLATION_VALIDATION.md](./INSTALLATION_VALIDATION.md)。

1. **项目健康检查**

   ```bash
   sage doctor
   ```

   - 检查安装包、依赖版本、API Key、CLI 状态。
   - 该命令在 `README.md` 和 Quick Start 中推荐，适用于本地验证。

1. **完整安装验证测试（推荐）** 🆕

   ```bash
   bash tools/install/tests/verify_installation.sh
   ```

   - 全面测试 SAGE 核心组件、依赖、CLI 工具。
   - 检查版本一致性、配置文件、可选组件。
   - 运行快速示例验证功能。
   - 提供详细的测试报告和下一步建议。

1. **环境医生 / 自动修复**

   ```bash
   ./quickstart.sh --doctor          # 仅诊断
   ./quickstart.sh --doctor --fix    # 诊断 + 自动修复
   ./quickstart.sh --doctor --log    # 输出日志位置
   ```

   - 对 Python、pip/conda、CUDA、**磁盘空间**、**网络连接**等进行全面检测。
   - 诊断日志写入 `./.sage/logs/environment_doctor.log`。
   - 同步 `tools/install/fixes/environment_doctor.sh` 手动执行也可获得同样结果。

1. **安装脚本（来自 README）**

   ```bash
   ./quickstart.sh --dev --yes       # 推荐的开发者安装
   ./quickstart.sh --core --yes      # 轻量核心安装
   ./quickstart.sh --standard --sync-submodules --vllm --yes
   ```

   - 失败时配合 `--doctor --fix` 重新运行，或换用全新的虚拟环境。

______________________________________________________________________

## 🧩 常见安装问题 (Common Install Issues)

### 0. 安装前检查 🆕

在运行 `./quickstart.sh` 时，安装脚本会自动进行以下检查：

- **磁盘空间检查**：

  - 最小需求：10GB
  - 推荐：20GB+（包含 vLLM、submodules）
  - 不足 5GB 时会提示确认是否继续

- **网络连接检查**：

  - 自动测试 PyPI、清华镜像、阿里云镜像的可访问性
  - 网络异常时提示使用镜像源或检查代理设置

- **系统环境检查**：

  - Python 版本（推荐 3.10-3.12）
  - 操作系统和运行环境（Docker、WSL、Native）
  - CPU 架构（x86_64 推荐，ARM 会警告）
  - GPU/CUDA 配置（可选）

**手动触发检查**：

```bash
./quickstart.sh --doctor
```

### 1. Python 版本不兼容

- **症状**：`Python 3.13 not supported`、`Failed building wheel for faiss-cpu`。
- **建议版本**：3.10–3.12（`README`、安装指南一致推荐）。
- **解决**：
  ```bash
  conda create -n sage python=3.11 -y
  conda activate sage
  ./quickstart.sh --dev --yes
  ```

### 2. pip / conda 依赖冲突、`numpy` / `torch` 不匹配

- **症状**：`numpy install conflict`、`PyTorch与CUDA版本不匹配`、`pip/conda conflict`。
- **快速修复**：
  ```bash
  ./quickstart.sh --doctor --fix
  ```
- **手动方案**：
  ```bash
  pip uninstall numpy torch -y
  pip install numpy==2.3.3
  pip install torch --index-url https://download.pytorch.org/whl/cu124
  ```
  或统一交给 conda 管理（参考 `tools/install/fixes/friendly_error_handler.sh` 提示）。

### 3. C++ / CUDA 扩展无法编译（例如 `sageFlow`, vLLM）

- **症状**：`libstdc++.so` 中缺少 `GLIBCXX_x_y`、`CUDA not found`。
- **处理**：
  1. 在 Conda 环境中运行 `packages/sage-middleware/.../build.sh` 会自动调用 `check_libstdcxx`。
  1. 确认 `nvcc`、`CUDA_HOME` 设置正确；必要时设置 `CUDACXX=/usr/local/cuda/bin/nvcc`。
  1. 使用 `./quickstart.sh --standard --vllm --yes` 自动拉取所需 submodule 并重试。

### 4. 网络 / 超时

- 使用镜像源或多次重试：
  ```bash
  pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements.txt
  ```
- 安装脚本会自动捕获 `network timeout` 并提示镜像命令（见 `friendly_error_handler.sh`）。

______________________________________________________________________

## 🧱 Submodule & 仓库状态

- **症状**：`fatal: not a git repository`、submodule 在 detached HEAD、不同步。
- **命令（来自 `DEVELOPER.md`）**：
  ```bash
  ./tools/maintenance/sage-maintenance.sh submodule init
  ./tools/maintenance/sage-maintenance.sh submodule status
  ./tools/maintenance/sage-maintenance.sh submodule switch
  ./tools/maintenance/sage-maintenance.sh submodule update
  ```
- **常见修复**：
  - 切换主仓分支后立刻执行 `submodule switch`。
  - 避免直接运行 `git submodule update --init`（会导致 detached HEAD）。

______________________________________________________________________

## 🔐 环境变量 & API Key 缺失

- **症状**：`RuntimeError: method requires API Key`、`OPENAI_API_KEY not set`。
- **配置步骤（来自 README & docs-public）**：
  ```bash
  cp .env.template .env
  nano .env   # 或编辑器打开
  ```
  填写至少以下键：`OPENAI_API_KEY`, `HF_TOKEN`, `JINA_API_KEY`, `ALIBABA_API_KEY`。
- **验证**：
  ```bash
  sage config env show
  ```
- **在代码中**：`EmbeddingFactory` / CLI 会检测 `*_API_KEY`，缺失时直接报错；确保在运行 shell 中已加载 `.env`。

______________________________________________________________________

## ▶️ 示例 & CLI 运行问题

1. **始终在仓库根目录执行**：

   ```bash
   cd /path/to/SAGE
   python examples/tutorials/hello_world.py
   ```

1. **Missing dependency**：确保开发安装已完成：

   ```bash
   pip install -e packages/sage-libs -e packages/sage-kernel
   ```

1. **批量测试失败**：

   ```bash
   bash tools/tests/run_examples_tests.sh | tee /tmp/examples.log
   grep -i FAIL /tmp/examples.log || true
   ```

1. **CLI / Pipeline Builder 报错**：

   - 检查 `--api-key` 或 `SAGE_PIPELINE_BUILDER_API_KEY` 是否存在。
   - 使用 `sage doctor` 查看 `sage-cli` 依赖（`rich`, `typer`, `pydantic` 等）。

______________________________________________________________________

## 🆘 提交 Issue 前的清单

1. **附带命令输出**：
   - `sage doctor`
   - `./quickstart.sh --doctor --log`
   - `pip list | grep isage`
1. **日志**：
   - `.sage/logs/environment_doctor.log`
   - 安装脚本日志（若使用 `--log`）。
1. **系统信息**：
   - OS、Python 版本、虚拟环境类型（conda / venv）。
1. **运行命令**：提供原始命令和完整错误堆栈。
1. **必要时附带**：`git status`、`./tools/maintenance/sage-maintenance.sh submodule status` 输出。

携带以上信息提 Issue 可大幅缩短排查时间。社区渠道参考 `README.md`、`docs/COMMUNITY.md`（WeChat、QQ、Slack、GitHub Discussions）。

______________________________________________________________________

> ✅ 建议：完成上述排查后再次执行 `sage doctor`，确认一切恢复正常。欢迎根据实践经验向本文件提交改进 PR！

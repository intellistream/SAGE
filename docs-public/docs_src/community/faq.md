# 常见问题 (FAQ)

## 安装与环境配置

### Q: 安装过程卡住怎么办？

**A**: 正常安装时间为 10-25 分钟。如果长时间无响应：

1. 检查网络连接
1. 使用 `--resume` 选项从断点恢复
1. 中国大陆用户：设置 `SAGE_FORCE_CHINA_MIRROR=true` 使用镜像源

```bash
# 断点恢复
./quickstart.sh --dev --yes --resume

# 强制使用中国镜像
SAGE_FORCE_CHINA_MIRROR=true ./quickstart.sh --dev --yes
```

**相关脚本**：`quickstart.sh`

______________________________________________________________________

### Q: C++ 扩展编译失败怎么办？

**A**: 确保安装了必要的系统依赖：

```bash
# Ubuntu/Debian
sudo apt install build-essential cmake pkg-config libopenblas-dev liblapack-dev

# macOS
brew install cmake openblas lapack
```

如果仍然失败，可以跳过 C++ 扩展（仅用于开发调试）：

```bash
SAGE_SKIP_CPP_EXTENSIONS=true ./quickstart.sh --dev --yes
```

**相关文件**：

- `packages/sage-middleware/src/sage/middleware/components/` - C++ 扩展源码
- `.sage/build/` - 构建产物目录

______________________________________________________________________

### Q: 子模块 (Submodule) 出现 detached HEAD 怎么办？

**A**: 使用专用脚本修复：

```bash
# 修复 detached HEAD
./tools/maintenance/sage-maintenance.sh submodule switch

# 查看子模块状态
./tools/maintenance/sage-maintenance.sh submodule status
```

**⚠️ 重要**：不要使用 `git submodule update --init`，这会破坏子模块配置。

**相关脚本**：

- `manage.sh` - 子模块管理入口
- `tools/maintenance/sage-maintenance.sh` - 子模块维护脚本

______________________________________________________________________

## WSL2 开发环境

### Q: WSL2 下端口 8001 无法连接怎么办？

**A**: 这是 WSL2 网络栈的已知问题。端口可能显示为监听状态，但连接被拒绝。

**解决方案**：使用备用端口 8901

```python
from sage.common.config.ports import SagePorts

# 方式 1: 自动检测
port = SagePorts.get_recommended_llm_port()  # WSL2 下自动返回 8901

# 方式 2: 直接使用备用端口
port = SagePorts.BENCHMARK_LLM  # 8901
```

CLI 启动时也推荐使用 8901 端口：

```bash
sage llm serve --port 8901
```

**相关配置**：`packages/sage-common/src/sage/common/config/ports.py`

______________________________________________________________________

### Q: WSL2 下如何检测是否在 WSL 环境？

**A**: 使用内置函数：

```python
from sage.common.config.ports import is_wsl

if is_wsl():
    print("Running in WSL2")
```

______________________________________________________________________

## CI/CD 与测试

### Q: 本地测试通过但 CI 失败怎么办？

**A**: 按以下步骤排查：

1. **确保从仓库根目录运行测试**：

   ```bash
   cd /path/to/SAGE
   sage-dev project test --coverage
   ```

1. **检查环境一致性**：

   ```bash
   # 复制 CI 安装方式
   ./tools/install/ci_install_wrapper.sh --dev --yes
   ```

1. **检查 API Key**：CI 使用 GitHub Secrets 注入 `OPENAI_API_KEY`、`HF_TOKEN`

1. **查看 CI 日志**：关注子模块初始化、C++ 构建、API 调用相关错误

**CI 工作流文件**：`.github/workflows/build-test.yml`

______________________________________________________________________

### Q: CI 中如何正确安装 SAGE？

**A**: 根据场景选择安装方式：

| 场景                           | 安装命令                                                                                    | 说明           |
| ------------------------------ | ------------------------------------------------------------------------------------------- | -------------- |
| GitHub Actions (ubuntu-latest) | `./tools/install/ci_install_wrapper.sh --dev --yes`                                         | 标准 CI        |
| GitHub Actions + Conda         | `unset CI GITHUB_ACTIONS && ./quickstart.sh --dev --yes --pip`                              | 需取消 CI 变量 |
| Self-hosted (中国)             | `unset CI GITHUB_ACTIONS && SAGE_FORCE_CHINA_MIRROR=true ./quickstart.sh --dev --yes --pip` | 强制中国镜像   |

**为什么需要 `unset CI GITHUB_ACTIONS`**：`quickstart.sh` 检测到 CI 环境时会添加 `--user` 参数安装到 `~/.local`，如果使用
conda 环境需要取消这些变量。

______________________________________________________________________

### Q: 如何运行特定包的测试？

**A**:

```bash
# 运行所有测试（带覆盖率）
sage-dev project test --coverage

# 快速测试
sage-dev project test --quick

# 特定包测试
pytest packages/sage-kernel/tests/unit/ -v

# 示例测试
sage-dev examples test
```

**测试配置**：`tools/pytest.ini`

______________________________________________________________________

## LLM 服务

### Q: 如何启动 LLM 服务？

**A**: 使用 `sage llm serve` 命令：

```bash
# 启动 LLM + Embedding 服务（默认）
sage llm serve

# 仅启动 LLM
sage llm serve --no-embedding

# 指定模型和端口
sage llm serve -m "Qwen/Qwen2.5-7B-Instruct" --port 8901
```

服务启动后可通过 Python 或 curl 访问：

```python
from sage.llm import UnifiedInferenceClient

client = UnifiedInferenceClient.create_auto()
response = client.chat([{"role": "user", "content": "Hello"}])
```

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen2.5-7B-Instruct", "messages": [{"role": "user", "content": "Hello"}]}'
```

______________________________________________________________________

### Q: 模型下载很慢怎么办？

**A**: SAGE 会自动检测网络区域。中国大陆用户会自动使用 hf-mirror.com 镜像。

手动确保镜像配置：

```python
from sage.common.config import ensure_hf_mirror_configured

ensure_hf_mirror_configured()  # 自动检测并配置
```

或设置环境变量：

```bash
export HF_ENDPOINT=https://hf-mirror.com
sage llm model download --model "Qwen/Qwen2.5-0.5B-Instruct"
```

**相关配置**：`packages/sage-common/src/sage/common/config/network.py`

______________________________________________________________________

## 代码质量与格式化

### Q: pre-commit 检查失败怎么办？

**A**: 运行自动修复：

```bash
# 自动修复
sage-dev quality

# 仅检查（不修复）
sage-dev quality --check-only

# 或直接使用 pre-commit
pre-commit run --all-files --config tools/pre-commit-config.yaml
```

**工具配置**：

- Ruff: `tools/ruff.toml`
- Pre-commit: `tools/pre-commit-config.yaml`

______________________________________________________________________

### Q: Ruff 版本不一致怎么办？

**A**: 检查并修复版本：

```bash
# 检查版本一致性
./tools/install/check_tool_versions.sh

# 自动修复版本不匹配
./tools/install/check_tool_versions.sh --fix
```

Ruff 版本在两处定义，必须保持一致：

- `tools/pre-commit-config.yaml` (rev)
- `packages/sage-tools/pyproject.toml` (==x.y.z)

______________________________________________________________________

## 端口配置

### Q: 各服务默认端口是什么？

**A**: 所有端口通过 `SagePorts` 统一管理：

| 常量                | 端口 | 服务                               |
| ------------------- | ---- | ---------------------------------- |
| `GATEWAY_DEFAULT`   | 8000 | sage-llm-gateway (OpenAI 兼容 API) |
| `LLM_DEFAULT`       | 8001 | vLLM 推理服务                      |
| `LLM_WSL_FALLBACK`  | 8901 | WSL2 备用 LLM 端口                 |
| `STUDIO_BACKEND`    | 8080 | sage-studio 后端                   |
| `STUDIO_FRONTEND`   | 5173 | sage-studio 前端 (Vite)            |
| `EMBEDDING_DEFAULT` | 8090 | Embedding 服务                     |
| `BENCHMARK_LLM`     | 8901 | Benchmark 专用                     |

```python
from sage.common.config.ports import SagePorts

# 使用常量，禁止硬编码
port = SagePorts.LLM_DEFAULT  # 8001
```

**配置文件**：`packages/sage-common/src/sage/common/config/ports.py`

______________________________________________________________________

## 其他问题

### Q: 如何清理构建产物？

**A**:

```bash
# 使用 Makefile
make clean

# 或手动删除
rm -rf .sage/build/ build/ dist/ *.egg-info/
```

______________________________________________________________________

### Q: Import 报错怎么办？

**A**: 确保满足以下条件：

1. 使用 `--dev` 模式安装：`./quickstart.sh --dev --yes`
1. 从仓库根目录运行代码
1. 激活正确的 Python 环境

```bash
# 检查安装
pip list | grep isage

# 应该看到类似输出
# isage-common    x.y.z
# isage-kernel    x.y.z
# ...
```

______________________________________________________________________

### Q: 在哪里找到更多开发文档？

**A**:

- **架构文档**：`docs/dev-notes/` (按层级组织 l1-l6)
- **公开文档**：`docs-public/docs_src/`
- **贡献指南**：`CONTRIBUTING.md` (中文), `DEVELOPER.md` (英文)
- **包架构**：`docs-public/docs_src/dev-notes/package-architecture.md`

______________________________________________________________________

## 获取帮助

如果以上内容未能解决您的问题：

1. 搜索 [GitHub Issues](https://github.com/intellistream/SAGE/issues)
1. 加入 [社群讨论](community.md)
1. 提交新 Issue（附上错误日志和环境信息）

**收集环境信息**：

```bash
# Python 版本
python --version

# SAGE 版本
pip show isage-common

# 系统信息
uname -a

# GPU 信息（如有）
nvidia-smi
```

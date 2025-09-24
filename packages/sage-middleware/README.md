# SAGE Middleware（中间件）

用于构建带有 AI 能力的流式数据应用的中间件层，集成了多家大模型提供商、异步任务、鉴权以及高性能的数据处理组件。

## 主要功能

- 🤖 AI 接入：OpenAI / Anthropic / Cohere / Ollama / 智谱 等
- 🔎 检索与向量：RAG、BM25、FAISS 等
- � 任务调度：Celery 异步任务
- 🔐 安全鉴权：JWT、密码学工具
- ⚙️ 核心组件：
  - `sage_db`：数据库/向量存储相关组件（含 C/C++ 扩展）
  - `sage_flow`：高性能向量流处理（可能包含扩展或独立子模块）

## 安装

```bash
pip install isage-middleware

# 可选：VLLM 支持（需要 CUDA）
pip install isage-middleware[vllm]

# 可选：与完整 SAGE 框架集成
pip install isage-middleware[sage]
```

## 快速开始

```python
from sage.middleware.api.client import APIClient
from sage.middleware.auth.jwt import JWTManager

client = APIClient()
jwt_manager = JWTManager()

resp = client.chat_completion(
    provider="openai",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(resp)
```

## 配置示例

```yaml
# config.yaml
middleware:
  auth:
    secret_key: "your-secret-key"
    algorithm: "HS256"
  providers:
    openai:
      api_key: "sk-..."
      base_url: "https://api.openai.com/v1"
```

## 开发与本地安装

```bash
git clone https://github.com/intellistream/SAGE.git
cd SAGE/packages/sage-middleware
pip install -e .
```

> 提示：如果使用了子模块（例如 `sage_flow`），请先在仓库根目录执行：
>
> ```bash
> git submodule update --init --recursive
> ```

## 新增中间件组件的规范（重要）

当你添加新的中间件组件（例如 `sage_foo`）时，请务必在 `setup.py` 中接入其构建逻辑，这样在安装 `isage-middleware` 时会自动构建/准备该组件。

建议遵循以下约定：

1) 目录结构（放在源码目录下，保证被打包发现）

- `src/sage/middleware/components/sage_foo/`
  - `__init__.py`（Python 包）
  - 可选：`build.sh`（如含 C/C++/额外构建步骤）

2) 构建脚本（可选）

- 如组件需要编译或额外准备工作，请在组件目录提供标准的 `build.sh`，支持无交互执行：
  - `bash build.sh --install-deps`

3) 在 `setup.py` 里接入构建

- 在自定义的 `build_ext` 流程中：
  - 新增 `build_sage_foo()` 方法（参照已有的 `build_sage_db()` / `build_sage_flow()`）。
  - 在 `run()` 中调用 `self.build_sage_foo()`，并保证失败不阻断安装（打印清晰日志即可）。

4) 环境变量开关（可选）

- 如需跳过所有扩展构建（调试 Python 逻辑时常用）：
  - 设置 `SAGE_SKIP_C_EXTENSIONS=1`

5) CI 提示

- CI 会递归检出子模块并按 `setup.py` 的逻辑尝试构建。
- 如果组件以子模块形式提供源码，请确保子模块在 CI 和本地都能被初始化（`git submodule update --init --recursive`）。

## 贡献

欢迎提交 PR！请先阅读仓库根目录的 [CONTRIBUTING.md](../../CONTRIBUTING.md)。

## 许可协议

MIT 许可协议，详见仓库根目录的 [LICENSE](../../LICENSE)。
# SAGE Middleware（中间件）

## 📋 Overview

用于构建带有 AI 能力的流式数据应用的中间件层，集成了多家大模型提供商、异步任务、鉴权以及高性能的数据处理组件。

## ✨ Key Features

- 🤖 AI 接入：OpenAI / Anthropic / Cohere / Ollama / 智谱 等
- 🔎 检索与向量：RAG、BM25、FAISS 等
- � 任务调度：Celery 异步任务
- 🔐 安全鉴权：JWT、密码学工具
- ⚙️ 核心组件：
  - `sage_db`：数据库/向量存储相关组件（含 C/C++ 扩展）
  - `sage_flow`：高性能向量流处理（可能包含扩展或独立子模块）

## 🚀 Installation

```bash
pip install isage-middleware

# 可选：VLLM 支持（需要 CUDA）
pip install isage-middleware[vllm]

# 可选：与完整 SAGE 框架集成
pip install isage-middleware[sage]
```

## 📖 Quick Start

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
    secret_key: "your-secret-key"  # pragma: allowlist secret
    algorithm: "HS256"
  providers:
    openai:
      api_key: "sk-..."  # pragma: allowlist secret
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

### 1. 目录结构

- `src/sage/middleware/components/sage_foo/`
  - `__init__.py`（Python 包）
  - （如包含 C/C++ 部分）`cmake/`、`build.sh`、`CMakeLists.txt`
  - 其他源码/资源文件

### 2. C++ 扩展与依赖要求

如果组件包含 C/C++ 扩展，**必须**遵守以下依赖约束，以与现有 `sage_db`、`sage_flow` 保持一致：

1. **共享依赖入口：**

   - 在 `CMakeLists.txt` 中优先加载 `SAGE_COMMON_DEPS_FILE` 指向的共享脚本：
     ```cmake
     set(_sage_foo_shared_deps FALSE)
     if(DEFINED SAGE_COMMON_DEPS_FILE AND EXISTS "${SAGE_COMMON_DEPS_FILE}")
         include("${SAGE_COMMON_DEPS_FILE}")
         set(_sage_foo_shared_deps TRUE)
     endif()
     ```
   - 共享脚本会提供 `pybind11::module`、统一的可见性编译选项、以及全部 gperftools 配置变量。

1. **本地回退脚本：**

   - 请在组件目录的 `cmake/` 下提供 `pybind11_dependency.cmake` 和（如需要）`gperftools.cmake`，用于在独立构建或共享脚本缺失时下载依赖。
   - 在 `CMakeLists.txt` 中检测 `_sage_foo_shared_deps`，若为 `FALSE` 再加载本地脚本：
     ```cmake
     if(NOT _sage_foo_shared_deps)
         include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/pybind11_dependency.cmake)
     endif()
     ```

1. **gperftools 约定：**

   - 新增扩展应暴露 `ENABLE_GPERFTOOLS` 选项，并默认遵循 `SAGE_ENABLE_GPERFTOOLS` 环境变量。
   - 只有在确认找到 `SAGE_GPERFTOOLS_LIBS`（或本地回退脚本成功解析）时才链接 gperftools；否则务必禁用该选项并给出清晰日志。

1. **环境变量约定：**

   - 共享脚本会设置 `SAGE_COMMON_COMPILE_OPTIONS`、`SAGE_COMMON_COMPILE_DEFINITIONS` 等变量，请在目标上引用，避免重复配置。
   - 新扩展若需要自定义变量，务必提供合理的默认值，并允许通过环境变量覆写。

1. **打包要求：**

   - `pyproject.toml` 中需包含 `"sage.middleware.components.sage_foo" = ["cmake/*.cmake"]` 等条目，保证 CMake
     脚本在发布包内。
   - 如扩展存在 Python 侧绑定（`python/` 目录），确保 `pyproject.toml` 中的 `package-data` 同步更新。

### 3. 构建脚本

- 如果组件需要编译或额外准备工作，请提供标准的 `build.sh`，支持无交互执行：
  - `bash build.sh --install-deps`
- `build.sh` 应读取 `SAGE_COMMON_DEPS_FILE`、`SAGE_ENABLE_GPERFTOOLS` 等环境变量，并在调用 `cmake` 时透传（参考
  `sage_db`、`sage_flow`）。

### 4. 在 `setup.py` 中接入

- 在自定义的 `build_ext` 流程中：
  - 新增 `build_sage_foo()` 方法（参照现有 `build_sage_db()` / `build_sage_flow()`）。
  - 使用统一的 `_shared_env()` 帮助函数为子进程注入共享依赖环境。
  - 在 `run()` 中调用 `self.build_sage_foo()`，并保证失败不阻断安装（打印清晰日志即可）。

### 5. 环境变量开关（可选）

- 通过设置 `SAGE_SKIP_C_EXTENSIONS=1` 可以跳过所有扩展构建（调试纯 Python 逻辑时常用）。

### 6. CI 与子模块提示

- CI 会递归检出子模块并按 `setup.py` 的逻辑尝试构建。
- 如果组件以子模块形式提供源码，请确保子模块在 CI 和本地都能被初始化：
  - `git submodule update --init --recursive`

## 贡献

欢迎提交 PR！请先阅读仓库根目录的 [CONTRIBUTING.md](../../CONTRIBUTING.md)。

## 📄 License

MIT License - see [LICENSE](../../LICENSE) for details.

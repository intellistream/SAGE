# SAGE Middleware（中间件）

## 📋 Overview

用于构建带有 AI 能力的流式数据应用的中间件层，集成了多家大模型提供商、异步任务、鉴权以及高性能的数据处理组件。

## ✨ Key Features

- 🤖 **LLM 推理**：
  - **sageLLM** ✅ 推荐：统一 LLM 推理引擎，支持 CUDA/Ascend/Mock 后端
  - vLLM ⚠️ 已弃用：将在 v0.4.0 移除，请迁移至 sageLLM
- 🔎 检索与向量：RAG、BM25、FAISS 等
- 📋 任务调度：Celery 异步任务
- 🔐 安全鉴权：JWT、密码学工具
- ⚙️ 核心组件：
  - `sage_db`：数据库/向量存储相关组件（含 C/C++ 扩展）
  - `sage_flow`：高性能向量流处理（可能包含扩展或独立子模块）

## 🚀 Installation

```bash
pip install isage-middleware

# 可选：VLLM 支持（需要 CUDA）
pip install isage-common[vllm]

# 可选：与完整 SAGE 框架集成
pip install isage-middleware[sage]
```

## 📖 Quick Start

### LLM 推理（推荐：sageLLM）

```python
from sage.middleware.operators.llm import SageLLMGenerator

# 自动选择最佳后端
generator = SageLLMGenerator(
    model_path="Qwen/Qwen2.5-7B-Instruct",
    backend_type="auto",  # auto/cuda/ascend/mock
    temperature=0.7,
    max_tokens=2048,
)

result = generator.execute("你好，世界！")
print(result)
```

### API 客户端

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

> 📖 **迁移指南**：如果您正在使用 `VLLMGenerator`，请参阅
> [vLLM to sageLLM Migration Guide](../../docs-public/docs_src/dev-notes/migration/VLLM_TO_SAGELLM_MIGRATION.md)

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

> 说明：中间件组件（sage_db/sage_flow/sage_tsdb 等）现已随源码直接提供或通过 pip 依赖分发，无需初始化任何子模块。

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

> **注意**: 以下代码示例中的 `SAGE_COMMON_DEPS_FILE` 等变量是 CMake 环境变量，非占位符。

1. **共享依赖入口：**

   - 在 `CMakeLists.txt` 中优先加载共享依赖脚本（通过环境变量）：
     ```cmake
     set(_sage_foo_shared_deps FALSE)
     # Check if shared deps file is defined
     if(DEFINED SAGE_COMMON_DEPS_FILE AND EXISTS "$ENV(SAGE_COMMON_DEPS_FILE)")
         include("$ENV(SAGE_COMMON_DEPS_FILE)")
         set(_sage_foo_shared_deps TRUE)
     endif()
     ```
   - 共享脚本会提供 `pybind11::module`、统一的可见性编译选项、以及全部 gperftools 配置变量。

1. **本地回退脚本：**

   - 请在组件目录的 `cmake/` 下提供 `pybind11_dependency.cmake` 和（如需要）`gperftools.cmake`，用于在独立构建或共享脚本缺失时下载依赖。
   - 在 `CMakeLists.txt` 中检测 `_sage_foo_shared_deps`，若为 `FALSE` 再加载本地脚本：
     ```cmake
     if(NOT _sage_foo_shared_deps)
         include(cmake/pybind11_dependency.cmake)
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
- `build.sh` 应读取相关环境变量（如依赖文件路径、gperftools 开关等），并在调用 `cmake` 时透传（参考 `sage_db`、`sage_flow`）。

### 4. 在 `setup.py` 中接入

- 在自定义的 `build_ext` 流程中：
  - 新增 `build_sage_foo()` 方法（参照现有 `build_sage_db()` / `build_sage_flow()`）。
  - 使用统一的 `_shared_env()` 帮助函数为子进程注入共享依赖环境。
  - 在 `run()` 中调用 `self.build_sage_foo()`，并保证失败不阻断安装（打印清晰日志即可）。

### 5. 环境变量开关（可选）

- 通过设置 `SAGE_SKIP_C_EXTENSIONS=1` 可以跳过所有扩展构建（调试纯 Python 逻辑时常用）。

### 6. CI 与子模块提示

- CI 会递归检出子模块并按 `setup.py` 的逻辑尝试构建。
- 中间件组件不再通过 Git submodule 分发；请不要在 CI 或本地执行子模块初始化命令。

## 贡献

欢迎提交 PR！请先阅读仓库根目录的 [CONTRIBUTING.md](../../CONTRIBUTING.md)。

## 📄 License

MIT License - see [LICENSE](../../LICENSE) for details.

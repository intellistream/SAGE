# API Key 安全配置指南

## 问题背景

之前的配置方式将 API key 直接硬编码在配置文件中，这会导致严重的安全隐患：
- API key 可能被意外提交到 git 仓库
- 配置文件可能被他人看到，导致 key 泄露
- 难以在不同环境间切换不同的 key

## 解决方案

### 1. 环境变量配置（推荐）

将敏感信息存储在 `.env` 文件中，**永远不要提交 `.env` 文件到 git**。

#### `.env` 文件配置

```bash
# OpenAI API Key (for GPT models)
# qwen-turbo API key via DashScope compatible endpoint
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL_NAME=qwen-turbo-2025-02-11
```

#### 配置文件设置

在 YAML 配置文件中，将 `api_key` 设置为空字符串：

```yaml
generator:
  vllm:
    api_key: ""  # 留空，将从环境变量 OPENAI_API_KEY 读取
    method: "openai"
    model_name: "qwen-turbo-2025-02-11"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    seed: 42
```

### 2. 代码实现

#### Generator 自动读取环境变量

`packages/sage-libs/src/sage/libs/rag/generator.py` 中的实现：

```python
# API key 优先级: 配置文件 > OPENAI_API_KEY > ALIBABA_API_KEY
api_key = (
    self.config["api_key"]
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("ALIBABA_API_KEY")
)
self.model = OpenAIClient(
    model_name=self.config["model_name"],
    base_url=self.config["base_url"],
    api_key=api_key,
    seed=self.config.get("seed", 42),
)
```

这个优先级顺序保证了：
1. 如果配置文件中有 API key，使用配置文件的（用于特殊情况）
2. 否则尝试从 `OPENAI_API_KEY` 环境变量读取
3. 最后回退到 `ALIBABA_API_KEY` 环境变量

#### QA Pipeline Service 配置检查

`examples/service/pipeline_as_service/qa_pipeline_as_service.py` 中的修改：

```python
if method == "openai":
    if not selected_config:
        return _mock_fallback("no OpenAI-compatible configuration block found")
    # 允许 api_key 为空字符串，Generator 会从环境变量读取
    api_key = selected_config.get("api_key")
    if api_key is None:  # 只在字段完全缺失时报错
        return _mock_fallback("api_key field missing for OpenAI-compatible generator")
    if not selected_config.get("base_url"):
        return _mock_fallback("missing base_url for OpenAI-compatible generator")
    return OpenAIGenerator, selected_config, ""
```

### 3. 使用方法

#### 启动 QA Pipeline Service

```bash
cd /home/shuhao/SAGE

# 方式1: 使用环境变量指定 generator
SAGE_QA_GENERATOR=openai SAGE_QA_GENERATOR_PROFILE=vllm \
    python examples/service/pipeline_as_service/qa_pipeline_as_service.py

# 方式2: 如果 .env 文件配置正确，也可以直接运行
python examples/service/pipeline_as_service/qa_pipeline_as_service.py
```

#### 交互式测试

服务启动后，可以直接在终端输入问题：

```
You> 什么是人工智能？
```

服务会调用配置的 LLM (qwen-turbo-2025-02-11) 生成回答。

退出命令：输入 `bye bye` 或按 `Ctrl+C`

### 4. 安全最佳实践

1. **永远不要提交 `.env` 文件到 git**
   ```bash
   # 确保 .gitignore 包含
   .env
   .env.local
   .env.*.local
   ```

2. **使用 `.env.template` 作为模板**
   ```bash
   # 创建模板文件（不含真实 key）
   cp .env .env.template
   # 在 .env.template 中将 key 替换为占位符
   ```

3. **团队成员各自管理自己的 `.env` 文件**
   - 不要通过邮件、聊天工具分享 API key
   - 使用团队密钥管理工具（如 1Password, Vault）

4. **定期轮换 API key**
   - 定期更新 API key
   - 撤销不再使用的 key

5. **限制 API key 权限**
   - 只授予必要的权限
   - 设置使用限额

## 环境变量优先级总结

```
配置文件 > OPENAI_API_KEY > ALIBABA_API_KEY
```

这个设计允许：
- 开发环境使用 `.env` 文件
- 生产环境使用系统环境变量
- 特殊情况可以在配置文件中临时覆盖（但不推荐）

## 相关文件

- `.env` - 环境变量配置文件（不提交到 git）
- `examples/config/config_source.yaml` - QA pipeline 配置文件
- `packages/sage-libs/src/sage/libs/rag/generator.py` - Generator 实现
- `examples/service/pipeline_as_service/qa_pipeline_as_service.py` - QA service 实现

## 相关文档

- [快速开始指南](../get_start/quickstart.md)
- [配置指南](../kernel/config/config.md)

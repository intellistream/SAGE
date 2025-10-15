# 环境变量迁移指南

## ⚠️ 重大变更 - 不向后兼容

**`SAGE_CHAT_*` 环境变量已被完全移除，不再支持。**

所有使用这些变量的代码必须更新为使用新的 `TEMP_GENERATOR_*` 变量或配置文件。

## 变更摘要

为了更清晰地区分生产环境和演示/测试环境的配置，我们将环境变量进行了重命名，并**完全移除**了旧的变量支持。

## 变更内容

### 旧的环境变量（已废弃）

```bash
SAGE_CHAT_BACKEND=openai
SAGE_CHAT_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
SAGE_CHAT_MODEL=qwen-turbo-2025-02-11
SAGE_CHAT_API_KEY=sk-xxx
SAGE_CHAT_SEED=42
```

### 新的环境变量（推荐使用）

```bash
# 用于示例和演示的临时配置
TEMP_GENERATOR_BACKEND=openai
TEMP_GENERATOR_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
TEMP_GENERATOR_MODEL=qwen-turbo-2025-02-11
TEMP_GENERATOR_API_KEY=your_temporary_api_key_here
TEMP_GENERATOR_SEED=42
```

## 迁移原因

1. **更清晰的命名**：`TEMP_GENERATOR_*` 明确表示这些是临时的、仅用于演示和测试的配置
2. **避免混淆**：`SAGE_CHAT_*` 容易让人误以为是聊天功能的生产配置
3. **配置文件优先**：鼓励使用 YAML 配置文件而不是环境变量来配置生成器

## 迁移步骤

### 对于开发者

1. 更新你的 `.env` 文件：
   ```bash
   # 旧的配置（删除）
   # SAGE_CHAT_BACKEND=openai
   # SAGE_CHAT_API_KEY=sk-xxx
   
   # 新的配置（添加）
   TEMP_GENERATOR_BACKEND=openai
   TEMP_GENERATOR_API_KEY=your_key_here
   ```

2. 如果你的代码中使用了这些环境变量，请改为：
   - **推荐**：使用 YAML 配置文件中的 `generator` 配置
   - **临时方案**：使用新的 `TEMP_GENERATOR_*` 环境变量

### 对于示例代码

**不推荐**：直接读取环境变量
```python
# ❌ 不推荐
import os
generator_config = {
    "api_key": os.getenv("SAGE_CHAT_API_KEY"),  # 旧的
    "model_name": os.getenv("SAGE_CHAT_MODEL"),
}
```

**推荐**：使用配置文件
```python
# ✅ 推荐
import yaml
with open("config.yaml") as f:
    config = yaml.safe_load(f)

generator_config = config.get("generator", {}).get("vllm", {})
generator = OpenAIGenerator(generator_config)
```

## 受影响的文件

以下文件已更新，不再支持 `SAGE_CHAT_*` 变量：

- ✅ `examples/tutorials/templates_to_llm_demo.py` - 已更新
- ✅ `examples/tutorials/test_new_templates.py` - 已更新
- ✅ `examples/tutorials/test_real_llm.py` - 已更新
- ✅ `packages/sage-tools/src/sage/tools/cli/commands/pipeline.py` - 已更新
- ✅ `packages/sage-tools/src/sage/tools/cli/commands/chat.py` - 已更新
- ✅ `docs-public/docs_src/tools/cli_reference.md` - 已更新

## 兼容性

**不提供向后兼容性**。如果你的代码或配置中仍在使用 `SAGE_CHAT_*` 变量，程序将无法找到配置并报错。

### 错误示例

```bash
# ❌ 这将不再工作
export SAGE_CHAT_API_KEY="sk-xxx"
sage chat

# 错误信息: 未提供 API Key。请设置 TEMP_GENERATOR_API_KEY
```

### 正确做法

```bash
# ✅ 使用新的变量名
export TEMP_GENERATOR_API_KEY="sk-xxx"
sage chat

# ✅ 或者使用配置文件（推荐）
sage chat --config config.yaml
```

## 最佳实践

1. **生产环境**：始终使用 YAML 配置文件，不要依赖环境变量
2. **开发/测试**：可以使用 `TEMP_GENERATOR_*` 环境变量快速测试
3. **示例代码**：应该从配置文件读取，展示最佳实践
4. **API Key 安全**：永远不要提交真实的 API Key 到 Git

## 相关 PR

- 修复 CI/CD 超时和移除硬编码环境变量
- 添加资源清理最佳实践

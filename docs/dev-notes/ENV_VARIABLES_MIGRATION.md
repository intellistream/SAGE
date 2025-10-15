# 环境变量迁移指南

## 变更摘要

为了更清晰地区分生产环境和演示/测试环境的配置，我们将环境变量进行了重命名。

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

以下文件可能需要更新（仅供参考，大部分文档性质）：

- `examples/tutorials/templates_to_llm_demo.py` - 文档说明
- `examples/tutorials/test_new_templates.py` - 测试脚本
- `examples/tutorials/test_real_llm.py` - 测试脚本
- `packages/sage-tools/src/sage/tools/cli/commands/pipeline.py` - CLI 工具（兼容性保留）
- `packages/sage-tools/src/sage/tools/cli/commands/chat.py` - CLI 工具（兼容性保留）
- 各种文档文件

## 兼容性

CLI 工具（如 `sage chat`、`sage pipeline`）会继续支持 `SAGE_CHAT_*` 环境变量以保持向后兼容性，但建议逐步迁移到：
1. 使用配置文件（YAML）
2. 使用新的 `TEMP_GENERATOR_*` 环境变量（仅用于临时测试）

## 最佳实践

1. **生产环境**：始终使用 YAML 配置文件，不要依赖环境变量
2. **开发/测试**：可以使用 `TEMP_GENERATOR_*` 环境变量快速测试
3. **示例代码**：应该从配置文件读取，展示最佳实践
4. **API Key 安全**：永远不要提交真实的 API Key 到 Git

## 相关 PR

- 修复 CI/CD 超时和移除硬编码环境变量
- 添加资源清理最佳实践

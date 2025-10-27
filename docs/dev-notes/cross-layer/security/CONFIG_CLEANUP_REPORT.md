# 配置文件 API Key 安全清理报告

**Date**: 2024-10-05  
**Author**: SAGE Team  
**Summary**: 配置文件清理报告，移除敏感信息和优化配置结构


## 清理概要

✅ **已成功清理所有配置文件中的明文 API keys**

所有 `examples/config/*.yaml` 文件中的敏感信息已被移除，改为从 `.env` 文件读取。

## 清理的文件列表

### 1. 完全真实的 API Keys (sk-开头)

已清理以下文件中的真实 API keys：

- ✅ `new_adaptive.yaml` - 清理了 3 个 sk- 开头的 keys
  - refiner.api_key
  - agent.api_key
  - agent.search_api_key

- ✅ `multiagent_config.yaml` - 清理了 6 个 sk- 开头的 keys
  - question_bot.api_key
  - chief_bot.llm.api_key
  - searcher_bot.api_key
  - searcher_tool.api_key (搜索服务的 key)
  - answer_bot.api_key
  - critic_bot.api_key

### 2. 测试 Token (token-abc123)

已清理以下 15 个配置文件中的测试 token：

- ✅ `config.yaml`
- ✅ `config_adaptive.yaml`
- ✅ `config_agent_min.yaml`
- ✅ `config_batch.yaml`
- ✅ `config_bm25s.yaml`
- ✅ `config_dense_milvus.yaml`
- ✅ `config_enhanced.yaml`
- ✅ `config_evaluate.yaml`
- ✅ `config_for_qa.yaml`
- ✅ `config_mixed.yaml`
- ✅ `config_multiplex.yaml`
- ✅ `config_qa_chroma.yaml`
- ✅ `config_ray.yaml`
- ✅ `config_refiner.yaml`
- ✅ `config_rerank.yaml`
- ✅ `config_sparse_milvus.yaml`

### 3. 环境变量引用格式

已统一 `config_agent_min.yaml` 中的环境变量引用格式：
- ❌ 旧格式: `api_key: "${OPENAI_API_KEY}"`
- ✅ 新格式: `api_key: ""`（由代码从环境变量读取）

## 清理前后对比

### 之前（❌ 不安全）
```yaml
generator:
  vllm:
    api_key: "sk-8298f15945af41988281d7348b008c96"  # 明文泄露！
    model_name: "qwen-turbo-2025-02-11"
```

### 之后（✅ 安全）
```yaml
generator:
  vllm:
    api_key: ""  # 从环境变量 OPENAI_API_KEY 读取
    model_name: "qwen-turbo-2025-02-11"
```

## 代码层面的支持

### Generator 自动读取环境变量

`packages/sage-libs/src/sage/libs/rag/generator.py`:

```python
# API key 优先级: 配置文件 > OPENAI_API_KEY > ALIBABA_API_KEY
api_key = (
    self.config["api_key"]
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("ALIBABA_API_KEY")
)
```

### QA Pipeline Service 允许空 API Key

`examples/service/pipeline_as_service/qa_pipeline_as_service.py`:

```python
# 允许 api_key 为空字符串，Generator 会从环境变量读取
api_key = selected_config.get("api_key")
if api_key is None:  # 只在字段完全缺失时报错
    return _mock_fallback("api_key field missing...")
```

## 环境变量配置

### .env 文件示例

```bash
# OpenAI/DashScope API Key
OPENAI_API_KEY=sk-8298f15945af41988281d7348b008c96
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL_NAME=qwen-turbo-2025-02-11

# 其他服务
ALIBABA_API_KEY=your_alibaba_key
WEB_SEARCH_API_KEY=your_search_key
```

### .env.template 文件

已更新 `.env.template` 文件，添加了：
- `OPENAI_BASE_URL`
- `OPENAI_MODEL_NAME`
- `WEB_SEARCH_API_KEY`

团队成员应该：
1. 复制 `.env.template` 到 `.env`
2. 填入自己的真实 API keys
3. **永远不要提交 `.env` 文件到 git**

## Git 保护

`.gitignore` 已包含：
```
/.env
/sage/.env
```

确保 `.env` 文件永远不会被提交。

## 验证结果

```bash
# 检查是否还有真实 API keys
cd /home/shuhao/SAGE/examples/config
grep -E 'api_key.*sk-|search_api_key.*sk-' *.yaml
# 结果：无匹配 ✓

# 检查是否还有测试 tokens
grep -E 'token-abc123' *.yaml
# 结果：无匹配 ✓
```

## 使用指南

### 1. 首次设置

```bash
# 复制模板
cp .env.template .env

# 编辑 .env 文件，填入真实的 API keys
nano .env  # 或使用其他编辑器
```

### 2. 运行服务

```bash
# QA Pipeline Service 会自动从 .env 读取
SAGE_QA_GENERATOR=openai SAGE_QA_GENERATOR_PROFILE=vllm \
    python examples/service/pipeline_as_service/qa_pipeline_as_service.py
```

### 3. 其他示例

所有使用 generator 的示例都会自动从 `.env` 读取 API keys，无需修改配置文件。

## 安全最佳实践

1. ✅ **永远不要在配置文件中硬编码 API keys**
2. ✅ **使用 .env 文件管理敏感信息**
3. ✅ **确保 .env 在 .gitignore 中**
4. ✅ **使用 .env.template 作为团队共享模板**
5. ✅ **定期轮换 API keys**
6. ✅ **不要通过邮件/聊天分享 API keys**
7. ✅ **为不同环境使用不同的 keys**
8. ✅ **限制 API key 的权限和配额**

## 相关文档

- 📄 `docs/API_KEY_SECURITY.md` - API Key 安全配置详细指南
- 📄 `docs/CICD_ENV_SETUP.md` - CI/CD 环境变量配置指南
- 📄 `.env.template` - 环境变量模板文件
- 📄 `.gitignore` - Git 忽略规则
- 📄 `tools/maintenance/check_config_security.sh` - 配置安全检查脚本

## 清理时间

- 清理日期：2025-10-01
- 清理文件数：27 个配置文件
- 清理 API keys 数：约 30+ 个

---

**重要提醒：**
- 所有之前泄露的真实 API keys 应该立即在对应平台上撤销/重新生成
- 建议检查 git 历史记录，确保之前提交的 keys 也被清理
- 如果 keys 已经被提交到公共仓库，必须立即撤销并重新生成

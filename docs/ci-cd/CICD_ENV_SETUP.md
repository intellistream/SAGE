# GitHub CI/CD 环境变量配置指南

## 概述

SAGE 项目的 CI/CD 流程需要从 GitHub Secrets 读取 API keys，并在运行时创建 `.env` 文件。这样做的好处是：

1. ✅ 与本地开发环境保持一致
2. ✅ 集中管理敏感信息
3. ✅ 避免在代码中硬编码密钥
4. ✅ 支持不同环境使用不同的配置

## 需要配置的 GitHub Secrets

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中配置以下 secrets：

### 必需的 Secrets

| Secret 名称 | 用途 | 示例值 |
|------------|------|--------|
| `OPENAI_API_KEY` | OpenAI/DashScope API 密钥 | `sk-xxx...` |
| `HF_TOKEN` | Hugging Face Token（用于模型下载） | `hf_xxx...` |

### 可选的 Secrets

| Secret 名称 | 用途 | 默认值 |
|------------|------|--------|
| `ALIBABA_API_KEY` | 阿里云 DashScope API 密钥 | 空 |
| `SILICONCLOUD_API_KEY` | SiliconCloud API 密钥 | 空 |
| `JINA_API_KEY` | Jina AI API 密钥 | 空 |
| `VLLM_API_KEY` | 本地 vLLM 服务的 token | `token-abc123` |
| `WEB_SEARCH_API_KEY` | Web 搜索服务 API 密钥 | 空 |

## CI/CD 工作流程

### 1. CI Pipeline (main 分支)

文件：`.github/workflows/ci.yml`

```yaml
- name: Create .env File from Secrets
  run: |
    echo "🔐 从 GitHub Secrets 创建 .env 文件..."
    cat > .env << EOF
    OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }}
    OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
    OPENAI_MODEL_NAME=qwen-turbo-2025-02-11
    
    HF_TOKEN=${{ secrets.HF_TOKEN }}
    HF_ENDPOINT=https://hf-mirror.com
    
    VLLM_API_KEY=${{ secrets.VLLM_API_KEY }}
    VLLM_BASE_URL=http://localhost:8000/v1
    VLLM_MODEL_NAME=meta-llama/Llama-2-13b-chat-hf
    
    SAGE_TEST_MODE=true
    SAGE_EXAMPLES_MODE=test
    EOF
```

### 2. Dev CI Pipeline (main-dev 分支)

文件：`.github/workflows/dev-ci.yml`

使用相同的 secrets 配置，但可能有不同的环境设置。

## 环境变量说明

### LLM 服务配置

```bash
# OpenAI/DashScope 配置
OPENAI_API_KEY=sk-xxx              # API 密钥
OPENAI_BASE_URL=https://...        # API 端点
OPENAI_MODEL_NAME=qwen-turbo-...   # 模型名称

# Alibaba DashScope
ALIBABA_API_KEY=sk-xxx

# vLLM 本地服务
VLLM_API_KEY=token-abc123          # 本地服务的简单 token
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL_NAME=meta-llama/...
```

### Hugging Face 配置

```bash
HF_TOKEN=hf_xxx                    # Hugging Face token
HF_ENDPOINT=https://hf-mirror.com  # 镜像站点（中国用户）
```

### CI/CD 专用配置

```bash
SAGE_DEBUG=false                   # 是否启用调试日志
SAGE_SKIP_CPP_EXTENSIONS=false     # 是否跳过 C++ 扩展编译
SAGE_LOG_LEVEL=INFO                # 日志级别
SAGE_TEST_MODE=true                # 测试模式
SAGE_EXAMPLES_MODE=test            # 示例运行模式
```

## 配置 GitHub Secrets 的步骤

### 方式一：通过 Web 界面

1. 访问仓库页面
2. 点击 `Settings` → `Secrets and variables` → `Actions`
3. 点击 `New repository secret`
4. 输入 Secret 名称和值
5. 点击 `Add secret`

### 方式二：通过 GitHub CLI

```bash
# 设置单个 secret
gh secret set OPENAI_API_KEY -b "sk-xxx..."

# 从文件读取并设置多个 secrets
gh secret set OPENAI_API_KEY < openai_key.txt
gh secret set HF_TOKEN < hf_token.txt

# 批量设置（从 .env 文件）
while IFS='=' read -r key value; do
  if [[ ! $key =~ ^#.* ]] && [[ -n $key ]]; then
    gh secret set "$key" -b "$value"
  fi
done < .env
```

## 安全最佳实践

### ✅ 应该做的

1. **定期轮换密钥**
   ```bash
   # 每 90 天轮换一次关键 API keys
   gh secret set OPENAI_API_KEY -b "new-key"
   ```

2. **使用最小权限原则**
   - 只授予 CI/CD 所需的最小权限
   - 为 CI/CD 创建专用的 API keys

3. **监控使用情况**
   - 定期检查 API key 的使用情况
   - 设置使用配额和警报

4. **分离环境**
   - 生产环境和测试环境使用不同的 keys
   - 考虑使用 GitHub Environments 功能

### ❌ 不应该做的

1. ❌ **不要在日志中输出完整的密钥**
   ```bash
   # ❌ 错误
   echo "API_KEY=$OPENAI_API_KEY"
   
   # ✅ 正确
   echo "API_KEY=***"
   cat .env | sed 's/=.*/=***/'
   ```

2. ❌ **不要将 .env 文件提交到 git**
   - 确保 `.env` 在 `.gitignore` 中
   - 使用 `.env.template` 作为模板

3. ❌ **不要在 Pull Request 中暴露 secrets**
   - Fork 的仓库无法访问 secrets（这是好的）
   - 外部贡献者的 PR 不应该需要真实的 API keys

## 本地开发 vs CI/CD 对比

| 特性 | 本地开发 | CI/CD |
|-----|---------|-------|
| 配置来源 | `.env` 文件 | GitHub Secrets |
| 创建方式 | 手动复制 `.env.template` | CI 自动生成 |
| 更新频率 | 按需更新 | 每次运行时重新创建 |
| 版本控制 | 不提交（.gitignore） | 不提交（临时生成） |
| 安全性 | 本地保护 | GitHub 加密存储 |

## 故障排查

### 问题：CI 中找不到 API key

**症状：** 测试失败，提示 "API key not found" 或类似错误

**解决方案：**
1. 检查 GitHub Secrets 是否已配置
   ```bash
   gh secret list
   ```

2. 验证 secret 名称是否正确（区分大小写）

3. 确认 `.env` 文件是否被正确创建
   ```yaml
   - name: Debug .env file
     run: |
       ls -la .env
       cat .env | sed 's/=.*/=***/'
   ```

### 问题：Secret 值包含特殊字符

**症状：** YAML 解析错误或密钥格式不正确

**解决方案：**
1. 使用引号包裹包含特殊字符的值
2. 对于多行值，使用 base64 编码
   ```bash
   echo "secret-value" | base64 | gh secret set MY_SECRET
   ```

### 问题：Fork 仓库的 CI 失败

**症状：** 外部贡献者的 PR CI 失败，提示缺少 secrets

**解决方案：**
- 这是预期行为（安全特性）
- 贡献者应该在自己的 fork 中配置 secrets
- 或者使用 mock 模式运行测试：
  ```bash
  SAGE_TEST_MODE=true SAGE_EXAMPLES_MODE=test pytest
  ```

## 相关文档

- 📄 [API Key 安全配置指南](./API_KEY_SECURITY.md)
- 📄 [配置清理报告](./CONFIG_CLEANUP_REPORT.md)
- 📄 [.env.template](../.env.template) - 环境变量模板
- 🔗 [GitHub Secrets 文档](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

## 更新日志

- **2025-10-01**: 初始版本，统一本地和 CI/CD 的环境变量管理方式
  - 添加 `.env` 文件自动生成步骤
  - 配置所有必需的 GitHub Secrets
  - 添加 vLLM 本地服务支持

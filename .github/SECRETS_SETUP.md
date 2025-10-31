# GitHub Secrets 快速设置指南

## 🚀 快速开始

为了让 CI/CD 正常工作，你需要在 GitHub 仓库中配置以下 Secrets。

### 最小必需配置

```bash
# 使用 GitHub CLI（推荐）
gh secret set OPENAI_API_KEY -b "your-openai-or-dashscope-key"
gh secret set HF_TOKEN -b "your-huggingface-token"
```

### 完整配置（可选）

```bash
# LLM 服务
gh secret set OPENAI_API_KEY -b "sk-xxx..."
gh secret set ALIBABA_API_KEY -b "sk-xxx..."
gh secret set SILICONCLOUD_API_KEY -b "your-key"

# 其他服务
gh secret set JINA_API_KEY -b "your-key"
gh secret set WEB_SEARCH_API_KEY -b "your-key"

# vLLM 本地服务（如果不需要认证可以留空）
gh secret set VLLM_API_KEY -b "token-abc123"

# Hugging Face
gh secret set HF_TOKEN -b "hf_xxx..."
```

## 📋 通过 Web 界面设置

1. 访问：`https://github.com/YOUR_ORG/SAGE/settings/secrets/actions`
1. 点击 `New repository secret`
1. 添加以下 secrets：

| Name                 | Value                                 | Required |
| -------------------- | ------------------------------------- | -------- |
| `OPENAI_API_KEY`     | 你的 OpenAI/DashScope API key         | ✅ 是    |
| `HF_TOKEN`           | 你的 Hugging Face token               | ✅ 是    |
| `ALIBABA_API_KEY`    | 阿里云 API key                        | ⭕ 可选  |
| `VLLM_API_KEY`       | vLLM 服务 token（默认: token-abc123） | ⭕ 可选  |
| `WEB_SEARCH_API_KEY` | Web 搜索服务 key                      | ⭕ 可选  |

## 🔍 验证配置

配置完成后，触发一次 CI 运行来验证：

```bash
# 触发 workflow
git commit --allow-empty -m "test: trigger CI to verify secrets"
git push
```

查看 CI 日志，应该能看到：

```
✅ .env 文件创建完成
📋 验证 .env 文件内容（隐藏敏感信息）:
OPENAI_API_KEY=***
HF_TOKEN=***
...
```

## 📚 详细文档

查看完整文档：[docs/CICD_ENV_SETUP.md](../docs/CICD_ENV_SETUP.md)

## ⚠️ 注意事项

1. **不要**在 Pull Request 评论或 Issue 中粘贴真实的 API keys
1. Fork 的仓库需要自己配置 Secrets（外部贡献者无法访问主仓库的 Secrets）
1. 定期轮换 API keys（建议每 90 天一次）
1. 使用专用的 CI/CD API keys，与生产环境分离

## 🆘 故障排查

### 问题：CI 失败，提示 "API key not found"

**解决方案：**

1. 检查 Secret 名称是否正确（区分大小写）
1. 验证 Secret 是否已设置：
   ```bash
   gh secret list
   ```
1. 确认分支有权限访问 Secrets（默认所有分支都可以）

### 问题：我是外部贡献者，CI 失败怎么办？

**解决方案：** 外部贡献者的 PR 默认无法访问仓库的 Secrets（这是安全特性）。你可以：

1. 在自己的 fork 中配置 Secrets
1. 或者使用 mock 模式测试（大多数测试支持）：
   ```bash
   SAGE_TEST_MODE=true pytest
   ```

## 📞 需要帮助？

- 查看 [CI/CD 环境配置指南](../docs/CICD_ENV_SETUP.md)
- 查看 [API Key 安全指南](../docs/API_KEY_SECURITY.md)
- 提交 Issue：[GitHub Issues](https://github.com/intellistream/SAGE/issues)

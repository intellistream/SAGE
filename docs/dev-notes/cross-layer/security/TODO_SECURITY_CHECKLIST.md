# 安全更新 - 待办事项清单

**Date**: 2024-10-01  
**Author**: SAGE Team  
**Summary**: 安全检查清单，包含代码审计、依赖扫描等待办事项

---


## ✅ 已完成的工作

### 代码和配置
- [x] 清理所有配置文件中的明文 API keys（27 个文件）
- [x] 更新 `.env` 文件，添加 vLLM 和 Web Search 配置
- [x] 更新 `.env.template` 模板文件
- [x] 修改 `generator.py` 支持环境变量读取
- [x] 修改 `qa_pipeline_as_service.py` 允许空 API key
- [x] 更新 `.github/workflows/ci.yml` 添加 .env 创建步骤
- [x] 更新 `.github/workflows/dev-ci.yml` 添加 .env 创建步骤

### 文档和工具
- [x] 创建 `docs/API_KEY_SECURITY.md` - 安全配置指南
- [x] 创建 `docs/CONFIG_CLEANUP_REPORT.md` - 清理报告
- [x] 创建 `docs/CICD_ENV_SETUP.md` - CI/CD 配置指南
- [x] 整合 GitHub Secrets 配置到 `CONTRIBUTING.md` - Secrets 快速设置
- [x] 创建 `docs/SECURITY_UPDATE_SUMMARY.md` - 完整更新总结
- [x] 创建 `tools/maintenance/check_config_security.sh` - 安全检查脚本

### 测试验证
- [x] 运行安全检查脚本 - 通过 ✅
- [x] 测试 QA Pipeline Service - 成功使用 OpenAIGenerator ✅

## ⚠️ 需要立即执行的操作

### 1. 撤销已泄露的 API Keys

**已泄露的 keys（需要在对应平台撤销）：**

#### OpenAI/DashScope Keys
- [ ] `sk-8298f15945af41988281d7348b008c96` - 在 DashScope 控制台撤销
- [ ] `sk-700a53a2a85344e09a82afa96ae072a8` - 在 DashScope 控制台撤销

#### Web Search API Keys
- [ ] `sk-b21a67cf99d14ead9d1c5bf8c2eb90ef` - 在搜索服务控制台撤销
- [ ] `sk-455d6a2c79464dd2959197477a908e53` - 在搜索服务控制台撤销

**操作步骤：**
1. 登录对应的服务控制台
2. 找到 API Keys 管理页面
3. 撤销/删除上述 keys
4. 生成新的 API keys
5. 更新本地 `.env` 文件和 GitHub Secrets

### 2. 配置 GitHub Secrets

**访问：** https://github.com/intellistream/SAGE/settings/secrets/actions

#### 必需的 Secrets
- [ ] `OPENAI_API_KEY` - 新生成的 OpenAI/DashScope key
- [ ] `HF_TOKEN` - Hugging Face token

#### 可选的 Secrets
- [ ] `ALIBABA_API_KEY` - 阿里云 DashScope key（如果不同于 OPENAI_API_KEY）
- [ ] `VLLM_API_KEY` - 本地 vLLM 服务 token（默认 `token-abc123`）
- [ ] `WEB_SEARCH_API_KEY` - 新生成的 Web 搜索 key
- [ ] `SILICONCLOUD_API_KEY` - SiliconCloud key（如果使用）
- [ ] `JINA_API_KEY` - Jina AI key（如果使用）

**快速命令：**
```bash
# 使用 GitHub CLI 设置
gh secret set OPENAI_API_KEY -b "your-new-key"
gh secret set HF_TOKEN -b "your-hf-token"
gh secret set VLLM_API_KEY -b "token-abc123"
gh secret set WEB_SEARCH_API_KEY -b "your-new-search-key"
```

### 3. 更新本地 .env 文件

- [ ] 打开 `.env` 文件
- [ ] 替换为新生成的 API keys
- [ ] 保存文件
- [ ] 验证不要提交 `.env` 到 git

```bash
# 验证 .env 不会被提交
git status .env
# 应该显示：（使用 .gitignore 排除）
```

### 4. 验证 CI/CD

- [ ] 提交一个测试 commit 触发 CI
  ```bash
  git commit --allow-empty -m "test: verify CI with new secrets"
  git push origin main-dev
  ```
- [ ] 查看 CI 日志，确认 .env 文件被正确创建
- [ ] 确认测试通过

### 5. 检查 Git 历史（可选但推荐）

- [ ] 检查历史提交中是否有敏感信息
  ```bash
  git log -p -- examples/config/*.yaml | grep -E "sk-" | head -20
  git log -p -- .env | head -20
  ```

- [ ] 如果发现敏感信息，决定是否需要清理历史
  - **警告：** 清理历史需要强制推送，会影响所有协作者

## 📋 后续维护任务

### 定期任务
- [ ] 每 90 天轮换一次 API keys
- [ ] 每月检查 API 使用情况和账单
- [ ] 每季度运行安全检查脚本

### 团队协作
- [ ] 通知团队成员更新本地 .env 文件
- [ ] 分享 `CONTRIBUTING.md` 中的 GitHub Secrets 配置章节给新成员
- [ ] 在团队文档中添加安全最佳实践链接

### 监控和审计
- [ ] 设置 API 使用配额和警报
- [ ] 定期审计 GitHub Secrets 的访问日志
- [ ] 检查是否有未授权的 API 调用

## 🔗 相关资源

### 文档链接
- [API Key 安全配置指南](./docs/API_KEY_SECURITY.md)
- [CI/CD 环境配置指南](./docs/CICD_ENV_SETUP.md)
- [配置清理报告](./docs/CONFIG_CLEANUP_REPORT.md)
- [完整更新总结](./docs/SECURITY_UPDATE_SUMMARY.md)
- [GitHub Secrets 快速设置](../../../CONTRIBUTING.md#github-secrets-配置维护者贡献者)

### 工具和脚本
- 安全检查脚本：`./tools/maintenance/check_config_security.sh`

### 外部资源
- [GitHub Secrets 文档](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [DashScope 控制台](https://dashscope.console.aliyun.com/)
- [Hugging Face Tokens](https://huggingface.co/settings/tokens)

## 📞 需要帮助？

如果遇到问题：
1. 查看相关文档（见上方链接）
2. 运行安全检查脚本获取诊断信息
3. 提交 Issue：https://github.com/intellistream/SAGE/issues

## ✅ 完成确认

当所有上述任务完成后，请在此确认：

- [ ] 所有已泄露的 API keys 已撤销
- [ ] 新的 API keys 已生成
- [ ] GitHub Secrets 已配置
- [ ] 本地 .env 已更新
- [ ] CI/CD 验证通过
- [ ] 团队成员已通知
- [ ] 文档已分享

**完成日期：** _______________  
**完成人：** _______________

---

**创建时间：** 2025-10-01  
**最后更新：** 2025-10-01

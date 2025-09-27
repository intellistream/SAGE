# CICD Embedding模型集成指南

## 问题描述

在CICD环境中，neuromem测试可能因为无法下载HuggingFace模型而失败。之前的版本会静默回退到MockEmbedder，但这导致测试结果不可靠。

## 解决方案

### 1. 预缓存模型（推荐）

在CICD pipeline中添加模型缓存步骤：

```yaml
# GitHub Actions 示例
- name: Cache embedding models
  run: |
    python tools/cache_embedding_models.py --cache
```

### 2. 使用本地模型缓存

如果CICD环境支持缓存，可以缓存transformers模型：

```yaml
- name: Cache transformers models
  uses: actions/cache@v3
  with:
    path: ~/.cache/huggingface/transformers
    key: ${{ runner.os }}-transformers-${{ hashFiles('**/requirements.txt') }}
```

### 3. 环境变量配置

设置HuggingFace镜像源以提高下载成功率：

```yaml
env:
  HF_ENDPOINT: https://hf-mirror.com
```

### 4. 失败时的处理

如果模型加载失败，测试会明确失败并提供清晰的错误信息，不再静默回退到MockEmbedder。

## 本地测试

验证模型缓存：
```bash
python tools/cache_embedding_models.py --check
```

缓存模型：
```bash
python tools/cache_embedding_models.py --cache
```

## 修改内容

1. **移除了MockEmbedder静默回退机制**
2. **测试失败时提供明确的错误信息**
3. **提供了模型缓存脚本**
4. **恢复了测试代码的简洁性**

这确保了测试结果的一致性和可靠性。
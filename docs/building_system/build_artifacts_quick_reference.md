# SAGE 构建产物管理快速参考

## 🧹 基本清理命令

```bash
# 预览清理（安全，推荐）
sage-dev clean --dry-run

# 清理Python缓存和临时文件
sage-dev clean --categories pycache,temp

# 完全清理所有构建产物  
sage-dev clean --categories all

# 强制清理（不询问确认）
sage-dev clean --categories all --force

# 只清理超过7天的文件
sage-dev clean --older-than-days 7
```

## 📊 可清理的类别

| 类别 | 说明 | 大小预估 |
|------|------|----------|
| `pycache` | Python字节码缓存 | 通常2-5MB |
| `egg_info` | pip安装信息 | 通常100-500KB |
| `dist` | 分发包目录 | 通常1-10MB |
| `build` | 构建中间产物 | 可能很大 |
| `coverage` | 覆盖率报告 | 通常1-5MB |
| `pytest` | 测试缓存 | 通常100-500KB |
| `temp` | 临时文件 | 变化很大 |

## 🛠️ 工具命令

```bash
# 生成自动化清理脚本
sage-dev clean --create-script

# 更新.gitignore规则
sage-dev clean --update-gitignore

# 详细输出
sage-dev clean --verbose --dry-run
```

## 📅 推荐使用频率

### 每天
```bash
sage-dev clean --categories pycache,temp
```

### 每周  
```bash
sage-dev clean --categories all --older-than-days 7
```

### 发布前
```bash
sage-dev clean --categories all --force
```

## 🔒 安全保证

- 自动保护 `.git/`, `.venv/`, `.idea/` 等关键目录
- 默认需要确认，除非使用 `--force`
- 支持 `--dry-run` 预览功能
- 提供详细的清理报告

## 💡 最佳实践

1. **先预览再执行**: 总是先用 `--dry-run` 查看
2. **选择性清理**: 根据需要选择特定类别
3. **定期维护**: 建立清理习惯
4. **团队协作**: 使用 `--update-gitignore` 保持一致

## 🚀 一键命令

```bash
# 日常清理一键命令
sage-dev clean --categories pycache,temp --force

# 深度清理一键命令  
sage-dev clean --categories all --older-than-days 7

# 发布准备一键命令
sage-dev clean --categories all --force && sage-dev clean --update-gitignore
```

---
🔗 更多详情见: `docs/building_system/build_artifacts_management.md`

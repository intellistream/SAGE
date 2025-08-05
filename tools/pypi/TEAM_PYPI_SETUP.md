# 共享PyPI Token配置指南

## 方法1：直接共享.pypirc文件内容

同事们可以在自己的机器上创建 ~/.pypirc 文件，内容如下：

```ini
[pypi]
username = __token__
password = pypi-AgEIcHlwaS5xcmcCJGYwOTE4NWEzLTY3OTQtNDQ4NS05YmY1LWY2MDRmNGUxMDY4NQACKlszLCI4NDkyOTgyYy0yYjhmLTQ0MTgtYWEwYS00MWJjY2JiNGExMjAiXQAABiDhYL8zrEkG_QVcatvOtzhjRL8DftHbeuFZKbWEu1jODQ
```

## 方法2：使用环境变量

在 ~/.bashrc 或 ~/.zshrc 中添加：

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcCJGYwOTE4NWEzLTY3OTQtNDQ4NS05YmY1LWY2MDRmNGUxMDY4NQACKlszLCI4NDkyOTgyYy0yYjhmLTQ0MTgtYWEwYS00MWJjY2JiNGExMjAiXQAABiDhYL8zrEkG_QVcatvOtzhjRL8DftHbeuFZKbWEu1jODQ
```

## 方法3：项目级配置（推荐）

在项目根目录创建 .pypirc 文件，团队共享（注意不要提交到git）：

```bash
# 在项目根目录
echo ".pypirc" >> .gitignore  # 确保不提交敏感信息
```

## 安全注意事项

⚠️ **重要安全提醒**：

1. **Token权限**: 这个token有完整的上传权限，请谨慎分享
2. **访问控制**: 只分享给需要发布权限的核心团队成员  
3. **Token轮换**: 定期更换token，特别是团队成员变动时
4. **监控使用**: 监控PyPI上的包发布活动

## 推荐的团队协作方案

### 方案A：一人负责发布（推荐小团队）
- 只有一个人拥有PyPI token
- 其他人提交代码，由发布负责人统一上传

### 方案B：多个个人Token（推荐大团队）
- 每个需要发布权限的人创建自己的PyPI账号
- 在PyPI项目中添加多个维护者
- 每人使用自己的token

### 方案C：组织账号（推荐企业）
- 创建组织PyPI账号
- 使用组织级别的token
- 通过组织管理访问权限

## 设置脚本（供同事使用）

创建一个设置脚本供同事使用：

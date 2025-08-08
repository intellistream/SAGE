# Conda 服务条款问题故障排除

## 问题描述

在新机器上首次运行 SAGE 安装脚本时，可能会遇到以下错误：

```
CondaToSNonInteractiveError: Terms of Service have not been accepted for the following channels. 
Please accept or remove them before proceeding:
    • https://repo.anaconda.com/pkgs/main
    • https://repo.anaconda.com/pkgs/r
```

## 原因

这是因为 Conda 要求用户接受特定频道的服务条款才能使用。在新安装或新机器上，这些条款通常没有被接受。

## 解决方案

### 方案 1：使用自动修复脚本（推荐）

运行我们提供的修复脚本：

```bash
./scripts/fix_conda_tos.sh
```

该脚本会：
- 自动检测服务条款问题
- 提供多种解决选项
- 验证修复结果

### 方案 2：手动接受服务条款

```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

### 方案 3：使用 conda-forge 频道（推荐）

```bash
conda config --add channels conda-forge
conda config --set channel_priority strict
```

使用 conda-forge 频道的优势：
- 通常不需要接受额外的服务条款
- 包更新更频繁
- 社区维护，更加开放

## 验证修复

运行以下命令验证问题是否解决：

```bash
conda info
```

如果没有看到服务条款相关的错误信息，说明问题已解决。

## 重新安装

修复后，重新运行安装脚本：

```bash
./quickstart.sh
```

## 预防措施

为避免将来遇到类似问题，建议：

1. **使用 conda-forge 作为默认频道**：
   ```bash
   conda config --add channels conda-forge
   conda config --set channel_priority strict
   ```

2. **在新机器上首次使用 conda 时主动接受服务条款**

3. **定期更新 conda**：
   ```bash
   conda update conda
   ```

## 相关链接

- [Conda 官方文档](https://docs.conda.io/)
- [conda-forge 文档](https://conda-forge.org/)
- [SAGE 快速安装指南](../README.md)

## 其他问题

如果以上方案都不能解决问题，请：

1. 检查网络连接
2. 确保有足够的磁盘空间
3. 查看详细错误日志
4. 在项目 GitHub 上提交 issue

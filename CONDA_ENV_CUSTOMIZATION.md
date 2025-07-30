# SAGE Conda 环境名称自定义功能

## 概述

现在SAGE安装脚本支持用户自定义conda环境名称，而不是固定使用"sage"环境名。

## 使用方法

### 1. 使用install.py脚本

#### 命令行参数方式
```bash
# 使用自定义环境名称进行最小化安装
python install.py --minimal --env-name my-sage-env

# 使用自定义环境名称进行完整安装
python install.py --full --env-name my-sage-env

# 查看帮助信息
python install.py --env-name my-sage-env --help-sage
```

#### 交互式方式
```bash
# 运行安装脚本
python install.py

# 脚本会提示您输入自定义环境名称
# 如果直接按回车，将使用默认名称"sage"
```

### 2. 使用setup.sh脚本

#### 环境变量方式
```bash
# 设置环境变量
export SAGE_ENV_NAME=my-custom-env
./setup.sh
```

#### 交互式方式
```bash
# 直接运行setup.sh，脚本会提示输入自定义环境名称
./setup.sh
```

## 功能特性

### 1. 自动配置保存
- 用户选择的环境名称会自动保存到配置文件中
- 后续运行安装脚本时会自动加载之前的配置

### 2. 激活脚本更新
- `activate_sage.sh` 脚本会根据您选择的环境名称自动生成
- 脚本中的环境名称会正确反映您的选择

### 3. 完全兼容性
- 支持最小化安装(minimal setup)和完整安装(full setup)
- 支持Docker环境中的自定义环境名称
- 所有SAGE功能保持不变

## 示例场景

### 场景1：开发环境
```bash
# 为开发创建一个专门的环境
python install.py --minimal --env-name sage-dev
conda activate sage-dev
```

### 场景2：生产环境
```bash
# 为生产创建一个专门的环境
python install.py --full --env-name sage-prod
# 使用生成的激活脚本
./activate_sage.sh
```

### 场景3：多项目管理
```bash
# 项目A
python install.py --minimal --env-name sage-project-a

# 项目B
python install.py --minimal --env-name sage-project-b
```

## 配置文件位置

用户的环境配置保存在：
```
~/.sage_setup/config.json
```

配置文件包含：
```json
{
  "setup_type": "minimal",
  "conda_env_name": "your-custom-env-name",
  "installation_date": 1643234567.89
}
```

## 注意事项

1. **环境名称规则**：请确保环境名称符合conda的命名规范（字母、数字、下划线、连字符）
2. **CI/CD模式**：在CI环境中，默认使用"sage"环境名，除非通过`--env-name`明确指定
3. **Docker环境**：在Docker完整安装中，自定义环境名称会在容器内生效
4. **向后兼容**：如果没有指定自定义名称，系统仍然使用默认的"sage"环境名

## 卸载

卸载时，系统会自动检测并删除您指定的自定义环境：
```bash
python install.py --uninstall --env-name your-custom-env-name
```

## 故障排除

### 问题：环境激活失败
```bash
# 检查环境是否存在
conda env list | grep your-env-name

# 手动激活
conda activate your-env-name
```

### 问题：激活脚本使用错误的环境名
```bash
# 重新生成激活脚本
python install.py --status --env-name your-env-name
```

这个功能让SAGE的安装更加灵活，特别适合需要管理多个项目或环境的用户。

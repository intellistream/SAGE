# SAGE Scripts Directory

本目录包含SAGE项目的各种自动化脚本和工具。

## 🚀 部署脚本

### `deployment_setup.py`
**主要的部署自动化脚本**

- **功能**: 一键部署SAGE项目，包括Git submodule初始化、依赖安装、文档构建等
- **使用方法**:
  ```bash
  # 快速安装
  python3 scripts/deployment_setup.py install
  
  # 开发环境完整安装
  python3 scripts/deployment_setup.py full --dev
  
  # 检查项目状态
  python3 scripts/deployment_setup.py status
  
  # 初始化Git submodule
  python3 scripts/deployment_setup.py init
  
  # 运行测试
  python3 scripts/deployment_setup.py test
  ```

- **特性**:
  - 🎨 彩色输出和进度指示
  - 🔍 智能状态检查
  - 📦 自动依赖管理（包括sage-tools包）
  - 📚 文档构建集成
  - 🧪 测试运行支持
  - 🔄 Git submodule自动化
  - 🛠️ 完整包检查（sage, sage-kernel, sage-middleware, sage-apps, sage-dev-toolkit, sage-frontend）

## 🛠️ 构建脚本

### `build_with_license.sh`
- **功能**: 带许可证的构建脚本
- **用途**: 企业版本构建

### `cleanup_build_artifacts.sh` 
- **功能**: 清理构建产物
- **使用**: `./scripts/cleanup_build_artifacts.sh`

### `create_dual_repository.sh`
- **功能**: 创建双仓库结构
- **用途**: 管理公共/私有代码分离

## 📋 最佳实践

1. **脚本执行权限**: 确保脚本有执行权限
   ```bash
   chmod +x scripts/*.sh
   ```

2. **推荐使用顺序**:
   ```bash
   # 1. 新用户快速开始
   ./quickstart.sh
   
   # 2. 或者手动步骤
   python3 scripts/deployment_setup.py init
   python3 scripts/deployment_setup.py install --dev
   
   # 3. 检查状态
   python3 scripts/deployment_setup.py status
   ```

3. **开发工作流**:
   ```bash
   # 日常开发
   python3 scripts/deployment_setup.py status  # 检查环境
   
   # 更新依赖
   python3 scripts/deployment_setup.py install --dev
   
   # 清理构建
   ./scripts/cleanup_build_artifacts.sh
   ```

## 🆘 故障排除

- **权限问题**: 确保脚本有执行权限
- **Python路径**: 确保使用正确的Python环境
- **Git权限**: 检查Git submodule访问权限
- **依赖冲突**: 使用虚拟环境隔离依赖

## 📖 相关文档

- [开发者指南](../DEVELOPER_GUIDE.md)
- [安装说明](../README.md)
- [文档构建指南](../docs-public/README.md)

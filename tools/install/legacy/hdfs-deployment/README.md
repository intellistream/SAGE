# HDFS Docker 部署工具

本目录包含 SAGE 项目的 HDFS 分布式文件系统 Docker 部署工具和相关配置。

## 📁 目录结构

```
hdfs-deployment/
├── README.md                    # 本文件
├── start_hdfs.sh               # 主启动脚本(交互式菜单)
├── docker-compose.yml          # Docker Compose 配置(自动生成)
├── config/                     # Hadoop 配置文件
│   ├── core-site.xml          # Hadoop 核心配置
│   └── hdfs-site.xml          # HDFS 配置
├── data/                       # HDFS 数据目录(运行时创建)
│   ├── namenode/              # NameNode 数据
│   └── datanode/              # DataNode 数据
└── docs/                       # 文档
    ├── 启动机制说明.md        # Docker+HDFS 启动机制详解
    ├── 故障排查指南.md        # 常见问题和解决方案
    └── 部署指南.md            # 快速部署指南

```

## 🚀 快速开始

### 一键部署

```bash
# 进入部署目录
cd /home/lpl/SAGE_dev/tools/install/hdfs-deployment

# 启动交互式菜单
bash start_hdfs.sh

# 或直接启动
bash start_hdfs.sh start
```

### 主要功能

1. **🚀 启动 HDFS 集群** - 自动检查环境、创建配置、启动容器
1. **🛑 停止 HDFS 集群** - 优雅停止所有容器
1. **🔄 重启 HDFS 集群** - 完整重启服务
1. **📊 查看集群状态** - 实时查看容器和 HDFS 状态
1. **🧪 测试 HDFS 功能** - 自动化测试读写删除操作
1. **📝 查看日志** - 查看 NameNode/DataNode 日志
1. **🧹 清理所有数据** - 完全清理环境
1. **⚙️ 高级操作** - 格式化、诊断等高级功能

## 📋 系统要求

- **Docker**: 版本 20.10+
- **Docker Compose**: 版本 2.0+
- **磁盘空间**: 至少 1GB 可用空间
- **内存**: 建议至少 2GB
- **操作系统**: Linux (已在 Ubuntu 测试)

## 🔧 配置说明

### 端口映射

- **9000**: HDFS RPC 端口 (客户端连接)
- **9870**: NameNode Web UI
- **9864**: DataNode Web UI

### 访问方式

```bash
# Python 连接
export HDFS_NAMENODE_HOST=localhost
export HDFS_NAMENODE_PORT=9000

# Web UI
http://localhost:9870  # NameNode
http://localhost:9864  # DataNode
```

## 🛠️ 核心特性

### 自动配置管理

脚本会自动检查并创建所有必需的配置文件:

- ✅ 自动生成 `docker-compose.yml`
- ✅ 自动创建 Hadoop 配置文件
- ✅ 自动设置正确的用户权限 (`user: "0:0"`)
- ✅ 自动创建数据目录并设置权限

### 权限问题解决

本部署自动解决了常见的容器权限问题:

- 容器以 root 用户运行 (`user: "0:0"`)
- 避免 DataNode 因权限导致的启动失败
- 数据目录自动设置为 777 权限

### 错误诊断

内置智能错误诊断功能:

- 自动检查 Docker 环境
- 分析容器日志
- 提供详细的错误信息和解决建议
- 带颜色的输出便于快速定位问题

## 📖 文档

详细文档请查看 `docs/` 目录:

- **启动机制说明.md**: 深入理解 Docker + HDFS 的启动流程
- **故障排查指南.md**: 常见问题和解决方案
- **部署指南.md**: 详细的部署步骤和最佳实践

## ⚠️ 重要说明

### 数据持久化

- HDFS 数据存储在 `data/` 目录
- 停止容器不会丢失数据
- 使用 "清理所有数据" 功能会永久删除数据

### 生产环境使用

本部署主要用于**开发和测试环境**。生产环境建议:

- 使用 Kubernetes 部署
- 配置多节点集群
- 启用 HDFS 高可用 (HA)
- 配置适当的资源限制
- 启用安全认证

## 🐛 故障排查

### 容器无法启动

```bash
# 查看详细日志
bash start_hdfs.sh logs

# 检查容器状态
docker ps -a | grep hdfs

# 查看 Docker Compose 配置
cat docker-compose.yml
```

### DataNode 未注册

1. 检查 DataNode 日志: `docker logs hdfs-datanode`
1. 验证网络连接: `docker network inspect hdfs-deployment_hadoop`
1. 确认配置正确: `cat config/core-site.xml`

### 权限错误

脚本已自动处理权限问题。如果仍有问题:

```bash
# 手动设置权限
sudo chmod -R 777 data/

# 确认 docker-compose.yml 中有 user: "0:0"
grep "user:" docker-compose.yml
```

## 📞 支持

遇到问题请:

1. 查看 `docs/故障排查指南.md`
1. 使用脚本的 "高级操作" -> "诊断问题" 功能
1. 查看容器日志定位具体错误

## 🔄 版本历史

- **v1.0** (2025-11-18): 初始版本
  - 交互式菜单界面
  - 自动配置管理
  - 权限问题自动修复
  - 完整的错误诊断功能

## 📝 许可证

本部署工具是 SAGE 项目的一部分,遵循项目的开源许可证。

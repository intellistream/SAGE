# CLI 命令行工具

SAGE Kernel 提供了完整的命令行工具集，支持开发、调试、部署和监控等全生命周期操作。

## 🔧 主要命令

### sage - 主入口命令

```bash
# 查看版本信息
sage --version

# 查看帮助
sage --help

# 显示系统信息
sage info

# 配置管理
sage config list
sage config set parallelism 8
sage config get checkpoint_interval
```

### sage-core - 核心管理命令

```bash
# 启动作业管理器
sage-core jobmanager start

# 启动工作节点
sage-core worker start --slots 4

# 启动集群头节点
sage-core head start --port 8081

# 集群管理
sage-core cluster list
sage-core cluster status
sage-core cluster scale --workers 5
```

## 📊 作业管理

### 作业提交和控制

```bash
# 提交作业
sage job submit my_app.py --parallelism 4

# 列出作业
sage job list

# 查看作业状态
sage job status <job-id>

# 停止作业
sage job stop <job-id>

# 取消作业
sage job cancel <job-id>

# 重启作业
sage job restart <job-id>
```

### 作业监控

```bash
# 查看作业详情
sage job describe <job-id>

# 查看作业日志
sage job logs <job-id>

# 实时跟踪日志
sage job logs <job-id> --follow

# 查看指标
sage job metrics <job-id>

# 性能分析
sage job profile <job-id>
```

## 🚀 部署工具

### 应用打包

```bash
# 创建部署包
sage deploy package my_app/ --output my_app.sage

# 验证部署包
sage deploy validate my_app.sage

# 提取部署包
sage deploy extract my_app.sage --target ./extracted/
```

## 🛠️ 开发工具

### 项目脚手架

```bash
# 创建新项目
sage create project my-stream-app --template basic

# 可用模板
sage create project --list-templates

# 创建函数模板
sage create function MyMapFunction --type map --output-dir src/functions/
```

### 本地开发

```bash
# 启动本地开发环境
sage dev start

# 热重载模式运行
sage dev run my_app.py --watch

# 调试模式
sage dev debug my_app.py --breakpoint MyFunction.map

# 性能分析
sage dev profile my_app.py --output profile.html
```

### 测试工具

```bash
# 运行测试
sage test run tests/

# 运行特定测试
sage test run tests/test_my_function.py::test_map

# 性能测试
sage test benchmark my_app.py --iterations 100

# 生成测试报告
sage test report --format html --output test-report.html
```

## 📈 监控和诊断

### 系统监控

```bash
# 查看集群状态
sage cluster status

# 查看节点信息
sage cluster nodes

# 查看资源使用
sage cluster resources

# 查看网络状态
sage cluster network
```

### 日志管理

```bash
# 查看系统日志
sage logs system

# 查看组件日志
sage logs jobmanager
sage logs worker --node worker-01

# 日志搜索
sage logs search "ERROR" --since 1h

# 日志导出
sage logs export --output logs.tar.gz --since 24h
```

### 性能分析

```bash
# CPU性能分析
sage profile cpu <job-id> --duration 60s

# 内存分析
sage profile memory <job-id>

# 网络分析
sage profile network <job-id>

# 生成性能报告
sage profile report <job-id> --format html
```

## ⚙️ 配置管理

### 全局配置

```bash
# 查看所有配置
sage config list

# 设置配置项
sage config set logging.level DEBUG
sage config set cluster.default_parallelism 8

# 获取配置项
sage config get logging.level

# 重置配置
sage config reset logging.level

# 导入配置
sage config import config.yaml

# 导出配置  
sage config export --output current-config.yaml
```

### 环境配置

```bash
# 列出环境
sage config env list

# 创建环境
sage config env create production --from staging

# 切换环境
sage config env use production

# 删除环境
sage config env delete development
```

## 🔌 扩展管理

### 插件管理

```bash
# 列出已安装插件
sage extensions list

# 安装插件
sage extensions install sage-kafka-connector

# 更新插件
sage extensions update sage-kafka-connector

# 卸载插件
sage extensions uninstall sage-kafka-connector

# 搜索插件
sage extensions search kafka
```

### 自定义扩展

```bash
# 创建扩展模板
sage extensions create my-extension --type connector

# 构建扩展
sage extensions build my-extension/

# 发布扩展
sage extensions publish my-extension/ --registry local
```

## 🔐 安全和认证

### 用户管理

```bash
# 登录
sage auth login --username admin

# 登出
sage auth logout

# 查看当前用户
sage auth whoami

# 修改密码
sage auth passwd
```

### 访问控制

```bash
# 列出角色
sage auth roles list

# 创建角色
sage auth roles create developer --permissions job:submit,job:read

# 分配角色
sage auth users assign-role user1 developer

# 查看权限
sage auth permissions check user1 job:submit
```

## 📱 交互式界面

### Web UI

```bash
# 启动Web界面
sage ui start --port 8080

# 启动只读模式
sage ui start --readonly

# 启动带认证的界面
sage ui start --auth-required
```

### 交互式Shell

```bash
# 启动交互式Shell
sage shell

# 在Shell中执行命令
sage> job list
sage> cluster status
sage> exit
```

## 📊 示例命令组合

### 开发工作流

```bash
# 1. 创建项目
sage create project stream-analytics --template kafka-processing

# 2. 启动开发环境
cd stream-analytics
sage dev start

# 3. 运行应用
sage dev run main.py --watch

# 4. 运行测试
sage test run --coverage

# 5. 性能分析
sage dev profile main.py --output profile.html
```

### 生产部署

```bash
# 1. 打包应用
sage deploy package . --output stream-analytics.sage

# 2. 验证包
sage deploy validate stream-analytics.sage

# 3. 部署到集群
sage job submit stream-analytics.sage --env production

# 4. 监控部署
sage job status <job-id>
sage job logs <job-id> --follow
```

### 运维监控

```bash
# 1. 检查集群健康
sage cluster status
sage cluster resources

# 2. 查看作业状态
sage job list --filter running
sage job metrics --all

# 3. 性能分析
sage profile cpu --all-jobs --duration 5m

# 4. 导出日志
sage logs export --output daily-logs.tar.gz --since 24h
```

## 🔧 故障排除

### 常见问题诊断

```bash
# 检查系统状态
sage doctor

# 网络连接测试
sage network test

# 配置验证
sage config validate

# 依赖检查
sage dependencies check
```

### 调试工具

```bash
# 详细日志输出
sage --verbose job submit my_app.py

# 跟踪模式
sage --trace job submit my_app.py

# 调试信息
sage --debug cluster status
```

## 📚 更多信息

- 查看 `sage <command> --help` 获取详细帮助
<!-- - 访问 [CLI 参考文档](../cli-reference.md) 了解所有命令 -->
- 访问 CLI 参考文档 了解所有命令
<!-- - 查看 [配置参考](../configuration.md) 了解配置选项 -->
- 查看 配置参考 了解配置选项

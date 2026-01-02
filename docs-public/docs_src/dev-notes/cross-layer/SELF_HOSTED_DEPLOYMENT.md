# SAGE Studio Self-Hosted 部署指南

本文档介绍如何在 self-hosted GitHub Actions runner 上自动部署 SAGE Studio。

## 📋 前置要求

### 1. Self-Hosted Runner 配置

确保你的 self-hosted runner 已配置：

```bash
# 在服务器上安装 GitHub Actions runner
# 参考: https://docs.github.com/en/actions/hosting-your-own-runners/adding-self-hosted-runners

# 添加 runner 标签
./config.sh --labels self-hosted,linux,x64
```

### 2. 服务器环境

**最低要求**:

- Ubuntu 20.04+ / CentOS 7+ / Debian 10+
- Python 3.10+
- 4GB+ RAM
- 20GB+ 磁盘空间
- 公网 IP 或可访问的内网 IP

**安装依赖**:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git \
    build-essential cmake pkg-config \
    libopenblas-dev liblapack-dev curl

# CentOS/RHEL
sudo yum install -y python3 python3-pip python3-devel git \
    gcc gcc-c++ make cmake pkgconfig \
    openblas-devel lapack-devel curl
```

### 3. GitHub Secrets 配置

在 GitHub 仓库设置中配置以下 Secrets:

| Secret 名称         | 说明                                         | 必需 |
| ------------------- | -------------------------------------------- | ---- |
| `SAGE_CHAT_API_KEY` | OpenAI 兼容 LLM 访问密钥 (用于 Gateway/vLLM) | ✅   |
| `OPENAI_API_KEY`    | OpenAI API Key (可选)                        | ❌   |
| `HF_TOKEN`          | Hugging Face Token (用于模型下载)            | ❌   |

配置路径: `Settings → Secrets and variables → Actions → New repository secret`

## 🚀 部署方式

### 方式 1: 自动部署（推荐）

每次推送到 `main` 或 `feat/unified-chat-canvas-rebased` 分支时自动部署：

```bash
git push origin feat/unified-chat-canvas-rebased
```

GitHub Actions 会自动：

1. 在 self-hosted runner 上拉取最新代码
1. 安装 SAGE 及依赖
1. 构建 RAG 索引
1. 启动 Gateway 和 Studio 服务
1. 输出访问地址

### 方式 2: 手动触发部署

在 GitHub Actions 页面手动触发：

1. 进入 `Actions` 标签
1. 选择 `Deploy SAGE Studio to Self-Hosted Server`
1. 点击 `Run workflow`
1. (可选) 自定义端口:
   - Studio 访问端口 (默认: 4200)
   - Gateway API 端口 (默认: 8000)
1. 点击 `Run workflow` 执行

## 📍 访问部署的服务

部署成功后，在 Actions 运行日志的 Summary 中可以看到访问地址：

### 公网访问

```
Studio UI:   http://<公网IP>:4200
Gateway API: http://<公网IP>:8000
```

### 内网访问

```
Studio UI:   http://<内网IP>:4200
Gateway API: http://<内网IP>:8000
```

### 测试访问

```bash
# 测试 Gateway API
curl http://<服务器IP>:8000/health

# 测试 Studio（浏览器访问）
http://<服务器IP>:4200
```

## 🔧 服务管理

### SSH 到服务器后的管理命令

```bash
# 查看服务状态
ps aux | grep -E "sage studio|sage-llm-gateway"

# 查看日志
tail -f ~/.sage/gateway.log
tail -f ~/.sage/studio.log

# 停止服务
pkill -f "sage studio"
pkill -f "sage-llm-gateway"

# 手动重启服务
nohup sage-llm-gateway --host 0.0.0.0 --port 8000 > ~/.sage/gateway.log 2>&1 &
nohup sage studio start --port 4200 > ~/.sage/studio.log 2>&1 &

# 重建 RAG 索引
sage chat ingest --source docs-public/docs_src
```

### 检查服务健康

```bash
# 检查 Gateway
curl http://localhost:8000/health

# 检查 Studio（返回 HTML）
curl http://localhost:4200

# 查看端口占用
sudo netstat -tlnp | grep -E "4200|8000"
```

## 🔒 安全配置

### 1. 防火墙配置

**Ubuntu/Debian (UFW)**:

```bash
# 允许 Studio 端口
sudo ufw allow 4200/tcp

# 允许 Gateway 端口
sudo ufw allow 8000/tcp

# 查看规则
sudo ufw status
```

**CentOS/RHEL (firewalld)**:

```bash
# 允许端口
sudo firewall-cmd --permanent --add-port=4200/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# 查看规则
sudo firewall-cmd --list-ports
```

### 2. 反向代理配置（可选）

使用 Nginx 配置 HTTPS 和域名访问：

```nginx
# /etc/nginx/sites-available/sage-studio
server {
    listen 80;
    server_name studio.yourdomain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name studio.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Studio UI
    location / {
        proxy_pass http://localhost:4200;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Gateway API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/sage-studio /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Systemd 服务配置（推荐生产环境）

创建 systemd 服务文件以实现开机自启和崩溃重启：

**Gateway 服务** (`/etc/systemd/system/sage-llm-gateway.service`):

```ini
[Unit]
Description=SAGE Gateway API Service
After=network.target

[Service]
Type=simple
User=<your-username>
WorkingDirectory=/home/<your-username>/SAGE
Environment="PATH=/home/<your-username>/.local/bin:/usr/bin"
Environment="SAGE_CHAT_API_KEY=<your-key>"
ExecStart=/home/<your-username>/.local/bin/sage-llm-gateway --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=append:/home/<your-username>/.sage/gateway.log
StandardError=append:/home/<your-username>/.sage/gateway.log

[Install]
WantedBy=multi-user.target
```

**Studio 服务** (`/etc/systemd/system/sage-studio.service`):

```ini
[Unit]
Description=SAGE Studio UI Service
After=network.target sage-llm-gateway.service
Requires=sage-llm-gateway.service

[Service]
Type=simple
User=<your-username>
WorkingDirectory=/home/<your-username>/SAGE
Environment="PATH=/home/<your-username>/.local/bin:/usr/bin"
ExecStart=/home/<your-username>/.local/bin/sage studio start --port 4200
Restart=always
RestartSec=10
StandardOutput=append:/home/<your-username>/.sage/studio.log
StandardError=append:/home/<your-username>/.sage/studio.log

[Install]
WantedBy=multi-user.target
```

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable sage-llm-gateway sage-studio
sudo systemctl start sage-llm-gateway sage-studio

# 查看状态
sudo systemctl status sage-llm-gateway sage-studio

# 查看日志
sudo journalctl -u sage-llm-gateway -f
sudo journalctl -u sage-studio -f
```

## 🔍 故障排查

### 问题 1: 部署后无法访问

**检查步骤**:

```bash
# 1. 检查进程是否运行
ps aux | grep -E "sage studio|sage-llm-gateway"

# 2. 检查端口是否监听
sudo netstat -tlnp | grep -E "4200|8000"

# 3. 检查防火墙
sudo ufw status  # Ubuntu
sudo firewall-cmd --list-all  # CentOS

# 4. 查看日志
tail -100 ~/.sage/gateway.log
tail -100 ~/.sage/studio.log
```

### 问题 2: Gateway 启动失败

常见原因:

- API Key 未配置或无效
- 端口被占用
- Python 环境问题

**解决方法**:

```bash
# 检查 API Key
cat ~/.sage/.env | grep SAGE_CHAT_API_KEY

# 检查端口占用
sudo lsof -i :8000

# 手动启动查看详细错误
sage-llm-gateway --host 0.0.0.0 --port 8000
```

### 问题 3: RAG 索引构建失败

**解决方法**:

```bash
# 手动重建索引
cd /home/<username>/SAGE
sage chat ingest --source docs-public/docs_src

# 检查索引文件
ls -la ~/.sage/cache/chat/
```

### 问题 4: 从外网无法访问

**检查清单**:

1. ✅ 服务器有公网 IP
1. ✅ 云服务商安全组开放端口 4200, 8000
1. ✅ 服务器防火墙允许端口
1. ✅ 服务监听在 `0.0.0.0` 而非 `127.0.0.1`

## 📊 监控和维护

### 日志轮转配置

创建 `/etc/logrotate.d/sage-studio`:

```
/home/*/.sage/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644
}
```

### 定期健康检查脚本

创建 `~/sage-health-check.sh`:

```bash
#!/bin/bash

check_service() {
    local name=$1
    local port=$2

    if curl -s -o /dev/null -w "%{http_code}" http://localhost:$port | grep -q "200\|301"; then
        echo "✅ $name 运行正常"
        return 0
    else
        echo "❌ $name 异常，尝试重启..."
        pkill -f "$name"
        sleep 3
        # 根据服务类型重启
        if [ "$name" = "sage-llm-gateway" ]; then
            nohup sage-llm-gateway --host 0.0.0.0 --port $port > ~/.sage/gateway.log 2>&1 &
        else
            nohup sage studio start --port $port > ~/.sage/studio.log 2>&1 &
        fi
        return 1
    fi
}

check_service "sage-llm-gateway" 8000
check_service "sage studio" 4200
```

添加到 crontab (每 5 分钟检查):

```bash
*/5 * * * * /home/<username>/sage-health-check.sh
```

## 📚 相关资源

- [SAGE 文档](https://github.com/intellistream/SAGE)
- [GitHub Actions 自托管 Runner](https://docs.github.com/en/actions/hosting-your-own-runners)
- [SAGE CLI 命令参考](../../../packages/sage-cli/README.md)
- [Gateway API 文档](../../../packages/sage-llm-gateway/README.md)

## 💡 最佳实践

1. **使用 systemd**: 实现自动重启和开机启动
1. **配置反向代理**: 通过 Nginx 提供 HTTPS 和域名访问
1. **定期备份**: 备份 `~/.sage/` 目录（包含索引和配置）
1. **监控日志**: 定期检查日志文件大小，配置日志轮转
1. **安全加固**:
   - 使用非 root 用户运行服务
   - 配置防火墙仅开放必要端口
   - 定期更新系统和依赖
1. **性能优化**:
   - 根据服务器配置调整工作进程数
   - 配置 Redis/Memcached 缓存（可选）
   - 使用 CDN 加速静态资源（可选）

______________________________________________________________________

**需要帮助？** 在 [GitHub Issues](https://github.com/intellistream/SAGE/issues) 提交问题。

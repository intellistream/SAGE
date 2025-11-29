# SAGE Studio 远程访问指南

## 部署架构

SAGE Studio 部署在实验室服务器上，可通过以下方式访问：

- **服务器位置**: 华中科技大学校园网
- **Studio 端口**: 4200 (默认)
- **Gateway 端口**: 8000 (默认)

## 访问方案

### 方案 1: 校园网内直接访问 ✅ 推荐

如果你在华中科技大学校园网内，可以直接访问：

**获取访问地址**：

1. 查看 GitHub Actions 的部署摘要
1. 或联系团队成员获取服务器 IP
1. 访问: `http://<服务器IP>:4200`

**适用场景**：

- 在校园内使用校园网
- 通过华科 VPN 连接到校园网
- 在实验室/办公室内网

**优点**：

- 无需额外配置
- 访问速度快
- 安全可靠

### 方案 2: 华科 VPN 访问 🔐 校外访问

如果你不在校园内，需要先连接华科 VPN：

1. **安装华科 VPN 客户端**

   - 访问华科网络中心获取 VPN 客户端
   - 使用统一身份认证账号登录

1. **连接 VPN 后访问**

   - 从 GitHub Actions 部署摘要获取服务器地址
   - 或联系团队获取访问 URL

## CI/CD 自动部署后的访问

当 GitHub Actions 部署完成后：

```yaml
# .github/workflows/deploy-studio.yml 会输出：
- ✅ Studio deployed successfully
- 📍 Local access: http://192.168.31.88:4200
- 🌐 Public access: Configure port forwarding or use tunnel
```

## 推荐配置

### 开发/测试环境

- 使用 ngrok（快速临时访问）

### 生产环境

- 使用 Cloudflare Tunnel + 自定义域名
- 配置 nginx 反向代理
- 启用 HTTPS
- 添加身份认证（OAuth2 或 Basic Auth）

## 安全检查清单

- [ ] 配置防火墙规则
- [ ] 使用 HTTPS（SSL/TLS）
- [ ] 启用访问认证
- [ ] 限制允许访问的 IP 段
- [ ] 定期更新 SAGE 到最新版本
- [ ] 监控访问日志
- [ ] 配置 rate limiting

## 故障排查

### 无法访问 Studio

1. 检查服务是否运行：

```bash
ps aux | grep -E "sage-studio|uvicorn"
```

2. 检查端口监听：

```bash
ss -tlnp | grep 4200
```

3. 检查防火墙：

```bash
sudo ufw status
sudo iptables -L -n | grep 4200
```

4. 查看日志：

```bash
tail -50 ~/.sage/studio.log
tail -50 ~/.sage/gateway.log
```

### 外网无法访问但内网可以

- 检查路由器端口转发配置
- 检查服务是否绑定到 0.0.0.0 而非 127.0.0.1
- 检查运营商是否封禁了相关端口

## 联系支持

遇到问题？

- GitHub Issues: https://github.com/intellistream/SAGE/issues
- 文档: https://intellistream.github.io/SAGE

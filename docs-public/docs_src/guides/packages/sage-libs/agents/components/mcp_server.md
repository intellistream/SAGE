# MCP Server 使用文档

!!! note "定位"
    **MCP Server** 是一个统一的工具服务端，实现了 `list_tools` 和 `call_tool` 两个核心接口，
    支持 **本地工具注册** 与 **远程 MCP 服务挂载**，使得 Agent 可以调用本地和远程的工具。

---

## 1. 功能概述

- **本地工具注册**：支持通过 Python 模块路径动态加载工具类并注册。
- **远程 MCP 挂载**：支持将其他 MCP 服务的工具映射为本地代理工具，带前缀区分。
- **统一调用接口**：所有工具（本地/远程代理）都可以通过 `call_tool` 调用。
- **参数校验**：基于 MCP `input_schema.required` 字段进行必填参数校验。
- **健康检查**：提供 `/health` 接口返回当前注册工具和远程 MCP 的数量。

---

## 2. 接口设计

### 2.1 JSON-RPC 基础格式

请求：
```json
{
  "jsonrpc": "2.0",
  "id": "req-id",
  "method": "method_name",
  "params": {...}
}
```

响应：
```json
{
  "jsonrpc": "2.0",
  "id": "req-id",
  "result": {...},
  "error": null
}
```

---

### 2.2 支持的方法

#### (1) list_tools
- 描述：列出当前所有可用工具。
- 示例请求：
```json
{
  "jsonrpc": "2.0", "id": "l0", "method": "list_tools", "params": {}
}
```
- 响应示例：
```json
{
  "jsonrpc": "2.0", "id": "l0",
  "result": {
    "translator": {
      "description": "Translate English text to Chinese",
      "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}
    }
  }
}
```

#### (2) call_tool
- 描述：调用某个工具。
- 示例请求：
```json
{
  "jsonrpc": "2.0", "id": "c1", "method": "call_tool",
  "params": {"name": "translator", "arguments": {"text": "Hello world"}}
}
```
- 响应示例：
```json
{
  "jsonrpc": "2.0", "id": "c1", "result": {"translated": "[翻译结果] Hello world"}
}
```

#### (3) register_tool_from_path
- 描述：通过 Python 路径动态注册本地工具类。
- 示例请求：
```json
{
  "jsonrpc": "2.0", "id": "r1", "method": "register_tool_from_path",
  "params": {"module": "other_pkg.tools.my_tool", "class": "MyCoolTool", "init_kwargs": {}}
}
```
- 响应示例：
```json
{"jsonrpc": "2.0", "id": "r1", "result": {"ok": true, "name": "MyCoolTool"}}
```

#### (4) mount_remote_mcp
- 描述：挂载远程 MCP 服务，将对方工具映射为本地代理工具。
- 示例请求：
```json
{
  "jsonrpc": "2.0", "id": "m1", "method": "mount_remote_mcp",
  "params": {"adapter_id": "t1", "base_url": "http://upstream:9001", "prefix": "up_"}
}
```
- 响应示例：
```json
{"jsonrpc": "2.0", "id": "m1", "result": {"ok": true, "mounted": ["up_translator"]}}
```

#### (5) refresh_remote_mcp
- 描述：刷新远程 MCP 工具清单，更新代理。
- 示例请求：
```json
{"jsonrpc": "2.0", "id": "rf1", "method": "refresh_remote_mcp", "params": {"adapter_id": "t1", "prefix": "up_"}}
```

#### (6) unmount_remote_mcp
- 描述：卸载远程 MCP，清除对应的代理工具。
- 示例请求：
```json
{"jsonrpc": "2.0", "id": "u1", "method": "unmount_remote_mcp", "params": {"adapter_id": "t1"}}
```

---

## 3. 部署方式

### 安装依赖
```bash
pip install fastapi uvicorn pydantic requests
```

### 启动服务
```bash
uvicorn mcp_server:app --host 0.0.0.0 --port 9000
```

### 健康检查
```bash
curl http://localhost:9000/health
```
返回：
```json
{"ok": true, "tools": 0, "remotes": 0}
```

---

## 4. 使用示例

### 本地工具调用流程
1. 注册工具：
```bash
curl -s http://localhost:9000/jsonrpc -H "Content-Type: application/json" -d '{
  "jsonrpc":"2.0","id":"r1","method":"register_tool_from_path",
  "params":{"module":"my_pkg.tools","class":"MyTool","init_kwargs":{}}
}'
```
2. 调用工具：
```bash
curl -s http://localhost:9000/jsonrpc -H "Content-Type: application/json" -d '{
  "jsonrpc":"2.0","id":"c1","method":"call_tool",
  "params":{"name":"MyTool","arguments":{"x":42}}
}'
```

### 远程工具调用流程
1. 挂载远程 MCP：
```bash
curl -s http://localhost:9000/jsonrpc -H "Content-Type: application/json" -d '{
  "jsonrpc":"2.0","id":"m1","method":"mount_remote_mcp",
  "params":{"adapter_id":"t1","base_url":"http://upstream:9001","prefix":"up_"}
}'
```
2. 调用代理工具：
```bash
curl -s http://localhost:9000/jsonrpc -H "Content-Type: application/json" -d '{
  "jsonrpc":"2.0","id":"c2","method":"call_tool",
  "params":{"name":"up_translator","arguments":{"text":"Hello world"}}
}'
```

---

## 5. 扩展方向

- **完整 JSON Schema 校验**：目前只校验必填参数，可以接入 `jsonschema`。
- **权限控制**：为不同客户端配置访问令牌，限制可用工具。
- **日志与监控**：记录调用耗时、错误率，支持 Prometheus 指标。
- **多协议支持**：除了 HTTP，还可以支持 WebSocket / stdio。

---

## 6. 总结

MCP Server 提供了一个 **本地+远程工具统一调用平台**，
- Agent 只需通过 `list_tools` 获取清单，
- 再通过 `call_tool` 调用，无需关心工具实现细节。

这样，你不仅可以快速注册本地 Python 工具，还能无缝调用他人提供的远程 MCP 工具。

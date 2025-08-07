# SAGE JobManager CLI Pause 功能文档

## 概述

已成功将 `jobmanager.pause_job` 接口集成到 SAGE CLI 的 job 管理模块中，为用户提供了便捷的作业暂停和恢复功能。

## 新增命令

### 1. `sage job pause` - 暂停作业

**语法：**
```bash
sage job pause <job_identifier> [--force]
```

**参数：**
- `job_identifier`: 作业编号或UUID（支持部分匹配）
- `--force, -f`: 强制暂停，无需确认

**功能：**
- 暂停正在运行的作业
- 保持作业状态以便后续恢复
- 提供友好的确认提示

**示例：**
```bash
# 暂停作业（使用作业编号）
sage job pause 1

# 暂停作业（使用UUID）
sage job pause a1b2c3d4-e5f6-7890-1234-567890abcdef

# 强制暂停，无需确认
sage job pause 1 --force
```

### 2. `sage job resume` - 恢复作业

**语法：**
```bash
sage job resume <job_identifier> [--force]
```

**参数：**
- `job_identifier`: 作业编号或UUID（支持部分匹配）
- `--force, -f`: 强制恢复，无需确认

**功能：**
- 恢复已暂停的作业
- 从暂停点继续执行
- `continue` 命令的语义化别名

**示例：**
```bash
# 恢复作业（使用作业编号）
sage job resume 1

# 恢复作业（使用UUID）
sage job resume a1b2c3d4-e5f6-7890-1234-567890abcdef

# 强制恢复，无需确认
sage job resume 1 --force
```

## 现有命令更新

### 状态显示增强

所有状态显示命令现在都支持 `paused` 状态：

- `sage job list` - 列表中显示暂停状态
- `sage job show` - 详情中显示暂停状态
- `sage job status` - 状态查询支持暂停状态
- `sage job monitor` - 监控界面显示暂停状态

**颜色编码：**
- 🟢 `running` - 绿色
- 🟡 `stopped/paused` - 黄色
- 🔴 `failed` - 红色

## 命令对比

| 功能 | 命令 | 说明 |
|------|------|------|
| 暂停作业 | `sage job pause` | 暂停作业，保持状态 |
| 停止作业 | `sage job stop` | 停止作业（与pause相同实现）|
| 恢复作业 | `sage job resume` | 恢复暂停的作业 |
| 继续作业 | `sage job continue` | 重启/继续作业 |

## 技术实现

### 1. CLI层级集成

```python
@app.command("pause")
def pause_job(
    job_identifier: str = typer.Argument(..., help="作业编号或UUID"),
    force: bool = typer.Option(False, "--force", "-f", help="强制暂停，无需确认")
):
    # 调用 JobManagerClient.pause_job()
    result = cli.client.pause_job(job_uuid)
```

### 2. 客户端支持

`JobManagerClient` 已实现 `pause_job` 方法：

```python
def pause_job(self, job_uuid: str) -> Dict[str, Any]:
    request = {
        "action": "pause_job",
        "request_id": str(uuid.uuid4()),
        "job_uuid": job_uuid
    }
    return self.send_request(request)
```

### 3. JobManager后端

后端 `JobManager.pause_job` 方法处理实际的作业暂停：

```python
def pause_job(self, env_uuid: str) -> Dict[str, Any]:
    # 停止dispatcher
    job_info.dispatcher.stop()
    job_info.update_status("stopped")
    return {"uuid": env_uuid, "status": "stopped", ...}
```

## 使用场景

1. **资源管理**: 临时释放计算资源给其他任务
2. **调试分析**: 暂停作业进行中间状态检查
3. **系统维护**: 在系统维护期间暂停非关键作业
4. **错误排查**: 暂停异常作业进行问题诊断

## 最佳实践

### 1. 作业标识符使用
```bash
# 推荐：使用作业编号（简单）
sage job pause 1

# 可选：使用UUID前缀（唯一时）
sage job pause a1b2c3d4

# 完整UUID（明确）
sage job pause a1b2c3d4-e5f6-7890-1234-567890abcdef
```

### 2. 批量操作
```bash
# 列出所有作业
sage job list

# 逐个暂停运行中的作业
sage job pause 1
sage job pause 2

# 批量恢复
sage job resume 1
sage job resume 2
```

### 3. 监控工作流
```bash
# 监控作业状态
sage job monitor

# 暂停特定作业
sage job pause 1

# 查看暂停状态
sage job show 1

# 恢复作业
sage job resume 1
```

## 错误处理

CLI 提供完善的错误处理和用户提示：

- ✅ 成功操作提示
- ❌ 错误信息显示
- ℹ️ 操作确认对话
- 🟡 状态变更通知

## 总结

通过将 `jobmanager.pause_job` 接口集成到 CLI 中，现在用户可以：

1. **便捷地暂停和恢复作业**
2. **获得丰富的状态反馈**
3. **使用统一的命令行界面**
4. **享受完整的错误处理和确认机制**

这大大提升了 SAGE 系统的可用性和作业管理的灵活性。

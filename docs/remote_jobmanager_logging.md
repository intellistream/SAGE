# RemoteJobManager 日志系统重构

## 概述

为 `RemoteJobManager` 重新设计了专用的日志系统，使其独立于父类 `JobManager` 的日志配置，采用更规范的目录结构和软链接机制。

## 新的日志目录结构

```
/tmp/sage-jm/
├── session_20250722_062643/          # 具体的session目录
│   ├── remote_jobmanager.log         # 主要日志文件
│   ├── error.log                     # 错误日志
│   └── actor.log                     # Ray Actor专用日志
├── session_20250722_065432/          # 另一个session目录
│   └── ...
└── session_latest -> session_20250722_065432  # 软链接指向最新session
```

## 主要特性

### 1. 独立的日志目录
- **基础目录**: `/tmp/sage-jm/`
- **Session目录**: `/tmp/sage-jm/session_YYYYMMDD_HHMMSS/`
- **软链接**: `/tmp/sage-jm/session_latest` 始终指向最新的session目录

### 2. 多层次日志文件
- `remote_jobmanager.log`: 详细的DEBUG级别日志
- `error.log`: 错误级别日志
- `actor.log`: Ray Actor相关的INFO级别日志
- **控制台**: INFO级别输出

### 3. 自动软链接管理
每次启动 `RemoteJobManager` 时：
1. 创建新的 session 目录
2. 自动更新 `session_latest` 软链接指向新目录
3. 保留历史session目录以便追溯

## 代码实现

### 重写的 setup_logging_system 方法

```python
def setup_logging_system(self):
    """
    重写日志系统设置，为RemoteJobManager使用专门的日志目录结构
    - 日志目录: /tmp/sage-jm/session_xxxx
    - 软链接: /tmp/sage-jm/session_latest -> session_xxxx
    """
    # 1. 生成时间戳标识
    self.session_timestamp = datetime.now()
    self.session_id = self.session_timestamp.strftime("%Y%m%d_%H%M%S")
    
    # 2. 设置RemoteJobManager专用的日志目录结构
    sage_jm_base = Path("/tmp/sage-jm")
    sage_jm_base.mkdir(parents=True, exist_ok=True)
    
    # 具体的session目录
    session_dir = sage_jm_base / f"session_{self.session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    self.log_base_dir = session_dir
    
    # 3. 创建或更新 session_latest 软链接
    latest_link = sage_jm_base / "session_latest"
    try:
        # 如果软链接已存在，先删除
        if latest_link.is_symlink() or latest_link.exists():
            latest_link.unlink()
        
        # 创建新的软链接，指向当前session目录
        latest_link.symlink_to(f"session_{self.session_id}")
        
    except Exception as e:
        # 如果创建软链接失败，记录警告但不影响主要功能
        print(f"Warning: Failed to create session_latest symlink: {e}")
    
    # 4. 创建RemoteJobManager专用的日志配置
    self.logger = CustomLogger([
        ("console", "INFO"),  # 控制台显示重要信息
        (os.path.join(self.log_base_dir, "remote_jobmanager.log"), "DEBUG"),  # 详细日志
        (os.path.join(self.log_base_dir, "error.log"), "ERROR"),  # 错误日志
        (os.path.join(self.log_base_dir, "actor.log"), "INFO")    # Actor专用日志
    ], name="RemoteJobManager")
    
    # 5. 记录初始化信息
    self.logger.info(f"RemoteJobManager logging system initialized")
    self.logger.info(f"Session ID: {self.session_id}")
    self.logger.info(f"Log directory: {self.log_base_dir}")
    self.logger.info(f"Latest session link: {latest_link}")
```

## 使用方式

### 快速查看最新日志
```bash
# 查看最新session的日志
tail -f /tmp/sage-jm/session_latest/remote_jobmanager.log

# 查看错误日志
tail -f /tmp/sage-jm/session_latest/error.log

# 查看Actor日志
tail -f /tmp/sage-jm/session_latest/actor.log
```

### 历史日志查询
```bash
# 列出所有session
ls -la /tmp/sage-jm/

# 查看特定session的日志
ls -la /tmp/sage-jm/session_20250722_062643/
```

## 测试

提供了完整的测试脚本 `test_remote_jobmanager_logging.py`，可以验证：
- 日志目录创建
- 软链接功能
- 日志文件生成
- 内容写入

运行测试：
```bash
cd /home/tjy/SAGE
python test_remote_jobmanager_logging.py
```

## 优势

1. **独立性**: RemoteJobManager 有自己的日志系统，不受父类影响
2. **便捷性**: `session_latest` 软链接让用户总是能快速找到最新日志
3. **历史性**: 保留所有历史session，便于问题追溯
4. **标准化**: 统一的目录结构，便于运维和监控
5. **扩展性**: 容易添加新的日志文件类型

## 与父类的区别

| 特性 | JobManager | RemoteJobManager |
|------|------------|------------------|
| 日志目录 | `{project_root}/logs/jobmanager_{session_id}` | `/tmp/sage-jm/session_{session_id}` |
| 软链接 | 无 | `session_latest` 指向最新session |
| 日志文件 | `jobmanager.log`, `error.log` | `remote_jobmanager.log`, `error.log`, `actor.log` |
| Actor支持 | 无 | 专门的 `actor.log` |

这样的设计确保了 RemoteJobManager 在分布式环境中有更好的日志管理和监控能力。

# SAGE Studio 用户私有模块开发任务

## 概述

为 SAGE Studio 增加用户认证和数据隔离功能，使每个用户拥有私有的工作空间。

**总工作量预估**: 5-7 天 (MVP 版本)

---

## 并行任务分配

以下 4 个任务可以**并行开发**，最后进行集成测试。

---

## Task 1: 后端认证 API (Backend Auth)

**负责人**: Copilot A  
**预计时间**: 2-3 天  
**依赖**: 无

### Prompt

```
你是 SAGE 框架的开发者。请在 sage-studio 后端实现用户认证系统。

**目标文件**: `packages/sage-studio/src/sage/studio/config/backend/api.py`

**需要实现**:

1. 新建 `packages/sage-studio/src/sage/studio/services/auth_service.py`:
   - 用户模型 (User: id, username, password_hash, created_at)
   - 密码哈希 (使用 bcrypt 或 passlib)
   - JWT Token 生成和验证 (使用 python-jose)
   - SQLite 数据库存储用户信息 (存放在 ~/.local/share/sage/studio.db)

2. 在 api.py 中添加认证端点:
   - POST /api/auth/register - 用户注册
   - POST /api/auth/login - 用户登录，返回 JWT token
   - GET /api/auth/me - 获取当前用户信息
   - POST /api/auth/logout - 登出

3. 创建 FastAPI 依赖注入:
   - `get_current_user(token: str)` - 从 JWT 解析用户
   - 可选的认证中间件

**技术要求**:
- JWT 过期时间: 24 小时
- 密码要求: 最少 6 位
- 使用 Pydantic 模型定义请求/响应
- 添加适当的错误处理和日志

**参考现有代码**:
- 查看 `api.py` 中现有的 API 结构
- 遵循 SAGE 的代码风格 (ruff 格式化, 100 字符行宽)

**测试**: 创建 `packages/sage-studio/tests/services/test_auth_service.py`
```

---

## Task 2: 后端数据隔离 (Data Isolation)

**负责人**: Copilot B  
**预计时间**: 2 天  
**依赖**: Task 1 的 `get_current_user` 函数接口定义

### Prompt

```
你是 SAGE 框架的开发者。请修改 sage-studio 后端，实现按用户隔离数据。

**目标文件**: `packages/sage-studio/src/sage/studio/config/backend/api.py`

**当前状态**:
- Pipeline 存储在全局目录: `.sage/pipelines/`
- Chat session 使用全局 session ID
- 所有用户看到相同内容

**需要修改**:

1. 修改数据存储路径结构:
   ```
   ~/.local/share/sage/
   ├── studio.db          # 用户数据库 (Task 1 创建)
   └── users/
       └── {user_id}/
           ├── pipelines/  # 用户的流程
           ├── sessions/   # 用户的聊天会话
           └── uploads/    # 用户上传的文件
   ```

2. 修改以下 API 端点，添加用户过滤:
   - GET /api/jobs - 只返回当前用户的 jobs
   - POST /api/submit - 保存到用户目录
   - GET /api/flow/{flow_id}/export - 只能导出自己的流程
   - POST /api/flow/import - 导入到用户目录

3. 修改 Chat 相关 API:
   - GET /api/chat/sessions - 只返回当前用户的会话
   - POST /api/chat/sessions - 创建会话时关联用户
   - 所有 /api/chat/* 端点添加用户权限检查

4. 创建辅助函数:
   - `get_user_data_dir(user_id: str) -> Path`
   - `get_user_pipelines_dir(user_id: str) -> Path`

**兼容性**:
- 未登录用户使用 "anonymous" 作为 user_id (向后兼容)
- 迁移脚本: 将现有 .sage/pipelines/ 数据标记为 "anonymous"

**参考**:
- 查看 `_convert_pipeline_to_job()` 函数了解数据格式
- 查看 `/api/jobs` 端点了解现有实现
```

---

## Task 3: 前端认证 UI (Frontend Auth)

**负责人**: Copilot C  
**预计时间**: 2 天  
**依赖**: Task 1 的 API 接口定义

### Prompt

```
你是 SAGE 框架的前端开发者。请为 sage-studio 前端添加用户认证功能。

**技术栈**: React + TypeScript + Ant Design + Zustand

**目标目录**: `packages/sage-studio/src/sage/studio/frontend/src/`

**需要创建**:

1. `store/authStore.ts` - Zustand 状态管理:
   ```typescript
   interface AuthState {
     user: User | null
     token: string | null
     isAuthenticated: boolean
     login: (username: string, password: string) => Promise<void>
     register: (username: string, password: string) => Promise<void>
     logout: () => void
     checkAuth: () => Promise<void>
   }
   ```
   - Token 存储在 localStorage
   - 页面加载时自动检查认证状态

2. `components/LoginPage.tsx`:
   - 登录/注册切换表单
   - 使用 Ant Design Form 组件
   - 显示错误信息
   - 登录成功后跳转到主页

3. `components/UserMenu.tsx`:
   - 显示当前用户名
   - 下拉菜单: 个人设置、退出登录
   - 集成到 Toolbar.tsx 右侧

4. 修改 `services/api.ts`:
   - 添加 auth API 调用函数
   - 所有 API 请求自动添加 Authorization header
   - 401 响应时自动跳转登录页

5. 修改 `App.tsx`:
   - 添加路由守卫
   - 未登录用户重定向到登录页
   - 或者: 未登录显示受限功能提示

**UI 设计**:
- 登录页面居中卡片式布局
- 与现有 SAGE Studio 风格一致 (蓝色主题 #1890ff)
- 支持按 Enter 提交表单

**参考现有代码**:
- 查看 `store/chatStore.ts` 了解 Zustand 用法
- 查看 `components/Settings.tsx` 了解 Modal 用法
- 查看 `services/api.ts` 了解 API 调用方式
```

---

## Task 4: 前端状态集成 (Frontend Integration)

**负责人**: Copilot D  
**预计时间**: 1-2 天  
**依赖**: Task 2, Task 3 完成后

### Prompt

```
你是 SAGE 框架的前端开发者。请集成用户认证状态到现有组件。

**目标**: 让现有组件感知用户登录状态，显示用户私有数据。

**需要修改的文件**:

1. `components/Toolbar.tsx`:
   - 右侧添加 UserMenu 组件
   - 未登录时显示 "登录" 按钮
   - 已登录时显示用户名和下拉菜单

2. `components/ChatMode.tsx`:
   - 会话列表只显示当前用户的会话
   - 新建会话时自动关联当前用户
   - 未登录时提示需要登录才能保存会话

3. `App.tsx`:
   - 启动时检查认证状态
   - 添加 /login 路由
   - 保护需要认证的路由

4. `store/flowStore.ts`:
   - 添加 userId 字段
   - 保存/加载流程时使用用户上下文

5. 修改所有 API 调用:
   - 确保所有请求带上 Authorization header
   - 处理 401 未授权响应

**用户体验**:
- 页面刷新后保持登录状态
- 登出后清除所有用户数据
- 切换用户时刷新数据列表

**测试场景**:
1. 新用户注册 → 登录 → 创建流程 → 登出 → 重新登录 → 看到之前的流程
2. 用户 A 的流程对用户 B 不可见
3. 未登录用户可以使用基本功能，但数据不持久化

**参考**:
- 查看 `hooks/useKeyboardShortcuts.ts` 了解 hooks 写法
- 查看现有组件的状态管理方式
```

---

## 集成与测试 (最后阶段)

**时间**: 1 天  
**依赖**: 所有任务完成

### 集成检查清单

- [ ] 后端 API 认证正常工作
- [ ] 前端登录/注册流程顺畅
- [ ] 数据按用户正确隔离
- [ ] 未登录用户的兼容性
- [ ] Token 过期处理
- [ ] 错误提示友好

### 测试命令

```bash
# 后端测试
cd packages/sage-studio
pytest tests/services/test_auth_service.py -v

# 前端构建测试
cd packages/sage-studio/src/sage/studio/frontend
npm run build

# 集成测试
sage studio start
# 手动测试登录流程
```

---

## 技术栈汇总

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| 认证 | JWT (python-jose) |
| 密码 | bcrypt / passlib |
| 数据库 | SQLite |
| 前端框架 | React 18 |
| 状态管理 | Zustand |
| UI 组件 | Ant Design 5.x |
| HTTP 客户端 | fetch API |

---

## 文件变更预览

```
packages/sage-studio/
├── src/sage/studio/
│   ├── config/backend/
│   │   └── api.py                    # 修改: 添加认证端点
│   └── services/
│       └── auth_service.py           # 新增: 认证服务
├── frontend/src/
│   ├── components/
│   │   ├── LoginPage.tsx             # 新增: 登录页面
│   │   ├── UserMenu.tsx              # 新增: 用户菜单
│   │   ├── Toolbar.tsx               # 修改: 集成用户菜单
│   │   ├── ChatMode.tsx              # 修改: 用户会话隔离
│   │   └── App.tsx                   # 修改: 路由和认证
│   ├── store/
│   │   └── authStore.ts              # 新增: 认证状态
│   └── services/
│       └── api.ts                    # 修改: 添加认证 header
└── tests/services/
    └── test_auth_service.py          # 新增: 认证测试
```

# SAGE Studio v2.0 - 快速参考

## 🎯 已实现功能速查

### 核心功能
| 功能 | 状态 | 位置 | 快捷键 |
|------|------|------|--------|
| 保存流程 | ✅ | Toolbar → 保存按钮 | - |
| 加载流程 | ✅ | Toolbar → 打开按钮 | - |
| 运行流程 | ✅ | Toolbar → 运行按钮 | - |
| 停止流程 | ✅ | Toolbar → 停止按钮 | - |
| 放大视图 | ✅ | Toolbar → 放大按钮 | - |
| 缩小视图 | ✅ | Toolbar → 缩小按钮 | - |
| 拖放节点 | ✅ | NodePalette → 拖到画布 | - |
| 连接节点 | ✅ | 拖动节点端点 | - |
| 编辑属性 | ✅ | PropertiesPanel | - |
| 动态配置 | ✅ | PropertiesPanel → 配置参数 | - |

### 组件架构

```
App.tsx (主布局)
├── Toolbar.tsx (工具栏)
│   ├── 运行/停止控制
│   ├── 保存/打开模态框
│   └── 缩放控制
├── NodePalette.tsx (节点面板)
│   ├── 搜索节点
│   ├── 分类显示
│   └── 拖放支持
├── FlowEditor.tsx (画布)
│   ├── React Flow 集成
│   ├── 拖放处理
│   ├── 节点/边管理
│   └── MiniMap/Controls
├── PropertiesPanel.tsx (属性面板)
│   ├── 基础属性编辑
│   └── 动态配置表单
└── StatusBar.tsx (状态栏)
```

### 状态管理 (Zustand)

**flowStore.ts**
```typescript
{
  nodes: Node[]                    // 所有节点
  edges: Edge[]                    // 所有连接
  selectedNode: Node | null        // 当前选中节点
  reactFlowInstance: any | null    // React Flow 实例
  
  // 方法
  onNodesChange()                  // 节点变化处理
  onEdgesChange()                  // 边变化处理
  addNode()                        // 添加节点
  updateNode()                     // 更新节点数据
  deleteNode()                     // 删除节点
  selectNode()                     // 选择节点
  setNodes()                       // 批量设置节点
  setEdges()                       // 批量设置边
  setReactFlowInstance()           // 设置实例
}
```

### API 接口

**services/api.ts**
```typescript
// 节点管理
getNodes(): Promise<NodeDefinition[]>

// 流程管理
submitFlow(config: FlowConfig): Promise<{ pipeline_id: string }>
getAllJobs(): Promise<Job[]>

// 执行控制
startJob(jobId: string): Promise<{ status: string, message: string }>
stopJob(jobId: string, duration?: string): Promise<{ status: string, message: string }>

// 日志查询
getJobLogs(jobId: string, offset?: number): Promise<JobLogs>

// 健康检查
healthCheck(): Promise<any>
```

## 📝 使用指南

### 1. 创建新流程

1. 从左侧 NodePalette 拖动节点到画布
2. 拖动节点端点创建连接
3. 点击节点查看/编辑属性
4. 在右侧 PropertiesPanel 配置参数

### 2. 保存流程

1. 点击工具栏 "保存" 按钮
2. 输入流程名称（必填）
3. 输入流程描述（可选）
4. 点击确认
5. 查看成功消息中的 Pipeline ID

### 3. 加载流程

1. 点击工具栏 "打开" 按钮
2. 在列表中选择要加载的流程
3. 点击流程右侧的 "打开" 按钮
4. 等待画布渲染完成

### 4. 运行流程

1. 确保流程已保存或画布有节点
2. 点击工具栏 "运行" 按钮
3. 观察节点状态变为绿色（运行中）
4. 等待执行完成

### 5. 停止流程

1. 在流程运行时点击 "停止" 按钮
2. 确认节点状态重置为灰色（空闲）

### 6. 编辑节点属性

1. 单击选中节点
2. 在右侧属性面板编辑：
   - 节点名称
   - 描述信息
   - 配置参数
   - 启用/禁用开关
3. 更改实时保存到节点数据

### 7. 画布操作

- **平移**: 鼠标左键拖动空白区域
- **缩放**: 
  - 鼠标滚轮
  - 工具栏放大/缩小按钮
  - Controls 面板
- **多选**: Shift + 鼠标框选（待实现）
- **删除**: 选中节点后按 Delete 键

## 🔧 开发者参考

### 添加新节点类型

1. 后端注册节点定义
2. 前端自动从 API 加载
3. （可选）在 PropertiesPanel 添加配置定义

### 添加新配置项

在 `PropertiesPanel.tsx` 中更新 `getNodeConfig()`:

```typescript
const getNodeConfig = () => {
  return {
    your_node_type: [
      { 
        name: 'param_name',
        label: '参数名称',
        type: 'text|textarea|number|select',
        defaultValue: '默认值',
        options: ['选项1', '选项2']  // 仅 select 类型
      }
    ]
  }
}
```

支持的配置类型：
- `text`: 单行文本输入
- `textarea`: 多行文本输入
- `number`: 数字输入（带加减按钮）
- `select`: 下拉选择（需要 options）

### 扩展节点状态

在 `CustomNode.tsx` 中添加新状态样式：

```typescript
const statusColors = {
  idle: 'text-gray-400',
  running: 'text-green-500',
  success: 'text-green-600',
  error: 'text-red-500',
  // 添加新状态
  warning: 'text-yellow-500',
}
```

### 调试技巧

1. **查看节点数据**:
   ```javascript
   const nodes = useFlowStore.getState().nodes
   console.log(nodes)
   ```

2. **查看选中节点**:
   ```javascript
   const selected = useFlowStore.getState().selectedNode
   console.log(selected)
   ```

3. **手动操作画布**:
   ```javascript
   const instance = useFlowStore.getState().reactFlowInstance
   instance?.fitView()
   instance?.zoomIn()
   instance?.zoomOut()
   ```

## 🐛 故障排除

### 保存失败

**问题**: 点击保存后提示错误

**解决方案**:
1. 检查后端服务是否运行 (localhost:8080)
2. 检查浏览器控制台网络请求
3. 确认画布上至少有一个节点
4. 查看错误消息详情

### 节点不显示

**问题**: 拖放后节点没有出现在画布上

**解决方案**:
1. 检查 FlowEditor 是否正确初始化
2. 查看浏览器控制台是否有错误
3. 确认 addNode 方法被调用
4. 检查节点位置是否在可见区域

### 属性面板不更新

**问题**: 修改属性后节点数据没有变化

**解决方案**:
1. 确认 updateNode 方法正确调用
2. 检查 selectedNode 是否同步更新
3. 查看 flowStore 中的数据是否正确
4. 重新选择节点刷新属性面板

### 流程无法运行

**问题**: 点击运行按钮没有反应

**解决方案**:
1. 确认画布上有节点
2. 检查后端 API 是否可达
3. 查看 submitFlow 和 startJob 返回结果
4. 检查节点是否有必需的配置参数

## 📚 相关文档

- [PHASE2_GUIDE.md](./docs/PHASE2_GUIDE.md) - Phase 2 完整指南
- [CHANGELOG.md](./CHANGELOG.md) - 详细更新日志
- [README.md](./README.md) - 项目概览

## 🚀 下一步计划

1. ⏳ 实现状态轮询（自动更新节点状态）
2. ⏳ 从后端获取动态节点配置
3. ⏳ 添加撤销/重做功能
4. ⏳ 实现键盘快捷键
5. ⏳ 添加流程验证逻辑

---

**最后更新**: 2025-01-14  
**版本**: v2.0 (Phase 2 完成)

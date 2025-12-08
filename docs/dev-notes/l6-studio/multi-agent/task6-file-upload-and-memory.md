# Task 6: 文件上传与记忆集成

## 目标
实现用户文件上传功能，并将上传的文件和对话历史集成到 SAGE 的记忆系统（sage-memory）中。

## 背景
SAGE Studio 需要支持用户上传自定义文档（PDF, MD, TXT 等）作为知识库的一部分。同时，Studio 需要与 `sage-memory` 集成，以支持长短期记忆、向量检索等功能。

## 任务详情

### 1. 文件上传服务 (File Upload Service)
**文件位置**: `packages/sage-studio/src/sage/studio/services/file_upload_service.py`

- **功能**:
  - 接收前端上传的文件
  - 验证文件类型和大小
  - 保存到 `~/.local/share/sage/studio/uploads/`
  - 生成文件元数据（ID, 文件名, 大小, 上传时间, 路径）
  - (可选) 触发后台索引任务

- **接口定义**:
  ```python
  class FileUploadService:
      async def upload_file(self, file: UploadFile) -> FileMetadata: ...
      def list_files(self) -> List[FileMetadata]: ...
      def get_file_path(self, file_id: str) -> Path: ...
      def delete_file(self, file_id: str) -> bool: ...
  ```

### 2. 记忆集成服务 (Memory Integration Service)
**文件位置**: `packages/sage-studio/src/sage/studio/services/memory_integration.py`

- **功能**:
  - 封装与 `sage-memory` (或 Gateway 记忆端点) 的交互
  - 提供 `add_context(session_id, message)` 接口
  - 提供 `get_context(session_id, query)` 接口
  - 提供 `index_document(file_path)` 接口 (用于 RAG)

- **注意**:
  - 如果 `sage-memory` 包不存在，请在 `sage.studio.adapters` 中定义一个 `MemoryAdapter` 接口，并提供一个基于本地文件/向量库的默认实现。
  - 优先检查 `sage.common` 或 `sage.libs` 中是否有现成的记忆组件。

### 3. 后端 API 更新
**文件位置**: `packages/sage-studio/src/sage/studio/config/backend/api.py`

- **新增端点**:
  - `POST /api/uploads`: 上传文件
  - `GET /api/uploads`: 获取文件列表
  - `DELETE /api/uploads/{file_id}`: 删除文件
  - `GET /api/chat/memory/config`: 获取记忆配置 (对接 MemorySettings)
  - `GET /api/chat/memory/stats`: 获取记忆统计

### 4. 前端组件
**文件位置**: `packages/sage-studio/src/sage/studio/frontend/src/components/FileUpload.tsx`

- **功能**:
  - 使用 Ant Design Upload 组件
  - 展示已上传文件列表
  - 支持拖拽上传

**更新**: `packages/sage-studio/src/sage/studio/frontend/src/components/ChatMode.tsx`
- 在侧边栏或输入框附近添加 "上传知识库" 按钮
- 集成 `FileUpload` 组件

## 依赖
- `python-multipart` (用于文件上传)
- `shutil` (文件操作)

## 验证
- 上传一个 PDF 文件，确认出现在 `~/.local/share/sage/studio/uploads/`
- 调用 `list_files` API 确认返回正确元数据
- (后续) 确认 KnowledgeManager 能读取这些文件

"""
SAGE Gateway FastAPI Server

提供 OpenAI/Anthropic 兼容的 REST API
"""

# pyright: reportMissingImports=false

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from sage.gateway.adapters import ChatCompletionRequest, OpenAIAdapter
from sage.gateway.session import get_session_manager
from pydantic import BaseModel

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sage.gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 SAGE Gateway starting...")
    yield
    logger.info("👋 SAGE Gateway shutting down...")


# 创建 FastAPI 应用
app = FastAPI(
    title="SAGE Gateway",
    description="OpenAI/Anthropic compatible API gateway for SAGE framework",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置（允许 sage-studio 调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # NOTE: 生产环境应配置具体的允许域名列表
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化适配器
openai_adapter = OpenAIAdapter()
session_manager = get_session_manager()


class SessionCreatePayload(BaseModel):
    title: str | None = None


class SessionTitlePayload(BaseModel):
    title: str


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "SAGE Gateway",
        "version": "0.1.0",
        "endpoints": [
            "/v1/chat/completions",
            "/health",
            "/sessions",
            "/admin/index/status",
            "/admin/index/build",
        ],
    }


@app.get("/health")
async def health():
    """健康检查"""
    stats = session_manager.get_stats()
    return {
        "status": "healthy",
        "sessions": stats,
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI 兼容的 chat completions 端点

    支持：
    - 非流式响应 (stream=false)
    - 流式响应 (stream=true, SSE)
    - 会话管理 (session_id)
    """
    try:
        logger.info(f"Chat request: model={request.model}, stream={request.stream}")

        response = await openai_adapter.chat_completions(request)

        if request.stream:
            # 流式响应（SSE）
            return StreamingResponse(
                response,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        else:
            # 非流式响应
            return response

    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions")
async def list_sessions():
    """列出所有会话"""
    return {
        "sessions": session_manager.list_sessions(),
        "stats": session_manager.get_stats(),
    }


@app.post("/sessions")
async def create_session(payload: SessionCreatePayload):
    """创建新的会话"""
    session = session_manager.create_session(title=payload.title)
    return session.to_dict()


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话详情"""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@app.post("/sessions/{session_id}/clear")
async def clear_session(session_id: str):
    """清空会话历史"""
    if not session_manager.clear_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "cleared", "session_id": session_id}


@app.patch("/sessions/{session_id}/title")
async def update_session_title(session_id: str, payload: SessionTitlePayload):
    """更新会话标题"""
    if not session_manager.rename_session(session_id, payload.title):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "updated", "session_id": session_id, "title": payload.title}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    success = session_manager.delete(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}


@app.post("/sessions/cleanup")
async def cleanup_sessions(max_age_minutes: int = 30):
    """清理过期会话"""
    count = session_manager.cleanup_expired(max_age_minutes)
    return {
        "status": "cleaned",
        "removed_sessions": count,
    }


# ==================== Index Management APIs ====================


class IndexBuildPayload(BaseModel):
    """索引构建请求"""

    source_dir: str | None = None  # 源文档目录，默认使用 docs-public/docs_src
    force_rebuild: bool = False  # 强制重建（即使已存在）


@app.get("/admin/index/status")
async def get_index_status():
    """获取索引状态

    Returns:
        索引的元数据信息，包括文档数、chunk数、创建时间等
    """
    from pathlib import Path
    import json

    index_dir = Path.home() / ".sage" / "vector_db"
    manifest_path = index_dir / "manifest.json"

    if not manifest_path.exists():
        return {
            "status": "not_found",
            "message": "RAG index has not been built yet",
        }

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)

        return {
            "status": "ready",
            "index": manifest,
        }
    except Exception as e:
        logger.error(f"Failed to load index manifest: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load index: {str(e)}")


@app.post("/admin/index/build")
async def build_index(payload: IndexBuildPayload):
    """触发索引构建

    Args:
        payload: 包含 source_dir 和 force_rebuild 选项

    Returns:
        构建结果和索引元数据
    """
    from pathlib import Path
    import json

    index_dir = Path.home() / ".sage" / "vector_db"
    manifest_path = index_dir / "manifest.json"

    # Check if index exists and force_rebuild is False
    if manifest_path.exists() and not payload.force_rebuild:
        with open(manifest_path) as f:
            existing_manifest = json.load(f)

        return {
            "status": "already_exists",
            "message": "Index already exists. Use force_rebuild=true to rebuild.",
            "index": existing_manifest,
        }

    # Determine source directory
    if payload.source_dir:
        source_dir = Path(payload.source_dir)
    else:
        # Auto-detect
        from sage.common.config.output_paths import find_sage_project_root

        project_root = find_sage_project_root()
        if project_root:
            source_dir = project_root / "docs-public" / "docs_src"
        else:
            source_dir = Path.cwd() / "docs-public" / "docs_src"
            if not source_dir.exists():
                source_dir = Path.home() / "SAGE" / "docs-public" / "docs_src"

    if not source_dir.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Source directory not found: {source_dir}",
        )

    try:
        # Clear existing index if force_rebuild
        if payload.force_rebuild and index_dir.exists():
            import shutil

            shutil.rmtree(index_dir)
            logger.info(f"Removed existing index at {index_dir}")

        # Build index (reuse adapter's method)
        openai_adapter._build_index_from_docs(source_dir, index_dir)

        # Load manifest
        with open(manifest_path) as f:
            manifest = json.load(f)

        return {
            "status": "built",
            "message": "Index built successfully",
            "index": manifest,
        }

    except Exception as e:
        logger.error(f"Failed to build index: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to build index: {str(e)}")


@app.delete("/admin/index")
async def delete_index():
    """删除索引

    Returns:
        删除结果
    """
    from pathlib import Path
    import shutil

    index_dir = Path.home() / ".sage" / "vector_db"

    if not index_dir.exists():
        return {
            "status": "not_found",
            "message": "No index to delete",
        }

    try:
        shutil.rmtree(index_dir)
        logger.info(f"Deleted index at {index_dir}")

        return {
            "status": "deleted",
            "message": f"Index deleted: {index_dir}",
        }

    except Exception as e:
        logger.error(f"Failed to delete index: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete index: {str(e)}")


# ==================== Main Entry Point ====================


def main():
    """主入口"""
    import uvicorn

    logger.info("Starting SAGE Gateway server...")
    uvicorn.run(
        "sage.gateway.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

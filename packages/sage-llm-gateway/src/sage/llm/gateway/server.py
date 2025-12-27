"""
SAGE Gateway FastAPI Server

提供 OpenAI/Anthropic 兼容的 REST API，并集成 Control Plane 管理功能。

Key Features:
- OpenAI 兼容的 /v1/chat/completions 端点
- 会话管理 (Session Management)
- RAG 索引管理
- Control Plane 引擎管理 (/v1/management/*)
"""

# pyright: reportMissingImports=false

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from sage.common.config.ports import SagePorts
from sage.llm.gateway.adapters import ChatCompletionRequest, OpenAIAdapter
from sage.llm.gateway.routes.engine_control_plane import (
    control_plane_router as engine_control_plane_router,
)
from sage.llm.gateway.routes.engine_control_plane import (
    get_control_plane_manager,
    init_control_plane,
    start_control_plane,
    stop_control_plane,
)
from sage.llm.gateway.routes.studio import studio_router
from sage.llm.gateway.session import get_session_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("sage.llm.gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 SAGE Gateway starting...")

    # Initialize and start Control Plane if enabled
    enable_control_plane = os.getenv("SAGE_GATEWAY_ENABLE_CONTROL_PLANE", "true").lower() == "true"
    if enable_control_plane:
        scheduling_policy = os.getenv("SAGE_GATEWAY_SCHEDULING_POLICY", "adaptive")
        if init_control_plane(scheduling_policy=scheduling_policy):
            await start_control_plane()
            logger.info("✅ Control Plane enabled")
        else:
            logger.warning("⚠️ Control Plane initialization failed, continuing without it")

    yield

    # Stop Control Plane on shutdown
    if enable_control_plane:
        await stop_control_plane()

    logger.info("👋 SAGE Gateway shutting down...")


# 创建 FastAPI 应用
app = FastAPI(
    title="SAGE Gateway",
    description="OpenAI/Anthropic compatible API gateway for SAGE framework",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def api_prefix_middleware(request: Request, call_next):
    """
    Middleware to handle /api prefix for Gateway routes.

    In some deployment scenarios (e.g. production without Vite proxy),
    requests might reach the Gateway with /api prefix (e.g. /api/v1/chat/completions).
    We strip this prefix for specific Gateway routes to ensure they match.
    """
    path = request.url.path
    if path.startswith("/api/v1/") or path.startswith("/api/sessions") or path == "/api/health":
        request.scope["path"] = path.replace("/api", "", 1)

    response = await call_next(request)
    return response


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

# 挂载 Control Plane 管理路由
app.include_router(engine_control_plane_router)
# 挂载 Studio Backend 路由（原 Studio Backend 服务现合并到 Gateway）
app.include_router(studio_router)


class SessionCreatePayload(BaseModel):
    title: str | None = None


class SessionTitlePayload(BaseModel):
    title: str


class MemoryConfigPayload(BaseModel):
    """记忆配置"""

    backend: str  # short_term, vdb, kv, graph
    max_dialogs: int | None = None  # 短期记忆窗口大小
    embedding_model: str | None = None  # VDB 嵌入模型
    embedding_dim: int | None = None  # VDB 向量维度
    index_type: str | None = None  # KV 索引类型


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "SAGE Gateway",
        "version": "0.1.0",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "embeddings": "/v1/embeddings",
            "health": "/health",
            "sessions": "/sessions",
            "index": {
                "status": "/admin/index/status",
                "build": "/admin/index/build",
            },
            "control_plane": {
                "engines": "/v1/management/engines",
                "start_engine": "POST /v1/management/engines",
                "register_engine": "POST /v1/management/engines/register",
                "stop_engine": "DELETE /v1/management/engines/{engine_id}",
                "status": "/v1/management/status",
                "backends": "/v1/management/backends",
                "gpu": "/v1/management/gpu",
            },
        },
    }


@app.get("/health")
async def health():
    """健康检查"""
    stats = session_manager.get_stats()
    return {
        "status": "healthy",
        "sessions": stats,
    }


@app.get("/v1/models")
async def list_models():
    """
    OpenAI-compatible models endpoint.
    Returns list of available models from Control Plane.
    """
    manager = get_control_plane_manager()
    models = []

    if manager:
        # Get status which includes engines
        status = manager.get_cluster_status()
        engines = status.get("engines", []) or status.get("engine_instances", [])

        seen_models = set()
        for engine in engines:
            # Support both dict and object access if needed, though usually dict here
            if isinstance(engine, dict):
                model_id = engine.get("model_id") or engine.get("model_name")
            else:
                model_id = getattr(engine, "model_id", None)

            if model_id and model_id not in seen_models:
                # Filter out embedding models
                runtime = (
                    engine.get("runtime")
                    if isinstance(engine, dict)
                    else getattr(engine, "runtime", None)
                )
                if runtime == "embedding":
                    continue

                seen_models.add(model_id)
                models.append(
                    {
                        "id": model_id,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "sage",
                    }
                )

    return {"object": "list", "data": models}


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


class EmbeddingRequest(BaseModel):
    """OpenAI 兼容的 Embedding 请求"""

    input: str | list[str]
    model: str | None = None
    encoding_format: str = "float"


@app.post("/v1/embeddings")
async def create_embeddings(request: EmbeddingRequest):
    """
    OpenAI 兼容的 embeddings 端点

    通过 Control Plane 将请求路由到可用的 Embedding 后端。
    """
    import httpx

    try:
        # 获取 Control Plane manager
        manager = get_control_plane_manager()
        if manager is None:
            raise HTTPException(
                status_code=503,
                detail="Control Plane not initialized. Start Gateway with --control-plane",
            )

        # 获取可用的 embedding 后端
        backends_info = manager.get_registered_backends()
        embedding_backends = backends_info.get("embedding_backends", [])

        if not embedding_backends:
            raise HTTPException(
                status_code=503,
                detail="No embedding backend available",
            )

        # 选择第一个健康的后端
        backend = None
        for b in embedding_backends:
            if b.get("healthy", False):
                backend = b
                break

        if not backend:
            # 如果没有健康的，使用第一个
            backend = embedding_backends[0]

        # 构建后端 URL
        host = backend.get("host", "localhost")
        port = backend.get("port", 8090)
        backend_url = f"http://{host}:{port}/v1/embeddings"

        logger.info(f"Proxying embedding request to {backend_url}")

        # 代理请求到后端
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                backend_url,
                json={
                    "input": request.input,
                    "model": request.model or backend.get("model_id", "default"),
                    "encoding_format": request.encoding_format,
                },
            )
            response.raise_for_status()
            return response.json()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing embedding request: {e}", exc_info=True)
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


# ==================== Memory Configuration APIs ====================


@app.get("/memory/config")
async def get_memory_config():
    """获取当前记忆配置

    Returns:
        当前的记忆后端类型和配置
    """
    return {
        "backend": session_manager._memory_backend,
        "max_dialogs": session_manager._max_memory_dialogs,
        "config": session_manager._memory_config,
        "available_backends": ["short_term", "vdb", "kv", "graph"],
    }


@app.get("/memory/stats")
async def get_memory_stats():
    """获取记忆统计信息

    Returns:
        各会话的记忆使用情况
    """
    stats = {}
    for session_id, memory_service in session_manager._memory_services.items():
        if session_manager._memory_backend == "short_term":
            # 短期记忆统计
            stats[session_id] = {
                "backend": "short_term",
                "dialog_count": len(memory_service.dialog_queue),
                "max_dialogs": memory_service.max_dialog,
                "usage_percent": (
                    len(memory_service.dialog_queue) / memory_service.max_dialog * 100
                    if memory_service.max_dialog > 0
                    else 0
                ),
            }
        else:
            # neuromem collection 统计
            stats[session_id] = {
                "backend": session_manager._memory_backend,
                "collection_name": getattr(memory_service, "name", "unknown"),
                "has_index": hasattr(memory_service, "_gateway_index_name"),
            }

    return {
        "total_sessions": len(stats),
        "sessions": stats,
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
    import json
    from pathlib import Path

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
    import json
    from pathlib import Path

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
    import shutil
    from pathlib import Path

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

    # Support environment variable configuration
    host = os.getenv("SAGE_GATEWAY_HOST", "0.0.0.0")
    port = int(os.getenv("SAGE_GATEWAY_PORT", str(SagePorts.GATEWAY_DEFAULT)))

    logger.info(f"Starting SAGE Gateway server on {host}:{port}...")
    uvicorn.run(
        "sage.llm.gateway.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()

"""
SAGE Frontend FastAPI Application

This module provides the main FastAPI application for the SAGE Web UI.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn


def _load_version():
    """加载版本信息"""
    try:
        # 尝试从本地包的版本文件加载
        from sage.common._version import __version__
        return __version__
    except ImportError:
        # 如果本地版本文件不存在，返回默认值
        return '0.1.3'


# 创建 FastAPI 应用
app = FastAPI(
    title="SAGE Web UI",
    description="SAGE Framework Web 管理界面，提供 API 文档、系统监控和基础管理功能",
    version=_load_version(),
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径，返回欢迎页面"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SAGE Web UI</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 0; 
                   background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                   min-height: 100vh; display: flex; justify-content: center; align-items: center; }
            .container { background: white; padding: 2rem; border-radius: 10px;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3); text-align: center;
                        max-width: 600px; width: 90%; }
            h1 { color: #333; margin-bottom: 1rem; }
            p { color: #666; line-height: 1.6; }
            .nav-links { margin-top: 2rem; }
            .nav-links a { display: inline-block; margin: 0 1rem; padding: 0.5rem 1rem;
                          background: #667eea; color: white; text-decoration: none;
                          border-radius: 5px; transition: background 0.3s; }
            .nav-links a:hover { background: #764ba2; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌟 欢迎使用 SAGE Web UI</h1>
            <p>SAGE (Streaming-Augmented Generative Execution) Framework Web 管理界面</p>
            <p>提供 API 文档、系统监控和基础管理功能</p>
            <div class="nav-links">
                <a href="/docs">📚 API 文档</a>
                <a href="/redoc">📖 ReDoc</a>
                <a href="/health">🏥 健康检查</a>
                <a href="/api/info">ℹ️ API 信息</a>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "SAGE Web UI", 
        "version": _load_version(),
        "timestamp": "2025-09-01"
    }


@app.get("/api/info")
async def api_info():
    """API 信息端点"""
    return {
        "name": "SAGE Web UI API",
        "version": _load_version(),
        "description": "SAGE Framework Web 管理界面 API",
        "author": "IntelliStream Team",
        "repository": "https://github.com/intellistream/SAGE"
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SAGE Web UI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()
    
    uvicorn.run(
        "sage.common.frontend.web_ui.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

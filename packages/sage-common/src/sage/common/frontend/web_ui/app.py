"""
SAGE Frontend FastAPI Application

This module provides the main FastAPI application for the SAGE Web UI.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn


# 创建 FastAPI 应用
app = FastAPI(
    title="SAGE Web UI",
    description="SAGE Framework Web 管理界面，提供 API 文档、系统监控和基础管理功能",
    version="0.1.0",
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
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .header {
                text-align: center;
                color: #333;
                margin-bottom: 30px;
            }
            .status {
                background: #e8f5e8;
                border: 1px solid #4caf50;
                border-radius: 5px;
                padding: 15px;
                margin: 20px 0;
            }
            .links {
                margin-top: 30px;
            }
            .links a {
                display: inline-block;
                margin: 10px 15px 10px 0;
                padding: 10px 20px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }
            .links a:hover {
                background: #0056b3;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌐 SAGE Web UI</h1>
                <p>Web 管理界面和 API 文档</p>
            </div>
            
            <div class="status">
                <strong>✅ 服务器运行正常</strong>
                <br>Version: 0.1.0
                <br>Author: IntelliStream Team
            </div>
            
            <div class="links">
                <h3>快速链接:</h3>
                <a href="/docs">📚 API 文档 (Swagger)</a>
                <a href="/redoc">📖 API 文档 (ReDoc)</a>
                <a href="/health">🔍 健康检查</a>
            </div>
            
            <div style="margin-top: 30px; color: #666; text-align: center;">
                <p>SAGE Framework - 数据处理管道管理和监控平台</p>
                <p><a href="https://github.com/intellistream/SAGE">GitHub Repository</a></p>
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
        "version": "0.1.0",
        "timestamp": "2025-08-11"
    }


@app.get("/api/info")
async def api_info():
    """API 信息端点"""
    return {
        "name": "SAGE Web UI API",
        "version": "0.1.0",
        "description": "SAGE Framework Web 管理界面 API",
        "author": "IntelliStream Team",
        "repository": "https://github.com/intellistream/SAGE"
    }


def start_server(host: str = "127.0.0.1", port: int = 8080, reload: bool = False):
    """启动服务器"""
    print(f"🚀 启动 SAGE Web UI...")
    print(f"📍 地址: http://{host}:{port}")
    print(f"📚 API文档: http://{host}:{port}/docs")
    print(f"🔍 健康检查: http://{host}:{port}/health")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    start_server()

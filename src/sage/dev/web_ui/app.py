"""
SAGE Frontend FastAPI Application

This module provides the main FastAPI application for the SAGE Web UI.
"""

import json
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from sage.common.config.ports import SagePorts


def _load_version():
    """加载版本信息"""
    try:
        # 尝试从本地包的版本文件加载
        from sage.common import __version__

        return __version__
    except ImportError:
        # 如果本地版本文件不存在，返回默认值
        return "0.1.3"


def _get_sage_dir():
    """获取 SAGE 目录路径"""
    # 首先检查环境变量
    env_dir = os.environ.get("SAGE_OUTPUT_DIR")
    if env_dir:
        sage_dir = Path(env_dir)
    else:
        # 检查是否在开发环境中
        current_dir = Path.cwd()
        if (current_dir / "packages" / "sage-common").exists():
            sage_dir = current_dir / ".sage"
        else:
            sage_dir = Path.home() / ".sage"

    sage_dir.mkdir(parents=True, exist_ok=True)
    return sage_dir


# Pydantic 模型定义
class Job(BaseModel):
    jobId: str
    name: str
    isRunning: bool
    nthreads: str
    cpu: str
    ram: str
    startTime: str
    duration: str
    nevents: int
    minProcessTime: int
    maxProcessTime: int
    meanProcessTime: int
    latency: int
    throughput: int
    ncore: int
    periodicalThroughput: list[int]
    periodicalLatency: list[int]
    totalTimeBreakdown: dict
    schedulerTimeBreakdown: dict
    operators: list[dict]


class OperatorInfo(BaseModel):
    id: int
    name: str
    description: str
    code: str
    isCustom: bool


# 创建 FastAPI 应用
app = FastAPI(
    title="SAGE Web UI",
    description="SAGE Framework Web 管理界面，提供 API 文档、系统监控和基础管理功能",
    version=_load_version(),
    docs_url="/docs",
    redoc_url="/redoc",
)


def _read_sage_data_from_files():
    """从 .sage 目录的文件中读取实际的 SAGE 数据"""
    sage_dir = _get_sage_dir()
    data = {"jobs": [], "operators": [], "pipelines": []}

    try:
        # 读取作业信息
        states_dir = sage_dir / "states"
        if states_dir.exists():
            for job_file in states_dir.glob("*.json"):
                try:
                    with open(job_file) as f:
                        job_data = json.load(f)
                        data["jobs"].append(job_data)
                except Exception as e:
                    print(f"Error reading job file {job_file}: {e}")

        # 读取操作符信息
        operators_file = sage_dir / "output" / "operators.json"
        if operators_file.exists():
            try:
                with open(operators_file) as f:
                    operators_data = json.load(f)
                    data["operators"] = operators_data
            except Exception as e:
                print(f"Error reading operators file: {e}")

        # 读取管道信息
        pipelines_file = sage_dir / "output" / "pipelines.json"
        if pipelines_file.exists():
            try:
                with open(pipelines_file) as f:
                    pipelines_data = json.load(f)
                    data["pipelines"] = pipelines_data
            except Exception as e:
                print(f"Error reading pipelines file: {e}")

    except Exception as e:
        print(f"Error reading SAGE data: {e}")

    return data


# 创建 FastAPI 应用
app = FastAPI(
    title="SAGE Web UI",
    description="SAGE Framework Web 管理界面，提供 API 文档、系统监控和基础管理功能",
    version=_load_version(),
    docs_url="/docs",
    redoc_url="/redoc",
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
        "timestamp": "2025-09-01",
    }


@app.get("/api/info")
async def api_info():
    """API 信息端点"""
    return {
        "name": "SAGE Web UI API",
        "version": _load_version(),
        "description": "SAGE Framework Web 管理界面 API",
        "author": "IntelliStream Team",
        "repository": "https://github.com/intellistream/SAGE",
    }


@app.get("/api/jobs/all", response_model=list[Job])
async def get_all_jobs():
    """获取所有作业信息"""
    try:
        sage_data = _read_sage_data_from_files()
        jobs = sage_data.get("jobs", [])

        # 如果没有实际数据，返回一些示例数据（用于开发）
        if not jobs:
            jobs = [
                {
                    "jobId": "job_001",
                    "name": "RAG问答管道",
                    "isRunning": True,
                    "nthreads": "4",
                    "cpu": "80%",
                    "ram": "2GB",
                    "startTime": "2025-08-18 10:30:00",
                    "duration": "00:45:12",
                    "nevents": 1000,
                    "minProcessTime": 10,
                    "maxProcessTime": 500,
                    "meanProcessTime": 150,
                    "latency": 200,
                    "throughput": 800,
                    "ncore": 4,
                    "periodicalThroughput": [750, 800, 820, 785, 810],
                    "periodicalLatency": [180, 200, 190, 210, 195],
                    "totalTimeBreakdown": {
                        "totalTime": 2712000,
                        "serializeTime": 50000,
                        "persistTime": 100000,
                        "streamProcessTime": 2500000,
                        "overheadTime": 62000,
                    },
                    "schedulerTimeBreakdown": {
                        "overheadTime": 50000,
                        "streamTime": 2600000,
                        "totalTime": 2712000,
                        "txnTime": 62000,
                    },
                    "operators": [
                        {
                            "id": 1,
                            "name": "FileSource",
                            "numOfInstances": 1,
                            "throughput": 800,
                            "latency": 50,
                            "explorationStrategy": "greedy",
                            "schedulingGranularity": "batch",
                            "abortHandling": "rollback",
                            "numOfTD": 10,
                            "numOfLD": 5,
                            "numOfPD": 2,
                            "lastBatch": 999,
                            "downstream": [2],
                        }
                    ],
                }
            ]

        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取作业信息失败: {str(e)}")


@app.get("/api/operators", response_model=list[OperatorInfo])
async def get_operators():
    """获取所有操作符信息"""
    try:
        sage_data = _read_sage_data_from_files()
        operators = sage_data.get("operators", [])

        # 如果没有实际数据，返回一些示例数据
        if not operators:
            operators = [
                {
                    "id": 1,
                    "name": "FileSource",
                    "description": "从文件读取数据的源操作符",
                    "code": "class FileSource:\n    def __init__(self, file_path):\n        self.file_path = file_path\n    \n    def read_data(self):\n        with open(self.file_path, 'r') as f:\n            return f.read()",
                    "isCustom": True,
                },
                {
                    "id": 2,
                    "name": "SimpleRetriever",
                    "description": "简单的检索操作符",
                    "code": "class SimpleRetriever:\n    def __init__(self, top_k=5):\n        self.top_k = top_k\n    \n    def retrieve(self, query):\n        return query[:self.top_k]",
                    "isCustom": True,
                },
            ]

        return operators
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取操作符信息失败: {str(e)}")


@app.get("/api/pipelines")
async def get_pipelines():
    """获取所有管道信息"""
    try:
        sage_data = _read_sage_data_from_files()
        pipelines = sage_data.get("pipelines", [])

        # 如果没有实际数据，返回一些示例数据
        if not pipelines:
            pipelines = [
                {
                    "id": "pipeline_001",
                    "name": "示例RAG管道",
                    "description": "演示RAG问答系统的数据处理管道",
                    "status": "running",
                    "operators": [
                        {
                            "id": "source1",
                            "type": "FileSource",
                            "config": {"file_path": "/data/documents.txt"},
                        },
                        {
                            "id": "retriever1",
                            "type": "SimpleRetriever",
                            "config": {"top_k": 5},
                        },
                        {
                            "id": "sink1",
                            "type": "TerminalSink",
                            "config": {"format": "json"},
                        },
                    ],
                    "connections": [
                        {"from": "source1", "to": "retriever1"},
                        {"from": "retriever1", "to": "sink1"},
                    ],
                }
            ]

        return {"pipelines": pipelines}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取管道信息失败: {str(e)}")


def start_server(host: str = "127.0.0.1", port: int | None = None, reload: bool = False):
    """启动服务器"""
    if port is None:
        port = SagePorts.GATEWAY_DEFAULT
    uvicorn.run(
        "sage.dev.web_ui.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAGE Web UI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument(
        "--port",
        type=int,
        default=SagePorts.GATEWAY_DEFAULT,
        help="Port to bind",
    )
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    uvicorn.run(
        "sage.dev.web_ui.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )

"""
from sage.common.utils.logging.custom_logger import CustomLogger
SAGE Studio Backend API

A simple FastAPI backend service that provides real SAGE data to the Studio frontend.
"""

import importlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


def _get_sage_dir() -> Path:
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
    periodicalThroughput: List[int]
    periodicalLatency: List[int]
    totalTimeBreakdown: dict
    schedulerTimeBreakdown: dict
    operators: List[dict]


class OperatorInfo(BaseModel):
    id: int
    name: str
    description: str
    code: str
    isCustom: bool


# 创建 FastAPI 应用
app = FastAPI(
    title="SAGE Studio Backend",
    description="Backend API service for SAGE Studio frontend",
    version="1.0.0",
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Studio 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
                    with open(job_file, "r") as f:
                        job_data = json.load(f)
                        data["jobs"].append(job_data)
                except Exception as e:
                    self.logger.info(f"Error reading job file {job_file}: {e}")

        # 读取操作符信息
        operators_file = sage_dir / "output" / "operators.json"
        if operators_file.exists():
            try:
                with open(operators_file, "r") as f:
                    operators_data = json.load(f)
                    data["operators"] = operators_data
            except Exception as e:
                self.logger.info(f"Error reading operators file: {e}")

        # 读取管道信息
        pipelines_file = sage_dir / "output" / "pipelines.json"
        if pipelines_file.exists():
            try:
                with open(pipelines_file, "r") as f:
                    pipelines_data = json.load(f)
                    data["pipelines"] = pipelines_data
            except Exception as e:
                self.logger.info(f"Error reading pipelines file: {e}")

    except Exception as e:
        self.logger.info(f"Error reading SAGE data: {e}")

    return data


@app.get("/")
async def root():
    """根路径"""
    return {"message": "SAGE Studio Backend API", "status": "running"}


@app.get("/api/jobs/all", response_model=List[Job])
async def get_all_jobs():
    """获取所有作业信息"""
    try:
        sage_data = _read_sage_data_from_files()
        jobs = sage_data.get("jobs", [])

        self.logger.info(f"DEBUG: Read {len(jobs)} jobs from files")
        self.logger.info(f"DEBUG: sage_data = {sage_data}")

        # 如果没有实际数据，返回一些示例数据（用于开发）
        if not jobs:
            self.logger.info("DEBUG: No real jobs found, using fallback data")
            jobs = [
                {
                    "jobId": "job_001",
                    "name": "RAG问答管道示例",
                    "isRunning": False,
                    "nthreads": "4",
                    "cpu": "0%",
                    "ram": "0GB",
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


def _get_studio_operators_dir() -> Path:
    """获取 Studio operators 数据目录路径"""
    current_file = Path(__file__)
    # 从 api.py 文件路径找到 studio 根目录:
    # ../../../ 从 backend/ 到 studio/
    studio_root = current_file.parent.parent.parent
    operators_dir = studio_root / "data" / "operators"
    return operators_dir


def _load_operator_class_source(module_path: str, class_name: str) -> str:
    """动态加载operator类并获取其源代码"""
    try:
        # 添加SAGE项目路径到sys.path
        sage_root = Path(__file__).parent.parent.parent.parent.parent.parent
        if str(sage_root) not in sys.path:
            sys.path.insert(0, str(sage_root))

        # 动态导入模块
        module = importlib.import_module(module_path)

        # 获取类
        operator_class = getattr(module, class_name)

        # 获取源代码
        source_code = inspect.getsource(operator_class)

        return source_code

    except Exception as e:
        self.logger.info(f"Error loading operator class {module_path}.{class_name}: {e}")
        return f"# Error loading source code for {class_name}\n# {str(e)}"


def _read_real_operators():
    """从 studio data 目录读取真实的操作符数据并动态加载源代码"""
    operators = []
    operators_dir = _get_studio_operators_dir()

    if not operators_dir.exists():
        self.logger.info(f"Operators directory not found: {operators_dir}")
        return []

    try:
        # 读取所有 JSON 文件
        for json_file in operators_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    operator_data = json.load(f)

                    # 检查是否有module_path和class_name字段
                    if "module_path" in operator_data and "class_name" in operator_data:
                        # 动态加载源代码
                        source_code = _load_operator_class_source(
                            operator_data["module_path"], operator_data["class_name"]
                        )
                        operator_data["code"] = source_code
                    else:
                        # 如果没有模块路径信息，使用空代码
                        operator_data["code"] = ""

                    # 确保数据格式正确
                    required_fields = ["id", "name", "description", "isCustom"]
                    if all(key in operator_data for key in required_fields):
                        # 清理不需要的字段
                        clean_data = {
                            "id": operator_data["id"],
                            "name": operator_data["name"],
                            "description": operator_data["description"],
                            "code": operator_data.get("code", ""),
                            "isCustom": operator_data["isCustom"],
                        }
                        operators.append(clean_data)
                        self.logger.info(f"Loaded operator: {operator_data['name']}")
                    else:
                        self.logger.info(f"Invalid operator data in {json_file}")

            except Exception as e:
                self.logger.info(f"Error reading operator file {json_file}: {e}")

    except Exception as e:
        self.logger.info(f"Error reading operators directory: {e}")

    return operators


@app.get("/api/operators", response_model=List[OperatorInfo])
async def get_operators():
    """获取所有操作符信息"""
    try:
        # 首先尝试读取真实的操作符数据
        operators = _read_real_operators()

        # 如果没有找到真实数据，使用后备数据
        if not operators:
            self.logger.info("No real operator data found, using fallback data")
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

        self.logger.info(f"Returning {len(operators)} operators")
        return operators
    except Exception as e:
        self.logger.info(f"Error in get_operators: {e}")
        raise HTTPException(status_code=500, detail=f"获取操作符信息失败: {str(e)}")


@app.get("/api/operators/list")
async def get_operators_list(page: int = 1, size: int = 10, search: str = ""):
    """获取操作符列表 - 支持分页和搜索"""
    try:
        # 获取所有操作符
        all_operators = _read_real_operators()

        # 如果没有找到真实数据，使用后备数据
        if not all_operators:
            self.logger.info("No real operator data found, using fallback data")
            all_operators = [
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

        # 搜索过滤
        if search:
            filtered_operators = [
                op
                for op in all_operators
                if search.lower() in op["name"].lower()
                or search.lower() in op["description"].lower()
            ]
        else:
            filtered_operators = all_operators

        # 分页计算
        total = len(filtered_operators)
        start = (page - 1) * size
        end = start + size
        items = filtered_operators[start:end]

        result = {"items": items, "total": total}

        self.logger.info(f"Returning page {page} with {len(items)} operators (total: {total})")
        return result

    except Exception as e:
        self.logger.info(f"Error in get_operators_list: {e}")
        raise HTTPException(status_code=500, detail=f"获取操作符列表失败: {str(e)}")


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


@app.post("/api/pipeline/submit")
async def submit_pipeline(topology_data: dict):
    """提交拓扑图/管道配置"""
    try:
        self.logger.info(f"Received pipeline submission: {topology_data}")

        # 这里可以添加保存到文件或数据库的逻辑
        sage_dir = _get_sage_dir()
        pipelines_dir = sage_dir / "pipelines"
        pipelines_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名（使用时间戳）
        import time

        timestamp = int(time.time())
        pipeline_file = pipelines_dir / f"pipeline_{timestamp}.json"

        # 保存拓扑数据到文件
        with open(pipeline_file, "w", encoding="utf-8") as f:
            json.dump(topology_data, f, indent=2, ensure_ascii=False)

        return {
            "status": "success",
            "message": "拓扑图提交成功",
            "pipeline_id": f"pipeline_{timestamp}",
            "file_path": str(pipeline_file),
        }
    except Exception as e:
        self.logger.info(f"Error submitting pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"提交拓扑图失败: {str(e)}")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "SAGE Studio Backend"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)

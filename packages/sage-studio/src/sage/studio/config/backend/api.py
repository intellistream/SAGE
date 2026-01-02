"""
SAGE Studio Backend API

A simple FastAPI backend service that provides real SAGE data to the Studio frontend.
"""

import importlib
import inspect
import ipaddress
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse, urlunparse

import requests
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from sage.common.config.ports import SagePorts
from sage.common.config.user_paths import get_user_data_dir as get_common_user_data_dir
from sage.studio.services.agent_orchestrator import get_orchestrator
from sage.studio.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AuthService,
    Token,
    User,
    UserCreate,
    get_auth_service,
)
from sage.studio.services.file_upload_service import get_file_upload_service
from sage.studio.services.memory_integration import get_memory_service
from sage.studio.services.stream_handler import get_stream_handler

# Gateway URL for API calls
# Use 127.0.0.1 instead of localhost to avoid IPv6 issues and ensure consistent behavior
GATEWAY_HOST = os.getenv("SAGE_GATEWAY_HOST", "127.0.0.1")
GATEWAY_BASE_URL = f"http://{GATEWAY_HOST}:{SagePorts.GATEWAY_DEFAULT}"

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    from sage.common.config import find_sage_project_root

    # Use centralized function to find project root
    repo_root = find_sage_project_root()
    if repo_root:
        env_file = repo_root / ".env"
        if env_file.exists():
            load_dotenv(env_file, override=True)  # override=True to ensure env vars are updated
            # Use logging instead of print for production
            import logging

            logging.info(f"Loaded environment variables from {env_file}")
        else:
            import logging

            logging.warning(f".env file not found at {env_file}")
    else:
        import logging

        logging.warning("Could not find SAGE project root, skipping .env loading")
except ImportError as e:
    import logging

    logging.warning(f"Failed to load environment: {e}")


def _convert_pipeline_to_job(
    pipeline_data: dict, pipeline_id: str, file_path: Path | None = None
) -> dict:
    """将拓扑图数据转换为 Job 格式"""
    from datetime import datetime

    # 从拓扑图数据中提取信息
    name = pipeline_data.get("name", f"拓扑图 {pipeline_id}")
    description = pipeline_data.get("description", "")
    nodes = pipeline_data.get("nodes", [])
    edges = pipeline_data.get("edges", [])

    # 创建操作符列表
    operators = []
    for i, node in enumerate(nodes):
        # 构建下游连接
        downstream = []
        for edge in edges:
            if edge.get("source") == node.get("id"):
                # 找到目标节点的索引
                target_node = next((n for n in nodes if n.get("id") == edge.get("target")), None)
                if target_node:
                    target_index = next(
                        (j for j, n in enumerate(nodes) if n.get("id") == edge.get("target")),
                        None,
                    )
                    if target_index is not None:
                        downstream.append(target_index)

        operator = {
            "id": i,
            "name": node.get("name", f"Operator_{i}"),
            "numOfInstances": 1,
            "downstream": downstream,
        }
        operators.append(operator)

    # 从文件名或文件元数据中提取创建时间
    create_time = None

    # 方法1: 从文件名解析时间戳 (pipeline_1759908680.json)
    if pipeline_id.startswith("pipeline_"):
        try:
            timestamp_str = pipeline_id.replace("pipeline_", "")
            timestamp = int(timestamp_str)
            create_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError) as e:
            print(f"Failed to parse timestamp from pipeline_id {pipeline_id}: {e}")

    # 方法2: 如果解析失败,使用文件的修改时间
    if create_time is None and file_path and file_path.exists():
        try:
            mtime = file_path.stat().st_mtime
            create_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Failed to get file mtime for {file_path}: {e}")

    # 方法3: 兜底使用当前时间
    if create_time is None:
        create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    job = {
        "jobId": pipeline_id,
        "name": name,
        "description": description,  # 添加描述字段
        "isRunning": False,  # 拓扑图默认不在运行
        "nthreads": "1",
        "cpu": "0%",
        "ram": "0GB",
        "startTime": create_time,
        "duration": "00:00:00",
        "nevents": 0,
        "minProcessTime": 0,
        "maxProcessTime": 0,
        "meanProcessTime": 0,
        "latency": 0,
        "throughput": 0,
        "ncore": 1,
        "periodicalThroughput": [0],
        "periodicalLatency": [0],
        "totalTimeBreakdown": {
            "totalTime": 0,
            "serializeTime": 0,
            "persistTime": 0,
            "streamProcessTime": 0,
            "overheadTime": 0,
        },
        "schedulerTimeBreakdown": {
            "overheadTime": 0,
            "streamTime": 0,
            "totalTime": 0,
            "txnTime": 0,
        },
        "operators": operators,
        # 添加 config 字段，保留原始的 React Flow 格式数据
        "config": {
            "name": name,
            "description": description,
            "nodes": nodes,
            "edges": edges,
        },
    }

    return job


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


def get_user_data_dir(user_id: str) -> Path:
    """Get user-specific data directory."""
    # Use the common user data dir as base
    base_dir = get_common_user_data_dir()
    user_dir = base_dir / "users" / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_user_pipelines_dir(user_id: str) -> Path:
    """Get user-specific pipelines directory."""
    pipelines_dir = get_user_data_dir(user_id) / "pipelines"
    pipelines_dir.mkdir(parents=True, exist_ok=True)
    return pipelines_dir


def get_user_sessions_dir(user_id: str) -> Path:
    """Get user-specific sessions directory."""
    sessions_dir = get_user_data_dir(user_id) / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


# Pydantic 模型定义
class Job(BaseModel):
    jobId: str
    name: str
    description: str | None = ""  # 添加描述字段
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
    config: dict | None = None  # 添加 config 字段，用于存储 React Flow 格式的节点和边数据


class ParameterConfig(BaseModel):
    """节点参数配置"""

    name: str
    label: str
    type: str  # text, textarea, number, select, password, json
    required: bool | None = False
    defaultValue: str | int | float | dict | list | None = None  # 支持 JSON 对象和数组
    placeholder: str | None = None
    description: str | None = None
    options: list[str] | None = None
    min: int | float | None = None
    max: int | float | None = None
    step: int | float | None = None


class OperatorInfo(BaseModel):
    id: int
    name: str
    description: str
    code: str
    isCustom: bool
    parameters: list[ParameterConfig] | None = []  # 添加参数配置字段


# Auth Dependency
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    username = auth_service.verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = auth_service.get_user(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return User(id=user.id, username=user.username, created_at=user.created_at)


# 创建 FastAPI 应用
app = FastAPI(
    title="SAGE Studio Backend",
    description="Backend API service for SAGE Studio frontend",
    version="1.0.0",
)

# 动态构建允许的来源列表
allowed_origins = [
    "http://localhost:5173",  # Vite 开发服务器默认端口
    "http://localhost:4173",  # Vite preview 服务器默认端口
    f"http://localhost:{SagePorts.STUDIO_FRONTEND}",
    f"http://127.0.0.1:{SagePorts.STUDIO_FRONTEND}",
    f"http://0.0.0.0:{SagePorts.STUDIO_FRONTEND}",
]

# 添加常用开发端口
for port in [5173, 4173, 35180]:
    if port != SagePorts.STUDIO_FRONTEND:
        allowed_origins.extend(
            [
                f"http://localhost:{port}",
                f"http://127.0.0.1:{port}",
                f"http://0.0.0.0:{port}",
            ]
        )

# 从环境变量添加额外来源
extra_origins = os.getenv("SAGE_STUDIO_ALLOWED_ORIGINS", "")
if extra_origins:
    allowed_origins.extend(
        [origin.strip() for origin in extra_origins.split(",") if origin.strip()]
    )

# 去重
allowed_origins = list(set(allowed_origins))

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Auth Endpoints
@app.post("/api/auth/register", response_model=User)
async def register(
    user: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    db_user = auth_service.get_user(user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return auth_service.create_user(user.username, user.password)


@app.post("/api/auth/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    # Strip whitespace from username to match registration behavior
    username = form_data.username.strip()
    user = auth_service.get_user(username)

    if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/auth/guest", response_model=Token)
async def login_guest(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    user = auth_service.create_guest_user()
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user


@app.post("/api/auth/logout")
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    if getattr(current_user, "is_guest", False):
        # Clean up guest data
        import shutil

        # Delete user from DB
        auth_service.delete_user(current_user.id)

        # Delete user data directory
        # Use the local get_user_data_dir function defined in this file
        user_dir = get_user_data_dir(str(current_user.id))
        if user_dir.exists():
            try:
                shutil.rmtree(user_dir)
            except Exception as e:
                print(f"Error deleting guest data: {e}")

    return {"message": "Successfully logged out"}


def _read_sage_data_from_files(user_id: str | None = None):
    """从 .sage 目录的文件中读取实际的 SAGE 数据"""
    # Global dir for system data
    global_sage_dir = _get_sage_dir()

    # User dir for user data
    if user_id:
        user_sage_dir = get_user_data_dir(user_id)
    else:
        user_sage_dir = global_sage_dir

    data = {"jobs": [], "operators": [], "pipelines": []}

    try:
        # 读取作业信息
        states_dir = user_sage_dir / "states"
        if states_dir.exists():
            for job_file in states_dir.glob("*.json"):
                try:
                    with open(job_file, encoding="utf-8") as f:
                        job_data = json.load(f)
                        data["jobs"].append(job_data)
                except Exception as e:
                    print(f"Error reading job file {job_file}: {e}")

        # 读取保存的拓扑图并转换为 Job 格式
        pipelines_dir = user_sage_dir / "pipelines"
        if pipelines_dir.exists():
            for pipeline_file in pipelines_dir.glob("pipeline_*.json"):
                try:
                    with open(pipeline_file, encoding="utf-8") as f:
                        pipeline_data = json.load(f)
                        # 将拓扑图转换为 Job 格式，传递文件路径以提取真实创建时间
                        job_from_pipeline = _convert_pipeline_to_job(
                            pipeline_data, pipeline_file.stem, pipeline_file
                        )
                        data["jobs"].append(job_from_pipeline)
                except Exception as e:
                    print(f"Error reading pipeline file {pipeline_file}: {e}")

        # 读取操作符信息
        operators_file = global_sage_dir / "output" / "operators.json"
        if operators_file.exists():
            try:
                with open(operators_file, encoding="utf-8") as f:
                    operators_data = json.load(f)
                    data["operators"] = operators_data
            except Exception as e:
                print(f"Error reading operators file: {e}")

        # 读取管道信息
        pipelines_file = global_sage_dir / "output" / "pipelines.json"
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


@app.get("/")
async def root():
    """根路径"""
    return {"message": "SAGE Studio Backend API", "status": "running"}


@app.get("/api/jobs/all", response_model=list[Job])
async def get_all_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """获取所有作业信息"""
    try:
        sage_data = _read_sage_data_from_files(user_id=str(current_user.id))
        jobs = sage_data.get("jobs", [])

        print(f"DEBUG: Read {len(jobs)} jobs from files for user {current_user.username}")
        print(f"DEBUG: sage_data = {sage_data}")

        # 如果没有实际数据，返回一些示例数据（用于开发）
        if not jobs:
            print("DEBUG: No real jobs found, using fallback data")
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
        sage_root = find_sage_project_root()
        if sage_root and str(sage_root) not in sys.path:
            sys.path.insert(0, str(sage_root))

        # 动态导入模块
        module = importlib.import_module(module_path)

        # 获取类
        operator_class = getattr(module, class_name)

        # 获取源代码
        source_code = inspect.getsource(operator_class)

        return source_code

    except Exception as e:
        print(f"Error loading operator class {module_path}.{class_name}: {e}")
        return f"# Error loading source code for {class_name}\n# {str(e)}"


def _read_real_operators():
    """从 studio data 目录读取真实的操作符数据并动态加载源代码"""
    operators = []
    operators_dir = _get_studio_operators_dir()

    if not operators_dir.exists():
        print(f"Operators directory not found: {operators_dir}")
        return []

    try:
        # 读取所有 JSON 文件
        for json_file in operators_dir.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
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
                            "parameters": operator_data.get("parameters", []),  # 添加参数配置
                        }
                        operators.append(clean_data)
                        print(
                            f"Loaded operator: {operator_data['name']} with {len(clean_data['parameters'])} parameters"
                        )
                    else:
                        print(f"Invalid operator data in {json_file}")

            except Exception as e:
                print(f"Error reading operator file {json_file}: {e}")

    except Exception as e:
        print(f"Error reading operators directory: {e}")

    return operators


@app.get("/api/operators", response_model=list[OperatorInfo])
async def get_operators():
    """获取所有操作符信息"""
    try:
        # 首先尝试读取真实的操作符数据
        operators = _read_real_operators()

        # 如果没有找到真实数据，使用后备数据
        if not operators:
            print("No real operator data found, using fallback data")
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

        print(f"Returning {len(operators)} operators")
        return operators
    except Exception as e:
        print(f"Error in get_operators: {e}")
        raise HTTPException(status_code=500, detail=f"获取操作符信息失败: {str(e)}")


@app.get("/api/operators/list")
async def get_operators_list(page: int = 1, size: int = 10, search: str = ""):
    """获取操作符列表 - 支持分页和搜索"""
    try:
        # 获取所有操作符
        all_operators = _read_real_operators()

        # 如果没有找到真实数据，使用后备数据
        if not all_operators:
            print("No real operator data found, using fallback data")
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

        print(f"Returning page {page} with {len(items)} operators (total: {total})")
        return result

    except Exception as e:
        print(f"Error in get_operators_list: {e}")
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
async def submit_pipeline(
    topology_data: dict,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """提交拓扑图/管道配置"""
    try:
        print(f"Received pipeline submission from {current_user.username}: {topology_data}")

        # 这里可以添加保存到文件或数据库的逻辑
        pipelines_dir = get_user_pipelines_dir(str(current_user.id))

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
        print(f"Error submitting pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"提交拓扑图失败: {str(e)}")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "SAGE Studio Backend"}


# ==================== 管道详情相关端点 ====================
# 用于支持前端 View Details 功能的占位符端点

# 全局状态存储（生产环境应使用数据库）
job_runtime_status = {}  # {job_id: {status, use_ray, isRunning, ...}}
job_logs = {}  # {job_id: [log_lines]}
job_configs_cache = {}  # {pipeline_id: yaml_config}
user_queries = {}  # {job_id: [(query, answer), ...]}


@app.get("/jobInfo/get/{job_id}")
async def get_job_detail(job_id: str):
    """获取作业详细信息 - 包含操作符拓扑结构"""
    try:
        # 首先尝试从已保存的数据中查找
        sage_data = _read_sage_data_from_files()
        jobs = sage_data.get("jobs", [])

        # 查找匹配的作业
        job = next((j for j in jobs if j.get("jobId") == job_id), None)

        if job:
            return job

        # 如果没有找到实际数据，返回占位符数据（用于开发）
        print(f"Job {job_id} not found in saved data, returning placeholder")
        return {
            "jobId": job_id,
            "name": f"管道 {job_id}",
            "isRunning": False,
            "nthreads": "4",
            "cpu": "0%",
            "ram": "0GB",
            "startTime": "2025-10-10 15:00:00",
            "duration": "00:00:00",
            "nevents": 0,
            "minProcessTime": 0,
            "maxProcessTime": 0,
            "meanProcessTime": 0,
            "latency": 0,
            "throughput": 0,
            "ncore": 4,
            "periodicalThroughput": [0],
            "periodicalLatency": [0],
            "totalTimeBreakdown": {
                "totalTime": 0,
                "serializeTime": 0,
                "persistTime": 0,
                "streamProcessTime": 0,
                "overheadTime": 0,
            },
            "schedulerTimeBreakdown": {
                "overheadTime": 0,
                "streamTime": 0,
                "totalTime": 0,
                "txnTime": 0,
            },
            "operators": [
                {
                    "id": 1,
                    "name": "FileSource",
                    "numOfInstances": 1,
                    "throughput": 0,
                    "latency": 0,
                    "explorationStrategy": "greedy",
                    "schedulingGranularity": "batch",
                    "abortHandling": "rollback",
                    "numOfTD": 0,
                    "numOfLD": 0,
                    "numOfPD": 0,
                    "lastBatch": 0,
                    "downstream": [2],
                },
                {
                    "id": 2,
                    "name": "TerminalSink",
                    "numOfInstances": 1,
                    "throughput": 0,
                    "latency": 0,
                    "explorationStrategy": "greedy",
                    "schedulingGranularity": "batch",
                    "abortHandling": "rollback",
                    "numOfTD": 0,
                    "numOfLD": 0,
                    "numOfPD": 0,
                    "lastBatch": 0,
                    "downstream": [],
                },
            ],
        }
    except Exception as e:
        print(f"Error getting job detail: {e}")
        raise HTTPException(status_code=500, detail=f"获取作业详情失败: {str(e)}")


@app.get("/api/signal/status/{job_id}")
async def get_job_status(job_id: str):
    """获取作业运行状态"""
    try:
        # 从内存中获取状态
        status = job_runtime_status.get(
            job_id,
            {
                "job_id": job_id,
                "status": "idle",
                "use_ray": False,
                "isRunning": False,
            },
        )
        return status
    except Exception as e:
        print(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=f"获取作业状态失败: {str(e)}")


@app.post("/api/signal/start/{job_id}")
async def start_job(job_id: str):
    """启动作业"""
    try:
        # 更新运行状态
        job_runtime_status[job_id] = {
            "job_id": job_id,
            "status": "running",
            "use_ray": False,
            "isRunning": True,
        }

        # 初始化日志
        if job_id not in job_logs:
            job_logs[job_id] = []

        job_logs[job_id].append(f"[SYSTEM] Job {job_id} started at 2025-10-10 15:30:00")

        return {"status": "success", "message": f"作业 {job_id} 已启动"}
    except Exception as e:
        print(f"Error starting job: {e}")
        raise HTTPException(status_code=500, detail=f"启动作业失败: {str(e)}")


@app.post("/api/signal/stop/{job_id}/{duration}")
async def stop_job(job_id: str, duration: str):
    """停止作业"""
    try:
        # 更新运行状态
        job_runtime_status[job_id] = {
            "job_id": job_id,
            "status": "stopped",
            "use_ray": False,
            "isRunning": False,
        }

        # 添加停止日志
        if job_id in job_logs:
            job_logs[job_id].append(f"[SYSTEM] Job {job_id} stopped after {duration}")

        return {"status": "success", "message": f"作业 {job_id} 已停止"}
    except Exception as e:
        print(f"Error stopping job: {e}")
        raise HTTPException(status_code=500, detail=f"停止作业失败: {str(e)}")


@app.get("/api/signal/sink/{job_id}")
async def get_job_logs(job_id: str, offset: int = 0):
    """获取作业日志（增量）"""
    try:
        # 获取该作业的日志
        logs = job_logs.get(job_id, [])

        # 如果是第一次请求（offset=0）且没有日志，返回种子消息
        if offset == 0 and len(logs) == 0:
            seed_line = (
                f"[SYSTEM] Console ready for {job_id}. Click Start or submit a FileSource query."
            )
            job_logs[job_id] = [seed_line]
            return {"offset": 1, "lines": [seed_line]}

        # 返回从 offset 开始的新日志
        new_logs = logs[offset:]
        new_offset = len(logs)

        return {"offset": new_offset, "lines": new_logs}
    except Exception as e:
        print(f"Error getting job logs: {e}")
        raise HTTPException(status_code=500, detail=f"获取作业日志失败: {str(e)}")


@app.get("/batchInfo/get/all/{job_id}/{operator_id}")
async def get_all_batches(job_id: str, operator_id: str):
    """获取操作符的所有批次信息"""
    try:
        # operator_id 可以是字符串（如 "s1", "r1"）或数字
        # 返回空数组作为占位符
        # 实际实现需要从 SAGE 运行时获取批次统计数据
        print(f"Getting batches for job={job_id}, operator={operator_id}")
        return []
    except Exception as e:
        print(f"Error getting batches: {e}")
        raise HTTPException(status_code=500, detail=f"获取批次信息失败: {str(e)}")


@app.get("/batchInfo/get/{job_id}/{batch_id}/{operator_id}")
async def get_batch_detail(job_id: str, batch_id: int, operator_id: str):
    """获取单个批次的详细信息"""
    try:
        # operator_id 可以是字符串（如 "s1", "r1"）或数字
        # 返回占位符批次数据
        return {
            "batchId": batch_id,
            "operatorId": operator_id,
            "processTime": 0,
            "tupleCount": 0,
            "timestamp": "2025-10-10 15:30:00",
        }
    except Exception as e:
        print(f"Error getting batch detail: {e}")
        raise HTTPException(status_code=500, detail=f"获取批次详情失败: {str(e)}")


@app.get("/jobInfo/config/{pipeline_id}")
async def get_pipeline_config(pipeline_id: str):
    """获取管道配置（YAML格式）"""
    try:
        # 尝试从缓存获取
        if pipeline_id in job_configs_cache:
            return {"config": job_configs_cache[pipeline_id]}

        # 返回默认配置模板
        default_config = """# SAGE Pipeline Configuration
name: Example RAG Pipeline
version: 1.0.0

operators:
  - name: FileSource
    type: source
    config:
      file_path: /data/documents.txt

  - name: SimpleRetriever
    type: retriever
    config:
      top_k: 5

  - name: TerminalSink
    type: sink
    config:
      output_path: /tmp/output.txt
"""
        return {"config": default_config}
    except Exception as e:
        print(f"Error getting pipeline config: {e}")
        raise HTTPException(status_code=500, detail=f"获取管道配置失败: {str(e)}")


@app.put("/jobInfo/config/update/{pipeline_id}")
async def update_pipeline_config(pipeline_id: str, config: dict):
    """更新管道配置"""
    try:
        # 保存配置到缓存
        config_yaml = config.get("config", "")
        job_configs_cache[pipeline_id] = config_yaml

        # 可选：保存到文件
        sage_dir = _get_sage_dir()
        config_dir = sage_dir / "configs"
        config_dir.mkdir(exist_ok=True)

        config_file = config_dir / f"{pipeline_id}.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(config_yaml)

        return {
            "status": "success",
            "message": "配置更新成功",
            "file_path": str(config_file),
        }
    except Exception as e:
        print(f"Error updating pipeline config: {e}")
        raise HTTPException(status_code=500, detail=f"更新管道配置失败: {str(e)}")


# ==================== Playground API ====================


def _load_flow_data(flow_id: str, user_id: str | None = None) -> dict | None:
    """加载 Flow 数据"""
    if user_id:
        pipelines_dir = get_user_pipelines_dir(user_id)
    else:
        sage_dir = _get_sage_dir()
        pipelines_dir = sage_dir / "pipelines"

    print(f"🔍 Looking for flow: {flow_id}")
    print(f"📁 Pipelines dir: {pipelines_dir}")
    print(f"📁 Pipelines dir exists: {pipelines_dir.exists()}")

    # 尝试加载 pipeline 文件
    flow_file = pipelines_dir / f"{flow_id}.json"
    print(f"📄 Flow file path: {flow_file}")
    print(f"📄 Flow file exists: {flow_file.exists()}")

    if flow_file.exists():
        with open(flow_file, encoding="utf-8") as f:
            data = json.load(f)
            print(f"✅ Loaded flow: {data.get('name', 'Unnamed')}")
            return data

    print("❌ Flow file not found")
    return None


def _convert_to_flow_definition(flow_data: dict, flow_id: str):
    """将前端 Flow 数据转换为 FlowDefinition"""
    import sys

    # 添加 sage-studio 到 Python 路径
    studio_root = find_sage_project_root()
    if studio_root:
        studio_path = studio_root / "packages" / "sage-studio"
        if str(studio_path) not in sys.path:
            sys.path.insert(0, str(studio_path))

    from sage.studio.models import (  # type: ignore[import-not-found]
        VisualConnection,
        VisualNode,
        VisualPipeline,
    )
    from sage.studio.services.node_registry import (  # type: ignore[import-not-found]
        convert_node_type_to_snake_case,
    )

    name = flow_data.get("name", "Unnamed Flow")
    description = flow_data.get("description", "")
    nodes_data = flow_data.get("nodes", [])
    edges_data = flow_data.get("edges", [])

    # 转换节点
    nodes = []
    for node_data in nodes_data:
        # 获取节点类型并转换为 snake_case
        node_id = node_data.get("data", {}).get("nodeId", "unknown")
        node_type = convert_node_type_to_snake_case(node_id)

        print(f"🔄 Converting node: {node_id} → {node_type}")

        node = VisualNode(
            id=node_data.get("id", ""),
            type=node_type,  # 使用转换后的类型
            label=node_data.get("data", {}).get("label", "Unnamed Node"),
            position=node_data.get("position", {"x": 0, "y": 0}),
            config=node_data.get("data", {}).get("properties", {}),
        )
        nodes.append(node)

    # 转换连接
    connections = []
    for edge_data in edges_data:
        connection = VisualConnection(
            id=edge_data.get("id", f"{edge_data.get('source')}-{edge_data.get('target')}"),
            source_node_id=edge_data.get("source", ""),
            source_port="output",  # 默认输出端口
            target_node_id=edge_data.get("target", ""),
            target_port="input",  # 默认输入端口
        )
        connections.append(connection)

    return VisualPipeline(
        id=flow_id,
        name=name,
        description=description,
        nodes=nodes,
        connections=connections,
    )


def _parse_execution_results(results, pipeline, execution_time):
    """
    解析执行结果,生成输出和步骤

    Args:
        results: Sink 收集的结果列表
        pipeline: VisualPipeline 定义
        execution_time: 执行时间

    Returns:
        tuple: (output_text, agent_steps)
    """
    from datetime import datetime

    agent_steps = []
    output_parts = []

    # 为每个节点生成步骤
    step_time = int(execution_time * 1000 / len(pipeline.nodes)) if pipeline.nodes else 0

    for idx, node in enumerate(pipeline.nodes, start=1):
        # 查找该节点的输出
        node_output = None
        if results and idx <= len(results):
            node_output = results[idx - 1]

        # 生成步骤
        agent_steps.append(
            AgentStep(
                step=idx,
                type="tool_call",
                content=f"✓ {node.label}",
                timestamp=datetime.now().isoformat(),
                duration=step_time,
                toolName=node.label,
                toolInput={"config": node.config},
                toolOutput={"result": str(node_output) if node_output else "完成"},
            )
        )

        # 收集输出
        if node_output:
            output_parts.append(f"## {node.label}\n{node_output}\n")

    # 生成最终输出
    if output_parts:
        output_text = "\n".join(output_parts)
    else:
        output_text = f"Pipeline 执行成功！\n\n总耗时: {execution_time:.2f}秒"

    return output_text, agent_steps


class PlaygroundExecuteRequest(BaseModel):
    """Playground 执行请求"""

    flowId: str
    input: str
    sessionId: str = "default"
    stream: bool = False


class AgentStep(BaseModel):
    """Agent 执行步骤"""

    step: int
    type: str  # reasoning, tool_call, response
    content: str
    timestamp: str
    duration: int | None = None
    toolName: str | None = None
    toolInput: dict | None = None
    toolOutput: dict | None = None


class PlaygroundExecuteResponse(BaseModel):
    """Playground 执行响应"""

    output: str
    status: str
    agentSteps: list[AgentStep] | None = None


@app.post("/api/playground/execute", response_model=PlaygroundExecuteResponse)
async def execute_playground(
    request: PlaygroundExecuteRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """执行 Playground Flow - 使用增强的 PipelineBuilder"""
    try:
        import sys
        import time

        # 添加 sage-studio 到 Python 路径
        studio_root = find_sage_project_root()
        if studio_root:
            studio_path = studio_root / "packages" / "sage-studio"
            if str(studio_path) not in sys.path:
                sys.path.insert(0, str(studio_path))

        from sage.studio.models import PipelineStatus
        from sage.studio.services import get_pipeline_builder

        print(f"\n{'=' * 60}")
        print("🎯 Playground 执行开始")
        print(f"   User: {current_user.username}")
        print(f"   Flow ID: {request.flowId}")
        print(f"   Session: {request.sessionId}")
        print(f"   Input: {request.input[:100]}...")
        print(f"{'=' * 60}\n")

        # 1. 加载 Flow 定义
        flow_data = _load_flow_data(request.flowId, user_id=str(current_user.id))
        if not flow_data:
            raise HTTPException(status_code=404, detail=f"Flow not found: {request.flowId}")

        # 2. 转换为 VisualPipeline
        visual_pipeline = _convert_to_flow_definition(flow_data, request.flowId)
        print(f"📊 Pipeline 节点数: {len(visual_pipeline.nodes)}")

        # 3. 🆕 使用增强的 PipelineBuilder (传入用户输入)
        builder = get_pipeline_builder()
        sage_env = builder.build(visual_pipeline, user_input=request.input)

        # 4. 执行并收集结果
        start_time = time.time()
        print("⚙️ 开始执行...")

        # 提交作业并等待完成
        sage_env.submit(autostop=True)

        execution_time = time.time() - start_time
        print(f"✅ 执行完成,耗时: {execution_time:.2f}秒\n")

        # 5. 🆕 收集执行结果
        from sage.libs.io.sink import RetriveSink

        results = []
        if hasattr(RetriveSink, "get_results"):
            results = RetriveSink.get_results()

        # 6. 🆕 解析结果并生成步骤
        output_text, agent_steps = _parse_execution_results(
            results, visual_pipeline, execution_time
        )

        print(f"📤 输出长度: {len(output_text)} 字符")
        print(f"📋 步骤数: {len(agent_steps)}")
        print(f"{'=' * 60}\n")

        return PlaygroundExecuteResponse(
            output=output_text,
            status=PipelineStatus.COMPLETED.value,
            agentSteps=agent_steps if agent_steps else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        print("\n❌ 执行出错:")
        print(traceback.format_exc())
        print(f"{'=' * 60}\n")

        return PlaygroundExecuteResponse(
            output=f"执行出错: {str(e)}", status="failed", agentSteps=None
        )


# ==================== MVP 增强功能 ====================


# 1. 节点输出预览
@app.get("/api/node/{flow_id}/{node_id}/output")
async def get_node_output(flow_id: str, node_id: str):
    """获取节点的输出数据"""
    try:
        # 从缓存或状态存储中获取节点输出
        # 这里简化实现，实际应该从 SAGE 运行时获取
        sage_dir = _get_sage_dir()
        states_dir = sage_dir / "states" / flow_id

        if not states_dir.exists():
            raise HTTPException(404, "Flow 尚未执行或输出不可用")

        # 查找节点输出文件
        output_file = states_dir / f"{node_id}_output.json"
        if not output_file.exists():
            raise HTTPException(404, "节点输出不可用")

        import json

        with open(output_file, encoding="utf-8") as f:
            output_data = json.load(f)

        return output_data
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting node output: {e}")
        raise HTTPException(500, f"获取节点输出失败: {str(e)}")


# 2. Flow 导入/导出
@app.get("/api/flows/{flow_id}/export")
async def export_flow(
    flow_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """导出 Flow 为 JSON 文件"""
    try:
        flow_data = _load_flow_data(flow_id, user_id=str(current_user.id))
        if not flow_data:
            raise HTTPException(404, f"Flow not found: {flow_id}")

        import json

        from fastapi.responses import Response

        # 添加导出元数据
        export_data = {
            "version": "1.0.0",
            "exportTime": str(datetime.now()),
            "flowId": flow_id,
            "flow": flow_data,
        }

        json_str = json.dumps(export_data, indent=2, ensure_ascii=False)

        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{flow_id}.sage-flow.json"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"导出失败: {str(e)}")


@app.post("/api/flows/import")
async def import_flow(
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    """导入 Flow JSON 文件"""
    try:
        import json
        from datetime import datetime

        # 读取上传的文件
        content = await file.read()
        import_data = json.loads(content)

        # 验证格式
        if "flow" not in import_data:
            raise HTTPException(400, "无效的 Flow 文件格式")

        flow_data = import_data["flow"]

        # 生成新的 flow_id
        timestamp = int(datetime.now().timestamp() * 1000)
        new_flow_id = f"pipeline_{timestamp}"

        # 保存到本地
        pipelines_dir = get_user_pipelines_dir(str(current_user.id))

        flow_file = pipelines_dir / f"{new_flow_id}.json"
        with open(flow_file, "w", encoding="utf-8") as f:
            json.dump(flow_data, f, indent=2, ensure_ascii=False)

        return {
            "flowId": new_flow_id,
            "name": flow_data.get("name", "Imported Flow"),
            "message": "Flow 导入成功",
        }
    except json.JSONDecodeError:
        raise HTTPException(400, "无效的 JSON 文件")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"导入失败: {str(e)}")


# 3. 环境变量管理
@app.get("/api/env")
async def get_env_vars():
    """获取环境变量"""
    try:
        sage_dir = _get_sage_dir()
        env_file = sage_dir / ".env.json"

        if not env_file.exists():
            return {}

        import json

        with open(env_file, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading env vars: {e}")
        return {}


@app.put("/api/env")
async def update_env_vars(vars: dict):
    """更新环境变量"""
    try:
        import json

        sage_dir = _get_sage_dir()
        env_file = sage_dir / ".env.json"

        # 加密敏感信息（简化实现，实际应使用加密库）
        with open(env_file, "w", encoding="utf-8") as f:
            json.dump(vars, f, indent=2, ensure_ascii=False)

        return {"message": "环境变量已更新"}
    except Exception as e:
        raise HTTPException(500, f"更新失败: {str(e)}")


@app.get("/api/logs/{flow_id}")
async def get_logs(flow_id: str, last_id: int = 0):
    """获取流程执行日志（增量获取）

    Args:
        flow_id: 流程ID
        last_id: 上次获取的最后一条日志ID，用于增量获取

    Returns:
        日志条目列表
    """
    try:
        sage_dir = _get_sage_dir()
        log_file = sage_dir / "logs" / f"{flow_id}.log"

        if not log_file.exists():
            return {"logs": [], "last_id": 0}

        # 读取日志文件
        logs = []
        with open(log_file, encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                if idx > last_id:  # 只返回新日志
                    # 简单的日志解析（格式: [timestamp] [level] [node_id] message）
                    try:
                        parts = line.strip().split("] ", 3)
                        if len(parts) >= 3:
                            timestamp = parts[0].replace("[", "")
                            level = parts[1].replace("[", "")
                            node_id = parts[2].replace("[", "") if len(parts) == 4 else None
                            message = parts[-1]

                            logs.append(
                                {
                                    "id": idx,
                                    "timestamp": timestamp,
                                    "level": level,
                                    "message": message,
                                    "nodeId": node_id,
                                }
                            )
                    except Exception:
                        # 解析失败，跳过这行
                        continue

        return {"logs": logs, "last_id": last_id + len(logs)}
    except Exception as e:
        raise HTTPException(500, f"获取日志失败: {str(e)}")


# ==================== Chat Mode API (新增) ====================


class ChatRequest(BaseModel):
    """Chat 模式请求"""

    message: str
    session_id: str | None = None
    model: str = "sage-default"
    stream: bool = False


class AgentChatRequest(BaseModel):
    """Agent 聊天请求"""

    message: str
    session_id: str
    history: list[dict[str, str]] | None = None
    route: str | None = None
    should_index: bool | None = None
    metadata: dict[str, Any] | None = None
    evidence: list[dict[str, Any]] | None = None


class ChatResponse(BaseModel):
    """Chat 模式响应"""

    content: str
    session_id: str
    timestamp: str


class ChatSessionSummary(BaseModel):
    """Chat 会话摘要"""

    id: str
    title: str
    created_at: str
    last_active: str
    message_count: int


class ChatSessionDetail(ChatSessionSummary):
    messages: list[dict]
    metadata: dict | None = None


class ChatSessionCreateRequest(BaseModel):
    title: str | None = None


class ChatSessionTitleUpdate(BaseModel):
    title: str


def _get_session_path(user_id: str, session_id: str) -> Path:
    return get_user_sessions_dir(user_id) / f"{session_id}.json"


def _load_session(user_id: str, session_id: str) -> dict | None:
    path = _get_session_path(user_id, session_id)
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading session {path}: {e}")
    return None


def _save_session(user_id: str, session_id: str, data: dict):
    path = _get_session_path(user_id, session_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.post("/api/chat/v1/chat/completions")
async def proxy_chat_completions(
    request: Request, current_user: Annotated[User, Depends(get_current_user)]
):
    """Proxy for OpenAI-compatible chat completions used by Studio frontend"""
    from datetime import datetime

    import httpx

    try:
        # Get the raw body
        body = await request.json()
        session_id = body.get("session_id")
        user_id = str(current_user.id)

        # Extract user message from request
        messages = body.get("messages", [])
        user_message_content = None
        if messages:
            # Get the last user message
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_message_content = msg.get("content")
                    break

        # Load or create session
        session_data = None
        if session_id:
            session_data = _load_session(user_id, session_id)

        if not session_data and session_id:
            # Create new session
            now = datetime.now().isoformat()
            session_data = {
                "id": session_id,
                "title": "New Chat",
                "created_at": now,
                "last_active": now,
                "messages": [],
                "metadata": {},
            }

        # Save user message to session
        if session_data and user_message_content:
            user_msg = {
                "role": "user",
                "content": user_message_content,
                "timestamp": datetime.now().isoformat(),
            }
            session_data["messages"].append(user_msg)
            session_data["last_active"] = datetime.now().isoformat()
            _save_session(user_id, session_id, session_data)

        # Collect assistant response
        collected_content = []

        # Forward to Gateway
        # We use a stream to support SSE
        async def event_generator():
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        f"{GATEWAY_BASE_URL}/v1/chat/completions",
                        json=body,
                    ) as response:
                        if response.status_code != 200:
                            error_msg = await response.aread()
                            yield f"data: {json.dumps({'error': f'Gateway error: {response.status_code} - {error_msg.decode()}'})}\n\n"
                            return

                        async for chunk in response.aiter_bytes():
                            # Parse SSE to collect assistant content
                            chunk_str = chunk.decode("utf-8", errors="ignore")
                            for line in chunk_str.split("\n"):
                                if line.startswith("data: "):
                                    data = line[6:].strip()
                                    if data and data != "[DONE]":
                                        try:
                                            parsed = json.loads(data)
                                            content = (
                                                parsed.get("choices", [{}])[0]
                                                .get("delta", {})
                                                .get("content")
                                            )
                                            if content:
                                                collected_content.append(content)
                                        except Exception:
                                            pass
                            yield chunk

                # Save assistant message after streaming completes
                if session_data and collected_content:
                    assistant_msg = {
                        "role": "assistant",
                        "content": "".join(collected_content),
                        "timestamp": datetime.now().isoformat(),
                    }
                    session_data["messages"].append(assistant_msg)
                    session_data["last_active"] = datetime.now().isoformat()
                    _save_session(user_id, session_id, session_data)

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/message", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    发送聊天消息（调用 sage-gateway）

    注意：需要 sage-gateway 服务运行在 GATEWAY_BASE_URL
    """
    import uuid
    from datetime import datetime

    import httpx

    # 1. Handle Session
    session_id = request.session_id
    session_data = None
    user_id = str(current_user.id)

    if session_id:
        session_data = _load_session(user_id, session_id)

    if not session_data:
        # Create new session if not found or not provided
        session_id = session_id or str(uuid.uuid4())
        now = datetime.now().isoformat()
        session_data = {
            "id": session_id,
            "title": "New Chat",
            "created_at": now,
            "last_active": now,
            "messages": [],
            "metadata": {},
        }

    # 2. Append User Message
    user_msg = {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()}
    session_data["messages"].append(user_msg)
    session_data["last_active"] = datetime.now().isoformat()
    _save_session(user_id, session_id, session_data)

    # Resolve model if "sage-default"
    model_to_use = request.model
    if model_to_use == "sage-default":
        # 1. Try environment variable (set by select_llm_model)
        model_to_use = os.getenv("SAGE_CHAT_MODEL")

        # 2. If not set, try to detect from Gateway
        if not model_to_use:
            try:
                from sage.common.config.ports import SagePorts
                from sage.llm import UnifiedInferenceClient

                client = UnifiedInferenceClient.create(
                    control_plane_url=f"http://localhost:{SagePorts.GATEWAY_DEFAULT}/v1"
                )
                detected = client._get_default_llm_model()
                if detected and detected != "default":
                    model_to_use = detected
            except Exception:
                pass

        # 3. Fallback to original if still failed
        if not model_to_use:
            model_to_use = request.model

    try:
        # 调用 sage-gateway 的 OpenAI 兼容接口
        # We pass the session_id to gateway as well, so it can maintain its own state if needed,
        # or we can pass full history if gateway is stateless.
        # For now, let's pass session_id.
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            gateway_response = await client.post(
                f"{GATEWAY_BASE_URL}/v1/chat/completions",
                json={
                    "model": model_to_use,
                    "messages": [{"role": "user", "content": request.message}],
                    "stream": False,
                    "session_id": session_id,  # Pass session_id to gateway
                },
            )

            if gateway_response.status_code != 200:
                raise HTTPException(
                    status_code=gateway_response.status_code,
                    detail=f"Gateway error: {gateway_response.text}",
                )

            data = gateway_response.json()

            # 提取响应内容
            assistant_content = data["choices"][0]["message"]["content"]

            # 3. Append Assistant Message
            assistant_msg = {
                "role": "assistant",
                "content": assistant_content,
                "timestamp": datetime.now().isoformat(),
            }
            session_data["messages"].append(assistant_msg)
            session_data["last_active"] = datetime.now().isoformat()
            _save_session(user_id, session_id, session_data)

            return ChatResponse(
                content=assistant_content,
                session_id=session_id,
                timestamp=datetime.now().isoformat(),
            )

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"无法连接到 SAGE Gateway ({GATEWAY_BASE_URL})。请确保 gateway 服务已启动。",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat 请求失败: {str(e)}")


@app.post("/api/chat/agent")
async def agent_chat(request: AgentChatRequest):
    """Multi-Agent 聊天接口"""
    orchestrator = get_orchestrator()
    stream_handler = get_stream_handler()

    source = orchestrator.process_message(
        message=request.message,
        session_id=request.session_id,
        history=request.history,
        should_index=request.should_index or False,
        metadata=request.metadata or {},
        evidence=request.evidence or [],
    )

    return stream_handler.create_response(source)


@app.post("/api/chat/agent/sync")
async def agent_chat_sync(request: AgentChatRequest):
    """非流式 Agent 聊天接口（调试用）"""
    orchestrator = get_orchestrator()

    steps = []
    text_parts = []

    async for item in orchestrator.process_message(
        message=request.message,
        session_id=request.session_id,
        history=request.history,
        should_index=request.should_index or False,
        metadata=request.metadata or {},
        evidence=request.evidence or [],
    ):
        if hasattr(item, "step_id"):  # AgentStep
            # Handle both dataclass and Pydantic models
            if hasattr(item, "to_dict"):
                steps.append(item.to_dict())
            elif hasattr(item, "dict"):
                steps.append(item.dict())
            else:
                from dataclasses import asdict

                steps.append(asdict(item))
        else:  # str
            text_parts.append(item)

    return {
        "steps": steps,
        "response": "".join(text_parts),
    }


@app.get("/api/chat/sessions", response_model=list[ChatSessionSummary])
async def list_chat_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """获取所有聊天会话"""
    sessions_dir = get_user_sessions_dir(str(current_user.id))
    sessions = []
    if sessions_dir.exists():
        for session_file in sessions_dir.glob("*.json"):
            try:
                with open(session_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert to summary
                    sessions.append(
                        ChatSessionSummary(
                            id=data["id"],
                            title=data.get("title", "Untitled Session"),
                            created_at=data.get("created_at", ""),
                            last_active=data.get("last_active", ""),
                            message_count=len(data.get("messages", [])),
                        )
                    )
            except Exception as e:
                print(f"Error reading session {session_file}: {e}")

    # Sort by last_active desc
    sessions.sort(key=lambda x: x.last_active, reverse=True)
    return sessions


@app.post("/api/chat/sessions", response_model=ChatSessionDetail)
async def create_chat_session(
    payload: ChatSessionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """创建新的聊天会话"""
    import uuid
    from datetime import datetime

    try:
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        session_data = {
            "id": session_id,
            "title": payload.title or "New Session",
            "created_at": now,
            "last_active": now,
            "message_count": 0,
            "messages": [],
            "metadata": {},
        }

        _save_session(str(current_user.id), session_id, session_data)

        return ChatSessionDetail(**session_data)
    except Exception as e:
        print(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@app.get("/api/chat/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """获取单个会话详情"""
    session = _load_session(str(current_user.id), session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return ChatSessionDetail(**session)


@app.post("/api/chat/sessions/{session_id}/clear")
async def clear_chat_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """清空会话历史"""
    from datetime import datetime

    user_id = str(current_user.id)
    session = _load_session(user_id, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    session["messages"] = []
    session["last_active"] = datetime.now().isoformat()
    _save_session(user_id, session_id, session)

    return {"status": "success", "message": "Session cleared"}


@app.patch("/api/chat/sessions/{session_id}/title", response_model=ChatSessionSummary)
async def update_chat_session_title(
    session_id: str,
    payload: ChatSessionTitleUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """更新会话标题"""
    from datetime import datetime

    user_id = str(current_user.id)
    session = _load_session(user_id, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    session["title"] = payload.title
    session["last_active"] = datetime.now().isoformat()
    _save_session(user_id, session_id, session)

    return ChatSessionSummary(
        id=session["id"],
        title=session["title"],
        created_at=session["created_at"],
        last_active=session["last_active"],
        message_count=len(session["messages"]),
    )


@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """删除聊天会话"""
    user_id = str(current_user.id)
    path = _get_session_path(user_id, session_id)
    if path.exists():
        path.unlink()
        return {"status": "success", "message": "Session deleted"}
    raise HTTPException(404, "Session not found")


@app.get("/api/studio/memory/config")
async def get_memory_config():
    """获取记忆配置"""
    import logging
    from pathlib import Path

    import yaml

    # 默认配置
    config = {
        "enabled": True,
        "backends": ["short_term", "long_term"],
        "short_term": {"max_items": 20},
        "long_term": {"enabled": True},
    }

    try:
        # 尝试加载配置文件
        # api.py 在 sage/studio/config/backend/
        # knowledge_sources.yaml 在 sage/studio/config/
        current_dir = Path(__file__).parent
        config_path = current_dir.parent / "knowledge_sources.yaml"

        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
                if "memory" in yaml_data:
                    mem_config = yaml_data["memory"]
                    config["enabled"] = mem_config.get("enabled", True)

                    # 更新 backends 列表
                    if "backends" in mem_config:
                        config["backends"] = list(mem_config["backends"].keys())

                        # 更新具体后端配置
                        if "short_term" in mem_config["backends"]:
                            config["short_term"] = mem_config["backends"]["short_term"]
                        if "long_term" in mem_config["backends"]:
                            config["long_term"] = mem_config["backends"]["long_term"]
    except Exception as e:
        logging.error(f"Failed to load memory config: {e}")

    logging.info(f"Returning memory config: {config}")
    return config


@app.get("/api/chat/memory/stats")
async def get_memory_stats(session_id: str):
    """获取记忆统计"""
    service = get_memory_service(session_id)
    return await service.get_summary()


@app.post("/api/uploads")
async def upload_file(file: UploadFile = File(...)):
    """上传文件"""
    from dataclasses import asdict

    service = get_file_upload_service()
    try:
        # UploadFile.file is a SpooledTemporaryFile which is a file-like object
        metadata = await service.upload_file(file.file, file.filename)
        return asdict(metadata)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/uploads")
async def list_uploaded_files():
    """获取已上传文件列表"""
    from dataclasses import asdict

    service = get_file_upload_service()
    files = service.list_files()
    return [asdict(f) for f in files]


@app.get("/api/uploads/{file_id}")
async def get_uploaded_file(file_id: str):
    """获取单个文件的元数据"""
    from dataclasses import asdict

    service = get_file_upload_service()
    metadata = service.get_file(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found")
    return asdict(metadata)


@app.get("/api/uploads/{file_id}/content")
async def get_uploaded_file_content(file_id: str):
    """获取上传文件的内容"""
    service = get_file_upload_service()
    file_path = service.get_file_path(file_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # 读取文件内容
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        return {"file_id": file_id, "content": content}
    except UnicodeDecodeError:
        # 二进制文件
        raise HTTPException(status_code=400, detail="Binary file cannot be read as text")


class IndexFileRequest(BaseModel):
    """索引文件请求"""

    source_name: str = "user_uploads"  # 知识源名称


@app.post("/api/uploads/{file_id}/index")
async def index_uploaded_file(file_id: str, request: IndexFileRequest):
    """将上传的文件索引到知识库

    这会将文件内容分块并存入向量数据库，使其可通过语义搜索检索。
    """
    from sage.studio.services.knowledge_manager import KnowledgeManager

    service = get_file_upload_service()
    metadata = service.get_file(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = service.get_file_path(file_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File path not found")

    # 索引到知识库
    try:
        km = KnowledgeManager()
        success = await km.add_document(file_path, source_name=request.source_name)

        if success:
            # 标记文件已索引
            service.mark_indexed(file_id)
            return {
                "success": True,
                "file_id": file_id,
                "source_name": request.source_name,
                "message": f"File indexed to '{request.source_name}' knowledge source",
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to index file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@app.get("/api/knowledge/sources")
async def list_knowledge_sources():
    """列出可用的知识源"""
    from sage.studio.services.knowledge_manager import KnowledgeManager

    km = KnowledgeManager()
    sources = []
    for name, source in km.sources.items():
        sources.append(
            {
                "name": name,
                "type": source.type.value,
                "description": source.description,
                "enabled": source.enabled,
                "is_dynamic": source.is_dynamic,
            }
        )
    return sources


class KnowledgeSearchRequest(BaseModel):
    """知识检索请求"""

    query: str
    sources: list[str] | None = None  # None 表示所有已加载的源
    limit: int = 5
    score_threshold: float = 0.6


@app.post("/api/knowledge/search")
async def search_knowledge(request: KnowledgeSearchRequest):
    """在知识库中检索"""
    from sage.studio.services.knowledge_manager import KnowledgeManager

    km = KnowledgeManager()
    try:
        results = await km.search(
            query=request.query,
            sources=request.sources,
            limit=request.limit,
            score_threshold=request.score_threshold,
        )
        return {
            "query": request.query,
            "results": [
                {
                    "content": r.content,
                    "score": r.score,
                    "source": r.source,
                    "metadata": r.metadata,
                }
                for r in results
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.delete("/api/uploads/{file_id}")
async def delete_uploaded_file(file_id: str):
    """删除已上传文件"""
    service = get_file_upload_service()
    success = service.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found")
    return {"success": True, "file_id": file_id}


class WorkflowGenerateRequest(BaseModel):
    """工作流生成请求 (LLM驱动的高级版本)"""

    user_input: str
    session_id: str | None = None
    enable_optimization: bool = False
    optimization_strategy: str = "greedy"  # greedy, parallelization, noop
    constraints: dict | None = None  # max_cost, max_latency, min_quality


@app.post("/api/chat/generate-workflow")
async def generate_workflow_advanced(request: WorkflowGenerateRequest):
    """生成智能工作流 (使用 LLM Pipeline Builder)

    这个端点使用更高级的 LLM 驱动生成，而不是简单的意图识别。
    可选地应用 sage-libs 中的工作流优化算法。

    Args:
        request: 包含用户输入、会话信息、优化选项

    Returns:
        {
            "success": bool,
            "visual_pipeline": {...},  # Studio 可视化格式
            "raw_plan": {...},         # 原始 Pipeline 配置
            "optimization_applied": bool,
            "optimization_metrics": {...},
            "message": str
        }
    """
    import httpx

    from sage.studio.services.workflow_generator import generate_workflow_from_chat

    # 如果提供了 session_id，获取对话历史
    session_messages = None
    if request.session_id:
        try:
            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                response = await client.get(f"{GATEWAY_BASE_URL}/sessions/{request.session_id}")
                if response.status_code == 200:
                    session = response.json()
                    session_messages = session.get("messages", [])
        except httpx.ConnectError:
            # 如果无法连接 Gateway，继续使用仅用户输入
            pass

    # 调用工作流生成器
    try:
        print("🔍 Calling generate_workflow_from_chat with:")
        print(f"  - user_input: {request.user_input}")
        print(f"  - session_messages: {session_messages is not None}")
        print(f"  - enable_optimization: {request.enable_optimization}")

        result = generate_workflow_from_chat(
            user_input=request.user_input,
            session_messages=session_messages,
            enable_optimization=request.enable_optimization,
        )

        print(f"✅ Result returned: {result}")
        print(f"  - Type: {type(result)}")
        if result:
            print(f"  - success: {result.success}")
            print(f"  - visual_pipeline: {result.visual_pipeline is not None}")

    except Exception as e:
        import traceback

        print("❌ Exception in generate_workflow_from_chat:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"工作流生成失败: {str(e)}")

    if result is None:
        raise HTTPException(status_code=500, detail="工作流生成器返回了 None")

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error or "工作流生成失败")

    print("📤 Preparing response...")
    response_data = {
        "success": result.success,
        "visual_pipeline": result.visual_pipeline,
        "raw_plan": result.raw_plan,
        "optimization_applied": result.optimization_applied,
        "optimization_metrics": result.optimization_metrics,
        "message": result.message,
    }
    print(f"✅ Response data prepared: {list(response_data.keys())}")
    return response_data


# ===== Fine-tune API Endpoints =====


class FinetuneCreateRequest(BaseModel):
    """Create fine-tune task request"""

    model_name: str = "Qwen/Qwen2.5-7B-Instruct"
    dataset_file: str  # Path to uploaded dataset
    num_epochs: int = 3
    batch_size: int = 1
    gradient_accumulation_steps: int = 16
    learning_rate: float = 5e-5
    max_length: int = 1024
    load_in_8bit: bool = True


class UseAsBackendRequest(BaseModel):
    """Use finetuned model as backend request"""

    task_id: str


@app.post("/api/finetune/create")
async def create_finetune_task(request: FinetuneCreateRequest):
    """创建微调任务（带 OOM 风险检测）"""
    import torch

    from sage.libs.finetune import finetune_manager

    # GPU 显存检测
    warnings = []
    if torch.cuda.is_available():
        gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)

        # 估算显存需求
        estimated_memory = 0
        if "7B" in request.model_name or "7b" in request.model_name:
            estimated_memory = 14 if request.load_in_8bit else 28
        elif "3B" in request.model_name or "3b" in request.model_name:
            estimated_memory = 6 if request.load_in_8bit else 12
        elif "1.5B" in request.model_name or "1.5b" in request.model_name:
            estimated_memory = 3 if request.load_in_8bit else 6
        elif "0.5B" in request.model_name or "0.5b" in request.model_name:
            estimated_memory = 1 if request.load_in_8bit else 2

        # 添加 batch size 和 sequence length 的额外开销
        estimated_memory += request.batch_size * (request.max_length / 1024) * 0.5

        # OOM 风险检测
        if estimated_memory > gpu_memory_gb * 0.9:
            warnings.append(
                f"⚠️ OOM 风险高：预计需要 {estimated_memory:.1f}GB，但只有 {gpu_memory_gb:.1f}GB 可用"
            )
            warnings.append("建议：减小 batch_size 或 max_length，或启用 8-bit 量化")
        elif estimated_memory > gpu_memory_gb * 0.7:
            warnings.append(
                f"⚠️ OOM 风险中：预计需要 {estimated_memory:.1f}GB，可用 {gpu_memory_gb:.1f}GB"
            )
    else:
        warnings.append("⚠️ 未检测到 GPU，训练将非常缓慢")

    config = {
        "num_epochs": request.num_epochs,
        "batch_size": request.batch_size,
        "gradient_accumulation_steps": request.gradient_accumulation_steps,
        "learning_rate": request.learning_rate,
        "max_length": request.max_length,
        "load_in_8bit": request.load_in_8bit,
    }

    task = finetune_manager.create_task(
        model_name=request.model_name, dataset_path=request.dataset_file, config=config
    )

    # 添加警告日志
    for warning in warnings:
        finetune_manager.add_task_log(task.task_id, warning)

    # Start training immediately
    success = finetune_manager.start_training(task.task_id)
    if not success:
        raise HTTPException(status_code=409, detail="Another training task is running")

    result = task.to_dict()
    result["warnings"] = warnings
    return result


@app.get("/api/finetune/tasks")
async def list_finetune_tasks():
    """列出所有微调任务"""
    from sage.libs.finetune import finetune_manager

    tasks = finetune_manager.list_tasks()
    return [task.to_dict() for task in tasks]


@app.get("/api/finetune/tasks/{task_id}")
async def get_finetune_task(task_id: str):
    """获取微调任务详情"""
    from sage.libs.finetune import finetune_manager

    task = finetune_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@app.get("/api/finetune/models")
async def list_finetune_models():
    """获取可用模型列表（基础模型 + 微调后的模型）"""
    from sage.libs.finetune import finetune_manager

    return finetune_manager.list_available_models()


@app.post("/api/finetune/switch-model")
async def switch_model(model_path: str):
    """切换当前使用的模型并热重启 LLM 服务（无需重启 Studio）"""
    from sage.studio.chat_manager import ChatModeManager

    # Get ChatModeManager instance and apply the model
    chat_manager = ChatModeManager()
    result = chat_manager.apply_finetuned_model(model_path)

    if result["success"]:
        return {
            "message": result["message"],
            "current_model": result["model"],
            "llm_service_restarted": True,
        }
    else:
        raise HTTPException(status_code=500, detail=result["message"])


@app.get("/api/finetune/current-model")
async def get_current_model():
    """获取当前使用的模型"""
    from sage.libs.finetune import finetune_manager

    return {"current_model": finetune_manager.get_current_model()}


@app.post("/api/finetune/upload-dataset")
async def upload_dataset(file: UploadFile = File(...)):
    """上传微调数据集"""
    from pathlib import Path

    # Validate file type
    if not file.filename.endswith((".json", ".jsonl")):
        raise HTTPException(status_code=400, detail="Only JSON/JSONL files are supported")

    # Save to uploads directory
    upload_dir = Path.home() / ".sage" / "studio_finetune" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{int(time.time())}_{file.filename}"

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        return {"file_path": str(file_path), "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@app.get("/api/finetune/tasks/{task_id}/download")
async def download_finetuned_model(task_id: str):
    """下载微调后的模型（打包为 tar.gz）"""
    import tarfile
    from pathlib import Path

    from fastapi.responses import FileResponse

    from sage.libs.finetune import finetune_manager

    task = finetune_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Task is not completed yet")

    model_dir = Path(task.output_dir)
    if not model_dir.exists():
        raise HTTPException(status_code=404, detail="Model directory not found")

    # 创建临时打包目录
    temp_dir = Path.home() / ".sage" / "studio_finetune" / "downloads"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 打包模型文件
    archive_path = temp_dir / f"{task_id}.tar.gz"
    try:
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(model_dir, arcname=task_id)

        return FileResponse(
            path=str(archive_path),
            media_type="application/gzip",
            filename=f"{task_id}_finetuned_model.tar.gz",
            headers={
                "Content-Disposition": f'attachment; filename="{task_id}_finetuned_model.tar.gz"'
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to package model: {e}")


@app.delete("/api/finetune/tasks/{task_id}")
async def delete_finetune_task(task_id: str):
    """删除微调任务（仅允许删除已完成、失败或取消的任务）"""
    from sage.libs.finetune import FinetuneStatus, finetune_manager

    if finetune_manager.delete_task(task_id):
        return {"status": "success", "message": f"任务 {task_id} 已删除"}
    else:
        task = finetune_manager.tasks.get(task_id)
        if not task:
            # 尝试重新加载任务
            finetune_manager._load_tasks()
            task = finetune_manager.tasks.get(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        elif task.status in (
            FinetuneStatus.TRAINING,
            FinetuneStatus.PREPARING,
            FinetuneStatus.QUEUED,
        ):
            raise HTTPException(status_code=400, detail="无法删除运行中或排队中的任务")
        else:
            raise HTTPException(status_code=500, detail="Failed to delete task")


@app.post("/api/finetune/tasks/{task_id}/cancel")
async def cancel_finetune_task(task_id: str):
    """取消运行中的微调任务"""
    from sage.libs.finetune import FinetuneStatus, finetune_manager

    task = finetune_manager.tasks.get(task_id)
    if not task:
        # 任务不在内存中，尝试重新加载
        print(f"[API] Task {task_id} not found in memory, attempting to reload tasks...")
        finetune_manager._load_tasks()
        task = finetune_manager.tasks.get(task_id)

        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task not found: {task_id}. Available tasks: {list(finetune_manager.tasks.keys())}",
            )

    if task.status not in (
        FinetuneStatus.TRAINING,
        FinetuneStatus.PREPARING,
        FinetuneStatus.QUEUED,
    ):
        raise HTTPException(status_code=400, detail="任务不在运行中，无法取消")

    if finetune_manager.cancel_task(task_id):
        return {"status": "success", "message": f"任务 {task_id} 已取消"}
    else:
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@app.get("/api/finetune/models/base")
async def list_base_models():
    """列出推荐的基础模型（按显存需求分类）"""
    return {
        "recommended_for_rtx3060": [
            {
                "name": "Qwen/Qwen2.5-Coder-1.5B-Instruct",
                "size": "1.5B",
                "vram_required": "6-8GB",
                "description": "代码专精，最适合 RTX 3060（推荐）",
                "training_time": "2-4小时 (1000样本)",
            },
            {
                "name": "Qwen/Qwen2.5-0.5B-Instruct",
                "size": "500M",
                "vram_required": "4-6GB",
                "description": "超轻量级，训练最快",
                "training_time": "1-2小时 (1000样本)",
            },
            {
                "name": "Qwen/Qwen2.5-1.5B-Instruct",
                "size": "1.5B",
                "vram_required": "6-8GB",
                "description": "通用对话模型，平衡性能和显存",
                "training_time": "2-4小时 (1000样本)",
            },
        ],
        "advanced_models": [
            {
                "name": "Qwen/Qwen2.5-3B-Instruct",
                "size": "3B",
                "vram_required": "10-12GB",
                "description": "更强性能，需要更多显存",
                "training_time": "4-6小时 (1000样本)",
            },
            {
                "name": "Qwen/Qwen2.5-7B-Instruct",
                "size": "7B",
                "vram_required": "16-20GB",
                "description": "高性能模型，需要 RTX 4090 或更强",
                "training_time": "8-12小时 (1000样本)",
            },
        ],
    }


@app.post("/api/finetune/prepare-sage-docs")
async def prepare_sage_docs(force_refresh: bool = False):
    """准备 SAGE 官方文档作为训练数据"""
    from sage.studio.services.docs_processor import get_docs_processor

    try:
        processor = get_docs_processor()

        # 准备训练数据
        data_file = processor.prepare_training_data(force_refresh=force_refresh)

        # 获取统计信息
        stats = processor.get_stats(data_file)

        return {
            "status": "success",
            "message": "SAGE 文档已准备完成",
            "data_file": str(data_file),
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prepare SAGE docs: {e}")


@app.post("/api/finetune/use-as-backend")
async def use_finetuned_as_backend(request: UseAsBackendRequest):
    """将微调后的模型设置为 Studio 对话后端"""
    from sage.libs.finetune import finetune_manager

    try:
        task = finetune_manager.get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.status != "completed":
            raise HTTPException(status_code=400, detail="Task is not completed yet")

        # 获取模型路径
        model_path = Path(task.output_dir)
        if not model_path.exists():
            raise HTTPException(status_code=404, detail="Model directory not found")

        # 注册到 vLLM Registry
        from sage.platform.llm.vllm_registry import vllm_registry

        model_name = f"sage-finetuned-{request.task_id}"

        # 自动检测 GPU 数量和显存
        try:
            import torch

            num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0
            # 获取单个 GPU 的显存（以 GB 为单位）
            if num_gpus > 0:
                gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
            else:
                gpu_memory_gb = 0
        except Exception:
            num_gpus = 0
            gpu_memory_gb = 0

        # 根据 GPU 配置模型参数
        config = {
            "trust_remote_code": True,
            "max_model_len": 2048,  # 默认值
        }

        # 只有当有 GPU 时才设置 GPU 相关参数
        if num_gpus > 0:
            # 根据显存大小调整 max_model_len
            if gpu_memory_gb >= 24:  # 24GB+ (A100, RTX 4090, etc.)
                config["max_model_len"] = 4096
                config["gpu_memory_utilization"] = 0.85
            elif gpu_memory_gb >= 16:  # 16GB+ (V100, RTX 4080, etc.)
                config["max_model_len"] = 3072
                config["gpu_memory_utilization"] = 0.8
            elif gpu_memory_gb >= 8:  # 8GB+ (RTX 3070, etc.)
                config["max_model_len"] = 2048
                config["gpu_memory_utilization"] = 0.75
            else:  # < 8GB
                config["max_model_len"] = 1024
                config["gpu_memory_utilization"] = 0.7

            # 如果有多个 GPU 且模型较大，启用张量并行
            if num_gpus > 1:
                config["tensor_parallel_size"] = num_gpus

        # 注册模型
        vllm_registry.register_model(
            model_name=model_name,
            model_path=str(model_path),
            config=config,
        )

        # 切换到该模型
        vllm_registry.switch_model(model_name)

        # 更新环境变量（供 RAG pipeline 使用）
        os.environ["SAGE_STUDIO_LLM_MODEL"] = model_name
        os.environ["SAGE_STUDIO_LLM_PATH"] = str(model_path)

        return {
            "status": "success",
            "message": f"已切换到微调模型: {model_name}",
            "model_name": model_name,
            "model_path": str(model_path),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch backend: {e}")


@app.get("/api/system/gpu-info")
async def get_gpu_info():
    """Get GPU information for finetune recommendations"""
    try:
        import torch

        gpu_info = {
            "available": torch.cuda.is_available(),
            "count": 0,
            "devices": [],
            "recommendation": "CPU 模式（不推荐微调）",
        }

        if torch.cuda.is_available():
            gpu_info["count"] = torch.cuda.device_count()

            for i in range(gpu_info["count"]):
                device_name = torch.cuda.get_device_name(i)
                device_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)  # GB

                gpu_info["devices"].append(
                    {
                        "id": i,
                        "name": device_name,
                        "memory_gb": round(device_memory, 1),
                    }
                )

            # 生成推荐配置
            if gpu_info["count"] == 1:
                gpu_name = gpu_info["devices"][0]["name"]
                gpu_memory = gpu_info["devices"][0]["memory_gb"]

                # 根据显存推荐模型
                if gpu_memory >= 24:
                    gpu_info["recommendation"] = (
                        f"{gpu_name} ({gpu_memory}GB): 推荐 Qwen 2.5 Coder 7B 或 3B"
                    )
                elif gpu_memory >= 12:
                    gpu_info["recommendation"] = (
                        f"{gpu_name} ({gpu_memory}GB): 推荐 Qwen 2.5 Coder 3B 或 1.5B"
                    )
                elif gpu_memory >= 8:
                    gpu_info["recommendation"] = (
                        f"{gpu_name} ({gpu_memory}GB): 推荐 Qwen 2.5 Coder 1.5B（最佳平衡）或 0.5B（最快训练）"
                    )
                else:
                    gpu_info["recommendation"] = (
                        f"{gpu_name} ({gpu_memory}GB): 推荐 Qwen 2.5 Coder 0.5B"
                    )
            else:
                total_memory = sum(d["memory_gb"] for d in gpu_info["devices"])
                gpu_info["recommendation"] = (
                    f"检测到 {gpu_info['count']} 块 GPU（总显存 {total_memory:.1f}GB）：支持多卡并行训练"
                )

        return gpu_info

    except Exception as e:
        return {
            "available": False,
            "count": 0,
            "devices": [],
            "recommendation": f"GPU 检测失败: {e}",
        }


# ==================== LLM 状态 API ====================


class SelectModelRequest(BaseModel):
    model_name: str
    base_url: str


def _get_models_config_path(create_dir: bool = False) -> Path | None:
    """Locate config/models.json, optionally creating the directory."""
    try:
        from sage.common.config import find_sage_project_root

        project_root = find_sage_project_root()
    except Exception:
        project_root = None

    base_dir = project_root or Path.cwd()
    config_dir = base_dir / "config"

    if create_dir:
        config_dir.mkdir(parents=True, exist_ok=True)
    elif not config_dir.exists():
        return None

    return config_dir / "models.json"


def _expand_api_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    if value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.getenv(env_var, "")
    return value


def _load_models_config(filter_missing: bool = False) -> tuple[list[dict[str, Any]], Path | None]:
    path = _get_models_config_path()
    if not path or not path.exists():
        return ([], path)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            models: list[dict[str, Any]] = []
            for entry in data:
                if isinstance(entry, dict):
                    entry_copy = dict(entry)
                    raw_key = entry_copy.get("api_key")
                    expanded_key = _expand_api_key(raw_key)

                    # Skip if API key is required (variable reference) but missing/empty
                    if (
                        filter_missing
                        and isinstance(raw_key, str)
                        and raw_key.startswith("${")
                        and not expanded_key
                    ):
                        continue

                    entry_copy["api_key"] = expanded_key
                    models.append(entry_copy)
            return models, path
    except Exception:
        pass
    return ([], path)


def _save_models_config(path: Path | None, models: list[dict[str, Any]]) -> None:
    if not path:
        return
    target_path = path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(models, indent=4, ensure_ascii=False), encoding="utf-8")


def _persist_model_selection(model_name: str, base_url: str) -> str:
    """Update config/models.json default selection and return API key."""
    models, path = _load_models_config()
    if path is None:
        path = _get_models_config_path(create_dir=True)
    target_entry: dict[str, Any] | None = None

    for entry in models:
        names_match = entry.get("name") == model_name
        url_match = (
            _base_urls_match(entry.get("base_url"), base_url) if entry.get("base_url") else False
        )
        if names_match and (url_match or not entry.get("base_url")):
            entry["base_url"] = base_url
            target_entry = entry
            break

    if target_entry is None:
        target_entry = {
            "name": model_name,
            "base_url": base_url,
            "is_local": _is_loopback_url(base_url),
        }
        models.append(target_entry)
    else:
        target_entry["is_local"] = _is_loopback_url(base_url)

    for entry in models:
        entry["default"] = entry is target_entry

    _save_models_config(path, models)
    return _expand_api_key(target_entry.get("api_key"))


def _discover_launcher_models() -> list[dict[str, Any]]:
    try:
        from sage.llm import LLMLauncher
    except ImportError:
        return []

    models: list[dict[str, Any]] = []
    for service in LLMLauncher.discover_running_services():
        # Filter out embedding models
        if service.get("config", {}).get("engine_kind") == "embedding":
            continue

        model_name = service.get("served_model_name") or service.get("model") or "local-llm"
        if "embedding" in model_name.lower():
            continue

        models.append(
            {
                "name": model_name,
                "base_url": service.get("base_url"),
                "is_local": True,
                "description": "Auto-detected Local Model",
            }
        )
    return models


def _normalize_base_url(base_url: str | None) -> str | None:
    return base_url.rstrip("/") if base_url else base_url


def _normalize_probe_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    parsed = urlparse(base_url)
    host = parsed.hostname
    replacement = None
    if not host or host in {"0.0.0.0", "*"}:
        replacement = "127.0.0.1"
    elif host in {"::", "[::]"}:
        replacement = "::1"

    if replacement:
        host_token = replacement
        if ":" in host_token and not host_token.startswith("["):
            host_token = f"[{host_token}]"
        if parsed.port:
            netloc = f"{host_token}:{parsed.port}"
        else:
            netloc = host_token
        parsed = parsed._replace(netloc=netloc)
        return urlunparse(parsed).rstrip("/")

    return base_url.rstrip("/")


def _canon_host(host: str | None) -> str | None:
    if not host:
        return None
    host = host.lower()
    if host in {"0.0.0.0", "*", "localhost"}:
        return "127.0.0.1"
    if host in {"::", "[::]"}:
        return "::1"
    return host


def _base_url_signature(base_url: str | None) -> tuple[str, str, int, str] | None:
    if not base_url:
        return None

    candidate = base_url.strip()
    if not candidate:
        return None

    parsed = urlparse(candidate if "://" in candidate else f"http://{candidate}")
    scheme = parsed.scheme or "http"
    host = _canon_host(parsed.hostname) or ""
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80

    path = parsed.path.rstrip("/")
    if path in ("", "/v1"):
        path = ""

    return (scheme, host, port, path)


def _base_urls_match(a: str | None, b: str | None) -> bool:
    sig_a = _base_url_signature(a)
    sig_b = _base_url_signature(b)
    return bool(sig_a and sig_b and sig_a == sig_b)


def _build_health_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/v1"):
        health_path = path[:-3] + "/health"
    else:
        health_path = path + "/health"
    return urlunparse(parsed._replace(path=health_path, query="", fragment=""))


def _is_loopback_url(base_url: str | None) -> bool:
    if not base_url:
        return False
    parsed = urlparse(base_url)
    host = parsed.hostname
    if not host:
        return False
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _probe_llm_endpoint(base_url: str | None, headers: dict[str, str] | None = None) -> bool:
    normalized = _normalize_probe_base_url(base_url)
    if not normalized:
        return False
    headers = headers or {}

    try:
        health_url = _build_health_url(normalized)
        resp = requests.get(health_url, headers=headers, timeout=2.0)
        if resp.status_code == 200:
            return True
    except Exception:
        pass

    try:
        resp = requests.get(f"{normalized}/models", headers=headers, timeout=2.0)
        if resp.status_code == 200:
            return True
    except Exception:
        pass

    try:
        parsed = urlparse(normalized)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if host:
            import socket

            with socket.create_connection((host, port), timeout=2.0):
                return True
    except Exception:
        pass

    return False


@app.post("/api/llm/select")
async def select_llm_model(request: SelectModelRequest):
    """选择要使用的 LLM 模型"""
    try:
        # 更新环境变量，这样后续的 get_llm_status 调用（会创建新的 UnifiedInferenceClient）
        # 就会使用新的配置
        os.environ["SAGE_CHAT_MODEL"] = request.model_name
        os.environ["SAGE_CHAT_BASE_URL"] = request.base_url

        api_key = ""
        try:
            api_key = _persist_model_selection(request.model_name, request.base_url)
        except Exception as exc:
            print(f"Failed to persist selected model: {exc}")

        if api_key:
            os.environ["SAGE_CHAT_API_KEY"] = api_key
            print(f"Set API key for model {request.model_name}")
        else:
            # 如果没有找到特定的 API Key，清除环境变量，以免使用旧的
            if "SAGE_CHAT_API_KEY" in os.environ:
                del os.environ["SAGE_CHAT_API_KEY"]

        # Register with Control Plane
        try:
            parsed = urlparse(request.base_url)
            host = parsed.hostname or "localhost"
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            register_url = f"{GATEWAY_BASE_URL}/v1/management/engines/register"

            payload = {
                "engine_id": f"ext-{request.model_name}",
                "model_id": request.model_name,
                "host": host,
                "port": port,
                "engine_kind": "llm",
                "metadata": {"source": "studio_select", "scheme": parsed.scheme or "http"},
            }

            requests.post(register_url, json=payload, timeout=2)
            print(f"Registered model {request.model_name} with Control Plane")
        except Exception as e:
            print(f"Failed to register model with Control Plane: {e}")

        return {"status": "success", "message": f"已切换到模型: {request.model_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换模型失败: {str(e)}")


@app.get("/api/llm/status")
async def get_llm_status():
    """获取当前运行的 LLM 服务状态"""
    try:
        from sage.llm import UnifiedInferenceClient
    except Exception:
        UnifiedInferenceClient = None  # type: ignore[assignment]

    try:
        env_base_url = os.getenv("SAGE_CHAT_BASE_URL", "")
        env_model_name = os.getenv("SAGE_CHAT_MODEL", "")

        # Start with explicit environment variables (highest priority)
        base_url = env_base_url
        model_name = env_model_name

        # Next, honor persisted default selection from config/models.json when env is not set
        # This keeps frontend selections sticky across restarts without being overwritten by
        # Control Plane discovery.
        config_models, _ = _load_models_config(filter_missing=False)
        persisted_default = next((m for m in config_models if m.get("default")), None)
        persisted_base_url = (
            _normalize_base_url(persisted_default.get("base_url")) if persisted_default else None
        )
        if not base_url and persisted_base_url:
            base_url = persisted_base_url
        if not model_name and persisted_default:
            model_name = persisted_default.get("name", "")

        use_control_plane = not base_url and not model_name and not persisted_default

        if UnifiedInferenceClient:
            try:
                # Only fall back to Control Plane when nothing is configured/persisted
                if use_control_plane:
                    client = UnifiedInferenceClient.create(
                        control_plane_url=f"{GATEWAY_BASE_URL}/v1"
                    )
                    base_url = client.config.llm_base_url or base_url
                    model_name = client.config.llm_model or model_name

                # Try to fetch model name if still missing but base_url is known
                if not model_name and base_url:
                    model_name = UnifiedInferenceClient._fetch_model_name(base_url) or model_name
            except Exception:
                pass

        normalized_base_url = _normalize_base_url(base_url)
        is_local = _is_loopback_url(normalized_base_url)
        display_model_name = model_name or ("未配置 LLM 服务" if not base_url else "未命名模型")

        status = {
            "running": False,
            "healthy": False,
            "service_type": "not_configured" if not base_url else "remote_api",
            "model_name": display_model_name,
            "base_url": normalized_base_url or base_url,
            "is_local": is_local,
            "details": {},
        }

        if base_url:
            status["running"] = True

        # Local detailed status
        if is_local and base_url:
            probe_url = _normalize_probe_base_url(base_url)
            if probe_url:
                status["base_url"] = probe_url
                try:
                    health_resp = requests.get(_build_health_url(probe_url), timeout=2)
                    status["healthy"] = health_resp.status_code == 200
                    status["service_type"] = "local_vllm"

                    models_resp = requests.get(f"{probe_url}/models", timeout=2)
                    if models_resp.status_code == 200:
                        models_data = models_resp.json()
                        if models_data.get("data"):
                            first_model = models_data["data"][0]
                            status["details"] = {
                                "model_id": first_model.get("id", ""),
                                "max_model_len": first_model.get("max_model_len", 0),
                                "owned_by": first_model.get("owned_by", ""),
                            }
                            status["model_name"] = first_model.get("id", status["model_name"])
                except Exception as exc:
                    status["error"] = str(exc)

        # Build available model list
        # 复用前面读取的配置，避免重复加载
        available_models = []
        for model in config_models:
            # Filter out embedding models
            if model.get("engine_kind") == "embedding":
                continue
            # Double check for embedding in name/description if engine_kind is missing
            if "embedding" in model.get("name", "").lower():
                continue
            if "embedding" in model.get("description", "").lower():
                continue
            available_models.append(dict(model))

        def _merge_model(entry: dict[str, Any]) -> None:
            entry_url = entry.get("base_url")
            for existing in available_models:
                existing_url = existing.get("base_url")
                names_match = entry.get("name") and entry.get("name") == existing.get("name")
                urls_match = _base_urls_match(entry_url, existing_url)
                if urls_match or (not entry_url and not existing_url and names_match):
                    existing.update({k: v for k, v in entry.items() if v is not None})
                    return
            available_models.append(entry)

        for detected in _discover_launcher_models():
            _merge_model(detected)

        if not available_models:
            default_base = f"http://127.0.0.1:{SagePorts.BENCHMARK_LLM}/v1"
            defaults = [
                {
                    "name": "Qwen/Qwen2.5-0.5B-Instruct",
                    "base_url": default_base,
                    "is_local": True,
                    "description": "Local Small Model (Fast, CPU-friendly)",
                },
                {
                    "name": "Qwen/Qwen2.5-7B-Instruct",
                    "base_url": default_base,
                    "is_local": True,
                    "description": "Local Standard Model (Requires GPU)",
                },
            ]
            for entry in defaults:
                _merge_model(entry)

        cloud_api_key = os.getenv("SAGE_CHAT_API_KEY")
        cloud_base_url = os.getenv("SAGE_CHAT_BASE_URL")
        if cloud_api_key and cloud_base_url:
            cloud_entry = {
                "name": os.getenv("SAGE_CHAT_MODEL", "qwen-turbo-2025-02-11"),
                "base_url": _normalize_base_url(cloud_base_url),
                "is_local": False,
                "description": "Cloud API (Configured in .env)",
                "api_key": cloud_api_key,
                "healthy": True,
            }
            _merge_model(cloud_entry)

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            openai_entry = {
                "name": os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo"),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "is_local": False,
                "description": "OpenAI API (Configured in .env)",
                "api_key": openai_api_key,
                "healthy": True,
            }
            _merge_model(openai_entry)

        import concurrent.futures

        def evaluate_model(model: dict[str, Any]) -> dict[str, Any]:
            entry = dict(model)
            base = entry.get("base_url")
            headers = {}
            if entry.get("api_key"):
                headers["Authorization"] = f"Bearer {entry['api_key']}"

            if not base:
                entry["healthy"] = False
                return entry

            if not entry.get("is_local") and entry.get("healthy"):
                return entry

            entry["healthy"] = _probe_llm_endpoint(base, headers=headers)
            return entry

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            available_models = list(executor.map(evaluate_model, available_models))

        # Prefer healthy local models even if cloud env vars are present; fall back to any healthy.
        preferred_model: dict[str, Any] | None = None
        for model in available_models:
            if model.get("is_local") and model.get("healthy") and model.get("default"):
                preferred_model = model
                break
        if not preferred_model:
            for model in available_models:
                if model.get("is_local") and model.get("healthy"):
                    preferred_model = model
                    break
        if not preferred_model:
            for model in available_models:
                if model.get("healthy"):
                    preferred_model = model
                    break

        if preferred_model:
            status["base_url"] = preferred_model.get("base_url") or status.get("base_url")
            status["model_name"] = preferred_model.get("name") or status.get("model_name")
            status["is_local"] = preferred_model.get("is_local", status.get("is_local"))
            status["service_type"] = (
                "local_vllm" if preferred_model.get("is_local") else "remote_api"
            )
            if preferred_model.get("base_url"):
                status["running"] = True

        status_base_url = status.get("base_url")
        match_found = False
        for model in available_models:
            if _base_urls_match(status_base_url, model.get("base_url")):
                status["healthy"] = model.get("healthy", False)
                status["model_name"] = model.get("name", status["model_name"])
                match_found = True
                break

        if not match_found and status["model_name"] and status.get("base_url"):
            available_models.insert(
                0,
                {
                    "name": status["model_name"],
                    "base_url": status["base_url"],
                    "is_local": status["is_local"],
                    "description": "Current Model",
                    "healthy": status["healthy"],
                },
            )

        status["available_models"] = available_models

        return status

    except Exception as e:
        return {
            "running": False,
            "healthy": False,
            "service_type": "error",
            "error": str(e),
        }


# ==================== Dataset Management APIs ====================


@app.get("/api/datasets/sources")
async def list_dataset_sources():
    """列出所有可用的数据源"""
    try:
        from sage.data import DataManager

        manager = DataManager.get_instance()
        sources = manager.list_sources()

        result = []
        for source_name in sources:
            metadata = manager.get_source_metadata(source_name)
            result.append(
                {
                    "name": metadata.name,
                    "description": metadata.description,
                    "type": metadata.type,
                    "format": metadata.format,
                    "size": metadata.size,
                    "license": metadata.license,
                    "version": metadata.version,
                    "maintainer": metadata.maintainer,
                    "tags": metadata.tags,
                }
            )

        return {"sources": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load datasets: {str(e)}")


@app.get("/api/datasets/usages")
async def list_dataset_usages():
    """列出所有用途配置"""
    try:
        from sage.data import DataManager

        manager = DataManager.get_instance()
        usages = manager.list_usages()

        result = []
        for usage_name in usages:
            try:
                profile = manager.get_by_usage(usage_name)
                result.append(
                    {
                        "name": usage_name,
                        "description": profile.description,
                        "datasets": profile.list_datasets(),
                    }
                )
            except Exception as e:
                result.append(
                    {
                        "name": usage_name,
                        "description": f"Error: {str(e)}",
                        "datasets": [],
                    }
                )

        return {"usages": result, "count": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load usages: {str(e)}")


@app.get("/api/datasets/sources/{source_name}")
async def get_dataset_source(source_name: str):
    """获取特定数据源的详细信息"""
    try:
        from sage.data import DataManager

        manager = DataManager.get_instance()

        if source_name not in manager.list_sources():
            raise HTTPException(status_code=404, detail=f"Dataset '{source_name}' not found")

        metadata = manager.get_source_metadata(source_name)

        # Find which usages include this source
        usages_with_source = []
        for usage_name in manager.list_usages():
            try:
                profile = manager.get_by_usage(usage_name)
                if source_name in [profile.datasets.get(k) for k in profile.datasets]:
                    usages_with_source.append(usage_name)
            except Exception:
                pass

        return {
            "name": metadata.name,
            "description": metadata.description,
            "type": metadata.type,
            "format": metadata.format,
            "size": metadata.size,
            "license": metadata.license,
            "version": metadata.version,
            "maintainer": metadata.maintainer,
            "tags": metadata.tags,
            "used_in": usages_with_source,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {str(e)}")


@app.get("/api/datasets/usages/{usage_name}")
async def get_dataset_usage(usage_name: str):
    """获取特定用途配置的详细信息"""
    try:
        from sage.data import DataManager

        manager = DataManager.get_instance()

        if usage_name not in manager.list_usages():
            raise HTTPException(status_code=404, detail=f"Usage '{usage_name}' not found")

        profile = manager.get_by_usage(usage_name)

        # Get metadata for each dataset in this usage
        datasets_info = []
        for ds_name, source_name in profile.datasets.items():
            try:
                metadata = manager.get_source_metadata(source_name)
                datasets_info.append(
                    {
                        "alias": ds_name,
                        "source": source_name,
                        "description": metadata.description,
                        "type": metadata.type,
                    }
                )
            except Exception:
                datasets_info.append(
                    {
                        "alias": ds_name,
                        "source": source_name,
                        "description": "N/A",
                        "type": "unknown",
                    }
                )

        return {
            "name": usage_name,
            "description": profile.description,
            "datasets": datasets_info,
            "dataset_count": len(datasets_info),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load usage: {str(e)}")


@app.post("/api/datasets/test/{source_name}")
async def test_dataset_source(source_name: str):
    """测试加载数据源"""
    try:
        from sage.data import DataManager

        manager = DataManager.get_instance()

        if source_name not in manager.list_sources():
            raise HTTPException(status_code=404, detail=f"Dataset '{source_name}' not found")

        # Try to load the dataset
        loader = manager.get_by_source(source_name)

        return {
            "success": True,
            "source": source_name,
            "loader_type": type(loader).__name__,
            "message": f"Successfully loaded {source_name}",
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "source": source_name,
            "error": str(e),
            "message": f"Failed to load {source_name}: {str(e)}",
        }


if __name__ == "__main__":
    # NOTE: 后端 API 已合并到 Gateway，推荐通过 sage gateway start 启动。
    # 此处保留用于独立调试，生产环境请使用 Gateway。
    uvicorn.run(app, host="0.0.0.0", port=SagePorts.GATEWAY_DEFAULT)
